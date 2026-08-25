import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

import pymysql


ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from database.mysql import get_conn


JWT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){1,2}",
    re.IGNORECASE,
)
AUTHORIZATION_PATTERN = re.compile(
    r"(\bAuthorization\b\s*[:=]\s*)(?:Bearer\s+)?(?:\"[^\"]*\"|'[^']*'|[^\s,]+)",
    re.IGNORECASE,
)
COOKIE_PATTERN = re.compile(
    r"(\bCookie\b\s*[:=]\s*)[^\r\n]*",
    re.IGNORECASE,
)
ASSIGNMENT_PATTERN = re.compile(
    r"(\b(?:[A-Za-z0-9_]*(?:token|password|passwd|secret)[A-Za-z0-9_]*)\b\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;&]+)",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(
    r"(\bBearer\s+)[A-Za-z0-9._~+/-]+",
    re.IGNORECASE,
)


def redact_sensitive_text(value):
    text = "" if value is None else str(value)
    text = JWT_PATTERN.sub("[REDACTED_JWT]", text)
    text = AUTHORIZATION_PATTERN.sub(r"\1[REDACTED]", text)
    text = COOKIE_PATTERN.sub(r"\1[REDACTED]", text)
    text = ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", text)
    text = BEARER_PATTERN.sub(r"\1[REDACTED]", text)
    return text


def job_enabled(platform_id, name):
    if platform_id <= 0:
        return True

    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT spider_enabled,result_enabled
            FROM platform_config
            WHERE platform_id=%s
            LIMIT 1
            """,
            (platform_id,),
        )
        row = cursor.fetchone()
        if not row:
            return True
        lowered = str(name or "").lower()
        if "result" in lowered:
            return bool(int(row.get("result_enabled") or 0))
        if "spider" in lowered:
            return bool(int(row.get("spider_enabled") or 0))
        return True
    except Exception:
        return True
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def write_log(platform_id, name, started, finished, status, exit_code, message):
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            INSERT INTO spider_logs
            (platform_id,spider_name,started_time,finished_time,status,exit_code,message)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                platform_id,
                name,
                started,
                finished,
                status,
                exit_code,
                redact_sensitive_text(message)[-8000:],
            ),
        )
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="统一任务执行与日志记录")
    parser.add_argument("--name", required=True)
    parser.add_argument("--platform-id", type=int, default=0)
    parser.add_argument("--module", required=True)
    parser.add_argument("--args", nargs=argparse.REMAINDER, default=[])
    args = parser.parse_args()

    started = datetime.now()

    if not job_enabled(args.platform_id, args.name):
        message = "平台配置已暂停此任务"
        print(message)
        write_log(
            args.platform_id,
            args.name,
            started,
            datetime.now(),
            "skipped",
            0,
            message,
        )
        return

    command = [sys.executable, "-m", args.module] + list(args.args)
    print(
        "执行任务:",
        redact_sensitive_text(" ".join(command)),
    )

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    safe_stdout = redact_sensitive_text(result.stdout)
    safe_stderr = redact_sensitive_text(result.stderr)

    if safe_stdout:
        print(safe_stdout, end="")
    if safe_stderr:
        print(safe_stderr, end="", file=sys.stderr)

    status = "success" if result.returncode == 0 else "failed"
    message = safe_stderr or safe_stdout or ""

    write_log(
        args.platform_id,
        args.name,
        started,
        datetime.now(),
        status,
        result.returncode,
        message,
    )

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
