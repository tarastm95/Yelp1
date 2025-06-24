import base64
import hashlib

from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


def get_fernet():
    """Return a Fernet instance built from ``YELP_TOKEN_SECRET``.

    The ``YELP_TOKEN_SECRET`` setting may contain either a valid Fernet key
    (32 url‑safe base64 encoded bytes) or an arbitrary string.  If the provided
    value is not a valid Fernet key we derive one deterministically using
    ``SHA256`` and ``urlsafe_b64encode`` so that any string can be used as the
    secret.
    """

    raw_key = settings.YELP_TOKEN_SECRET
    if isinstance(raw_key, str):
        raw_key = raw_key.encode()

    try:
        decoded = base64.urlsafe_b64decode(raw_key)
    except Exception:  # not base64 encoded
        decoded = None

    # Fallback to a derived key if provided value is not a valid Fernet key
    if decoded is None or len(decoded) != 32:
        raw_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())

    return Fernet(raw_key)


class EncryptedTextField(models.TextField):
    """TextField that encrypts values using Fernet."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        f = get_fernet()
        try:
            return f.decrypt(value.encode()).decode()
        except InvalidToken:
            # value was not encrypted
            return value

    def get_prep_value(self, value):
        if value is None:
            return value
        f = get_fernet()
        return f.encrypt(str(value).encode()).decode()
