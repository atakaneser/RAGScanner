# RAGScanner

[English](README.md) · [Türkçe](README.tr.md) · **Deutsch** · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner ist ein kostenloses, quelloffenes und lokal ausgerichtetes Werkzeug zur Prüfung von
Sicherheits- und Inhaltsqualitätsrisiken in RAG-Wissensquellen. Die aktuelle technische
Alpha-Version scannt TXT-, Markdown-, textbasierte PDF- und DOCX-Dateien und erzeugt Terminal-,
JSON- oder eigenständige HTML-Berichte.

> [!WARNING]
> Diese Version ist eine technische Alpha. Ein statischer Scan beweist nicht, dass eine laufende
> RAG-Anwendung sicher ist. Ergebnisse sind Prüfhinweise, keine Sicherheitsgarantie.

## Derzeit verfügbar

- Scans einzelner lokaler Dateien und Ordner
- TXT, Markdown, textbasierte PDF und DOCX
- Deterministische Normalisierung, Chunking und Quellenzuordnung
- Versionierte statische Sicherheitsregeln
- Exakte und lexikalische Near-Duplicate-Analyse
- Chunk-Qualitätsprüfungen
- Terminal-, JSON- und eigenständige HTML-Berichte
- Standardmäßig vollständig lokale und offline statische Scans
- Englische geführte Einrichtung mit dem Befehl `ragscanner`

OCR, Persistenz, API, Dashboard, Scheduler, OpenWebUI-Inhaltsconnector und ModelProvider sind noch
nicht verfügbar.

## Installation und erster Scan

Erforderlich sind Python 3.12/3.13 und [`uv`](https://docs.astral.sh/uv/).

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Direkter Scan:

```powershell
ragscanner scan "C:\Users\Example\Documents\Wissensbasis"
```

```bash
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Pfade mit Leerzeichen oder Klammern müssen in Anführungszeichen stehen. Vorhandene Berichte werden
standardmäßig nicht überschrieben.

## Sprache und Datenschutz

Produktoberfläche, Fehlermeldungen, Abhilfetexte und erzeugte technische Metadaten sind Englisch.
Gescannte RAG-Dokumente können jede Unicode-Sprache enthalten. Quellenbelege bleiben für eine
zuverlässige Prüfung in der Originalsprache erhalten.

Statische Scans übertragen keine Dokumente an externe Dienste, benötigen kein LLM, verwenden keine
Telemetrie, folgen keinen Links und führen keine erkannten Befehle aus. Zukünftige Remote-Connectoren
und Modelle werden nur nach ausdrücklicher Konfiguration und Zustimmung aktiviert.

## Architektur und Roadmap

`SourceConnector`, `TargetAdapter` und `ModelProvider` bleiben getrennte Rollen. OpenWebUI ist eine
geplante Integration, nicht der Produktkern.

Die nächsten Schritte sind PDF-/Pfadrobustheit und Report-UX, SQLite-Verlauf, API,
OpenWebUI-Connector, lokales Dashboard und Scheduler. Siehe die kanonische
[englische README](README.md) und [ROADMAP.md](ROADMAP.md).

RAGScanner steht unter der [Apache License 2.0](LICENSE) und bleibt vollständig kostenlos.
