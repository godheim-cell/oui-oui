# Politique des registres Nexus

Les fichiers de `data/` n'ont pas tous le même statut. Un registre vide ne signifie jamais automatiquement « aucun problème ».

La source machine de cette politique est `data/registry_policy.yml`.

## Modes

- `active` : registre utilisé comme source structurée de contrôle. À partir de son état `required_from`, une vacuité déclenche une alerte de couverture.
- `workshop` : registre utile à l'atelier mais non canonique. Il ne constitue pas une preuve de conformité.
- `dormant` : capacité disponible mais non activée. Sa vacuité est un état assumé, pas un résultat d'audit.

## Règle d'interprétation

Un indicateur n'est probant que si sa source de données est renseignée et que son mécanisme de contrôle est identifié. Les rapports et cockpits doivent distinguer absence d'anomalie, absence de données et contrôle non applicable.

## Lecteurs

`reader_profiles.yml` est un registre d'atelier. Les simulations doivent rester étiquetées comme simulations et ne peuvent pas être présentées comme une validation humaine. Voir `reader_panel_policy.yml`.
