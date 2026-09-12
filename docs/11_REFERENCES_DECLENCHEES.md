# Recherche de références déclenchée par les entrées du roman

Le [suivi croisé et les exercices](12_RECHERCHE_CROISEE.md) complètent ce protocole. Le cockpit et `reference-sync` présentent désormais un dossier commun au projet. Traiter ce dossier courant, pas ses demandes élémentaires archivées.

## Déclencheurs

`new-concept --name`, `new-theme --name`, `genre-profile --genre` et `setup --genre` génèrent une demande en attente lors de la mise à jour du cockpit. Les modifications manuelles des noms/définitions dans les registres sont détectées au prochain `cockpit` ou `reference-sync`. Il n'y a pas de surveillance permanente du disque.

Les registres sont `data/concepts.yml`, `data/themes.yml`, `data/genre_contract.yml` et le genre de `config/projet.toml`. Les entrées vides/provisoires ne déclenchent rien. Une même catégorie, un même nom normalisé et une même définition ne produisent pas de doublon. Une définition différente crée une nouvelle demande et conserve l'historique ; les anciennes demandes concernées deviennent `stale` au prochain passage.

```bash
python scripts/nexus.py new-theme --name "Thème choisi par l’auteur"
python scripts/nexus.py reference-sync
```

## Travail obligatoire de l'assistant connecté

1. Lire le sujet, sa définition et le projet pour distinguer concept intellectuel, thème dramatique et convention de genre. En cas d'ambiguïté, présenter plusieurs interprétations plutôt que sélectionner silencieusement une seule.
2. Exécuter les requêtes proposées, en les adaptant au besoin, puis ouvrir les sources. Privilégier œuvres, entretiens d'auteurs, éditeurs, bibliothèques et travaux universitaires. Une notice ou une critique lue n'équivaut pas à la lecture de l'œuvre.
3. Chercher un ensemble court de références pertinentes : viser 3 à 5 auteurs, avec un précurseur, une approche différente et une référence moins évidente quand les sources le justifient. Ne pas remplir un quota avec des auteurs peu pertinents.
4. Pour chaque auteur : œuvres précises, lien avec le sujet, procédé documenté, application possible au roman et limites de cette influence. Pour un concept, distinguer penseurs du concept et romanciers qui le mettent en scène. Pour un thème, comparer des positions opposées. Pour un genre, comparer promesses de lecture et transgressions.
5. Séparer les éléments établis par les sources des propositions d'application de l'assistant. Indiquer les œuvres non lues, sources inaccessibles et incertitudes. Ne pas imiter une voix ni transformer une recommandation en préférence de l'auteur.
6. Présenter une courte sélection argumentée à l'auteur. Conserver les résultats dans `recherches/`, les sources utiles dans `data/sources.yml` et les influences retenues via `new-influence` si l'auteur les adopte. La recherche reste NON_CANON.

La création automatique de la demande n'effectue aucune navigation : le script n'embarque ni moteur de recherche ni clé d'API. L'assistant connecté doit réellement chercher dans la séance conformément à AGENTS.md. Sans accès web, laisser pending et expliquer le blocage.

## Résultat structuré et clôture

Les demandes sont dans `recherches/reference-requests/`. Après recherche réelle, écrire un résultat JSON dans `recherches/` :

```json
{
  "request_id": "IDENTIFIANT_DE_LA_DEMANDE",
  "authors": [{
    "name": "Nom vérifié",
    "role": "central",
    "works": ["Titre vérifié"],
    "relevance": "Lien étayé avec le sujet",
    "technique": "Procédé documenté, avec limites d'accès au texte",
    "application": "Proposition narrative de l'assistant, non canonique",
    "limits": "Distance à conserver et incertitudes",
    "claim_sources": {"relevance": [0], "technique": [0]},
    "sources": [{
      "url": "https://adresse-reelle-de-la-source",
      "accessed": "date réelle de consultation",
      "reading_status": "read",
      "material": "commentary",
      "evidence": "Affirmation soutenue par la page effectivement ouverte"
    }]
  }]
}
```

Les valeurs ci-dessus sont des indications de format, jamais des références à enregistrer telles quelles.

```bash
python scripts/nexus.py reference-complete --id IDENTIFIANT --file recherches/resultat.json
```

La clôture contrôle les champs, l'association à la demande, les dates de consultation, les doublons par auteur et les indices reliant affirmations et sources. Elle ne vérifie pas la véracité des affirmations ni la visite des liens. Cette responsabilité appartient à l'assistant et à l'auteur. Les références ne sont pas rafraîchies automatiquement au fil du temps.
