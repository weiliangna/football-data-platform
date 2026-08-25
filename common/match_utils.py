import re
import unicodedata


def normalize_team_name(value):
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    text = re.sub(r"[\s\-_·•\.]+", "", text)
    text = re.sub(r"[（）()\[\]【】]", "", text)
    return text


def split_match_name(match_name):
    text = str(match_name or "").strip()
    for sep in (":", "：", " vs ", " VS ", " v ", " V "):
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return text, ""


def build_match_key(home_team=None, away_team=None, match_name=None):
    home = str(home_team or "").strip()
    away = str(away_team or "").strip()
    if not home or not away:
        home, away = split_match_name(match_name)
    if not home or not away:
        return ""
    return normalize_team_name(home) + "|" + normalize_team_name(away)
