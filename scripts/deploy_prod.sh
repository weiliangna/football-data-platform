#!/usr/bin/env bash

set -Eeuo pipefail


PROJECT_DIR="/www/wwwroot/football_system"
APP_USER="admin"
PREFLIGHT_SCRIPT="$PROJECT_DIR/scripts/preflight_prod.sh"
LOCK_FILE="/var/lock/football-deploy.lock"
LOG_FILE="/var/log/football-deploy.log"
FRONTEND_BUILD_MARKER="$PROJECT_DIR/frontend/dist/.build-commit"

OLD_COMMIT=""
NEW_COMMIT=""
DEPLOYMENT_ACTIVE=0
FORCE_REPAIR=0

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


announce_step() {
    announce ""
    announce "===== $1 ====="
    log_event "step=$1 status=START"
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


frontend_source_commit() {
    local target_commit="$1"

    admin_git log -1 --format=%H "$target_commit" -- frontend
}


frontend_build_is_current() {
    local target_commit="$1"
    local expected_commit
    local built_commit

    expected_commit="$(frontend_source_commit "$target_commit")"

    if [[ -z "$expected_commit" || ! -s "$FRONTEND_BUILD_MARKER" ]]; then
        return 1
    fi

    built_commit="$(tr -d '[:space:]' <"$FRONTEND_BUILD_MARKER")"
    [[ "$built_commit" == "$expected_commit" ]]
}


mark_frontend_build() {
    local source_commit

    source_commit="$(frontend_source_commit HEAD)"
    printf '%s\n' "$source_commit" | run_as_admin tee \
        "$FRONTEND_BUILD_MARKER" >/dev/null
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
    announce "Installing locked frontend dependencies."
    run_as_admin bash -lc \
        "cd '$PROJECT_DIR/frontend' && npm ci --no-audit --no-fund"

    announce "Building frontend production assets."
    run_as_admin bash -lc \
        "cd '$PROJECT_DIR/frontend' && npm run build"

    mark_frontend_build
}


install_python_requirements() {
    run_as_admin "$PROJECT_DIR/venv/bin/pip" install \
        -r "$PROJECT_DIR/requirements.txt"
}


compile_python() {
    local tracked_file
    local tracked_files=()
    local python_files=()

    mapfile -d '' tracked_files < <(
        admin_git ls-files -z -- '*.py'
    )

    for tracked_file in "${tracked_files[@]}"; do
        if [[ -f "$PROJECT_DIR/$tracked_file" ]]; then
            python_files+=("$PROJECT_DIR/$tracked_file")
        fi
    done

    if [[ "${#python_files[@]}" -eq 0 ]]; then
        announce "No Git-tracked Python files found; skipping compile check."
        return 0
    fi

    announce "Compiling ${#python_files[@]} Git-tracked Python files."
    run_as_admin env PYTHONPATH="$PROJECT_DIR" \
        "$PROJECT_DIR/venv/bin/python" -m py_compile \
        "${python_files[@]}"
}


run_tests() {
    run_as_admin env PYTHONPATH="$PROJECT_DIR" \
        "$PROJECT_DIR/venv/bin/python" -m unittest \
        discover -s "$PROJECT_DIR/tests" -v
}


wait_for_http() {
    local url="$1"
    local attempts="${2:-3}"
    local attempt

    for ((attempt = 1; attempt <= attempts; attempt += 1)); do
        announce "Health check $attempt/$attempts: $url"

        if curl --fail --silent --show-error \
            --connect-timeout 3 --max-time 20 \
            "$url" >/dev/null; then
            return 0
        fi

        if [[ "$attempt" -lt "$attempts" ]]; then
            sleep 2
        fi
    done

    return 1
}


verify_api() {
    if systemctl is-active --quiet football-api; then
        log_event "service=football-api status=active"
    else
        log_event "service=football-api status=FAIL"
        return 1
    fi

    if wait_for_http "http://127.0.0.1:8000/" 3; then
        log_event "service=football-api root_health=PASS"
    else
        announce "football-api root endpoint failed three health checks."
        log_event "service=football-api root_health=FAIL"
        return 1
    fi

    if wait_for_http \
        "http://127.0.0.1:8000/api/portal/dashboard" 3; then
        log_event "service=football-api dashboard_health=PASS"
    else
        announce "football-api dashboard failed three health checks."
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
    log_event "deployment old=$OLD_COMMIT new=$NEW_COMMIT status=FAIL line=$line_number"

    if [[ "$DEPLOYMENT_ACTIVE" -eq 1 && -n "$OLD_COMMIT" ]]; then
        printf 'Deployment failed. Rolling back to %s.\n' "$OLD_COMMIT" >&2
        rollback_to_commit "$OLD_COMMIT" "automatic_failure" || true
    fi

    exit "$exit_code"
}


usage() {
    printf 'Usage: %s [--repair | --rollback <local-commit>]\n' "$0"
}


if [[ "${EUID}" -ne 0 ]]; then
    printf 'This deployment script must run as root.\n' >&2
    exit 1
fi

if [[ "${1:-}" == "--repair" ]]; then
    if [[ "$#" -ne 1 ]]; then
        usage
        exit 2
    fi
    FORCE_REPAIR=1
elif [[ "${1:-}" == "--rollback" ]]; then
    if [[ "$#" -ne 2 ]]; then
        usage
        exit 2
    fi
elif [[ "$#" -ne 0 ]]; then
    usage
    exit 2
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

announce_step "Preflight"
if ! bash "$PREFLIGHT_SCRIPT"; then
    exit 1
fi

cd "$PROJECT_DIR"

if [[ "${1:-}" == "--rollback" ]]; then
    rollback_to_commit "$2" "manual_request"
    exit $?
fi

announce_step "Fetch origin/main"
admin_git fetch origin

OLD_COMMIT="$(admin_git rev-parse HEAD)"
NEW_COMMIT="$(admin_git rev-parse origin/main)"

log_event "deployment old=$OLD_COMMIT new=$NEW_COMMIT status=START"

if [[ "$OLD_COMMIT" != "$NEW_COMMIT" ]]; then
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
else
    CHANGED_FILES=()
    reset_change_flags
fi

if ! frontend_build_is_current "$NEW_COMMIT"; then
    FRONTEND_CHANGED=1
    announce "Frontend build marker is missing or stale; rebuild scheduled."
fi

if [[ "$FORCE_REPAIR" -eq 1 ]]; then
    FRONTEND_CHANGED=1
    PYTHON_CHANGED=1
    API_CHANGED=1
    announce "Repair mode enabled for the current Git snapshot."
fi

if [[ "$OLD_COMMIT" == "$NEW_COMMIT" \
      && "$FRONTEND_CHANGED" -eq 0 \
      && "$FORCE_REPAIR" -eq 0 ]]; then
    announce "already up to date"
    exit 0
fi

trap 'handle_deploy_error "$?" "$LINENO"' ERR
DEPLOYMENT_ACTIVE=1

if [[ "$OLD_COMMIT" != "$NEW_COMMIT" ]]; then
    announce_step "Fast-forward source"
    admin_git merge --ff-only origin/main
else
    announce "Source is already at origin/main; repairing generated assets."
fi

if [[ "$REQUIREMENTS_CHANGED" -eq 1 ]]; then
    announce_step "Python dependencies"
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
    announce_step "Frontend build"
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
    announce_step "Python compile"
    if compile_python; then
        log_event "build=python_compile status=PASS"
    else
        log_event "build=python_compile status=FAIL"
        false
    fi
else
    log_event "build=python_compile status=SKIP"
fi

announce_step "Offline tests"
if run_tests; then
    log_event "tests status=PASS"
else
    log_event "tests status=FAIL"
    false
fi

if [[ "$API_CHANGED" -eq 1 || "$REQUIREMENTS_CHANGED" -eq 1 ]]; then
    announce_step "Restart API"
    if systemctl restart football-api; then
        log_event "service=football-api status=restarted"
    else
        log_event "service=football-api status=FAIL"
        false
    fi
fi

announce_step "Refresh related timers"
restart_related_timers

announce_step "Health verification"
verify_api

DEPLOYMENT_ACTIVE=0
trap - ERR

log_event "deployment old=$OLD_COMMIT new=$NEW_COMMIT status=PASS"
printf 'Deployment complete: %s -> %s\n' "$OLD_COMMIT" "$NEW_COMMIT"
