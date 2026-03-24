"""Lead row and schema validators."""
from __future__ import annotations

import re
from typing import Any, Optional


PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")
EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def validate_lead_row(row: dict[str, Any]) -> Optional[str]:
    """
    Validate a single CSV row.
    Returns an error message string if invalid, else None.
    """
    phone = (row.get("phone") or "").strip()
    email = (row.get("email") or "").strip()

    if not phone and not email:
        return "At least one of phone or email is required"

    if phone and not PHONE_RE.match(phone):
        return f"Invalid phone number: {phone!r}"

    if email and not EMAIL_RE.match(email):
        return f"Invalid email address: {email!r}"

    return None
