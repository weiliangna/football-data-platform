from typing import Any, Dict, List, Optional, TypedDict


class PublicMatch(TypedDict, total=False):
    id: str
    code: str
    competition: str
    kickoff: str
    kickoffAt: str
    home: str
    away: str
    homeRank: Optional[int]
    awayRank: Optional[int]
    direction: str
    consensusCount: int
    marketCount: int
    strength: Any
    status: str
    classification: str
    explanation: str
    externalSource: str
    externalId: str


class MarketSeries(TypedDict, total=False):
    id: str
    type: str
    name: str
    selection: str
    rawSelection: str
    line: Any
    delta: Any
    color: str
    values: List[Any]
    labels: List[Any]
    openingProbability: Any
    currentProbability: Any
    openingOdd: Any
    currentOdd: Any
    openingAt: str
    currentAt: str
    directionKey: str
    directionLabel: str
    synchronized: bool
    rawMarketId: str
    rawMarketName: str


JsonObject = Dict[str, Any]
