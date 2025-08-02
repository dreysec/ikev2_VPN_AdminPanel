#!/bin/bash

# === Настройки ===
SERVICE_NAME="vpn_admin"
WORKDIR="$(pwd)"
PYTHON_BIN="python3"
APP_FILE="app.py"
REQUIREMENTS="requirements.txt"
USER_NAME="$(whoami)"

# === Автоматическая установка Python, pip и venv ===
install_python_tools() {
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
}

if ! command -v $PYTHON_BIN &> /dev/null; then
    install_python_tools
fi

if ! command -v pip3 &> /dev/null; then
    install_python_tools
fi

if ! $PYTHON_BIN -m venv --help &> /dev/null; then
    install_python_tools
fi

# === Удаление неудачного venv, если есть ===
if [ -d "$WORKDIR/venv" ]; then
    if [ ! -f "$WORKDIR/venv/bin/activate" ]; then
        rm -rf "$WORKDIR/venv"
    fi
fi

# === Создание виртуального окружения, если нет ===
if [ ! -d "$WORKDIR/venv" ]; then
    $PYTHON_BIN -m venv venv
    if [ $? -ne 0 ]; then
        install_python_tools
        $PYTHON_BIN -m venv venv
        if [ $? -ne 0 ]; then
            exit 1
        fi
    fi
fi

# === Установка зависимостей ===
source venv/bin/activate
pip install --upgrade pip
pip install -r $REQUIREMENTS
if [ $? -ne 0 ]; then
    install_python_tools
    pip install --upgrade pip
    pip install -r $REQUIREMENTS
    if [ $? -ne 0 ]; then
        deactivate
        exit 1
    fi
fi
deactivate

# === Создание systemd unit-файла ===
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=VPN Admin Flask Service
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$WORKDIR
ExecStart=$WORKDIR/venv/bin/python $WORKDIR/$APP_FILE
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# === Перезагрузка systemd, включение и запуск сервиса ===
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

# === Проверка статуса ===
sudo systemctl status $SERVICE_NAME --no-pager

echo "Готово! Приложение запущено как systemd-сервис."