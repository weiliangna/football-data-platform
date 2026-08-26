# Production deployment

This project uses a guarded production deployment workflow. Production secrets remain in untracked `config/*.env` files and are never copied into Git, deployment output, or deployment logs.

## Production layout

- Project directory: `/www/wwwroot/football_system`
- Git deployment branch: `main`
- Application user: `admin`
- Deployment command user: `root`
- Python environment: `/www/wwwroot/football_system/venv`
- Deployment log: `/var/log/football-deploy.log`
- Deployment lock: `/var/lock/football-deploy.lock`

The deployment scripts do not modify nginx, database rows, database schema, or production environment files.

## Initial preparation

The repository must already be cloned at the production path and checked out on `main`. The following production-only files must exist:

- `config/database.env`
- `config/app.env`
- `config/caizhanyun.env`
- `config/hongrui.env`

Optional platform environment files may also be present for enabled integrations. Their contents are not inspected or printed by the deployment scripts.

Before the first deployment, ensure both scripts are executable:

```bash
sudo chmod 0755 \
  /www/wwwroot/football_system/scripts/preflight_prod.sh \
  /www/wwwroot/football_system/scripts/deploy_prod.sh
```

The Git remote must allow the `admin` user to fetch `origin/main` without an interactive password prompt.

## Preflight only

Run the production checks without deploying:

```bash
sudo /www/wwwroot/football_system/scripts/preflight_prod.sh
```

The preflight requires:

- execution as `root`;
- the `admin` application user;
- the exact project directory and Git metadata;
- current branch `main`;
- a clean tracked and untracked Git working tree;
- a valid and fetchable `origin/main`;
- all required production environment files;
- executable project Python and pip;
- Node.js and npm available to `admin`;
- the API service and known football/Hongrui timers installed in systemd;
- deployment commands such as Git, `flock`, `systemctl`, and `curl`.

Every check prints `PASS` or `FAIL`. A critical failure returns a non-zero exit code.

## Standard deployment

After a feature branch is reviewed, merged into `main`, and pushed to GitHub, production deployment is one command:

```bash
sudo /www/wwwroot/football_system/scripts/deploy_prod.sh
```

The script:

1. obtains an exclusive deployment lock;
2. runs the complete preflight;
3. fetches `origin/main` as `admin`;
4. records the current and target commits;
5. exits successfully when both commits are identical;
6. blocks when the commit range changes a SQL migration;
7. classifies requirements, frontend, Python, API, Spider, scheduler, backup, and systemd changes;
8. advances `main` only with a Git fast-forward merge;
9. installs Python requirements only when `requirements.txt` changed;
10. installs locked frontend dependencies and builds production assets only when `frontend/` changed;
11. compiles Python only when relevant Python files changed;
12. runs the complete offline unit test suite;
13. restarts the API only for API, backend, or dependency changes;
14. restarts only already-active timers related to changed Spider or scheduled modules;
15. verifies the API service and both local HTTP health endpoints.

The script never enables or disables a timer. Historical Hongrui or avatar timers that are inactive remain inactive.

## Migration guard

Any changed file under `database/migrations/` blocks automatic deployment before the Git fast-forward occurs. The operator sees:

```text
Database migration detected.
Review and execute migration manually before deployment.
```

Review, backup, authorization, execution, and validation of a migration are separate manual production operations. A migration is never run or rolled back by these scripts.

## systemd template guard

Changes under `deploy/systemd/` produce a manual-review warning. The deployment script does not copy unit files, reload the systemd manager, or change unit enablement. An operator must compare and approve unit changes separately.

## Automatic rollback

After the fast-forward, a failed dependency install, frontend build, Python compile, unit test, service restart, or health check triggers rollback to the commit recorded before deployment.

Rollback:

- validates that the target is an existing local Git commit;
- requires a clean Git working tree;
- stops the API;
- switches the local `main` branch to the target commit;
- reinstalls that commit's requirements when required;
- rebuilds that commit's frontend when required;
- compiles changed Python sources;
- restarts the API and only related timers that were already active.

Production environment files and database contents are outside the rollback scope and remain untouched.

## Manual rollback

Use the full local commit identifier:

```bash
sudo /www/wwwroot/football_system/scripts/deploy_prod.sh \
  --rollback <local-commit>
```

The target must already exist in the production repository. Database schema changes require their own reviewed recovery plan and are not part of code rollback.

## Change triggers

### Frontend

Any changed path under `frontend/` runs:

```text
npm ci
npm run build
```

Both commands run as `admin`, preventing root-owned production assets.

### Python and API

Changes to Python application paths run `compileall`. API-facing or shared backend changes restart `football-api` after tests pass. A `requirements.txt` change installs the pinned requirements and also restarts the API.

### Spider and scheduled jobs

Spider and shared data-layer changes refresh the unified pipeline timer when it is already active. Settlement, statistics, avatar, daily, backup, and historical Hongrui timers are restarted only when their related modules changed and the timer was already active.

## Health verification

The deployment succeeds only when all checks pass:

- `football-api` is active;
- `http://127.0.0.1:8000/` returns a successful response;
- `http://127.0.0.1:8000/api/portal/dashboard` returns a successful response.

## Deployment log

`/var/log/football-deploy.log` is root-owned and mode `0640`. It records timestamps, old and new commit identifiers, changed file names, build/test outcomes, and service or health status. Command output and environment-file contents are not copied into this log.
