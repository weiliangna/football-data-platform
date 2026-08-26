# Football Data Platform deployment

This directory contains secret-free deployment templates. The commands assume the repository is deployed to `/www/wwwroot/football_system` and systemd runs the application as `admin`.

Verified production tool versions:

- Python 3.10.12
- Node.js v20.20.2
- npm 10.8.2

## 1. Create the Python virtual environment

```bash
cd /www/wwwroot/football_system
python3.10 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python --version
```

## 2. Create local environment files

Copy the tracked examples to untracked production paths:

```bash
cd /www/wwwroot/football_system
cp config/database.env.example config/database.env
cp config/app.env.example config/app.env
cp config/caizhanyun.env.example config/caizhanyun.env
cp config/hongrui.env.example config/hongrui.env
cp config/zhouyunbao.env.example config/zhouyunbao.env
cp config/yuncai.env.example config/yuncai.env
cp config/haodianzhu.env.example config/haodianzhu.env
cp config/qishilu.env.example config/qishilu.env
chmod 600 config/*.env
```

Supply real values only on the server. Never place passwords, tokens, cookies, authorization values, session IDs, UUIDs, or signing keys in tracked files or systemd units.

The platform files use these variables:

- `config/caizhanyun.env`: `CAIZHANYUN_TOKEN`, `CAIZHANYUN_COOKIE`.
- `config/hongrui.env`: `HONGRUI_TOKEN`.
- `config/zhouyunbao.env`: `ZHOUYUNBAO_TOKEN`; store and bootstrap user overrides are optional.
- `config/haodianzhu.env`: `HAODIANZHU_SID`, `HAODIANZHU_UUID`, `HAODIANZHU_COOKIE`; shop ID override is optional.
- `config/qishilu.env`: `QISHILU_AUTHORIZATION`.
- `config/yuncai.env`: reserved for the verified authorization fields. Live sampling remains blocked until the dynamic query/body signing algorithm is available.

## 3. Unified platform scheduling

All platform ingestion is launched by one timer:

```text
football-pipeline.timer
→ football-pipeline.service
→ spider/pipeline.py
→ 彩站云 / 州运宝 / 鸿瑞 / 云彩 / 好店主 / 启示录
```

The six platform tasks run concurrently. Each platform records its own status, so one failure does not suppress the other five records. Order details, available match results, and response avatars are processed in the same platform cycle.

The pipeline transactionally inserts missing `platform_config` rows. Existing IDs and enable flags are preserved. On the current four-platform production schema, the automatic continuation assigns 好店主 ID 5 and 启示录 ID 6.

Do not run the historical independent Hongrui and avatar timers together with the unified pipeline. Before enabling the new pipeline, disable them:

```bash
sudo systemctl disable --now hongrui-spider.timer
sudo systemctl disable --now hongrui-results.timer
sudo systemctl disable --now football-avatar-sync.timer
```

The old unit templates remain only for production rollback compatibility and must not be enabled in unified mode.

## 4. Install and enable systemd units

```bash
cd /www/wwwroot/football_system
sudo install -m 0644 deploy/systemd/*.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now football-pipeline.timer
sudo systemctl enable --now football-settlement.timer
sudo systemctl enable --now football-statistics.timer
sudo systemctl enable --now football-daily.timer
sudo systemctl enable --now football-backup.timer
```

Current active schedules:

- `football-pipeline.timer`: 30 seconds after the previous pipeline run becomes inactive.
- `football-statistics.timer`: every 30 seconds.
- `football-settlement.timer`: every 60 seconds.
- `football-daily.timer`: every day at 00:05.
- `football-backup.timer`: every day at 03:30.

## 5. Prepare the backup directory

```bash
sudo install -d -o admin -g admin -m 0700 /www/backups/football
```

Validate backups in an authorized environment before relying on the timer. Repository preparation does not connect to production MySQL.

## 6. Start or restart the API

```bash
sudo systemctl enable football-api.service
sudo systemctl restart football-api.service
sudo systemctl status football-api.service
```

The API listens on `127.0.0.1:8000`; nginx remains responsible for the public reverse proxy.

## 7. Build the frontend

```bash
node --version
npm --version
cd /www/wwwroot/football_system/frontend
npm install
npm run build
```

The generated `frontend/dist` directory is intentionally ignored by Git.

## 8. Database prerequisite

These deployment steps do not create or migrate the database. The reviewed DDL snapshot is `database/schema/football_data_schema.sql`. See `database/schema/README.md` for migration coverage and known differences.
