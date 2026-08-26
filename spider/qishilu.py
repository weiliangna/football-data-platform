import argparse
import json

from common.platform_registry import default_platform_id
from config.platform_ingestion_config import (
    get_qishilu_config,
    require_values,
)
from spider.platform_pending import load_pending_order_refs
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


PLATFORM_ID = default_platform_id("qishilu")
PLATFORM_NAME = "启示录"

VERIFIED_MARKETS = {
    "g501": ("胜平负", "p501"),
    "g504": ("半全场", "p504"),
}

ENDPOINTS = {
    "hall": "/portal/follow/list",
    "detail": "/portal/follow/selectFollowProInfo",
    "profile": "/portal/follow/selectUserHome",
}


def _response_json(response):
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("启示录响应不是 JSON 对象")
    if as_int(data.get("code"), 0) != 200:
        raise RuntimeError("启示录接口返回非成功状态")
    return data


class QishiluClient:
    def __init__(self, config=None, session=None):
        self.config = require_values(
            config or get_qishilu_config(),
            PLATFORM_NAME,
            ("authorization",),
        )
        if session is None:
            import requests

            session = requests.Session()
        self.session = session

    def _headers(self):
        value = self.config["authorization"]
        if " " not in value:
            value = "Bearer " + value
        return {
            "Accept": "*/*",
            "Authorization": value,
            "Origin": "https://zs.htycp.cn",
            "Referer": "https://zs.htycp.cn/",
            "User-Agent": "Mozilla/5.0",
        }

    def _get(self, path, params):
        return _response_json(
            self.session.get(
                self.config["base_url"] + path,
                headers=self._headers(),
                params=params,
                timeout=20,
            )
        )

    def list_orders(self, page_num=1, page_size=30):
        return self._get(
            ENDPOINTS["hall"],
            {
                "pageNum": max(int(page_num), 1),
                "pageSize": max(int(page_size), 1),
                "orderCondition": 1,
            },
        )

    def order_detail(self, pro_id):
        return self._get(
            ENDPOINTS["detail"],
            {"proId": str(pro_id)},
        )

    def user_profile(self, user_id):
        return self._get(
            ENDPOINTS["profile"],
            {
                "userId": str(user_id),
                "isCount": 0,
            },
        )


def parse_list_response(response):
    raw = response if isinstance(response, dict) else {}
    if as_int(raw.get("code"), 0) != 200:
        raise ValueError("启示录列表响应 code 非 200")
    rows = raw.get("rows") or []
    if not isinstance(rows, list):
        raise ValueError("启示录列表响应缺少 rows")
    return [item for item in rows if isinstance(item, dict)]


def parse_profile_response(response):
    raw = response if isinstance(response, dict) else {}
    if as_int(raw.get("code"), 0) != 200:
        raise ValueError("启示录用户响应 code 非 200")
    data = raw.get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("启示录用户响应 data 非对象")
    return {
        "userId": data.get("userId"),
        "userName": data.get("nickName"),
        "avatar": data.get("avatar"),
    }


def parse_detail_response(response):
    raw = response if isinstance(response, dict) else {}
    if as_int(raw.get("code"), 0) != 200:
        raise ValueError("启示录详情响应 code 非 200")
    data = raw.get("data") or {}
    if not isinstance(data, dict) or not data:
        raise ValueError("启示录详情响应缺少 data")
    try:
        matches = json.loads(data.get("matchContent") or "[]")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("启示录 matchContent 不是有效 JSON") from exc
    if not isinstance(matches, list):
        raise ValueError("启示录 matchContent 必须是数组")
    return data, matches


def parse_score(value):
    text = str(value or "").strip()
    if ":" not in text:
        return None
    left, right = text.split(":", 1)
    try:
        return int(left), int(right)
    except ValueError:
        return None


def verified_order_result(data):
    cal_state = as_int(data.get("proCalState"), -1)
    award = as_int(data.get("proTicketAward"), -1)
    if cal_state != 1:
        return "待开奖", "待开奖", None
    if award == 2:
        return "赢", "已中奖", None
    if award == 0:
        return "输", "未中奖", None
    return (
        "待开奖",
        "状态待取证",
        f"启示录:{data.get('id')}:unverified_award_code:{award}",
    )


def normalize_option(value):
    return {
        "胜": "主胜",
        "平": "平",
        "负": "主负",
    }.get(str(value or "").strip(), str(value or "").strip())


def build_record(
    list_item,
    detail_response,
    platform_id=PLATFORM_ID,
):
    data, matches = parse_detail_response(detail_response)
    source_order_id = str(
        data.get("id") or list_item.get("proId") or ""
    ).strip()
    user_id = data.get("userId") or list_item.get("userId")
    nickname = str(
        data.get("userName") or list_item.get("userName") or ""
    ).strip()
    avatar = str(list_item.get("avatar") or "").strip()
    stake = as_float(
        data.get("bets"),
        as_float(list_item.get("bets"), 0),
    )
    platform_bonus = as_float(data.get("proAwardMoney"), 0)
    result, settlement_status, result_issue = verified_order_result(data)
    profit = (
        platform_bonus - stake
        if result == "赢"
        else (-stake if result == "输" else 0)
    )
    deadline_time = parse_datetime(data.get("stopSaleTime"))
    legs = []
    match_results = []
    issues = []
    selection_text = []
    play_types = []

    if result_issue:
        issues.append(result_issue)

    for match in matches:
        if not isinstance(match, dict):
            continue
        home = str(match.get("home") or "").strip()
        away = str(match.get("guest") or "").strip()
        match_name = f"{home}:{away}" if home and away else ""
        source_match_code = str(match.get("matchId") or "").strip()
        match_date = match.get("openingDate")
        score = parse_score(match.get("score"))
        half_score = parse_score(match.get("halfScore"))

        if score is not None and match_name:
            match_results.append(
                {
                    "source_match_code": source_match_code,
                    "match_name": match_name,
                    "home_team": home,
                    "away_team": away,
                    "match_date": match_date,
                    "league": match.get("group"),
                    "home_score": score[0],
                    "away_score": score[1],
                    "half_home_score": (half_score or (0, 0))[0],
                    "half_away_score": (half_score or (0, 0))[1],
                    "source": "qishilu_matchContent",
                }
            )

        markets = match.get("proCon") or {}
        for market_key, option_rows in markets.items():
            contract = VERIFIED_MARKETS.get(str(market_key))
            if contract is None:
                issues.append(
                    f"启示录:{source_order_id}:{source_match_code}:"
                    f"unverified_market:{market_key}"
                )
                continue
            play_type, actual_result_key = contract
            selected_rows = [
                row
                for row in option_rows or []
                if isinstance(row, dict) and bool(row.get("is"))
            ]
            if not selected_rows:
                continue
            if play_type not in play_types:
                play_types.append(play_type)
            selected_raw = [
                str(row.get("na") or "").strip()
                for row in selected_rows
                if str(row.get("na") or "").strip()
            ]
            selection = "/".join(
                normalize_option(value) for value in selected_raw
            )
            leg_result = "待开奖"
            actual_result = str(
                match.get(actual_result_key) or ""
            ).strip()
            if score is not None and actual_result:
                leg_result = (
                    "赢" if actual_result in selected_raw else "输"
                )
            legs.append(
                {
                    "source_match_code": source_match_code,
                    "match_name": match_name,
                    "home_team": home,
                    "away_team": away,
                    "match_date": match_date,
                    "league": match.get("group"),
                    "play_type": play_type,
                    "selection": selection,
                    "option_detail": [
                        {
                            "name": normalize_option(row.get("na")),
                            "odds": as_float(row.get("s"), 0),
                        }
                        for row in selected_rows
                    ],
                    "handicap": 0,
                    "deadline_time": deadline_time,
                    "deadline_source": "stopSaleTime",
                    "deadline_exact": bool(deadline_time),
                    "result": leg_result,
                }
            )
            selection_text.append(
                f"{match_name} → {play_type}：{selection}"
            )

    if not legs:
        issues.append(
            f"启示录:{source_order_id}:missing_verified_bet_legs"
        )

    first_leg = legs[0] if legs else {}
    return {
        "platform_id": int(platform_id),
        "platform_name": PLATFORM_NAME,
        "user": {
            "user_id": user_id,
            "nickname": nickname,
            "avatar_url": avatar,
            "avatar_source": "qishilu_list",
        },
        "order": {
            "platform_order_id": source_order_id,
            "user_id": user_id,
            "nickname": nickname,
            "match_id": None,
            "match_name": first_leg.get("match_name"),
            "league": data.get("proGameCodeName"),
            "play_type": "/".join(play_types),
            "pass_summary": data.get("manner"),
            "selection": "；".join(selection_text),
            "bet_code": data.get("dataContent"),
            "odds_text": str(
                list_item.get("oneMultiple") or ""
            ) or None,
            "stake": stake,
            "result": result,
            "profit": profit,
            "publish_time": parse_datetime(
                data.get("createTime") or list_item.get("payTime")
            ),
            "declaration": (
                data.get("proClaim") or list_item.get("proClaim")
            ),
            "hit_rate": as_float(list_item.get("hitRate"), 0),
            "profitability": as_float(
                list_item.get("profitMargin"),
                0,
            ),
            "follow_num": 0,
            "handicap": 0,
            "platform_bonus": platform_bonus,
            "commission_total": as_float(
                data.get("proCommission"),
                0,
            ),
            "settlement_status": settlement_status,
            "settled_time": parse_datetime(
                data.get("proAwardDistributionTime")
            ),
            "expected_bonus": 0,
        },
        "legs": legs,
        "match_results": match_results,
        "issues": issues,
    }


def _merge_live_items(client, rows, pending_refs):
    merged = []
    seen = set()
    profiles = {}

    for item in rows:
        source_id = str(item.get("proId") or "").strip()
        if source_id and source_id not in seen:
            seen.add(source_id)
            merged.append(item)

    for ref in pending_refs or []:
        source_id = str(
            ref.get("platform_order_id") or ""
        ).strip()
        if not source_id or source_id in seen:
            continue
        user_id = ref.get("user_id")
        profile = {}
        if user_id not in (None, "", 0):
            if user_id not in profiles:
                profiles[user_id] = parse_profile_response(
                    client.user_profile(user_id)
                )
            profile = profiles[user_id]
        merged.append(
            {
                "proId": source_id,
                "userId": user_id,
                "userName": (
                    profile.get("userName") or ref.get("nickname")
                ),
                "avatar": profile.get("avatar"),
            }
        )
        seen.add(source_id)
    return merged


def ingest_responses(
    list_response,
    detail_fetcher,
    platform_id=PLATFORM_ID,
    repository=None,
    status_recorder=None,
    limit=None,
):
    rows = parse_list_response(list_response)
    if limit is not None:
        rows = rows[:max(int(limit), 0)]
    target_repository = repository or preview_repository()

    def fetch(item):
        source_id = str(item.get("proId") or "").strip()
        if not source_id:
            raise ValueError("启示录列表项缺少 proId")
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


def run_live(
    platform_id=PLATFORM_ID,
    limit=30,
    repository=None,
    client=None,
    pending_refs=None,
):
    target_client = client or QishiluClient()
    refs = pending_refs
    if refs is None:
        refs = load_pending_order_refs(platform_id)
    list_response = target_client.list_orders(
        page_num=1,
        page_size=max(int(limit), 1),
    )
    rows = _merge_live_items(
        target_client,
        parse_list_response(list_response),
        refs,
    )
    wrapped = {
        "code": 200,
        "rows": rows,
    }
    return ingest_responses(
        wrapped,
        lambda source_id, _item: target_client.order_detail(
            source_id
        ),
        platform_id=platform_id,
        repository=repository or DatabaseRepository(),
        limit=None,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="启示录采集与已取证响应接管工具"
    )
    parser.add_argument("--platform-id", type=int, default=PLATFORM_ID)
    parser.add_argument("--list-json")
    parser.add_argument("--details-json")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    repository = (
        DatabaseRepository() if args.write else preview_repository()
    )

    if args.live:
        if not args.write:
            raise ValueError("启示录线上采集必须显式使用 --write")
        summary = run_live(
            platform_id=args.platform_id,
            limit=args.limit,
            repository=repository,
        )
    else:
        if not args.list_json or not args.details_json:
            parser.error("离线模式需要 --list-json 和 --details-json")
        details = load_detail_map(args.details_json)
        summary = ingest_responses(
            load_json_file(args.list_json),
            lambda source_id, _item: details[source_id],
            platform_id=args.platform_id,
            repository=repository,
            limit=args.limit,
        )

    print(
        "启示录处理完成:",
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


if __name__ == "__main__":
    main()
