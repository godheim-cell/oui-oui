"""Déclenchement de recherches bibliographiques pour l'assistant connecté."""
import hashlib
import json
import unicodedata
from datetime import date, datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from author_tools import create
import yaml


def requests(root):
    directory = root / 'recherches/reference-requests'
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(directory.glob('*.json'))]


def sync(root, config):
    inputs = []
    for filename, key, kind in [('concepts.yml', 'concepts', 'concept'), ('themes.yml', 'themes', 'theme'), ('genre_contract.yml', 'genres', 'genre')]:
        file = root / 'data' / filename
        if not file.exists(): continue
        data = yaml.safe_load(file.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get(key), list):
            raise ValueError(f'Registre invalide : {filename}')
        for row in data[key]:
            if not isinstance(row, dict): raise ValueError(f'Entrée invalide : {filename}')
            inputs.append((kind, row.get('name'), str(row.get('id', filename)), row.get('working_definition', row.get('question', ''))))
    inputs.append(('genre', config.get('project', {}).get('genre'), 'config/projet.toml', ''))
    existing = {r['key']: r for r in requests(root)}
    active_keys = set()
    for kind, name, origin, definition in inputs:
        if not isinstance(name, str) or name.strip().casefold() in {'', 'unknown', 'a_definir', 'not_applicable'}: continue
        normalized = ' '.join(unicodedata.normalize('NFKC', name).casefold().split())
        context = str(definition or '').strip()
        if context in {'unknown', 'A_DEFINIR'}: context = ''
        key = hashlib.sha256(json.dumps([kind, normalized, context], ensure_ascii=False).encode()).hexdigest()
        active_keys.add(key)
        if key in existing: continue
        rid = 'REF-' + key[:16]
        directory = root / 'recherches/reference-requests'
        directory.mkdir(parents=True, exist_ok=True)
        record = {'id': rid, 'key': key, 'kind': kind, 'subject': name, 'context': context,
                  'origin': origin, 'status': 'pending', 'created': datetime.now(timezone.utc).isoformat(),
                  'queries': [f'{name} littérature auteurs œuvres de référence', f'{name} fiction authors critical study', f'{name} littérature approches critiques alternatives'],
                  'result': None}
        with (directory / (rid + '.json')).open('x', encoding='utf-8') as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
        existing[key] = record
    for record in existing.values():
        if record['kind'] == 'project': continue
        if record['key'] not in active_keys and record['status'] != 'stale':
            record['status'] = 'stale'
            save(root, record)
        elif record['key'] in active_keys and record['status'] == 'stale':
            record['status'] = 'pending'
            save(root, record)
    return [r for r in existing.values() if r['kind'] != 'project' and r['status'] not in {'completed', 'stale'}]


def save(root, record):
    directory = root / 'recherches/reference-requests'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (record['id'] + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')


def plan(root, config):
    sync(root, config)
    records = requests(root)
    leaves = sorted([r for r in records if r['kind'] != 'project' and r['status'] != 'stale'], key=lambda r: r['key'])
    intention = config.get('project', {}).get('intention', '').strip()
    context = {'subjects': [{'kind': r['kind'], 'subject': r['subject'], 'context': r['context']} for r in leaves], 'intention': intention}
    key = hashlib.sha256(json.dumps(context, ensure_ascii=False, sort_keys=True).encode()).hexdigest() if leaves else None
    for record in records:
        if record['kind'] == 'project' and record['key'] != key and record['status'] != 'stale':
            record['status'] = 'stale'
            save(root, record)
    if not leaves: return []
    record = next((r for r in records if r['kind'] == 'project' and r['key'] == key), None)
    if record is None:
        subject = ' / '.join(r['subject'] for r in leaves)
        record = {'id': 'REF-' + key[:16], 'key': key, 'kind': 'project', 'subject': subject,
                  'context': context, 'members': [r['id'] for r in leaves], 'status': 'pending',
                  'created': datetime.now(timezone.utc).isoformat(), 'result': None,
                  'queries': [f'{subject} {intention} auteurs œuvres références', f'{subject} literary criticism contrasting approaches'],
                  'reuse_results': [r['result'] for r in records if r.get('result')],
                  'arbitrages': 'recherches/reference-decisions.jsonl'}
        save(root, record)
    elif record['status'] == 'stale':
        record['status'] = 'pending'
        save(root, record)
    return [] if record['status'] == 'completed' else [record]


def transition(root, rid, status, reason):
    if status not in {'pending', 'in_progress', 'blocked'} or not reason.strip():
        raise ValueError('Statut pending/in_progress/blocked et raison requis')
    record = next((r for r in requests(root) if r['id'] == rid), None)
    if not record or record['status'] in {'stale', 'completed'}:
        raise ValueError('Demande absente, périmée ou terminée')
    record.setdefault('history', []).append({'from': record['status'], 'to': status, 'reason': reason, 'at': datetime.now(timezone.utc).isoformat()})
    record['status'] = status
    save(root, record)
    return record


def decide(root, rid, author, decision, reason, scope):
    if decision not in {'accept', 'reject', 'defer'} or not reason.strip() or not scope.strip():
        raise ValueError('Arbitrage, raison et portée requis')
    record = next((r for r in requests(root) if r['id'] == rid and r.get('result')), None)
    if not record: raise ValueError('Recherche documentée requise')
    result = json.loads((root / record['result']).read_text(encoding='utf-8'))
    if author not in [a['name'] for a in result['authors']]: raise ValueError('Auteur absent du résultat')
    path = root / 'recherches/reference-decisions.jsonl'
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'request_id': rid, 'author': author, 'decision': decision, 'reason': reason, 'scope': scope, 'at': datetime.now(timezone.utc).isoformat()}, ensure_ascii=False) + '\n')
    return path


def complete(root, rid, filename):
    # Clôture déclarative après navigation réelle de l'assistant, pas une preuve de lecture.
    matches = [r for r in requests(root) if r['id'] == rid]
    if len(matches) != 1: raise ValueError('Demande introuvable')
    if matches[0]['status'] in {'stale', 'completed'}: raise ValueError('Demande périmée ou déjà terminée')
    path = (root / filename).resolve()
    if not path.is_relative_to((root / 'recherches').resolve()):
        raise ValueError('Le résultat doit être conservé dans recherches/')
    result = json.loads(path.read_text(encoding='utf-8'))
    if result.get('request_id') != rid: raise ValueError('Résultat associé à une autre demande')
    authors = result.get('authors')
    if not isinstance(authors, list) or not authors: raise ValueError('Au moins un auteur documenté requis')
    names = set()
    for author in authors:
        if not isinstance(author, dict) or not all(isinstance(author.get(k), str) and author[k].strip() for k in ('name', 'relevance', 'technique', 'application', 'limits')):
            raise ValueError('Auteur : nom, pertinence, procédé, application et limites requis')
        name = ' '.join(author['name'].casefold().split())
        if name in names: raise ValueError('Auteur dupliqué')
        names.add(name)
        if author.get('role') not in {'central', 'counterpoint', 'unexpected'}:
            raise ValueError('Rôle central/counterpoint/unexpected requis')
        if not isinstance(author.get('works'), list) or not author['works'] or not all(isinstance(w, str) and w.strip() for w in author['works']):
            raise ValueError('Œuvres précises requises')
        sources = author.get('sources')
        if not isinstance(sources, list) or not sources: raise ValueError('Sources requises')
        urls = set()
        for source in sources:
            if not isinstance(source, dict) or source.get('reading_status') != 'read' or not all(isinstance(source.get(k), str) and source[k].strip() for k in ('url', 'accessed', 'evidence')):
                raise ValueError('Source lue avec URL, date et élément étayé requise')
            parsed = urlsplit(source['url'])
            if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username or any(c.isspace() for c in source['url']): raise ValueError('URL web valide requise')
            normalized = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), parsed.query, ''))
            if normalized in urls: raise ValueError('Source dupliquée pour cet auteur')
            urls.add(normalized)
            if date.fromisoformat(source['accessed']) > date.today(): raise ValueError('Date de consultation future')
            if source.get('material') not in {'work', 'excerpt', 'commentary'}:
                raise ValueError('Préciser material : work/excerpt/commentary')
        links = author.get('claim_sources', {})
        for claim in ('relevance', 'technique'):
            indices = links.get(claim) if isinstance(links, dict) else None
            if not isinstance(indices, list) or not indices or not all(type(i) is int and 0 <= i < len(sources) for i in indices):
                raise ValueError('Relier relevance et technique aux indices de sources (base 0)')
    record = matches[0]
    frozen = create(root, f'recherches/reference-results/{rid}.json', json.dumps(result, ensure_ascii=False, indent=2))
    exercises = '# Exercices proposés — NON CANON\n\nChoisir une référence et une scène avant tout essai. Aucun original ne sera remplacé par ce dossier.\n'
    for author in authors:
        exercises += f"\n## {author['name']} ({author['role']})\n\nProcédé documenté : {author['technique']}\n\nApplication proposée : {author['application']}\n\nLimites : {author['limits']}\n\nScène choisie :\nEffet attendu :\nInstantané avant essai :\nVariante sur un seul axe :\nComparaison / retour lecteur :\nDécision et raison :\n"
    exercise = create(root, f'atelier/exercices/{rid}.md', exercises)
    record.update(status='completed', result=frozen.relative_to(root).as_posix(), exercise=exercise.relative_to(root).as_posix(), completed=datetime.now(timezone.utc).isoformat())
    save(root, record)
    return frozen
