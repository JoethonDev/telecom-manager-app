# Telecom Manager App

Flask web panel for managing SSH TLS, VMess TCP TLS, and VLESS TCP TLS Vision users.

## Local Dev

```bash
export TELECOM_DEV=1
export TELECOMCTL_MODE=mock
export MANAGER_DB=./var/dev/manager.db

python manage.py migrate
python manage.py create-admin
python manage.py runserver
```

## Production

Deployed by telecom-vps-installer. Runs as `telecom-web` user via Gunicorn.
All privileged operations go through `sudo /usr/local/sbin/telecomctl`.
