"""
FocusLens Lite — Summary Utilities
Compute aggregate metrics from a list of FocusEvent objects and
serialize the final API response payload.
"""

import logging
from dataclasses import dataclass

from analyzer import FocusEvent, FOCUS, DISTRACTION, IDLE

logger = logging.getLogger(__name__)


@dataclass
class SessionSummary:
    total_duration: float
    focus_time: float
    distraction_time: float
    idle_time: float
    focus_percentage: float
    distraction_percentage: float
    idle_percentage: float
    event_count: int
    events: list[FocusEvent]

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_duration_seconds": round(self.total_duration, 2),
                "focus_time_seconds": round(self.focus_time, 2),
                "distraction_time_seconds": round(self.distraction_time, 2),
                "idle_time_seconds": round(self.idle_time, 2),
                "focus_percentage": round(self.focus_percentage, 1),
                "distraction_percentage": round(self.distraction_percentage, 1),
                "idle_percentage": round(self.idle_percentage, 1),
                "focus_score": _focus_score(self.focus_percentage),
                "event_count": self.event_count,
            },
            "events": [e.to_dict() for e in self.events],
        }


def _focus_score(focus_pct: float) -> str:
    """Convert focus percentage into a human-readable rating."""
    if focus_pct >= 80:
        return "Excellent"
    if focus_pct >= 60:
        return "Good"
    if focus_pct >= 40:
        return "Fair"
    return "Needs Improvement"


def _safe_percentage(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return (part / total) * 100


def build_summary(events: list[FocusEvent]) -> SessionSummary:
    """
    Aggregate focus / distraction / idle durations from a list of FocusEvents.

    Args:
        events: Classified events produced by analyzer.analyze_scenes().

    Returns:
        A SessionSummary dataclass.

    Raises:
        ValueError: If events list is empty.
    """
    if not events:
        raise ValueError("Cannot build summary from an empty event list.")

    focus_time = sum(e.duration for e in events if e.type == FOCUS)
    distraction_time = sum(e.duration for e in events if e.type == DISTRACTION)
    idle_time = sum(e.duration for e in events if e.type == IDLE)
    total_duration = focus_time + distraction_time + idle_time

    summary = SessionSummary(
        total_duration=total_duration,
        focus_time=focus_time,
        distraction_time=distraction_time,
        idle_time=idle_time,
        focus_percentage=_safe_percentage(focus_time, total_duration),
        distraction_percentage=_safe_percentage(distraction_time, total_duration),
        idle_percentage=_safe_percentage(idle_time, total_duration),
        event_count=len(events),
        events=events,
    )

    logger.info(
        "Session summary: total=%.1fs | focus=%.1f%% | distraction=%.1f%% | idle=%.1f%% | score=%s",
        total_duration,
        summary.focus_percentage,
        summary.distraction_percentage,
        summary.idle_percentage,
        _focus_score(summary.focus_percentage),
    )

    return summary