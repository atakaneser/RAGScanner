# RAGScanner

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · **Français** ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner est un outil gratuit, open source et local-first destiné à examiner les risques de
sécurité et de qualité du contenu dans les sources de connaissances RAG. La version alpha technique
actuelle analyse les fichiers TXT, Markdown, PDF textuels et DOCX, puis produit des rapports dans le
terminal, en JSON ou en HTML autonome.

> [!WARNING]
> Cette version est une alpha technique. Une analyse statique ne prouve pas qu’une application RAG
> en fonctionnement est sécurisée. Les résultats sont des éléments de revue, pas une garantie.

## Fonctionnalités disponibles

- Analyse d’un fichier local ou d’un dossier
- TXT, Markdown, PDF textuel et DOCX
- Normalisation, découpage et correspondance des sources déterministes
- Règles de sécurité statiques versionnées
- Analyse des doublons exacts et lexicaux proches
- Contrôles de qualité des chunks
- Rapports terminal, JSON et HTML autonome
- Analyse statique locale et hors ligne par défaut
- Parcours guidé en anglais avec la commande `ragscanner`

L’OCR, la persistance, l’API, le tableau de bord, le planificateur, le connecteur de contenu
OpenWebUI et ModelProvider ne sont pas encore disponibles.

## Installation et première analyse

Python 3.12/3.13 et [`uv`](https://docs.astral.sh/uv/) sont requis.

```powershell
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner
```

Analyse directe :

```powershell
ragscanner scan "C:\Users\Example\Documents\Base de connaissances"
```

```bash
ragscanner scan ./knowledge-base --format html --output ragscanner-report.html
```

Placez entre guillemets les chemins contenant des espaces ou des parenthèses. RAGScanner
n’écrase pas un rapport existant par défaut.

## Langues et confidentialité

L’interface du produit, les erreurs, les recommandations et les métadonnées techniques générées
sont en anglais. Les documents RAG analysés peuvent utiliser toutes les langues Unicode. Les preuves
issues des sources restent dans leur langue d’origine afin de préserver leur valeur d’audit.

L’analyse statique n’envoie aucun document à un service externe, ne nécessite pas de LLM,
n’utilise aucune télémétrie, ne suit aucun lien et n’exécute aucune commande détectée. Les futurs
connecteurs distants et modèles nécessiteront une configuration et un consentement explicites.

## Architecture et feuille de route

`SourceConnector`, `TargetAdapter` et `ModelProvider` sont des rôles distincts. OpenWebUI est une
intégration prévue, pas le cœur du produit.

Les prochaines étapes couvrent la robustesse PDF/chemins et l’UX des rapports, l’historique SQLite,
l’API, le connecteur OpenWebUI, le tableau de bord local et le planificateur. Consultez le
[README anglais canonique](README.md) et [ROADMAP.md](ROADMAP.md).

RAGScanner utilise la [licence Apache 2.0](LICENSE) et reste entièrement gratuit.
