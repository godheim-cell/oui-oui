# Parcours auteur

Nexus cache la complexité autant que possible. L'auteur commence toujours par `COCKPIT_AUTEUR.md`.

## Modes

- `essential` : projet, personnages, chapitres, scènes et reprise.
- `structured` : ajoute continuité, arcs, mystères et promesses.
- `expert` : expose canon, NDR, motifs, connaissances et recherche avancée.

Le mode change l'affichage et les conseils, jamais les données ni les règles du projet.

## Boucle quotidienne

1. `python scripts/nexus.py cockpit`
2. choisir une intention ;
3. `python scripts/nexus.py new-scene --chapter N --title "..."` ;
4. écrire ;
5. `python scripts/nexus.py audit-author` ;
6. `python scripts/nexus.py checkpoint --summary "..." --next "..."`.

## Valeurs incomplètes admises

- `unknown` : décision non prise ;
- `not_applicable` : champ inutile pour ce projet ;
- `due:SCN-042` : décision nécessaire avant cette scène.

Une inconnue explicite est préférable à une invention. Elle ne devient bloquante que lorsqu'elle atteint son échéance ou compromet une scène active.

