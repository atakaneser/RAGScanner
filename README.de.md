# RAGScanner

> Scannen Sie Ihr RAG, bevor es Ihre Benutzer tun.

[English](README.md) · [Türkçe](README.tr.md) · **Deutsch** · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner ist ein kostenloser, quelloffener und lokal ausgerichteter Scanner für Sicherheits- und
Inhaltsqualitätsrisiken in RAG-Wissensquellen. Er verbindet deterministische Prüfungen, dauerhafte
Aufträge, Berichtsverlauf, wiederkehrende Überwachung und optionale KI-Beratung in einem lokalen Dashboard.

> [!WARNING]
> RAGScanner ist eine technische Alpha-Version. Ein statischer Bericht ist eine Prüfhilfe und kein
> Beweis, dass ein laufendes RAG-System sicher oder gegen jede Prompt-Injection geschützt ist.

## Jetzt verfügbar

| Bereich | Aktuelle Fähigkeit |
|---|---|
| Lokale Inhalte | Einzeldateien und auf einen Stammordner begrenzte Verzeichnisse |
| Formate | Markdown, TXT, HTML, PDF, DOCX, PPTX, XLSX, ODT, EPUB, RST, AsciiDoc, CSV/TSV, JSON/JSONL, YAML, XML und Protokolle |
| Externe Quellen | OpenWebUI-Wissensdatenbanken; HTTPS-Seiten, Dokumente, gleichursprüngliche Sitemaps und zugängliche SharePoint-URLs |
| Analyse | Statische Sicherheitsregeln, exakte/lexikalische Duplikate und Chunk-Qualität |
| Berichte | Terminal, JSON, eigenständiges HTML und detaillierte Dashboard-Berichte |
| Verlauf | Lesbare IDs, Filter, Details, Vergleich, Gesundheitstrend und dauerhaftes Löschen |
| Aufträge | Dauerhafte Einzelaufträge, Intervalle, Abbruch, Wiederholung, Fortschritt und sichere Logs |
| KI | Optionale lokale oder ausdrücklich erlaubte externe Beratung; standardmäßig aus |
| Sprachen | Englische, türkische, deutsche, französische, vereinfachte chinesische und italienische Dashboard-Texte |
| Installation | Maschinenlokaler Host Service für Windows, macOS und Linux |

OCR, semantische Duplikatanalyse, authentifizierte Microsoft-Graph-Bibliothekserkennung,
Vektorspeicher-Inhaltskonnektoren, Cron/Kalender, konfigurierbare Aufbewahrung,
Mehrbenutzer-Authentifizierung und Docker-Bereitstellung sind noch nicht verfügbar. Eine erkannte
Plattform bedeutet weder Inhaltszugriff noch Bewertung.

## Installieren und öffnen

Installieren Sie aus dem offiziellen Repository und erstellen Sie den Maschinendienst:

```bash
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

Der Installer öffnet das lokale Dashboard. Später verwenden Sie:

```bash
ragscanner
ragscanner open
ragscanner status
ragscanner paths
```

Installation und Lebenszyklusbefehle benötigen Administratorrechte. Das Dashboard ist standardmäßig
nur über Loopback und nach der Installation unter `http://local.ragscanner.com` erreichbar.

## Aktualisieren, reparieren und entfernen

```bash
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner uninstall --purge-data --yes
```

`update` installiert die aktuelle offizielle `main`-Laufzeit und erhält Einstellungen, Geheimnisse,
Aufträge und Berichte. `repair` erneuert Laufzeit und Dienstregistrierung. `uninstall` erhält lokale
Daten standardmäßig; `--purge-data` löscht sie dauerhaft.

## Inhalte scannen

Das Dashboard ist die empfohlene Oberfläche. Für Automatisierung oder direkte lokale Scans:

```bash
ragscanner scan PATH
ragscanner scan PATH --save-history
ragscanner scan PATH --format html --output report.html
ragscanner serve
```

Der Dialog „Auftrag erstellen“ unterstützt:

- lokale Dateien und Ordner;
- OpenWebUI-Wissensdatenbanken nach ausdrücklicher Inhaltsfreigabe;
- eine HTTPS-Seite oder ein unterstütztes Dokument;
- gleichursprüngliche URL-Sitemaps und eine verschachtelte Sitemap-Index-Ebene;
- direkt zugängliche SharePoint-URLs mit optionaler Bearer-Token-Umgebungsreferenz;
- einmalige Ausführung oder wiederkehrende Intervallüberwachung.

Externe Webscans lehnen Weiterleitungen und fremde Sitemap-Einträge ab, führen keine Skripte aus und
begrenzen Seiten, Antwortgröße und Zeit. Authentifizierte Microsoft-Graph-Site-/Bibliothekserkennung
ist ein separat geplanter Konnektor.

## KI-unterstützte Berichte

KI-Analyse ist optional und ersetzt keine deterministischen Befunde. Die Einstellungen erkennen
installierte Modelle von Ollama, LM Studio, LocalAI oder vLLM, statt veraltete Namen zu behalten.
Externe Anbieter benötigen HTTPS, eine externe Anmeldedatenreferenz und Zustimmung pro Scan.

Nur eine begrenzte, geschwärzte Befundzusammenfassung wird gesendet—keine Rohdokumente oder Beweise.
Die Ausgabe wird gegen ein Schema geprüft. Lehnt ein kompatibler lokaler Server strukturierte Felder
mit HTTP 400 ab, wird einmal der JSON-Kompatibilitätsmodus versucht und andernfalls ein hilfreicher
Fehlercode gespeichert.

## Berichte und Betrieb

Die Übersicht verwendet immer den neuesten verbleibenden abgeschlossenen Bericht. Berichte lassen
sich filtern, zeitlich vergleichen, detailliert prüfen oder nach Bestätigung dauerhaft löschen.
Einmalige Aufträge und wiederkehrende Definitionen erscheinen getrennt. Aktivitätsprotokolle zeigen
stabile Codes und sichere Gründe ohne Anbieter-Rohantworten oder Anmeldedaten.

Nützliche Betriebsbefehle:

```bash
ragscanner jobs list
ragscanner history list
ragscanner worker
```

Weitere Optionen stehen in der [vollständigen CLI-Referenz](docs/cli.md), im
[Dashboard-Leitfaden](docs/dashboard.md) und in der [Fehlerbehebung](docs/troubleshooting.md).

## Datenschutz und Sicherheit

- Lokale statische Scans sind standardmäßig offline und benötigen kein LLM.
- Externer Dokument- oder Modellzugriff erfordert sichtbare Konfiguration und Zustimmung.
- API-Schlüssel liegen außerhalb von SQLite in geschützten Maschinendateien oder `env:`-Referenzen.
- Dauerhafte Aufträge und Berichte enthalten nur undurchsichtige Geheimnisreferenzen.
- Inhalte, Modellausgaben, URLs und Belege werden als nicht vertrauenswürdig und begrenzt behandelt.
- Erzeugte UI-Texte sind lokalisiert; Quellbelege bleiben in ihrer ursprünglichen Sprache.

Lesen Sie [PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md) und den
[SourceConnector-Vertrag](docs/source-connector-contract.md), bevor Sie Integrationen freigeben.

## Für Mitwirkende

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run pytest
```

Führen Sie vor Änderungen Ruff, Formatierung, mypy, Tests und `uv build` gemäß
[CONTRIBUTING.md](CONTRIBUTING.md) aus. Grenzen stehen in [ARCHITECTURE.md](ARCHITECTURE.md), der
aktuelle Umfang in [docs/status/current.md](docs/status/current.md).

## Lizenz

Apache-2.0. Siehe [LICENSE](LICENSE).
