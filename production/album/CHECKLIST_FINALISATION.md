# Checklist de finalisation — Oui-Oui en vacances au Pays Enchanté

## 1. Texte

- [ ] chaque page reste compréhensible seule ;
- [ ] vocabulaire adapté 3–6 ans ;
- [ ] lecture à voix haute fluide ;
- [ ] répétitions volontaires et non accidentelles ;
- [ ] onomatopées cohérentes : Tin-tin, Pouf, Boïng, Ding/Dong, Tournicoti-tournicota ;
- [ ] aucune page n'explique inutilement l'image ;
- [ ] fin rassurante et promesse de retour claire.

## 2. Continuité visuelle

- [ ] Oui-Oui conserve tenue, bonnet, proportions et lisibilité ;
- [ ] voiture jaune et rouge identique sur toutes les pages ;
- [ ] progression lumineuse matin → jour → coucher de soleil → début de nuit ;
- [ ] personnages secondaires cohérents d'une apparition à l'autre ;
- [ ] le Manège Enchanté reste reconnaissable pages 8 à 12.

## 3. Interactions enfant

- [ ] page 2 : reproduire « Tin-tin ! » ;
- [ ] page 4 : reconnaître des couleurs ;
- [ ] page 6 : choisir le panneau différent ;
- [ ] page 9 : compter les étoiles ;
- [ ] aucune interaction ne bloque la compréhension de l'histoire.

## 4. Équilibre émotionnel

- [ ] page 5 crée une petite incertitude sans peur ;
- [ ] page 6 donne une résolution rapide ;
- [ ] page 8 marque clairement la récompense du voyage ;
- [ ] page 10 constitue le pic merveilleux ;
- [ ] page 11 ralentit le rythme ;
- [ ] page 12 ferme l'histoire avec sécurité.

## 5. Maquette

- [ ] zones de texte prévues avant rendu final des illustrations ;
- [ ] aucun texte dans la reliure ou trop près des bords ;
- [ ] aucune information essentielle sous le texte ;
- [ ] taille typographique lisible en impression réelle ;
- [ ] vue miniature cohérente sur les 12 pages ;
- [ ] couverture lisible en petite vignette.

## 6. Production images

Pour chaque page :

- [ ] brief validé ;
- [ ] composition validée ;
- [ ] continuité personnage/voiture validée ;
- [ ] zone texte suffisante ;
- [ ] version haute résolution conservée ;
- [ ] fichier final nommé selon la scène (`SCN-001` à `SCN-012`).

## 7. Contrôle Nexus

Avant gel :

```bash
python -m unittest discover -s tests -v
python scripts/nexus.py audit
python scripts/nexus.py cockpit
python scripts/nexus.py build
python scripts/lifecycle.py saga-audit
```

Le passage de cette checklist ne transforme pas automatiquement le projet en `validated` : la validation finale reste une décision humaine.
