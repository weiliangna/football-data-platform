from collections import defaultdict
from copy import deepcopy
from threading import Lock
from time import monotonic


GRADE_CACHE_SECONDS = 30.0

GRADE_CONFIG = {
    "weights": {
        "platform_level": 0.04,
        "self_purchase_7d": 0.30,
        "followers_7d": 0.25,
        "orders_7d": 0.03,
        "total_prize": 0.20,
        "profit_7d": 0.05,
        "hit_rate_7d": 0.10,
        "recent_5": 0.05,
    },
    "s_grade": {
        "min_score": 80,
        "min_orders_7d": 5,
        "min_settled_7d": 5,
        "min_profit_7d": 0,
        "min_hit_rate_7d": 0.30,
        "min_recent_5_count": 5,
        "min_recent_5_hit_rate": 0.30,
    },
    "a_grade": {
        "min_score": 60,
        "min_orders_7d": 3,
        "min_settled_7d": 3,
        "min_roi_7d": 0,
    },
}

_grade_cache = {"created_at": 0.0, "rows": None}
_grade_lock = Lock()


def _number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _integer(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def normalize_platform_level(value):
    text = str(value or "").strip()
    if not text:
        return 35.0

    labels = (
        (("至尊", "大师", "殿堂", "钻石"), 100.0),
        (("铂金", "白金"), 90.0),
        (("金牌", "黄金", "金级"), 78.0),
        (("专家", "达人"), 70.0),
        (("银牌", "白银", "银级"), 64.0),
        (("铜牌", "青铜", "铜级"), 50.0),
    )
    for names, score in labels:
        if any(name in text for name in names):
            return score

    digits = "".join(character for character in text if character.isdigit() or character == ".")
    if not digits:
        return 35.0
    try:
        level = float(digits)
    except ValueError:
        return 35.0
    return min(100.0, max(0.0, level * 10.0 if level <= 10 else level))


def percentile_scores(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[_integer(row.get("platform_id"))].append(row)

    scores = {}
    for platform_id, items in groups.items():
        ordered = sorted(items, key=lambda item: _number(item.get(key)))
        count = len(ordered)
        positions = defaultdict(list)
        for index, item in enumerate(ordered):
            positions[_number(item.get(key))].append(index)
        for item in ordered:
            indexes = positions[_number(item.get(key))]
            average_index = sum(indexes) / len(indexes)
            score = 50.0 if count == 1 else average_index / (count - 1) * 100.0
            scores[(platform_id, _integer(item.get("user_id")))] = score
    return scores


def _recent_score(results):
    if not results:
        return 35.0
    weights = (5, 4, 3, 2, 1)[: len(results)]
    possible = sum(weights)
    earned = sum(weight for weight, result in zip(weights, results) if result == "赢")
    base = earned / possible * 100.0 if possible else 0.0
    confidence = min(1.0, len(results) / 5.0)
    return 50.0 + (base - 50.0) * confidence


def calculate_user_grades(rows, manual_grades=None):
    manual_grades = manual_grades or {}
    prepared = []
    for source in rows:
        row = dict(source)
        row["platform_level_value"] = normalize_platform_level(row.get("platform_level"))
        settled = _integer(row.get("settled7d"))
        wins = _integer(row.get("wins7d"))
        settled_stake = _number(row.get("settled_stake7d"))
        settled_prize = _number(row.get("settled_prize7d"))
        profit = settled_prize - settled_stake
        row["profit7d"] = profit
        row["roi7d"] = profit / settled_stake if settled_stake > 0 else None
        row["hit_rate7d"] = wins / settled if settled > 0 else None
        row["last5"] = list(row.get("last5") or [])[:5]
        row["last5_wins"] = sum(1 for result in row["last5"] if result == "赢")
        row["last5_rate"] = row["last5_wins"] / len(row["last5"]) if row["last5"] else None
        prepared.append(row)

    percentile_keys = {
        name: percentile_scores(prepared, field)
        for name, field in {
            "platform_level": "platform_level_value",
            "self_purchase_7d": "self_buy7d",
            "followers_7d": "followers7d",
            "orders_7d": "orders7d",
            "total_prize": "total_prize",
        }.items()
    }

    output = []
    weights = GRADE_CONFIG["weights"]
    for row in prepared:
        key = (_integer(row.get("platform_id")), _integer(row.get("user_id")))
        settled = _integer(row.get("settled7d"))
        wins = _integer(row.get("wins7d"))
        roi = row.get("roi7d")
        if roi is None:
            profit_score = 35.0
        else:
            base = max(0.0, min(100.0, 50.0 + roi * 50.0))
            profit_score = 50.0 + (base - 50.0) * min(1.0, settled / 5.0)
        hit_score = (wins + 1) / (settled + 2) * 100.0 if settled else 35.0
        recent_score = _recent_score(row["last5"])
        score_detail = {
            "platform_level": percentile_keys["platform_level"].get(key, 50.0),
            "self_purchase_7d": percentile_keys["self_purchase_7d"].get(key, 50.0),
            "followers_7d": percentile_keys["followers_7d"].get(key, 50.0),
            "orders_7d": percentile_keys["orders_7d"].get(key, 50.0),
            "total_prize": percentile_keys["total_prize"].get(key, 50.0),
            "profit_7d": profit_score,
            "hit_rate_7d": hit_score,
            "recent_5": recent_score,
        }
        score = min(100, round(sum(score_detail[name] * weight for name, weight in weights.items())))
        s = GRADE_CONFIG["s_grade"]
        a = GRADE_CONFIG["a_grade"]
        if (
            score >= s["min_score"]
            and _integer(row.get("orders7d")) >= s["min_orders_7d"]
            and settled >= s["min_settled_7d"]
            and _number(row.get("profit7d")) > s["min_profit_7d"]
            and (row.get("hit_rate7d") or 0) >= s["min_hit_rate_7d"]
            and len(row["last5"]) >= s["min_recent_5_count"]
            and (row.get("last5_rate") or 0) >= s["min_recent_5_hit_rate"]
        ):
            auto_grade = "S"
        elif (
            score >= a["min_score"]
            and _integer(row.get("orders7d")) >= a["min_orders_7d"]
            and settled >= a["min_settled_7d"]
            and roi is not None
            and roi >= a["min_roi_7d"]
        ):
            auto_grade = "A"
        else:
            auto_grade = "B"

        manual_grade = str(manual_grades.get(key) or "").upper()
        final_grade = manual_grade if manual_grade in {"S", "A", "B"} else auto_grade
        grade_reasons = {
            "s_grade": {
                "score": score >= s["min_score"],
                "orders7d": _integer(row.get("orders7d")) >= s["min_orders_7d"],
                "settled7d": settled >= s["min_settled_7d"],
                "profit7d": _number(row.get("profit7d")) > s["min_profit_7d"],
                "hit_rate7d": (row.get("hit_rate7d") or 0) >= s["min_hit_rate_7d"],
                "recent5_count": len(row["last5"]) >= s["min_recent_5_count"],
                "recent5_hit_rate": (row.get("last5_rate") or 0) >= s["min_recent_5_hit_rate"],
            },
            "a_grade": {
                "score": score >= a["min_score"],
                "orders7d": _integer(row.get("orders7d")) >= a["min_orders_7d"],
                "settled7d": settled >= a["min_settled_7d"],
                "roi7d": roi is not None and roi >= a["min_roi_7d"],
            },
        }
        output.append({
            **row,
            "grade": final_grade,
            "auto_grade": auto_grade,
            "manual_grade": manual_grade,
            "score": score,
            "score_detail": {name: round(value, 2) for name, value in score_detail.items()},
            "grade_reasons": grade_reasons,
            "hit_rate7d": None if row.get("hit_rate7d") is None else round(row["hit_rate7d"] * 100, 2),
            "roi7d": None if roi is None else round(roi * 100, 2),
            "last5_rate": None if row.get("last5_rate") is None else round(row["last5_rate"] * 100, 2),
        })
    return output


def _load_grade_rows(cursor):
    cursor.execute(
        """
        SELECT
            o.platform_id,
            o.user_id,
            MAX(o.nickname) AS nickname,
            COUNT(*) AS orders7d,
            IFNULL(SUM(o.stake),0) AS self_buy7d,
            IFNULL(SUM(o.follow_num),0) AS followers7d,
            SUM(CASE WHEN o.result<>'待开奖' THEN 1 ELSE 0 END) AS settled7d,
            SUM(CASE WHEN o.result='赢' THEN 1 ELSE 0 END) AS wins7d,
            IFNULL(SUM(CASE WHEN o.result<>'待开奖' THEN o.stake ELSE 0 END),0) AS settled_stake7d,
            IFNULL(SUM(CASE WHEN o.result<>'待开奖' THEN o.platform_bonus ELSE 0 END),0) AS settled_prize7d,
            MAX(us.recent_results) AS recent_results
        FROM orders o
        LEFT JOIN user_statistics us
          ON us.platform_id=o.platform_id
         AND us.user_id=o.user_id
        WHERE o.platform_id IN (1,2,3,4)
          AND o.user_id IS NOT NULL
          AND o.user_id<>0
          AND COALESCE(o.publish_time,o.created_time)>=DATE_SUB(NOW(),INTERVAL 7 DAY)
          AND COALESCE(o.publish_time,o.created_time)<=NOW()
        GROUP BY o.platform_id,o.user_id
        """
    )
    rows = [dict(row) for row in cursor.fetchall() or []]
    if not rows:
        return []

    cursor.execute(
        """
        SELECT
            o.platform_id,
            o.user_id,
            IFNULL(SUM(o.platform_bonus),0) AS total_prize,
            MAX(u.level) AS platform_level,
            MAX(ugo.grade) AS manual_grade
        FROM orders o
        LEFT JOIN users u
          ON u.platform_id=o.platform_id
         AND u.platform_user_id=o.user_id
        LEFT JOIN user_grade_overrides ugo
          ON ugo.platform_id=o.platform_id
         AND ugo.user_id=o.user_id
        WHERE o.platform_id IN (1,2,3,4)
          AND o.user_id IS NOT NULL
          AND o.user_id<>0
        GROUP BY o.platform_id,o.user_id
        """
    )
    lifetime = {
        (_integer(row.get("platform_id")), _integer(row.get("user_id"))): row
        for row in cursor.fetchall() or []
    }
    manual = {
        key: row.get("manual_grade")
        for key, row in lifetime.items()
    }

    for row in rows:
        key = (_integer(row.get("platform_id")), _integer(row.get("user_id")))
        row.update(lifetime.get(key) or {})
        row["last5"] = [
            value
            for value in str(row.get("recent_results") or "").split(",")
            if value in {"赢", "输"}
        ][:5]
    return calculate_user_grades(rows, manual)


def load_user_grades(cursor, use_cache=True):
    now = monotonic()
    cached = _grade_cache.get("rows")
    if use_cache and cached is not None and now - _grade_cache["created_at"] < GRADE_CACHE_SECONDS:
        return deepcopy(cached)

    with _grade_lock:
        now = monotonic()
        cached = _grade_cache.get("rows")
        if use_cache and cached is not None and now - _grade_cache["created_at"] < GRADE_CACHE_SECONDS:
            return deepcopy(cached)
        rows = _load_grade_rows(cursor)
        _grade_cache["rows"] = deepcopy(rows)
        _grade_cache["created_at"] = now
        return rows


def invalidate_user_grade_cache():
    with _grade_lock:
        _grade_cache["rows"] = None
        _grade_cache["created_at"] = 0.0
