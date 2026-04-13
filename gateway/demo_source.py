from __future__ import annotations

import os

DEFAULT_MEETING_DEMO_SOURCE = "audio"
LEGACY_VCSUM_DEMO_SOURCE = "vcsum"


def resolve_meeting_demo_source(value: str | None = None) -> str:
    raw_value = value
    if raw_value is None:
        raw_value = os.getenv("MEETING_DEMO_SOURCE", DEFAULT_MEETING_DEMO_SOURCE)

    normalized = raw_value.strip().lower() if isinstance(raw_value, str) else ""
    if normalized == LEGACY_VCSUM_DEMO_SOURCE:
        return LEGACY_VCSUM_DEMO_SOURCE
    return DEFAULT_MEETING_DEMO_SOURCE


def use_vcsum_demo_source(value: str | None = None) -> bool:
    # Keep gateway and startup on the same source-selection rule so audio stays the default.
    return resolve_meeting_demo_source(value) == LEGACY_VCSUM_DEMO_SOURCE