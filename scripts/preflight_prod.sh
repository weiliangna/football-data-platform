#!/usr/bin/env bash

set -uo pipefail


PROJECT_DIR="/www/wwwroot/football_system"
APP_USER="admin"
FAILURES=0

REQUIRED_ENV_FILES=(
    "config/database.env"
    "config/app.env"
    "config/caizhanyun.env"
    "config/hongrui.env"
)

REQUIRED_UNITS=(
    "football-api.service"
    "football-pipeline.timer"
    "hongrui-spider.timer"
    "hongrui-results.timer"
    "football-settlement.timer"
    "football-statistics.timer"
    "football-avatar-sync.timer"
    "football-daily.timer"
    "football-backup.timer"
)


pass() {
    printf 'PASS: %s\n' "$1"
}


fail() {
    printf 'FAIL: %s\n' "$1" >&2
    FAILURES=$((FAILURES + 1))
}


run_as_admin() {
    runuser -u "$APP_USER" -- "$@"
}


admin_git() {
    run_as_admin git -C "$PROJECT_DIR" "$@"
}


check_command() {
    local command_name="$1"

    if command -v "$command_name" >/dev/null 2>&1; then
        pass "command available: $command_name"
    else
        fail "command unavailable: $command_name"
    fi
}


if [[ "${EUID}" -eq 0 ]]; then
    pass "running as root"
else
    fail "script must run as root"
fi

if id "$APP_USER" >/dev/null 2>&1; then
    pass "application user exists: $APP_USER"
else
    fail "application user missing: $APP_USER"
fi

for command_name in git runuser flock systemctl curl node npm; do
    check_command "$command_name"
done

if [[ -d "$PROJECT_DIR" ]]; then
    pass "project directory exists"
else
    fail "project directory missing: $PROJECT_DIR"
fi

if [[ -d "$PROJECT_DIR/.git" ]]; then
    pass "project is a Git repository"
else
    fail "Git metadata missing from project directory"
fi

if [[ -d "$PROJECT_DIR/.git" ]] && id "$APP_USER" >/dev/null 2>&1; then
    CURRENT_BRANCH="$(admin_git branch --show-current 2>/dev/null || true)"

    if [[ "$CURRENT_BRANCH" == "main" ]]; then
        pass "current branch is main"
    else
        fail "current branch must be main"
    fi

    WORKTREE_STATUS="$(
        admin_git status --porcelain --untracked-files=normal 2>/dev/null \
            || printf '__STATUS_FAILED__'
    )"

    if [[ -z "$WORKTREE_STATUS" ]]; then
        pass "Git working tree is clean"
    elif [[ "$WORKTREE_STATUS" == "__STATUS_FAILED__" ]]; then
        fail "unable to inspect Git working tree"
    else
        fail "Git working tree is not clean"
    fi

    if admin_git remote get-url origin >/dev/null 2>&1; then
        pass "Git remote origin exists"
    else
        fail "Git remote origin is unavailable"
    fi

    if admin_git fetch --quiet origin main; then
        pass "origin/main fetch succeeded"
    else
        fail "origin/main fetch failed"
    fi

    if admin_git rev-parse --verify origin/main^{commit} >/dev/null 2>&1; then
        pass "origin/main resolves to a commit"
    else
        fail "origin/main does not resolve to a commit"
    fi
fi

for relative_path in "${REQUIRED_ENV_FILES[@]}"; do
    if [[ -f "$PROJECT_DIR/$relative_path" ]]; then
        pass "production environment file exists: $relative_path"
    else
        fail "production environment file missing: $relative_path"
    fi
done

if [[ -x "$PROJECT_DIR/venv/bin/python" ]]; then
    pass "Python virtual environment is executable"
else
    fail "Python virtual environment missing: venv/bin/python"
fi

if [[ -x "$PROJECT_DIR/venv/bin/pip" ]]; then
    pass "pip is executable in the virtual environment"
else
    fail "pip missing from Python virtual environment"
fi

if id "$APP_USER" >/dev/null 2>&1; then
    if run_as_admin node --version >/dev/null 2>&1; then
        pass "Node.js is available to admin"
    else
        fail "Node.js is unavailable to admin"
    fi

    if run_as_admin npm --version >/dev/null 2>&1; then
        pass "npm is available to admin"
    else
        fail "npm is unavailable to admin"
    fi

    if run_as_admin test -x "$PROJECT_DIR/venv/bin/python"; then
        pass "admin can execute the project Python"
    else
        fail "admin cannot execute the project Python"
    fi
fi

for unit_name in "${REQUIRED_UNITS[@]}"; do
    if systemctl cat "$unit_name" >/dev/null 2>&1; then
        pass "systemd unit exists: $unit_name"
    else
        fail "systemd unit missing: $unit_name"
    fi
done

if [[ "$FAILURES" -eq 0 ]]; then
    printf 'PASS: production preflight completed successfully\n'
    exit 0
fi

printf 'FAIL: production preflight found %s critical problem(s)\n' \
    "$FAILURES" >&2
exit 1
