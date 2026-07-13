"""Thin adapter for reading explicitly approved local JSON rule-pack files."""

from collections.abc import Iterable
from pathlib import Path

from ragscanner.security.active_test_library import ActiveTestLibrary


def load_active_rule_pack_files(paths: Iterable[Path]) -> ActiveTestLibrary:
    """Read only caller-approved paths; discovery and recursive traversal are intentionally absent."""

    return ActiveTestLibrary.from_texts(path.read_bytes() for path in paths)
