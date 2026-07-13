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
| Démarrage guidé en anglais | Disponible avec `ragscanner` seul |
| OCR et analyse sémantique des doublons | Pas encore disponible |
| Persistance, API, dashboard, historique et scheduler | Pas encore disponible |
| Connecteurs de contenu OpenWebUI et vector store | Pas encore disponible |
| Intégration ModelProvider/BYOM | Pas encore disponible |
| CLI d’analyse active d’endpoint | Indisponible ; contrats core uniquement |

`ragscanner scan` exécute le pipeline local découverte → parsing → normalisation → découpage →
sécurité statique → analyse des doublons → qualité des chunks → score → rapport.

## Démarrage rapide pour les utilisateurs

Prérequis : Python 3.12 ou 3.13 et [`uv`](https://docs.astral.sh/uv/).

Installez l’alpha directement depuis GitHub :

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

La commande seule ouvre un parcours d’accueil en anglais. Il demande la source utilisée, suggère des
sources locales proches et limitées, et peut lancer une analyse. La découverte OpenWebUI vérifie
uniquement des endpoints de santé loopback fixes après consentement explicite ; elle ne récupère pas
encore le contenu OpenWebUI.

Entretenez ou supprimez l’installation avec une seule commande RAGScanner :

```powershell
ragscanner update
ragscanner repair
ragscanner uninstall
```

`uninstall` demande confirmation. Les automatisations peuvent utiliser `ragscanner uninstall --yes`.
Ces commandes délèguent à l’environnement officiel `uv tool` sans shell ; `repair` réinstalle
complètement l’outil tout en conservant la source et les paramètres d’installation d’origine.

Après une publication PyPI, l’installation utilisera `uv tool install ragscanner`. Aucun paquet PyPI
ni tag de version n’a encore été publié.

## Analyses directes

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

Par défaut, RAGScanner n’écrase pas un fichier de sortie existant.

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

Les connecteurs distants et modèles optionnels resteront désactivés tant qu’ils ne seront pas
explicitement configurés et acceptés. OpenWebUI est une intégration prévue, pas le cœur du produit.

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

1. Résilience PDF/chemins et UX d’installation, de rapport et du terminal
2. Historique des analyses SQLite et persistance
3. API applicative et comparaison des analyses
4. Connecteur de source OpenWebUI
5. Dashboard local et scheduler
6. Autres connecteurs de sources, target adapters et fournisseurs de modèles optionnels
7. Renforcement du packaging et du déploiement

Les fonctionnalités prévues ne sont jamais présentées comme disponibles. Consultez
[ROADMAP.md](ROADMAP.md) pour plus de détails.

## Contribution et licence

Lisez [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) et
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) avant de contribuer. Ne publiez pas de secrets, exploits
ou contenus clients dans les issues publiques.

RAGScanner est distribué sous [Apache License 2.0](LICENSE). Il existe un seul produit gratuit et open
source : aucune séparation Community/Pro, aucun flux de règles payant, abonnement, habilitation ou
module fermé.
