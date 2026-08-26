from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformDefinition:
    key: str
    name: str
    preferred_id: int
    short_name: str
    site: str


PLATFORM_DEFINITIONS = (
    PlatformDefinition(
        "caizhanyun",
        "彩站云",
        1,
        "彩",
        "https://hfive.cfgsdok.com/",
    ),
    PlatformDefinition(
        "zhouyunbao",
        "州运宝",
        2,
        "州",
        "https://hfive.cfkjmagic.cn/",
    ),
    PlatformDefinition(
        "hongrui",
        "鸿瑞",
        3,
        "鸿",
        "http://playerhf.fxgzht.com.cn/h5_1",
    ),
    PlatformDefinition(
        "yuncai",
        "云彩",
        4,
        "云",
        "https://ycahdtoquick03.sadsdh.com/",
    ),
    PlatformDefinition(
        "haodianzhu",
        "好店主",
        5,
        "店",
        "https://bbbkzu.haodianzhu.com.cn/",
    ),
    PlatformDefinition(
        "qishilu",
        "启示录",
        6,
        "启",
        "https://zs.htycp.cn/",
    ),
)


PLATFORM_BY_KEY = {
    item.key: item
    for item in PLATFORM_DEFINITIONS
}


PLATFORM_BY_DEFAULT_ID = {
    item.preferred_id: item
    for item in PLATFORM_DEFINITIONS
}


def default_platform_id(key):
    return PLATFORM_BY_KEY[str(key)].preferred_id


def default_platform_name(platform_id):
    item = PLATFORM_BY_DEFAULT_ID.get(int(platform_id or 0))
    if item:
        return item.name
    return f"平台{platform_id}"


def default_platform_metadata():
    return {
        item.preferred_id: {
            "key": item.key,
            "name": item.name,
            "short": item.short_name,
            "site": item.site,
        }
        for item in PLATFORM_DEFINITIONS
    }


def _default_connection_factory():
    from database.mysql import get_conn

    return get_conn()


def _rows_by_name(rows):
    return {
        str(row.get("name") or "").strip(): row
        for row in rows
        if isinstance(row, dict)
    }


def ensure_platform_configs(connection_factory=None):
    factory = connection_factory or _default_connection_factory
    conn = factory()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                platform_id,
                name,
                enabled,
                spider_enabled,
                result_enabled,
                settlement_enabled
            FROM platform_config
            ORDER BY platform_id
            FOR UPDATE
            """
        )
        rows = list(cursor.fetchall() or [])
        by_name = _rows_by_name(rows)
        used_ids = {
            int(row.get("platform_id") or 0)
            for row in rows
            if isinstance(row, dict)
            and int(row.get("platform_id") or 0) > 0
        }
        next_id = max(used_ids or {0}) + 1
        resolved = {}

        for definition in PLATFORM_DEFINITIONS:
            existing = by_name.get(definition.name)

            if existing:
                resolved[definition.key] = dict(existing)
                continue

            if definition.preferred_id not in used_ids:
                platform_id = definition.preferred_id
            else:
                while next_id in used_ids:
                    next_id += 1
                platform_id = next_id
                next_id += 1

            cursor.execute(
                """
                INSERT INTO platform_config
                (
                    platform_id,
                    name,
                    enabled,
                    spider_enabled,
                    result_enabled,
                    settlement_enabled
                )
                VALUES (%s,%s,1,1,1,1)
                """,
                (platform_id, definition.name),
            )
            created = {
                "platform_id": platform_id,
                "name": definition.name,
                "enabled": 1,
                "spider_enabled": 1,
                "result_enabled": 1,
                "settlement_enabled": 1,
            }
            resolved[definition.key] = created
            by_name[definition.name] = created
            used_ids.add(platform_id)

        conn.commit()
        return resolved
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
