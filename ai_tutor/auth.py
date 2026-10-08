import hashlib
from typing import Optional
from uuid import UUID

from ai_tutor.config import Settings
from ai_tutor.errors import unauthenticated


def resolve_principal(authorization: Optional[str], settings: Settings) -> UUID:
    """Only a server-provisioned opaque credential can select the principal."""
    if authorization is None:
        raise unauthenticated()
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise unauthenticated()
    token = parts[1]
    if any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise unauthenticated()
    user_id = settings.credential_users.get(hashlib.sha256(token.encode("ascii")).hexdigest())
    if user_id is None:
        raise unauthenticated()
    return user_id
