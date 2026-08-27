import json

from common.match_utils import parse_match_name
from common.pass_utils import decode_pass_code
from common.platform_field_mapping import (
    database_datetime,
    parse_epoch_milliseconds_beijing,
)
from spider.unified_ingestion import as_float, as_int


PLAY_TYPES = {
    "J00001": "胜平负",
    "J00002": "比分",
    "J00003": "总进球",
    "J00004": "半全场",
    "J00013": "让球胜平负",
}

THREE_WAY = {
    "3": "主胜",
    "1": "平",
    "0": "主负",
}

HANDICAP_THREE_WAY = {
    "3": "让胜",
    "1": "让平",
    "0": "让负",
}

HALF_FULL = {
    "3": "胜",
    "1": "平",
    "0": "负",
}


def parse_list_response(response):
    raw = response if isinstance(response, dict) else {}

    if str(raw.get("errorCode") or "") != "0":
        raise ValueError("MagicAngle 列表响应 errorCode 非 0")

    data = raw.get("data") or {}
    rows = data.get("rankList") or []

    if not isinstance(rows, list):
        raise ValueError("MagicAngle 列表响应缺少 data.rankList")

    return [item for item in rows if isinstance(item, dict)]


def parse_detail_response(response):
    raw = response if isinstance(response, dict) else {}

    if str(raw.get("errorCode") or "") != "0":
        raise ValueError("MagicAngle 详情响应 errorCode 非 0")

    data = raw.get("data") or {}
    info = data.get("prescientInfo") or {}

    if not isinstance(info, dict) or not info:
        raise ValueError("MagicAngle 详情响应缺少 prescientInfo")

    return data, info, data.get("starterInfo") or {}


def decode_three_way(code, mapping):
    result = []

    for character in str(code or ""):
        value = mapping.get(character, character)
        if value not in result:
            result.append(value)

    return result


def decode_score(code):
    special = {
        "90": "胜其他",
        "99": "平其他",
        "09": "负其他",
    }
    text = str(code or "")
    result = []

    for index in range(0, len(text), 2):
        part = text[index:index + 2]
        if len(part) != 2:
            continue
        result.append(special.get(part, f"{part[0]}:{part[1]}"))

    return result


def decode_goals(code):
    result = []

    for character in str(code or ""):
        result.append(
            "7+球" if character == "7" else f"{character}球"
        )

    return result


def decode_half_full(code):
    text = str(code or "")
    result = []

    for index in range(0, len(text), 2):
        part = text[index:index + 2]
        if len(part) != 2:
            continue
        result.append(
            HALF_FULL.get(part[0], part[0])
            + HALF_FULL.get(part[1], part[1])
        )

    return result


def decode_market(play_type, code):
    if play_type == "让球胜平负":
        return decode_three_way(code, HANDICAP_THREE_WAY)
    if play_type == "比分":
        return decode_score(code)
    if play_type == "总进球":
        return decode_goals(code)
    if play_type == "半全场":
        return decode_half_full(code)
    return decode_three_way(code, THREE_WAY)


def build_match_maps(matches):
    by_team = {}
    by_day_team = {}

    for match in matches or []:
        if not isinstance(match, dict):
            continue
        team_id = str(match.get("teamId") or "").strip()
        day = str(match.get("day") or "").strip()
        if not team_id:
            continue
        by_team[team_id] = match
        if day:
            by_day_team[f"{day}|{team_id}"] = match

    return by_team, by_day_team


def decode_bet_code(info, matches):
    raw = str(
        info.get("betCodeForResult")
        or info.get("betCode")
        or ""
    ).strip()

    if not raw:
        order_info = info.get("orderInfo")
        if isinstance(order_info, str):
            raw = order_info.split("_", 1)[0]

    if "!" in raw:
        raw = raw.split("!", 1)[0]

    if "@" not in raw:
        return raw, []

    pass_code, option_body = raw.split("@", 1)
    by_team, by_day_team = build_match_maps(matches)
    decoded = []

    for segment in option_body.split("^"):
        parts = segment.strip().split("|")
        if len(parts) < 4:
            continue
        selection_code = str(parts[-1])
        team_id = str(parts[-2])
        market_code = None

        if team_id.startswith("J"):
            market_code = team_id
            if len(parts) < 5:
                continue
            team_id = str(parts[-3])

        play_type = (
            PLAY_TYPES.get(market_code)
            or PLAY_TYPES.get(str(info.get("lotNo") or ""))
            or "胜平负"
        )
        day = str(parts[0] or "")
        match = (
            by_day_team.get(f"{day}|{team_id}")
            or by_team.get(team_id)
            or {}
        )
        decoded.append(
            {
                "pass_code": pass_code,
                "pass_name": decode_pass_code(pass_code),
                "market_code": market_code,
                "play_type": play_type,
                "selection_code": selection_code,
                "selection": decode_market(play_type, selection_code),
                "team_id": str(match.get("teamId") or team_id),
                "match_id": str(match.get("matchId") or ""),
                "match_name": str(match.get("team") or team_id),
                "league": str(match.get("league") or ""),
                "day": str(match.get("day") or day),
                "week": str(match.get("week") or ""),
                "enddate": str(match.get("enddate") or ""),
                "letpoint": match.get("letpoint"),
                "source_match": match,
            }
        )

    return raw, decoded


def _selection_codes(play_type, selection_code):
    text = str(selection_code or "")
    width = 2 if play_type in {"比分", "半全场"} else 1
    return [
        text[index:index + width]
        for index in range(0, len(text), width)
        if len(text[index:index + width]) == width
    ]


def _peilv_type(play_type, code):
    prefixes = {
        "胜平负": "v",
        "让球胜平负": "letVs_v",
        "比分": "score_v",
        "总进球": "goal_v",
        "半全场": "half_v",
    }
    prefix = prefixes.get(play_type)
    return f"{prefix}{code}" if prefix else ""


def resolve_leg_result(decoded_item):
    match = decoded_item.get("source_match") or {}
    prices = match.get("peilvs") or []
    expected = {
        _peilv_type(decoded_item["play_type"], code)
        for code in _selection_codes(
            decoded_item["play_type"],
            decoded_item["selection_code"],
        )
    }
    matched = [
        item
        for item in prices
        if isinstance(item, dict)
        and str(item.get("type") or "") in expected
    ]

    if not matched:
        return "待开奖"

    if any(
        str(item.get("isHit") or "").strip().lower()
        in {"true", "1"}
        for item in matched
    ):
        return "赢"

    return "输"


def parse_score(value):
    text = str(value or "").strip()
    if ":" not in text:
        return None
    left, right = text.split(":", 1)
    try:
        return int(left), int(right)
    except ValueError:
        return None


def _verified_order_result(win_flag):
    value = as_int(win_flag, -1)
    if value == 2:
        return "赢", "已中奖"
    if value == 1:
        return "输", "未中奖"
    return "待开奖", "待开奖"


def build_record(
    list_item,
    detail_response,
    platform_id,
    platform_name,
    avatar_source,
):
    _, info, starter = parse_detail_response(detail_response)
    matches = info.get("jingcaiResultList") or []
    bet_code, decoded = decode_bet_code(info, matches)
    source_order_id = str(
        info.get("id") or list_item.get("id") or ""
    ).strip()
    user_id = (
        starter.get("id")
        or list_item.get("starterId")
        or info.get("starter")
    )
    nickname = str(
        starter.get("nickname")
        or list_item.get("staterName")
        or ""
    ).strip()
    avatar = str(
        starter.get("headPic")
        or list_item.get("staterPhoto")
        or ""
    ).strip()
    stake = as_float(info.get("selfBuyAmt"), 0) / 100
    platform_bonus = as_float(info.get("allPrizeAmt"), 0) / 100
    result, settlement_status = _verified_order_result(
        info.get("winFlag")
    )
    profit = (
        platform_bonus - stake
        if result == "赢"
        else (-stake if result == "输" else 0)
    )
    pass_names = []
    play_types = []
    selection_text = []
    legs = []
    match_results = []

    for item in decoded:
        if item["pass_name"] and item["pass_name"] not in pass_names:
            pass_names.append(item["pass_name"])
        if item["play_type"] not in play_types:
            play_types.append(item["play_type"])
        parsed_name = parse_match_name(item["match_name"])
        selection = "/".join(item["selection"])
        handicap = (
            as_int(item.get("letpoint"), 0)
            if item["play_type"] == "让球胜平负"
            else 0
        )
        leg_result = resolve_leg_result(item)
        prices = item["source_match"].get("peilvs") or []
        option_detail = [
            {
                "name": label,
                "odds": None,
            }
            for label in item["selection"]
        ]
        legs.append(
            {
                "source_match_code": item["match_id"],
                "match_name": item["match_name"],
                "home_team": parsed_name["home_team"],
                "away_team": parsed_name["away_team"],
                "match_date": item["day"],
                "league": item["league"],
                "play_type": item["play_type"],
                "selection": selection,
                "option_detail": option_detail,
                "handicap": handicap,
                "deadline_time": None,
                "deadline_source": "unverified_enddate",
                "deadline_exact": False,
                "result": leg_result,
                "source_prices": prices,
            }
        )
        selection_text.append(
            f"{item['match_name']} → {item['play_type']}：{selection}"
        )

    for match in matches:
        score = parse_score(match.get("result"))
        if score is None:
            continue
        half_score = parse_score(match.get("firsthalfresult")) or (0, 0)
        parsed_name = parse_match_name(match.get("team"))
        match_results.append(
            {
                "source_match_code": str(match.get("matchId") or ""),
                "match_name": parsed_name["raw_name"],
                "home_team": parsed_name["home_team"],
                "away_team": parsed_name["away_team"],
                "match_date": str(match.get("day") or ""),
                "league": str(match.get("league") or ""),
                "home_score": score[0],
                "away_score": score[1],
                "half_home_score": half_score[0],
                "half_away_score": half_score[1],
                "source": f"{platform_name}_detail",
            }
        )

    first_match = matches[0] if matches else {}
    military = starter.get("militaryInfo") or {}
    issues = []

    if not decoded:
        issues.append(
            f"{platform_name}:{source_order_id}:missing_verified_bet_legs"
        )

    return {
        "platform_id": int(platform_id),
        "platform_name": platform_name,
        "user": {
            "user_id": user_id,
            "nickname": nickname,
            "avatar_url": avatar,
            "avatar_source": avatar_source,
        },
        "order": {
            "platform_order_id": source_order_id,
            "user_id": user_id,
            "nickname": nickname,
            "match_id": first_match.get("matchId"),
            "match_name": first_match.get("team"),
            "league": first_match.get("league"),
            "play_type": "/".join(play_types),
            "pass_summary": "/".join(pass_names),
            "selection": "；".join(selection_text),
            "bet_code": bet_code,
            "odds_text": None,
            "stake": stake,
            "result": result,
            "profit": profit,
            "publish_time": database_datetime(
                parse_epoch_milliseconds_beijing(
                    info.get("createTime")
                )
            ),
            "declaration": info.get("description"),
            "hit_rate": as_float(military.get("hitRate"), 0),
            "profitability": as_float(
                military.get("earningsRate"),
                as_float(list_item.get("profitRate"), 0),
            ),
            "follow_num": as_int(
                info.get("followerNumber"),
                as_int(list_item.get("fansNumber"), 0),
            ),
            "handicap": next(
                (
                    leg["handicap"]
                    for leg in legs
                    if leg["play_type"] == "让球胜平负"
                ),
                0,
            ),
            "platform_bonus": platform_bonus,
            "commission_total": (
                as_float(info.get("commission"), 0) / 100
            ),
            "settlement_status": settlement_status,
            "settled_time": None,
            "expected_bonus": 0,
        },
        "legs": legs,
        "match_results": match_results,
        "issues": issues,
    }
