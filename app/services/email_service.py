import smtplib
from email.message import EmailMessage

from flask import current_app


class EmailDeliveryError(RuntimeError):
    """メール送信に失敗した場合の例外。"""


def smtp_configured() -> bool:
    host = (current_app.config.get("SMTP_HOST") or "").strip()
    from_addr = (current_app.config.get("SMTP_FROM") or "").strip()
    return bool(host and from_addr)


def send_magic_link_email(*, to_email: str, verify_url: str) -> None:
    if not smtp_configured():
        raise EmailDeliveryError("SMTP が未設定です。")

    subject = "CommunityComposer ログインリンク"
    body = (
        "CommunityComposer へのログインリンクです。\n\n"
        f"{verify_url}\n\n"
        "このリンクは一定時間のみ有効です。心当たりがない場合は無視してください。"
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = to_email
    message.set_content(body)

    if current_app.config.get("TESTING") and current_app.config.get(
        "MAGIC_LINK_CAPTURE_OUTBOX"
    ):
        outbox = current_app.config.setdefault("MAGIC_LINK_OUTBOX", [])
        outbox.append(
            {
                "to": to_email,
                "subject": subject,
                "body": body,
                "verify_url": verify_url,
            }
        )
        return

    host = current_app.config["SMTP_HOST"]
    port = int(current_app.config.get("SMTP_PORT") or 587)
    username = current_app.config.get("SMTP_USER") or ""
    password = current_app.config.get("SMTP_PASSWORD") or ""
    use_tls = bool(current_app.config.get("SMTP_USE_TLS", True))

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError(f"メール送信に失敗しました: {exc}") from exc
