from __future__ import annotations

import os
from twilio.rest import Client


def send_sms(to: str, body: str) -> str:
    """Send an SMS using Twilio and return the message SID."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        raise RuntimeError("Twilio credentials are not fully configured")

    client = Client(account_sid, auth_token)
    message = client.messages.create(from_=from_number, to=to, body=body)
    return message.sid
