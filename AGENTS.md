# Instructions de collaboration IA — Oui-Oui

## Projet dérivé de Nexus V5

Ce dépôt est un projet romanesque dérivé de `godheim-cell/Nexus`, version source `75486eb2cd2b816277c985123886c4b818e791a5` (Nexus V5). Il peut évoluer lorsque l’auteur demande une modification. Il ne doit jamais modifier le dépôt Nexus en retour.

## Avant toute modification

1. Lire `COCKPIT_AUTEUR.md`, `config/projet.toml`, `docs/01_GOUVERNANCE.md`, `docs/14_PROJET_OUI_OUI.md` et le manifeste actif.
2. Identifier la source de vérité visée.
3. Distinguer fait canonique, hypothèse, décision, recherche et artefact dérivé.
4. Ne jamais inventer un fait manquant pour combler un registre.
5. Préserver le fonctionnement des scripts/tests Nexus V5 ; toute adaptation du moteur doit être explicitement justifiée et testée.

## Recherche et influences

- À l’introduction ou au changement d’un concept, thème ou genre, lancer `reference-sync` ou traiter les demandes de référence créées par le cockpit.
- Effectuer une vraie recherche externe avant d’inscrire des références factuelles ou des auteurs comme sources du projet.
- Séparer fait, interprétation, hypothèse et invention.
- Enregistrer les sources dans `data/sources.yml` et les développements dans `recherches/`.
- Pour une influence, extraire fonctions et procédés observables ; ne pas imiter une voix, des tournures reconnaissables, des personnages ou une intrigue protégée.
- Un résultat de recherche reste `NON_CANON` jusqu’à validation et propagation explicites.

## Écriture jeunesse

- Respecter `docs/02_CHARTE_LITTERAIRE.md` et `docs/14_PROJET_OUI_OUI.md`.
- Public cible : 3–6 ans.
- Chaque page/scène doit produire un changement simple et visible.
- Le merveilleux reste doux et rassurant.
- Les interactions enfant doivent rester ponctuelles et naturelles.
- Le texte doit laisser une part narrative réelle à l’illustration.
- Signaler les contradictions ; ne pas les résoudre silencieusement.
- Ne jamais réécrire automatiquement la voix uniquement pour satisfaire un score.

## Fin de tâche

Après modification du moteur, des registres, du manifeste ou d’une scène :

1. lancer `python scripts/nexus.py audit` ;
2. régénérer le cockpit ;
3. lancer `python scripts/nexus.py build` si le manifeste ou une scène a changé ;
4. vérifier la CI `Nexus integrity` ;
5. mettre à jour une NDR si une décision durable de production est prise.
