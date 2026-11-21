# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""deepchord lead: a sung melody over a given form, checked phrase by phrase."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from sovereign_music import cli, core, lead  # noqa: E402

A = {'id': 'v1.a', 'start_bar': 5, 'chords': ['Am', 'F:2,G:2'], 'syllables': ['la', 'la', 'la', 'la']}
B = {'id': 'v1.b', 'start_bar': 7, 'chords': ['C'], 'syllables': ['oh', 'oh']}


def request(sections=None):
    return {'schema': lead.REQUEST_SCHEMA, 'title': 'T', 'tempo': 96, 'key': 'Am', 'style': 'ballad',
            'sections': sections or [{'name': 'Verse', 'centre': 67, 'phrases': [A, B]}]}


GOOD_A = [{'s': 0, 'd': 1, 'p': 69}, {'s': 1.5, 'd': .5, 'p': 67}, {'s': 2, 'd': 2, 'p': 64}, {'s': 4, 'd': 3, 'p': 65}]
GOOD_B = [{'s': 0, 'd': 1.5, 'p': 67}, {'s': 2, 'd': 1.5, 'p': 64}]


def reply(**phrases):
    return {'done_reason': 'stop', 'message': {'content': json.dumps({'phrases': [{'id': k.replace('_', '.'), 'notes': v} for k, v in phrases.items()]})}}


class Model:
    def __init__(self, *replies): self.replies = list(replies); self.payloads = []
    def __call__(self, payload, timeout=0):
        self.payloads.append(payload); return self.replies.pop(0)


def run(model, req=None, **kw):
    with tempfile.TemporaryDirectory() as d, patch.object(core, 'retrieve', return_value='evidence'), patch('builtins.print'):
        path = Path(d)/'request.json'; path.write_text(json.dumps(req or request()))
        out = lead.run_lead(path, Path(d)/'out', 'm', chat=model, **kw)
        return json.loads((out/'lead.json').read_text()), (out/'lead.mid').read_bytes(), json.loads((out/'validation.json').read_text())


class Rules(unittest.TestCase):
    def test_keys_and_chords(self):
        self.assertEqual(lead.key_scale('Am'), [9, 11, 0, 2, 4, 5, 7])
        self.assertEqual(lead.key_scale('D', 1)[0], 3)
        self.assertEqual(lead.chord_pcs('C/E'), [0, 4, 7])
        self.assertEqual(lead.chord_pcs('Amadd9'), [0, 4, 9, 11])
        spans = lead.chord_spans(['Am', 'F:2,G:2'])
        self.assertEqual([(a, b, n) for a, b, n, _ in spans], [(0, 4, 'Am'), (4, 6, 'F'), (6, 8, 'G')])
        with self.assertRaises(ValueError): lead.chord_spans(['F:2,G:1'])

    def problems(self, notes, phrase=A):
        return lead.phrase_problems(phrase, notes, lead.key_scale('Am'), (58, 77))

    def test_each_check_reports(self):
        ok = [(0, 1, 69), (1.5, .5, 67), (2, 2, 64), (4, 3, 65)]
        self.assertEqual(self.problems(ok), [])
        self.assertIn('exactly 4 notes', self.problems(ok[:3])[0])
        self.assertTrue(any('strong beat' in p for p in self.problems([(0, 1, 71), *ok[1:]])))
        self.assertTrue(any('outside the key' in p for p in self.problems([ok[0], (1.5, .5, 68), *ok[2:]])))
        self.assertTrue(any('outside 58..77' in p for p in self.problems([(0, 1, 81), *ok[1:]])))
        self.assertTrue(any('leap' in p for p in self.problems([(0, 1, 76), (1.5, .5, 62), *ok[2:]])))
        self.assertTrue(any('inside beats' in p for p in self.problems([*ok[:3], (7.5, 1, 67)])))
        self.assertTrue(any('one pitch only' in p for p in self.problems([(0, 1, 69), (1, 1, 69), (2, 1, 69), (4, 1, 69)])))

    def test_normalize_snaps_orders_and_trims(self):
        notes, repairs = lead.normalize(A, [{'s': 2.02, 'd': 9, 'p': 64}, {'s': 0, 'd': 3, 'p': 69}, {'s': 'x'}, {'s': 1, 'd': 1, 'p': True}])
        self.assertEqual(notes, [(0, 2.0, 69), (2.0, 6.0, 64)])
        self.assertEqual(repairs, ['snapped a start to the grid', 'trimmed an overlapping duration'])

    def test_request_errors(self):
        for change in ({'schema': 'x'}, {'key': 'H'}, {'tempo': 500}, {'sections': []}):
            with self.assertRaises(ValueError): lead.check_request({**request(), **change})
        with self.assertRaises(ValueError): lead.check_request(request([{'phrases': [A, A]}]))
        with self.assertRaises(ValueError): lead.check_request(request([{'phrases': [{**A, 'syllables': []}]}]))


class Compose(unittest.TestCase):
    def test_valid_answer_becomes_absolute_notes_and_midi(self):
        model = Model(reply(v1_a=GOOD_A, v1_b=GOOD_B))
        result, midi, validation = run(model)
        self.assertEqual(result['status'], {'valid': 2, 'repaired': 0, 'failed': 0})
        self.assertTrue(validation['valid'])
        first = result['phrases'][0]['notes'][0]
        self.assertEqual((first['start'], first['pitch'], first['velocity']), (16, 69, 100))
        self.assertEqual(result['phrases'][1]['notes'][0]['start'], 24)
        self.assertEqual(result['counts']['notes'], 6)
        self.assertEqual(midi[:4], b'MThd')
        brief = json.loads(model.payloads[0]['messages'][1]['content'].split('Section: ', 1)[1])
        self.assertEqual(brief['phrases'][0]['notes_required'], 4)
        self.assertEqual(brief['phrases'][0]['chords'][1]['chord'], 'F')

    def test_retry_asks_only_for_failed_phrases_with_reasons(self):
        bad = [{**GOOD_A[0], 'p': 71}, *GOOD_A[1:]]
        model = Model(reply(v1_a=bad, v1_b=GOOD_B), reply(v1_a=GOOD_A))
        result, _, _ = run(model)
        self.assertEqual(result['status']['valid'], 2)
        self.assertEqual([p['attempts'] for p in result['phrases']], [2, 1])
        hint = model.payloads[1]['messages'][-1]['content']
        self.assertIn('strong beat', hint); self.assertIn('v1.a', hint); self.assertNotIn('"id": "v1.b"', hint)

    def test_wrong_pitches_are_moved_only_after_the_last_attempt_and_reported(self):
        bad = [{**GOOD_A[0], 'p': 71}, *GOOD_A[1:]]
        result, _, _ = run(Model(*[reply(v1_a=bad, v1_b=GOOD_B)]*3))
        row = result['phrases'][0]
        self.assertEqual(row['status'], 'repaired')
        self.assertEqual(row['notes'][0]['pitch'], 72)
        self.assertIn('moved 1 pitches', row['repairs'][-1])

    def test_rhythm_that_runs_past_the_phrase_is_squeezed_only_after_the_last_attempt(self):
        late = [{'s': 0, 'd': .75, 'p': 67}, {'s': 4.5, 'd': .75, 'p': 64}]   # phrase B is one bar: the second note starts in the next bar
        result, _, _ = run(Model(*[reply(v1_a=GOOD_A, v1_b=late)]*3))
        row = result['phrases'][1]
        self.assertEqual(row['status'], 'repaired')
        self.assertEqual(row['relative'], [[0, 0.5, 67], [3.75, 0.25, 64]])  # durations shrink by the same factor
        self.assertEqual(row['repairs'], ['squeezed the rhythm to fit the phrase'])
        self.assertEqual(row['attempts'], 3)

    def test_fit_timing_keeps_order_and_spacing(self):
        one_bar = {**B, 'syllables': ['a']*7}
        notes = [(0.0, .75, 69), (.75, .75, 67), (1.5, .75, 67), (2.25, 1.0, 66), (3.25, .75, 64), (4.0, .75, 62), (4.75, .25, 64)]
        fitted, changed = lead.fit_timing(one_bar, notes)
        self.assertTrue(changed)
        starts = [n[0] for n in fitted]
        self.assertEqual(starts, sorted(set(starts))); self.assertLessEqual(fitted[-1][0]+fitted[-1][1], 4)
        self.assertTrue(all(b[0] >= a[0]+a[1]-1e-9 for a, b in zip(fitted, fitted[1:])), 'no overlaps')
        self.assertEqual([n[2] for n in fitted], [n[2] for n in notes])
        self.assertEqual(lead.fit_timing(one_bar, notes[:5]), (notes[:5], False), 'notes that fit are not touched')
        crowded = [(i*.25, .25, 60) for i in range(17)]
        self.assertFalse(lead.fit_timing(one_bar, crowded)[1], 'more notes than sixteenth slots cannot be fitted')

    def test_wrong_note_count_fails_that_phrase_and_keeps_the_rest(self):
        result, _, validation = run(Model(*[reply(v1_a=GOOD_A[:3], v1_b=GOOD_B)]*3))
        self.assertEqual(result['status'], {'valid': 1, 'repaired': 0, 'failed': 1})
        self.assertFalse(validation['valid'])
        self.assertEqual(result['phrases'][0]['notes'], [])
        self.assertIn('exactly 4 notes', result['phrases'][0]['problems'][0])

    def test_truncated_or_broken_answers_do_not_crash(self):
        cut = {'done_reason': 'length', 'message': {'content': '{"phr'}}
        result, _, _ = run(Model(cut, {'message': {'content': 'not json'}}, reply(v1_a=GOOD_A, v1_b=GOOD_B)))
        self.assertEqual(result['status']['valid'], 2)

    def test_nothing_usable_is_an_error(self):
        with self.assertRaises(ValueError): run(Model(*[reply()]*3))

    def test_identical_later_section_reuses_the_melody_without_a_model_call(self):
        again = [{**A, 'id': 'v2.a', 'start_bar': 21}, {**B, 'id': 'v2.b', 'start_bar': 23}]
        req = request([{'name': 'Verse', 'centre': 67, 'phrases': [A, B]}, {'name': 'Verse again', 'centre': 67, 'phrases': again}])
        model = Model(reply(v1_a=GOOD_A, v1_b=GOOD_B))
        result, _, _ = run(model, req)
        self.assertEqual(len(model.payloads), 1)
        self.assertEqual(result['phrases'][2]['reused_from'], 'v1.a')
        self.assertEqual(result['phrases'][2]['relative'], result['phrases'][0]['relative'])
        self.assertEqual(result['phrases'][2]['notes'][0]['start'], 80)

    def test_long_form_has_no_bar_limit(self):
        sections = [{'name': f'S{i}', 'centre': 67, 'phrases': [{**A, 'id': f's{i}', 'start_bar': 1+i*2, 'chords': A['chords']}]} for i in range(60)]
        result, _, _ = run(Model(reply(s0=GOOD_A)), request(sections))
        self.assertEqual(result['counts']['phrases'], 60)
        self.assertEqual(result['phrases'][-1]['notes'][0]['start'], 118*4)

    def test_revision_sends_previous_melody_and_the_note(self):
        with tempfile.TemporaryDirectory() as d, patch.object(core, 'retrieve', return_value='e'), patch('builtins.print'):
            path = Path(d)/'r.json'; path.write_text(json.dumps(request()))
            first = lead.run_lead(path, Path(d)/'one', 'm', chat=Model(reply(v1_a=GOOD_A, v1_b=GOOD_B)))
            model = Model(reply(v1_a=GOOD_A, v1_b=GOOD_B))
            lead.run_lead(path, Path(d)/'two', 'm', previous_run=first, note='higher ending', chat=model)
            with self.assertRaises(ValueError): lead.run_lead(path, Path(d)/'two', 'm', chat=model)
        user = model.payloads[0]['messages'][1]['content']
        self.assertIn('previous_version_of_this_section', user); self.assertIn('higher ending', user)

    def test_cli(self):
        a = cli.parser().parse_args(['lead', 'r.json', '--out', 'o', '--previous-run', 'p', '--note', 'n'])
        self.assertEqual((a.cmd, str(a.out), a.note), ('lead', 'o', 'n'))


NAMES = ['Verse1', 'Pre1', 'Chorus', 'Verse2', 'Pre2', 'Chorus', 'Bridge', 'FinalChorus', 'Outro']


class Scope(unittest.TestCase):
    def scope(self, note, sections=None):
        return sorted(lead.revision_scope(NAMES, note, sections)[0])

    def test_sections_named_in_the_note(self):
        self.assertEqual(self.scope('make the chorus climb higher'), [2, 5, 7])
        self.assertEqual(self.scope('후렴 끝을 더 높이 올려줘'), [2, 5, 7])
        self.assertEqual(self.scope('2절 멜로디를 더 낮게'), [3])
        self.assertEqual(self.scope('verse 1 needs more rests'), [0])
        self.assertEqual(self.scope('the verse is too busy'), [0, 3])
        self.assertEqual(self.scope('pre-chorus should build more'), [1, 4])
        self.assertEqual(self.scope('Bridge and outro: longer notes'), [6, 8])
        self.assertEqual(self.scope('FinalChorus only: add a high note'), [7])
        self.assertEqual(lead.revision_scope(NAMES, 'make the chorus climb')[1], 'sections named in the note')

    def test_note_without_a_section_means_the_whole_song(self):
        indexes, how = lead.revision_scope(NAMES, '전체적으로 더 부드럽게, 계절 느낌')
        self.assertEqual(sorted(indexes), list(range(9))); self.assertIn('whole song', how)

    def test_explicit_choice_wins_and_unknown_names_are_errors(self):
        self.assertEqual(self.scope('make the chorus climb', ['Bridge']), [6])
        self.assertEqual(self.scope('softer [sections: verse2, outro]'), [3, 8])
        self.assertEqual(self.scope('chorus', ['all']), list(range(9)))
        with self.assertRaises(ValueError) as caught: self.scope('x', ['Solo'])
        self.assertIn('Verse1', str(caught.exception))


class TargetedRevision(unittest.TestCase):
    def setUp(self):
        chorus = [{**A, 'id': 'c.a', 'start_bar': 9, 'chords': ['F', 'G']}, {**B, 'id': 'c.b', 'start_bar': 11}]
        self.req = request([{'name': 'Verse1', 'centre': 67, 'phrases': [A, B]}, {'name': 'Chorus', 'centre': 67, 'phrases': chorus}])
        self.CH_A = [{'s': 0, 'd': 1, 'p': 65}, {'s': 1.5, 'd': .5, 'p': 67}, {'s': 2, 'd': 2, 'p': 69}, {'s': 4, 'd': 3, 'p': 67}]
        self.CH_A2 = [{'s': 0, 'd': 1, 'p': 69}, {'s': 1.5, 'd': .5, 'p': 71}, {'s': 2, 'd': 2, 'p': 72}, {'s': 4, 'd': 4, 'p': 74}]

    def revise(self, note, model, **kw):
        with tempfile.TemporaryDirectory() as d, patch.object(core, 'retrieve', return_value='e'), patch('builtins.print') as printed:
            path = Path(d)/'r.json'; path.write_text(json.dumps(self.req))
            first = lead.run_lead(path, Path(d)/'one', 'm', chat=Model(reply(v1_a=GOOD_A, v1_b=GOOD_B), reply(c_a=self.CH_A, c_b=GOOD_B)))
            out = lead.run_lead(path, Path(d)/'two', 'm', previous_run=first, note=note, chat=model, **kw)
            return json.loads((first/'lead.json').read_text()), json.loads((out/'lead.json').read_text()), ' '.join(str(c.args[0]) for c in printed.call_args_list if c.args)

    def test_only_the_named_section_is_composed_again(self):
        model = Model(reply(c_a=self.CH_A2, c_b=GOOD_B))
        one, two, printed = self.revise('후렴을 더 높이', model)
        self.assertEqual(len(model.payloads), 1, 'the verse must not cost a model call')
        self.assertIn('"section": "Chorus"', model.payloads[0]['messages'][1]['content'])
        self.assertEqual([p['notes'] for p in two['phrases'][:2]], [p['notes'] for p in one['phrases'][:2]], 'verse notes are identical')
        self.assertTrue(all(p.get('kept_from_previous') for p in two['phrases'][:2]))
        self.assertEqual(two['phrases'][2]['relative'][-1], [4, 4, 74])
        self.assertEqual(two['revision_scope'], {'chosen_by': 'sections named in the note', 'composed': ['Chorus'], 'kept_from_previous': ['Verse1'], 'not_applied_phrases': []})
        self.assertIn('composed Chorus; kept Verse1', printed)
        self.assertEqual(two['counts']['notes'], one['counts']['notes'])

    def test_sections_option_and_whole_song_note(self):
        model = Model(reply(v1_a=GOOD_A, v1_b=GOOD_B))
        _, two, _ = self.revise('more rests', model, sections=['verse1'])
        self.assertEqual(two['revision_scope']['composed'], ['Verse1'])
        model = Model(reply(v1_a=GOOD_A, v1_b=GOOD_B), reply(c_a=self.CH_A2, c_b=GOOD_B))
        _, two, _ = self.revise('softer overall', model)
        self.assertEqual((len(model.payloads), two['revision_scope']['kept_from_previous']), (2, []))

    def test_a_section_whose_shape_changed_is_composed_even_when_not_named(self):
        self.req['sections'][0]['phrases'][1] = {**B, 'syllables': ['oh', 'oh', 'oh']}
        longer = [*GOOD_B[:1], {'s': 1, 'd': 1, 'p': 65}, GOOD_B[1]]
        with tempfile.TemporaryDirectory() as d, patch.object(core, 'retrieve', return_value='e'), patch('builtins.print'):
            old = request([{'name': 'Verse1', 'centre': 67, 'phrases': [A, B]}, self.req['sections'][1]])
            (Path(d)/'old.json').write_text(json.dumps(old)); (Path(d)/'new.json').write_text(json.dumps(self.req))
            first = lead.run_lead(Path(d)/'old.json', Path(d)/'one', 'm', chat=Model(reply(v1_a=GOOD_A, v1_b=GOOD_B), reply(c_a=self.CH_A, c_b=GOOD_B)))
            model = Model(reply(v1_a=GOOD_A, v1_b=longer), reply(c_a=self.CH_A2, c_b=GOOD_B))
            out = lead.run_lead(Path(d)/'new.json', Path(d)/'two', 'm', previous_run=first, note='chorus higher', chat=model)
            two = json.loads((out/'lead.json').read_text())
        self.assertEqual(two['revision_scope']['composed'], ['Verse1', 'Chorus'])
        self.assertEqual(len(two['phrases'][1]['notes']), 3)

    def test_a_failed_revision_keeps_the_previous_melody_and_reports_it(self):
        cut = {'done_reason': 'length', 'message': {'content': ''}}
        model = Model(cut, cut, reply(c_a=self.CH_A2[:3], c_b=GOOD_B))
        one, two, printed = self.revise('후렴을 더 높이', model)
        self.assertEqual(two['status'], {'valid': 4, 'repaired': 0, 'failed': 0})
        self.assertEqual(two['phrases'][2]['notes'], one['phrases'][2]['notes'], 'c.a keeps the previous melody')
        self.assertIn('exactly 4 notes', two['phrases'][2]['revision_not_applied'][0])
        self.assertNotIn('revision_not_applied', two['phrases'][3])
        self.assertEqual(two['revision_scope']['not_applied_phrases'], ['c.a'])
        self.assertIn('NOT applied to 1 phrases', printed)
        self.assertEqual(len(model.payloads[1]['messages']), 2, 'a truncated answer is asked again without growing the conversation')

    def test_truncation_lowers_the_reasoning_level_for_the_next_attempt(self):
        cut = {'done_reason': 'length', 'message': {'content': '', 'thinking': 'x'}}
        good = reply(v1_a=GOOD_A, v1_b=GOOD_B)
        req = request()
        with tempfile.TemporaryDirectory() as d, patch.object(core, 'retrieve', return_value='e'), patch('builtins.print'), \
                patch.object(core, 'local_model'), patch.object(core, 'api', side_effect=[cut, good]) as api:
            path = Path(d)/'r.json'; path.write_text(json.dumps(req))
            lead.run_lead(path, Path(d)/'out', 'gpt-oss:20b')
        self.assertEqual([c.args[1]['think'] for c in api.call_args_list], ['medium', 'low'])

    def test_sections_without_previous_run_is_refused(self):
        with tempfile.TemporaryDirectory() as d, patch.object(core, 'retrieve', return_value='e'):
            path = Path(d)/'r.json'; path.write_text(json.dumps(self.req))
            with self.assertRaises(ValueError): lead.run_lead(path, Path(d)/'x', 'm', chat=Model(), sections=['Chorus'])

    def test_cli_sections(self):
        a = cli.parser().parse_args(['lead', 'r.json', '--out', 'o', '--previous-run', 'p', '--sections', 'Chorus,Bridge'])
        self.assertEqual(a.sections, 'Chorus,Bridge')


if __name__ == '__main__':
    unittest.main()
