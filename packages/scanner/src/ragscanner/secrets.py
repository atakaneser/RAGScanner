"""Secret resolution port; concrete operating-system resolvers are intentionally absent."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretResolver(Protocol):
    async def resolve(self, reference: str) -> str: ...
