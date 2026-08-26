#!/usr/bin/env bash

set -Eeuo pipefail


PROJECT_DIR="/www/wwwroot/football_system"
APP_USER="admin"
PREFLIGHT_SCRIPT="$PROJECT_DIR/scripts/preflight_prod.sh"
LOCK_FILE="/var/lock/football-deploy.lock"
LOG_FILE="/var/log/football-deploy.log"

OLD_COMMIT=""
NEW_COMMIT=""
DEPLOYMENT_ACTIVE=0

REQUIREMENTS_CHANGED=0
FRONTEND_CHANGED=0
PYTHON_CHANGED=0
API_CHANGED=0
SPIDER_CHANGED=0
SYSTEMD_CHANGED=0
SETTLEMENT_CHANGED=0
STATISTICS_CHANGED=0
AVATAR_CHANGED=0
DAILY_CHANGED=0
BACKUP_CHANGED=0
HONGRUI_SPIDER_CHANGED=0
HONGRUI_RESULTS_CHANGED=0

CHANGED_FILES=()


timestamp() {
    date '+%Y-%m-%dT%H:%M:%S%z'
}


log_event() {
    printf '%s %s\n' "$(timestamp)" "$1" >>"$LOG_FILE"
}


announce() {
    printf '%s\n' "$1"
}


run_as_admin() {
    runuser -u "$APP_USER" -- "$@"
}


admin_git() {
    run_as_admin git -C "$PROJECT_DIR" "$@"
}


reset_change_flags() {
    REQUIREMENTS_CHANGED=0
    FRONTEND_CHANGED=0
    PYTHON_CHANGED=0
    API_CHANGED=0
    SPIDER_CHANGED=0
    SYSTEMD_CHANGED=0
    SETTLEMENT_CHANGED=0
    STATISTICS_CHANGED=0
    AVATAR_CHANGED=0
    DAILY_CHANGED=0
    BACKUP_CHANGED=0
    HONGRUI_SPIDER_CHANGED=0
    HONGRUI_RESULTS_CHANGED=0
}


classify_changes() {
    local file_name

    reset_change_flags

    for file_name in "${CHANGED_FILES[@]}"; do
        case "$file_name" in
            requirements.txt)
                REQUIREMENTS_CHANGED=1
                PYTHON_CHANGED=1
                API_CHANGED=1
                SPIDER_CHANGED=1
                SETTLEMENT_CHANGED=1
                STATISTICS_CHANGED=1
                AVATAR_CHANGED=1
                DAILY_CHANGED=1
                BACKUP_CHANGED=1
                HONGRUI_SPIDER_CHANGED=1
                HONGRUI_RESULTS_CHANGED=1
                ;;
        esac

        case "$file_name" in
            frontend/*)
                FRONTEND_CHANGED=1
                ;;
        esac

        case "$file_name" in
            main.py|api/*.py|common/*.py|config/*.py|database/*.py|scheduler/*.py|scripts/*.py|spider/*.py|tests/*.py)
                PYTHON_CHANGED=1
                ;;
        esac

        case "$file_name" in
            main.py|api/*.py|common/*.py|config/*.py|database/*.py)
                API_CHANGED=1
                ;;
        esac

        case "$file_name" in
            spider/*.py|common/*.py|config/*.py|database/*.py)
                SPIDER_CHANGED=1
                ;;
        esac

        case "$file_name" in
            deploy/systemd/*)
                SYSTEMD_CHANGED=1
                ;;
        esac

        case "$file_name" in
            spider/auto_settlement.py|common/*.py|config/*.py|database/*.py)
                SETTLEMENT_CHANGED=1
                ;;
        esac

        case "$file_name" in
            spider/update_statistics.py|common/*.py|config/*.py|database/*.py)
                STATISTICS_CHANGED=1
                ;;
        esac

        case "$file_name" in
            spider/sync_avatars.py|common/*.py|config/*.py|database/*.py)
                AVATAR_CHANGED=1
                ;;
        esac

        case "$file_name" in
            scheduler/*.py|common/*.py|config/*.py|database/*.py)
                DAILY_CHANGED=1
                ;;
        esac

        case "$file_name" in
            scripts/backup_db.py|common/*.py|config/*.py|database/*.py)
                BACKUP_CHANGED=1
                ;;
        esac

        case "$file_name" in
            spider/hongrui.py|common/*.py|config/*.py|database/*.py)
                HONGRUI_SPIDER_CHANGED=1
                ;;
        esac

        case "$file_name" in
            spider/hongrui_results.py|common/*.py|config/*.py|database/*.py)
                HONGRUI_RESULTS_CHANGED=1
                ;;
        esac
    done
}


load_changed_files() {
    local from_commit="$1"
    local to_commit="$2"

    CHANGED_FILES=()
    mapfile -d '' CHANGED_FILES < <(
        admin_git diff --name-only -z "$from_commit" "$to_commit"
    )
    classify_changes
}


log_changed_files() {
    local file_name

    for file_name in "${CHANGED_FILES[@]}"; do
        log_event "changed_file=$file_name"
    done
}


migration_detected() {
    local file_name

    for file_name in "${CHANGED_FILES[@]}"; do
        case "$file_name" in
            database/migrations/*.sql)
                return 0
                ;;
        esac
    done

    return 1
}


restart_if_active() {
    local unit_name="$1"

    if systemctl is-active --quiet "$unit_name"; then
        if systemctl restart "$unit_name"; then
            log_event "service=$unit_name status=restarted"
        else
            log_event "service=$unit_name status=FAIL"
            return 1
        fi
    else
        log_event "service=$unit_name status=inactive_unchanged"
    fi
}


restart_related_timers() {
    if [[ "$SPIDER_CHANGED" -eq 1 ]]; then
        restart_if_active "football-pipeline.timer"
    fi

    if [[ "$SETTLEMENT_CHANGED" -eq 1 ]]; then
        restart_if_active "football-settlement.timer"
    fi

    if [[ "$STATISTICS_CHANGED" -eq 1 ]]; then
        restart_if_active "football-statistics.timer"
    fi

    if [[ "$AVATAR_CHANGED" -eq 1 ]]; then
        restart_if_active "football-avatar-sync.timer"
    fi

    if [[ "$DAILY_CHANGED" -eq 1 ]]; then
        restart_if_active "football-daily.timer"
    fi

    if [[ "$BACKUP_CHANGED" -eq 1 ]]; then
        restart_if_active "football-backup.timer"
    fi

    if [[ "$HONGRUI_SPIDER_CHANGED" -eq 1 ]]; then
        restart_if_active "hongrui-spider.timer"
    fi

    if [[ "$HONGRUI_RESULTS_CHANGED" -eq 1 ]]; then
        restart_if_active "hongrui-results.timer"
    fi
}


build_frontend() {
    run_as_admin bash -lc \
        "cd '$PROJECT_DIR/frontend' && npm ci && npm run build"
}


install_python_requirements() {
    run_as_admin "$PROJECT_DIR/venv/bin/pip" install \
        -r "$PROJECT_DIR/requirements.txt"
}


compile_python() {
    run_as_admin env PYTHONPATH="$PROJECT_DIR" \
        "$PROJECT_DIR/venv/bin/python" -m compileall -q \
        "$PROJECT_DIR/main.py" \
        "$PROJECT_DIR/api" \
        "$PROJECT_DIR/common" \
        "$PROJECT_DIR/config" \
        "$PROJECT_DIR/database" \
        "$PROJECT_DIR/scheduler" \
        "$PROJECT_DIR/scripts" \
        "$PROJECT_DIR/spider" \
        "$PROJECT_DIR/tests"
}


run_tests() {
    run_as_admin env PYTHONPATH="$PROJECT_DIR" \
        "$PROJECT_DIR/venv/bin/python" -m unittest \
        discover -s "$PROJECT_DIR/tests" -v
}


verify_api() {
    if systemctl is-active --quiet football-api; then
        log_event "service=football-api status=active"
    else
        log_event "service=football-api status=FAIL"
        return 1
    fi

    if curl --fail --silent --show-error --max-time 15 \
        "http://127.0.0.1:8000/" >/dev/null; then
        log_event "service=football-api root_health=PASS"
    else
        log_event "service=football-api root_health=FAIL"
        return 1
    fi

    if curl --fail --silent --show-error --max-time 20 \
        "http://127.0.0.1:8000/api/portal/dashboard" >/dev/null; then
        log_event "service=football-api dashboard_health=PASS"
    else
        log_event "service=football-api dashboard_health=FAIL"
        return 1
    fi
}


rollback_to_commit() {
    local target_commit="$1"
    local rollback_reason="$2"
    local current_commit
    local rollback_failed=0

    set +e

    if ! admin_git cat-file -e "${target_commit}^{commit}" 2>/dev/null; then
        printf 'Rollback target is not a local Git commit.\n' >&2
        set -e
        return 1
    fi

    if [[ -n "$(admin_git status --porcelain --untracked-files=normal)" ]]; then
        printf 'Rollback stopped because the Git working tree is not clean.\n' >&2
        set -e
        return 1
    fi

    current_commit="$(admin_git rev-parse HEAD)"
    load_changed_files "$target_commit" "$current_commit"

    announce "Rollback started: reason=$rollback_reason target=$target_commit"

    systemctl stop football-api || rollback_failed=1

    admin_git switch --detach "$target_commit" || rollback_failed=1
    admin_git branch -f main "$target_commit" || rollback_failed=1
    admin_git switch main || rollback_failed=1

    if [[ "$REQUIREMENTS_CHANGED" -eq 1 ]]; then
        install_python_requirements || rollback_failed=1
        log_event "build=rollback_requirements status=$(
            [[ "$rollback_failed" -eq 0 ]] && printf 'PASS' || printf 'FAIL'
        )"
    fi

    if [[ "$FRONTEND_CHANGED" -eq 1 ]]; then
        build_frontend || rollback_failed=1
        log_event "build=rollback_frontend status=$(
            [[ "$rollback_failed" -eq 0 ]] && printf 'PASS' || printf 'FAIL'
        )"
    fi

    if [[ "$PYTHON_CHANGED" -eq 1 ]]; then
        compile_python || rollback_failed=1
    fi

    systemctl restart football-api || rollback_failed=1
    restart_related_timers || rollback_failed=1
    systemctl is-active --quiet football-api || rollback_failed=1

    if [[ "$rollback_failed" -ne 0 ]]; then
        printf 'Rollback completed with errors; inspect services manually.\n' >&2
        log_event "rollback old=$current_commit new=$target_commit status=FAIL"
        set -e
        return 1
    fi

    log_event "rollback old=$current_commit new=$target_commit status=PASS"
    printf 'Rollback complete: %s\n' "$target_commit"
    set -e
    return 0
}


handle_deploy_error() {
    local exit_code="$1"
    local line_number="$2"

    trap - ERR
    log_event "deployment old=$OLD_COMMIT new=$NEW_COMMIT status=FAIL"

    if [[ "$DEPLOYMENT_ACTIVE" -eq 1 && -n "$OLD_COMMIT" ]]; then
        printf 'Deployment failed. Rolling back to %s.\n' "$OLD_COMMIT" >&2
        rollback_to_commit "$OLD_COMMIT" "automatic_failure" || true
    fi

    exit "$exit_code"
}


usage() {
    printf 'Usage: %s [--rollback <local-commit>]\n' "$0"
}


if [[ "${EUID}" -ne 0 ]]; then
    printf 'This deployment script must run as root.\n' >&2
    exit 1
fi

touch "$LOG_FILE"
chown root:root "$LOG_FILE"
chmod 0640 "$LOG_FILE"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    printf 'Another football deployment is already running.\n' >&2
    exit 1
fi

if [[ ! -f "$PREFLIGHT_SCRIPT" ]]; then
    printf 'Preflight script is missing.\n' >&2
    exit 1
fi

if ! bash "$PREFLIGHT_SCRIPT"; then
    exit 1
fi

cd "$PROJECT_DIR"

if [[ "${1:-}" == "--rollback" ]]; then
    if [[ "$#" -ne 2 ]]; then
        usage
        exit 2
    fi

    rollback_to_commit "$2" "manual_request"
    exit $?
fi

if [[ "$#" -ne 0 ]]; then
    usage
    exit 2
fi

admin_git fetch origin

OLD_COMMIT="$(admin_git rev-parse HEAD)"
NEW_COMMIT="$(admin_git rev-parse origin/main)"

log_event "deployment old=$OLD_COMMIT new=$NEW_COMMIT status=START"

if [[ "$OLD_COMMIT" == "$NEW_COMMIT" ]]; then
    announce "already up to date"
    exit 0
fi

load_changed_files "$OLD_COMMIT" "$NEW_COMMIT"
log_changed_files

if migration_detected; then
    printf 'Database migration detected.\n' >&2
    printf 'Review and execute migration manually before deployment.\n' >&2
    log_event "deployment old=$OLD_COMMIT new=$NEW_COMMIT status=BLOCKED"
    exit 3
fi

if [[ "$SYSTEMD_CHANGED" -eq 1 ]]; then
    printf 'systemd templates changed; review deploy/systemd manually.\n' >&2
fi

trap 'handle_deploy_error "$?" "$LINENO"' ERR
DEPLOYMENT_ACTIVE=1

admin_git merge --ff-only origin/main

if [[ "$REQUIREMENTS_CHANGED" -eq 1 ]]; then
    if install_python_requirements; then
        log_event "build=requirements status=PASS"
    else
        log_event "build=requirements status=FAIL"
        false
    fi
else
    log_event "build=requirements status=SKIP"
fi

if [[ "$FRONTEND_CHANGED" -eq 1 ]]; then
    if build_frontend; then
        log_event "build=frontend status=PASS"
    else
        log_event "build=frontend status=FAIL"
        false
    fi
else
    log_event "build=frontend status=SKIP"
fi

if [[ "$PYTHON_CHANGED" -eq 1 ]]; then
    if compile_python; then
        log_event "build=python_compile status=PASS"
    else
        log_event "build=python_compile status=FAIL"
        false
    fi
else
    log_event "build=python_compile status=SKIP"
fi

if run_tests; then
    log_event "tests status=PASS"
else
    log_event "tests status=FAIL"
    false
fi

if [[ "$API_CHANGED" -eq 1 || "$REQUIREMENTS_CHANGED" -eq 1 ]]; then
    if systemctl restart football-api; then
        log_event "service=football-api status=restarted"
    else
        log_event "service=football-api status=FAIL"
        false
    fi
fi

restart_related_timers
verify_api

DEPLOYMENT_ACTIVE=0
trap - ERR

log_event "deployment old=$OLD_COMMIT new=$NEW_COMMIT status=PASS"
printf 'Deployment complete: %s -> %s\n' "$OLD_COMMIT" "$NEW_COMMIT"
