import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import lifecycle
import publication


class Finding:
    def __init__(self, level, code, path, message):
        self.level, self.code, self.path, self.message = level, code, path, message


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for directory in ('config', 'data', 'manuscrit/tome-01', 'manuscrit/tome-02', 'publication', 'atelier/lecture-externe'):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        (self.root / 'config/projet.toml').write_text('''
[project]
title = "Fixture"
author = "Auteur Test"
series = "Saga Test"
status = "revision"
[manuscript]
root = "manuscrit"
active_volume = "tome-01"
manifest = "manuscrit/tome-01/manifest.txt"
output = "publication/manuscrit.md"
[publication]
page_width_cm = 14.8
page_height_cm = 21.0
''', encoding='utf-8')
        (self.root / 'data/registry_policy.yml').write_text('''
version: 1
registries:
  data/canon.yml:
    mode: active
    required_from: writing
  data/objects.yml:
    mode: dormant
    required_from: writing
''', encoding='utf-8')
        (self.root / 'data/canon.yml').write_text('canon: []\n', encoding='utf-8')
        (self.root / 'data/objects.yml').write_text('objects: []\n', encoding='utf-8')
        (self.root / 'data/lifecycle.yml').write_text('version: 1\nvolumes: {}\n', encoding='utf-8')
        self._scene('tome-01', 'SCN-001', 1, 'Première scène.')
        self._scene('tome-02', 'SCN-002', 1, 'Deuxième scène.')

    def tearDown(self):
        self.tmp.cleanup()

    def _scene(self, volume, sid, chapter, body):
        path = self.root / 'manuscrit' / volume / f'{sid}-fixture.md'
        path.write_text(f'''---
id: {sid}
title: Fixture
status: draft
chapter: {chapter}
order: 1
pov: not_applicable
location: not_applicable
date: not_applicable
change: changement
consequence: conséquence
reader_hook: question
---
{body}
''', encoding='utf-8')
        manifest = self.root / 'manuscrit' / volume / 'manifest.txt'
        manifest.write_text(path.relative_to(self.root).as_posix() + '\n', encoding='utf-8')
        return path

    def test_aggregate_all_volume_manifests(self):
        paths = lifecycle.all_manifest_paths(self.root)
        self.assertEqual([p.name for p in paths], ['SCN-001-fixture.md', 'SCN-002-fixture.md'])

    def test_active_empty_registry_warns_but_dormant_does_not(self):
        findings = lifecycle.registry_coverage_findings(self.root, Finding)
        self.assertEqual([f.path for f in findings if f.code == 'EMPTY_ACTIVE_REGISTRY'], ['data/canon.yml'])

    def test_freeze_detects_later_manuscript_change_and_unfreeze_is_traced(self):
        with patch('lifecycle.saga_findings', return_value=[]):
            lifecycle.freeze_volume(self.root, 'tome-01', 'validation')
        before = lifecycle.release_status(self.root, 'tome-01')
        self.assertFalse(before['manuscript_changed_since_freeze'])
        scene = self.root / 'manuscrit/tome-01/SCN-001-fixture.md'
        scene.write_text(scene.read_text(encoding='utf-8') + '\nModification.\n', encoding='utf-8')
        after = lifecycle.release_status(self.root, 'tome-01')
        self.assertTrue(after['manuscript_changed_since_freeze'])
        lifecycle.unfreeze_volume(self.root, 'tome-01', 'correction nécessaire')
        state = yaml.safe_load((self.root / 'data/lifecycle.yml').read_text(encoding='utf-8'))
        self.assertEqual(state['volumes']['tome-01']['state'], 'revision')
        self.assertEqual(state['volumes']['tome-01']['history'][-1]['action'], 'unfreeze')

    def test_simulated_reader_campaign_cannot_claim_human_validation(self):
        target = lifecycle.new_reader_campaign(self.root, 'Stress test', 'tome-01', 'simulation')
        data = yaml.safe_load(target.read_text(encoding='utf-8'))
        self.assertFalse(data['may_claim_human_validation'])
        self.assertEqual(data['provenance'], 'simulated_reader_profiles')

    def test_publication_manifest_records_source_digest_and_artifact_hash(self):
        directory = self.root / 'publication/tome-01'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'fixture.txt').write_text('livrable', encoding='utf-8')
        target = lifecycle.publication_manifest(self.root, 'tome-01')
        text = target.read_text(encoding='utf-8')
        self.assertIn('Empreinte source', text)
        self.assertIn('fixture.txt', text)
        self.assertIn('SHA-256', text)

    def test_docx_contains_author_metadata(self):
        target = publication.build_docx(self.root, 'tome-01')
        from docx import Document
        doc = Document(target)
        self.assertEqual(doc.core_properties.author, 'Auteur Test')
        self.assertEqual(doc.core_properties.title, 'Fixture')


if __name__ == '__main__':
    unittest.main()
