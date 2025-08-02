from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from functools import wraps
import os
import sqlite3
from datetime import datetime, timedelta
import logging
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
import secrets
import string

# Настройка путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = BASE_DIR + '/logs/vpn-admin.log'
CERT_DIR = os.path.join(BASE_DIR, 'certificates')
DB_PATH = os.path.join(BASE_DIR, 'vpn_users.db')

# Создаем необходимые директории
os.makedirs(CERT_DIR, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)
logger = logging.getLogger(__name__)

# Добавляем вывод логов в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

app = Flask(__name__)
app.secret_key = '9QrDj806Rrs0Pf2jfwLvbGDbrN1zWMsL'

# Конфигурация
ADMIN_CONFIG = {
    'username': 'admin',
    'password': generate_password_hash('admin')
}

# Настройки блокировки
LOGIN_ATTEMPTS = defaultdict(list)
MAX_ATTEMPTS = 3
BLOCK_TIME = 30


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            logger.debug("User not logged in, redirecting to login page")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def root():
    logger.info("Accessing root route")
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.info(f"Accessing login route. Method: {request.method}")
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if (username == ADMIN_CONFIG['username'] and
                check_password_hash(ADMIN_CONFIG['password'], password)):
            session['logged_in'] = True
            flash('Успешная авторизация')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверные учетные данные')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    logger.info("Accessing dashboard route")
    try:
        users = load_users()
        # Преобразуем даты в объекты datetime для корректной сортировки
        for username, data in users.items():
            if isinstance(data['created_at'], str):
                data['created_at'] = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S')
        return render_template('index.html', users=users, format_date=format_date)
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Произошла ошибка при загрузке страницы')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Вы вышли из системы')
    return redirect(url_for('login'))


# Функции для работы с базой данных
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Существующая таблица vpn_users
    c.execute('''
        CREATE TABLE IF NOT EXISTS vpn_users (
            username TEXT PRIMARY KEY,
            display_name TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN NOT NULL DEFAULT 1
        )
    ''')

    # Новая таблица для ссылок на сертификаты
    c.execute('''
        CREATE TABLE IF NOT EXISTS cert_links (
            id TEXT PRIMARY KEY,
            username TEXT,
            platform TEXT,
            password TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES vpn_users(username) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def get_db():
    return sqlite3.connect(DB_PATH)


def load_users():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT username, display_name, created_at, active FROM vpn_users')
    users = {}
    for row in c.fetchall():
        users[row[0]] = {
            'display_name': row[1],
            'created_at': row[2],
            'active': bool(row[3])
        }
    conn.close()
    return users


def add_user_to_db(username):
    try:
        command_text = f'ikev2.sh --addclient {username}'
        os.popen(command_text).read()

        # Копируем файл на место публикации
        cp_cmd = f'mv /root/{username}.mobileconfig {CERT_DIR}'
        os.popen(cp_cmd)

        cp_cmd = f'mv /root/{username}.sswan {CERT_DIR}'
        os.popen(cp_cmd)

        cp_cmd = f'mv /root/{username}.p12 {CERT_DIR}'
        os.popen(cp_cmd)

        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO vpn_users (username) VALUES (?)', (username,))
        conn.commit()
        conn.close()
        return True
    except:
        return False


def delete_user_from_db(username):
    try:
        # Автоматически подтверждаем удаление через echo y |
        os.popen(f"echo y | ikev2.sh --revokeclient {username}").read()
        os.popen(f"echo y | ikev2.sh --deleteclient {username}").read()

        # Удаляем сертификаты
        for ext in ['mobileconfig', 'sswan', 'p12']:
            cert_file = os.path.join(CERT_DIR, f"{username}.{ext}")
            if os.path.exists(cert_file):
                os.remove(cert_file)

        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM vpn_users WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error deleting user from db: {str(e)}")
        return False


def toggle_user_status(username):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE vpn_users SET active = NOT active WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    return True


# Маршруты для управления пользователями
@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    try:
        username = request.form.get('username')
        if not username:
            flash('Имя пользователя обязательно')
            return redirect(url_for('dashboard'))

        if add_user_to_db(username):
            flash('Пользователь успешно добавлен')
        else:
            flash('Пользователь уже существует')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        flash('Ошибка при добавлении пользователя')
        return redirect(url_for('dashboard'))


@app.route('/delete_user/<username>')
@login_required
def delete_user(username):
    try:
        if delete_user_from_db(username):
            flash('Пользователь удален')
        else:
            flash('Ошибка при удалении пользователя')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        flash('Ошибка при удалении пользователя')
        return redirect(url_for('dashboard'))


@app.route('/toggle_user/<username>')
@login_required
def toggle_user(username):
    try:
        if toggle_user_status(username):
            flash('Статус пользователя изменен')
        else:
            flash('Ошибка при изменении статуса')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error toggling user: {str(e)}")
        flash('Ошибка при изменении статуса')
        return redirect(url_for('dashboard'))


@app.route('/download_cert/<username>/<platform>')
@login_required
def download_cert(username, platform):
    try:
        logger.info(f"Downloading certificate for {username}, platform: {platform}")

        # Проверяем существование пользователя
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM vpn_users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if not user:
            flash('Пользователь не найден')
            return redirect(url_for('dashboard'))

        # Определяем имя файла в зависимости от платформы
        if platform == 'pc':
            cert_name = f'{username}.p12'
        elif platform == 'ios':
            cert_name = f'{username}.mobileconfig'
        elif platform == 'android':
            cert_name = f'{username}.sswan'
        else:
            flash('Неверный тип платформы')
            return redirect(url_for('dashboard'))

        cert_path = os.path.join(CERT_DIR, cert_name)

        # Если сертификат не существует, создаем его
        if not os.path.exists(cert_path):
            # Здесь должна быть логика создания сертификата для конкретной платформы
            # Пока просто создаем пустой файл
            with open(cert_path, 'wb') as f:
                f.write(b'Test certificate content')

        return send_file(
            cert_path,
            as_attachment=True,
            download_name=cert_name
        )
    except Exception as e:
        logger.error(f"Error downloading certificate: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Ошибка при скачивании сертификата')
        return redirect(url_for('dashboard'))


@app.route('/update_display_name', methods=['POST'])
@login_required
def update_display_name():
    try:
        data = request.get_json()
        username = data.get('username')
        display_name = data.get('display_name')

        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE vpn_users SET display_name = ? WHERE username = ?',
                  (display_name, username))
        conn.commit()
        conn.close()

        logger.info(f"Updated display name for user {username}: {display_name}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating display name: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def format_date(date_str):
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return date.strftime('%d.%m.%Y %H:%M')
    except:
        return date_str


# Функция генерации пароля
def generate_password():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(8))


# Функция создания ссылки на сертификат
def create_cert_link(username, platform):
    link_id = secrets.token_urlsafe(16)
    password = generate_password()
    expires_at = datetime.now() + timedelta(days=7)  # Ссылка действительна 7 дней

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO cert_links (id, username, platform, password, expires_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (link_id, username, platform, password, expires_at))
    conn.commit()
    conn.close()

    return link_id, password


# Новый маршрут для генерации ссылки на сертификат
@app.route('/generate_cert_link/<username>/<platform>')
@login_required
def generate_cert_link(username, platform):
    try:
        link_id, password = create_cert_link(username, platform)
        link = url_for('download_cert_link', link_id=link_id, _external=True)
        return jsonify({
            'success': True,
            'link': link,
            'password': password
        })
    except Exception as e:
        logger.error(f"Error generating cert link: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


# Новый маршрут для скачивания сертификата по ссылке
@app.route('/cert/<link_id>', methods=['GET', 'POST'])
def download_cert_link(link_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT username, password, expires_at 
            FROM cert_links 
            WHERE id = ?
        ''', (link_id,))
        result = c.fetchone()
        conn.close()

        if not result:
            flash('Ссылка недействительна')
            return render_template('cert_download.html', valid=False)

        username, password, expires_at = result

        # Исправляем обработку даты
        try:
            # Пробуем сначала с миллисекундами
            expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                # Если не получилось, пробуем без миллисекунд
                expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.error(f"Invalid date format: {expires_at}")
                flash('Ошибка формата даты')
                return render_template('cert_download.html', valid=False)

        if expires_at < datetime.now():
            flash('Срок действия ссылки истек')
            return render_template('cert_download.html', valid=False)

        if request.method == 'POST':
            if 'password' in request.form:
                if request.form.get('password') == password:
                    session['cert_access_' + link_id] = True
                    return render_template('cert_download.html',
                                           valid=True,
                                           authenticated=True,
                                           username=username,
                                           link_id=link_id)
                else:
                    flash('Неверный пароль')
            elif 'platform' in request.form and session.get('cert_access_' + link_id):
                platform = request.form.get('platform')
                if platform in ['pc', 'ios', 'android']:
                    if platform == 'pc':
                        cert_name = f'{username}.p12'
                    elif platform == 'ios':
                        cert_name = f'{username}.mobileconfig'
                    elif platform == 'android':
                        cert_name = f'{username}.sswan'
                    else:
                        cert_name = ''

                    cert_path = os.path.join(CERT_DIR, cert_name)

                    if not os.path.exists(cert_path):
                        flash('Сертификат не найден')
                        return render_template('cert_download.html',
                                               valid=True,
                                               authenticated=True,
                                               username=username,
                                               link_id=link_id)

                    return send_file(
                        cert_path,
                        as_attachment=True,
                        download_name=cert_name
                    )
                else:
                    flash('Неверный тип платформы')

        return render_template('cert_download.html',
                               valid=True,
                               authenticated=session.get('cert_access_' + link_id, False))

    except Exception as e:
        logger.error(f"Error in download_cert_link: {str(e)}")
        logger.error(traceback.format_exc())
        flash('Произошла ошибка при скачивании сертификата')
        return render_template('cert_download.html', valid=False)


if __name__ == '__main__':
    # Инициализация базы данных
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
