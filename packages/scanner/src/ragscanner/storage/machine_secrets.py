"""Owner-readable machine secret files referenced by opaque durable identifiers."""

import base64
import binascii
import os
import stat
from pathlib import Path

MAX_SECRET_BYTES = 4096
REFERENCE_PREFIX = "file-secret:"


class MachineSecretStore:
    """Persist credentials outside SQLite with restrictive filesystem permissions."""

    def __init__(self, data_directory: Path) -> None:
        self.root = data_directory.expanduser().resolve() / "secrets"

    def save(self, secret_id: str, value: str) -> str:
        secret = value.strip()
        if not secret or len(secret.encode("utf-8")) > MAX_SECRET_BYTES:
            raise ValueError("API key is empty or exceeds the supported size limit")
        if not secret_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in secret_id
        ):
            raise ValueError("secret identifier is invalid")
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        path = (self.root / secret_id).resolve()
        temporary = path.with_suffix(".tmp")
        temporary.write_text(secret, encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)
        return _reference(path)

    def delete(self, reference: str | None) -> bool:
        path = _path_from_reference(reference) if reference else None
        if path is None or path.parent != self.root or not path.exists():
            return False
        path.unlink()
        return True


def resolve_file_secret_reference(reference: str) -> str:
    """Resolve one opaque file reference after permission, type, and size checks."""

    path = _path_from_reference(reference)
    if path is None or not path.is_absolute() or path.is_symlink():
        raise ValueError("The protected credential reference is invalid")
    try:
        details = path.stat()
    except OSError as error:
        raise ValueError("The protected credential is unavailable") from error
    if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_SECRET_BYTES:
        raise ValueError("The protected credential file is invalid")
    if os.name != "nt" and details.st_mode & 0o077:
        raise ValueError("The protected credential file permissions are too broad")
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ValueError("The protected credential is unavailable") from error
    if not value:
        raise ValueError("The protected credential is empty")
    return value


def _reference(path: Path) -> str:
    encoded = base64.urlsafe_b64encode(str(path).encode("utf-8")).decode("ascii").rstrip("=")
    return f"{REFERENCE_PREFIX}{encoded}"


def _path_from_reference(reference: str | None) -> Path | None:
    if not reference or not reference.startswith(REFERENCE_PREFIX):
        return None
    encoded = reference.removeprefix(REFERENCE_PREFIX)
    try:
        padding = "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    return Path(decoded).expanduser().resolve()
