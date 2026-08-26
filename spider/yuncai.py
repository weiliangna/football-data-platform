import argparse

from common.platform_registry import default_platform_id
from config.platform_ingestion_config import (
    SourceContractUnavailable,
    get_yuncai_config,
)
from spider.unified_ingestion import (
    DatabaseRepository,
    as_float,
    as_int,
    ingest_records,
    load_detail_map,
    load_json_file,
    parse_datetime,
    preview_repository,
)


PLATFORM_ID = default_platform_id("yuncai")
PLATFORM_NAME = "云彩"

VERIFIED_ENDPOINTS = {
    "hall": "/prod-api/order/order/track/hall",
    "detail": "/prod-api/order/orderDetail/tracking/order/item",
    "profile": "/prod-api/order/order/track/achievements",
    "user_orders": "/prod-api/order/order/user/order/list",
}

PLAY_TYPE_MAP = {
    "进球数": "总进球",
    "总进球数": "总进球",
}


def live_contract_status(environment=None):
    config = get_yuncai_config(environment)
    missing = [
        name
        for name in ("authorization", "cookie", "x_ca_key")
        if not config.get(name)
    ]
    if missing:
        return {
            "ready": False,
            "reason": "missing_secure_environment",
            "missing": missing,
        }
    return {
        "ready": False,
        "reason": "dynamic_signature_contract_missing",
        "missing": [
            "encrypted_query_builder",
            "encrypted_detail_body_builder",
            "x_ca_key_signing_algorithm",
        ],
    }


def parse_list_response(response):
    raw = response if isinstance(response, dict) else {}

    if "data" in raw:
        if as_int(raw.get("code"), 0) != 200:
            raise ValueError("云彩列表响应 code 非 200")
        rows = (raw.get("data") or {}).get("rows") or []
    else:
        if as_int(raw.get("code"), 0) != 200:
            raise ValueError("云彩订单列表响应 code 非 200")
        rows = raw.get("rows") or []

    if not isinstance(rows, list):
        raise ValueError("云彩列表响应缺少 rows")
    return [item for item in rows if isinstance(item, dict)]


def parse_detail_response(response):
    raw = response if isinstance(response, dict) else {}
    if as_int(raw.get("code"), 0) != 200:
        raise ValueError("云彩详情响应 code 非 200")
    data = raw.get("data") or {}
    if not isinstance(data, dict) or not data:
        raise ValueError("云彩详情响应缺少 data")
    return data


def parse_score(value):
    text = str(value or "").strip()
    if ":" not in text:
        return None
    left, right = text.split(":", 1)
    try:
        return int(left), int(right)
    except ValueError:
        return None


def verified_order_result(win_status):
    value = as_int(win_status, -1)
    if value == 2:
        return "赢", "已中奖"
    if value == 1:
        return "输", "未中奖"
    return "待开奖", "待开奖"


def build_record(
    list_item,
    detail_response,
    platform_id=PLATFORM_ID,
):
    data = parse_detail_response(detail_response)
    source_order_id = str(
        data.get("orderId") or list_item.get("orderId") or ""
    ).strip()
    user_id = data.get("userId") or list_item.get("userId")
    nickname = str(
        data.get("nickName") or list_item.get("nickName") or ""
    ).strip()
    avatar = str(
        data.get("imgUrl") or list_item.get("imgUrl") or ""
    ).strip()
    stake = as_float(
        data.get("amount"),
        as_float(list_item.get("amount")),
    )
    platform_bonus = as_float(data.get("returnAmount"), 0)
    result, settlement_status = verified_order_result(
        data.get("winStatus")
    )
    profit = (
        platform_bonus - stake
        if result == "赢"
        else (-stake if result == "输" else 0)
    )
    deadline_time = parse_datetime(data.get("buyEndTime"))
    legs = []
    match_results = []
    selection_text = []
    play_types = []

    for match in data.get("betContentJZCDtoList") or []:
        if not isinstance(match, dict):
            continue
        home = str(match.get("home") or "").strip()
        away = str(match.get("away") or "").strip()
        match_name = f"{home}:{away}" if home and away else ""
        source_code = str(
            match.get("competitionSessions") or ""
        ).strip()
        score = parse_score(match.get("matchScore"))
        half_score = parse_score(match.get("halfMatchScore"))

        for play in match.get("betPlayListList") or []:
            if not isinstance(play, dict):
                continue
            raw_play_type = str(play.get("betPlay") or "").strip()
            play_type = PLAY_TYPE_MAP.get(
                raw_play_type,
                raw_play_type,
            )
            selection = str(play.get("betItem") or "").strip()
            if not play_type or not selection or not match_name:
                continue
            if play_type not in play_types:
                play_types.append(play_type)
            handicap = (
                as_int(play.get("betHandicap"), 0)
                if play_type == "让球胜平负"
                else 0
            )
            leg_result = "待开奖"
            if score is not None:
                leg_result = (
                    "赢"
                    if as_int(play.get("hasHit"), 0) == 1
                    else "输"
                )
            option_detail = [
                {
                    "name": selection,
                    "odds": as_float(play.get("betOdds"), 0),
                }
            ]
            legs.append(
                {
                    "source_match_code": source_code,
                    "match_name": match_name,
                    "home_team": home,
                    "away_team": away,
                    "match_date": None,
                    "league": str(data.get("lotteryName") or ""),
                    "play_type": play_type,
                    "selection": selection,
                    "option_detail": option_detail,
                    "handicap": handicap,
                    "deadline_time": deadline_time,
                    "deadline_source": "buyEndTime",
                    "deadline_exact": bool(deadline_time),
                    "result": leg_result,
                }
            )
            selection_text.append(
                f"{match_name} → {play_type}：{selection}"
            )

        if score is not None and match_name:
            match_results.append(
                {
                    "source_match_code": source_code,
                    "match_name": match_name,
                    "home_team": home,
                    "away_team": away,
                    "match_date": None,
                    "league": str(data.get("lotteryName") or ""),
                    "home_score": score[0],
                    "away_score": score[1],
                    "half_home_score": (half_score or (0, 0))[0],
                    "half_away_score": (half_score or (0, 0))[1],
                    "source": "yuncai_detail",
                }
            )

    first_leg = legs[0] if legs else {}
    issues = []
    if not legs:
        issues.append(
            f"云彩:{source_order_id}:missing_verified_bet_legs"
        )
    if legs:
        issues.append(
            f"云彩:{source_order_id}:match_date_unavailable"
        )

    return {
        "platform_id": int(platform_id),
        "platform_name": PLATFORM_NAME,
        "user": {
            "user_id": user_id,
            "nickname": nickname,
            "avatar_url": avatar,
            "avatar_source": "yuncai_response",
        },
        "order": {
            "platform_order_id": source_order_id,
            "user_id": user_id,
            "nickname": nickname,
            "match_id": None,
            "match_name": first_leg.get("match_name"),
            "league": data.get("lotteryName"),
            "play_type": "/".join(play_types),
            "pass_summary": (
                data.get("betFreePass")
                or data.get("bettingString")
                or list_item.get("passType")
            ),
            "selection": "；".join(selection_text),
            "bet_code": None,
            "odds_text": str(data.get("returnMultiple") or "") or None,
            "stake": stake,
            "result": result,
            "profit": profit,
            "publish_time": None,
            "declaration": data.get("declaration"),
            "hit_rate": as_float(
                data.get("totalHitRate"),
                as_float(list_item.get("hitRate"), 0),
            ),
            "profitability": as_float(
                data.get("totalProfitability"),
                as_float(list_item.get("profitability"), 0),
            ),
            "follow_num": as_int(
                data.get("trackingOrderUserCount"),
                as_int(list_item.get("followNum"), 0),
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
            "commission_total": as_float(data.get("commission"), 0),
            "settlement_status": settlement_status,
            "settled_time": None,
            "expected_bonus": 0,
        },
        "legs": legs,
        "match_results": match_results,
        "issues": issues,
    }


def ingest_responses(
    list_response,
    detail_fetcher,
    repository=None,
    status_recorder=None,
    limit=None,
    platform_id=PLATFORM_ID,
):
    rows = parse_list_response(list_response)
    if limit is not None:
        rows = rows[:max(int(limit), 0)]
    target_repository = repository or preview_repository()

    def fetch(item):
        source_id = str(item.get("orderId") or "").strip()
        if not source_id:
            raise ValueError("云彩列表项缺少 orderId")
        return source_id, detail_fetcher(source_id, item)

    return ingest_records(
        rows,
        fetch,
        lambda item, detail: build_record(
            item,
            detail,
            platform_id=platform_id,
        ),
        int(platform_id),
        PLATFORM_NAME,
        target_repository,
        status_recorder=status_recorder,
    )


def run_live(*_args, **_kwargs):
    status = live_contract_status()
    reason = status["reason"]
    raise SourceContractUnavailable(
        "云彩动态请求签名契约尚未补齐: " + reason
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="云彩采集与已取证响应接管工具"
    )
    parser.add_argument("--platform-id", type=int, default=PLATFORM_ID)
    parser.add_argument("--list-json")
    parser.add_argument("--details-json")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)

    if args.live:
        return run_live(platform_id=args.platform_id)
    if not args.list_json or not args.details_json:
        parser.error("离线模式需要 --list-json 和 --details-json")

    details = load_detail_map(args.details_json)
    repository = (
        DatabaseRepository() if args.write else preview_repository()
    )
    summary = ingest_responses(
        load_json_file(args.list_json),
        lambda source_id, _item: details[source_id],
        repository=repository,
        limit=args.limit,
        platform_id=args.platform_id,
    )
    print(
        "云彩响应处理完成:",
        "总数",
        summary["total_count"],
        "新增",
        summary["new_count"],
        "重复",
        summary["duplicate_count"],
        "失败",
        summary["failed_count"],
    )
    if summary["failed_count"]:
        raise SystemExit(1)
    return summary


def run():
    return main()


if __name__ == "__main__":
    main()
