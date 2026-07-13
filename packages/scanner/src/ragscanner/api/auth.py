"""In-memory hashed API-key verification and bounded request rates."""

import hashlib
import hmac
import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class ApiPrincipal:
    key_id: str
    scopes: frozenset[str]


class ApiAuthenticationError(PermissionError):
    pass


class ApiAuthorizationError(PermissionError):
    pass


class ApiRateLimitError(RuntimeError):
    pass


class ApiKeyStore:
    """Keep only token digests after composition."""

    def __init__(self, keys: Mapping[str, tuple[str, set[str]]]) -> None:
        self._keys = {
            hashlib.sha256(token.encode("utf-8")).digest(): ApiPrincipal(
                key_id=key_id, scopes=frozenset(scopes)
            )
            for key_id, (token, scopes) in keys.items()
            if token
        }

    def authenticate(self, token: str) -> ApiPrincipal:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for expected, principal in self._keys.items():
            if hmac.compare_digest(digest, expected):
                return principal
        raise ApiAuthenticationError


class SlidingWindowRateLimiter:
    def __init__(
        self,
        *,
        maximum_requests: int = 60,
        window_seconds: float = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.maximum_requests = maximum_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key_id: str) -> None:
        now = self.clock()
        window = self._requests[key_id]
        while window and window[0] <= now - self.window_seconds:
            window.popleft()
        if len(window) >= self.maximum_requests:
            raise ApiRateLimitError
        window.append(now)


def bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.casefold() != "bearer" or not token.strip():
        raise ApiAuthenticationError
    return token.strip()
