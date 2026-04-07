import base64
import os

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash


def register_user_api(app, admin_config, add_user_to_db, delete_user_from_db, get_db, cert_dir, logger):
    api_bp = Blueprint('user_api', __name__)

    def _unauthorized():
        response = jsonify({'success': False, 'error': 'Authentication required'})
        response.status_code = 401
        response.headers['WWW-Authenticate'] = 'Basic realm="VPN Admin API"'
        return response

    def _is_authorized():
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return False
        return (
            auth.username == admin_config['username'] and
            check_password_hash(admin_config['password'], auth.password)
        )

    def _resolve_username():
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            return payload.get('username', '').strip()
        return (request.form.get('username') or '').strip()

    @api_bp.route('/api/users', methods=['POST'])
    def add_user_api():
        if not _is_authorized():
            return _unauthorized()

        username = _resolve_username()
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400

        if not add_user_to_db(username):
            return jsonify({'success': False, 'error': 'Cannot add user'}), 400

        config_files = []
        for ext in ['mobileconfig', 'sswan', 'p12']:
            cert_name = f'{username}.{ext}'
            cert_path = os.path.join(cert_dir, cert_name)
            if os.path.exists(cert_path):
                with open(cert_path, 'rb') as cert_file:
                    encoded = base64.b64encode(cert_file.read()).decode('ascii')
                config_files.append({
                    'filename': cert_name,
                    'content_base64': encoded
                })

        return jsonify({
            'success': True,
            'username': username,
            'config_files': config_files
        }), 201

    @api_bp.route('/api/users/<username>', methods=['DELETE'])
    def delete_user_api(username):
        if not _is_authorized():
            return _unauthorized()

        username = (username or '').strip()
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT username FROM vpn_users WHERE username = ?', (username,))
        user_exists = c.fetchone() is not None
        conn.close()

        if not user_exists:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        if not delete_user_from_db(username):
            logger.error(f"API failed to delete user: {username}")
            return jsonify({'success': False, 'error': 'Cannot delete user'}), 400

        return jsonify({'success': True, 'username': username})

    app.register_blueprint(api_bp)
