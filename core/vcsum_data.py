"""Shared VCSum data helpers used by M7 and tests.

Centralizing these helpers avoids duplicate parsing logic across services.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def load_vcsum_data(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL-formatted VCSum records from disk."""
    with open(file_path, "r", encoding="utf-8") as file_obj:
        rows: List[Dict[str, Any]] = []
        for line in file_obj:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def format_transcript(meeting_data: Dict[str, Any]) -> str:
    """Format VCSum meeting records into speaker-tagged transcript text."""
    formatted_lines: List[str] = []

    utterances = meeting_data.get("utterances", [])
    if utterances:
        for utterance in utterances:
            speaker = utterance.get("speaker", "UnknownSpeaker")
            text_data = utterance.get("text", {})
            text = text_data.get("zh", "") if isinstance(text_data, dict) else str(text_data)
            if text.strip():
                formatted_lines.append(f"[{speaker}]: {text}")
        return "\n".join(formatted_lines)

    context = meeting_data.get("context", [])
    speakers = meeting_data.get("speaker", [])
    for paragraph, speaker_id in zip(context, speakers):
        speaker_label = f"Speaker {speaker_id}"
        paragraph_text = " ".join(paragraph)
        formatted_lines.append(f"[{speaker_label}]: {paragraph_text}")

    return "\n".join(formatted_lines)


def get_participants(meeting_data: Dict[str, Any]) -> List[str]:
    """Return unique participant labels while preserving VCSum speaker semantics."""
    participants = set()

    speakers = meeting_data.get("speaker", [])
    if speakers and isinstance(speakers[0], int):
        for speaker_id in set(speakers):
            participants.add(f"Speaker {speaker_id}")
        return sorted(participants)

    topic_segments = meeting_data.get("topic_segments", [])
    for segment in topic_segments:
        speaker = segment.get("speaker", "")
        if speaker:
            participants.add(speaker)

    utterances = meeting_data.get("utterances", [])
    for utterance in utterances:
        speaker = utterance.get("speaker", "")
        if speaker:
            participants.add(speaker)

    return sorted(participants)