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

## HTTPS

По умолчанию панель отвечает по обычному HTTP. Если открыть её по `https://`, браузер
скажет, что защищённое соединение не поддерживается. Есть два способа включить HTTPS.

Настройки задаются переменными окружения; для systemd-сервиса их удобно держать в файле
`/etc/vpn_admin.env` (скрипт установки его создаёт и подключает к сервису).

### Вариант 1. HTTPS прямо в панели (Let's Encrypt)

В `/etc/vpn_admin.env` (подставьте свой домен и порт):

```
VPN_ADMIN_PORT=53523
VPN_ADMIN_SSL_CERT=/etc/letsencrypt/live/example.com/fullchain.pem
VPN_ADMIN_SSL_KEY=/etc/letsencrypt/live/example.com/privkey.pem
```

```sh
sudo systemctl restart vpn_admin
```

Панель откроется по `https://example.com:53523`. Если файлы сертификата не найдены, сервис
не запустится, причина будет в `journalctl -u vpn_admin`. Сервис должен работать от
пользователя, который может читать ключ (по умолчанию установщик запускает его от того, кто его
вызвал, обычно root).

Сертификат подгружается при старте, поэтому после продления Let's Encrypt панель нужно
перезапускать. Для этого добавьте хук:

```sh
printf '#!/bin/sh\nsystemctl restart vpn_admin\n' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/restart-vpn-admin.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-vpn-admin.sh
```

### Вариант 2. За nginx

HTTPS терминирует nginx, панель слушает только localhost. В `/etc/vpn_admin.env`:

```
VPN_ADMIN_HOST=127.0.0.1
VPN_ADMIN_PORT=53523
VPN_ADMIN_BEHIND_PROXY=1
```

Без `VPN_ADMIN_BEHIND_PROXY=1` ссылки на скачивание сертификатов будут строиться с `http://`.
В nginx должны передаваться заголовки `X-Forwarded-Proto`, `X-Forwarded-For` и `Host`.

Используйте один из вариантов: два листенера на одном порту работать не будут.

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
