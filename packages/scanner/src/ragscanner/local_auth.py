"""Small local administrator bootstrap store for the Host Service dashboard."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalAdministrator:
    username: str
    password_salt: str
    password_hash: str
    session_secret: str


class LocalAdministratorStore:
    """Persist one local dashboard administrator with a memory-hard password hash."""

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / "local-administrator.json"

    @property
    def configured(self) -> bool:
        return self._path.is_file()

    def create(self, username: str, password: str) -> LocalAdministrator:
        normalized = username.strip()
        if not 3 <= len(normalized) <= 80 or any(character.isspace() for character in normalized):
            raise ValueError("username must contain 3 to 80 non-space characters")
        if len(password) < 14:
            raise ValueError("password must contain at least 14 characters")
        if self.configured:
            raise ValueError("the local administrator is already configured")
        salt = os.urandom(16)
        digest = self._derive(password, salt)
        administrator = LocalAdministrator(
            username=normalized,
            password_salt=base64.b64encode(salt).decode("ascii"),
            password_hash=base64.b64encode(digest).decode("ascii"),
            session_secret=base64.b64encode(os.urandom(32)).decode("ascii"),
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(administrator.__dict__, handle, sort_keys=True)
            handle.write("\n")
        return administrator

    def verify(self, username: str, password: str) -> bool:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            administrator = LocalAdministrator(**raw)
            salt = base64.b64decode(administrator.password_salt, validate=True)
            expected = base64.b64decode(administrator.password_hash, validate=True)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return False
        actual = self._derive(password, salt)
        return username == administrator.username and hmac.compare_digest(actual, expected)

    def change_password(self, current_password: str, new_password: str) -> LocalAdministrator:
        """Replace the password atomically and rotate all existing dashboard sessions."""
        administrator = self._read()
        if administrator is None:
            raise ValueError("the local administrator is not configured")
        if not self.verify(administrator.username, current_password):
            raise PermissionError("current password is incorrect")
        if len(new_password) < 14:
            raise ValueError("password must contain at least 14 characters")
        if hmac.compare_digest(current_password, new_password):
            raise ValueError("new password must differ from the current password")
        salt = os.urandom(16)
        updated = LocalAdministrator(
            username=administrator.username,
            password_salt=base64.b64encode(salt).decode("ascii"),
            password_hash=base64.b64encode(self._derive(new_password, salt)).decode("ascii"),
            session_secret=base64.b64encode(os.urandom(32)).decode("ascii"),
        )
        temporary = self._path.with_name(f".{self._path.name}.{os.urandom(8).hex()}.tmp")
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(updated.__dict__, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        finally:
            temporary.unlink(missing_ok=True)
        return updated

    def issue_session(self, username: str) -> str:
        administrator = self._read()
        if administrator is None or username != administrator.username:
            raise ValueError("local administrator is not configured")
        issued = str(int(time.time()))
        payload = f"{username}.{issued}"
        signature = hmac.new(
            base64.b64decode(administrator.session_secret), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return f"{payload}.{signature}"

    def valid_session(self, value: str, *, maximum_age_seconds: int = 8 * 60 * 60) -> bool:
        try:
            username, issued, supplied = value.rsplit(".", 2)
            administrator = self._read()
            if administrator is None or username != administrator.username:
                return False
            if not 0 <= time.time() - int(issued) <= maximum_age_seconds:
                return False
            payload = f"{username}.{issued}"
            expected = hmac.new(
                base64.b64decode(administrator.session_secret),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(supplied, expected)
        except (TypeError, ValueError, OSError):
            return False

    def _read(self) -> LocalAdministrator | None:
        try:
            return LocalAdministrator(**json.loads(self._path.read_text(encoding="utf-8")))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _derive(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
