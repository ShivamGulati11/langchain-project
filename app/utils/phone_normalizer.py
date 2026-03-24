"""E.164 phone number normalization."""
from __future__ import annotations

import phonenumbers


def normalize_phone(raw: str, default_region: str = "IN") -> str:
    """
    Normalize a phone number to E.164 format.
    Raises ValueError on parse failure.
    """
    raw = raw.strip()
    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.NumberParseException as exc:
        raise ValueError(f"Cannot parse phone number {raw!r}: {exc}") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {raw!r}")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
