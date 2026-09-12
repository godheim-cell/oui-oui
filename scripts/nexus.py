#!/usr/bin/env python3
"""Nexus: outillage déterministe d'un dépôt romanesque (PyYAML)."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
import unicodedata
import yaml
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"\b(CHR|LOC|SCN|EVT|MYS|PRO|OBJ|REL|ARC|DEBT|NDR|SRC|CON|INF|GEN)-\d{3,4}\b")
PLACEHOLDERS = ("A_DEFINIR", "TITRE_DU_ROMAN", "YYYY-MM-DD", "HH:MM", "CHR-000", "LOC-000")
REQUIRED_SCENE = ("id", "title", "status", "chapter", "order", "pov", "location", "date", "change", "consequence", "reader_hook")


@dataclass
class Finding:
    level: str
    code: str
    path: str
    message: str


def config() -> dict:
    with (ROOT / "config/projet.toml").open("rb") as handle:
        return tomllib.load(handle)


def parse_value(value: str):
    value = value.strip()
    if value in {"null", "~"}: return None
    if value.lower() in {"true", "false"}: return value.lower() == "true"
    if value.startswith("["):
        try: return ast.literal_eval(value)
        except (ValueError, SyntaxError): return [x.strip().strip('"\'') for x in value[1:-1].split(",") if x.strip()]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try: return int(value)
    except ValueError: return value


def frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return {}, text
    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise ValueError(f"{path}: métadonnées attendues sous forme de dictionnaire")
    return data, parts[2]


def scene_files() -> list[Path]:
    return sorted(p for p in (ROOT / "manuscrit").rglob("*.md") if p.name.startswith("SCN-"))


def manifest_paths() -> list[Path]:
    path = ROOT / config()["manuscript"]["manifest"]
    if not path.exists(): return []
    return [ROOT / line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def yaml_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [str(row['id']) for row in registry_rows(path) if 'id' in row]


def audit() -> list[Finding]:
    findings: list[Finding] = []
    scenes = scene_files()
    ids: dict[str, str] = {}
    cfg = config()
    q = cfg["quality"]

    for path in scenes:
        rel = str(path.relative_to(ROOT))
        try:
            meta, body = frontmatter(path)
        except (yaml.YAMLError, ValueError) as exc:
            findings.append(Finding("ERROR", "SCENE_FRONTMATTER", rel, str(exc)))
            continue
        if not meta:
            findings.append(Finding("ERROR", "SCENE_FRONTMATTER", rel, "Métadonnées de scène absentes ou invalides."))
            continue
        editorial_level = "ERROR" if meta.get("status") in {"validated", "CANON", "VALIDE"} else "WARN"
        for field in ('chapter', 'order'):
            if type(meta.get(field)) is not int or meta[field] < 1:
                findings.append(Finding("ERROR", "SCENE_TYPE", rel, f"{field}: entier positif requis."))
        for field in ('characters', 'caused_by', 'goals', 'clues', 'knowledge_gained'):
            if field in meta and not isinstance(meta[field], list):
                findings.append(Finding("ERROR", "SCENE_TYPE", rel, f"{field}: liste requise."))
        if meta.get("status") not in {"draft", "revision", "validated", "CANON", "VALIDE"}:
            findings.append(Finding("ERROR", "STATUS", rel, "Statut de scène inconnu."))
        for key in REQUIRED_SCENE:
            if key not in meta or meta[key] in (None, "", []):
                findings.append(Finding(editorial_level, "SCENE_FIELD", rel, f"Champ obligatoire manquant: {key}."))
        for key, value in meta.items():
            if any(marker in str(value) for marker in PLACEHOLDERS) or value == "unknown":
                findings.append(Finding(editorial_level, "PLACEHOLDER", rel, f"Valeur provisoire dans {key}: {value}."))
        sid = str(meta.get("id", ""))
        if not re.fullmatch(r"SCN-\d{3,4}", sid):
            findings.append(Finding("ERROR", "SCENE_ID", rel, f"Identifiant invalide: {sid!r}."))
        elif sid in ids:
            findings.append(Finding("ERROR", "DUPLICATE_ID", rel, f"{sid} existe déjà dans {ids[sid]}."))
        else: ids[sid] = rel
        if sid and not path.name.startswith(sid):
            findings.append(Finding("ERROR", "FILENAME_ID", rel, "Le nom du fichier ne commence pas par l'ID de la scène."))
        words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", body))
        if words < q["minimum_scene_words"]:
            findings.append(Finding("WARN", "SCENE_SHORT", rel, f"Scène courte: {words} mots."))
        if words > q["maximum_scene_words"]:
            findings.append(Finding("WARN", "SCENE_LONG", rel, f"Scène longue: {words} mots."))
        for field in ("change", "consequence", "reader_hook"):
            if str(meta.get(field, "")).upper() in {"", "A_DEFINIR"}:
                findings.append(Finding(editorial_level, "DRAMA_FIELD", rel, f"{field} doit être explicite."))

    active = manifest_paths()
    if not (ROOT / cfg['manuscript']['manifest']).is_file():
        findings.append(Finding("ERROR", "MANIFEST_MISSING", cfg['manuscript']['manifest'], "Manifeste absent."))
    seen_manifest = set()
    for path in active:
        if not path.resolve().is_relative_to((ROOT / cfg['manuscript']['root']).resolve()):
            findings.append(Finding("ERROR", "MANIFEST_PATH", str(path), "Chemin hors manuscrit."))
            continue
        rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        if rel in seen_manifest:
            findings.append(Finding("ERROR", "MANIFEST_DUPLICATE", rel, "Chemin dupliqué dans le manifeste."))
        seen_manifest.add(rel)
        if not path.exists(): findings.append(Finding("ERROR", "MANIFEST_MISSING", rel, "Scène active introuvable."))
    for path in scenes:
        if path not in active:
            findings.append(Finding("WARN", "ORPHAN_SCENE", str(path.relative_to(ROOT)), "Scène absente du manifeste actif."))

    registry_files = list((ROOT / "data").glob("*.yml"))
    declared = set()
    for file in registry_files:
        try:
            value = yaml.safe_load(file.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Un dictionnaire racine est requis")
        except (yaml.YAMLError, ValueError) as exc:
            findings.append(Finding("ERROR", "REGISTRY_YAML", str(file.relative_to(ROOT)), str(exc)))
            continue
        for item in yaml_ids(file):
            if item in declared:
                findings.append(Finding("ERROR", "DUPLICATE_REGISTRY_ID", str(file.relative_to(ROOT)), f"ID dupliqué: {item}."))
            declared.add(item)
    declared.update(ids)
    for path in scenes:
        all_refs = set(m.group(0) for m in ID_RE.finditer(path.read_text(encoding="utf-8")))
        for ref in sorted(all_refs - declared):
            if ref.endswith("-000"): continue
            findings.append(Finding("WARN", "UNKNOWN_REFERENCE", str(path.relative_to(ROOT)), f"Référence non déclarée: {ref}."))

    for path in ROOT.rglob("*.md"):
        if any(part in {".git", "reports", "publication"} for part in path.parts): continue
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if "://" in target or target.startswith("mailto:"): continue
            if not (path.parent / target).resolve().exists():
                findings.append(Finding("ERROR", "BROKEN_LINK", str(path.relative_to(ROOT)), f"Lien cassé: {target}."))

    from continuity import audit_continuity
    findings.extend(audit_continuity(ROOT, active, frontmatter, registry_rows, Finding))
    return findings


def write_report(findings: list[Finding]) -> Path:
    target = ROOT / "reports/audit.md"
    counts = Counter(item.level for item in findings)
    lines = ["# Audit Nexus", "", f"Date : {date.today().isoformat()}", "", f"- Erreurs : {counts['ERROR']}", f"- Alertes : {counts['WARN']}", f"- Informations : {counts['INFO']}", "", "| Niveau | Code | Fichier | Message |", "|---|---|---|---|"]
    lines += [f"| {f.level} | {f.code} | `{f.path}` | {f.message.replace('|', '/')} |" for f in findings]
    if not findings: lines += ["", "Aucune anomalie détectée."]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "reports/audit.json").write_text(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def write_split_reports(findings: list[Finding]) -> list[Path]:
    groups = {
        "integrite": {"SCENE_FRONTMATTER", "SCENE_FIELD", "SCENE_ID", "DUPLICATE_ID", "FILENAME_ID", "MANIFEST_DUPLICATE", "MANIFEST_MISSING", "BROKEN_LINK", "DUPLICATE_REGISTRY_ID", "PLACEHOLDER"},
        "continuite": {"UNKNOWN_REFERENCE", "ORPHAN_SCENE", "DATE_FORMAT", "BIRTH_DATE_FORMAT", "BEFORE_BIRTH", "SELF_CAUSE", "CAUSE_IN_FUTURE", "KNOWLEDGE_SCHEMA", "KNOWLEDGE_CHARACTER", "KNOWLEDGE_UNCERTAIN", "KNOWLEDGE_TOO_EARLY"},
        "narratif": {"DRAMA_FIELD"},
        "style": {"SCENE_SHORT", "SCENE_LONG"},
    }
    outputs = []
    for name, codes in groups.items():
        selected = [f for f in findings if f.code in codes]
        target = ROOT / f"reports/audit-{name}.md"
        lines = [f"# Audit {name}", "", f"Constats : {len(selected)}", ""]
        lines += [f"- **{f.level} — {f.code}** — `{f.path}` — {f.message}" for f in selected]
        if not selected: lines.append("Aucun constat.")
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        outputs.append(target)
    return outputs


def load_checkpoint() -> dict:
    path = ROOT / config()["author"]["checkpoint"]
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return {}


def registry_rows(path: Path) -> list[dict]:
    """Lit le YAML, y compris listes imbriquées et chaînes multilignes."""
    if not path.exists(): return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict): raise ValueError(f"Racine YAML invalide: {path}")
    return [row for value in data.values() if isinstance(value, list) for row in value if isinstance(row, dict)]


def cockpit(focus=None) -> Path:
    cfg = config()
    from reference_research import plan
    pending_references = plan(ROOT, cfg)
    focus = focus or cfg.get('author', {}).get('focus', 'exploration')
    if focus not in {'exploration', 'writing', 'revision'}:
        raise ValueError('Focus inconnu')
    checkpoint = load_checkpoint()
    scenes = scene_files()
    active = manifest_paths()
    findings = audit()
    priorities = sorted(findings, key=lambda f: (f.level != "ERROR", f.code))[:cfg["quality"]["max_author_priorities"]]
    if focus != 'revision':
        priorities = [f for f in priorities if f.level == 'ERROR']
    promises = registry_rows(ROOT / "data/promises.yml")
    debts = registry_rows(ROOT / "data/narrative_debt.yml")
    characters = registry_rows(ROOT / "data/characters.yml")
    concepts = registry_rows(ROOT / "data/concepts.yml")
    influences = registry_rows(ROOT / "data/influences.yml")
    sources = registry_rows(ROOT / "data/sources.yml")
    words = sum(len(re.findall(r"\b[\wÀ-ÿ'-]+\b", frontmatter(p)[1])) for p in active if p.exists())
    last = active[-1].relative_to(ROOT).as_posix() if active else checkpoint.get("last_scene")
    lines = [
        f"# Cockpit auteur — {cfg['project']['title']}", "",
        f"**Mode :** `{cfg['project']['author_mode']}`  ",
        f"**Focus :** `{focus}`  ",
        f"**État :** {cfg['project']['status']}  ",
        f"**Manuscrit :** {len(active)} scène(s) active(s), {words} mots  ",
        f"**Dernière scène :** {last or 'aucune'}", "",
        "## Reprise immédiate", "",
        f"- Dernière séance : {checkpoint.get('session_summary') or 'non renseignée'}",
        f"- Prochaine intention : {checkpoint.get('next_intention') or 'à définir'}",
    ]
    difficulties = checkpoint.get("open_difficulties") or []
    focus_help = {
        'exploration': 'Question créative : quel choix difficile rend cette idée nécessaire ? Utiliser creative-interview ou world-consequences. Décision ouverte : ' + (checkpoint.get('next_intention') or 'à préciser'),
        'writing': 'Scène de travail par défaut : ' + str(last or 'à créer') + '. Relire son objectif, son obstacle et son changement ; écrire puis enregistrer un checkpoint.',
        'revision': 'Choisir un seul axe de révision. Créer un snapshot avant modification ; comparer ensuite. Les alertes non bloquantes sont affichées ici.'
    }
    lines += ['', '## Travail du moment', '', focus_help[focus], '', f"Audit complet : {len(findings)} constat(s). Les contrôles restent identiques quel que soit le focus."]
    lines += [f"- Difficulté ouverte : {x}" for x in difficulties] or ["- Difficulté ouverte : aucune enregistrée"]
    lines += ["", "## Priorités", ""]
    lines += [f"{i}. **{f.level}** — {f.message} (`{f.path}`)" for i, f in enumerate(priorities, 1)] or ["Aucune anomalie détectée."]
    lines += ["", "## Continuité vivante", "", f"- Personnages enregistrés : {len(characters)}", f"- Promesses ouvertes : {sum(1 for x in promises if x.get('status', 'open') == 'open')}", f"- Dettes ouvertes : {sum(1 for x in debts if x.get('status', 'open') == 'open')}", "", "## Laboratoire de références", "", f"- Concepts étudiés : {len(concepts)}", f"- Influences analysées : {len(influences)}", f"- Sources enregistrées : {len(sources)}", "", "## Action recommandée", ""]
    if priorities: lines.append("Corriger la première priorité, puis relancer `python scripts/nexus.py cockpit`.")
    elif not active: lines.append("Créer les personnages indispensables, puis la première scène.")
    else: lines.append("Préparer ou écrire la prochaine scène, puis enregistrer un checkpoint.")
    target = ROOT / cfg["author"]["cockpit"]
    if pending_references:
        lines += ['', '## Recherches de références à traiter', '', 'Assistant connecté : ouvrir les demandes, rechercher les auteurs et œuvres, vérifier les sources puis enregistrer les résultats.']
        lines += [f"- `{r['id']}` — {r['kind']} : {r['subject']} ({r['status']})" for r in pending_references]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def save_checkpoint(summary: str, next_intention: str, difficulties: list[str]) -> Path:
    active = manifest_paths()
    target = ROOT / config()["author"]["checkpoint"]
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "last_scene": active[-1].relative_to(ROOT).as_posix() if active else None,
        "session_summary": summary,
        "next_intention": next_intention,
        "open_difficulties": difficulties,
        "modified_files": [],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cockpit()
    return target


def prompt_value(label: str, supplied: str | None, default: str = "unknown") -> str:
    if supplied is not None: return supplied
    if not sys.stdin.isatty(): return default
    value = input(f"{label} [{default}] : ").strip()
    return value or default


def next_registry_id(prefix: str) -> str:
    found = []
    for path in (ROOT / "data").glob("*.yml"):
        active_text = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#"))
        found += [int(x) for x in re.findall(rf"\b{prefix}-(\d{{3,4}})\b", active_text) if int(x) > 0]
    return f"{prefix}-{max(found, default=0)+1:03d}"


def append_registry(filename: str, root_key: str, row: dict) -> str:
    path = ROOT / "data" / filename
    text = path.read_text(encoding="utf-8") if path.exists() else f"{root_key}: []\n"
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get(root_key), list):
        raise ValueError(f"Registre invalide: {filename}")
    if any(item.get('id') == row['id'] for item in data[root_key]):
        raise ValueError(f"ID déjà présent: {row['id']}")
    data[root_key].append(dict(row))
    # PyYAML preserves values, not comments or original formatting.
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return row['id']


def new_entity(kind: str, name: str | None, role: str | None = None) -> str:
    specs = {
        "character": ("CHR", "characters.yml", "characters"),
        "location": ("LOC", "locations.yml", "locations"),
        "mystery": ("MYS", "mysteries.yml", "mysteries"),
        "chapter": ("CHP", "chapters.yml", "chapters"),
    }
    prefix, filename, root_key = specs[kind]
    eid = next_registry_id(prefix)
    label = prompt_value("Nom / titre / question", name)
    if kind == "character": row = {"id": eid, "name": label, "role": prompt_value("Rôle", role, "secondary"), "status": "PROPOSE", "desire": "unknown", "need": "unknown", "fear": "unknown", "arc": "unknown"}
    elif kind == "location": row = {"id": eid, "name": label, "status": "PROPOSE", "function": "unknown"}
    elif kind == "mystery": row = {"id": eid, "question": label, "stakes": "unknown", "status": "open"}
    else: row = {"id": eid, "title": label, "order": len(registry_rows(ROOT / 'data/chapters.yml')) + 1, "promise": "unknown", "engine": "unknown", "status": "PROPOSE"}
    append_registry(filename, root_key, row)
    cockpit()
    return eid


REVISION_PASSES = {
    "causalite": ["Relier les événements par parce que/donc/mais.", "Appliquer le test contrefactuel.", "Repérer les scènes supprimables sans conséquence."],
    "personnages": ["Vérifier désir, obstacle et décision.", "Contrôler connaissances et croyances.", "Tester la distinction des voix et le prix de l'arc."],
    "mystere": ["Cartographier manque, indice, hypothèse et contradiction.", "Vérifier l'honnêteté des fausses pistes.", "Placer la conséquence humaine des révélations."],
    "continuite": ["Contrôler temps, lieux et déplacements.", "Suivre objets, blessures et relations.", "Vérifier qu'aucun personnage ne sait trop tôt."],
    "rythme": ["Cartographier tension et respiration.", "Repérer exposition et répétition.", "Tester les sorties de scène et de chapitre."],
}


def revision_plan(name: str) -> Path:
    if name not in REVISION_PASSES: raise SystemExit(f"Passe inconnue. Choix: {', '.join(REVISION_PASSES)}")
    directory = ROOT / config()["author"]["revision_dir"]
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{date.today().isoformat()}-{name}.md"
    lines = [f"# Passe de révision — {name}", "", "Ne corriger que cet axe pendant cette passe.", ""]
    lines += [f"- [ ] {item}" for item in REVISION_PASSES[name]]
    lines += ["", "## Scènes à revoir", ""] + [f"- [ ] `{p.relative_to(ROOT)}`" for p in manifest_paths()]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def setup_project(title: str | None, author: str | None, genre: str | None, mode: str | None) -> Path:
    path = ROOT / "config/projet.toml"
    text = path.read_text(encoding="utf-8")
    values = {
        "title": prompt_value("Titre du projet", title, "Titre à définir"),
        "author": prompt_value("Auteur", author, "Auteur"),
        "genre": prompt_value("Genre", genre, "unknown"),
        "author_mode": mode or "essential",
    }
    for key, value in values.items():
        text = re.sub(rf'^{key}\s*=\s*".*"$', f'{key} = {json.dumps(value, ensure_ascii=False)}', text, flags=re.M)
    path.write_text(text, encoding="utf-8")
    cockpit()
    return path


def add_decision(title: str | None, status_name: str) -> Path:
    existing = [int(x) for p in (ROOT / "decisions").glob("NDR-*.md") for x in re.findall(r"NDR-(\d+)", p.name)]
    number = max(existing, default=0) + 1
    decision_id = f"NDR-{number:04d}"
    title = prompt_value("Titre de la décision", title)
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-") or "decision"
    target = ROOT / "decisions" / f"{decision_id}-{slug}.md"
    text = (ROOT / "templates/ndr.md").read_text(encoding="utf-8")
    text = text.replace("NDR-0000", decision_id).replace("Décision", title, 1).replace("PROPOSE", status_name.upper()).replace("YYYY-MM-DD", date.today().isoformat())
    target.write_text(text, encoding="utf-8")
    return target


def close_promise(promise_id: str, scene_id: str) -> Path:
    path = ROOT / "data/promises.yml"
    text = path.read_text(encoding="utf-8")
    pattern = rf"(^\s*-\s+id:\s*{re.escape(promise_id)}\s*$)(.*?)(?=^\s*-\s+id:|\Z)"
    match = re.search(pattern, text, re.M | re.S)
    if not match: raise SystemExit(f"Promesse introuvable: {promise_id}")
    block = match.group(1) + match.group(2)
    block = re.sub(r"^\s+status:.*$", "  status: paid", block, flags=re.M)
    if re.search(r"^\s+payoff:", block, re.M): block = re.sub(r"^\s+payoff:.*$", f"  payoff: {scene_id}", block, flags=re.M)
    else: block = block.rstrip() + f"\n  payoff: {scene_id}\n"
    path.write_text(text[:match.start()] + block + text[match.end():], encoding="utf-8")
    cockpit()
    return path


def character_view(character_id: str) -> Path:
    rows = registry_rows(ROOT / "data/characters.yml")
    character = next((x for x in rows if x.get("id") == character_id), None)
    if not character: raise SystemExit(f"Personnage introuvable: {character_id}")
    appearances = []
    for path in manifest_paths():
        if not path.exists(): continue
        meta, _ = frontmatter(path)
        participants = meta.get("characters", [])
        if meta.get("pov") == character_id or character_id in participants:
            appearances.append((path, meta))
    target = ROOT / "reports" / f"personnage-{character_id}.md"
    lines = [f"# Vue personnage — {character.get('name', character_id)}", "", f"- ID : `{character_id}`", f"- Rôle : {character.get('role', 'unknown')}", f"- Désir : {character.get('desire', 'unknown')}", f"- Arc : {character.get('arc', 'unknown')}", "", "## Parcours dans le manuscrit", "", "| Ordre | Scène | POV | Connaissances acquises | Relations modifiées |", "|---:|---|---|---|---|"]
    for index, (path, meta) in enumerate(appearances, 1):
        lines.append(f"| {index} | `{meta.get('id')}` — {meta.get('title')} | {'oui' if meta.get('pov') == character_id else 'non'} | {meta.get('knowledge_gained', [])} | {meta.get('relationships_changed', [])} |")
    if not appearances: lines += ["", "Aucune apparition active."]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def safe_slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "dossier"


def create_research_dossier(subject: str, concept: str | None, genre: str | None, decision: str | None) -> Path:
    directory = ROOT / "recherches" / "dossiers"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{date.today().isoformat()}-{safe_slug(subject)}.md"
    text = (ROOT / "templates/research-dossier.md").read_text(encoding="utf-8")
    text = text.replace("SUJET", subject, 1)
    replacements = {"- Sujet :": subject, "- Concept associé :": concept or "unknown", "- Genre concerné :": genre or "unknown", "- Décision narrative à éclairer :": decision or "unknown"}
    for label, value in replacements.items(): text = text.replace(label, f"{label} {value}", 1)
    from author_tools import create
    return create(ROOT, target.relative_to(ROOT), text)


def create_concept(name: str) -> tuple[str, Path]:
    eid = next_registry_id("CON")
    append_registry("concepts.yml", "concepts", {"id": eid, "name": name, "working_definition": "unknown", "rival_definitions": [], "tensions": [], "dramatic_tests": [], "sources": [], "status": "RESEARCH"})
    directory = ROOT / "recherches" / "concepts"; directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{eid}-{safe_slug(name)}.md"
    target.write_text((ROOT / "templates/concept-lab.md").read_text(encoding="utf-8").replace("CONCEPT", name, 1), encoding="utf-8")
    cockpit(); return eid, target


def create_genre_profile(name: str) -> tuple[str, Path]:
    eid = next_registry_id("GEN")
    append_registry("genre_contract.yml", "genres", {"id": eid, "name": name, "core_promise": "unknown", "reader_expectations": [], "obligatory_questions": [], "optional_conventions": [], "tired_tropes": [], "deliberate_transgressions": [], "comparable_works": []})
    directory = ROOT / "recherches" / "genres"; directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{eid}-{safe_slug(name)}.md"
    target.write_text((ROOT / "templates/genre-profile.md").read_text(encoding="utf-8").replace("GENRE", name, 1), encoding="utf-8")
    cockpit(); return eid, target


def create_theme(name: str) -> str:
    eid = next_registry_id('THM')
    append_registry('themes.yml', 'themes', {'id': eid, 'name': name, 'question': 'unknown', 'status': 'RESEARCH'})
    cockpit()
    return eid


def create_influence(author: str, function_sought: str, genre: str | None) -> tuple[str, Path]:
    eid = next_registry_id("INF")
    append_registry("influences.yml", "influences", {"id": eid, "author": author, "works": [], "genre": genre or "unknown", "function_sought": function_sought, "observable_techniques": [], "transformations": [], "imitation_risks": [], "status": "RESEARCH"})
    directory = ROOT / "recherches" / "influences"; directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{eid}-{safe_slug(author)}.md"
    target.write_text((ROOT / "templates/influence-card.md").read_text(encoding="utf-8").replace("AUTEUR", author), encoding="utf-8")
    cockpit(); return eid, target


def add_source(title: str, author: str, url: str, source_type: str) -> str:
    eid = next_registry_id("SRC")
    append_registry("sources.yml", "sources", {"id": eid, "title": title, "author": author, "url": url, "source_type": source_type, "reliability": "unknown", "reading_status": "identified", "accessed": None, "claims": [], "contradictions": [], "narrative_uses": []})
    cockpit(); return eid


def build() -> Path:
    from author_tools import active_scenes, visible_text
    cfg = config()["manuscript"]
    paths = active_scenes(ROOT)
    missing = [p for p in paths if not p.exists()]
    if missing: raise SystemExit("Manifeste invalide; lancer audit.")
    chunks = [f"# {config()['project']['title']}", ""]
    for path in paths:
        body = visible_text(path)
        chunks += [body.strip(), "", "---", ""]
    target = ROOT / cfg["output"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
    return target


def new_scene(chapter: int, title: str) -> Path:
    ids = []
    for path in scene_files():
        meta, _ = frontmatter(path)
        match = re.fullmatch(r"SCN-(\d+)", str(meta.get("id", "")))
        if match: ids.append(int(match.group(1)))
    number = max(ids, default=0) + 1
    sid = f"SCN-{number:03d}"
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-") or "scene"
    directory = ROOT / config()["manuscript"]["root"] / config()["manuscript"]["active_volume"] / f"chapitre-{chapter:02d}"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{sid}-{slug}.md"
    text = (ROOT / "templates/scene.md").read_text(encoding="utf-8")
    text = text.replace("SCN-000", sid).replace("Scène 000", f"Scène {number:03d}")
    text = text.replace("title: TITRE", "title: " + json.dumps(title, ensure_ascii=False)).replace("TITRE", title)
    text = re.sub(r"^chapter: 0$", f"chapter: {chapter}", text, flags=re.M)
    text = re.sub(r"^order: 0$", f"order: {number}", text, flags=re.M)
    target.write_text(text, encoding="utf-8")
    if config()["author"]["auto_add_new_scene_to_manifest"]:
        manifest = ROOT / config()["manuscript"]["manifest"]
        relative = target.relative_to(ROOT).as_posix()
        manifest.write_text(manifest.read_text(encoding="utf-8").rstrip() + f"\n{relative}\n", encoding="utf-8")
    cockpit()
    return target


def initialize() -> None:
    for name in ("atelier", "recherches", "decisions", "reports", "publication"):
        (ROOT / name).mkdir(exist_ok=True)
    cockpit()
    print("Nexus initialisé. Ouvrez COCKPIT_AUTEUR.md.")


def status() -> None:
    findings = audit()
    counts = Counter(x.level for x in findings)
    print(f"Scènes: {len(scene_files())} | Actives: {len(manifest_paths())} | Erreurs: {counts['ERROR']} | Alertes: {counts['WARN']}")


def main() -> int:
    from editorial import dispatch as editorial_dispatch
    if len(sys.argv) > 1 and editorial_dispatch(sys.argv[1:], ROOT):
        return 0
    from author_tools import dispatch
    if len(sys.argv) > 1 and dispatch(sys.argv[1:], ROOT):
        return 0
    parser = argparse.ArgumentParser(prog="nexus")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("audit")
    sub.add_parser("audit-author")
    sub.add_parser("build")
    sub.add_parser("status")
    cockpit_parser = sub.add_parser("cockpit")
    cockpit_parser.add_argument('--focus', choices=['exploration', 'writing', 'revision'])
    setup = sub.add_parser("setup")
    setup.add_argument("--title")
    setup.add_argument("--author")
    setup.add_argument("--genre")
    setup.add_argument("--mode", choices=("essential", "structured", "expert"))
    checkpoint_parser = sub.add_parser("checkpoint")
    checkpoint_parser.add_argument("--summary")
    checkpoint_parser.add_argument("--next", dest="next_intention")
    checkpoint_parser.add_argument("--difficulty", action="append", default=[])
    revise = sub.add_parser("revise")
    revise.add_argument("--pass", dest="revision_pass", required=True, choices=sorted(REVISION_PASSES))
    for command in ("new-character", "new-location", "new-mystery", "new-chapter"):
        entity = sub.add_parser(command)
        entity.add_argument("--name")
        if command == "new-character": entity.add_argument("--role")
    decision = sub.add_parser("add-decision")
    decision.add_argument("--title")
    decision.add_argument("--status", default="PROPOSE")
    close = sub.add_parser("close-promise")
    close.add_argument("--id", required=True)
    close.add_argument("--scene", required=True)
    character = sub.add_parser("character-view")
    character.add_argument("--id", required=True)
    research = sub.add_parser("research-dossier")
    research.add_argument("--subject", required=True)
    research.add_argument("--concept")
    research.add_argument("--genre")
    research.add_argument("--decision")
    concept_parser = sub.add_parser("new-concept")
    concept_parser.add_argument("--name", required=True)
    genre_parser = sub.add_parser("genre-profile")
    genre_parser.add_argument("--genre", required=True)
    theme_parser = sub.add_parser('new-theme')
    theme_parser.add_argument('--name', required=True)
    sub.add_parser('reference-sync')
    reference_done = sub.add_parser('reference-complete')
    reference_done.add_argument('--id', required=True)
    reference_done.add_argument('--file', required=True)
    reference_state = sub.add_parser('reference-state')
    reference_state.add_argument('--id', required=True)
    reference_state.add_argument('--status', required=True, choices=['pending', 'in_progress', 'blocked'])
    reference_state.add_argument('--reason', required=True)
    reference_decision = sub.add_parser('reference-decide')
    reference_decision.add_argument('--id', required=True)
    reference_decision.add_argument('--author', required=True)
    reference_decision.add_argument('--decision', required=True, choices=['accept', 'reject', 'defer'])
    reference_decision.add_argument('--reason', required=True)
    reference_decision.add_argument('--scope', required=True)
    influence = sub.add_parser("new-influence")
    influence.add_argument("--author", required=True)
    influence.add_argument("--function", dest="function_sought", required=True)
    influence.add_argument("--genre")
    source = sub.add_parser("add-source")
    source.add_argument("--title", required=True)
    source.add_argument("--author", required=True)
    source.add_argument("--url", required=True)
    source.add_argument("--type", dest="source_type", choices=("primary", "secondary", "reference"), default="primary")
    create = sub.add_parser("new-scene")
    create.add_argument("--chapter", type=int, required=True)
    create.add_argument("--title", required=True)
    args = parser.parse_args()
    if args.command == "init": initialize()
    elif args.command == "setup": print(setup_project(args.title, args.author, args.genre, args.mode).relative_to(ROOT))
    elif args.command == "new-scene": print(new_scene(args.chapter, args.title).relative_to(ROOT))
    elif args.command in ("new-character", "new-location", "new-mystery", "new-chapter"):
        kind = args.command.removeprefix("new-")
        print(new_entity(kind, args.name, getattr(args, "role", None)))
    elif args.command == "add-decision": print(add_decision(args.title, args.status).relative_to(ROOT))
    elif args.command == "close-promise": print(close_promise(args.id, args.scene).relative_to(ROOT))
    elif args.command == "character-view": print(character_view(args.id).relative_to(ROOT))
    elif args.command == "research-dossier": print(create_research_dossier(args.subject, args.concept, args.genre, args.decision).relative_to(ROOT))
    elif args.command == "new-concept":
        eid, path = create_concept(args.name); print(f"{eid} {path.relative_to(ROOT)}")
    elif args.command == "genre-profile":
        eid, path = create_genre_profile(args.genre); print(f"{eid} {path.relative_to(ROOT)}")
    elif args.command == 'new-theme': print(create_theme(args.name))
    elif args.command == 'reference-sync':
        from reference_research import plan
        print(json.dumps(plan(ROOT, config()), ensure_ascii=False, indent=2))
    elif args.command == 'reference-complete':
        from reference_research import complete, plan
        plan(ROOT, config())
        print(complete(ROOT, args.id, args.file).relative_to(ROOT))
        cockpit()
    elif args.command == 'reference-state':
        from reference_research import transition, plan
        plan(ROOT, config())
        print(json.dumps(transition(ROOT, args.id, args.status, args.reason), ensure_ascii=False))
        cockpit()
    elif args.command == 'reference-decide':
        from reference_research import decide
        print(decide(ROOT, args.id, args.author, args.decision, args.reason, args.scope).relative_to(ROOT))
    elif args.command == "new-influence":
        eid, path = create_influence(args.author, args.function_sought, args.genre); print(f"{eid} {path.relative_to(ROOT)}")
    elif args.command == "add-source": print(add_source(args.title, args.author, args.url, args.source_type))
    elif args.command == "cockpit": print(cockpit(args.focus).relative_to(ROOT))
    elif args.command == "checkpoint":
        summary = prompt_value("Résumé de la séance", args.summary, "")
        next_intention = prompt_value("Prochaine intention", args.next_intention, "")
        print(save_checkpoint(summary, next_intention, args.difficulty).relative_to(ROOT))
    elif args.command == "revise": print(revision_plan(args.revision_pass).relative_to(ROOT))
    elif args.command == "build": print(build().relative_to(ROOT))
    elif args.command == "status": status()
    elif args.command == "audit-author":
        findings = audit(); write_report(findings); write_split_reports(findings); print(cockpit().relative_to(ROOT))
        if any(x.level == "ERROR" for x in findings): return 1
    elif args.command == "audit":
        findings = audit(); print(write_report(findings).relative_to(ROOT)); write_split_reports(findings)
        if any(x.level == "ERROR" for x in findings): return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
