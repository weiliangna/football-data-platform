from copy import deepcopy


MARKET_TYPE_MAP = {
    "win": "WIN_DRAW_LOSS",
    "handicap": "HANDICAP_1X2",
    "asian": "ASIAN_HANDICAP",
    "total": "OVER_UNDER",
    "btts": "BOTH_TEAMS_TO_SCORE",
}


def _object(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def normalize_match(raw):
    source = _object(raw)
    external_id = str(source.get("id") or "")
    fields = (
        "code",
        "competition",
        "kickoff",
        "kickoffAt",
        "home",
        "away",
        "homeRank",
        "awayRank",
        "direction",
        "consensusCount",
        "marketCount",
        "strength",
        "status",
        "classification",
        "explanation",
    )
    match = {key: deepcopy(source.get(key)) for key in fields}
    match.update(
        {
            "id": external_id,
            "externalSource": "scpai",
            "externalId": external_id,
        }
    )
    return match


def normalize_market_series(raw):
    source = _object(raw)
    raw_id = str(source.get("id") or "")
    raw_name = str(source.get("name") or "")
    fields = (
        "selection",
        "rawSelection",
        "line",
        "delta",
        "color",
        "values",
        "labels",
        "openingProbability",
        "currentProbability",
        "openingOdd",
        "currentOdd",
        "openingAt",
        "currentAt",
        "directionKey",
        "directionLabel",
        "synchronized",
    )
    series = {key: deepcopy(source.get(key)) for key in fields}
    series.update(
        {
            "id": raw_id,
            "name": raw_name,
            "type": MARKET_TYPE_MAP.get(raw_id, "UNKNOWN"),
            "rawMarketId": raw_id,
            "rawMarketName": raw_name,
        }
    )
    series["values"] = _list(series.get("values"))
    series["labels"] = _list(series.get("labels"))
    return series


def map_dashboard(raw):
    source = _object(raw)
    return {
        "matches": [normalize_match(item) for item in _list(source.get("queue"))],
        "match": normalize_match(source.get("selectedMatch"))
        if isinstance(source.get("selectedMatch"), dict)
        else None,
        "markets": [
            normalize_market_series(item) for item in _list(source.get("series"))
        ],
        "favoriteIndex": deepcopy(source.get("favoriteIndex")),
        "summary": deepcopy(_object(source.get("summary"))),
        "provider": deepcopy(_object(source.get("provider"))),
        "updatedAt": source.get("updatedAt") or source.get("checkedAt") or "",
        "refreshSeconds": source.get("refreshSeconds"),
    }


def map_context(raw):
    source = _object(raw)
    return {
        "match": normalize_match(source.get("match"))
        if isinstance(source.get("match"), dict)
        else None,
        "motivation": deepcopy(_object(source.get("motivation"))),
        "home": deepcopy(_object(source.get("home"))),
        "away": deepcopy(_object(source.get("away"))),
        "absences": deepcopy(_list(source.get("absences"))),
        "absenceStatus": source.get("absenceStatus") or "",
        "lineupStatus": source.get("lineupStatus") or "",
        "contextError": source.get("contextError") or "",
        "source": deepcopy(source.get("source")),
        "updatedAt": source.get("updatedAt") or "",
        "refreshing": bool(source.get("refreshing")),
        "dataStatus": source.get("dataStatus") or "",
        "newsGeneratedAt": source.get("newsGeneratedAt") or "",
    }


def map_news(raw):
    source = _object(raw)
    items = [deepcopy(item) for item in _list(source.get("items")) if isinstance(item, dict)]
    return {
        "match": normalize_match(source.get("match"))
        if isinstance(source.get("match"), dict)
        else None,
        "generatedAt": source.get("generatedAt") or "",
        "expiresAt": source.get("expiresAt") or "",
        "stale": bool(source.get("stale")),
        "items": items,
        "counts": deepcopy(_object(source.get("counts"))),
        "analysis": deepcopy(source.get("analysis")),
        "categories": sorted(
            {str(item.get("category")) for item in items if item.get("category")}
        ),
    }
