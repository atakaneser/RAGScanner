# RAGScanner

> Analysez votre RAG avant vos utilisateurs.

[English](README.md) · [Türkçe](README.tr.md) · [Deutsch](README.de.md) · **Français** ·
[简体中文](README.zh-CN.md) · [Italiano](README.it.md)

RAGScanner est un analyseur gratuit, open source et local-first pour les risques de sécurité et de
qualité dans les sources de connaissances RAG. Il réunit analyse déterministe, tâches durables,
historique, surveillance récurrente et conseil IA facultatif dans un dashboard local à la machine.

> [!WARNING]
> RAGScanner est une version alpha technique. Un rapport statique aide à la revue, mais ne prouve pas
> qu’un système RAG actif est sûr ou protégé contre toutes les formes de prompt injection.

## Disponible aujourd’hui

| Domaine | Capacité actuelle |
|---|---|
| Contenu local | Fichiers uniques et dossiers confinés à une racine |
| Formats | Markdown, TXT, HTML, PDF, DOCX, PPTX, XLSX, ODT, EPUB, RST, AsciiDoc, CSV/TSV, JSON/JSONL, YAML, XML et journaux |
| Sources distantes | Bases OpenWebUI ; pages HTTPS, documents, sitemaps de même origine et URL SharePoint accessibles |
| Analyse | Règles statiques, doublons exacts/lexicaux et qualité des chunks |
| Rapports | Terminal/JSON et téléchargements localisés en HTML, Excel et PDF |
| Historique | ID lisibles, filtres, détail, comparaison, tendance de santé et suppression permanente |
| Tâches | Exécutions durables, intervalles, annulation, reprise, progression et journaux sûrs |
| IA | Conseil local ou distant explicitement autorisé ; désactivé par défaut |
| Langues | Libellés anglais, turcs, allemands, français, chinois simplifié et italiens |
| Installation | Host Service local à la machine sur Windows, macOS et Linux |

OCR, doublons sémantiques, découverte authentifiée de bibliothèques Microsoft Graph, connecteurs de
contenu vectoriel, calendriers cron, rétention configurable, authentification multi-utilisateur et
déploiement Docker ne sont pas encore disponibles. Détecter une plateforme ne donne ni accès au
contenu ni évaluation.

## Installer et ouvrir

Installez depuis le dépôt officiel puis créez le service machine :

```bash
uv tool install git+https://github.com/atakaneser/RAGScanner.git
ragscanner doctor
ragscanner install
```

L’installateur ouvre le dashboard local. Utilisez ensuite :

```bash
ragscanner
ragscanner open
ragscanner status
ragscanner paths
```

Les commandes d’installation et de cycle de vie exigent les droits administrateur. Le dashboard
est lié uniquement à `127.0.0.1` et utilise l’adresse fixe `http://localhost:8765`. Il ne modifie pas
le fichier hosts et n’accepte ni nom d’hôte ni port personnalisé. Le mot de passe administrateur
local se modifie dans Paramètres ; cette action ferme toutes les autres sessions.

## Mettre à jour, réparer et désinstaller

```bash
ragscanner update
ragscanner repair
ragscanner uninstall
ragscanner uninstall --purge-data --yes
```

`update` installe le dernier runtime officiel `main` tout en conservant paramètres, secrets, tâches
et rapports. `repair` reconstruit runtime et service. `uninstall` conserve les données par défaut ;
`--purge-data` les supprime définitivement.

## Analyser le contenu

Le dashboard est l’interface recommandée. Pour l’automatisation ou une analyse locale directe :

```bash
ragscanner scan PATH
ragscanner scan PATH --save-history
ragscanner scan PATH --format html --output report.html
ragscanner serve
```

Le tiroir de création de tâche prend en charge :

- fichiers et dossiers locaux ;
- bases OpenWebUI après consentement explicite au contenu ;
- une page HTTPS ou un document pris en charge ;
- sitemaps URL de même origine et un niveau d’index imbriqué ;
- URL SharePoint directement accessibles avec référence d’environnement Bearer facultative ;
- exécution unique ou surveillance à intervalle récurrent.

La création d’une tâche suit quatre étapes : choisir une source connectée ou manuelle, saisir
uniquement ses informations, définir une exécution unique ou périodique, puis activer l’IA si
nécessaire. Une tâche périodique accepte une première date et heure locales explicites. Les
fournisseurs IA locaux sont vérifiés automatiquement ; les modèles confirmés sont réunis dans un
sélecteur, tandis que le point de terminaison, les identifiants et la saisie manuelle restent dans
les paramètres de connexion facultatifs.

Les analyses web refusent redirections et entrées de sitemap d’une autre origine, n’exécutent aucun
script et limitent pages, taille et délais. La découverte authentifiée des sites/bibliothèques
Microsoft Graph reste un connecteur distinct planifié.

## Configuration et validation RAG

Chaque nouveau rapport enregistre le profil de charge choisi et compare le découpage configuré aux
statistiques observées. Il propose une plage initiale explicable, un chevauchement et un top-k de
recherche pour les faits, les questions générales, les politiques/procédures, la recherche, le code
ou les tableaux. Il n’existe pas de taille de fragment universellement optimale ; le rapport liste
toujours les métriques de recherche, réponse, citation, latence et coût à valider avec des requêtes
représentatives.

Utilisez `--rag-profile` avec les options facultatives de contexte/top-k, ou la table `[rag]` de
`ragscanner.toml`. Voir [RAG configuration advice](docs/rag-configuration-advice.md). Mesurez un
corpus local étiqueté avec `ragscanner quality calibrate` ; voir
[Quality calibration](docs/quality-calibration.md). Le corpus intégré en six langues est un test de
régression, pas une preuve de précision en production.

## Rapports assistés par IA

L’analyse IA est facultative et ne remplace pas les constats déterministes. Les paramètres détectent
les modèles installés dans Ollama, LM Studio, LocalAI ou vLLM au lieu de conserver un nom obsolète.
Les fournisseurs distants exigent HTTPS, une référence d’identifiants et un consentement par analyse.

Seul un contexte de rapport limité et expurgé est envoyé—jamais les documents bruts. Les preuves
brutes des constats de sécurité statique et des autres constats de la même source affectée sont
retirées ; règle, fichier/page/ligne, impact et correction déterministe restent disponibles. Les
instructions d’un document ne deviennent donc pas des instructions pour le modèle.

La sortie est validée par schéma. RAGScanner accepte un objet d’analyse non ambigu dans les
enveloppes locales courantes—bloc JSON, préfixe de raisonnement ou chaîne JSON sérialisée—puis
réessaie une fois une sortie invalide avec des règles JSON et de données non fiables plus strictes.
Les écarts de schéma courants sont normalisés, les références inventées sont ignorées en sécurité et
l’analyse acceptée peut associer correction et vérification à chaque constat réel.

## Rapports et exploitation

La santé de l’aperçu repose toujours sur le dernier rapport achevé restant. Les rapports peuvent
être filtrés, comparés dans le temps, examinés ou supprimés définitivement après confirmation. Les
tâches uniques et définitions récurrentes sont séparées. L’activité affiche des codes et raisons sûrs
sans réponse brute du fournisseur ni identifiants.
La prochaine exécution et l’intervalle des planifications récurrentes sont modifiables. Les rapports
affichent sécurité, qualité du contenu, efficacité, fichier/page/ligne et preuve surlignée. Les mêmes
seuils s’appliquent partout : sous 85 jaune, sous 70 orange, sous 55 rouge. L’analyse IA attend par
défaut 180 secondes pour les modèles locaux lents ; erreurs et données suivent la langue choisie.
Chaque rapport enregistré se télécharge depuis sa page détaillée en HTML autonome sans réseau,
classeur Excel structuré à plusieurs feuilles ou PDF paginé. Les exports utilisent la langue de
l’interface sélectionnée et conservent les preuves sources dans leur langue d’origine.
Les nouveaux scans préservent correctement la ponctuation source, notamment les apostrophes, dans
le tableau de bord et les PDF. Les réponses naturellement courtes d’un seul document et les
positions approximatives dues uniquement à la normalisation ne sont pas signalées comme défauts de chunk.
Les tests de variation empêchent aussi les titres, listes, tableaux, blocs de code et chevauchements
générés, les écritures sans casse et les petits échantillons lexicaux de créer des constats sans
preuve appartenant à la source.

Commandes utiles :

```bash
ragscanner jobs list
ragscanner history list
ragscanner worker
```

Consultez la [référence CLI complète](docs/cli.md), le [guide du dashboard](docs/dashboard.md) et le
[guide de dépannage](docs/troubleshooting.md) pour les options avancées.

## Confidentialité et sécurité

- Les analyses statiques locales sont hors ligne par défaut et ne nécessitent aucun LLM.
- L’accès distant aux documents ou modèles exige une configuration visible et un consentement.
- Les clés API restent hors de SQLite, dans des fichiers protégés ou des références `env:`.
- Les tâches durables et rapports ne contiennent que des références opaques aux secrets.
- Contenu, sorties modèle, URL et preuves sont non fiables et strictement limités.
- Les libellés produits sont localisés ; les preuves sources conservent leur langue d’origine.

Lisez [PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md) et le
[contrat SourceConnector](docs/source-connector-contract.md) avant d’exposer une intégration.

## Pour contribuer

```bash
git clone https://github.com/atakaneser/RAGScanner.git
cd RAGScanner
uv sync --frozen
uv run pytest
```

Avant toute contribution, exécutez Ruff, formatage, mypy, tests et `uv build` selon
[CONTRIBUTING.md](CONTRIBUTING.md). Les limites sont dans [ARCHITECTURE.md](ARCHITECTURE.md) et
l’état actuel dans [docs/status/current.md](docs/status/current.md).

## Licence

Apache-2.0. Voir [LICENSE](LICENSE).
