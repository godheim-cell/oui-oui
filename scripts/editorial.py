"""Révisions protégées et dossiers de décision. Aucune analyse IA autonome."""
import argparse
import difflib
import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import yaml
from author_tools import active_scenes, create


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def scene(root, sid):
    if not sid or not re.fullmatch(r'SCN-\d{3,4}', sid):
        raise ValueError('Identifiant SCN requis')
    matches = [p for p in active_scenes(root) if p.name.startswith(sid + '-')]
    if len(matches) != 1:
        raise ValueError('Une scène active unique est requise')
    return matches[0]


def snapshot(root, source, reason):
    raw = source.read_bytes()
    record = {'source': source.relative_to(root).as_posix(), 'sha256': digest(raw),
              'text': raw.decode('utf-8'), 'reason': reason,
              'created': datetime.now(timezone.utc).isoformat()}
    return create(root, f'atelier/snapshots/{uuid.uuid4().hex}.json', json.dumps(record, ensure_ascii=False, indent=2))


def load_snapshot(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to((root / 'atelier/snapshots').resolve()):
        raise ValueError('Instantané hors du dossier autorisé')
    record = json.loads(path.read_text(encoding='utf-8'))
    if digest(record['text'].encode('utf-8')) != record['sha256']:
        raise ValueError('Instantané altéré')
    target = (root / record['source']).resolve()
    if target not in active_scenes(root):
        raise ValueError('La cible ne correspond plus à une scène active')
    return record, target


def yaml_data(path, default=None):
    if not path.exists():
        return {} if default is None else default
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    return data if isinstance(data, dict) else ({} if default is None else default)


def list_text(value):
    if not isinstance(value, list) or not value:
        return '—'
    return ', '.join(str(x) for x in value)


def v4_load_score(meta):
    load = meta.get('cognitive_load', {})
    if not isinstance(load, dict):
        return 0
    def n(key):
        value = load.get(key, [])
        return len(value) if isinstance(value, list) else 0
    return n('new_concepts') + n('new_rules') + n('new_names') // 2 + max(0, n('active_mysteries') - 1) + 2 * n('major_revelations')


def v4_scene_meta(root):
    from nexus import frontmatter
    result = []
    for source in active_scenes(root):
        meta, _ = frontmatter(source)
        result.append((source, meta))
    return result


def reader_map(root):
    text = '# Carte lecteur V4 — déclarative, NON CANON\n\n'
    text += 'Aucune expérience réelle n’est inférée. Les champs décrivent l’effet visé et doivent être confrontés aux bêta-lectures. La question dominante doit rester unique même lorsque plusieurs mystères sont actifs.\n'
    for source, meta in v4_scene_meta(root):
        reader = meta.get('reader_state', {}) if isinstance(meta.get('reader_state'), dict) else {}
        load = meta.get('cognitive_load', {}) if isinstance(meta.get('cognitive_load'), dict) else {}
        emotional = meta.get('emotional_continuity', {}) if isinstance(meta.get('emotional_continuity'), dict) else {}
        mystery = meta.get('mystery_state', {}) if isinstance(meta.get('mystery_state'), dict) else {}
        debt = meta.get('narrative_debt', {}) if isinstance(meta.get('narrative_debt'), dict) else {}
        text += f"\n## {meta.get('id')} — chapitre {meta.get('chapter')}\n\nVersion SHA256 : {digest(source.read_bytes())}\n"
        text += f"Question dominante avant : {reader.get('dominant_question', '')}\n"
        text += f"Question dominante après : {reader.get('dominant_question_after', '')}\n"
        text += f"Ce que le lecteur sait avant : {list_text(reader.get('knows_before'))}\n"
        text += f"Ce que le lecteur sait après : {list_text(reader.get('knows_after'))}\n"
        text += f"Hypothèse / croyance après : {list_text(reader.get('believes_after'))}\n"
        text += f"Ancrage humain : {reader.get('human_anchor', '')}\n"
        text += f"Focus cognitif : {load.get('dominant_focus', '')}\n"
        text += f"Charge déclarative : {v4_load_score(meta)}\n"
        text += f"Mystères actifs : {list_text(mystery.get('active') or load.get('active_mysteries'))}\n"
        text += f"Mystères différés : {list_text(mystery.get('deferred'))}\n"
        text += f"État émotionnel POV : {emotional.get('pov_entry', '')} → {emotional.get('pov_exit', '')}\n"
        text += f"Coût incarné : {emotional.get('embodied_cost', '')}\n"
        text += f"Dette ouverte/progressée/payée : {list_text(debt.get('opened'))} / {list_text(debt.get('progressed'))} / {list_text(debt.get('paid'))}\n"
        text += 'Retour lecteur observé :\n'
    text += '\n## Contrôle de fin\n\nRepérer les scènes où la question dominante change sans assimilation, où la charge augmente plusieurs scènes de suite, ou où l’ancrage humain disparaît pendant une séquence abstraite.\n'
    return create(root, f'atelier/editorial/reader-map-v4-{uuid.uuid4().hex}.md', text)


def experience_map(root):
    lines = ['# Tableau de bord V4 — expérience lecteur', '', '| Scène | Focus | Question avant → après | Mystères actifs | Charge | Ancrage humain | Émotion POV | Coût |', '|---|---|---|---|---:|---|---|---|']
    for _, meta in v4_scene_meta(root):
        reader = meta.get('reader_state', {}) if isinstance(meta.get('reader_state'), dict) else {}
        load = meta.get('cognitive_load', {}) if isinstance(meta.get('cognitive_load'), dict) else {}
        emotional = meta.get('emotional_continuity', {}) if isinstance(meta.get('emotional_continuity'), dict) else {}
        mysteries = load.get('active_mysteries', []) if isinstance(load.get('active_mysteries', []), list) else []
        q1 = str(reader.get('dominant_question', '')).replace('|', '/')
        q2 = str(reader.get('dominant_question_after', '')).replace('|', '/')
        lines.append(f"| {meta.get('id')} | {str(load.get('dominant_focus', '')).replace('|', '/')} | {q1} → {q2} | {list_text(mysteries)} | {v4_load_score(meta)} | {reader.get('human_anchor', '')} | {str(emotional.get('pov_entry', '')).replace('|', '/')} → {str(emotional.get('pov_exit', '')).replace('|', '/')} | {str(emotional.get('embodied_cost', '')).replace('|', '/')} |")
    lines += ['', 'Ce tableau ne mesure pas automatiquement la qualité. Il expose les zones où l’auteur doit vérifier hiérarchie, densité et continuité émotionnelle.']
    return create(root, f'reports/experience-v4-{uuid.uuid4().hex}.md', '\n'.join(lines) + '\n')


def mystery_graph(root):
    data = yaml_data(root / 'data/mysteries.yml')
    mysteries = [x for x in data.get('mysteries', []) if isinstance(x, dict)]
    touches = defaultdict(list)
    for _, meta in v4_scene_meta(root):
        sid = str(meta.get('id', ''))
        state = meta.get('mystery_state', {}) if isinstance(meta.get('mystery_state'), dict) else {}
        for category in ('active', 'deferred', 'dormant', 'resolved'):
            values = state.get(category, [])
            for mid in values if isinstance(values, list) else []:
                touches[str(mid)].append((sid, category))
    lines = ['# Graphe des mystères V4', '', '| Mystère | Question | État registre | Dernier état de scène | Dernière scène |', '|---|---|---|---|---|']
    for item in mysteries:
        mid = str(item.get('id', ''))
        last = touches.get(mid, [])[-1] if touches.get(mid) else ('—', '—')
        question = str(item.get('question', '')).replace('|', '/')
        lines.append(f"| {mid} | {question} | {item.get('status', 'open')} | {last[1]} | {last[0]} |")
    lines += ['', '## Règle V4', '', 'Un mystère peut être **actif**, **différé**, **dormant** ou **résolu**. Plusieurs mystères peuvent exister, mais une scène doit déclarer un seul `dominant_focus`.']
    return create(root, f'reports/mystery-graph-v4-{uuid.uuid4().hex}.md', '\n'.join(lines) + '\n')


def debt_ledger(root):
    data = yaml_data(root / 'data/narrative_debt.yml')
    debts = [x for x in data.get('debts', []) if isinstance(x, dict)]
    touches = defaultdict(list)
    for _, meta in v4_scene_meta(root):
        sid = str(meta.get('id', ''))
        state = meta.get('narrative_debt', {}) if isinstance(meta.get('narrative_debt'), dict) else {}
        for category in ('opened', 'progressed', 'paid'):
            values = state.get(category, [])
            for did in values if isinstance(values, list) else []:
                touches[str(did)].append((sid, category))
    lines = ['# Registre des dettes narratives V4', '', '| Dette | Description | Gravité | Ouverte par | Échéance | Statut | Dernier contact |', '|---|---|---|---|---|---|---|']
    for item in debts:
        did = str(item.get('id', ''))
        last = touches.get(did, [])[-1] if touches.get(did) else ('—', '—')
        lines.append(f"| {did} | {str(item.get('description', '')).replace('|', '/')} | {item.get('severity', '')} | {item.get('created_by', '')} | {item.get('resolve_before', '')} | {item.get('status', 'open')} | {last[0]} / {last[1]} |")
    if not debts:
        lines += ['', 'Aucune dette enregistrée. Une saga ne doit pas confondre mystère ouvert et dette sans échéance.']
    return create(root, f'reports/debt-ledger-v4-{uuid.uuid4().hex}.md', '\n'.join(lines) + '\n')


def saga_control(root):
    data = yaml_data(root / 'data/saga_control.yml')
    saga = data.get('saga', {}) if isinstance(data.get('saga'), dict) else {}
    lines = ['# Contrôleur de saga V4', '', f"Saga : {saga.get('title', 'à définir')}", f"Volume courant : {saga.get('current_volume', 'à définir')}", '']
    for volume in saga.get('volumes', []) if isinstance(saga.get('volumes', []), list) else []:
        if not isinstance(volume, dict):
            continue
        lines += [f"## {volume.get('id', 'volume')} — {volume.get('title', 'sans titre')}", '', f"Statut : {volume.get('status', '')}", f"Promesse : {volume.get('promise', '')}", f"Question centrale : {volume.get('central_question', '')}", f"Transformation : {volume.get('hero_transformation', '')}", f"Coût final : {volume.get('final_cost', '')}", '', 'Réponses irréversibles :']
        lines += [f"- {x}" for x in volume.get('irreversible_answers', [])] or ['- aucune déclarée']
        lines += ['', 'Dettes héritées :'] + ([f"- {x}" for x in volume.get('inherited_debts', [])] or ['- aucune'])
        lines += ['', 'Vérités protégées :'] + ([f"- {x}" for x in volume.get('protected_truths', [])] or ['- aucune'])
        lines += ['']
    lines += ['## Principe', '', 'Un volume suivant peut recontextualiser une vérité antérieure, mais ne doit pas l’annuler sans preuve préparée. Chaque tome doit apporter au moins une réponse irréversible et payer une partie des dettes héritées.']
    return create(root, f'reports/saga-control-v4-{uuid.uuid4().hex}.md', '\n'.join(lines) + '\n')


def beta_synthesis(root):
    groups = defaultdict(list)
    files = sorted((root / 'atelier/editorial').glob('beta-feedback-*.json')) if (root / 'atelier/editorial').exists() else []
    for path in files:
        try:
            item = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            continue
        key = (item.get('scene'), item.get('reaction'), item.get('subject'))
        groups[key].append(item)
    lines = ['# Synthèse bêta V4', '', '| Scène | Réaction | Sujet | Lecteurs | Signal |', '|---|---|---|---:|---|']
    for (sid, reaction, subject), items in sorted(groups.items(), key=lambda x: str(x[0])):
        readers = len({str(x.get('reader', 'anonyme')) for x in items})
        signal = 'convergence à examiner' if readers >= 2 else 'signal isolé'
        lines.append(f"| {sid} | {reaction} | {str(subject).replace('|', '/')} | {readers} | {signal} |")
    if not groups:
        lines += ['', 'Aucun retour structuré `beta-feedback` enregistré.']
    lines += ['', 'Une convergence n’est pas une instruction de réécriture : elle déclenche un diagnostic, puis un nouveau test après correction.']
    return create(root, f'reports/beta-synthesis-v4-{uuid.uuid4().hex}.md', '\n'.join(lines) + '\n')


def dispatch(argv, root):
    names = {'snapshot', 'snapshot-compare', 'snapshot-restore', 'reader-map', 'experience-map',
             'mystery-graph', 'debt-ledger', 'saga-control', 'beta-synthesis',
             'beta-feedback', 'evidence-review', 'world-consequences', 'voice-decision'}
    if argv[0] not in names:
        return False
    p = argparse.ArgumentParser(prog='nexus ' + argv[0])
    p.add_argument('--id')
    p.add_argument('--snapshot')
    p.add_argument('--expected-sha')
    p.add_argument('--reason', default='')
    p.add_argument('--subject', default='À préciser')
    p.add_argument('--quote', default='')
    p.add_argument('--reference')
    p.add_argument('--reference-quote', default='')
    p.add_argument('--reader', default='anonyme')
    p.add_argument('--reaction', choices=['confusion', 'ennui', 'emotion', 'anticipation'], default='confusion')
    p.add_argument('--decision', choices=['pending', 'accept', 'test', 'reject', 'defer'], default='pending')
    a = p.parse_args(argv[1:])
    command = argv[0]
    if command == 'snapshot':
        if not a.reason.strip(): p.error('--reason requis')
        output = snapshot(root, scene(root, a.id), a.reason)
    elif command in {'snapshot-compare', 'snapshot-restore'}:
        if not a.snapshot: p.error('--snapshot requis')
        record, target = load_snapshot(root, a.snapshot)
        raw = target.read_bytes()
        current_sha = digest(raw)
        if command == 'snapshot-restore':
            if a.expected_sha != current_sha or not a.reason.strip():
                p.error('Relancer compare puis fournir --expected-sha actuel et --reason ; aucune restauration effectuée')
            backup = snapshot(root, target, 'Avant restauration : ' + a.reason)
            if digest(target.read_bytes()) != current_sha:
                raise ValueError('La scène a changé pendant la préparation ; restauration annulée')
            target.write_bytes(record['text'].encode('utf-8'))
            print('Sauvegarde de retour : ' + backup.relative_to(root).as_posix())
            print('Relancer audit, cockpit et build ; aucune validation éditoriale automatique.')
            output = target
        else:
            diff = ''.join(difflib.unified_diff(record['text'].splitlines(True), raw.decode('utf-8').splitlines(True), fromfile='instantane', tofile='actuel'))
            text = f"# Comparaison\n\nSource : {record['source']}\nSHA256 actuel : {current_sha}\nModifié depuis instantané : {current_sha != record['sha256']}\n\n```diff\n{diff}\n```\n\nAvant adoption : vérifier les références avec la commande impact et relire les conséquences implicites.\n"
            output = create(root, f'reports/revisions/compare-{uuid.uuid4().hex}.md', text)
    elif command == 'reader-map':
        output = reader_map(root)
    elif command == 'experience-map':
        output = experience_map(root)
    elif command == 'mystery-graph':
        output = mystery_graph(root)
    elif command == 'debt-ledger':
        output = debt_ledger(root)
    elif command == 'saga-control':
        output = saga_control(root)
    elif command == 'beta-synthesis':
        output = beta_synthesis(root)
    elif command in {'beta-feedback', 'evidence-review', 'voice-decision'}:
        source = scene(root, a.id)
        raw = source.read_bytes()
        if not a.quote.strip() or a.quote not in raw.decode('utf-8'):
            p.error('--quote doit reproduire un passage présent dans la scène')
        record = {'kind': command, 'scene': a.id, 'source': source.relative_to(root).as_posix(),
                  'sha256': digest(raw),
                  'quote': a.quote, 'subject': a.subject, 'decision': a.decision, 'reason': a.reason}
        if command == 'beta-feedback':
            record.update(reader=a.reader, reaction=a.reaction, interpretation='', action='', result='')
        elif command == 'voice-decision':
            if a.decision == 'pending' or not a.reason.strip():
                p.error('Une décision explicite et --reason sont requis pour mémoriser un arbitrage')
            record.update(scope='Ce passage uniquement ; généralisation à valider', counterexample='', revisable=True)
        else:
            if not a.reference or not a.reference_quote.strip():
                p.error('--reference et --reference-quote requis')
            ref = (root / a.reference).resolve()
            if not ref.is_relative_to(root.resolve()) or ref.suffix not in {'.md', '.yml'}:
                p.error('Référence interne Markdown ou YAML requise')
            reference_raw = ref.read_bytes()
            if a.reference_quote not in reference_raw.decode('utf-8'):
                p.error('Passage de référence introuvable')
            record.update(reference=ref.relative_to(root).as_posix(), reference_sha256=digest(reference_raw),
                          reference_quote=a.reference_quote, hypothesis='',
                          alternatives=['mensonge', 'souvenir', 'ellipse', 'narrateur non fiable'],
                          author_question='', verdict='pending')
        frozen = snapshot(root, source, command + ' : version de référence')
        record['snapshot'] = frozen.relative_to(root).as_posix()
        output = create(root, f'atelier/editorial/{command}-{uuid.uuid4().hex}.json', json.dumps(record, ensure_ascii=False, indent=2))
    else:
        text = f'# Conséquences du monde — NON CANON\n\nPostulat : {a.subject}\n\n'
        for heading in ['Limites et coût', 'Ressource rare et maintenance', 'Qui décide et qui bénéficie ?', 'Qui paie et qui résiste ?', 'Vie quotidienne et institutions', 'Pourquoi aucune solution plus simple ?', 'Conséquences de second ordre', 'Scène qui dramatise ce coût', 'Faits documentés / extrapolations / inventions', 'Contre-exemple et décision de l’auteur']:
            text += f'## {heading}\n\nÀ explorer.\n\n'
        text += 'Ce dossier organise un raisonnement avec l’auteur ou l’assistant ; il ne simule pas une économie et ne recherche pas de sources automatiquement.\n'
        output = create(root, f'atelier/editorial/world-{uuid.uuid4().hex}.md', text)
    print(output.relative_to(root))
    return True
