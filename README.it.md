# RAGScanner

> Analizza il tuo RAG prima degli utenti.

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · [Français](README.fr.md) ·
[简体中文](README.zh-CN.md) · **Italiano**

RAGScanner è uno scanner gratuito, open source e local-first per rischi di sicurezza e qualità nelle
fonti RAG. Riunisce scansione deterministica, job persistenti, cronologia, monitoraggio ricorrente e
analisi AI consultiva facoltativa in una dashboard locale alla macchina.

> [!WARNING]
> RAGScanner è una versione alpha tecnica. Un rapporto statico aiuta la revisione, ma non dimostra
> che un sistema RAG attivo sia sicuro o protetto da ogni tecnica di prompt injection.

## Disponibile ora

| Area | Capacità attuale |
|---|---|
| Contenuti locali | Singoli file e cartelle confinate a una radice |
| Formati | Markdown, TXT, HTML, PDF, DOCX, PPTX, XLSX, ODT, EPUB, RST, AsciiDoc, CSV/TSV, JSON/JSONL, YAML, XML e log |
| Fonti remote | Basi OpenWebUI; pagine HTTPS, documenti, sitemap della stessa origine e URL SharePoint accessibili |
| Analisi | Regole statiche, duplicati esatti/lessicali e qualità dei chunk |
| Rapporti | Terminale/JSON e download localizzati in HTML, Excel e PDF |
| Cronologia | ID leggibili, filtri, dettagli, confronto, trend salute ed eliminazione permanente |
| Job | Esecuzioni persistenti, intervalli, annullamento, retry, avanzamento e log sicuri |
| AI | Analisi locale o remota esplicitamente autorizzata; disattivata per impostazione predefinita |
| Lingue | Etichette inglesi, turche, tedesche, francesi, cinesi semplificate e italiane |
| Installazione | Host Service locale alla macchina su Windows, macOS e Linux |

OCR, duplicati semantici, rilevamento autenticato di librerie Microsoft Graph, connettori di contenuto
vector store, cron/calendario, conservazione configurabile, autenticazione multiutente e distribuzione
Docker non sono ancora disponibili. Rilevare una piattaforma non equivale ad accesso o valutazione.

## Installa e apri

Installa dal repository ufficiale, quindi crea il servizio macchina:

```bash
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

L’installer apre la dashboard locale. In seguito usa:

```bash
ragscanner
ragscanner open
ragscanner status
ragscanner paths
```

Installazione e comandi del ciclo di vita richiedono privilegi amministrativi. La dashboard è
associata solo a `127.0.0.1` e usa l’indirizzo fisso `http://localhost:8765`. Non modifica il file
hosts e non accetta hostname o porte personalizzate. La password dell’amministratore locale si può
cambiare nelle Impostazioni; l’operazione chiude tutte le altre sessioni della dashboard.

## Aggiorna, ripara e disinstalla

```bash
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner uninstall --purge-data --yes
```

`update` installa il runtime ufficiale `main` più recente conservando impostazioni, segreti, job e
rapporti. `repair` ricrea runtime e servizio. `uninstall` conserva i dati per impostazione predefinita;
`--purge-data` li elimina definitivamente.

## Analizza i contenuti

La dashboard è l’interfaccia consigliata. Per automazione o scansioni locali dirette:

```bash
ragscanner scan PATH
ragscanner scan PATH --save-history
ragscanner scan PATH --format html --output report.html
ragscanner serve
```

Il pannello Crea job supporta:

- file e cartelle locali;
- basi OpenWebUI dopo consenso esplicito ai contenuti;
- una pagina HTTPS o un documento supportato;
- sitemap URL della stessa origine e un livello di indice annidato;
- URL SharePoint direttamente accessibili con riferimento ambiente Bearer facoltativo;
- esecuzione singola o monitoraggio a intervalli ricorrenti.

La creazione del job segue quattro passaggi: scegli un’origine collegata o manuale, inserisci solo i
dettagli necessari, imposta un’esecuzione singola o periodica e attiva facoltativamente l’AI. Per i
job periodici puoi scegliere la prima data e ora locali. I provider AI locali vengono controllati
automaticamente; i modelli verificati appaiono in un solo selettore, mentre endpoint, credenziali e
inserimento manuale restano nelle impostazioni di connessione facoltative.

Le scansioni web rifiutano reindirizzamenti e voci sitemap di altra origine, non eseguono script e
limitano pagine, dimensioni e timeout. Il rilevamento autenticato di siti/librerie Microsoft Graph
rimane un connettore separato pianificato.

## Configurazione e validazione RAG

Ogni nuovo rapporto registra il profilo di carico scelto e confronta il chunking configurato con le
statistiche osservate. Propone un intervallo iniziale spiegabile, la sovrapposizione e un top-k di
recupero per ricerca fattuale, domande generali, policy/procedure, ricerca, codice o tabelle. Non
esiste una dimensione dei chunk universalmente migliore; il rapporto elenca sempre le metriche di
recupero, risposta, citazione, latenza e costo da validare con query rappresentative.

Usa `--rag-profile` con i parametri opzionali di contesto/top-k oppure la tabella `[rag]` in
`ragscanner.toml`. Vedi [RAG configuration advice](docs/rag-configuration-advice.md). Misura un corpus
locale etichettato con `ragscanner quality calibrate`; vedi
[Quality calibration](docs/quality-calibration.md). Il corpus integrato in sei lingue è solo un test
di regressione, non una prova di accuratezza in produzione.

## Rapporti assistiti da AI

L’analisi AI è facoltativa e non sostituisce i risultati deterministici. Le impostazioni rilevano i
modelli installati in Ollama, LM Studio, LocalAI o vLLM invece di conservare nomi obsoleti. I provider
remoti richiedono HTTPS, riferimento credenziali esterno e consenso per scansione.

Viene inviato solo un contesto di rapporto limitato e oscurato, mai documenti grezzi. Le prove grezze
dei risultati di sicurezza statica e degli altri risultati della stessa fonte interessata vengono
omesse; regola, file/pagina/riga, impatto e rimedio deterministico restano disponibili. Le istruzioni
del documento non diventano quindi istruzioni per il modello.

L’output è validato da schema. RAGScanner accetta un unico oggetto di analisi non ambiguo dai comuni
involucri dei modelli locali—blocco JSON, prefisso di ragionamento o stringa JSON serializzata—poi
riprova una volta l’output non valido con regole JSON e dati non attendibili più severe.
Le deviazioni comuni dallo schema vengono normalizzate, i riferimenti inventati sono scartati in
sicurezza e l’analisi accettata può associare correzione e verifica a ogni risultato reale.

## Rapporti e operazioni

La salute della panoramica usa sempre l’ultimo rapporto completato rimasto. I rapporti possono essere
filtrati, confrontati nel tempo, esaminati o eliminati definitivamente dopo conferma. Job singoli e
definizioni ricorrenti sono separati. L’attività mostra codici e cause sicure senza risposte grezze o
credenziali.
Per le pianificazioni ricorrenti si possono modificare prossima esecuzione e intervallo. I rapporti
mostrano sicurezza, qualità dei contenuti, efficienza, file/pagina/riga e prove evidenziate. Ovunque
valgono le stesse soglie: sotto 85 giallo, sotto 70 arancione, sotto 55 rosso. L’analisi AI attende
180 secondi per i modelli locali lenti; errori e dati seguono la lingua selezionata.
Ogni rapporto salvato può essere scaricato dalla pagina di dettaglio come HTML autonomo senza rete,
cartella Excel strutturata con più fogli o PDF impaginato. Gli export usano la lingua selezionata e
mantengono le prove sorgente nella lingua originale.
Le nuove scansioni conservano correttamente la punteggiatura sorgente, inclusi gli apostrofi, nelle
prove del dashboard e dei PDF. Le risposte naturalmente brevi di un singolo documento e le posizioni
approssimative dovute solo alla normalizzazione non vengono segnalate come difetti dei chunk.
I test di variazione impediscono inoltre che titoli, liste, tabelle, codice e sovrapposizioni
generati, scritture senza distinzione tra maiuscole e minuscole e campioni lessicali troppo piccoli
producano risultati senza prove appartenenti alla sorgente.

Comandi operativi utili:

```bash
ragscanner jobs list
ragscanner history list
ragscanner worker
```

Consulta il [riferimento CLI completo](docs/cli.md), la [guida dashboard](docs/dashboard.md) e la
[risoluzione problemi](docs/troubleshooting.md) per opzioni avanzate.

## Privacy e sicurezza

- Le scansioni statiche locali sono offline per impostazione predefinita e non richiedono LLM.
- L’accesso remoto a documenti o modelli richiede configurazione visibile e consenso.
- Le chiavi API restano fuori da SQLite in file protetti o riferimenti `env:`.
- Job persistenti e rapporti contengono solo riferimenti opachi ai segreti.
- Contenuti, output modello, URL e prove sono non attendibili e limitati.
- Le etichette generate dal prodotto sono localizzate; le prove mantengono la lingua originale.

Leggi [PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md) e il
[contratto SourceConnector](docs/source-connector-contract.md) prima di esporre integrazioni.

## Per contribuire

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run pytest
```

Prima di inviare modifiche esegui Ruff, formattazione, mypy, test e `uv build` come indicato in
[CONTRIBUTING.md](CONTRIBUTING.md). I confini sono in [ARCHITECTURE.md](ARCHITECTURE.md), lo stato in
[docs/status/current.md](docs/status/current.md).

## Licenza

Apache-2.0. Vedi [LICENSE](LICENSE).
