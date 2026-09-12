"""Tests V4 sur fixtures fictives : aucun projet réel n'est utilisé comme scénario de test."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import nexus
import editorial


class V4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.original = nexus.ROOT
        (self.root / 'config').mkdir()
        (self.root / 'data').mkdir()
        (self.root / 'manuscrit/tome-01').mkdir(parents=True)
        (self.root / 'reports').mkdir()
        (self.root / 'atelier/editorial').mkdir(parents=True)
        (self.root / 'templates').mkdir()
        (self.root / 'config/projet.toml').write_text('''
[project]
title = "Fixture V4"
author_mode = "expert"
status = "writing"
[manuscript]
root = "manuscrit"
active_volume = "tome-01"
manifest = "manuscrit/tome-01/manifest.txt"
output = "publication/manuscrit.md"
[quality]
minimum_scene_words = 1
maximum_scene_words = 5000
max_author_priorities = 5
[author]
checkpoint = "data/checkpoint.json"
cockpit = "COCKPIT_AUTEUR.md"
auto_add_new_scene_to_manifest = true
''', encoding='utf-8')
        (self.root / 'manuscrit/tome-01/manifest.txt').write_text('', encoding='utf-8')
        (self.root / 'data/characters.yml').write_text('characters:\n  - id: CHR-001\n    name: Personnage fixture\n', encoding='utf-8')
        (self.root / 'data/mysteries.yml').write_text('mysteries:\n  - id: MYS-001\n    question: Question fixture ?\n    status: open\n', encoding='utf-8')
        (self.root / 'data/narrative_debt.yml').write_text('debts:\n  - id: DEBT-001\n    description: Dette fixture\n    severity: high\n    created_by: SCN-001\n    resolve_before: fin-tome\n    status: open\n', encoding='utf-8')
        (self.root / 'data/experience_model.yml').write_text('''version: 4
thresholds:
  max_active_mysteries: 1
  max_new_concepts: 1
  max_new_names: 1
  max_new_rules: 1
  max_major_revelations: 1
  max_load_score: 3
''', encoding='utf-8')
        (self.root / 'data/saga_control.yml').write_text('''saga:
  title: Fixture Saga
  current_volume: tome-01
  volumes:
    - id: tome-01
      title: Fixture
      status: planning
      promise: Test
      central_question: Question
      hero_transformation: Transformation
      final_cost: Coût
      irreversible_answers: []
      inherited_debts: [DEBT-001]
      protected_truths: []
''', encoding='utf-8')
        nexus.ROOT = self.root

    def tearDown(self):
        nexus.ROOT = self.original
        self.tmp.cleanup()

    def write_scene(self, with_v4=True, overload=False, assimilated=True):
        extra = ''
        if with_v4:
            active = '[MYS-001, MYS-002]' if overload else '[MYS-001]'
            concepts = '[concept-a, concept-b]' if overload else '[concept-a]'
            cost = 'Un choix coûteux' if assimilated else 'unknown'
            extra = f'''reader_state:
  dominant_question: "Que veut-il ?"
  knows_before: []
  believes_before: []
  suspects_before: []
  expects_before: []
  emotion_before: inquiétude
  knows_after: []
  believes_after: []
  dominant_question_after: "Pourquoi ?"
  emotion_after: tension
  human_anchor: CHR-001
cognitive_load:
  new_concepts: {concepts}
  active_mysteries: {active}
  new_names: []
  new_rules: []
  major_revelations: [revelation-a]
  deferred_questions: []
  dominant_focus: MYS-001
emotional_continuity:
  pov_entry: prudent
  pov_exit: inquiet
  relationship_shift: unknown
  embodied_cost: {cost}
mystery_state:
  active: [MYS-001]
  deferred: []
  dormant: []
  resolved: []
narrative_debt:
  opened: []
  progressed: [DEBT-001]
  paid: []
'''
        path = self.root / 'manuscrit/tome-01/SCN-001-fixture.md'
        path.write_text(f'''---
id: SCN-001
title: Fixture
status: draft
chapter: 1
order: 1
pov: CHR-001
location: not_applicable
date: not_applicable
characters: [CHR-001]
change: Une décision est prise.
consequence: Une conséquence demeure.
reader_hook: Pourquoi ?
{extra}---
Texte fixture.
''', encoding='utf-8')
        (self.root / 'manuscrit/tome-01/manifest.txt').write_text('manuscrit/tome-01/SCN-001-fixture.md\n', encoding='utf-8')
        return path

    def codes(self):
        return {item.code for item in nexus.audit()}

    def tool(self, name):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertTrue(editorial.dispatch([name], self.root))
        return self.root / out.getvalue().strip().splitlines()[-1]

    def test_legacy_scene_without_v4_is_accepted(self):
        self.write_scene(with_v4=False)
        self.assertFalse({code for code in self.codes() if code.startswith('V4_')})

    def test_cognitive_overload_and_unassimilated_revelation_are_signalled(self):
        self.write_scene(overload=True, assimilated=False)
        codes = self.codes()
        self.assertIn('V4_COGNITIVE_OVERLOAD', codes)
        self.assertIn('V4_LOAD_SCORE', codes)
        self.assertIn('V4_REVELATION_UNASSIMILATED', codes)

    def test_v4_reports_are_generated(self):
        self.write_scene()
        self.assertIn('SCN-001', self.tool('reader-map').read_text(encoding='utf-8'))
        self.assertIn('Charge', self.tool('experience-map').read_text(encoding='utf-8'))
        self.assertIn('MYS-001', self.tool('mystery-graph').read_text(encoding='utf-8'))
        self.assertIn('DEBT-001', self.tool('debt-ledger').read_text(encoding='utf-8'))
        self.assertIn('Fixture Saga', self.tool('saga-control').read_text(encoding='utf-8'))

    def test_beta_synthesis_requires_two_distinct_readers_for_convergence(self):
        base = {'scene': 'SCN-001', 'reaction': 'confusion', 'subject': 'Zone fixture'}
        for index, reader in enumerate(('A', 'B'), 1):
            item = dict(base, reader=reader)
            (self.root / f'atelier/editorial/beta-feedback-{index}.json').write_text(json.dumps(item), encoding='utf-8')
        text = self.tool('beta-synthesis').read_text(encoding='utf-8')
        self.assertIn('convergence à examiner', text)


if __name__ == '__main__':
    unittest.main()
