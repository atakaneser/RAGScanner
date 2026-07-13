"""Deterministic in-memory secret resolver for tests only."""

from ragscanner.domain import TargetError, TargetErrorCategory, TargetErrorDetail


class FakeSecretResolver:
    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets = dict(secrets or {})

    async def resolve(self, reference: str) -> str:
        value = self._secrets.get(reference)
        if value is None:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.AUTHENTICATION,
                    message="configured secret reference could not be resolved",
                )
            )
        return value
