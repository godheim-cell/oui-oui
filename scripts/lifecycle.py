#!/usr/bin/env python3
"""Nexus V5: cycle de vie générique d'un roman ou d'une saga.

Ce module ne lit pas le sens de la prose et ne rend rien canonique. Il agrège les
volumes, qualifie la couverture des registres, trace les gels éditoriaux,
prépare les campagnes de lecture et manifeste les livrables publiés.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
import unicodedata
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

STATE_ORDER = ["exploration", "planning", "writing", "revision", "frozen", "released"]
ID_RE_V5 = re.compile(r"\b(CHR|LOC|SCN|EVT|MYS|PRO|OBJ|REL|ARC|DEBT|NDR|SRC|CON|INF|GEN|THM|CHP)-\d{3,4}\b")


def load_config(root: Path) -> dict:
    with (root / "config/projet.toml").open("rb") as handle:
        return tomllib.load(handle)


def slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "item"


def manifests(root: Path) -> list[Path]:
    return sorted((root / "manuscrit").glob("tome-*/manifest.txt"))


def volume_manifest(root: Path, volume: str) -> Path:
    path = root / "manuscrit" / volume / "manifest.txt"
    if not path.is_file():
        raise ValueError(f"Manifeste introuvable pour {volume}: {path.relative_to(root)}")
    return path


def manifest_paths(root: Path, manifest: Path) -> list[Path]:
    result: list[Path] = []
    manuscript_root = (root / "manuscrit").resolve()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        path = (root / item).resolve()
        if not path.is_relative_to(manuscript_root):
            raise ValueError(f"Chemin hors manuscrit dans {manifest.relative_to(root)}: {item}")
        if path in result:
            raise ValueError(f"Scène dupliquée dans {manifest.relative_to(root)}: {item}")
        result.append(path)
    return result


def volume_paths(root: Path, volume: str) -> list[Path]:
    return manifest_paths(root, volume_manifest(root, volume))


def all_manifest_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for manifest in manifests(root):
        for path in manifest_paths(root, manifest):
            if path in seen:
                raise ValueError(f"Scène déclarée dans plusieurs manifestes: {path.relative_to(root)}")
            seen.add(path)
            paths.append(path)
    return paths


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", text))


def volume_digest(root: Path, volume: str) -> str:
    digest = hashlib.sha256()
    for path in volume_paths(root, volume):
        if not path.is_file():
            raise ValueError(f"Scène absente: {path.relative_to(root)}")
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def style_metrics(root: Path) -> dict[str, dict]:
    import nexus
    old_root = nexus.ROOT
    nexus.ROOT = root
    try:
        report: dict[str, dict] = {}
        for manifest in manifests(root):
            volume = manifest.parent.name
            paths = manifest_paths(root, manifest)
            words = 0
            sentence_lengths: list[int] = []
            paragraphs = short_paragraphs = dialogue_paragraphs = bare_yes_no = 0
            for path in paths:
                if not path.is_file():
                    continue
                _, body = nexus.frontmatter(path)
                words += word_count(body)
                parts = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
                paragraphs += len(parts)
                short_paragraphs += sum(1 for p in parts if word_count(p) <= 4)
                dialogue_paragraphs += sum(1 for p in parts if p.startswith("—"))
                bare_yes_no += len(re.findall(r"(?m)^\s*—\s*(?:Oui|Non)\.\s*$", body))
                for sentence in re.split(r"(?<=[.!?…])\s+", re.sub(r"\s+", " ", body).strip()):
                    count = word_count(sentence)
                    if count:
                        sentence_lengths.append(count)
            short_sentences = sum(1 for count in sentence_lengths if count < 6)
            report[volume] = {
                "scenes": len(paths),
                "words": words,
                "sentences": len(sentence_lengths),
                "mean_words_per_sentence": round(sum(sentence_lengths) / len(sentence_lengths), 2) if sentence_lengths else 0,
                "sentences_under_6_pct": round(100 * short_sentences / len(sentence_lengths), 1) if sentence_lengths else 0,
                "short_paragraphs_pct": round(100 * short_paragraphs / paragraphs, 1) if paragraphs else 0,
                "dialogue_paragraphs_pct": round(100 * dialogue_paragraphs / paragraphs, 1) if paragraphs else 0,
                "bare_yes_no": bare_yes_no,
            }
        return report
    finally:
        nexus.ROOT = old_root


def _root_nonempty_yaml(path: Path) -> bool:
    if not path.is_file():
        return False
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return False
    return any(bool(value) for value in data.values())


def registry_coverage_findings(root: Path, finding_type) -> list:
    policy_path = root / "data/registry_policy.yml"
    if not policy_path.is_file():
        return [finding_type("WARN", "REGISTRY_POLICY_MISSING", "data/registry_policy.yml", "Politique des registres absente; la couverture ne peut pas être qualifiée.")]
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    entries = policy.get("registries", {}) if isinstance(policy, dict) else {}
    if not isinstance(entries, dict):
        return [finding_type("ERROR", "REGISTRY_POLICY_SCHEMA", "data/registry_policy.yml", "registries doit être un dictionnaire.")]
    cfg = load_config(root)
    project_state = str(cfg.get("project", {}).get("status", "exploration"))
    state_index = STATE_ORDER.index(project_state) if project_state in STATE_ORDER else 0
    findings = []
    for rel, spec in entries.items():
        if not isinstance(spec, dict):
            findings.append(finding_type("ERROR", "REGISTRY_POLICY_SCHEMA", "data/registry_policy.yml", f"Entrée invalide: {rel}"))
            continue
        mode = spec.get("mode", "dormant")
        if mode not in {"active", "workshop", "dormant"}:
            findings.append(finding_type("ERROR", "REGISTRY_POLICY_SCHEMA", "data/registry_policy.yml", f"Mode inconnu pour {rel}: {mode}"))
            continue
        required_from = str(spec.get("required_from", "released"))
        threshold = STATE_ORDER.index(required_from) if required_from in STATE_ORDER else len(STATE_ORDER)
        if mode == "active" and state_index >= threshold and not _root_nonempty_yaml(root / rel):
            findings.append(finding_type("WARN", "EMPTY_ACTIVE_REGISTRY", rel, "Registre actif vide: le contrôle correspondant ne doit pas être présenté comme probant."))
    return findings


def saga_findings(root: Path) -> list:
    import nexus
    old_root = nexus.ROOT
    old_manifest_paths = nexus.manifest_paths
    old_id_re = nexus.ID_RE
    nexus.ROOT = root
    nexus.manifest_paths = lambda: all_manifest_paths(root)
    nexus.ID_RE = ID_RE_V5
    try:
        findings = list(nexus.audit())
        findings.extend(registry_coverage_findings(root, nexus.Finding))
        return findings
    finally:
        nexus.ID_RE = old_id_re
        nexus.manifest_paths = old_manifest_paths
        nexus.ROOT = old_root


def write_saga_report(root: Path) -> Path:
    findings = saga_findings(root)
    metrics = style_metrics(root)
    counts = Counter(item.level for item in findings)
    target = root / "reports/saga-audit.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Audit saga Nexus", "", f"Date : {date.today().isoformat()}",
        f"Scènes actives agrégées : {len(all_manifest_paths(root))}",
        f"Erreurs : {counts['ERROR']}", f"Alertes : {counts['WARN']}", "", "## Constats", "",
    ]
    if findings:
        lines += ["| Niveau | Code | Fichier | Message |", "|---|---|---|---|"]
        lines += [f"| {f.level} | {f.code} | `{f.path}` | {f.message.replace('|', '/')} |" for f in findings]
    else:
        lines.append("Aucune anomalie détectée.")
    lines += ["", "## Métriques par volume", ""]
    for volume, item in metrics.items():
        lines += [
            f"### {volume}", "", f"- Scènes : {item['scenes']}", f"- Mots : {item['words']}",
            f"- Mots moyens par phrase : {item['mean_words_per_sentence']}",
            f"- Phrases de moins de 6 mots : {item['sentences_under_6_pct']} %",
            f"- Paragraphes de 4 mots ou moins : {item['short_paragraphs_pct']} %",
            f"- Paragraphes de dialogue : {item['dialogue_paragraphs_pct']} %",
            f"- Répliques nues Oui/Non : {item['bare_yes_no']}", "",
        ]
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    (root / "reports/saga-audit.json").write_text(json.dumps({"findings": [vars(x) for x in findings], "metrics": metrics}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_lifecycle(root: Path) -> dict:
    path = root / "data/lifecycle.yml"
    if not path.is_file():
        return {"version": 1, "volumes": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("data/lifecycle.yml doit contenir un dictionnaire.")
    data.setdefault("version", 1)
    data.setdefault("volumes", {})
    return data


def save_lifecycle(root: Path, data: dict) -> Path:
    path = root / "data/lifecycle.yml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def saga_cockpit(root: Path) -> Path:
    cfg = load_config(root)
    metrics = style_metrics(root)
    findings = saga_findings(root)
    counts = Counter(x.level for x in findings)
    state = load_lifecycle(root)
    target = root / "COCKPIT_SAGA.md"
    lines = [
        f"# Cockpit saga — {cfg['project']['title']}", "",
        "> Artefact généré. La mémoire éditoriale durable se trouve dans `MEMOIRE_PROJET.md`.", "",
        f"**État projet :** `{cfg['project'].get('status', 'exploration')}`  ",
        f"**Volumes détectés :** {len(metrics)}  ",
        f"**Scènes actives :** {sum(x['scenes'] for x in metrics.values())}  ",
        f"**Audit :** {counts['ERROR']} erreur(s), {counts['WARN']} alerte(s)", "", "## Volumes", "",
        "| Volume | État cycle de vie | Scènes | Mots | Empreinte gelée |", "|---|---|---:|---:|---|",
    ]
    for volume, item in metrics.items():
        lifecycle = state.get("volumes", {}).get(volume, {})
        digest = lifecycle.get("frozen_digest", "")
        lines.append(f"| `{volume}` | {lifecycle.get('state', 'working')} | {item['scenes']} | {item['words']} | {digest[:12] if digest else '-'} |")
    lines += ["", "## Action recommandée", ""]
    if counts["ERROR"]:
        lines.append("Corriger les erreurs déterministes avant gel ou publication.")
    elif counts["WARN"]:
        lines.append("Examiner les alertes et la couverture des registres avant toute validation éditoriale.")
    else:
        lines.append("Aucun blocage déterministe. Poursuivre selon l'état du volume actif.")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def freeze_volume(root: Path, volume: str, reason: str, source_commit: str | None = None) -> Path:
    paths = volume_paths(root, volume)
    if not paths:
        raise ValueError(f"Impossible de geler {volume}: manifeste vide.")
    findings = saga_findings(root)
    if any(item.level == "ERROR" for item in findings):
        raise ValueError("Gel refusé: l'audit saga contient des erreurs déterministes.")
    state = load_lifecycle(root)
    entry = state["volumes"].setdefault(volume, {})
    now = datetime.now(timezone.utc).isoformat()
    entry.update({"state": "frozen", "frozen_at": now, "frozen_digest": volume_digest(root, volume), "reason": reason, "source_commit": source_commit or "unknown"})
    entry.setdefault("history", []).append({"action": "freeze", "at": now, "reason": reason})
    return save_lifecycle(root, state)


def unfreeze_volume(root: Path, volume: str, reason: str) -> Path:
    state = load_lifecycle(root)
    entry = state["volumes"].get(volume)
    if not entry or entry.get("state") not in {"frozen", "released"}:
        raise ValueError(f"{volume} n'est pas gelé ou publié.")
    now = datetime.now(timezone.utc).isoformat()
    entry["state"] = "revision"
    entry["reopened_at"] = now
    entry.setdefault("history", []).append({"action": "unfreeze", "at": now, "reason": reason})
    return save_lifecycle(root, state)


def publication_manifest(root: Path, volume: str) -> Path:
    cfg = load_config(root)
    directory = root / "publication" / volume
    directory.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name != "MANIFEST.md":
            artifacts.append((path.name, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()))
    lines = [
        f"# Manifeste de publication — {volume}", "", f"- Projet : {cfg['project']['title']}",
        f"- Auteur : {cfg['project'].get('author', 'unknown')}", f"- Série : {cfg['project'].get('series', '') or 'non renseignée'}",
        f"- Généré : {datetime.now(timezone.utc).isoformat()}", f"- Empreinte source : `{volume_digest(root, volume)}`", "", "## Livrables", "",
    ]
    if artifacts:
        lines += ["| Fichier | Octets | SHA-256 |", "|---|---:|---|"]
        lines += [f"| `{name}` | {size} | `{digest}` |" for name, size, digest in artifacts]
    else:
        lines.append("Aucun livrable matérialisé.")
    target = directory / "MANIFEST.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def release_status(root: Path, volume: str) -> dict:
    state = load_lifecycle(root)
    entry = state.get("volumes", {}).get(volume, {})
    frozen = entry.get("frozen_digest")
    current = volume_digest(root, volume)
    publication = root / "publication" / volume / "MANIFEST.md"
    return {"volume": volume, "state": entry.get("state", "working"), "frozen_digest": frozen, "current_digest": current, "manuscript_changed_since_freeze": bool(frozen and frozen != current), "publication_manifest": publication.relative_to(root).as_posix() if publication.is_file() else None}


def release_volume(root: Path, volume: str, reason: str) -> Path:
    status = release_status(root, volume)
    if status["state"] != "frozen":
        raise ValueError("Publication refusée: le volume doit être gelé.")
    if status["manuscript_changed_since_freeze"]:
        raise ValueError("Publication refusée: le manuscrit a changé depuis le gel.")
    if not status["publication_manifest"]:
        raise ValueError("Publication refusée: générer d'abord le manifeste de publication.")
    state = load_lifecycle(root)
    entry = state["volumes"][volume]
    now = datetime.now(timezone.utc).isoformat()
    entry["state"] = "released"
    entry["released_at"] = now
    entry.setdefault("history", []).append({"action": "release", "at": now, "reason": reason})
    return save_lifecycle(root, state)


def new_discussion(root: Path, title: str) -> Path:
    directory = root / "discussions" / f"{date.today().isoformat()}-{slug(title)}"
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / "DISCUSSION.md"
    target.write_text("\n".join([f"# Discussion — {title}", "", "**Statut : NON_CANON — exploration**", "", "## Question", "", "À préciser.", "", "## Hypothèses", "", "- À explorer.", "", "## Éléments à vérifier", "", "- Sources, cohérence, conséquences et alternatives.", "", "## Sortie possible", "", "Aucune promotion automatique. Une conclusion peut devenir une NDR après validation explicite de l'auteur.", ""]), encoding="utf-8")
    (directory / "RESUME.md").write_text(f"# Résumé — {title}\n\nÀ produire après discussion.\n", encoding="utf-8")
    return target


def new_reader_campaign(root: Path, name: str, volume: str, mode: str) -> Path:
    paths = volume_paths(root, volume)
    directory = root / "atelier" / "lecture-externe" / f"{date.today().isoformat()}-{slug(name)}"
    directory.mkdir(parents=True, exist_ok=False)
    payload = {"version": 1, "name": name, "volume": volume, "mode": mode, "status": "planned", "created": date.today().isoformat(), "scene_count": len(paths), "provenance": "human_readers" if mode == "human" else "simulated_reader_profiles", "may_trigger_revision": True, "may_claim_human_validation": mode == "human", "findings": []}
    target = directory / "CAMPAIGN.yml"
    target.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (directory / "README.md").write_text(f"# Campagne de lecture — {name}\n\nVolume : `{volume}`  \nMode : `{mode}`\n\nLes retours doivent citer des passages précis. Les simulations sont toujours étiquetées et ne valent jamais preuve de réception humaine.\n", encoding="utf-8")
    return target


def dispatch(argv: list[str], root: Path) -> bool:
    commands = {"saga-audit", "saga-status", "saga-metrics", "saga-cockpit", "freeze-volume", "unfreeze-volume", "release-status", "release-volume", "publication-manifest", "new-discussion", "new-reader-campaign"}
    if not argv or argv[0] not in commands:
        return False
    command = argv[0]
    parser = argparse.ArgumentParser(prog=f"nexus {command}")
    if command in {"freeze-volume", "unfreeze-volume", "release-status", "release-volume", "publication-manifest"}:
        parser.add_argument("--volume", required=True)
    if command in {"freeze-volume", "unfreeze-volume", "release-volume"}:
        parser.add_argument("--reason", required=True)
    if command == "freeze-volume":
        parser.add_argument("--commit")
    if command == "new-discussion":
        parser.add_argument("--title", required=True)
    if command == "new-reader-campaign":
        parser.add_argument("--name", required=True)
        parser.add_argument("--volume", required=True)
        parser.add_argument("--mode", choices=["human", "simulation"], required=True)
    args = parser.parse_args(argv[1:])
    if command == "saga-audit":
        target = write_saga_report(root); print(target.relative_to(root)); return True
    if command == "saga-status":
        findings = saga_findings(root); counts = Counter(x.level for x in findings); print(f"Volumes: {len(manifests(root))} | Scènes: {len(all_manifest_paths(root))} | Erreurs: {counts['ERROR']} | Alertes: {counts['WARN']}"); return True
    if command == "saga-metrics":
        print(json.dumps(style_metrics(root), ensure_ascii=False, indent=2)); return True
    if command == "saga-cockpit":
        print(saga_cockpit(root).relative_to(root)); return True
    if command == "freeze-volume":
        print(freeze_volume(root, args.volume, args.reason, args.commit).relative_to(root)); return True
    if command == "unfreeze-volume":
        print(unfreeze_volume(root, args.volume, args.reason).relative_to(root)); return True
    if command == "release-status":
        print(json.dumps(release_status(root, args.volume), ensure_ascii=False, indent=2)); return True
    if command == "release-volume":
        print(release_volume(root, args.volume, args.reason).relative_to(root)); return True
    if command == "publication-manifest":
        print(publication_manifest(root, args.volume).relative_to(root)); return True
    if command == "new-discussion":
        print(new_discussion(root, args.title).relative_to(root)); return True
    if command == "new-reader-campaign":
        print(new_reader_campaign(root, args.name, args.volume, args.mode).relative_to(root)); return True
    return False


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if dispatch(__import__("sys").argv[1:], root):
        return 0
    raise SystemExit("Commande lifecycle inconnue.")


if __name__ == "__main__":
    raise SystemExit(main())
