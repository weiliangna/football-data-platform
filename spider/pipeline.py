import os
import sys
import time


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from database.mysql import get_conn
from spider.run_job import redact_sensitive_text


PLATFORMS = (
    {
        "platform_id": 1,
        "platform_name": "彩站云",
        "status": None,
    },
    {
        "platform_id": 3,
        "platform_name": "鸿瑞",
        "status": "external_scheduler",
    },
    {
        "platform_id": 2,
        "platform_name": "州运宝",
        "status": "waiting_config",
    },
    {
        "platform_id": 4,
        "platform_name": "云彩",
        "status": "waiting_config",
    },
)


def save_sync_log(record):
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sync_log
            (
                platform_id,
                platform_name,
                new_count,
                duplicate_count,
                status,
                cost_time,
                created_time
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW()
            )
            """,
            (
                record["platform_id"],
                record["platform_name"],
                record.get("new_count", 0),
                record.get("duplicate_count", 0),
                record["status"],
                record.get("cost_time", 0),
            ),
        )
        conn.commit()
    except Exception as exc:
        print(
            "写入同步日志失败:",
            redact_sensitive_text(str(exc)),
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def run_caizhanyun():
    started = time.time()

    try:
        from spider.caizhanyun_pipeline import main

        result = main([]) or {}
        failed_count = int(result.get("failed_count") or 0)

        return {
            "platform_id": 1,
            "platform_name": "彩站云",
            "new_count": int(result.get("new_count") or 0),
            "duplicate_count": int(result.get("duplicate_count") or 0),
            "status": "failed" if failed_count else "success",
            "cost_time": round(time.time() - started, 2),
        }
    except Exception as exc:
        print(
            "彩站云采集失败:",
            redact_sensitive_text(str(exc)),
        )
        return {
            "platform_id": 1,
            "platform_name": "彩站云",
            "new_count": 0,
            "duplicate_count": 0,
            "status": "failed",
            "cost_time": round(time.time() - started, 2),
        }


def build_external_statuses():
    return [
        {
            "platform_id": platform["platform_id"],
            "platform_name": platform["platform_name"],
            "new_count": 0,
            "duplicate_count": 0,
            "status": platform["status"],
            "cost_time": 0,
        }
        for platform in PLATFORMS
        if platform["platform_id"] != 1
    ]


def run(caizhanyun_runner=None, status_recorder=None):
    runner = caizhanyun_runner or run_caizhanyun
    recorder = status_recorder or save_sync_log

    try:
        caizhanyun_status = runner()
        if not isinstance(caizhanyun_status, dict):
            raise TypeError("彩站云运行结果必须是字典")
    except Exception as exc:
        print(
            "彩站云状态生成失败:",
            redact_sensitive_text(str(exc)),
        )
        caizhanyun_status = {
            "platform_id": 1,
            "platform_name": "彩站云",
            "new_count": 0,
            "duplicate_count": 0,
            "status": "failed",
            "cost_time": 0,
        }

    statuses = [caizhanyun_status]
    statuses.extend(build_external_statuses())

    for record in statuses:
        try:
            recorder(record)
        except Exception as exc:
            print(
                f"{record['platform_name']} 状态记录失败:",
                redact_sensitive_text(str(exc)),
            )

    return statuses


if __name__ == "__main__":
    run()
