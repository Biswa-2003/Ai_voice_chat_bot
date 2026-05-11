import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger("analytics")


def build_summary(context: dict) -> dict:
    """Build an analytics summary from a conversation context dict."""
    start = context.get("conversation_start_time")
    if isinstance(start, str):
        start = datetime.fromisoformat(start)
    duration = (datetime.now() - start).total_seconds() if start else 0

    lang_hist = context.get("language_history", [])
    switches = max(0, len(lang_hist) - 1)

    return {
        "conversation_id": context.get("conversation_id"),
        "scenario": context.get("scenario"),
        "duration_seconds": round(duration, 1),
        "turn_count": context.get("turn_count", 0),
        "language_switches": switches,
        "languages_used": list(dict.fromkeys(lang_hist)),
        "topic_categories": context.get("topic_categories", []),
        "scope_violation_count": len(context.get("scope_violations", [])),
        "scope_violations": context.get("scope_violations", []),
        "sentiment": context.get("sentiment", "neutral"),
        "entities_extracted": context.get("entities_extracted", {}),
        "conversation_end_time": datetime.now().isoformat(),
    }


def save_conversation_log(context: dict, log_dir: str = "logs") -> None:
    """Persist conversation turns and analytics summary to the log directory."""
    os.makedirs(log_dir, exist_ok=True)
    cid = context.get("conversation_id", "unknown")

    # Turn-by-turn JSONL
    turns_path = os.path.join(log_dir, f"{cid}.jsonl")
    with open(turns_path, "w", encoding="utf-8") as f:
        for turn in context.get("conversation_history", []):
            f.write(json.dumps(turn, ensure_ascii=False, default=str) + "\n")

    # Analytics summary
    summary_path = os.path.join(log_dir, f"{cid}.analytics.json")
    summary = build_summary(context)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    logger.info(
        "Conversation %s saved: %d turns, %.1fs, %d scope violations",
        cid,
        context.get("turn_count", 0),
        summary["duration_seconds"],
        summary["scope_violation_count"],
    )
