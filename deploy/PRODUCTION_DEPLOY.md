# Production deployment

The production workflow deploys reviewed `main` commits without copying secrets into Git or deleting unknown server files.

## Production layout

- Project: `/www/wwwroot/football_system`
- Branch: `main`
- Application user: `admin`
- Deployment user: `root`
- Python environment: `/www/wwwroot/football_system/venv`
- Deployment log: `/var/log/football-deploy.log`
- Deployment lock: `/var/lock/football-deploy.lock`
- Frontend build marker: `frontend/dist/.build-commit`

Production secrets remain in untracked `config/*.env` files. The scripts never print those files, modify nginx, execute migrations, or delete database data.

## Required production files

The following untracked files must already exist:

- `config/database.env`
- `config/app.env`
- `config/caizhanyun.env`
- `config/hongrui.env`

Optional platform environment files may also be present. Their contents are not inspected.

The deployment scripts must be executable:

```bash
sudo chmod 0755 \
  /www/wwwroot/football_system/scripts/preflight_prod.sh \
  /www/wwwroot/football_system/scripts/deploy_prod.sh
```

The `admin` user must be able to fetch `origin/main` without an interactive password prompt.

## Preflight

Run checks without deploying:

```bash
sudo /www/wwwroot/football_system/scripts/preflight_prod.sh
```

Preflight requires root execution, the `admin` user, a clean `main` worktree, a fetchable `origin/main`, production environment files, Python, pip, Node.js, npm, and the installed football systemd units.

## Standard deployment

```bash
sudo /www/wwwroot/football_system/scripts/deploy_prod.sh
```

The script:

1. obtains an exclusive `flock` lock;
2. runs preflight;
3. fetches `origin/main` as `admin`;
4. records old and target commits;
5. blocks when the commit range changes a SQL migration;
6. reports every deployment phase before running it;
7. advances source only with `git merge --ff-only origin/main`;
8. installs requirements only when `requirements.txt` changed;
9. rebuilds frontend when frontend source changed or the build marker is missing/stale;
10. compiles Git-tracked Python files when Python source changed;
11. runs the complete offline unit test suite;
12. restarts only affected services and already-active timers;
13. performs bounded API health checks;
14. records the result without recording command output or secrets.

## Interrupted frontend deployment recovery

Every successful frontend build stores the latest frontend source commit in:

```text
frontend/dist/.build-commit
```

The marker is generated on the production server and is not committed. If deployment is interrupted after Git advances but before frontend build completion, the next normal deployment detects the missing or stale marker and rebuilds `frontend/dist` even when `HEAD` already equals `origin/main`.

To force validation and rebuilding of the current snapshot:

```bash
sudo /www/wwwroot/football_system/scripts/deploy_prod.sh --repair
```

Repair mode rebuilds frontend assets, compiles Python, runs all offline tests, restarts the API, and performs health checks. It does not modify production environment files or database data.

## Frontend build

Frontend builds run as `admin`:

```text
npm ci --no-audit --no-fund
npm run build
```

Running as `admin` prevents root-owned `frontend/dist` files. A failed build triggers automatic rollback after source deployment has started.

## Health verification

The script verifies:

- `football-api` is active;
- `http://127.0.0.1:8000/` responds successfully;
- `http://127.0.0.1:8000/api/portal/dashboard` responds successfully.

Each endpoint receives three visible attempts. Each attempt uses a three-second connection timeout and a twenty-second total request timeout, with two seconds between attempts. This prevents a slow dashboard query from creating a long silent wait.

## Migration guard

Any changed `database/migrations/*.sql` file blocks deployment before fast-forward:

```text
Database migration detected.
Review and execute migration manually before deployment.
```

Migration review, backup, execution, and recovery remain manual operations.

## systemd guard

Changes under `deploy/systemd/` produce a manual-review warning. The script does not copy units, run `daemon-reload`, enable units, or change timer enablement.

## Rollback

After source deployment begins, a failed dependency install, frontend build, Python compile, unit test, restart, or health check triggers rollback to the commit recorded before deployment.

Manual rollback uses an existing local commit:

```bash
sudo /www/wwwroot/football_system/scripts/deploy_prod.sh \
  --rollback <local-commit>
```

Rollback does not delete production environment files or database data. Database migration rollback is outside this script.

## Deployment log

`/var/log/football-deploy.log` is root-owned with mode `0640`. It records timestamps, old and new commits, changed file names, phase starts, tests, builds, and service status. It never records environment-file contents or platform credentials.
