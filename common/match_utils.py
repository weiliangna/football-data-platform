import re
import unicodedata


MATCH_SEPARATOR_RE = re.compile(
    r"(?:\s*[:：]\s*|\s+[vV](?:[sS])?\s+)",
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
    text = re.sub(r"[\s\-_·•\.]+", "", text)
    text = re.sub(r"[（）()\[\]【】]", "", text)
    return text


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
