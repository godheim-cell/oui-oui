# Atelier éditorial — contrat des fonctions

## Révisions réversibles

```bash
python scripts/nexus.py snapshot --id SCN-001 --reason "Avant essai de révision"
python scripts/nexus.py snapshot-compare --snapshot atelier/snapshots/IDENTIFIANT.json
python scripts/nexus.py snapshot-restore --snapshot atelier/snapshots/IDENTIFIANT.json --expected-sha EMPREINTE_ACTUELLE --reason "Retour après comparaison"
```

Les identifiants et empreintes doivent être copiés des sorties réelles. L'instantané conserve le fichier entier, y compris ses métadonnées, dans un fichier distinct. La comparaison indique l'empreinte actuelle et les différences. La restauration exige cette empreinte : si la scène a changé entre-temps, elle est refusée. Une sauvegarde de l'état remplacé est créée avant restauration. Elle permet de revenir sur cette restauration avec le même parcours.

Ne pas lancer plusieurs restaurations concurrentes : les vérifications ne constituent pas un verrou multi-processus. Ne pas modifier manuellement les instantanés. Leur empreinte contrôle l'intégrité du texte, pas une authenticité cryptographique contre un tiers malveillant.

L'adoption d'une variante reste une édition manuelle : instantané → modification → comparaison → audit → décision. `impact --id` aide à retrouver les références explicites ; les dépendances sémantiques ne sont pas calculées. Après restauration, relancer audit, cockpit et build. Restaurer une ancienne scène restaure aussi son ancien statut : cela ne certifie pas sa validité dans le roman actuel.

## Cockpit ciblé

```bash
python scripts/nexus.py cockpit --focus exploration
python scripts/nexus.py cockpit --focus writing
python scripts/nexus.py cockpit --focus revision
```

Exploration propose une question et une décision ouverte ; écriture indique par défaut la dernière scène du manifeste ; révision affiche aussi les alertes non bloquantes. Les erreurs restent visibles dans tous les focus, avec le plafond de priorités configuré et le nombre total de constats. L'audit lui-même reste complet.

Sans argument, `[author] focus` est utilisé, ou `exploration` par défaut. `--focus` ne modifie pas la configuration. Les anciens modes `essential/structured/expert` restent des étiquettes, indépendantes du focus.

## V4 — expérience lecteur

```bash
python scripts/nexus.py reader-map
python scripts/nexus.py experience-map
python scripts/nexus.py mystery-graph
python scripts/nexus.py debt-ledger
python scripts/nexus.py saga-control
python scripts/nexus.py beta-synthesis
```

### Reader State Engine

`reader-map` produit une carte détaillée par scène : question dominante avant/après, savoir lecteur, croyances, ancrage humain, charge, état émotionnel et dette narrative. Ces champs sont déclaratifs : ils décrivent l'effet visé et doivent être confrontés aux retours externes.

### Cognitive Load Guard

`audit` contrôle les blocs `cognitive_load` lorsqu'ils existent dans les métadonnées de scène. Il signale notamment : trop de mystères actifs, concepts, noms ou règles nouvelles ; plusieurs révélations majeures ; absence de focus dominant ; score de charge supérieur au seuil du projet.

Les seuils sont définis dans `data/experience_model.yml`. Ils indiquent une zone à relire, jamais une obligation de couper.

### Mystery Graph

`mystery-graph` croise `data/mysteries.yml` et les blocs `mystery_state` des scènes. Les états admis sont : `active`, `deferred`, `dormant`, `resolved`. Une même scène ne doit pas attribuer plusieurs états incompatibles au même mystère.

### Emotional Continuity

Le bloc `emotional_continuity` suit l'état du POV à l'entrée et à la sortie, le déplacement relationnel et le coût incarné. Une révélation majeure sans coût ou déplacement relationnel produit une alerte de révision.

### Narrative Debt Ledger

`debt-ledger` croise `data/narrative_debt.yml` et les scènes. Une dette possède une création, une gravité, une échéance, un statut et un prochain test. L'objectif est d'empêcher une saga de prolonger indéfiniment un mystère simplement parce qu'il reste attractif.

### Saga Controller

`saga-control` lit `data/saga_control.yml` : promesse de chaque tome, question centrale, transformation du héros, coût, réponses irréversibles, dettes héritées et vérités protégées. Le principe est : agrandir et recontextualiser, ne pas annuler sans préparation.

## Carte lecteur et conséquences du monde

```bash
python scripts/nexus.py reader-map
python scripts/nexus.py world-consequences --subject "Postulat à explorer"
```

Le laboratoire du monde prépare les questions de coût, maintenance, pouvoir, vie quotidienne, alternatives et conséquences indirectes. Il ne génère pas de réponses, ne recherche pas de sources et ne simule pas une société.

## Retours, preuves et mémoire éditoriale

```bash
python scripts/nexus.py beta-feedback --id SCN-001 --quote "PASSAGE EXACT" --reader "Pseudonyme" --reaction confusion --subject "Retour du lecteur"
python scripts/nexus.py evidence-review --id SCN-001 --quote "PASSAGE EXACT" --reference data/canon.yml --reference-quote "PASSAGE EXACT DE RÉFÉRENCE" --subject "Contradiction supposée"
python scripts/nexus.py voice-decision --id SCN-001 --quote "PASSAGE EXACT" --decision accept --reason "Raison explicite de l’auteur"
python scripts/nexus.py beta-synthesis
```

Ces commandes refusent les passages absents de leurs fichiers. Chaque dossier conserve une copie de la scène et son empreinte ; la revue avec preuve conserve également le passage et l'empreinte du fichier de référence. Les dossiers JSON sont distincts, non canoniques, éditables dans `atelier/editorial/`.

- Bêta-lecture : réaction parmi confusion/ennui/emotion/anticipation ; décision pending/accept/test/reject/defer, interprétation, action et résultat à compléter. Aucune invitation ou transmission du manuscrit n'est effectuée. Utiliser des pseudonymes ; ne pas publier ces retours sans accord.
- `beta-synthesis` regroupe les retours structurés par scène, réaction et sujet. Deux lecteurs distincts ou plus produisent seulement la mention `convergence à examiner` : cela déclenche un diagnostic, jamais une réécriture automatique.
- Relecture avec preuves : hypothèse, explications alternatives et question à l'auteur. La présence de deux passages ne prouve pas une contradiction. Aucune extraction sémantique autonome.
- Mémoire éditoriale : passage, arbitrage explicite, raison, portée locale et révisabilité. Pas d'apprentissage automatique des goûts, de recherche automatique d'arbitrages similaires ou de règle globale déduite.

Les fonctions V4 rendent l'expérience projetée, les dettes et les convergences visibles ; elles ne remplacent ni la lecture humaine ni le jugement de l'auteur.
