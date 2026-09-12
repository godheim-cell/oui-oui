# Gouvernance, statuts et décisions

## Statuts standard

`NON_CANON`, `RECHERCHE`, `HYPOTHESE`, `PROPOSE`, `EXPERIMENTAL`, `VALIDE`, `CANON`, `PROTEGE`, `REMPLACE`, `ABANDONNE`, `DERIVE`.

## Règles

- Un document possède une fonction dominante.
- Une vérité canonique a un identifiant stable.
- Une décision structurante possède un NDR dans `decisions/`.
- Une décision remplacée n'est jamais effacée : elle pointe vers son successeur.
- Les rapports et contextes générés sont dérivés.
- L'existence d'une scène ne la rend pas active : seul le manifeste fixe l'ordre officiel.
- Toute contradiction détectée devient une dette ou une décision, jamais une correction silencieuse.

## NDR

Format : contexte → options → décision → conséquences → éléments à propager → statut.

## Définition de « prêt »

Une scène est prête si ses métadonnées sont complètes, son changement est perceptible, ses conséquences sont enregistrées et elle ne viole aucun invariant bloquant. Un chapitre est prêt si toutes ses scènes sont prêtes, sa promesse progresse et sa sortie rend la suite nécessaire.

