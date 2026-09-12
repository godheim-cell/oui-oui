# Recherche croisée et passage à l'écriture

## Un dossier courant par projet

`reference-sync` regroupe les concepts, thèmes, genres et `[project] intention` dans un dossier de type `project`. L'intention est facultative et doit être renseignée par l'auteur. Les requêtes contiennent ces éléments ; l'assistant les affine plutôt que d'envoyer une longue concaténation sans discernement. Aucun texte de scène n'entre dans ces requêtes.

Après plusieurs ajouts, synchroniser puis traiter uniquement le dossier courant. Les dossiers intermédiaires restent historiques et passent à `stale`. Le système ne contient pas de minuterie : le regroupement est un état du projet à la synchronisation. Pour éviter des recherches répétées, l'assistant rassemble les ajouts d'une même demande utilisateur avant de naviguer.

Les résultats précédents sont listés dans `reuse_results` : les relire et réutiliser les sources encore pertinentes. Cette liste n'effectue ni réévaluation automatique des sources ni déduplication sémantique entre études. Le statut `stale` signifie « contexte changé, à réexaminer », pas « affirmation devenue fausse ». Un changement de nom, définition, ajout, retrait ou intention est détecté à la synchronisation. Un retour à un contexte antérieur demande une nouvelle revue ; les résultats historiques sont conservés.

## Suivi

États : `pending`, `in_progress`, `blocked`, `completed`, `stale`.

```bash
python scripts/nexus.py reference-sync
python scripts/nexus.py reference-state --id IDENTIFIANT --status in_progress --reason "Début de consultation"
python scripts/nexus.py reference-state --id IDENTIFIANT --status blocked --reason "Source inaccessible"
```

Une raison est obligatoire pour les transitions manuelles et l'historique est conservé. `completed` exige `reference-complete`. `stale` est attribué par synchronisation. Une demande terminée ou périmée ne peut pas être relancée par une simple transition. La synchronisation détecte le contexte à actualiser. Un blocage reste visible dans le cockpit.

## Sélection et preuves

Chaque auteur du résultat porte un `role` : `central`, `counterpoint` ou `unexpected`. Sa pertinence doit expliquer le choix. Il n'est pas obligatoire de remplir les trois catégories si les sources ne le justifient pas.

Chaque source consultée précise `material` : `work` pour une œuvre, `excerpt` pour un extrait, `commentary` pour un entretien, une notice ou une étude sur l'œuvre. `reading_status: read` concerne ce document, jamais une œuvre simplement évoquée. `accessed` est une date réelle YYYY-MM-DD, valide et non future.

`claim_sources` relie `relevance` et `technique` aux positions des sources de l'auteur, à partir de zéro. Les positions inexistantes, auteurs dupliqués et URL répétées par auteur sont refusés. Une même source peut légitimement documenter plusieurs auteurs. Les contrôles ne visitent pas les liens et ne prouvent pas les affirmations. L'assistant doit réellement les ouvrir et distinguer application proposée et procédé attesté.

## Exercices et arbitrages

Après clôture, le résultat est copié dans un fichier distinct sous `recherches/reference-results/` et un dossier sous `atelier/exercices/` propose, pour chaque référence, un essai à partir de son procédé et de l'application renseignés. L'auteur choisit la scène, l'effet recherché et un axe de variante. Le dossier n'écrit pas de prose et ne touche pas au manuscrit.

```bash
python scripts/nexus.py reference-decide --id IDENTIFIANT --author "Nom exact du résultat" --decision accept --reason "Apport recherché" --scope "Ce projet, passages de révélation"
```

Arbitrages : `accept`, `reject`, `defer`. Nom présent dans le résultat, raison et portée sont requis. Le journal `recherches/reference-decisions.jsonl` est cumulatif. Relire les arbitrages pertinents avant toute nouvelle sélection ; en cas de changements, expliquer les raisons. Ces choix ne sont pas appliqués comme une exclusion globale automatique et ne constituent pas un profil figé de l'auteur.

## Compatibilité

Les anciens résultats restent consultables. Une nouvelle clôture exige le format enrichi (rôle, nature du document, liens affirmation-source). Les demandes élémentaires sont conservées pour la traçabilité, mais le parcours utilisateur traite désormais le dossier de projet. Les fichiers JSON conservés ne sont pas verrouillés contre une modification manuelle ; éviter de les réécrire et utiliser de nouveaux résultats pour les mises à jour.
