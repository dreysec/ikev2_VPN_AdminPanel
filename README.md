# VPN Admin Panel

Веб-панель для управления пользователями VPN, генерации сертификатов и администрирования через веб интерфейс.

## Возможности

- Авторизация администратора
- Добавление, удаление пользователей
- Генерация и скачивание сертификатов для разных платформ
- Поиск и фильтрация пользователей

## Технологии

- Python 3.7+
- Flask 2.x
- Werkzeug
- SQLite (встроенная база данных)
- Bootstrap 5 (интерфейс)

## Установка

### 1. Клонируйте репозиторий

```sh
git clone https://github.com/dreysec/ikev2_VPN_AdminPanel.git
cd ikev2_VPN_AdminPanel
```

### 2. Создайте и активируйте виртуальное окружение (рекомендуется)

```sh
python -m venv venv
# Для Windows:
venv\Scripts\activate
# Для Linux/Mac:
source venv/bin/activate
```

### 3. Установите зависимости

```sh
pip install -r requirements.txt
```

### 4. (Опционально) Настройте параметры администратора

По умолчанию логин: `admin`, пароль: `admin`
Изменить можно в файле `app.py` в словаре `ADMIN_CONFIG`.

### 5. Инициализируйте базу данных

База данных создается автоматически при первом запуске.
Если нужно вручную — выполните:

```sh
python
>>> from app import init_db
>>> init_db()
>>> exit()
```

### 6. Запустите приложение

```sh
python app.py
```

По умолчанию приложение будет доступно по адресу:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Развертывание как сервиса (Linux)

В проекте есть скрипт для установки как systemd-сервиса:

```sh
sudo bash install_vpn_admin_service.sh
```

После этого сервис можно запускать/останавливать командами:

```sh
sudo systemctl start vpn_admin
sudo systemctl stop vpn_admin
sudo systemctl status vpn_admin
```

---

## Структура проекта

```
vpn_admin/
├── app.py                  # Основной файл приложения Flask
├── requirements.txt        # Зависимости Python
├── vpn_users.db            # База данных пользователей (создается автоматически)
├── certificates/           # Папка для сертификатов
├── logs/                   # Логи приложения
├── templates/              # HTML-шаблоны интерфейса
└── install_vpn_admin_service.sh # Скрипт для установки сервиса
```

---

## Контакты

Если возникли вопросы или предложения — создайте issue или напишите мне!"# ikev2_VPN_AdminPanel" 
