# Nexus V5 — cycle de vie complet d'une œuvre

Nexus V5 généralise les retours d'expérience de projets dérivés sans importer leur canon. Le socle V4 reste inchangé ; cette couche ajoute la gestion d'une saga, du gel éditorial, des campagnes de lecture et des livrables.

## 1. Saga multi-volume

`python scripts/lifecycle.py saga-status` agrège tous les `manuscrit/tome-*/manifest.txt`.

`python scripts/lifecycle.py saga-audit` exécute l'audit Nexus sur l'union des scènes actives, reconnaît les identifiants `THM` et `CHP`, vérifie la couverture déclarée des registres et produit `reports/saga-audit.md` ainsi qu'un JSON exploitable.

`python scripts/lifecycle.py saga-metrics` calcule des métriques de rythme par volume. `saga-cockpit` produit `COCKPIT_SAGA.md` sans remplacer le cockpit quotidien du volume actif.

## 2. Politique des registres

`data/registry_policy.yml` distingue :

- `active` : source structurée réellement utilisée ;
- `workshop` : outil de travail non canonique ;
- `dormant` : capacité disponible mais non activée.

Un registre actif vide à partir de son seuil `required_from` produit une alerte de couverture. Un registre dormant vide n'est jamais interprété comme « zéro problème ».

## 3. Gel, réouverture et release

Le registre `data/lifecycle.yml` conserve l'état par volume et l'empreinte SHA-256 du manuscrit manifesté.

```bash
python scripts/lifecycle.py freeze-volume --volume tome-01 --reason "validation éditoriale" --commit <sha>
python scripts/lifecycle.py release-status --volume tome-01
python scripts/lifecycle.py unfreeze-volume --volume tome-01 --reason "contradiction démontrée"
```

Le gel est refusé si l'audit saga contient des erreurs déterministes. Une réouverture exige une raison et reste tracée dans l'historique.

Pour passer un volume en `released`, il doit être gelé, inchangé depuis le gel et disposer d'un manifeste de publication.

## 4. Publication générique

`python scripts/publication.py --volume tome-01` construit le Markdown et le DOCX depuis les scènes manifestées. Le DOCX porte les métadonnées techniques d'auteur et de titre. Les paramètres de page et de typographie viennent de `[publication]` dans `config/projet.toml`.

`python scripts/publication.py --volume tome-01 --pdf` convertit ensuite ce DOCX en PDF avec LibreOffice. Le PDF n'est donc pas une seconde source éditoriale indépendante.

Chaque exécution régénère `publication/<volume>/MANIFEST.md` avec empreinte source, tailles et SHA-256 des livrables. Les workflows CI publient les binaires comme artefacts GitHub plutôt que de les committer dans la matrice.

## 5. Lecture externe

Les campagnes vivent dans `atelier/lecture-externe/`. Elles sont explicitement de mode `human` ou `simulation`.

Une simulation peut servir de stress-test et déclencher une révision, mais ne peut jamais être présentée comme validation humaine. La règle machine est dans `data/reader_panel_policy.yml`.

## 6. Apports externes

`echanges/` constitue une quarantaine : `inbox/` pour les dépôts bruts, puis analyse, intégration validée ou archivage. Tout apport est NON_CANON par défaut.

## 7. Mémoire et discussions

`MEMOIRE_PROJET.md` porte le contexte éditorial durable. Les cockpits sont des vues générées et peuvent être remplacés.

`discussions/` formalise l'étape entre intuition et décision : une discussion reste NON_CANON jusqu'à sa promotion explicite en NDR ou en donnée structurée validée.

## 8. Principe d'architecture

La règle V5 est : **extraire le mécanisme générique, laisser les données de projet dans le projet dérivé**. Aucun script V5 ne doit contenir de noms, titres, scènes ou règles propres à un roman particulier.
