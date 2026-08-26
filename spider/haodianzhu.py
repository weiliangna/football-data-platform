import argparse
import re
from urllib.parse import urlencode

from common.platform_registry import default_platform_id
from config.platform_ingestion_config import (
    get_haodianzhu_config,
    require_values,
)
from spider.platform_pending import load_pending_order_refs
from spider.unified_ingestion import (
    DatabaseRepository,
    as_float,
    as_int,
    ingest_records,
    load_json_file,
    parse_datetime,
    parse_epoch_milliseconds,
    preview_repository,
)


PLATFORM_ID = default_platform_id("haodianzhu")
PLATFORM_NAME = "好店主"


def require_platform_id(value):
    platform_id = as_int(value, 0)
    if platform_id <= 0:
        raise ValueError("好店主缺少已确认的 platform_id")
    return platform_id


API_METHODS = {
    "hall": "fying.pg.billing.recommend.v2",
    "history": "fying.pg.billing.history.v2",
    "profile": "fying.bet.fow.member.info",
    "content": "fying.bp.content.get",
}

COMMON_QUERY = {
    "v": "1.0",
    "aid": "1",
    "cid": "1",
    "cv": "3.0.1",
    "clientType": "5",
    "appName": "cmd",
    "ccv": "304",
}


def _response_json(response):
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("好店主响应不是 JSON 对象")
    if str(data.get("code") or "") != "0000":
        raise RuntimeError("好店主接口返回非成功状态")
    return data


class HaodianzhuClient:
    def __init__(self, config=None, session=None):
        self.config = require_values(
            config or get_haodianzhu_config(),
            PLATFORM_NAME,
            ("sid", "uuid", "cookie", "shop_id"),
        )
        if session is None:
            import requests

            session = requests.Session()
        self.session = session

    def _headers(self):
        return {
            "uuid": self.config["uuid"],
            "sid": self.config["sid"],
            "Cookie": self.config["cookie"],
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://bbbkzu.haodianzhu.com.cn",
            "Referer": "https://bbbkzu.haodianzhu.com.cn/",
            "User-Agent": "Mozilla/5.0",
        }

    def _post(self, method, form):
        query = dict(COMMON_QUERY)
        query["method"] = method
        url = self.config["url"] + "?" + urlencode(query)
        return _response_json(
            self.session.post(
                url,
                headers=self._headers(),
                data=form,
                timeout=20,
            )
        )

    def list_orders(self, page=1, page_size=30):
        return self._post(
            API_METHODS["hall"],
            {
                "memberId": "0",
                "index": "1",
                "lotteryTypeIndex": "0",
                "page": max(int(page), 1),
                "pageSize": max(int(page_size), 1),
                "shopId": self.config["shop_id"],
            },
        )

    def history(self, member_id, page=1, page_size=99):
        return self._post(
            API_METHODS["history"],
            {
                "index": "1",
                "memberId": str(member_id),
                "lotteryType": "",
                "page": max(int(page), 1),
                "pageSize": max(int(page_size), 1),
            },
        )

    def profile(self, member_id):
        return self._post(
            API_METHODS["profile"],
            {"memberId": str(member_id)},
        )

    def order_content(self, plan_id):
        return self._post(
            API_METHODS["content"],
            {"planId": str(plan_id)},
        )


def parse_list_response(response):
    raw = response if isinstance(response, dict) else {}
    if str(raw.get("code") or "") != "0000":
        raise ValueError("好店主列表响应 code 非 0000")
    rows = raw.get("result") or []
    if not isinstance(rows, list):
        raise ValueError("好店主列表响应缺少 result")
    return [item for item in rows if isinstance(item, dict)]


def parse_history_response(response):
    raw = response if isinstance(response, dict) else {}
    if str(raw.get("code") or "") != "0000":
        raise ValueError("好店主历史响应 code 非 0000")
    rows = raw.get("result") or []
    if not isinstance(rows, list):
        raise ValueError("好店主历史响应缺少 result")
    return [item for item in rows if isinstance(item, dict)]


def parse_content_response(response):
    raw = response if isinstance(response, dict) else {}
    if str(raw.get("code") or "") != "0000":
        raise ValueError("好店主内容响应 code 非 0000")
    data = raw.get("result") or {}
    if not isinstance(data, dict):
        raise ValueError("好店主内容响应 result 非对象")
    return data


def parse_profile_response(response):
    raw = response if isinstance(response, dict) else {}
    if str(raw.get("code") or "") != "0000":
        raise ValueError("好店主用户响应 code 非 0000")
    return {
        "memberId": raw.get("memberId"),
        "name": raw.get("nickName"),
        "headImage": raw.get("headImage"),
        "daShenStatistics": raw.get("daShenStatistics") or {},
    }


def parse_score(value):
    text = str(value or "").strip()
    if ":" not in text:
        return None
    left, right = text.split(":", 1)
    try:
        return int(left), int(right)
    except ValueError:
        return None


def resolve_play_type(
    options,
    bet_concede=None,
    play_type_desc=None,
):
    description = str(play_type_desc or "").strip()
    verified_descriptions = {
        "全场比分": "比分",
        "半全场": "半全场",
        "总进球": "总进球",
        "让球胜平负": "让球胜平负",
    }
    if description in verified_descriptions:
        return verified_descriptions[description]

    labels = [str(value or "").strip() for value in options]
    if labels and all(
        re.fullmatch(r"[胜平负]-?[胜平负]", label)
        for label in labels
    ):
        return "半全场"
    if labels and all(
        re.fullmatch(
            r"(?:\d+:\d+|胜其他|平其他|负其他)",
            label,
        )
        for label in labels
    ):
        return "比分"
    if labels and all(
        re.fullmatch(r"(?:[0-6](?:球)?|7\+球?)", label)
        for label in labels
    ):
        return "总进球"
    if labels and all(label.startswith("让") for label in labels):
        return "让球胜平负"
    if bet_concede not in (None, ""):
        return "让球胜平负"
    return None


def verified_order_result(item):
    status = as_int(item.get("status"), -1)
    win_status = as_int(item.get("win_status"), -1)
    if status == 3:
        return "待开奖", "待开奖", None
    if status == 4 and win_status == 3:
        return "赢", "已中奖", None
    return (
        "待开奖",
        "状态待取证",
        (
            f"好店主:{item.get('planId')}:"
            f"unverified_result_status:{status}:{win_status}"
        ),
    )


def build_record(list_item, detail_item, platform_id=PLATFORM_ID):
    platform_id = require_platform_id(platform_id)
    source = detail_item or list_item
    source_order_id = str(
        source.get("planId") or list_item.get("planId") or ""
    ).strip()
    user_id = source.get("memberId") or list_item.get("memberId")
    nickname = str(
        list_item.get("name")
        or source.get("name")
        or source.get("nickName")
        or ""
    ).strip()
    avatar = str(
        list_item.get("headImage")
        or source.get("headImage")
        or ""
    ).strip()
    result, settlement_status, result_issue = verified_order_result(
        source
    )
    stake = as_float(
        source.get("myself_amount"),
        as_float(list_item.get("amount"), 0),
    )
    platform_bonus = as_float(source.get("postax_prize"), 0)
    profit = (
        platform_bonus - stake
        if result == "赢"
        else (-stake if result == "输" else 0)
    )
    legs = []
    match_results = []
    issues = []
    selection_text = []
    play_types = []

    if result_issue:
        issues.append(result_issue)

    for content in source.get("contentList") or []:
        if not isinstance(content, dict):
            continue
        race = content.get("race") or {}
        home = str(race.get("home_team") or "").strip()
        away = str(race.get("guest_team") or "").strip()
        match_name = f"{home}:{away}" if home and away else ""
        option_rows = [
            item
            for item in content.get("itemList") or []
            if isinstance(item, dict)
        ]
        options = [
            str(item.get("text") or "").strip()
            for item in option_rows
            if str(item.get("text") or "").strip()
        ]
        play_type = resolve_play_type(
            options,
            content.get("bet_concede"),
            source.get("play_type_desc"),
        )
        score_source = race.get("zcrace") or race.get("dcrace") or {}
        score = parse_score(score_source.get("final_score"))
        half_score = parse_score(score_source.get("half_score"))
        source_match_code = str(race.get("race_no") or "").strip()
        match_time = parse_datetime(race.get("match_time"))

        if score is not None and match_name:
            match_results.append(
                {
                    "source_match_code": source_match_code,
                    "match_name": match_name,
                    "home_team": home,
                    "away_team": away,
                    "match_date": (
                        match_time.date() if match_time else None
                    ),
                    "league": race.get("league_name"),
                    "home_score": score[0],
                    "away_score": score[1],
                    "half_home_score": (half_score or (0, 0))[0],
                    "half_away_score": (half_score or (0, 0))[1],
                    "source": "haodianzhu_content",
                }
            )

        if play_type is None:
            issues.append(
                f"好店主:{source_order_id}:{source_match_code}:"
                "ambiguous_play_type"
            )
            continue
        if play_type not in play_types:
            play_types.append(play_type)
        handicap = (
            as_int(
                content.get("bet_concede"),
                as_int(score_source.get("concede"), 0),
            )
            if play_type == "让球胜平负"
            else 0
        )
        leg_result = "待开奖"
        if score is not None and option_rows:
            leg_result = (
                "赢"
                if any(bool(item.get("hit")) for item in option_rows)
                else "输"
            )
        selection = "/".join(options)
        deadline_time = parse_datetime(race.get("sell_stop_time"))
        legs.append(
            {
                "source_match_code": source_match_code,
                "match_name": match_name,
                "home_team": home,
                "away_team": away,
                "match_date": (
                    match_time.date() if match_time else None
                ),
                "league": race.get("league_name"),
                "play_type": play_type,
                "selection": selection,
                "option_detail": [
                    {
                        "name": str(item.get("text") or ""),
                        "odds": as_float(item.get("sp"), 0),
                    }
                    for item in option_rows
                ],
                "handicap": handicap,
                "deadline_time": deadline_time,
                "deadline_source": "race.sell_stop_time",
                "deadline_exact": bool(deadline_time),
                "result": leg_result,
            }
        )
        selection_text.append(
            f"{match_name} → {play_type}：{selection}"
        )

    if not source.get("contentList"):
        issues.append(
            f"好店主:{source_order_id}:missing_order_content"
        )

    first_leg = legs[0] if legs else {}
    statistics = (
        list_item.get("daShenStatistics")
        or source.get("daShenStatistics")
        or {}
    )
    hit_rate_source = statistics.get("recentTenHitRate") or {}

    return {
        "platform_id": int(platform_id),
        "platform_name": PLATFORM_NAME,
        "user": {
            "user_id": user_id,
            "nickname": nickname,
            "avatar_url": avatar,
            "avatar_source": "haodianzhu_response",
        },
        "order": {
            "platform_order_id": source_order_id,
            "user_id": user_id,
            "nickname": nickname,
            "match_id": None,
            "match_name": first_leg.get("match_name"),
            "league": (
                source.get("lottery_type_name")
                or list_item.get("lottery_type")
            ),
            "play_type": "/".join(play_types),
            "pass_summary": (
                source.get("passType")
                or list_item.get("pass_type")
            ),
            "selection": "；".join(selection_text),
            "bet_code": None,
            "odds_text": str(
                source.get("max_rate_return") or ""
            ) or None,
            "stake": stake,
            "result": result,
            "profit": profit,
            "publish_time": parse_datetime(
                source.get("create_time")
                or list_item.get("createTime")
            ),
            "declaration": list_item.get("description"),
            "hit_rate": as_float(
                hit_rate_source.get("hitRatePercentage"),
                as_float(list_item.get("recentHitRateValue"), 0),
            ),
            "profitability": as_float(
                statistics.get("recentThirtyReturnRateValue"),
                as_float(list_item.get("overallReturnRateValue"), 0),
            ),
            "follow_num": as_int(list_item.get("follow"), 0),
            "handicap": next(
                (
                    leg["handicap"]
                    for leg in legs
                    if leg["play_type"] == "让球胜平负"
                ),
                0,
            ),
            "platform_bonus": platform_bonus,
            "commission_total": as_float(
                source.get("deduct_amount"),
                0,
            ),
            "settlement_status": settlement_status,
            "settled_time": parse_datetime(
                source.get("send_prize_time")
            ),
            "expected_bonus": 0,
        },
        "legs": legs,
        "match_results": match_results,
        "issues": issues,
    }


def _profile_list_item(profile, ref):
    item = dict(profile or {})
    item["memberId"] = (
        item.get("memberId") or ref.get("user_id")
    )
    item["name"] = item.get("name") or ref.get("nickname")
    return item


def collect_live_items(client, pending_refs, page_size=30):
    hall_rows = parse_list_response(
        client.list_orders(page=1, page_size=page_size)
    )
    hall_by_id = {
        str(item.get("planId") or ""): item
        for item in hall_rows
    }
    pending_by_id = {
        str(ref.get("platform_order_id") or ""): ref
        for ref in pending_refs or []
        if str(ref.get("platform_order_id") or "").strip()
    }
    history_by_id = {}

    member_ids = {
        ref.get("user_id")
        for ref in pending_by_id.values()
        if ref.get("user_id") not in (None, "", 0)
    }
    for member_id in sorted(member_ids, key=str):
        response = client.history(member_id, page=1, page_size=99)
        for item in parse_history_response(response):
            source_id = str(item.get("planId") or "")
            if source_id in pending_by_id:
                history_by_id[source_id] = item

    source_ids = []
    for source_id in list(hall_by_id) + list(pending_by_id):
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)

    profiles = {}
    rows = []
    details = {}

    for source_id in source_ids:
        ref = pending_by_id.get(source_id) or {}
        list_item = dict(hall_by_id.get(source_id) or {})
        member_id = list_item.get("memberId") or ref.get("user_id")
        if not list_item:
            if member_id and member_id not in profiles:
                profiles[member_id] = parse_profile_response(
                    client.profile(member_id)
                )
            list_item = _profile_list_item(
                profiles.get(member_id),
                ref,
            )
            list_item["planId"] = source_id

        detail = dict(list_item)
        detail.update(history_by_id.get(source_id) or {})
        detail.update(
            parse_content_response(client.order_content(source_id))
        )
        detail["planId"] = source_id
        detail["memberId"] = detail.get("memberId") or member_id
        rows.append(list_item)
        details[source_id] = detail

    return rows, details


def ingest_items(
    rows,
    details,
    platform_id=PLATFORM_ID,
    repository=None,
    status_recorder=None,
    limit=None,
):
    if limit is not None:
        rows = list(rows)[:max(int(limit), 0)]
    target_repository = repository or preview_repository()

    def fetch(item):
        source_id = str(item.get("planId") or "").strip()
        if not source_id:
            raise ValueError("好店主列表项缺少 planId")
        return source_id, details[source_id]

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


def ingest_responses(
    list_response,
    history_response,
    platform_id=PLATFORM_ID,
    repository=None,
    status_recorder=None,
    limit=None,
):
    rows = parse_list_response(list_response)
    history = {
        str(item.get("planId") or ""): item
        for item in parse_history_response(history_response)
    }
    details = {
        str(item.get("planId") or ""): item
        for item in rows
    }
    details.update(history)
    return ingest_items(
        rows,
        details,
        platform_id=platform_id,
        repository=repository,
        status_recorder=status_recorder,
        limit=limit,
    )


def run_live(
    platform_id=PLATFORM_ID,
    limit=30,
    repository=None,
    client=None,
    pending_refs=None,
):
    target_client = client or HaodianzhuClient()
    refs = pending_refs
    if refs is None:
        refs = load_pending_order_refs(platform_id)
    rows, details = collect_live_items(
        target_client,
        refs,
        page_size=max(int(limit), 1),
    )
    return ingest_items(
        rows,
        details,
        platform_id=platform_id,
        repository=repository or DatabaseRepository(),
        limit=None,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="好店主采集与已取证响应接管工具"
    )
    parser.add_argument("--platform-id", type=int, default=PLATFORM_ID)
    parser.add_argument("--list-json")
    parser.add_argument("--history-json")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    repository = (
        DatabaseRepository() if args.write else preview_repository()
    )

    if args.live:
        if not args.write:
            raise ValueError("好店主线上采集必须显式使用 --write")
        summary = run_live(
            platform_id=args.platform_id,
            limit=args.limit,
            repository=repository,
        )
    else:
        if not args.list_json or not args.history_json:
            parser.error("离线模式需要 --list-json 和 --history-json")
        summary = ingest_responses(
            load_json_file(args.list_json),
            load_json_file(args.history_json),
            platform_id=args.platform_id,
            repository=repository,
            limit=args.limit,
        )

    print(
        "好店主处理完成:",
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
