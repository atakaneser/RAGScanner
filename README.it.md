# RAGScanner

> Scansiona il tuo RAG prima che lo facciano gli utenti.

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · **Italiano**

RAGScanner è uno strumento gratuito, open source e local-first per ispezionare i rischi di sicurezza
e qualità dei contenuti nelle fonti di conoscenza RAG. L’attuale alpha tecnica analizza file TXT,
Markdown, PDF testuali e DOCX, producendo report da terminale, JSON o HTML autonomi.

L’attuale pipeline statica non trasmette documenti a servizi remoti, non richiede un LLM, non usa
telemetria, non segue link e non esegue mai i comandi rilevati.

> [!WARNING]
> Questa è un’alpha tecnica. Una scansione statica non dimostra che un’applicazione RAG in esecuzione
> sia sicura e non offre protezione completa dalla prompt injection. I risultati sono elementi per la
> revisione, non una garanzia di sicurezza.

## Funzionalità disponibili oggi

| Funzionalità | Stato alpha |
|---|---|
| Scansione di singoli file e cartelle locali | Disponibile |
| TXT, Markdown, PDF testuali e DOCX | Disponibile |
| Normalizzazione deterministica e mappatura delle fonti | Disponibile |
| Chunking per struttura, paragrafo e finestra di token | Disponibile |
| Regole statiche di sicurezza RAG versionate | Disponibile |
| Analisi di duplicati esatti e lessicalmente simili | Disponibile |
| Controlli di qualità dei chunk | Disponibile |
| Report da terminale, JSON e HTML autonomi | Disponibile |
| Scansione statica offline | Comportamento predefinito |
| Onboarding guidato in inglese | Disponibile con il solo `ragscanner` |
| Scoperta OpenWebUI in container e inventario metadata KB/file | Disponibile |
| OCR e analisi semantica dei duplicati | Non ancora disponibile |
| Cronologia SQLite facoltativa e confronto basato sulla copertura | Disponibile dalla CLI |
| API localhost di cronologia | Disponibile con `ragscanner serve` |
| Job durevoli SQLite di scansione statica e worker | Disponibile |
| API asincrona autenticata con scope per scansioni/job | Disponibile su loopback |
| Dashboard locale di panoramica e coda | Disponibile con `ragscanner serve` |
| Agent locale per utente per un dashboard sempre pronto e l’elaborazione durevole dei job | Disponibile |
| Connettore di contenuti knowledge OpenWebUI con consenso | Disponibile |
| Scheduler e connettori di contenuti vector store | Non ancora disponibile |
| Integrazione ModelProvider/BYOM | Non ancora disponibile |
| CLI per scansioni attive degli endpoint | Non disponibile; solo contratti core |

`ragscanner scan` esegue la pipeline locale scoperta → parsing → normalizzazione → chunking →
sicurezza statica → analisi duplicati → qualità chunk → punteggio → reporting.

## Avvio rapido per gli utenti

Requisiti: Python 3.12 o 3.13 e [`uv`](https://docs.astral.sh/uv/).

Installa l’alpha direttamente da GitHub:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Il comando senza argomenti apre un onboarding in inglese. Chiede quale fonte usi e può avviare una
scansione. La scoperta automatica suggerisce solo cartelle immediate con nomi orientati al RAG e non
tratta cartelle generiche come Documents come fonti RAG. Dopo consenso esplicito, la scoperta OpenWebUI
ispeziona metadata limitati dei runtime Docker, Podman, nerdctl o Finch disponibili e gli indirizzi
loopback comuni. Una chiave API fornita separatamente e mantenuta solo in memoria può elencare i
metadata delle knowledge base accessibili e dei file collegati o autonomi/di chat. L’opzione 2
consente all’utente di selezionare una knowledge base OpenWebUI elencata e, dopo un consenso esplicito
separato al contenuto, di eseguire la pipeline statica nello stesso processo locale.

Gestisci o rimuovi l’installazione con un singolo comando RAGScanner:

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner agent install
```

`uninstall` chiede conferma. Le automazioni possono usare `ragscanner uninstall --yes`. Questi
comandi delegano all’ambiente ufficiale `uv tool` senza una shell; `repair` esegue una reinstallazione
completa conservando fonte e impostazioni dell’installazione originale. In Windows, `uninstall`
programma la rimozione dopo la chiusura del launcher, evitando errori di accesso dovuti a eseguibili bloccati.

Dopo una pubblicazione su PyPI, l’installazione userà `uv tool install ragscanner`. Non sono ancora
stati pubblicati né un pacchetto PyPI né un tag di rilascio.

## Scansioni dirette

Racchiudi tra virgolette i percorsi con spazi, parentesi o altri caratteri sensibili alla shell.

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
ragscanner scan "C:\Users\Example\Downloads\Manual (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/manual.pdf
```

Crea report:

```bash
ragscanner scan ./knowledge-base --format json --output report.json
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Salva e confronta la cronologia locale solo quando richiesto:

```bash
ragscanner scan ./knowledge-base --save-history
ragscanner history list
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner serve
```

Accoda scansioni durevoli ed esegui il worker:

```bash
ragscanner jobs enqueue-scan ./knowledge-base
ragscanner jobs list
ragscanner worker
```

Per una scansione OpenWebUI autorizzata, conserva la credenziale fuori da SQLite:

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID --credential-ref env:OPENWEBUI_API_KEY --consent-content
ragscanner worker
```

`ragscanner serve` apre il dashboard locale. Imposta `RAGSCANNER_API_KEY` per abilitare tramite API
la creazione di scansioni e il controllo dei job con autenticazione Bearer e scope. Il server si
lega solo a `127.0.0.1`.

Per impostazione predefinita RAGScanner non sovrascrive un file di output esistente.

## Input multilingue

Etichette UI, testi di stato, messaggi di errore, rimedi, metadati e documentazione canonica generati
dal prodotto sono in inglese. Le fonti RAG restano native Unicode e possono contenere turco, tedesco,
francese, cinese, italiano, arabo, cirillico, CJK, emoji e varianti NFC/NFD dei nomi file.

Le evidenze derivate dalle fonti restano nella lingua originale per preservare la fedeltà dell’audit.
I README localizzati sono gli unici documenti di progetto intenzionalmente non in inglese.

## Comprendere i report

I report distinguono:

- stato di completamento della scansione e copertura parziale;
- gravità e confidenza;
- classificazioni `confirmed`, `probable`, `ambiguous` e `not_detected`;
- controlli valutati, parziali, falliti e `not_assessed`;
- posizioni di documento, pagina, chunk e fonte quando disponibili;
- versioni di scanner, rule pack e policy.

`not_assessed` non significa sano o a rischio zero. Un punteggio di sicurezza non è una garanzia di
sicurezza. Scansione statica e test attivi autorizzati degli endpoint sono modalità separate.

## Modello di privacy e sicurezza

- Le scansioni statiche sono locali e non effettuano chiamate di rete nascoste.
- Il contenuto di documenti o chunk non viene inviato a servizi AI esterni.
- Gli URL possono essere analizzati ma non vengono recuperati.
- Payload sospetti, macro, comandi shell e oggetti incorporati non vengono eseguiti.
- Le relazioni DOCX esterne non vengono seguite; gli allegati PDF non vengono estratti.
- Le evidenze sono limitate, sottoposte a escape HTML e mascherate per pattern simili a secret.
- I percorsi assoluti delle fonti sono nascosti nei report per impostazione predefinita.
- Non esistono telemetria, fatturazione, abbonamenti, entitlement o server di licenza.

I connettori remoti e i modelli opzionali restano disabilitati finché non sono configurati e
autorizzati esplicitamente. L’accesso ai contenuti OpenWebUI richiede una knowledge base selezionata,
un riferimento esterno alla credenziale e consenso esplicito; è un’integrazione, non il core.

## Installazione per i contributori

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner --version
uv run ragscanner doctor
uv run ragscanner scan ./examples/sample-kb
```

Controlli di qualità:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

Tutte le fixture devono essere sintetiche. Non aggiungere mai credenziali reali, documenti dei
clienti o dati personali.

## Architettura

Il core resta indipendente da framework UI, database, connettori, fornitori di modelli e MCP. I ruoli
di integrazione sono deliberatamente separati:

- `SourceConnector` legge documenti, chunk, metadati o contenuti della knowledge base.
- `TargetAdapter` invia test black-box autorizzati a un’applicazione RAG/chat in esecuzione.
- `ModelProvider` fornisce un modello di analisi opzionale per RAGScanner stesso.

Usare OpenAI, Hugging Face o OpenWebUI non dimostra che esista retrieval. Un target è chiamato RAG
solo quando il retrieval da documenti/vector/index è verificato.

Consulta [ARCHITECTURE.md](ARCHITECTURE.md), [PRODUCT.md](PRODUCT.md) e
[docs/status/current.md](docs/status/current.md) per i confini dettagliati e lo stato corrente.

## Roadmap

La sequenza immediata è:

1. Lavori rimanenti su recupero della persistenza e cronologia/confronto su scala API
2. Connettori SharePoint, web, SaaS, Git, object store e vector store per capacità
3. Compatibilità OpenWebUI, rilevamento incrementale, identità delle fonti e provider di secret
4. Dettagli/confronto scansioni, impostazioni dei connettori e accettazione accessibilità del dashboard
5. Scheduler, conservazione e notifiche
6. Rafforzamento di packaging e deployment

Le funzionalità pianificate non sono mai presentate come disponibili. Consulta
[ROADMAP.md](ROADMAP.md) per i dettagli.

## Contributi e licenza

Leggi [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) e
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) prima di contribuire. Non pubblicare secret, exploit o
contenuti dei clienti nelle issue pubbliche.

RAGScanner è distribuito con [Apache License 2.0](LICENSE). Esiste un solo prodotto gratuito e open
source: nessuna divisione Community/Pro, feed di regole a pagamento, abbonamento, entitlement o
modulo chiuso.
