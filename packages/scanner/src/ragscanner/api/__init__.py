"""FastAPI composition for the local RAGScanner application API."""

from ragscanner.api.app import API_VERSION, create_app

__all__ = ["API_VERSION", "create_app"]
