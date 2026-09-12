"""Contrôles explicites : ne lit ni n'interprète la prose."""
from datetime import date, datetime
import yaml

EMPTY_DATES = (None, '', 'unknown', 'not_applicable', 'YYYY-MM-DD')
EMPTY_EDITORIAL = (None, '', 'unknown', 'not_applicable', 'A_DEFINIR')

DEFAULT_V4_THRESHOLDS = {
    'max_active_mysteries': 4,
    'max_new_concepts': 3,
    'max_new_names': 4,
    'max_new_rules': 2,
    'max_major_revelations': 1,
    'max_load_score': 8,
}


def calendar_day(value):
    if value in EMPTY_DATES:
        return None
    if isinstance(value, datetime):
        raise ValueError('Utiliser une date YYYY-MM-DD, sans heure')
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def meaningful(value):
    return value not in EMPTY_EDITORIAL and str(value).strip() not in {'', 'unknown', 'not_applicable', 'A_DEFINIR'}


def v4_thresholds(root):
    path = root / 'data/experience_model.yml'
    if not path.exists():
        return dict(DEFAULT_V4_THRESHOLDS)
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        supplied = data.get('thresholds', {}) if isinstance(data, dict) else {}
    except (yaml.YAMLError, ValueError):
        supplied = {}
    values = dict(DEFAULT_V4_THRESHOLDS)
    for key in values:
        if isinstance(supplied.get(key), int) and supplied[key] >= 0:
            values[key] = supplied[key]
    return values


def audit_continuity(root, paths, read_scene, rows, finding):
    result, scenes, characters = [], {}, {}

    def report(level, code, path, message):
        result.append(finding(level, code, str(path.relative_to(root)), message))

    character_file = root / 'data/characters.yml'
    try:
        characters = {str(r.get('id')): r for r in rows(character_file)}
    except (yaml.YAMLError, ValueError):
        pass  # Déjà signalé par l'audit YAML.
    try:
        mysteries = {str(r.get('id')) for r in rows(root / 'data/mysteries.yml') if r.get('id')}
    except (yaml.YAMLError, ValueError):
        mysteries = set()
    try:
        debts = {str(r.get('id')) for r in rows(root / 'data/narrative_debt.yml') if r.get('id')}
    except (yaml.YAMLError, ValueError):
        debts = set()
    thresholds = v4_thresholds(root)

    for path in paths:
        if not path.resolve().is_relative_to((root / 'manuscrit').resolve()) or not path.is_file():
            continue
        try:
            meta, _ = read_scene(path)
            if not isinstance(meta.get('id'), str):
                continue
        except (yaml.YAMLError, ValueError):
            continue
        level = 'ERROR' if meta.get('status') in ('validated', 'CANON', 'VALIDE') else 'WARN'
        try:
            day = calendar_day(meta.get('date'))
        except (ValueError, TypeError):
            report('ERROR', 'DATE_FORMAT', path, 'Date invalide : YYYY-MM-DD requis.')
            day = None
        scenes[meta['id']] = (meta, day, path, level)

        reader = meta.get('reader_state')
        if reader is not None:
            if not isinstance(reader, dict):
                report('ERROR', 'V4_READER_SCHEMA', path, 'reader_state: dictionnaire requis.')
            else:
                for key in ('knows_before', 'believes_before', 'suspects_before', 'expects_before', 'knows_after', 'believes_after'):
                    if key in reader and not isinstance(reader[key], list):
                        report('ERROR', 'V4_READER_SCHEMA', path, f'reader_state.{key}: liste requise.')
                for key in ('dominant_question', 'dominant_question_after', 'human_anchor'):
                    if not meaningful(reader.get(key)):
                        report(level, 'V4_READER_FIELD', path, f'reader_state.{key}: valeur explicite requise avant validation.')
                anchor = reader.get('human_anchor')
                if meaningful(anchor) and anchor not in characters and anchor != 'not_applicable':
                    report(level, 'V4_HUMAN_ANCHOR', path, f'Ancrage humain inconnu : {anchor}.')

        load = meta.get('cognitive_load')
        if load is not None:
            if not isinstance(load, dict):
                report('ERROR', 'V4_LOAD_SCHEMA', path, 'cognitive_load: dictionnaire requis.')
            else:
                counts = {}
                for key in ('new_concepts', 'active_mysteries', 'new_names', 'new_rules', 'major_revelations', 'deferred_questions'):
                    value = load.get(key, [])
                    if not isinstance(value, list):
                        report('ERROR', 'V4_LOAD_SCHEMA', path, f'cognitive_load.{key}: liste requise.')
                        value = []
                    counts[key] = len(value)
                limits = {
                    'active_mysteries': 'max_active_mysteries',
                    'new_concepts': 'max_new_concepts',
                    'new_names': 'max_new_names',
                    'new_rules': 'max_new_rules',
                    'major_revelations': 'max_major_revelations',
                }
                for key, limit_key in limits.items():
                    if counts[key] > thresholds[limit_key]:
                        report('WARN', 'V4_COGNITIVE_OVERLOAD', path, f'{key}: {counts[key]} > seuil {thresholds[limit_key]}. Hiérarchiser ou différer.')
                score = counts['new_concepts'] + counts['new_rules'] + counts['new_names'] // 2 + max(0, counts['active_mysteries'] - 1) + 2 * counts['major_revelations']
                if score > thresholds['max_load_score']:
                    report('WARN', 'V4_LOAD_SCORE', path, f'Charge déclarative {score} > seuil {thresholds["max_load_score"]}.')
                if any(counts.values()) and not meaningful(load.get('dominant_focus')):
                    report(level, 'V4_DOMINANT_FOCUS', path, 'cognitive_load.dominant_focus doit désigner une priorité unique.')
                for mid in load.get('active_mysteries', []) if isinstance(load.get('active_mysteries', []), list) else []:
                    if mysteries and isinstance(mid, str) and mid not in mysteries:
                        report(level, 'V4_MYSTERY_REFERENCE', path, f'Mystère actif inconnu : {mid}.')

        emotion = meta.get('emotional_continuity')
        if emotion is not None:
            if not isinstance(emotion, dict):
                report('ERROR', 'V4_EMOTION_SCHEMA', path, 'emotional_continuity: dictionnaire requis.')
            else:
                for key in ('pov_entry', 'pov_exit'):
                    if not meaningful(emotion.get(key)):
                        report(level, 'V4_EMOTION_FIELD', path, f'emotional_continuity.{key}: état explicite requis.')
                major = load.get('major_revelations', []) if isinstance(load, dict) else []
                if isinstance(major, list) and major and not (meaningful(emotion.get('embodied_cost')) or meaningful(emotion.get('relationship_shift'))):
                    report('WARN', 'V4_REVELATION_UNASSIMILATED', path, 'Révélation majeure sans coût incarné ni déplacement relationnel déclaré.')

        mystery_state = meta.get('mystery_state')
        if mystery_state is not None:
            if not isinstance(mystery_state, dict):
                report('ERROR', 'V4_MYSTERY_SCHEMA', path, 'mystery_state: dictionnaire requis.')
            else:
                seen = {}
                for state in ('active', 'deferred', 'dormant', 'resolved'):
                    values = mystery_state.get(state, [])
                    if not isinstance(values, list):
                        report('ERROR', 'V4_MYSTERY_SCHEMA', path, f'mystery_state.{state}: liste requise.')
                        continue
                    for mid in values:
                        if not isinstance(mid, str):
                            report('ERROR', 'V4_MYSTERY_SCHEMA', path, f'mystery_state.{state}: identifiants texte requis.')
                            continue
                        if mysteries and mid not in mysteries:
                            report(level, 'V4_MYSTERY_REFERENCE', path, f'Mystère inconnu : {mid}.')
                        if mid in seen:
                            report(level, 'V4_MYSTERY_CONFLICT', path, f'{mid} est à la fois {seen[mid]} et {state}.')
                        seen[mid] = state

        debt_state = meta.get('narrative_debt')
        if debt_state is not None:
            if not isinstance(debt_state, dict):
                report('ERROR', 'V4_DEBT_SCHEMA', path, 'narrative_debt: dictionnaire requis.')
            else:
                positions = {}
                for state in ('opened', 'progressed', 'paid'):
                    values = debt_state.get(state, [])
                    if not isinstance(values, list):
                        report('ERROR', 'V4_DEBT_SCHEMA', path, f'narrative_debt.{state}: liste requise.')
                        continue
                    for did in values:
                        if not isinstance(did, str):
                            report('ERROR', 'V4_DEBT_SCHEMA', path, f'narrative_debt.{state}: identifiants texte requis.')
                            continue
                        if debts and did not in debts:
                            report(level, 'V4_DEBT_REFERENCE', path, f'Dette narrative inconnue : {did}.')
                        if did in positions and state != 'progressed':
                            report(level, 'V4_DEBT_CONFLICT', path, f'{did} possède plusieurs états incompatibles dans la scène.')
                        positions[did] = state

    acquired = {}
    for meta, day, path, level in scenes.values():
        for field in ('knowledge_requires', 'knowledge_acquired'):
            items = meta.get(field, [])
            if not isinstance(items, list):
                report('ERROR', 'KNOWLEDGE_SCHEMA', path, f'{field}: liste requise.')
                continue
            for item in items:
                if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip() for k in ('character', 'fact')):
                    report('ERROR', 'KNOWLEDGE_SCHEMA', path, f'{field}: character et fact doivent être des chaînes non vides.')
                    continue
                if item['character'] not in characters:
                    report(level, 'KNOWLEDGE_CHARACTER', path, f"Personnage inconnu : {item['character']}.")
                if field == 'knowledge_acquired':
                    acquired.setdefault((item['character'], item['fact']), []).append((day, meta['id']))

    for sid, (meta, day, path, level) in scenes.items():
        participants = meta.get('characters', [])
        participants = participants if isinstance(participants, list) else []
        participants = [p for p in participants + [meta.get('pov')] if isinstance(p, str)]
        for cid in set(participants):
            person = characters.get(cid, {})
            try:
                birth = calendar_day(person.get('birth_date'))
            except (ValueError, TypeError):
                report('ERROR', 'BIRTH_DATE_FORMAT', character_file, f'{cid}: birth_date invalide.')
                continue
            if day and birth and day < birth:
                report(level, 'BEFORE_BIRTH', path, f'{cid} apparaît le {day}, avant sa naissance le {birth}.')
        causes = meta.get('caused_by', [])
        for cause in causes if isinstance(causes, list) else []:
            if not isinstance(cause, str):
                continue
            if cause == sid:
                report(level, 'SELF_CAUSE', path, 'La scène se déclare sa propre cause.')
            elif cause in scenes and day and scenes[cause][1] and scenes[cause][1] > day:
                report(level, 'CAUSE_IN_FUTURE', path, f'{cause} est datée après son effet {sid}.')
        requirements = meta.get('knowledge_requires', [])
        for item in requirements if isinstance(requirements, list) else []:
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ('character', 'fact')):
                continue
            cid, fact = item['character'], item['fact']
            initial = characters.get(cid, {}).get('initial_knowledge', [])
            if isinstance(initial, list) and fact in initial:
                continue
            origins = [(d, s) for d, s in acquired.get((cid, fact), []) if s != sid]
            if day and any(d and d < day for d, _ in origins):
                continue
            if day is None or any(d is None or d == day for d, _ in origins):
                report('WARN', 'KNOWLEDGE_UNCERTAIN', path, f'{cid} / {fact}: chronologie insuffisante (dates inconnues ou même jour).')
            else:
                report(level, 'KNOWLEDGE_TOO_EARLY', path, f'{cid} utilise {fact} sans acquisition antérieure déclarée.')
    return result
