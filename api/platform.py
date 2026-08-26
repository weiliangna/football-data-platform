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

    for preferred_id, metadata in default_platform_metadata().items():
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

    for row in existing:
        if row["platform_id"] in emitted_ids:
            continue
        item = dict(row)
        item["configured"] = True
        merged.append(item)

    return sorted(
        merged,
        key=lambda item: item["platform_id"],
    )


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
        return {
            "code": 200,
            "status": "success",
            "data": merge_platform_configs(rows),
        }
    except Exception:
        return {
            "code": 200,
            "status": "degraded",
            "msg": "platform_config unavailable",
            "data": merge_platform_configs([]),
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
