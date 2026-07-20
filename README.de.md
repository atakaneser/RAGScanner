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
| Einheitliche Maschineninstallation und Dashboard-Start | `ragscanner install`; einfaches `ragscanner` öffnet das Dashboard |
| Zustimmungsbasierte Container-OpenWebUI-Erkennung und KB-/Dateimetadateninventar | Verfügbar |
| OCR und semantische Duplikatanalyse | Noch nicht verfügbar |
| Optionaler SQLite-Verlauf und abdeckungsbewusster Vergleich | Über die CLI verfügbar |
| Localhost-Verlaufs-API | Mit `ragscanner serve` verfügbar |
| Dauerhafte SQLite-Static-Scan-Jobs und Worker | Verfügbar |
| Bereichsgebundene authentifizierte asynchrone Scan-/Job-API | Auf Loopback verfügbar |
| Lokales Übersichts- und Warteschlangen-Dashboard | Mit `ragscanner serve` verfügbar |
| Dashboard-Berichtsarchiv mit Datums-/Quellenfiltern, Details und Vergleich | Verfügbar |
| Dauerhafte, nicht geheime Quellenprofile und Sources-/Settings-Verwaltung | Verfügbar |
| Lokaler Agent pro Benutzer | Eingestellt; durch den Maschinendienst ersetzt |
| Maschinenlokaler Host Service mit lokaler Administrator-Ersteinrichtung | Verfügbar |
| Metadatenerkennung für Docker, Podman, nerdctl, Finch, Kubernetes und localhost | Verfügbar |
| Zustimmungsbasierter OpenWebUI-Wissensinhaltskonnektor | Verfügbar |
| Scheduler und Vektorspeicher-Inhaltskonnektoren | Noch nicht verfügbar |
| Lokale/entfernte KI-gestützte Berichtsanalyse pro Scan | Verfügbar und standardmäßig aus |
| CLI für aktive Endpoint-Scans | Nicht verfügbar; nur Core-Verträge |

`ragscanner scan` führt die lokale Pipeline Erkennung → Parsing → Normalisierung → Chunking →
statische Sicherheit → Duplikatanalyse → Chunk-Qualität → Bewertung → Berichterstellung aus.

## Schnellstart für Benutzer

Voraussetzungen: Python 3.12 oder 3.13 und [`uv`](https://docs.astral.sh/uv/).

Installieren Sie die Alpha direkt von GitHub:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

`ragscanner install` installiert den Maschinendienst, die isolierte Laufzeit und die lokale
Dashboard-Adresse in einem Schritt und öffnet standardmäßig das Dashboard. Mit
`ragscanner install --mode terminal` wird die Einrichtung in der CLI abgeschlossen. Spätere
Aufrufe von `ragscanner` öffnen immer das Dashboard. Die automatische Erkennung schlägt nur unmittelbare Ordner mit
RAG-orientierten Namen vor und behandelt allgemeine Ordner wie Documents nicht als RAG-Quellen. Nach ausdrücklicher
Zustimmung prüft die OpenWebUI-Erkennung begrenzte Metadaten verfügbarer Docker-, Podman-, nerdctl-
oder Finch-Runtimes sowie übliche Loopback-Adressen. Ein separat angegebener, nur im Speicher
gehaltener API-Schlüssel kann zugängliche Knowledge Bases sowie verknüpfte und eigenständige/Chat-
Dateimetadaten inventarisieren. Option 2 lässt den Benutzer eine aufgeführte OpenWebUI-Wissensbasis
auswählen und nach einer separaten ausdrücklichen Inhaltszustimmung die statische Pipeline im selben
lokalen Prozess ausführen.

Verwalten oder entfernen Sie die Installation mit einem RAGScanner-Befehl:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner status
ragscanner open
```

Diese Befehle benötigen Administratorrechte. `update` und `repair` ersetzen die Maschinenlaufzeit
und starten den Host Service neu. Automatisierung kann `ragscanner uninstall --yes` verwenden.
`uninstall` bewahrt Maschinenberichte und Verlauf, sofern
`--purge-data` nicht angegeben wird.

Installation und Reparatur tragen `%ProgramFiles%\RAGScanner\command` in den Windows-Maschinen-`PATH`
ein. Der stabile Dispatcher `ragscanner.cmd` folgt der aktiven Laufzeitgeneration, sodass neue
Terminals die Maschineninstallation statt eines veralteten `uv`-Tools im Benutzerprofil verwenden.
Öffnen Sie Terminals nach der ersten Installation oder Reparatur erneut.
Installationen vor diesem Maschinendispatcher benötigen gegebenenfalls einen einmaligen Übergang in
einem Administrator-Terminal: `uvx --refresh --from git+https://github.com/atakaneser/RAGScanner.git@main
ragscanner repair`. Dadurch wird der aktuelle Reparaturcode ohne weiteres Benutzer-Tool ausgeführt.

Nach einer PyPI-Veröffentlichung erfolgt die Installation mit `uv tool install ragscanner`. Bisher
wurde weder ein PyPI-Paket noch ein Release-Tag veröffentlicht.

## Direkte Scans

Die KI-gestützte Analyse kann für jeden direkten Scan oder Dashboard-Job einzeln gewählt werden.
Lokale Anbieter sind Ollama, LM Studio, LocalAI und vLLM. Entfernte Optionen umfassen OpenRouter,
OpenAI, NVIDIA NIM, Anthropic, Google Gemini, Groq, Mistral AI, Together AI und benutzerdefinierte
OpenAI-kompatible Endpunkte. KI ist standardmäßig deaktiviert; entfernte Nutzung erfordert die
ausdrückliche Zustimmung für diesen Scan. Nur eine begrenzte, redigierte Berichtszusammenfassung
wird übertragen; Rohdokumente und Befundnachweise bleiben lokal. Anbieterfehler beeinträchtigen den
deterministischen Bericht nicht.
Im Dashboard zeigt die Modellerkennung alle zurückgegebenen Modelle in einer eigenen Auswahl.
Externe API-Schlüssel können im Speicher des laufenden Host Service bereitgestellt oder für
unbeaufsichtigte Nutzung per `env:` referenziert werden. Die Auftragsseite aktualisiert sich alle
zwei Sekunden, trennt Scan-, KI- und Speicherfortschritt und zeigt begrenzte Erfolgs- oder
Fehlerprotokolle mit stabilen Codes; Geheimnisse und rohe Anbieterantworten bleiben ausgeschlossen.

```bash
ragscanner scan ./knowledge-base --ai-provider ollama --ai-model llama3.1:8b
```

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

## Vollständige CLI-Befehlsreferenz

`ragscanner COMMAND --help` zeigt die verbindliche Syntax der installierten Version. Dies ist die
vollständige öffentliche Oberfläche; interne Kompatibilitätsbefehle bleiben verborgen.

### Aufruf und Diagnose

| Befehl | Ausführliche Verwendung |
| --- | --- |
| `ragscanner` | Öffnet nach der Installation das Dashboard, andernfalls wird der Installationsbefehl angezeigt. |
| `ragscanner --version` | Zeigt die installierte CLI-Version. |
| `ragscanner --help` / `ragscanner COMMAND --help` | Zeigt globale oder befehlsspezifische Hilfe, ohne den Rechnerzustand zu ändern. |
| `ragscanner --install-completion` / `--show-completion` | Installiert Shell-Vervollständigung oder zeigt das von Typer unterstützte Skript. |
| `ragscanner doctor` | Prüft Installation, Pfade, Konfiguration, Parser und Laufzeit offline. |
| `ragscanner paths` | Zeigt betriebssystemspezifische Maschinen-, Daten-, Berichts-, temporäre und Legacy-Pfade. |

### Maschineninstallation und Lebenszyklus

| Befehl | Ausführliche Verwendung |
| --- | --- |
| `ragscanner install` | Installiert isolierte Laufzeit und Host-Supervisor (Windows-Startaufgabe unter `SYSTEM`, Linux systemd oder macOS LaunchDaemon), richtet `local.ragscanner.com` und Maschinendaten ein und öffnet das Dashboard. Fordert nötige Administratorrechte an. |
| `ragscanner install --yes` | Bestätigt normale Fragen für unbeaufsichtigte Installation; Betriebssystemrechte können weiter nötig sein. |
| `ragscanner install --mode terminal` | Verwendet Terminal-Einrichtung statt Dashboard. Gültig sind `dashboard` und `terminal`. |
| `ragscanner install --no-open-dashboard` | Installiert vollständig, ohne danach den Browser zu öffnen. |
| `ragscanner open` | Öffnet das installierte Dashboard, ohne einen zweiten Vordergrundserver zu starten. |
| `ragscanner status` | Zeigt Zustand von Installation, Dienst, Dashboard, Laufzeit und Datenpfaden. |
| `ragscanner update` | Lädt den neuesten Stand des offiziellen GitHub-Branches `main`, installiert ihn in die isolierte Maschinenlaufzeit und übergibt den Dienst; Administratorrechte erforderlich. Ein separater `uv tool install`-Befehl ist nicht nötig. |
| `ragscanner repair` | Lädt den neuesten `main`-Stand erneut und repariert Laufzeit, Dienst, Hostnamen, Verzeichnisse und Konfiguration; Administratorrechte erforderlich. Ein separater `uv tool install`-Befehl ist nicht nötig. |
| `ragscanner uninstall` | Entfernt nach Bestätigung Dienst, Laufzeit und Hostnamenzuordnung, behält aber Berichte und Verlauf. |
| `ragscanner uninstall --yes --purge-data` | Entfernt unbeaufsichtigt auch Konfiguration, Berichtsverlauf und verwaltete Daten. Dies ist destruktiv. |

### Direkte lokale Scans

```text
ragscanner scan PATH [OPTIONS]
```

`PATH` ist eine unterstützte Datei oder ein Verzeichnis. Pfade mit Leerzeichen oder Shell-Zeichen
müssen in Anführungszeichen stehen. AI-Anreicherung ist ohne ausdrückliche Auswahl deaktiviert.

| Option | Ausführliche Verwendung |
| --- | --- |
| `--format terminal|json|html`, `--output PATH` | Wählt Terminal oder expliziten JSON/HTML-Export. Exporte benötigen einen Pfad und überschreiben keine Datei. |
| `--include GLOB`, `--exclude GLOB` | Begrenzt die Verzeichnissuche mit wiederholbaren Glob-Mustern. |
| `--recursive` / `--no-recursive` | Schaltet Unterverzeichnisse ein oder aus; standardmäßig aktiv. |
| `--max-file-size BYTES`, `--max-files COUNT` | Setzt positive Sicherheitsgrenzen für Größe und Dateizahl. |
| `--category NAME`, `--exclude-rule ID` | Nimmt Kategorien auf oder Regeln aus; für mehrere Werte wiederholen. |
| `--include-pii` / `--no-include-pii` | Schaltet PII-Regeln der wirksamen Scanrichtlinie ein oder aus. |
| `--min-severity LEVEL`, `--fail-on LEVEL`, `--max-findings COUNT` | Filtert Anzeige, bestimmt den fehlerhaften Exit-Level und begrenzt Befunde. |
| `--config FILE` | Lädt eine explizite Scanrichtlinie zusätzlich zu Standard- und Maschinenkonfiguration. |
| `--security-only`, `--quality-only` | Führt nur Sicherheit oder nur Qualität aus; nicht kombinieren. |
| `--quiet`, `--verbose`, `--no-color` | Steuert Terminaldetails und ANSI-Farbe, nicht das Scanergebnis. |
| `--save-history`, `--history-db FILE` | Speichert einen versionierten Bericht und wählt optional eine andere SQLite-Datenbank. |
| `--ai-provider NAME`, `--ai-model NAME`, `--ai-base-url URL` | Aktiviert Berichtsanreicherung mit Anbieter, Modell und optionalem kompatiblem Endpunkt. |
| `--ai-credential-ref REF`, `--consent-remote-ai` | Löst Secrets extern auf, etwa `env:OPENROUTER_API_KEY`, und erteilt nötige Remote-Zustimmung. |

### AI-Berichtsanreicherung

| Befehl oder Option | Ausführliche Verwendung |
| --- | --- |
| `ragscanner analyze-report REPORT_FILE --model MODEL --output FILE` | Reichert einen vorhandenen unterstützten Bericht an; Modell und Ausgabedatei sind Pflicht. |
| `--provider NAME` | Wählt den Anbieter, standardmäßig `ollama`; lokale und entfernte kompatible Anbieter sind konfigurierbar. |
| `--base-url URL`, `--credential-ref REF` | Überschreibt den Endpunkt und löst das Secret außerhalb von Bericht/Verlauf auf. |
| `--consent-remote` | Erlaubt ausdrücklich die Übertragung einer begrenzten, redigierten Zusammenfassung; Rohdokumente und Belege bleiben lokal. |

### Dauerhafte Aufträge und Worker

| Befehl | Ausführliche Verwendung |
| --- | --- |
| `ragscanner jobs enqueue-scan PATH` | Stellt einen Datei-/Ordnerscan ein; unterstützt `--database`, `--config`, `--idempotency-key`, `--max-attempts` und AI-Optionen. |
| `ragscanner jobs enqueue-openwebui` | Stellt einen OpenWebUI-Scan ein. `--base-url`, `--knowledge-id`, `--credential-ref`, `--consent-content` sind Pflicht; Datenbank-, Idempotenz-, Retry- und AI-Optionen sind möglich. |
| `ragscanner jobs list` | Listet Aufträge mit `--database`, `--limit` (1–200), `--offset` und `--format`. |
| `ragscanner jobs show JOB_ID` | Zeigt Versuche, Zeiten, Ergebnisreferenz und Fehler; `--database` wählt den Speicher. |
| `ragscanner jobs cancel JOB_ID` | Bricht einen noch nicht endgültigen Auftrag ab; `--database` wählt den Speicher. |
| `ragscanner jobs retry JOB_ID` | Erstellt einen neuen Versuch für einen geeigneten fehlgeschlagenen/abgebrochenen Auftrag. |
| `ragscanner worker` | Least und verarbeitet dauerhaft Aufträge aus der Maschinendatenbank. |
| `ragscanner worker --once` | Verarbeitet verfügbare Arbeit einmal und beendet sich. |
| `--database FILE`, `--poll-interval SECONDS`, `--lease-seconds SECONDS`, `--worker-id ID` | Steuert Speicher, Polling (0,1–60), Lease (5–3600) und Worker-Identität. |

### Gespeicherter Berichtsverlauf

| Befehl | Ausführliche Verwendung |
| --- | --- |
| `ragscanner history list` | Listet Scans mit `--database`, `--limit` (1–200), `--offset` und `--format`. |
| `ragscanner history show SCAN_ID` | Rendert einen Bericht mit `--database`, `--format` und optionalem `--verbose`. |
| `ragscanner history compare BASELINE_ID CANDIDATE_ID` | Vergleicht neue, gelöste und unveränderte Befunde; akzeptiert `--database` und `--format`. |
| `ragscanner history delete SCAN_ID` | Löscht nach Bestätigung. `--yes` nur bewusst automatisiert verwenden; `--database` wählt den Speicher. |

### Rendering und Vordergrunddienst

| Befehl | Ausführliche Verwendung |
| --- | --- |
| `ragscanner report SCAN_RESULT` | Rendert neu mit `--format`, `--output`, `--verbose`, Befundfiltern, `--max-findings`, `--include-info`/`--exclude-info` und optional `--show-absolute-paths`. |
| `ragscanner serve` | Startet Dashboard/API für Entwicklung oder Diagnose im Vordergrund auf Loopback; installiert wird der Maschinendienst genutzt. |
| `ragscanner serve --port PORT --history-db FILE` | Wählt Loopback-Port (1–65535) und alternative Verlaufsdatenbank. |

### Spezialisierte Scanner

| Befehl | Ausführliche Verwendung |
| --- | --- |
| `ragscanner security scan PATH` | Führt Sicherheitsregeln aus; unterstützt Regel-/Kategorie-/Schwerefilter, `--format`, `--fail-on`, `--max-findings`, `--include-pii`, `--offline`/`--no-offline`; offline ist Standard. |
| `ragscanner quality scan PATH` | Prüft exakte/nahe Duplikate und Chunk-Qualität mit Einzelschaltern, `--similarity-threshold` (0,5–1,0), Token-Grenzen, `--fail-on` und `--format`. |

### Betriebsregeln

| Regel | Bedeutung |
| --- | --- |
| Exit-Status | Ungültige Eingabe, Betriebsfehler oder Befund ab `--fail-on` erzeugen einen CI-tauglichen Exit ungleich null. |
| Zustimmung | OpenWebUI-Inhaltszugriff und Remote-AI benötigen ausdrückliche Schalter; Metadatensuche gewährt keinen Inhaltszugriff. |
| Zugangsdaten | Secrets extern speichern und nur eine Zugangsdatenreferenz übergeben. |
| Speicher | Nicht angegebene Pfade werden auf die von `ragscanner paths` gezeigten Maschinenorte aufgelöst. |
| Dienste | Dashboard/Worker sind maschinenweit; `serve` und `worker` im Vordergrund dienen der Diagnose. |
| Ausgabesicherheit | Dateien werden nicht überschrieben, absolute Pfade sind standardmäßig verborgen, Belege begrenzt und escaped. |
| Kompatibilität | Optionen und Befehlsausgabe sind Englisch; RAG-Inhalt bleibt in jeder unterstützten Sprache Unicode-nativ. |

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
4. Planung, Aufbewahrung, wiederkehrende Jobs und Lokalisierung der Berichtsoberfläche
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
