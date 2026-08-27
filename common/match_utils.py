import re
import unicodedata
from difflib import SequenceMatcher


MATCH_SEPARATOR_RE = re.compile(
    r"(?:\s*[:：]\s*|\s*[vV][sS]\s*|\s+[vV]\s+|\s*[-—–/／]\s*)",
)

TEAM_NOISE_RE = re.compile(
    r"足球俱乐部|足球队|俱乐部|球队|footballclub|\bfc\b",
    re.IGNORECASE,
)


def parse_match_name(value):
    raw_name = str(value or "").strip()

    if not raw_name:
        return {
            "raw_name": raw_name,
            "home_team": None,
            "away_team": None,
        }

    parts = MATCH_SEPARATOR_RE.split(raw_name, maxsplit=1)

    if len(parts) != 2:
        return {
            "raw_name": raw_name,
            "home_team": None,
            "away_team": None,
        }

    home_team = parts[0].strip()
    away_team = parts[1].strip()

    if not home_team or not away_team:
        return {
            "raw_name": raw_name,
            "home_team": None,
            "away_team": None,
        }

    return {
        "raw_name": raw_name,
        "home_team": home_team,
        "away_team": away_team,
    }


def split_match_name(match_name):
    parsed = parse_match_name(match_name)
    return (
        parsed["home_team"] or "",
        parsed["away_team"] or "",
    )


def normalize_team_name(value):
    text = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip().lower()
    text = TEAM_NOISE_RE.sub("", text)
    text = re.sub(
        r"[\s\-—–_/／\\:：·•\.，,。()（）\[\]【】]+",
        "",
        text,
    )
    return text


def team_name_similarity(left, right):
    first = normalize_team_name(left)
    second = normalize_team_name(right)
    if not first or not second:
        return 0.0
    if first == second:
        return 1.0
    if min(len(first), len(second)) >= 3 and (
        first in second or second in first
    ):
        return 0.95
    return SequenceMatcher(None, first, second).ratio()


def match_pair_similarity(
    home_team,
    away_team,
    reference_home,
    reference_away,
):
    direct = (
        team_name_similarity(home_team, reference_home)
        + team_name_similarity(away_team, reference_away)
    ) / 2
    reversed_score = (
        team_name_similarity(home_team, reference_away)
        + team_name_similarity(away_team, reference_home)
    ) / 2
    if reversed_score > direct:
        return reversed_score, True
    return direct, False


def build_match_key(
    home_team=None,
    away_team=None,
    match_name=None,
):
    home = str(home_team or "").strip()
    away = str(away_team or "").strip()

    if not home or not away:
        parsed = parse_match_name(match_name)
        home = parsed["home_team"] or ""
        away = parsed["away_team"] or ""

    if not home or not away:
        return ""

    return (
        normalize_team_name(home)
        + "|"
        + normalize_team_name(away)
    )
