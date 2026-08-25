import argparse
import os
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
            (platform_id,)
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
                message[-8000:] if message else ""
            )
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
            message
        )
        return

    command = [sys.executable, "-m", args.module] + list(args.args)
    print("执行任务:", " ".join(command))

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    status = "success" if result.returncode == 0 else "failed"
    message = result.stderr or result.stdout or ""

    write_log(
        args.platform_id,
        args.name,
        started,
        datetime.now(),
        status,
        result.returncode,
        message
    )

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
