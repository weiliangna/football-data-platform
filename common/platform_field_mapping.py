from datetime import datetime, timedelta, timezone


BEIJING_TZ = timezone(
    timedelta(hours=8),
    name="Asia/Shanghai",
)


def parse_epoch_milliseconds_beijing(value):
    if value in (None, ""):
        return None

    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return None

    try:
        return datetime.fromtimestamp(
            milliseconds / 1000,
            tz=BEIJING_TZ,
        )
    except (OverflowError, OSError, ValueError):
        return None


def database_datetime(value):
    if value is None:
        return None

    if value.tzinfo is None:
        return value

    return value.astimezone(BEIJING_TZ).replace(
        tzinfo=None
    )


def parse_caizhanyun_kickoff(day, enddate):
    day_text = str(day or "").strip()
    enddate_text = str(enddate or "").strip()

    if not day_text or not enddate_text:
        return None

    time_text = enddate_text.split()[-1].strip()

    try:
        return datetime.strptime(
            f"{day_text} {time_text}",
            "%Y%m%d %H:%M",
        )
    except (TypeError, ValueError):
        return None


def parse_integer_candidate(value):
    if value in (None, ""):
        return None

    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def resolve_caizhanyun_handicap(
    play_type,
    letpoint,
    legacy_order_handicap=0,
    allow_legacy_fallback=False,
):
    if str(play_type or "").strip() != "让球胜平负":
        return {
            "handicap": 0,
            "source": "not_applicable",
            "used_legacy_fallback": False,
        }

    per_leg = parse_integer_candidate(letpoint)

    if per_leg is not None:
        return {
            "handicap": per_leg,
            "source": "jingcaiResultList[].letpoint",
            "used_legacy_fallback": False,
        }

    if allow_legacy_fallback:
        legacy = parse_integer_candidate(
            legacy_order_handicap
        )
        return {
            "handicap": legacy or 0,
            "source": "orders.handicap_legacy_fallback",
            "used_legacy_fallback": True,
        }

    return {
        "handicap": 0,
        "source": "missing_per_leg_letpoint",
        "used_legacy_fallback": False,
    }


def resolve_hongrui_handicap(play_type, rq_number):
    if str(play_type or "").strip() != "让球胜平负":
        return 0

    value = parse_integer_candidate(rq_number)
    return value if value is not None else 0


def caizhanyun_identity_candidate(day, match_id):
    day_text = str(day or "").strip()
    match_id_text = str(match_id or "").strip()

    if not day_text or not match_id_text:
        return ""

    return f"1:{day_text}:{match_id_text}"


def select_avatar(
    detail_avatar=None,
    list_avatar=None,
    existing_avatar=None,
):
    for value in (
        detail_avatar,
        list_avatar,
        existing_avatar,
    ):
        text = str(value or "").strip()
        if text:
            return text

    return ""


def extract_caizhanyun_order_fields(info):
    source = info if isinstance(info, dict) else {}
    create_time = parse_epoch_milliseconds_beijing(
        source.get("createTime")
    )
    end_time = parse_epoch_milliseconds_beijing(
        source.get("endTime")
    )

    return {
        "publish_time": database_datetime(create_time),
        "create_time": create_time,
        "end_time_candidate": end_time,
        "end_time_semantic_status": (
            "probable" if end_time else "unknown"
        ),
        "end_time_deadline_exact": False,
    }


def extract_caizhanyun_match_fields(item):
    source = item if isinstance(item, dict) else {}
    match_id = str(
        source.get("matchId")
        or ""
    ).strip()
    team_id = str(
        source.get("teamId")
        or ""
    ).strip()
    day = str(source.get("day") or "").strip()
    week = str(source.get("week") or "").strip()
    enddate = str(
        source.get("enddate")
        or ""
    ).strip()
    kickoff_time = parse_caizhanyun_kickoff(
        day,
        enddate,
    )

    return {
        "match_id": match_id,
        "team_id": team_id,
        "day": day,
        "week": week,
        "match_name": str(
            source.get("team")
            or ""
        ).strip(),
        "league": str(
            source.get("league")
            or ""
        ).strip(),
        "letpoint": source.get("letpoint"),
        "enddate": enddate,
        "kickoff_time": kickoff_time,
        "kickoff_source": (
            "kickoff_proxy" if kickoff_time else None
        ),
        "kickoff_exact": False,
        "identity_candidate": (
            caizhanyun_identity_candidate(
                day,
                match_id,
            )
        ),
    }


def extract_hongrui_source_fields(
    raw_detail,
    list_item=None,
):
    raw = raw_detail if isinstance(raw_detail, dict) else {}
    data = raw.get("data") or {}
    head = data.get("head") or {}
    message = data.get("order_message") or {}
    list_source = (
        list_item if isinstance(list_item, dict) else {}
    )
    list_user = list_source.get("user") or {}

    expire_time = (
        head.get("expire_time")
        or list_source.get("expire_time")
        or ""
    )
    avatar_url = select_avatar(
        detail_avatar=head.get("user_pic"),
        list_avatar=list_user.get("user_pic"),
    )

    return {
        "expire_time_candidate": str(
            expire_time or ""
        ).strip(),
        "expire_time_semantic_status": "unknown",
        "expire_time_deadline_exact": False,
        "avatar_url": avatar_url,
        "fans_count": head.get("fans_count"),
        "profit_candidate": head.get("profit"),
        "bonus_num_candidate": head.get("bonus_num"),
        "field_count_candidate": message.get(
            "field_count"
        ),
        "status": head.get("status"),
        "status_msg": head.get("status_msg"),
        "bonus": head.get("bonus"),
        "commission_total": head.get(
            "commission_total"
        ),
    }
