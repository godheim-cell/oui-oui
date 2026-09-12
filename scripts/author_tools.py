"""Parcours auteur V3/V5 : sorties non canoniques, aucune prose modifiée."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime, timezone
import yaml


def create(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    base = path
    number = 2
    while path.exists():
        path = base.with_name(f"{base.stem}-{number}{base.suffix}")
        number += 1
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
    return path


def visible_text(path):
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) != 3:
            raise ValueError("Front matter incomplet")
        text = parts[2]
    return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()


def active_scenes(root, volume=None):
    import tomllib
    cfg = tomllib.loads((root / "config/projet.toml").read_text())
    manifest = root / "manuscrit" / volume / "manifest.txt" if volume else root / cfg["manuscript"]["manifest"]
    if not manifest.is_file():
        raise ValueError(f"Manifeste introuvable : {manifest.relative_to(root)}")
    result = []
    for line in manifest.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        path = (root / line.strip()).resolve()
        if not path.is_relative_to((root / cfg["manuscript"]["root"]).resolve()) or not path.is_file():
            raise ValueError(f"Chemin de scène invalide : {line}")
        if path in result:
            raise ValueError(f"Scène dupliquée : {line}")
        result.append(path)
    return result


def dispatch(argv, root):
    commands = {"creative-interview", "variant-lab", "impact", "reader-pack", "influence-note", "research-brief"}
    if argv[0] not in commands:
        return False
    parser = argparse.ArgumentParser(prog=f"nexus {argv[0]}")
    parser.add_argument("--subject", default="Intuition à explorer")
    parser.add_argument("--id")
    parser.add_argument("--through", type=int, default=1)
    parser.add_argument("--volume")
    parser.add_argument("--spoilers", action="store_true")
    parser.add_argument("--axis", choices=["pov", "information", "rythme", "dialogue", "sensation"], default="information")
    args = parser.parse_args(argv[1:])
    command = argv[0]
    text = "# Atelier auteur — NON CANON\n\n"
    if command == "creative-interview":
        questions = ["Qu'est-ce qui te fascine ?", "Quelle contradiction explorer ?", "Qui en souffrirait concrètement ?", "Quel choix serait impossible ?", "Quelle expérience offrir au lecteur ?"]
        text += args.subject + "\n\n"
        for question in questions:
            text += f"## {question}\n\nÀ renseigner.\n\n"
        text += "## Trois propositions à construire avec l'assistant\n\nPour chaque piste : prémisse, protagoniste, conflit, coût, singularité, risque, décisions ouvertes. Les propositions doivent différer par leur moteur dramatique. Aucune génération automatique ici.\n"
    elif command == "variant-lab":
        if not args.id:
            parser.error("--id SCN-xxx requis")
        candidates = [p for p in active_scenes(root, args.volume) if p.name.startswith(args.id + "-")]
        if len(candidates) != 1:
            raise ValueError("Une scène active unique est requise")
        source = candidates[0]
        text += f"Source : {source.relative_to(root)}\nEmpreinte SHA256 : {hashlib.sha256(source.read_bytes()).hexdigest()}\nAxe unique : {args.axis}\n\n## Original de référence\n\n{visible_text(source)}\n\n## Variante A\n\nÀ écrire.\n\n## Variante B\n\nÀ écrire.\n\n## Comparaison humaine\n\nClarté, émotion, tension, voix, fidélité aux faits. Choix et justification : à renseigner. Aucun remplacement automatique.\n"
    elif command == "impact":
        if not args.id or not re.fullmatch(r"[A-Z]+-\d{3,4}", args.id):
            parser.error("--id valide requis")
        pattern = re.compile(rf"\b{re.escape(args.id)}\b")
        text += f"## Références explicites à {args.id}\n\n"
        for directory in ["data", "manuscrit", "decisions", "recherches"]:
            for path in sorted((root / directory).rglob("*")):
                if path.is_file() and path.suffix in {".md", ".yml", ".json"}:
                    if pattern.search(path.read_text(encoding="utf-8")):
                        text += f"- `{path.relative_to(root)}`\n"
        text += "\nRevoir aussi les conséquences implicites : âges, souvenirs, trajets, relations et causalité. Cette recherche textuelle n'est pas un graphe sémantique exhaustif.\n"
    elif command == "reader-pack":
        paths = active_scenes(root, args.volume)
        if args.through < 1 or args.through > len(paths):
            raise ValueError("--through doit désigner une position existante du manifeste")
        text = "# Dossier lecteur\n\n"
        if args.volume:
            text += f"Volume : `{args.volume}`\n\n"
        for path in paths[:args.through]:
            text += visible_text(path) + "\n\n"
        text += "## Questions de lecture\n\nQue comprends-tu ? Que soupçonnes-tu ? Qu'attends-tu ? Où hésites-tu entre mystère et confusion ? Appuie chaque retour sur le texte.\n"
        if args.spoilers:
            text += "\n## ATTENTION — CANON AUTEUR / SPOILERS\n\n" + (root / "data/canon.yml").read_text()
        else:
            text += "\nLes métadonnées, commentaires et scènes suivantes sont exclus. Ne pas joindre le canon à cette lecture. Aucun filtre ne peut retirer un spoiler déjà présent dans la prose.\n"
    elif command == "influence-note":
        text += f"## Référence : {args.subject}\n\nŒuvre, édition/traduction, passage réellement lu :\n\nCe qui m'a marqué :\n\nCe que je veux apprendre :\n\nCe que je refuse de reproduire :\n\nProcédé observable :\n\nExpérience dans mon texte :\n\nVerdict après essai :\n\nLa note recueille les préférences de l'auteur ; elle ne les invente pas.\n"
    else:
        text += f"## Mandat : {args.subject}\n\nDécision d'écriture à éclairer :\nBudget de recherche :\nCritère d'arrêt : décision suffisamment éclairée et désaccords importants identifiés.\n\n## Protocole de recherche assistée\n\n1. Construire 3 questions et une requête contradictoire.\n2. Chercher avec les accès disponibles ; ne pas téléverser le manuscrit.\n3. Ouvrir les sources utiles et consigner les limites d'accès.\n4. Marquer chaque source : repérée / lue / inaccessible.\n5. Relier chaque affirmation à son passage et à une application narrative.\n6. Proposer une décision sans la canoniser.\n\n| Affirmation | Source et passage | État de lecture | Désaccord | Effet sur le roman |\n|---|---|---|---|---|\n\nCette commande prépare le mandat ; elle n'effectue ni navigation ni analyse IA autonome.\n"
    slug = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = create(root, f"atelier/v3/{command}-{slug}.md", text)
    print(output.relative_to(root))
    return True
