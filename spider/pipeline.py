import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from common.platform_registry import (
    PLATFORM_DEFINITIONS,
    STOPPED_PLATFORM_KEYS,
    ensure_platform_configs,
)
from config.platform_ingestion_config import (
    MissingPlatformConfig,
    SourceContractUnavailable,
)
from database.mysql import get_conn
from spider.run_job import redact_sensitive_text


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
            VALUES (%s,%s,%s,%s,%s,%s,NOW())
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


def _summary_counts(summary):
    data = summary if isinstance(summary, dict) else {}
    return {
        "new_count": int(data.get("new_count") or 0),
        "duplicate_count": int(
            data.get("duplicate_count") or 0
        ),
        "failed_count": int(data.get("failed_count") or 0),
        "issue_count": int(data.get("issue_count") or 0),
    }


def _combine_summaries(*summaries):
    result = {
        "new_count": 0,
        "duplicate_count": 0,
        "failed_count": 0,
        "issue_count": 0,
    }
    for summary in summaries:
        counts = _summary_counts(summary)
        for key in result:
            result[key] += counts[key]
    return result


def _run_command(arguments, timeout=180):
    completed = subprocess.run(
        arguments,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    stdout = redact_sensitive_text(completed.stdout or "")
    stderr = redact_sensitive_text(completed.stderr or "")
    if stdout.strip():
        print(stdout.rstrip())
    if stderr.strip():
        print(stderr.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(
            f"子任务退出码 {completed.returncode}"
        )
    return completed


def run_caizhanyun(runtime):
    from spider.caizhanyun_pipeline import main as run_collection
    from spider.caizhanyun_result_sync import sync_pending_results

    collection_summary = None
    result_summary = None
    errors = []

    try:
        collection_summary = run_collection([]) or {}
    except Exception as exc:
        errors.append(exc)

    if int(runtime.get("result_enabled") or 0):
        try:
            result_summary = sync_pending_results(
                platform_id=runtime["platform_id"],
            )
        except Exception as exc:
            errors.append(exc)

    summary = _combine_summaries(
        collection_summary,
        result_summary,
    )
    summary["failed_count"] += len(errors)
    for exc in errors:
        print(
            "彩站云子任务失败:",
            redact_sensitive_text(str(exc)),
        )
    return summary


def run_hongrui(runtime):
    _run_command(
        [
            sys.executable,
            "-m",
            "spider.hongrui",
            "--limit",
            "0",
            "--write",
        ]
    )
    if int(runtime.get("result_enabled") or 0):
        _run_command(
            [
                sys.executable,
                "-m",
                "spider.hongrui_results",
            ]
        )
    return {
        "new_count": 0,
        "duplicate_count": 0,
        "failed_count": 0,
    }


def run_zhouyunbao(runtime):
    from spider.zhouyunbao import run_live

    return run_live(
        platform_id=runtime["platform_id"],
        limit=None,
    )


def run_yuncai(runtime):
    from spider.yuncai import run_live

    return run_live(
        platform_id=runtime["platform_id"],
        limit=None,
    )


def run_haodianzhu(runtime):
    from spider.haodianzhu import run_live

    return run_live(
        platform_id=runtime["platform_id"],
        limit=None,
    )


def run_qishilu(runtime):
    from spider.qishilu import run_live

    return run_live(
        platform_id=runtime["platform_id"],
        limit=None,
    )


DEFAULT_RUNNERS = {
    "caizhanyun": run_caizhanyun,
    "zhouyunbao": run_zhouyunbao,
    "hongrui": run_hongrui,
    "yuncai": run_yuncai,
    "haodianzhu": run_haodianzhu,
    "qishilu": run_qishilu,
}


def _disabled_status(runtime):
    return not (
        int(runtime.get("enabled") or 0)
        and int(runtime.get("spider_enabled") or 0)
    )


def _run_one(definition, runtime, runner):
    started = time.time()
    base = {
        "platform_id": int(runtime["platform_id"]),
        "platform_name": definition.name,
        "new_count": 0,
        "duplicate_count": 0,
        "status": "failed",
        "cost_time": 0,
    }

    if (
        definition.key in STOPPED_PLATFORM_KEYS
        or _disabled_status(runtime)
    ):
        base["status"] = "disabled"
        return base

    try:
        summary = runner(runtime) or {}
        counts = _summary_counts(summary)
        base.update(counts)
        issues = list(summary.get("issues") or [])
        for issue in issues[:20]:
            print(
                f"{definition.name}数据契约问题:",
                redact_sensitive_text(str(issue)),
            )
        if len(issues) > 20:
            print(
                f"{definition.name}数据契约问题:",
                f"另有 {len(issues) - 20} 条未展开",
            )
        if counts["failed_count"] or counts["issue_count"]:
            base["status"] = (
                "partial"
                if counts["new_count"]
                or counts["duplicate_count"]
                else "failed"
            )
        else:
            base["status"] = "success"
    except MissingPlatformConfig as exc:
        base["status"] = "waiting_config"
        print(
            f"{definition.name}配置未就绪:",
            redact_sensitive_text(str(exc)),
        )
    except SourceContractUnavailable as exc:
        base["status"] = "waiting_contract"
        print(
            f"{definition.name}请求契约未就绪:",
            redact_sensitive_text(str(exc)),
        )
    except Exception as exc:
        base["status"] = "failed"
        print(
            f"{definition.name}采集失败:",
            redact_sensitive_text(str(exc)),
        )
    finally:
        base["cost_time"] = round(time.time() - started, 2)
    return base


def _legacy_run(caizhanyun_runner, status_recorder):
    started = time.time()
    try:
        raw = caizhanyun_runner() or {}
        counts = _summary_counts(raw)
        caizhanyun_status = {
            "platform_id": 1,
            "platform_name": "彩站云",
            "new_count": counts["new_count"],
            "duplicate_count": counts["duplicate_count"],
            "status": (
                "failed"
                if counts["failed_count"]
                else "success"
            ),
            "cost_time": round(time.time() - started, 2),
        }
    except Exception:
        caizhanyun_status = {
            "platform_id": 1,
            "platform_name": "彩站云",
            "new_count": 0,
            "duplicate_count": 0,
            "status": "failed",
            "cost_time": round(time.time() - started, 2),
        }

    statuses = [
        caizhanyun_status,
        {
            "platform_id": 3,
            "platform_name": "鸿瑞",
            "new_count": 0,
            "duplicate_count": 0,
            "status": "external_scheduler",
            "cost_time": 0,
        },
        {
            "platform_id": 2,
            "platform_name": "州运宝",
            "new_count": 0,
            "duplicate_count": 0,
            "status": "waiting_config",
            "cost_time": 0,
        },
        {
            "platform_id": 4,
            "platform_name": "云彩",
            "new_count": 0,
            "duplicate_count": 0,
            "status": "waiting_config",
            "cost_time": 0,
        },
    ]
    for record in statuses:
        status_recorder(record)
    return statuses


def run(
    platform_resolver=None,
    runners=None,
    status_recorder=None,
    executor_factory=None,
    caizhanyun_runner=None,
):
    recorder = status_recorder or save_sync_log
    if caizhanyun_runner is not None:
        return _legacy_run(caizhanyun_runner, recorder)

    resolver = platform_resolver or ensure_platform_configs
    active_runners = dict(DEFAULT_RUNNERS)
    if runners:
        active_runners.update(runners)
    executor_type = executor_factory or ThreadPoolExecutor

    runtimes = resolver()
    statuses_by_key = {}

    with executor_type(
        max_workers=len(PLATFORM_DEFINITIONS)
    ) as executor:
        futures = {}
        for definition in PLATFORM_DEFINITIONS:
            runtime = runtimes[definition.key]
            future = executor.submit(
                _run_one,
                definition,
                runtime,
                active_runners[definition.key],
            )
            futures[future] = definition.key

        for future in as_completed(futures):
            key = futures[future]
            try:
                statuses_by_key[key] = future.result()
            except Exception as exc:
                definition = next(
                    item
                    for item in PLATFORM_DEFINITIONS
                    if item.key == key
                )
                runtime = runtimes[key]
                statuses_by_key[key] = {
                    "platform_id": int(runtime["platform_id"]),
                    "platform_name": definition.name,
                    "new_count": 0,
                    "duplicate_count": 0,
                    "status": "failed",
                    "cost_time": 0,
                }
                print(
                    f"{definition.name}并发任务失败:",
                    redact_sensitive_text(str(exc)),
                )

    statuses = [
        statuses_by_key[item.key]
        for item in PLATFORM_DEFINITIONS
    ]

    for record in statuses:
        try:
            recorder(record)
        except Exception as exc:
            print(
                f"{record['platform_name']}状态记录失败:",
                redact_sensitive_text(str(exc)),
            )

    return statuses


if __name__ == "__main__":
    run()
