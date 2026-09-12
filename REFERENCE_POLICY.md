# Politique de référence — projet Oui-Oui

## Source du modèle

Le dépôt est dérivé de `godheim-cell/Nexus` à partir de Nexus V5, commit source :

`75486eb2cd2b816277c985123886c4b818e791a5`

Les scripts centraux, workflows, tests et templates importés conservent autant que possible les mêmes contenus et empreintes que cette version source. Les fichiers propres au roman — configuration, canon, registres remplis, manuscrit, mémoire et cockpit — sont volontairement spécialisés.

## Séparation des responsabilités

- `godheim-cell/Nexus` reste la matrice de référence protégée.
- `godheim-cell/oui-oui` est un projet dérivé et peut être modifié selon les demandes de l’auteur.
- Aucune modification de `oui-oui` ne doit être propagée automatiquement vers Nexus.
- Une amélioration générique jugée utile à Nexus doit être proposée séparément dans le cadre de la politique de validation de Nexus.

## Sources de vérité du projet

- `config/projet.toml` : configuration active.
- `data/canon.yml` : faits et règles canoniques.
- `data/*.yml` : registres narratifs structurés.
- `manuscrit/tome-01/manifest.txt` : ordre des scènes actives.
- `manuscrit/tome-01/` : prose active.
- `MEMOIRE_PROJET.md` : état durable et décisions de travail.
- `decisions/` : décisions durables formalisées.
- `recherches/` : matériaux non canoniques tant qu’ils ne sont pas validés et propagés.

## Contrôle d’intégrité

Toute modification structurante doit préserver les contrôles Nexus V5. Le workflow `Nexus integrity` doit rester vert avant gel ou publication. Les sorties de CI, audits et publications sont des artefacts dérivés ; elles ne remplacent pas les sources de vérité.

## Propriété intellectuelle et publication

Ce dépôt contient un projet utilisant des personnages et univers préexistants. Toute diffusion ou publication externe doit faire l’objet d’une vérification distincte des droits applicables ; la présence du projet dans ce dépôt ne vaut pas autorisation d’exploitation commerciale.
