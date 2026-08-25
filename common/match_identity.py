from datetime import date, datetime

from common.match_utils import (
    build_match_key,
    normalize_team_name,
    parse_match_name,
)


IDENTITY_V2_COLUMNS = {
    "platform_id",
    "match_date",
    "normalized_home",
    "normalized_away",
    "match_identity",
    "identity_quality",
}


def normalize_match_date(value):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    for format_text in (
        "%Y-%m-%d",
        "%Y%m%d",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(
                text[:10],
                format_text,
            ).date()
        except ValueError:
            continue

    return None


def normalize_identity_text(value):
    return normalize_team_name(value)


def build_alias_map(rows):
    alias_map = {}

    for row in rows or []:
        if not isinstance(row, dict):
            continue

        try:
            platform_id = int(row.get("platform_id") or 0)
        except (TypeError, ValueError):
            platform_id = 0

        alias = normalize_identity_text(
            row.get("alias_name")
        )
        canonical = str(
            row.get("canonical_name")
            or ""
        ).strip()

        if alias and canonical:
            alias_map[(platform_id, alias)] = canonical

    return alias_map


def load_team_aliases(cursor):
    cursor.execute(
        """
        SELECT platform_id,canonical_name,alias_name
        FROM team_aliases
        """
    )
    return build_alias_map(cursor.fetchall())


def canonical_team(alias_map, platform_id, team):
    raw_team = str(team or "").strip()

    if not raw_team:
        return ""

    try:
        platform = int(platform_id or 0)
    except (TypeError, ValueError):
        platform = 0

    key = normalize_identity_text(raw_team)
    return (
        (alias_map or {}).get((platform, key))
        or (alias_map or {}).get((0, key))
        or raw_team
    )


def canonical_match(
    alias_map,
    platform_id,
    match_name=None,
    home_team=None,
    away_team=None,
):
    home = str(home_team or "").strip()
    away = str(away_team or "").strip()

    if not home or not away:
        parsed = parse_match_name(match_name)
        home = parsed["home_team"] or ""
        away = parsed["away_team"] or ""

    canonical_home = canonical_team(
        alias_map,
        platform_id,
        home,
    )
    canonical_away = canonical_team(
        alias_map,
        platform_id,
        away,
    )
    match_key = build_match_key(
        home_team=canonical_home,
        away_team=canonical_away,
    )

    return {
        "home": canonical_home,
        "away": canonical_away,
        "normalized_home": normalize_identity_text(
            canonical_home
        ),
        "normalized_away": normalize_identity_text(
            canonical_away
        ),
        "display": (
            f"{canonical_home} VS {canonical_away}"
            if canonical_home and canonical_away
            else str(match_name or canonical_home or "")
        ),
        "match_key": match_key,
    }


def build_match_identity(
    platform_id,
    match_date=None,
    source_match_code=None,
    match_name=None,
    home_team=None,
    away_team=None,
    alias_map=None,
):
    try:
        platform = int(platform_id)
    except (TypeError, ValueError):
        platform = None

    normalized_date = normalize_match_date(match_date)
    source_code = str(
        source_match_code
        or ""
    ).strip()
    canonical = canonical_match(
        alias_map or {},
        platform or 0,
        match_name=match_name,
        home_team=home_team,
        away_team=away_team,
    )
    match_key = canonical["match_key"]

    if platform is not None and normalized_date and source_code:
        identity = (
            f"{platform}|{normalized_date.isoformat()}|"
            f"{source_code}"
        )
        quality = "exact"
    elif platform is not None and normalized_date and match_key:
        identity = (
            f"{platform}|{normalized_date.isoformat()}|"
            f"{match_key}"
        )
        quality = "secondary"
    elif platform is not None and source_code and match_key:
        identity = (
            f"{platform}|incomplete|{source_code}|"
            f"{match_key}"
        )
        quality = "incomplete"
    else:
        identity = ""
        quality = "legacy"

    return {
        "platform_id": platform,
        "match_date": normalized_date,
        "source_match_code": source_code,
        "normalized_home": canonical["normalized_home"],
        "normalized_away": canonical["normalized_away"],
        "match_key": match_key,
        "match_identity": identity,
        "identity_quality": quality,
        "home_team": canonical["home"],
        "away_team": canonical["away"],
        "display_name": canonical["display"],
    }


def identity_match_strategy(result_row, order_match_row):
    result = result_row or {}
    order_match = order_match_row or {}

    try:
        result_platform = int(result.get("platform_id"))
    except (TypeError, ValueError):
        result_platform = None

    try:
        order_platform = int(order_match.get("platform_id"))
    except (TypeError, ValueError):
        order_platform = None

    if (
        result_platform is not None
        and order_platform is not None
        and result_platform != order_platform
    ):
        return None

    result_date = normalize_match_date(
        result.get("match_date")
    )
    order_date = normalize_match_date(
        order_match.get("match_date")
    )
    result_code = str(
        result.get("source_match_code")
        or result.get("match_code")
        or ""
    ).strip()
    order_code = str(
        order_match.get("source_match_code")
        or order_match.get("match_code")
        or ""
    ).strip()

    if (
        result_platform is not None
        and order_platform is not None
        and result_date
        and order_date
        and result_date == order_date
        and result_code
        and result_code == order_code
    ):
        return "identity_v2"

    result_key = str(
        result.get("match_key")
        or ""
    ).strip()
    order_key = str(
        order_match.get("match_key")
        or ""
    ).strip()

    if (
        result_platform is not None
        and order_platform is not None
        and result_date
        and order_date
        and result_date == order_date
        and result_key
        and result_key == order_key
    ):
        return "identity_fallback"

    result_name = str(
        result.get("match_name")
        or ""
    ).strip()
    order_name = str(
        order_match.get("match_name")
        or ""
    ).strip()
    result_complete = bool(
        result_platform is not None
        and result_date
        and (result_code or result_key)
    )
    order_complete = bool(
        order_platform is not None
        and order_date
        and (order_code or order_key)
    )

    if (
        result_name
        and result_name == order_name
        and (not result_complete or not order_complete)
    ):
        return "legacy_match_name"

    return None


def table_columns(cursor, table_name):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME=%s
        """,
        (table_name,),
    )
    return {
        row["COLUMN_NAME"]
        for row in cursor.fetchall()
    }


def supports_identity_v2(columns):
    return IDENTITY_V2_COLUMNS.issubset(
        set(columns or ())
    )
