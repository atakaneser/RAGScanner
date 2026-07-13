# RAGScanner

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) ·
[Français](README.fr.md) · [简体中文](README.zh-CN.md) · **Italiano**

RAGScanner è uno strumento gratuito, open source e local-first per esaminare i rischi di sicurezza
e qualità dei contenuti nelle fonti di conoscenza RAG. L’attuale alpha tecnica analizza file TXT,
Markdown, PDF testuali e DOCX e produce report nel terminale, JSON o HTML autonomo.

> [!WARNING]
> Questa versione è un’alpha tecnica. Una scansione statica non dimostra che un’applicazione RAG in
> esecuzione sia sicura. I risultati sono elementi da revisionare, non una garanzia di sicurezza.

## Funzionalità disponibili

- Scansione di un singolo file locale o di una cartella
- TXT, Markdown, PDF testuali e DOCX
- Normalizzazione, suddivisione in chunk e mappatura delle fonti deterministiche
- Regole di sicurezza statiche versionate
- Analisi dei duplicati esatti e lessicalmente simili
- Controlli della qualità dei chunk
- Report nel terminale, JSON e HTML autonomo
- Scansione statica completamente locale e offline per impostazione predefinita
- Procedura guidata in inglese con il comando `ragscanner`

OCR, persistenza, API, dashboard, scheduler, connettore dei contenuti OpenWebUI e ModelProvider non
sono ancora disponibili.

## Installazione e prima scansione

Sono richiesti Python 3.12/3.13 e [`uv`](https://docs.astral.sh/uv/).

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Scansione diretta:

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
```

```bash
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Racchiudere tra virgolette i percorsi che contengono spazi o parentesi. Per impostazione
predefinita RAGScanner non sovrascrive un report esistente.

## Lingue e privacy

L’interfaccia del prodotto, gli errori, i testi di correzione e i metadati tecnici generati sono in
inglese. I documenti RAG analizzati possono usare qualsiasi lingua Unicode. Le prove derivate dalle
fonti rimangono nella lingua originale per preservare l’affidabilità dell’audit.

La scansione statica non invia documenti a servizi esterni, non richiede un LLM, non usa telemetria,
non segue collegamenti e non esegue i comandi rilevati. I futuri connettori remoti e modelli saranno
attivati solo con configurazione e consenso espliciti.

## Architettura e roadmap

`SourceConnector`, `TargetAdapter` e `ModelProvider` restano ruoli separati. OpenWebUI è
un’integrazione pianificata, non il nucleo del prodotto.

I prossimi passi riguardano robustezza PDF/percorsi e UX dei report, cronologia SQLite, API,
connettore OpenWebUI, dashboard locale e scheduler. Consultare il
[README inglese canonico](README.md) e [ROADMAP.md](ROADMAP.md).

RAGScanner usa la [licenza Apache 2.0](LICENSE) e rimarrà completamente gratuito.
