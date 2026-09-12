# V4 — assistance vérifiable, auteur décisionnaire

## Automatisation effective

- Lecture du YAML avec PyYAML : listes imbriquées, chaînes citées, textes multilignes.
- Audit : erreurs de syntaxe, identifiants, types élémentaires, références, manifeste, continuité explicite et métadonnées V4 quand elles sont présentes.
- `draft` / `revision` : valeurs provisoires signalées ; `validated` : champs manquants et `unknown` bloquants. Les erreurs structurelles restent bloquantes à chaque stade. `not_applicable` est une valeur explicite acceptée ; son adéquation relève de l'auteur.
- Dossiers de recherche homonymes conservés avec suffixes ; originaux des variantes intacts.
- Sources ajoutées comme `identified`, sans fausse date de consultation.
- Assemblage et dossiers lecteur : retrait des métadonnées YAML et commentaires HTML. Les scènes du manifeste peuvent encore être en brouillon : un assemblage n'est pas une validation éditoriale.
- Tests sur un mini-manuscrit fictif construit uniquement dans un répertoire temporaire.

## Parcours auteur existants

```bash
python scripts/nexus.py creative-interview --subject "Mon intuition"
python scripts/nexus.py research-brief --subject "Question à éclairer"
python scripts/nexus.py influence-note --subject "Auteur, œuvre, passage"
python scripts/nexus.py variant-lab --id SCN-001 --axis rythme
python scripts/nexus.py impact --id CHR-001
python scripts/nexus.py reader-pack --through 3
python scripts/nexus.py reader-pack --through 3 --spoilers
```

Les sorties sont distinctes, dans `atelier/v3/`, et non canoniques.

L'entretien recueille cinq réponses puis cadre trois propositions à élaborer avec l'assistant. Le mandat de recherche prévoit une décision, un budget, les sources contradictoires, leur état de lecture et un critère d'arrêt. Il n'effectue pas de recherche Internet tout seul. La note d'influence recueille des réactions réelles de l'auteur : elle ne déduit pas ses goûts et ne demande pas d'imiter une voix d'auteur.

Le laboratoire copie l'original, enregistre son empreinte et prépare deux variantes sur un axe unique : leur rédaction et leur choix restent humains ou assistés. L'impact recense les fichiers mentionnant explicitement un identifiant, pas ses conséquences implicites. Le dossier lecteur borne la lecture à une position du manifeste ; `--spoilers` ajoute explicitement le canon. Un lecteur simulé ne remplace pas un bêta-lecteur humain.

## Nouveaux moteurs V4

### 1. Reader State Engine

Les scènes peuvent déclarer `reader_state` : question dominante, savoir/croyances avant et après, attente, émotion et ancrage humain. `reader-map` expose ces intentions pour comparaison avec la lecture réelle.

### 2. Cognitive Load Guard

Les scènes peuvent déclarer `cognitive_load` : concepts, mystères actifs, noms, règles, révélations majeures, questions différées et focus dominant. `audit` applique des seuils configurables dans `data/experience_model.yml` et produit des alertes de densité. Ces alertes ne notent pas la qualité littéraire.

### 3. Mystery Graph

`mystery_state` répartit les mystères en `active`, `deferred`, `dormant`, `resolved`. `mystery-graph` rend visible leur hiérarchie et leur dernier état déclaré.

### 4. Emotional Continuity

`emotional_continuity` suit l'entrée/sortie du POV, le déplacement relationnel et le coût incarné. Une révélation majeure sans assimilation humaine produit une alerte.

### 5. Narrative Debt Ledger

`narrative_debt` suit les dettes ouvertes, progressées et payées scène par scène. `debt-ledger` les croise avec le registre `data/narrative_debt.yml` et leurs échéances.

### 6. Saga Controller

`data/saga_control.yml` enregistre les réponses irréversibles, vérités protégées, dettes héritées, promesse, question centrale, transformation et coût de chaque tome. `saga-control` génère une vue de contrôle inter-tomes.

### Synthèse bêta

`beta-synthesis` agrège les dossiers structurés issus de `beta-feedback`. Plusieurs lecteurs distincts sur un même sujet constituent une convergence à diagnostiquer, jamais une instruction automatique de réécriture.

## Commandes V4

```bash
python scripts/nexus.py reader-map
python scripts/nexus.py experience-map
python scripts/nexus.py mystery-graph
python scripts/nexus.py debt-ledger
python scripts/nexus.py saga-control
python scripts/nexus.py beta-synthesis
```

## Limites et suite du travail

La prose n'est toujours pas interprétée automatiquement : ironie, beauté, originalité, sous-texte implicite, intensité émotionnelle réelle et réception effective exigent une lecture humaine. V4 contrôle la cohérence des **intentions déclarées** et rend visibles des risques de concurrence, de dette ou de surcharge.

L'analyse sémantique complète de continuité, les échéances temporelles automatiques par acte/tome, la mesure fiable du sous-texte, le suivi de tension à partir de la prose et la fusion automatique des retours libres restent hors périmètre.

Le statut `validated` reste choisi par l'auteur, jamais promu automatiquement.

Pour contrôler localement :

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/nexus.py audit
python scripts/nexus.py cockpit
python scripts/nexus.py build
python scripts/nexus.py experience-map
```
