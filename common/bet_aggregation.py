import re
from datetime import date, datetime


PLAY_ALIASES = {
    "胜平负": "胜平负",
    "让球胜平负": "让球胜平负",
    "让胜平负": "让球胜平负",
    "半全场": "半全场",
    "比分": "比分",
}

STANDARD_PLAYS = (
    "胜平负",
    "让球胜平负",
    "半全场",
    "比分",
)


def normalize_play_type(value):
    text = re.sub(r"\s+", "", str(value or ""))
    return PLAY_ALIASES.get(text, "")


def _split_values(value):
    text = str(value or "").strip()
    for separator in ("，", ",", "|", "、", ";", "；"):
        text = text.replace(separator, "/")
    return [item.strip() for item in text.split("/") if item.strip()]


def _normalize_spf(value, handicap=False):
    text = re.sub(r"\s+", "", str(value or ""))
    if handicap:
        mapping = {
            "胜": "让胜", "主胜": "让胜", "3": "让胜",
            "让胜": "让胜", "让主胜": "让胜",
            "平": "让平", "1": "让平", "让平": "让平",
            "负": "让负", "客胜": "让负", "主负": "让负",
            "0": "让负", "让负": "让负", "让客胜": "让负",
        }
    else:
        mapping = {
            "胜": "主胜", "主胜": "主胜", "3": "主胜",
            "平": "平", "1": "平",
            "负": "主负", "客胜": "主负", "主负": "主负", "0": "主负",
        }
    return mapping.get(text, text)


def _normalize_half_full(value):
    text = re.sub(r"[\s:：\-—–_/／]+", "", str(value or ""))
    replacements = {
        "主胜": "胜", "客胜": "负", "主负": "负",
        "让胜": "胜", "让负": "负", "让平": "平",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    if len(text) == 2 and all(item in "胜平负" for item in text):
        return text
    return text


def _normalize_score(value):
    text = re.sub(r"\s+", "", str(value or ""))
    matched = re.fullmatch(r"(\d+)\s*[-—–:：]\s*(\d+)", text)
    if matched:
        return f"{matched.group(1)}:{matched.group(2)}"
    return text.replace("：", ":")


def normalize_selection_combination(play_type, selection):
    play = normalize_play_type(play_type)
    raw = str(selection or "").strip()
    if not play or not raw:
        return ""

    if play == "半全场":
        values = [raw]
        for separator in ("，", ",", "|", "、", ";", "；"):
            values = [
                part
                for value in values
                for part in value.replace(separator, "|").split("|")
                if part.strip()
            ]
        normalized = [_normalize_half_full(value) for value in values]
    elif play == "比分":
        normalized = [_normalize_score(value) for value in _split_values(raw)]
    else:
        normalized = [
            _normalize_spf(value, handicap=play == "让球胜平负")
            for value in _split_values(raw)
        ]

    unique = []
    for value in normalized:
        if value and value not in unique:
            unique.append(value)
    return "/".join(sorted(unique))


def local_date(value):
    if isinstance(value, datetime):
        return value.astimezone().date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("T", " ").replace("Z", "")
    for pattern in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y%m%d",
    ):
        try:
            return datetime.strptime(text[:19], pattern).date()
        except ValueError:
            continue
    return None


def resolve_archive_date(order, matches=None):
    source = order or {}
    legs = matches or []
    first_match = legs[0] if legs else {}
    candidates = (
        source.get("betEndTime") or source.get("bet_end_time"),
        source.get("planDate") or source.get("plan_date") or source.get("publish_time"),
        first_match.get("day") or first_match.get("match_date"),
        source.get("firstViewedAt") or source.get("first_viewed_at"),
        source.get("firstSyncedAt") or source.get("first_synced_at") or source.get("created_time"),
    )
    for candidate in candidates:
        parsed = local_date(candidate)
        if parsed:
            return parsed.isoformat()
    return ""
