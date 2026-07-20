import re
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


def test_localized_readmes_match_canonical_scope() -> None:
    root = Path(__file__).resolve().parents[2]
    canonical = (root / "README.md").read_text(encoding="utf-8")
    localized_names = [
        "README.tr.md",
        "README.de.md",
        "README.fr.md",
        "README.zh-CN.md",
        "README.it.md",
    ]

    def structure(content: str) -> tuple[int, int, int, int, int]:
        return (
            len(re.findall(r"^## ", content, flags=re.MULTILINE)),
            len(re.findall(r"^\|", content, flags=re.MULTILINE)),
            content.count("```"),
            len(re.findall(r"^- ", content, flags=re.MULTILINE)),
            len(re.findall(r"^\d+\. ", content, flags=re.MULTILINE)),
        )

    shared_commands = [
        "uv tool install git+https://github.com/atakaneser/RAGScanner.git",
        "ragscanner doctor",
        "ragscanner paths",
        "ragscanner install",
        "ragscanner open",
        "ragscanner status",
        "ragscanner update",
        "ragscanner repair",
        "ragscanner uninstall",
        "ragscanner scan PATH",
        "ragscanner jobs list",
        "ragscanner worker",
        "ragscanner history list",
        "ragscanner serve",
        "uv sync --frozen",
        "uv run pytest",
    ]
    canonical_structure = structure(canonical)
    for name in localized_names:
        content = (root / name).read_text(encoding="utf-8")
        assert structure(content) == canonical_structure, name
        for command in shared_commands:
            assert command in content, (name, command)


def test_canonical_markdown_has_no_turkish_product_copy() -> None:
    root = Path(__file__).resolve().parents[2]
    intentional_multilingual = {
        "README.md",
        "README.tr.md",
        "README.de.md",
        "README.fr.md",
        "README.zh-CN.md",
        "README.it.md",
        "docs/cli.md",
        "examples/sample-kb/README.md",
        "examples/sample-kb/healthy-tr.md",
    }
    ignored_roots = {".git", ".venv", "dist", "graphify-out"}
    turkish_characters = set("çğıöşüÇĞİÖŞÜ")

    failures: list[str] = []
    for path in root.rglob("*.md"):
        relative = path.relative_to(root).as_posix()
        if relative in intentional_multilingual or ignored_roots.intersection(path.parts):
            continue
        if not turkish_characters.isdisjoint(path.read_text(encoding="utf-8")):
            failures.append(relative)

    assert failures == []
