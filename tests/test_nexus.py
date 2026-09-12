"""Fixtures fictives et temporaires : aucun canon ajouté à la matrice."""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import nexus
import author_tools
import editorial
import json
import reference_research


class NexusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.original = nexus.ROOT
        for directory in ('config', 'data', 'templates'):
            shutil.copytree(self.original / directory, self.root / directory)
        # Fixtures indépendantes des données et de la configuration de l'auteur.
        for file in (self.root / 'data').glob('*.yml'):
            data = nexus.yaml.safe_load(file.read_text(encoding='utf-8'))
            file.write_text(nexus.yaml.safe_dump({key: [] for key in data}), encoding='utf-8')
        (self.root / 'config/projet.toml').write_text('''
[project]
title = "Fixture"
author_mode = "essential"
status = "exploration"
[manuscript]
root = "manuscrit"
active_volume = "tome-01"
manifest = "manuscrit/tome-01/manifest.txt"
output = "publication/manuscrit.md"
[quality]
minimum_scene_words = 300
maximum_scene_words = 5000
max_author_priorities = 5
[author]
checkpoint = "data/checkpoint.json"
cockpit = "COCKPIT_AUTEUR.md"
auto_add_new_scene_to_manifest = true
''', encoding='utf-8')
        for directory in ('manuscrit/tome-01', 'reports', 'decisions', 'recherches'):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.manifest = self.root / 'manuscrit/tome-01/manifest.txt'
        self.manifest.write_text('')
        nexus.ROOT = self.root

    def tearDown(self):
        nexus.ROOT = self.original
        self.tmp.cleanup()

    def scene(self, number=1, status='draft'):
        path = self.root / f'manuscrit/tome-01/SCN-{number:03d}-test.md'
        path.write_text(f'''---
id: SCN-{number:03d}
title: "Un choix : maintenant"
status: {status}
chapter: 1
order: {number}
pov: not_applicable
location: not_applicable
date: not_applicable
characters: []
change: |
  Une porte se ferme.
  Un choix reste.
consequence: La route est fermée.
reader_hook: Qui possède la clef ?
secret: META_SECRET
---
Prose visible {number}.
<!-- NOTE_SECRETE -->
''', encoding='utf-8')
        with self.manifest.open('a') as stream:
            stream.write(str(path.relative_to(self.root)) + '\n')
        return path

    def run_tool(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertTrue(author_tools.dispatch(list(args), self.root))
        return self.root / output.getvalue().strip()

    def test_validated_filled_scene_and_multiline_yaml(self):
        path = self.scene(status='validated')
        self.assertIn('Un choix reste.', nexus.frontmatter(path)[0]['change'])
        self.assertFalse([f for f in nexus.audit() if f.level == 'ERROR'])

    def test_lifecycle(self):
        path = self.scene()
        path.write_text(path.read_text().replace('La route est fermée.', 'unknown'))
        self.assertFalse([f for f in nexus.audit() if f.level == 'ERROR'])
        path.write_text(path.read_text().replace('status: draft', 'status: validated'))
        self.assertTrue([f for f in nexus.audit() if f.level == 'ERROR' and f.code == 'PLACEHOLDER'])

    def test_invalid_yaml_is_reported(self):
        path = self.scene()
        path.write_text('---\nid: [\n---\nTexte')
        self.assertIn('SCENE_FRONTMATTER', [f.code for f in nexus.audit()])

    def test_registry_nested_values_and_input_preserved(self):
        row = {'id': 'CHR-001', 'name': 'Nom : test', 'knowledge': [{'fact': 'secret'}]}
        nexus.append_registry('characters.yml', 'characters', row)
        self.assertEqual(nexus.registry_rows(self.root / 'data/characters.yml'), [row])
        self.assertEqual(row['id'], 'CHR-001')
        with self.assertRaises(ValueError):
            nexus.append_registry('characters.yml', 'characters', row)

    def test_manifest_duplicate_and_escape_rejected(self):
        path = self.scene()
        with self.manifest.open('a') as stream:
            stream.write(str(path.relative_to(self.root)) + '\n')
        with self.assertRaises(ValueError): author_tools.active_scenes(self.root)
        self.manifest.write_text('config/projet.toml\n')
        with self.assertRaises(ValueError): nexus.build()

    def test_reader_pack_excludes_future_and_notes(self):
        self.scene(1)
        self.scene(2)
        text = self.run_tool('reader-pack', '--through', '1').read_text()
        self.assertIn('Prose visible 1', text)
        for secret in ('Prose visible 2', 'META_SECRET', 'NOTE_SECRETE'):
            self.assertNotIn(secret, text)

    def test_variant_preserves_original(self):
        path = self.scene()
        original = path.read_bytes()
        output = self.run_tool('variant-lab', '--id', 'SCN-001', '--axis', 'rythme')
        self.assertEqual(path.read_bytes(), original)
        self.assertIn('SHA256', output.read_text())

    def test_research_does_not_overwrite(self):
        a = nexus.create_research_dossier('Même sujet', None, None, None)
        a.write_text('Mes notes personnelles')
        b = nexus.create_research_dossier('Même sujet', None, None, None)
        self.assertNotEqual(a, b)
        self.assertEqual(a.read_text(), 'Mes notes personnelles')

    def test_title_colon_and_build_notes(self):
        path = nexus.new_scene(1, 'Question : pourquoi ?')
        self.assertEqual(nexus.frontmatter(path)[0]['title'], 'Question : pourquoi ?')
        self.assertNotIn('<!--', nexus.build().read_text())

    def test_new_assisted_commands(self):
        for command in ('creative-interview', 'influence-note', 'research-brief'):
            self.assertTrue(self.run_tool(command, '--subject', 'Sujet fictif').is_file())
        self.scene()
        self.assertIn('SCN-001-test.md', self.run_tool('impact', '--id', 'SCN-001').read_text())

    def metadata(self, path, **values):
        meta, body = nexus.frontmatter(path)
        meta.update(values)
        path.write_text('---\n' + nexus.yaml.safe_dump(meta, allow_unicode=True) + '---\n' + body, encoding='utf-8')

    def codes(self):
        return {f.code for f in nexus.audit()}

    def test_before_birth(self):
        nexus.append_registry('characters.yml', 'characters', {'id': 'CHR-001', 'birth_date': '2200-01-01'})
        scene = self.scene(status='validated')
        self.metadata(scene, date='2184-05-01', pov='CHR-001')
        self.assertIn('BEFORE_BIRTH', self.codes())

    def test_cause_in_future_but_flashback_allowed(self):
        first, second = self.scene(1), self.scene(2)
        self.metadata(first, date='2184-05-03')
        self.metadata(second, date='2184-05-01')
        self.assertNotIn('CAUSE_IN_FUTURE', self.codes())
        self.metadata(second, caused_by=['SCN-001'])
        self.assertIn('CAUSE_IN_FUTURE', self.codes())

    def test_knowledge_uses_dates_not_manifest_order(self):
        nexus.append_registry('characters.yml', 'characters', {'id': 'CHR-001'})
        later, earlier = self.scene(1), self.scene(2)
        fact = {'character': 'CHR-001', 'fact': 'origine_signal'}
        self.metadata(later, date='2184-05-03', knowledge_requires=[fact])
        self.metadata(earlier, date='2184-05-01', knowledge_acquired=[fact])
        self.assertNotIn('KNOWLEDGE_TOO_EARLY', self.codes())
        self.metadata(earlier, date='2184-05-04')
        self.assertIn('KNOWLEDGE_TOO_EARLY', self.codes())

    def test_same_day_knowledge_is_uncertain(self):
        nexus.append_registry('characters.yml', 'characters', {'id': 'CHR-001'})
        first, second = self.scene(1), self.scene(2)
        fact = {'character': 'CHR-001', 'fact': 'origine_signal'}
        self.metadata(first, date='2184-05-01', knowledge_acquired=[fact])
        self.metadata(second, date='2184-05-01', knowledge_requires=[fact])
        self.assertIn('KNOWLEDGE_UNCERTAIN', self.codes())
        self.assertNotIn('KNOWLEDGE_TOO_EARLY', self.codes())

    def test_initial_knowledge(self):
        nexus.append_registry('characters.yml', 'characters', {'id': 'CHR-001', 'initial_knowledge': ['origine_signal']})
        scene = self.scene()
        self.metadata(scene, date='2184-05-01', knowledge_requires=[{'character': 'CHR-001', 'fact': 'origine_signal'}])
        self.assertNotIn('KNOWLEDGE_TOO_EARLY', self.codes())

    def test_bad_date_and_knowledge_schema(self):
        scene = self.scene()
        self.metadata(scene, date='2184-02-30', knowledge_requires='texte au lieu de liste')
        self.assertTrue({'DATE_FORMAT', 'KNOWLEDGE_SCHEMA'} <= self.codes())

    def test_prose_not_semantically_checked(self):
        scene = self.scene(status='validated')
        self.metadata(scene, date='2184-05-01')
        with scene.open('a', encoding='utf-8') as stream:
            stream.write('Elle naquit en 2200, vingt ans avant ce jour de 2184.')
        self.assertFalse([f for f in nexus.audit() if f.level == 'ERROR'])

    def editorial_tool(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertTrue(editorial.dispatch(list(args), self.root))
        return self.root / output.getvalue().strip().splitlines()[-1]

    def test_snapshot_compare_restore_and_backup(self):
        source = self.scene()
        original = source.read_bytes()
        saved = self.editorial_tool('snapshot', '--id', 'SCN-001', '--reason', 'Essai')
        source.write_bytes(original + b'\nModification\n')
        modified = source.read_bytes()
        compare = self.editorial_tool('snapshot-compare', '--snapshot', str(saved))
        self.assertIn('+Modification', compare.read_text())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.editorial_tool('snapshot-restore', '--snapshot', str(saved), '--reason', 'Retour', '--expected-sha', editorial.digest(original))
        self.assertEqual(source.read_bytes(), modified)
        self.editorial_tool('snapshot-restore', '--snapshot', str(saved), '--reason', 'Retour', '--expected-sha', editorial.digest(modified))
        self.assertEqual(source.read_bytes(), original)
        backups = [json.loads(p.read_text()) for p in (self.root / 'atelier/snapshots').glob('*.json')]
        self.assertTrue(any(p['sha256'] == editorial.digest(modified) for p in backups))

    def test_snapshot_tamper_and_external_path_rejected(self):
        self.scene()
        saved = self.editorial_tool('snapshot', '--id', 'SCN-001', '--reason', 'Essai')
        record = json.loads(saved.read_text())
        record['text'] += 'altération'
        saved.write_text(json.dumps(record))
        with self.assertRaises(ValueError): editorial.load_snapshot(self.root, str(saved))
        with self.assertRaises(ValueError): editorial.load_snapshot(self.root, '../outside.json')

    def test_feedback_version_and_quote_validation(self):
        source = self.scene()
        output = self.editorial_tool('beta-feedback', '--id', 'SCN-001', '--quote', 'Prose visible 1.', '--reader', 'Testeur', '--reaction', 'emotion')
        record = json.loads(output.read_text())
        self.assertEqual(record['sha256'], editorial.digest(source.read_bytes()))
        self.assertTrue((self.root / record['snapshot']).is_file())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.editorial_tool('beta-feedback', '--id', 'SCN-001', '--quote', 'Passage inventé')

    def test_evidence_requires_two_existing_passages(self):
        source = self.scene()
        output = self.editorial_tool('evidence-review', '--id', 'SCN-001', '--quote', 'Prose visible', '--reference', str(source), '--reference-quote', 'Un choix')
        self.assertEqual(json.loads(output.read_text())['verdict'], 'pending')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.editorial_tool('evidence-review', '--id', 'SCN-001', '--quote', 'Prose visible', '--reference', str(source), '--reference-quote', 'inexistant')

    def test_voice_requires_explicit_reason(self):
        self.scene()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.editorial_tool('voice-decision', '--id', 'SCN-001', '--quote', 'Prose visible')
        output = self.editorial_tool('voice-decision', '--id', 'SCN-001', '--quote', 'Prose visible', '--decision', 'accept', '--reason', 'Clarté')
        self.assertTrue(json.loads(output.read_text())['revisable'])

    def test_reader_map_world_and_cockpit_focus(self):
        self.scene()
        self.assertIn('SCN-001', self.editorial_tool('reader-map').read_text())
        self.assertIn('Qui paie', self.editorial_tool('world-consequences', '--subject', 'Postulat fictif').read_text())
        exploration = nexus.cockpit('exploration').read_text()
        revision = nexus.cockpit('revision').read_text()
        writing = nexus.cockpit('writing').read_text()
        self.assertIn('Question créative', exploration)
        self.assertNotIn('Scène courte:', exploration)
        self.assertIn('Scène courte:', revision)
        self.assertIn('Scène de travail', writing)

    def test_reference_triggers_and_deduplication(self):
        nexus.create_concept('Mémoire')
        nexus.create_theme('Consentement')
        nexus.create_genre_profile('Science-fiction')
        pending = reference_research.sync(self.root, nexus.config())
        self.assertEqual({r['kind'] for r in pending}, {'concept', 'theme', 'genre'})
        self.assertEqual(len(pending), 3)
        self.assertIn('Recherches de références', nexus.cockpit().read_text())
        cfg = nexus.config()
        cfg['project']['genre'] = ' science-fiction '
        self.assertEqual(len(reference_research.sync(self.root, cfg)), 3)

    def test_blank_reference_inputs_and_changed_definition(self):
        self.assertEqual(reference_research.sync(self.root, nexus.config()), [])
        nexus.create_concept('Mémoire')
        path = self.root / 'data/concepts.yml'
        data = nexus.yaml.safe_load(path.read_text())
        data['concepts'][0]['working_definition'] = 'Transmission collective'
        path.write_text(nexus.yaml.safe_dump(data))
        self.assertEqual(len(reference_research.sync(self.root, nexus.config())), 1)
        self.assertTrue(any(r['status'] == 'stale' for r in reference_research.requests(self.root)))

    def test_reference_completion_requires_documented_authors(self):
        nexus.create_theme('Sujet de fixture')
        rid = reference_research.plan(self.root, nexus.config())[0]['id']
        output = self.root / 'recherches/resultat.json'
        output.write_text(json.dumps({'request_id': rid, 'authors': []}))
        with self.assertRaises(ValueError): reference_research.complete(self.root, rid, str(output))
        self.assertEqual(reference_research.requests(self.root)[0]['status'], 'pending')
        output.write_text(json.dumps(self.reference_fixture(rid)))
        reference_research.complete(self.root, rid, str(output))
        self.assertEqual(reference_research.plan(self.root, nexus.config()), [])

    def reference_fixture(self, rid):
        return {'request_id': rid, 'authors': [{'name': 'Auteur fictif de test', 'works': ['Titre fictif'], 'role': 'central', 'relevance': 'Fixture', 'technique': 'Fixture', 'application': 'Essai de changement de focalisation', 'limits': 'Données synthétiques', 'claim_sources': {'relevance': [0], 'technique': [0]}, 'sources': [{'url': 'https://example.com', 'accessed': '2020-01-01', 'reading_status': 'read', 'material': 'commentary', 'evidence': 'Fixture synthétique, aucun accès réel'}]}]}

    def test_crossed_plan_intention_and_stale_results(self):
        nexus.create_concept('Mémoire')
        nexus.create_theme('Identité')
        nexus.create_genre_profile('SF')
        cfg = nexus.config()
        cfg['project']['intention'] = 'Conflit intime'
        batch = reference_research.plan(self.root, cfg)
        self.assertEqual(len(batch), 1)
        self.assertEqual(len(batch[0]['members']), 3)
        self.assertIn('Conflit intime', batch[0]['queries'][0])
        rid = batch[0]['id']
        file = self.root / 'recherches/resultat.json'
        file.write_text(json.dumps(self.reference_fixture(rid)))
        saved = reference_research.complete(self.root, rid, str(file))
        cfg['project']['intention'] = 'Conflit collectif'
        changed = reference_research.plan(self.root, cfg)
        self.assertNotEqual(changed[0]['id'], rid)
        self.assertTrue(saved.is_file())
        self.assertIn(saved.relative_to(self.root).as_posix(), changed[0]['reuse_results'])
        self.assertEqual(next(r['status'] for r in reference_research.requests(self.root) if r['id'] == rid), 'stale')

    def test_reference_lifecycle_decision_and_exercise(self):
        nexus.create_theme('Identité')
        rid = reference_research.plan(self.root, nexus.config())[0]['id']
        reference_research.transition(self.root, rid, 'blocked', 'Accès indisponible')
        reference_research.transition(self.root, rid, 'in_progress', 'Reprise')
        file = self.root / 'recherches/resultat.json'
        file.write_text(json.dumps(self.reference_fixture(rid)))
        frozen = reference_research.complete(self.root, rid, str(file))
        file.write_text('{}')
        self.assertIn('Auteur fictif', frozen.read_text())
        record = next(r for r in reference_research.requests(self.root) if r['id'] == rid)
        self.assertIn('focalisation', (self.root / record['exercise']).read_text())
        decisions = reference_research.decide(self.root, rid, 'Auteur fictif de test', 'defer', 'Plus tard', 'Ce projet')
        self.assertEqual(json.loads(decisions.read_text())['decision'], 'defer')
        with self.assertRaises(ValueError): reference_research.transition(self.root, rid, 'in_progress', 'Reprise')

    def test_reference_rejects_bad_evidence(self):
        nexus.create_theme('Identité')
        rid = reference_research.plan(self.root, nexus.config())[0]['id']
        file = self.root / 'recherches/resultat.json'
        for mutation in ('date', 'url', 'duplicate', 'claim', 'material'):
            result = self.reference_fixture(rid)
            author = result['authors'][0]
            if mutation == 'date': author['sources'][0]['accessed'] = '2020-02-30'
            if mutation == 'url': author['sources'][0]['url'] = 'https://'
            if mutation == 'duplicate': author['sources'].append(dict(author['sources'][0]))
            if mutation == 'claim': author['claim_sources']['technique'] = [42]
            if mutation == 'material': author['sources'][0]['material'] = 'invente'
            file.write_text(json.dumps(result))
            with self.assertRaises(ValueError): reference_research.complete(self.root, rid, str(file))


if __name__ == '__main__':
    unittest.main()
