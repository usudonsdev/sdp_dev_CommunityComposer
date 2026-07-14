from flask import current_app


def configured_admin_emails() -> set[str]:
    emails: set[str] = set()
    for key in ("AUTH_ADMIN_EMAILS", "AUTH_MOCK_ADMIN_EMAIL"):
        raw = (current_app.config.get(key) or "").strip()
        if not raw:
            continue
        for part in raw.split(","):
            normalized = part.strip().lower()
            if normalized:
                emails.add(normalized)
    return emails


def is_admin_email(email: str) -> bool:
    normalized = (email or "").strip().lower()
    if not normalized:
        return False
    return normalized in configured_admin_emails()
