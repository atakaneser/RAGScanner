from pathlib import Path

from ragscanner import __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0a1"


def test_canonical_and_localized_readmes_are_present_and_cross_linked() -> None:
    root = Path(__file__).resolve().parents[2]
    names = [
        "README.md",
        "README.tr.md",
        "README.de.md",
        "README.fr.md",
        "README.zh-CN.md",
        "README.it.md",
    ]
    for name in names:
        content = (root / name).read_text(encoding="utf-8")
        assert content.startswith("# RAGScanner")
        for linked_name in names:
            if linked_name != name:
                assert linked_name in content

    canonical = (root / "README.md").read_text(encoding="utf-8")
    assert "**English**" in canonical
    assert "Product-generated UI labels" in canonical
