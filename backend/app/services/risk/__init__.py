"""Risk scoring engine package: rule-based fraud risk analysis."""

from app.services.risk.reason_codes import ReasonCode, ReasonCodeDef
from app.services.risk.scoring_engine import (
    FLAGGED_PEER_SCORE_THRESHOLD,
    HUB_SENDER_THRESHOLD,
    INVESTIGATOR_RECOMMENDATION,
    LOW_RISK_NOTE,
    MAX_SCORE,
    OVERSIZED_CLUSTER_RATIO,
    SIM_SWITCH_PHONE_THRESHOLD,
    SIM_SWITCH_WINDOW_HOURS,
    VELOCITY_HOP_THRESHOLD,
    VELOCITY_WINDOW_MINUTES,
    RiskScoreResult,
    RiskScoringEngine,
    TriggeredRule,
)

__all__ = [
    # Reason codes
    "ReasonCode",
    "ReasonCodeDef",
    # Engine
    "RiskScoringEngine",
    "RiskScoreResult",
    "TriggeredRule",
    # Constants
    "INVESTIGATOR_RECOMMENDATION",
    "LOW_RISK_NOTE",
    "MAX_SCORE",
    "VELOCITY_HOP_THRESHOLD",
    "VELOCITY_WINDOW_MINUTES",
    "SIM_SWITCH_PHONE_THRESHOLD",
    "SIM_SWITCH_WINDOW_HOURS",
    "FLAGGED_PEER_SCORE_THRESHOLD",
    "OVERSIZED_CLUSTER_RATIO",
    "HUB_SENDER_THRESHOLD",
]
