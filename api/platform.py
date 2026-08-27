from fastapi import APIRouter

from common.platform_registry import default_platform_metadata
from database.mysql import get_conn


router = APIRouter(prefix="/api/platform", tags=["platform"])


CONFIG_FIELDS = (
    "enabled",
    "spider_enabled",
    "result_enabled",
    "settlement_enabled",
)

READY_SYNC_STATUSES = {
    "success",
    "partial",
    "external_scheduler",
}


def _integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_row(row):
    if not isinstance(row, dict):
        return {}

    cleaned = dict(row)
    cleaned["platform_id"] = _integer(
        cleaned.get("platform_id"),
        0,
    )
    cleaned["name"] = str(cleaned.get("name") or "").strip()
    return cleaned


def merge_platform_configs(rows):
    existing = [
        _clean_row(row)
        for row in rows or []
        if isinstance(row, dict)
    ]
    existing = [
        row
        for row in existing
        if row["platform_id"] > 0
    ]
    by_name = {
        row["name"]: row
        for row in existing
        if row["name"]
    }
    used_ids = {
        row["platform_id"]
        for row in existing
    }
    emitted_ids = set()
    next_id = max(used_ids or {0}) + 1
    merged = []

    for preferred_id, metadata in default_platform_metadata(
        active_only=True
    ).items():
        name = metadata["name"]
        configured = by_name.get(name)

        if configured:
            item = dict(configured)
            platform_id = item["platform_id"]
        else:
            if preferred_id not in used_ids:
                platform_id = preferred_id
            else:
                while next_id in used_ids:
                    next_id += 1
                platform_id = next_id
                next_id += 1
            item = {
                "platform_id": platform_id,
                "name": name,
                "updated_time": None,
            }
            for field in CONFIG_FIELDS:
                item[field] = 0

        item["configured"] = configured is not None
        item["key"] = metadata["key"]
        item["short"] = metadata["short"]
        item["site"] = metadata["site"]
        merged.append(item)
        emitted_ids.add(platform_id)
        used_ids.add(platform_id)

    return sorted(
        merged,
        key=lambda item: item["platform_id"],
    )


def attach_runtime_status(platforms, sync_rows):
    latest = {
        _integer(row.get("platform_id"), 0): row
        for row in sync_rows or []
        if isinstance(row, dict)
        and _integer(row.get("platform_id"), 0) > 0
    }
    result = []

    for platform in platforms:
        item = dict(platform)
        platform_id = _integer(item.get("platform_id"), 0)
        sync = latest.get(platform_id, {})

        if _integer(item.get("enabled"), 0) != 1:
            runtime_status = "disabled"
        elif sync.get("status"):
            runtime_status = str(sync["status"]).strip()
        elif not item.get("configured"):
            runtime_status = "waiting_config"
        else:
            runtime_status = "not_run"

        item["runtime_status"] = runtime_status
        item["runtime_ready"] = runtime_status in READY_SYNC_STATUSES
        item["last_sync_time"] = sync.get("created_time")
        item["last_new_count"] = _integer(sync.get("new_count"), 0)
        item["last_duplicate_count"] = _integer(
            sync.get("duplicate_count"),
            0,
        )
        item["last_cost_time"] = float(sync.get("cost_time") or 0)
        result.append(item)

    return result


@router.get("/list")
def platform_list():
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                platform_id,
                name,
                enabled,
                spider_enabled,
                result_enabled,
                settlement_enabled,
                updated_time
            FROM platform_config
            ORDER BY platform_id ASC
            """
        )
        rows = cursor.fetchall() or []
        platforms = merge_platform_configs(rows)
        sync_rows = []
        try:
            cursor.execute(
                """
                SELECT
                    sl.platform_id,
                    sl.new_count,
                    sl.duplicate_count,
                    sl.status,
                    sl.cost_time,
                    sl.created_time
                FROM sync_log sl
                INNER JOIN
                (
                    SELECT platform_id,MAX(id) AS latest_id
                    FROM sync_log
                    GROUP BY platform_id
                ) latest
                    ON latest.latest_id=sl.id
                """
            )
            sync_rows = cursor.fetchall() or []
        except Exception:
            sync_rows = []
        return {
            "code": 200,
            "status": "success",
            "data": attach_runtime_status(platforms, sync_rows),
        }
    except Exception:
        return {
            "code": 200,
            "status": "degraded",
            "msg": "platform_config unavailable",
            "data": attach_runtime_status(
                merge_platform_configs([]),
                [],
            ),
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
