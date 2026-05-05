"""
FocusLens Lite — Analyzer Service
Converts raw VideoDB scene descriptions into structured
focus / distraction / idle events using keyword heuristics.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Event type constants ───────────────────────────────────────────────────────
FOCUS = "focus"
DISTRACTION = "distraction"
IDLE = "idle"

# ── Keyword dictionaries (order matters: idle > distraction > focus) ──────────
_IDLE_KEYWORDS: list[str] = [
    "not present", "empty", "no one", "nobody", "absent",
    "lights off", "away from desk", "left the room", "unoccupied",
]

_DISTRACTION_KEYWORDS: list[str] = [
    "phone", "mobile", "smartphone", "texting", "scrolling",
    "looking away", "turned away", "distracted", "yawning", "sleepy",
    "talking to", "conversation", "chatting", "fidgeting",
    "leaning back", "stretched", "eating", "drinking", "staring into space",
    "not focused", "off screen", "daydreaming",
]

_FOCUS_KEYWORDS: list[str] = [
    "focused", "looking at screen", "typing", "reading", "writing",
    "taking notes", "studying", "working", "attentive", "engaged",
    "on task", "using computer", "watching", "concentrating",
]


@dataclass
class FocusEvent:
    type: str          # "focus" | "distraction" | "idle"
    start: float       # seconds
    end: float         # seconds
    description: str   # raw VideoDB description (for transparency)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "duration": round(self.duration, 2),
            "description": self.description,
        }


def _classify_description(description: str) -> str:
    """
    Rule-based classifier.  Priority: idle → distraction → focus → distraction (fallback).

    Args:
        description: Raw text annotation from VideoDB.

    Returns:
        One of FOCUS, DISTRACTION, IDLE.
    """
    text = description.lower()

    for kw in _IDLE_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            return IDLE

    for kw in _DISTRACTION_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            return DISTRACTION

    for kw in _FOCUS_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            return FOCUS

    # If description mentions a person at all but no clear focus signal, call it distraction.
    logger.debug("Ambiguous description — defaulting to distraction: '%s'", description[:80])
    return DISTRACTION


def _merge_consecutive(events: list[FocusEvent]) -> list[FocusEvent]:
    """
    Merge adjacent events of the same type into a single event.
    Reduces noise from frame-by-frame flickering.
    """
    if not events:
        return []

    merged: list[FocusEvent] = [events[0]]
    for evt in events[1:]:
        last = merged[-1]
        if evt.type == last.type:
            # Extend the previous event
            merged[-1] = FocusEvent(
                type=last.type,
                start=last.start,
                end=evt.end,
                description=last.description,
            )
        else:
            merged.append(evt)

    return merged


def analyze_scenes(raw_scenes: list[dict]) -> list[FocusEvent]:
    """
    Convert raw VideoDB scene data into classified FocusEvent objects.

    Args:
        raw_scenes: List of dicts with keys: start (float), end (float), description (str).

    Returns:
        Sorted, merged list of FocusEvent objects.

    Raises:
        ValueError: If raw_scenes is empty.
    """
    if not raw_scenes:
        raise ValueError("No scene data provided for analysis.")

    events: list[FocusEvent] = []

    for scene in raw_scenes:
        start = float(scene.get("start", 0))
        end = float(scene.get("end", start))
        description = scene.get("description", "")

        if end <= start:
            logger.debug("Skipping zero-duration scene at t=%s", start)
            continue

        event_type = _classify_description(description)
        logger.debug("t=%.1f–%.1f → %s | '%s…'", start, end, event_type, description[:60])

        events.append(FocusEvent(type=event_type, start=start, end=end, description=description))

    # Sort chronologically then merge
    events.sort(key=lambda e: e.start)
    merged = _merge_consecutive(events)

    logger.info(
        "Analysis complete: %d raw scenes → %d merged events (%s focus, %s distraction, %s idle)",
        len(raw_scenes),
        len(merged),
        sum(1 for e in merged if e.type == FOCUS),
        sum(1 for e in merged if e.type == DISTRACTION),
        sum(1 for e in merged if e.type == IDLE),
    )

    return merged
