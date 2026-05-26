"""
Placeholder content moderation before video generation.

This is a lightweight keyword heuristic, not a production classifier.
Replace with a hosted moderation API or fine-tuned model for production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ModerationResult:
    allowed: bool
    reason: str | None = None


# Broad keyword groups — intentionally conservative for a placeholder.
_BLOCKED_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "minors_sexual",
        re.compile(
            r"\b(child|children|minor|minors|underage|loli|shota|pedo|preteen|"
            r"kindergarten|schoolkid)\b.*\b(sex|nude|naked|porn|nsfw|erotic)\b|"
            r"\b(sex|nude|naked|porn|nsfw|erotic)\b.*\b(child|children|minor|minors|underage)\b",
            re.IGNORECASE,
        ),
        "Prompts involving minors and sexual content are not allowed.",
    ),
    (
        "explicit_sexual",
        re.compile(
            r"\b(porn|xxx|blowjob|cumshot|anal sex|hardcore sex|explicit sex|"
            r"sexual intercourse|orgy|gangbang)\b",
            re.IGNORECASE,
        ),
        "Explicit sexual content is not allowed.",
    ),
    (
        "graphic_violence",
        re.compile(
            r"\b(gore|dismember|beheading|torture porn|snuff|mutilat|"
            r"graphic murder|blood bath)\b",
            re.IGNORECASE,
        ),
        "Graphic violence is not allowed.",
    ),
    (
        "hate",
        re.compile(
            r"\b(nazi|genocide celebration|racial slur|ethnic cleansing|"
            r"kill all \w+|exterminate \w+)\b",
            re.IGNORECASE,
        ),
        "Hate content is not allowed.",
    ),
    (
        "illegal",
        re.compile(
            r"\b(how to make a bomb|terror attack plan|fentanyl recipe|"
            r"human trafficking|hire a hitman)\b",
            re.IGNORECASE,
        ),
        "Illegal activity instructions are not allowed.",
    ),
    (
        "impersonation",
        re.compile(
            r"\b(deepfake|impersonat).{0,40}\b(celebrity|real person|politician|"
            r"public figure)\b|\b(non.?consensual|without consent).{0,40}\b(face|likeness)\b",
            re.IGNORECASE,
        ),
        "Impersonation of real people without consent is not allowed.",
    ),
]


def moderate_prompt(prompt: str) -> ModerationResult:
    text = (prompt or "").strip()
    if not text:
        return ModerationResult(False, "Prompt cannot be empty.")

    lowered = text.lower()
    for _key, pattern, reason in _BLOCKED_PATTERNS:
        if pattern.search(lowered):
            return ModerationResult(False, reason)
    return ModerationResult(True, None)
