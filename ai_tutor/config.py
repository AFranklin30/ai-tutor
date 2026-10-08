"""Server-owned demo configuration; no credentials are accepted in request bodies."""

import json
import os
import re
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    # SHA-256 of opaque bearer credential -> existing user UUID.
    credential_users: dict[str, UUID] = field(repr=False)
    max_message_characters: int = 4000

    def __post_init__(self):
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        if self.max_message_characters < 1:
            raise ValueError("Message limit must be positive")
        if any(not re.fullmatch(r"[0-9a-f]{64}", k) for k in self.credential_users):
            raise ValueError("Demo credential keys must be SHA-256 hex digests")
        if any(not isinstance(v, UUID) for v in self.credential_users.values()):
            raise ValueError("Credential mappings must reference UUID users")

    @classmethod
    def from_environment(cls):
        return cls(
            database_url=os.environ["DATABASE_URL"],
            credential_users={
                digest: UUID(user)
                for digest, user in json.loads(os.environ["DEMO_CREDENTIALS_JSON"]).items()
            },
            max_message_characters=int(os.getenv("MAX_MESSAGE_CHARACTERS", "4000")),
        )
