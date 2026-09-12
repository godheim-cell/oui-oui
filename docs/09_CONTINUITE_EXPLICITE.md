# Continuité explicite

Les contrôles suivants sont intégrés à `audit` et au rapport `reports/audit-continuite.md`. Ils ne modifient pas les scènes et ne lisent pas leur sens littéraire.

## Dates et causalité

- `date` : date grégorienne YYYY-MM-DD ; les dates impossibles sont signalées.
- `birth_date` facultatif dans un personnage : une apparition avant la naissance est signalée.
- `caused_by` : une cause datée après son effet est signalée, ainsi qu'une scène qui se déclare sa propre cause.
- L'ordre du manifeste n'impose pas l'ordre chronologique : les retours en arrière sont autorisés.
- `unknown` et `not_applicable` ne sont pas convertis en dates inventées. Les calendriers fictifs, voyages temporels et temps propres relativistes exigent une revue humaine ; les règles présentes supposent une chronologie commune ordinaire.

## Connaissances

Champs facultatifs des scènes, listes de dictionnaires `{character: identifiant, fact: clé_stable}` :

- `knowledge_requires` : connaissances nécessaires **à l'entrée** de la scène.
- `knowledge_acquired` : connaissances acquises dans cette scène, disponibles pour les scènes postérieures.

Dans le registre des personnages, `initial_knowledge` contient une liste de clés stables connues avant les événements du récit. Ces clés doivent être identiques pour qu'une correspondance soit reconnue. L'ancien champ libre `knowledge_gained` reste descriptif et n'est pas interprété automatiquement.

Une acquisition datée avant la scène satisfait le prérequis, même si elle apparaît plus tard dans le manifeste. Une acquisition le même jour, ou sans date, produit une alerte d'incertitude : le contrôle ne tranche pas l'ordre des heures. Une acquisition dans la scène elle-même ne justifie pas une connaissance exigée dès son entrée.

Une connaissance sans acquisition antérieure déclarée est signalée, ce qui peut indiquer un oubli de métadonnées plutôt qu'une faute de récit. Ces contradictions sont des alertes en brouillon/révision et des erreurs en scène validée. Les formats invalides sont toujours des erreurs.

## Ce qui n'est pas couvert

La prose n'est pas analysée sémantiquement. Âges exprimés en dialogue, mensonges, croyances erronées, oubli ultérieur, trajets, simultanéité des présences, cycles de plusieurs causes et conséquences implicites restent à relire. Ne pas assimiler une absence d'alerte à une preuve de cohérence. Une lecture assistée doit relever un passage précis, le comparer à une source canonique et soumettre la contradiction à l'auteur.

## Isolation des essais

Les tests reconstruisent des registres vides et une configuration de fixture dans un répertoire temporaire. Ils n'utilisent pas les personnages du roman comme données de test et ne modifient jamais le canon de l'auteur. Le mini-roman SF de vérification n'est pas intégré à la matrice.
