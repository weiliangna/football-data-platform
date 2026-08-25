# Football Data Platform deployment

This directory contains secret-free deployment templates for the current production task chain. The commands below assume the repository is deployed to `/www/wwwroot/football_system` and systemd runs the application as `admin`.

The production runtime versions used to lock this deployment are:

- Python 3.10.12
- Node.js v20.20.2
- npm 10.8.2

## 1. Create the Python virtual environment

```bash
cd /www/wwwroot/football_system
python3.10 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
```

Verify the interpreter before installing dependencies:

```bash
./venv/bin/python --version
```

## 2. Create local environment files

Copy the tracked examples to their untracked production paths:

```bash
cd /www/wwwroot/football_system
cp config/database.env.example config/database.env
cp config/app.env.example config/app.env
cp config/caizhanyun.env.example config/caizhanyun.env
cp config/hongrui.env.example config/hongrui.env
chmod 600 config/database.env config/app.env config/caizhanyun.env config/hongrui.env
```

Edit the copied files on the server and supply the real values there. Never place real passwords, tokens, or cookies in tracked files or systemd unit files.

`database/mysql.py` recognizes `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `DB_CHARSET`. Values supplied by the system environment take precedence over `config/database.env`.

`config/app.env` supplies `FOOTBALL_ADMIN_TOKEN`. `config/caizhanyun.env` supplies `CAIZHANYUN_TOKEN` and `CAIZHANYUN_COOKIE`. `config/hongrui.env` supplies `HONGRUI_TOKEN`.

## 3. Prepare the backup directory

The backup task writes to `/www/backups/football`, so create it with permissions for the systemd user:

```bash
sudo install -d -o admin -g admin -m 0700 /www/backups/football
```

The repository version of `scripts/backup_db.py` supports the DictCursor returned by `database.mysql.get_conn()`. Because no production database test is performed during repository preparation, validate the backup in an authorized environment before relying on its timer.

## 4. Install the systemd templates

```bash
cd /www/wwwroot/football_system
sudo install -m 0644 deploy/systemd/*.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

Enable the timers:

```bash
sudo systemctl enable --now football-pipeline.timer
sudo systemctl enable --now hongrui-spider.timer
sudo systemctl enable --now hongrui-results.timer
sudo systemctl enable --now football-settlement.timer
sudo systemctl enable --now football-statistics.timer
sudo systemctl enable --now football-avatar-sync.timer
sudo systemctl enable --now football-daily.timer
sudo systemctl enable --now football-backup.timer
```

The production-aligned schedules are:

- `football-pipeline.timer`: every minute.
- `hongrui-spider.timer`: 30 seconds after boot, then every 60 seconds.
- `hongrui-results.timer`: 40 seconds after boot, then every 60 seconds.
- `football-settlement.timer`: 50 seconds after boot, then every 60 seconds.
- `football-statistics.timer`: 70 seconds after boot, then every 300 seconds.
- `football-avatar-sync.timer`: 90 seconds after boot, then every 1800 seconds.
- `football-daily.timer`: every day at 00:05.
- `football-backup.timer`: every day at 03:30.

## 5. Start or restart the API

```bash
sudo systemctl enable football-api.service
sudo systemctl restart football-api.service
sudo systemctl status football-api.service
```

The API template listens on `127.0.0.1:8000`; nginx remains responsible for the public reverse proxy.

## 6. Build the frontend

Verify the production-aligned tool versions, then install and build:

```bash
node --version
npm --version
cd /www/wwwroot/football_system/frontend
npm install
npm run build
```

The generated frontend is written to `frontend/dist`, which is intentionally ignored by Git.

## 7. Database prerequisite

These deployment steps do not create or migrate the database. Use the reviewed DDL snapshot in `database/schema/football_data_schema.sql` only for authorized reconstruction workflows. See `database/schema/README.md` for the comparison with repository migrations.
