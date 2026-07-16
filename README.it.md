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
| Installazione macchina unificata e apertura dashboard | `ragscanner install`; `ragscanner` apre il dashboard |
| Scoperta OpenWebUI in container e inventario metadata KB/file | Disponibile |
| OCR e analisi semantica dei duplicati | Non ancora disponibile |
| Cronologia SQLite facoltativa e confronto basato sulla copertura | Disponibile dalla CLI |
| API localhost di cronologia | Disponibile con `ragscanner serve` |
| Job durevoli SQLite di scansione statica e worker | Disponibile |
| API asincrona autenticata con scope per scansioni/job | Disponibile su loopback |
| Dashboard locale di panoramica e coda | Disponibile con `ragscanner serve` |
| Archivio report con filtri data/fonte, dettaglio e confronto | Disponibile |
| Profili fonte persistenti senza secret e gestione Sources/Settings | Disponibile |
| Agent locale per utente | Ritirato; sostituito dal servizio di macchina |
| Host Service locale alla macchina con inizializzazione di un amministratore locale | Disponibile |
| Scoperta metadata Docker, Podman, nerdctl, Finch, Kubernetes e localhost | Disponibile |
| Connettore di contenuti knowledge OpenWebUI con consenso | Disponibile |
| Scheduler e connettori di contenuti vector store | Non ancora disponibile |
| Analisi report assistita da IA locale/remota per scansione | Disponibile e disattivata per impostazione predefinita |
| CLI per scansioni attive degli endpoint | Non disponibile; solo contratti core |

`ragscanner scan` esegue la pipeline locale scoperta → parsing → normalizzazione → chunking →
sicurezza statica → analisi duplicati → qualità chunk → punteggio → reporting.

## Avvio rapido per gli utenti

Requisiti: Python 3.12 o 3.13 e [`uv`](https://docs.astral.sh/uv/).

Installa l’alpha direttamente da GitHub:

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

`ragscanner install` installa in un solo passaggio il servizio di macchina, il runtime isolato e
l’indirizzo del dashboard locale, quindi apre il dashboard per impostazione predefinita. Usa
`ragscanner install --mode terminal` per completare la configurazione nella CLI. Le esecuzioni
successive di `ragscanner` aprono sempre il dashboard. La scoperta automatica suggerisce solo cartelle immediate con nomi orientati al RAG e non
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
ragscanner status
ragscanner open
```

Questi comandi richiedono privilegi di amministratore. `update` e `repair` sostituiscono il runtime
di macchina e riavviano il Host Service. L’automazione può usare `ragscanner uninstall --yes`.
`uninstall` conserva report e cronologia della macchina a
meno che non venga specificato `--purge-data`.

Dopo una pubblicazione su PyPI, l’installazione userà `uv tool install ragscanner`. Non sono ancora
stati pubblicati né un pacchetto PyPI né un tag di rilascio.

## Scansioni dirette

L’analisi assistita da IA può essere scelta separatamente per ogni scansione diretta o job del
dashboard. I provider locali sono Ollama, LM Studio, LocalAI e vLLM. Le opzioni remote includono
OpenRouter, OpenAI, NVIDIA NIM, Anthropic, Google Gemini, Groq, Mistral AI, Together AI ed endpoint
personalizzati compatibili con OpenAI. L’IA è disattivata per impostazione predefinita; l’uso remoto
richiede il consenso esplicito per quella scansione. Viene inviato solo un riepilogo limitato e
redatto; documenti grezzi e prove dei rilievi restano locali. Un errore del provider non compromette
il report deterministico.

```bash
ragscanner scan ./knowledge-base --ai-provider ollama --ai-model llama3.1:8b
```

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

## Riferimento completo dei comandi CLI

`ragscanner COMMAND --help` mostra la sintassi autorevole della versione installata. L’elenco seguente
copre l’interfaccia pubblica completa; i comandi interni di compatibilità restano nascosti.

### Avvio e diagnostica

| Comando | Uso dettagliato |
| --- | --- |
| `ragscanner` | Apre la dashboard se installato; altrimenti mostra il comando di installazione. |
| `ragscanner --version` | Mostra la versione CLI installata. |
| `ragscanner --help` / `ragscanner COMMAND --help` | Mostra l’aiuto globale o specifico senza modificare la macchina. |
| `ragscanner --install-completion` / `--show-completion` | Installa il completamento shell o mostra lo script supportato da Typer. |
| `ragscanner doctor` | Diagnostica offline installazione, percorsi, configurazione, parser e runtime. |
| `ragscanner paths` | Mostra percorsi di configurazione macchina, dati, report, temporanei e legacy per il sistema operativo. |

### Installazione macchina e ciclo di vita

| Comando | Uso dettagliato |
| --- | --- |
| `ragscanner install` | Installa runtime isolato e servizio di sistema, configura `local.ragscanner.com`, inizializza i dati e apre la dashboard. Richiede elevazione quando serve. |
| `ragscanner install --yes` | Accetta le richieste ordinarie per installazioni non presidiate; l’elevazione può restare necessaria. |
| `ragscanner install --mode terminal` | Usa il setup da terminale invece della dashboard. Modi validi: `dashboard` e `terminal`. |
| `ragscanner install --no-open-dashboard` | Installa tutto senza aprire il browser al termine. |
| `ragscanner open` | Apre la dashboard installata senza avviare un secondo server in primo piano. |
| `ragscanner status` | Mostra stato di installazione, servizio, dashboard, runtime e percorsi dati. |
| `ragscanner update` | Sostituisce il runtime isolato e riavvia il servizio macchina; richiede privilegi amministrativi. |
| `ragscanner repair` | Ripristina runtime, servizio, hostname, directory e configurazione; richiede privilegi amministrativi. |
| `ragscanner uninstall` | Dopo conferma rimuove servizio, runtime e hostname conservando report e cronologia. |
| `ragscanner uninstall --yes --purge-data` | Rimuove senza interazione anche configurazione, cronologia e dati gestiti. È distruttivo. |

### Scansioni locali dirette

```text
ragscanner scan PATH [OPTIONS]
```

`PATH` può essere un file supportato o una directory. Racchiudere tra virgolette i percorsi sensibili
alla shell. La scansione è locale e l’arricchimento AI è disattivato salvo scelta esplicita.

| Opzione | Uso dettagliato |
| --- | --- |
| `--format terminal|json|html`, `--output PATH` | Seleziona terminale o export JSON/HTML esplicito. L’export richiede un percorso e non sovrascrive file. |
| `--include GLOB`, `--exclude GLOB` | Limita la scoperta con pattern glob ripetibili. |
| `--recursive` / `--no-recursive` | Abilita o disabilita le sottodirectory; attivo per impostazione predefinita. |
| `--max-file-size BYTES`, `--max-files COUNT` | Imposta limiti positivi per dimensione e numero di file. |
| `--category NAME`, `--exclude-rule ID` | Include categorie o esclude regole; ripetere per più valori. |
| `--include-pii` / `--no-include-pii` | Abilita o disabilita le regole PII nella policy effettiva. |
| `--min-severity LEVEL`, `--fail-on LEVEL`, `--max-findings COUNT` | Filtra la visualizzazione, imposta la soglia di errore e limita i risultati. |
| `--config FILE` | Carica una policy esplicita oltre a valori predefiniti e configurazione macchina. |
| `--security-only`, `--quality-only` | Esegue solo sicurezza o solo qualità; non combinarli. |
| `--quiet`, `--verbose`, `--no-color` | Controlla dettagli terminale e colore ANSI senza cambiare i risultati. |
| `--save-history`, `--history-db FILE` | Salva un report versionato e sceglie opzionalmente un altro database SQLite. |
| `--ai-provider NAME`, `--ai-model NAME`, `--ai-base-url URL` | Attiva l’arricchimento con provider, modello ed endpoint compatibile scelti. |
| `--ai-credential-ref REF`, `--consent-remote-ai` | Risolve esternamente un segreto come `env:OPENROUTER_API_KEY` e registra il consenso remoto richiesto. |

### Arricchimento AI dei report

| Comando o opzione | Uso dettagliato |
| --- | --- |
| `ragscanner analyze-report REPORT_FILE --model MODEL --output FILE` | Arricchisce un report esistente supportato; modello e output sono obbligatori. |
| `--provider NAME` | Seleziona il provider, predefinito `ollama`; sono configurabili provider locali e remoti compatibili. |
| `--base-url URL`, `--credential-ref REF` | Sostituisce l’endpoint e risolve il segreto fuori da report e cronologia. |
| `--consent-remote` | Consente esplicitamente l’invio di un riepilogo limitato e mascherato; documenti grezzi e prove restano locali. |

### Job persistenti e worker

| Comando | Uso dettagliato |
| --- | --- |
| `ragscanner jobs enqueue-scan PATH` | Accoda una scansione file/cartella; accetta `--database`, `--config`, `--idempotency-key`, `--max-attempts` e opzioni AI. |
| `ragscanner jobs enqueue-openwebui` | Accoda OpenWebUI. Richiede `--base-url`, `--knowledge-id`, `--credential-ref`, `--consent-content`; accetta database, idempotenza, retry e AI. |
| `ragscanner jobs list` | Elenca i job con `--database`, `--limit` (1–200), `--offset` e `--format`. |
| `ragscanner jobs show JOB_ID` | Mostra tentativi, tempi, riferimento risultato ed errore; `--database` sceglie lo storage. |
| `ragscanner jobs cancel JOB_ID` | Annulla un job non terminale; `--database` sceglie lo storage. |
| `ragscanner jobs retry JOB_ID` | Crea un nuovo tentativo per un job fallito/annullato idoneo. |
| `ragscanner worker` | Prende in lease ed esegue continuamente i job dal database macchina. |
| `ragscanner worker --once` | Elabora una volta il lavoro disponibile e termina. |
| `--database FILE`, `--poll-interval SECONDS`, `--lease-seconds SECONDS`, `--worker-id ID` | Controlla storage, polling (0,1–60), lease (5–3600) e identità worker. |

### Cronologia dei report

| Comando | Uso dettagliato |
| --- | --- |
| `ragscanner history list` | Elenca scansioni con `--database`, `--limit` (1–200), `--offset` e `--format`. |
| `ragscanner history show SCAN_ID` | Renderizza un report con `--database`, `--format` e `--verbose` opzionale. |
| `ragscanner history compare BASELINE_ID CANDIDATE_ID` | Confronta risultati nuovi, risolti e invariati; accetta `--database` e `--format`. |
| `ragscanner history delete SCAN_ID` | Elimina dopo conferma. Usare `--yes` solo per automazione intenzionale; `--database` sceglie lo storage. |

### Rendering e servizio in primo piano

| Comando | Uso dettagliato |
| --- | --- |
| `ragscanner report SCAN_RESULT` | Rigenera con `--format`, `--output`, `--verbose`, filtri, `--max-findings`, `--include-info`/`--exclude-info` e `--show-absolute-paths` opzionale. |
| `ragscanner serve` | Avvia dashboard/API su loopback in primo piano per sviluppo o diagnostica; l’uso installato normale usa il servizio macchina. |
| `ragscanner serve --port PORT --history-db FILE` | Sceglie porta loopback (1–65535) e database cronologia alternativo. |

### Scanner specializzati

| Comando | Uso dettagliato |
| --- | --- |
| `ragscanner security scan PATH` | Esegue regole di sicurezza con filtri, `--format`, `--fail-on`, `--max-findings`, `--include-pii`, `--offline`/`--no-offline`; offline è predefinito. |
| `ragscanner quality scan PATH` | Verifica duplicati esatti/simili e qualità chunk con interruttori, `--similarity-threshold` (0,5–1,0), limiti token, `--fail-on` e `--format`. |

### Regole operative

| Regola | Significato |
| --- | --- |
| Stato di uscita | Input non valido, errore operativo o risultato alla soglia `--fail-on` produce un’uscita non zero adatta alla CI. |
| Consenso | Contenuti OpenWebUI e AI remota richiedono opzioni esplicite; la scoperta metadata non concede accesso ai contenuti. |
| Credenziali | Conservare i segreti esternamente e passare solo un riferimento. |
| Storage | I percorsi omessi usano le posizioni macchina mostrate da `ragscanner paths`. |
| Servizi | Dashboard/worker installati sono a livello macchina; `serve` e `worker` in primo piano servono alla diagnostica. |
| Sicurezza output | Nessuna sovrascrittura, percorsi assoluti nascosti per default, prove limitate ed escaped. |
| Compatibilità | Opzioni e output sono in inglese; il contenuto RAG resta Unicode nativo in ogni lingua supportata. |

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
4. Pianificazione, conservazione, job ricorrenti e localizzazione dell’interfaccia report
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
