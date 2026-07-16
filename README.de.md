# RAGScanner

> Scannen Sie Ihr RAG, bevor es Ihre Benutzer tun.

[English](README.md) · [Türkçe](README.tr.md) · **Deutsch** · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner ist ein kostenloses, quelloffenes und lokal ausgerichtetes Werkzeug zur Prüfung von
Sicherheits- und Inhaltsqualitätsrisiken in RAG-Wissensquellen. Die aktuelle technische Alpha scannt
TXT-, Markdown-, textbasierte PDF- und DOCX-Dateien und erstellt Terminal-, JSON- oder eigenständige
HTML-Berichte.

Die aktuelle statische Pipeline überträgt keine Dokumente an entfernte Dienste, benötigt kein LLM,
verwendet keine Telemetrie, folgt keinen Links und führt erkannte Befehle niemals aus.

> [!WARNING]
> Dies ist eine technische Alpha. Ein statischer Scan beweist weder die Sicherheit einer laufenden
> RAG-Anwendung noch bietet er vollständigen Schutz vor Prompt Injection. Ergebnisse sind
> Prüfhinweise und keine Sicherheitsgarantie.

## Was heute funktioniert

| Funktion | Alpha-Status |
|---|---|
| Scans einzelner lokaler Dateien und Ordner | Verfügbar |
| TXT, Markdown, textbasierte PDF und DOCX | Verfügbar |
| Deterministische Normalisierung und Quellenzuordnung | Verfügbar |
| Struktur-, Absatz- und Tokenfenster-Chunking | Verfügbar |
| Versionierte statische RAG-Sicherheitsregeln | Verfügbar |
| Exakte und lexikalische Analyse nahezu identischer Inhalte | Verfügbar |
| Prüfungen der Chunk-Qualität | Verfügbar |
| Terminal-, JSON- und eigenständige HTML-Berichte | Verfügbar |
| Offline ausgeführte statische Scans | Standardverhalten |
| Englischsprachige geführte Einrichtung | Mit einfachem `ragscanner` verfügbar |
| Zustimmungsbasierte Container-OpenWebUI-Erkennung und KB-/Dateimetadateninventar | Verfügbar |
| OCR und semantische Duplikatanalyse | Noch nicht verfügbar |
| Optionaler SQLite-Verlauf und abdeckungsbewusster Vergleich | Über die CLI verfügbar |
| Localhost-Verlaufs-API | Mit `ragscanner serve` verfügbar |
| Dauerhafte SQLite-Static-Scan-Jobs und Worker | Verfügbar |
| Bereichsgebundene authentifizierte asynchrone Scan-/Job-API | Auf Loopback verfügbar |
| Lokales Übersichts- und Warteschlangen-Dashboard | Mit `ragscanner serve` verfügbar |
| Zustimmungsbasierter OpenWebUI-Wissensinhaltskonnektor | Verfügbar |
| Scheduler und Vektorspeicher-Inhaltskonnektoren | Noch nicht verfügbar |
| ModelProvider-/BYOM-Integration | Noch nicht verfügbar |
| CLI für aktive Endpoint-Scans | Nicht verfügbar; nur Core-Verträge |

`ragscanner scan` führt die lokale Pipeline Erkennung → Parsing → Normalisierung → Chunking →
statische Sicherheit → Duplikatanalyse → Chunk-Qualität → Bewertung → Berichterstellung aus.

## Schnellstart für Benutzer

Voraussetzungen: Python 3.12 oder 3.13 und [`uv`](https://docs.astral.sh/uv/).

Installieren Sie die Alpha direkt von GitHub:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Der einfache Befehl öffnet eine englische Einführung. Sie fragt nach der verwendeten Quelle und
kann einen Scan starten. Die automatische Erkennung schlägt nur unmittelbare Ordner mit
RAG-orientierten Namen vor und behandelt allgemeine Ordner wie Documents nicht als RAG-Quellen. Nach ausdrücklicher
Zustimmung prüft die OpenWebUI-Erkennung begrenzte Metadaten verfügbarer Docker-, Podman-, nerdctl-
oder Finch-Runtimes sowie übliche Loopback-Adressen. Ein separat angegebener, nur im Speicher
gehaltener API-Schlüssel kann zugängliche Knowledge Bases sowie verknüpfte und eigenständige/Chat-
Dateimetadaten inventarisieren. Ein separater ausdrücklich genehmigter Job kann zugängliche Dateien
aus einer ausgewählten OpenWebUI-Wissensbasis abrufen und die statische Pipeline ausführen.

Verwalten oder entfernen Sie die Installation mit einem RAGScanner-Befehl:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
```

`uninstall` verlangt eine Bestätigung. Automatisierungen können `ragscanner uninstall --yes`
verwenden. Diese Befehle delegieren ohne Shell an die offizielle `uv tool`-Umgebung; `repair` führt
eine vollständige Neuinstallation unter Beibehaltung der ursprünglichen Quelle und Einstellungen aus.
Unter Windows plant `uninstall` die Entfernung nach dem Beenden des Starters, damit gesperrte Dateien
keinen Zugriffsfehler verursachen.

Nach einer PyPI-Veröffentlichung erfolgt die Installation mit `uv tool install ragscanner`. Bisher
wurde weder ein PyPI-Paket noch ein Release-Tag veröffentlicht.

## Direkte Scans

Setzen Sie Pfade mit Leerzeichen, Klammern oder anderen Shell-Sonderzeichen in Anführungszeichen.

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
ragscanner scan "C:\Users\Example\Downloads\Manual (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/manual.pdf
```

Berichte erstellen:

```bash
ragscanner scan ./knowledge-base --format json --output report.json
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Lokalen Scanverlauf nur bei Bedarf speichern und vergleichen:

```bash
ragscanner scan ./knowledge-base --save-history
ragscanner history list
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner serve
```

Dauerhafte Scans einreihen und den Worker ausführen:

```bash
ragscanner jobs enqueue-scan ./knowledge-base
ragscanner jobs list
ragscanner worker
```

Für einen genehmigten OpenWebUI-Scan bleiben Zugangsdaten außerhalb von SQLite:

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID --credential-ref env:OPENWEBUI_API_KEY --consent-content
ragscanner worker
```

`ragscanner serve` öffnet das lokale Dashboard. Setzen Sie `RAGSCANNER_API_KEY`, um bereichsgebundene
Bearer-authentifizierte Scan-Erstellung und Job-Steuerung über die API zu aktivieren. Der Server
bindet ausschließlich an `127.0.0.1`.

RAGScanner überschreibt standardmäßig keine vorhandene Ausgabedatei.

## Mehrsprachige Eingaben

Vom Produkt erzeugte UI-Beschriftungen, Statustexte, Fehlermeldungen, Abhilfen, Metadaten und die
kanonische Dokumentation sind Englisch. RAG-Quellen bleiben Unicode-nativ und können Türkisch,
Deutsch, Französisch, Chinesisch, Italienisch, Arabisch, Kyrillisch, CJK, Emoji sowie NFC-/NFD-
Dateinamensvarianten enthalten.

Quellenbasierte Belege bleiben für eine zuverlässige Prüfung in ihrer Originalsprache erhalten. Die
lokalisierten README-Dateien sind die einzigen absichtlich nicht englischen Projektdokumente.

## Berichte verstehen

Berichte unterscheiden:

- Abschlussstatus des Scans und teilweise Abdeckung;
- Schweregrad und Konfidenz;
- die Klassifizierungen `confirmed`, `probable`, `ambiguous` und `not_detected`;
- bewertete, teilweise, fehlgeschlagene und `not_assessed` Prüfungen;
- Dokument-, Seiten-, Chunk- und Quellenpositionen, sofern vorhanden;
- Scanner-, Regelpaket- und Richtlinienversionen.

`not_assessed` bedeutet weder gesund noch risikofrei. Eine Sicherheitsbewertung ist keine
Sicherheitsgarantie. Statisches Scannen und autorisierte aktive Endpoint-Tests sind getrennte Modi.

## Datenschutz- und Sicherheitsmodell

- Statische Scans laufen lokal und führen keine versteckten Netzwerkaufrufe aus.
- Dokument- oder Chunk-Inhalte werden nicht an externe KI-Dienste gesendet.
- URLs können geparst, werden aber nicht abgerufen.
- Verdächtige Payloads, Makros, Shell-Befehle und eingebettete Objekte werden nicht ausgeführt.
- Externe DOCX-Beziehungen werden nicht verfolgt; PDF-Anhänge werden nicht extrahiert.
- Belege sind begrenzt, HTML-escaped und bei geheimnisähnlichen Mustern maskiert.
- Absolute Quellpfade sind in Berichten standardmäßig verborgen.
- Es gibt keine Telemetrie, Abrechnung, Abonnements, Berechtigungs- oder Lizenzserver.

Entfernte Konnektoren und optionale Modelle bleiben deaktiviert, bis sie ausdrücklich konfiguriert
und genehmigt werden. OpenWebUI-Inhaltszugriff erfordert eine ausgewählte Wissensbasis, eine externe
Zugangsdatenreferenz und Zustimmung; er ist eine Integration, nicht der Produktkern.

## Installation für Mitwirkende

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner --version
uv run ragscanner doctor
uv run ragscanner scan ./examples/sample-kb
```

Qualitätsprüfungen:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

Alle Fixtures müssen synthetisch sein. Fügen Sie niemals echte Zugangsdaten, Kundendokumente oder
personenbezogene Daten hinzu.

## Architektur

Der Core bleibt unabhängig von UI-Frameworks, Datenbanken, Konnektoren, Modellanbietern und MCP.
Integrationsrollen sind bewusst getrennt:

- `SourceConnector` liest Dokumente, Chunks, Metadaten oder Wissensbasisinhalte.
- `TargetAdapter` sendet autorisierte Black-Box-Tests an eine laufende RAG-/Chat-Anwendung.
- `ModelProvider` stellt ein optionales Analysemodell für RAGScanner selbst bereit.

Die Verwendung von OpenAI, Hugging Face oder OpenWebUI beweist keine vorhandene Retrieval-Funktion.
Ein Ziel heißt nur RAG-Ziel, wenn Dokument-/Vektor-/Index-Retrieval verifiziert wurde.

Ausführliche Grenzen und den aktuellen Status finden Sie in [ARCHITECTURE.md](ARCHITECTURE.md),
[PRODUCT.md](PRODUCT.md) und [docs/status/current.md](docs/status/current.md).

## Roadmap

Die unmittelbare Reihenfolge lautet:

1. Verbleibende Wiederherstellung der Persistenz und Verlauf/Vergleich im API-Maßstab
2. Fähigkeitsgestufte SharePoint-, Web-, SaaS-, Git-, Objektspeicher- und Vektorkonnektoren
3. OpenWebUI-Kompatibilität, inkrementelle Änderungserkennung, Quellenidentität und Secret-Anbieter
4. Dashboard-Scandetails, Vergleich, Konnektoreinstellungen und Barrierefreiheitsabnahme
5. Scheduler, Aufbewahrung und Benachrichtigungen
6. Härtung von Paketierung und Bereitstellung

Geplante Funktionen werden niemals als verfügbar dargestellt. Details stehen in
[ROADMAP.md](ROADMAP.md).

## Mitwirkung und Lizenz

Lesen Sie vor der Mitwirkung [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) und
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Veröffentlichen Sie keine Geheimnisse, Exploits oder
Kundeninhalte in öffentlichen Issues.

RAGScanner steht unter der [Apache License 2.0](LICENSE). Es gibt ein einziges kostenloses,
quelloffenes Produkt: keine Community-/Pro-Aufteilung, keinen kostenpflichtigen Regel-Feed, kein
Abonnement, keine Berechtigungen und kein geschlossenes Modul.
