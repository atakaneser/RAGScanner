# RAGScanner

> Analysez votre RAG avant vos utilisateurs.

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · **Français** ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner est un outil gratuit, open source et local-first qui inspecte les risques de sécurité et
de qualité du contenu dans les sources de connaissances RAG. L’alpha technique actuelle analyse les
fichiers TXT, Markdown, PDF textuels et DOCX, puis produit des rapports terminal, JSON ou HTML
autonomes.

Le pipeline statique actuel ne transmet aucun document à un service distant, ne nécessite aucun LLM,
n’exécute aucune télémétrie, ne suit aucun lien et n’exécute jamais les commandes détectées.

> [!WARNING]
> Il s’agit d’une alpha technique. Une analyse statique ne prouve pas qu’une application RAG en
> fonctionnement est sûre et n’offre pas une protection complète contre la prompt injection. Les
> résultats sont des éléments d’examen, pas une garantie de sécurité.

## Fonctionnalités disponibles aujourd’hui

| Fonctionnalité | État de l’alpha |
|---|---|
| Analyse d’un fichier local ou d’un dossier | Disponible |
| TXT, Markdown, PDF textuel et DOCX | Disponible |
| Normalisation déterministe et correspondance des sources | Disponible |
| Découpage par structure, paragraphe et fenêtre de tokens | Disponible |
| Règles de sécurité RAG statiques versionnées | Disponible |
| Analyse des doublons exacts et lexicaux proches | Disponible |
| Contrôles de qualité des chunks | Disponible |
| Rapports terminal, JSON et HTML autonomes | Disponible |
| Analyse statique hors ligne | Comportement par défaut |
| Installation machine unifiée et ouverture du dashboard | `ragscanner install` ; `ragscanner` seul ouvre le dashboard |
| Découverte OpenWebUI en conteneur et inventaire des métadonnées KB/fichiers | Disponible |
| OCR et analyse sémantique des doublons | Pas encore disponible |
| Historique SQLite facultatif et comparaison tenant compte de la couverture | Disponible via la CLI |
| API localhost d’historique | Disponible avec `ragscanner serve` |
| Jobs d’analyse statique SQLite durables et worker | Disponible |
| API asynchrone authentifiée avec scopes pour analyses/jobs | Disponible sur loopback |
| Dashboard local d’aperçu et de file d’attente | Disponible avec `ragscanner serve` |
| Archive de rapports avec filtres date/source, détail et comparaison | Disponible |
| Profils de sources persistants sans secrets et gestion Sources/Settings | Disponible |
| Agent local par utilisateur | Retiré ; remplacé par le service machine |
| Découverte des métadonnées Docker, Podman, nerdctl, Finch, Kubernetes et localhost | Disponible |
| Service hôte local à la machine avec initialisation d’un administrateur local | Disponible |
| Connecteur de contenu de connaissances OpenWebUI avec consentement | Disponible |
| Scheduler et connecteurs de contenu vector store | Pas encore disponible |
| Analyse de rapport assistée par IA locale/distante par analyse | Disponible et désactivée par défaut |
| CLI d’analyse active d’endpoint | Indisponible ; contrats core uniquement |

`ragscanner scan` exécute le pipeline local découverte → parsing → normalisation → découpage →
sécurité statique → analyse des doublons → qualité des chunks → score → rapport.

## Démarrage rapide pour les utilisateurs

Prérequis : Python 3.12 ou 3.13 et [`uv`](https://docs.astral.sh/uv/).

Installez l’alpha directement depuis GitHub :

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

`ragscanner install` installe en une seule étape le service machine, le runtime isolé et l’adresse
du dashboard local, puis ouvre le dashboard par défaut. Utilisez
`ragscanner install --mode terminal` pour terminer la configuration dans la CLI. Les appels
ultérieurs à `ragscanner` ouvrent toujours le dashboard. La découverte automatique ne suggère que les dossiers immédiats aux noms orientés
RAG et ne traite pas les dossiers généraux tels que Documents comme des sources RAG. Après consentement explicite, la
découverte OpenWebUI inspecte des métadonnées limitées des runtimes Docker, Podman, nerdctl ou Finch
disponibles ainsi que les adresses loopback courantes. Une clé API fournie séparément et conservée
uniquement en mémoire peut inventorier les bases de connaissances accessibles ainsi que les
métadonnées des fichiers liés ou autonomes/de chat. L’option 2 permet à l’utilisateur de sélectionner
une base de connaissances OpenWebUI listée puis, après un consentement explicite distinct pour le
contenu, d’exécuter le pipeline statique dans le même processus local.

Entretenez ou supprimez l’installation avec une seule commande RAGScanner :

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner status
ragscanner open
```

Ces commandes exigent des droits administrateur. `update` et `repair` remplacent le runtime machine
et redémarrent le Host Service. L’automatisation peut utiliser `ragscanner uninstall --yes`.
`uninstall` conserve les rapports et l’historique machine sauf si
`--purge-data` est fourni.

L’installation et la réparation ajoutent `%ProgramFiles%\RAGScanner\command` au `PATH` machine de
Windows. Le répartiteur stable `ragscanner.cmd` suit la génération active : les nouveaux terminaux
utilisent donc l’installation machine plutôt qu’un ancien outil `uv` du profil utilisateur. Rouvrez
les terminaux après la première installation ou réparation.
Les installations antérieures à ce répartiteur peuvent nécessiter une transition unique depuis un
terminal administrateur : `uvx --refresh --from git+https://github.com/atakaneser/RAGScanner.git@main
ragscanner repair`. Le code de réparation actuel s’exécute sans installer un autre outil utilisateur.

Après une publication PyPI, l’installation utilisera `uv tool install ragscanner`. Aucun paquet PyPI
ni tag de version n’a encore été publié.

## Analyses directes

L’analyse assistée par IA se choisit séparément pour chaque analyse directe ou tâche du dashboard.
Les fournisseurs locaux sont Ollama, LM Studio, LocalAI et vLLM. Les options distantes comprennent
OpenRouter, OpenAI, NVIDIA NIM, Anthropic, Google Gemini, Groq, Mistral AI, Together AI et les points
de terminaison compatibles OpenAI personnalisés. L’IA est désactivée par défaut et un fournisseur
distant exige un consentement explicite pour l’analyse concernée. Seul un résumé borné et expurgé
est transmis ; les documents bruts et les preuves restent locaux. Une panne du fournisseur ne
compromet pas le rapport déterministe.
Dans le dashboard, la découverte affiche tous les modèles retournés dans un sélecteur dédié. Une
clé API distante peut rester en mémoire du Host Service actif ou être référencée avec `env:` pour
les tâches sans surveillance. La page des tâches se met à jour toutes les deux secondes, distingue
la progression de l’analyse, de l’IA et de l’enregistrement, et affiche des journaux bornés de
succès ou d’échec avec des codes stables, sans secrets ni réponses brutes du fournisseur.

```bash
ragscanner scan ./knowledge-base --ai-provider ollama --ai-model llama3.1:8b
```

Placez entre guillemets les chemins contenant des espaces, des parenthèses ou d’autres caractères
sensibles au shell.

```powershell
ragscanner scan "C:\Users\Example\Documents\Knowledge Base"
ragscanner scan "C:\Users\Example\Downloads\Manual (2026).pdf"
```

```bash
ragscanner scan ./knowledge-base
ragscanner scan ./knowledge-base/manual.pdf
```

Créez des rapports :

```bash
ragscanner scan ./knowledge-base --format json --output report.json
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Enregistrez et comparez l’historique local uniquement sur demande :

```bash
ragscanner scan ./knowledge-base --save-history
ragscanner history list
ragscanner history compare BASELINE_HISTORY_ID CANDIDATE_HISTORY_ID
ragscanner serve
```

Mettez les analyses durables en file d’attente et lancez le worker :

```bash
ragscanner jobs enqueue-scan ./knowledge-base
ragscanner jobs list
ragscanner worker
```

Pour une analyse OpenWebUI consentie, conservez l’identifiant hors de SQLite :

```bash
export OPENWEBUI_API_KEY="your-local-runtime-secret"
ragscanner jobs enqueue-openwebui --base-url http://127.0.0.1:3000 \
  --knowledge-id KNOWLEDGE_ID --credential-ref env:OPENWEBUI_API_KEY --consent-content
ragscanner worker
```

`ragscanner serve` ouvre le dashboard local. Définissez `RAGSCANNER_API_KEY` pour activer la création
d’analyses et le contrôle des jobs via l’API avec authentification Bearer et scopes. Le serveur
écoute uniquement sur `127.0.0.1`.

Par défaut, RAGScanner n’écrase pas un fichier de sortie existant.

## Référence complète des commandes CLI

`ragscanner COMMAND --help` donne la syntaxe de référence de la version installée. La liste suivante
couvre toute l’interface publique ; les commandes internes de compatibilité restent masquées.

### Lancement et diagnostic

| Commande | Utilisation détaillée |
| --- | --- |
| `ragscanner` | Ouvre le dashboard si RAGScanner est installé, sinon affiche la commande d’installation. |
| `ragscanner --version` | Affiche la version installée du CLI. |
| `ragscanner --help` / `ragscanner COMMAND --help` | Affiche l’aide générale ou propre à une commande sans modifier la machine. |
| `ragscanner --install-completion` / `--show-completion` | Installe l’autocomplétion du shell ou affiche le script pris en charge par Typer. |
| `ragscanner doctor` | Diagnostique hors ligne installation, chemins, configuration, parseurs et runtime. |
| `ragscanner paths` | Affiche les chemins machine, données, rapports, temporaires et historiques propres au système. |

### Installation machine et cycle de vie

| Commande | Utilisation détaillée |
| --- | --- |
| `ragscanner install` | Installe le runtime isolé et le superviseur Host (tâche de démarrage Windows sous `SYSTEM`, systemd Linux ou LaunchDaemon macOS), configure `local.ragscanner.com`, initialise les données machine et ouvre le dashboard. Demande l’élévation si nécessaire. |
| `ragscanner install --yes` | Accepte les invites courantes pour une installation automatisée ; l’élévation peut rester nécessaire. |
| `ragscanner install --mode terminal` | Utilise la configuration terminal au lieu du dashboard. Modes valides : `dashboard` et `terminal`. |
| `ragscanner install --no-open-dashboard` | Installe tout sans ouvrir le navigateur à la fin. |
| `ragscanner open` | Ouvre le dashboard installé sans démarrer un second serveur au premier plan. |
| `ragscanner status` | Affiche l’état de l’installation, du service, du dashboard, du runtime et des chemins. |
| `ragscanner update` | Télécharge la dernière version de la branche `main` du dépôt GitHub officiel, l’installe dans le runtime isolé et lui transfère le service ; droits administrateur requis. Aucune commande `uv tool install` séparée n’est nécessaire. |
| `ragscanner repair` | Télécharge et réinstalle la dernière branche `main`, puis répare runtime, service, nom d’hôte, dossiers et configuration ; droits administrateur requis. Aucune commande `uv tool install` séparée n’est nécessaire. |
| `ragscanner uninstall` | Après confirmation, retire service, runtime et nom d’hôte tout en conservant rapports et historique. |
| `ragscanner uninstall --yes --purge-data` | Retire sans interaction également configuration, historique et données gérées. Opération destructive. |

### Analyses locales directes

```text
ragscanner scan PATH [OPTIONS]
```

`PATH` désigne un fichier pris en charge ou un dossier. Placez entre guillemets les chemins sensibles
au shell. L’analyse est locale et l’enrichissement AI reste désactivé sans sélection explicite.

| Option | Utilisation détaillée |
| --- | --- |
| `--format terminal|json|html`, `--output PATH` | Choisit le terminal ou un export JSON/HTML explicite. Un export exige un chemin et n’écrase aucun fichier. |
| `--include GLOB`, `--exclude GLOB` | Restreint la découverte par motifs glob répétables. |
| `--recursive` / `--no-recursive` | Active ou désactive les sous-dossiers ; actif par défaut. |
| `--max-file-size BYTES`, `--max-files COUNT` | Fixe des limites positives de taille et de nombre de fichiers. |
| `--category NAME`, `--exclude-rule ID` | Inclut des catégories ou exclut des règles ; répéter pour plusieurs valeurs. |
| `--include-pii` / `--no-include-pii` | Active ou désactive les règles PII de la politique effective. |
| `--min-severity LEVEL`, `--fail-on LEVEL`, `--max-findings COUNT` | Filtre l’affichage, définit le seuil d’échec et borne le volume des résultats. |
| `--config FILE` | Charge une politique depuis un fichier explicite en plus des valeurs par défaut et machine. |
| `--security-only`, `--quality-only` | Exécute uniquement la sécurité ou la qualité ; ne pas combiner. |
| `--quiet`, `--verbose`, `--no-color` | Règle le détail terminal et la couleur ANSI sans modifier les résultats. |
| `--save-history`, `--history-db FILE` | Enregistre un rapport versionné et choisit éventuellement une autre base SQLite. |
| `--ai-provider NAME`, `--ai-model NAME`, `--ai-base-url URL` | Active l’enrichissement avec le fournisseur, modèle et endpoint compatible choisis. |
| `--ai-credential-ref REF`, `--consent-remote-ai` | Résout un secret externe tel que `env:OPENROUTER_API_KEY` et enregistre le consentement distant requis. |

### Enrichissement AI des rapports

| Commande ou option | Utilisation détaillée |
| --- | --- |
| `ragscanner analyze-report REPORT_FILE --model MODEL --output FILE` | Enrichit un rapport existant pris en charge ; modèle et sortie sont obligatoires. |
| `--provider NAME` | Choisit le fournisseur, `ollama` par défaut ; fournisseurs locaux et distants compatibles sont configurables. |
| `--base-url URL`, `--credential-ref REF` | Remplace l’endpoint et résout le secret hors du rapport et de l’historique. |
| `--consent-remote` | Autorise explicitement l’envoi d’un résumé borné et masqué ; documents bruts et preuves restent locaux. |

### Jobs durables et worker

| Commande | Utilisation détaillée |
| --- | --- |
| `ragscanner jobs enqueue-scan PATH` | Met en file une analyse fichier/dossier ; accepte `--database`, `--config`, `--idempotency-key`, `--max-attempts` et les options AI. |
| `ragscanner jobs enqueue-openwebui` | Met en file OpenWebUI. Exige `--base-url`, `--knowledge-id`, `--credential-ref`, `--consent-content` ; accepte base, idempotence, reprises et AI. |
| `ragscanner jobs list` | Liste les jobs avec `--database`, `--limit` (1–200), `--offset` et `--format`. |
| `ragscanner jobs show JOB_ID` | Affiche tentatives, dates, résultat et erreur ; `--database` choisit le stockage. |
| `ragscanner jobs cancel JOB_ID` | Annule un job non terminal ; `--database` choisit le stockage. |
| `ragscanner jobs retry JOB_ID` | Crée une nouvelle tentative pour un job éligible échoué/annulé. |
| `ragscanner worker` | Loue et exécute en continu les jobs de la base machine. |
| `ragscanner worker --once` | Traite une fois le travail disponible puis quitte. |
| `--database FILE`, `--poll-interval SECONDS`, `--lease-seconds SECONDS`, `--worker-id ID` | Règle stockage, polling (0,1–60), bail (5–3600) et identité du worker. |

### Historique des rapports

| Commande | Utilisation détaillée |
| --- | --- |
| `ragscanner history list` | Liste les scans avec `--database`, `--limit` (1–200), `--offset` et `--format`. |
| `ragscanner history show SCAN_ID` | Rend un rapport avec `--database`, `--format` et éventuellement `--verbose`. |
| `ragscanner history compare BASELINE_ID CANDIDATE_ID` | Compare résultats nouveaux, résolus et inchangés ; accepte `--database` et `--format`. |
| `ragscanner history delete SCAN_ID` | Supprime après confirmation. Réserver `--yes` à l’automatisation délibérée ; `--database` choisit le stockage. |

### Rendu et service au premier plan

| Commande | Utilisation détaillée |
| --- | --- |
| `ragscanner report SCAN_RESULT` | Refait le rendu avec `--format`, `--output`, `--verbose`, filtres de résultats, `--max-findings`, `--include-info`/`--exclude-info` et éventuellement `--show-absolute-paths`. |
| `ragscanner serve` | Lance dashboard/API sur loopback au premier plan pour développement ou diagnostic ; l’installation normale utilise le service machine. |
| `ragscanner serve --port PORT --history-db FILE` | Choisit le port loopback (1–65535) et une autre base d’historique. |

### Analyseurs spécialisés

| Commande | Utilisation détaillée |
| --- | --- |
| `ragscanner security scan PATH` | Exécute les règles de sécurité avec filtres, `--format`, `--fail-on`, `--max-findings`, `--include-pii`, `--offline`/`--no-offline` ; hors ligne par défaut. |
| `ragscanner quality scan PATH` | Vérifie doublons exacts/proches et qualité des chunks avec interrupteurs, `--similarity-threshold` (0,5–1,0), bornes de tokens, `--fail-on` et `--format`. |

### Règles opérationnelles

| Règle | Signification |
| --- | --- |
| Code de sortie | Entrée invalide, erreur opérationnelle ou résultat au seuil `--fail-on` produit un code non nul adapté à la CI. |
| Consentement | Contenu OpenWebUI et AI distante exigent leurs options explicites ; la découverte de métadonnées ne donne aucun accès au contenu. |
| Identifiants | Stocker les secrets à l’extérieur et ne transmettre qu’une référence d’identifiant. |
| Stockage | Les chemins omis utilisent les emplacements machine affichés par `ragscanner paths`. |
| Services | Dashboard/worker installé est à l’échelle machine ; `serve` et `worker` au premier plan servent au diagnostic. |
| Sécurité de sortie | Aucun écrasement, chemins absolus masqués par défaut, preuves bornées et échappées. |
| Compatibilité | Options et sorties sont en anglais ; le contenu RAG reste Unicode natif dans toute langue prise en charge. |

## Entrées multilingues

Les libellés d’interface, textes d’état, messages d’erreur, remédiations, métadonnées et documents
canoniques générés par le produit sont en anglais. Les sources RAG restent natives Unicode et peuvent
contenir du turc, de l’allemand, du français, du chinois, de l’italien, de l’arabe, du cyrillique, du
CJK, des emoji et des variantes de noms de fichiers NFC/NFD.

Les preuves issues des sources restent dans leur langue d’origine afin de préserver la fidélité de
l’audit. Les README localisés sont les seuls documents du projet volontairement non anglophones.

## Comprendre les rapports

Les rapports distinguent :

- l’état d’achèvement de l’analyse et la couverture partielle ;
- la gravité et le niveau de confiance ;
- les classifications `confirmed`, `probable`, `ambiguous` et `not_detected` ;
- les contrôles évalués, partiels, échoués et `not_assessed` ;
- les emplacements de document, page, chunk et source lorsqu’ils existent ;
- les versions du scanner, du paquet de règles et de la politique.

`not_assessed` ne signifie pas sain ou sans risque. Un score de sécurité n’est pas une garantie de
sécurité. L’analyse statique et les tests actifs autorisés d’endpoint sont des modes distincts.

## Modèle de confidentialité et de sécurité

- Les analyses statiques sont locales et n’effectuent aucun appel réseau caché.
- Le contenu des documents ou chunks n’est pas envoyé à des services d’IA externes.
- Les URL peuvent être analysées mais ne sont pas récupérées.
- Les payloads suspects, macros, commandes shell et objets intégrés ne sont pas exécutés.
- Les relations DOCX externes ne sont pas suivies ; les pièces jointes PDF ne sont pas extraites.
- Les preuves sont limitées, échappées pour HTML et masquées pour les motifs ressemblant à des secrets.
- Les chemins source absolus sont masqués par défaut dans les rapports.
- Il n’existe aucune télémétrie, facturation, souscription, habilitation ou serveur de licence.

Les connecteurs distants et modèles optionnels restent désactivés tant qu’ils ne sont pas
explicitement configurés et acceptés. L’accès au contenu OpenWebUI exige une base sélectionnée, une
référence externe d’identifiant et un consentement explicite ; c’est une intégration, pas le cœur.

## Installation pour les contributeurs

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run ragscanner --version
uv run ragscanner doctor
uv run ragscanner scan ./examples/sample-kb
```

Contrôles qualité :

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
```

Tous les fixtures doivent être synthétiques. N’ajoutez jamais de véritables identifiants, documents
clients ou données personnelles.

## Architecture

Le core reste indépendant des frameworks UI, bases de données, connecteurs, fournisseurs de modèles
et de MCP. Les rôles d’intégration sont délibérément séparés :

- `SourceConnector` lit les documents, chunks, métadonnées ou contenus de base de connaissances.
- `TargetAdapter` envoie des tests black-box autorisés à une application RAG/chat en fonctionnement.
- `ModelProvider` fournit un modèle d’analyse optionnel à RAGScanner lui-même.

Utiliser OpenAI, Hugging Face ou OpenWebUI ne prouve pas l’existence d’un retrieval. Une cible n’est
appelée cible RAG que si le retrieval de documents/vector/index est vérifié.

Consultez [ARCHITECTURE.md](ARCHITECTURE.md), [PRODUCT.md](PRODUCT.md) et
[docs/status/current.md](docs/status/current.md) pour les limites détaillées et l’état actuel.

## Feuille de route

La séquence immédiate est :

1. Travaux restants de récupération de persistance et d’historique/comparaison à l’échelle API
2. Connecteurs SharePoint, web, SaaS, Git, object store et vector store par niveau de capacité
3. Compatibilité OpenWebUI, détection incrémentale, identité des sources et fournisseurs de secrets
4. Planification, rétention, tâches récurrentes et localisation de l’interface des rapports
5. Scheduler, rétention et notifications
6. Renforcement du packaging et du déploiement

Les fonctionnalités prévues ne sont jamais présentées comme disponibles. Consultez
[ROADMAP.md](ROADMAP.md) pour plus de détails.

## Contribution et licence

Lisez [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) et
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) avant de contribuer. Ne publiez pas de secrets, exploits
ou contenus clients dans les issues publiques.

RAGScanner est distribué sous [Apache License 2.0](LICENSE). Il existe un seul produit gratuit et open
source : aucune séparation Community/Pro, aucun flux de règles payant, abonnement, habilitation ou
module fermé.
