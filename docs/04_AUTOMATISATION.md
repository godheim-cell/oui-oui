# Architecture d'automatisation

## Ce qui est automatique

- création normalisée des scènes ;
- validation des métadonnées obligatoires ;
- unicité et format des identifiants ;
- vérification du manifeste ;
- liens internes et références croisées ;
- chronologie et ordre simples ;
- inventaire des placeholders ;
- suivi des promesses, indices, révélations et dettes ;
- statistiques de longueur et densité ;
- génération du tableau de bord et du manuscrit consolidé ;
- contrôle continu à chaque push et pull request.

## Ce qui reste humain

Voix, beauté, vérité émotionnelle, choix de variante, valeur d'un symbole, force d'une révélation, canonisation et réécriture de prose.

## Niveaux

- `ERROR` : invariant cassé ; bloque l'intégration.
- `WARN` : risque éditorial ; n'empêche pas le travail.
- `INFO` : mesure ou suggestion.

## Convention de métadonnées

Les fichiers structurés utilisent YAML simple. Les scènes utilisent un front matter entre `---`. Les identifiants ne changent jamais après publication interne.

