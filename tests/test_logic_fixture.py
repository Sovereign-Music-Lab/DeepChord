# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from scripts.check_logic_fixture import check, check_snapshot, create, fixture, position


def snapshot(name, start_bar=1):
    channel = 1 if name == 'Untouched' else 2
    track = fixture()['tracks'][channel-1]
    def bbt(ticks, duration=False):
        bar, rem = divmod(ticks, 3840); beat, rem = divmod(rem, 960); sub, tick = divmod(rem, 240)
        base = 0 if duration else 1
        return ' '.join(str(n+base) for n in (bar, beat, sub, tick))
    def row(at, kind, number, value):
        return {'Position': {'value_description': bbt(at+(start_bar-1)*3840)},
                'Status': {'value_description': kind}, 'Ch': {'slider_value': channel},
                'Num': {'slider_value': number}, 'Val': {'value_description': str(value)}}
    rows = [row(0, 'Program', -1, 0)]
    for note in track['notes']:
        r = row(round(note['start']*960), 'Note', note['pitch'], note['velocity'])
        r['Length/Info'] = {'value_description': bbt(round(note['duration']*960), True)}
        rows.append(r)
    for bar in range(8):
        rows.extend([row(bar*3840, 'Control', 64, 0), row(bar*3840+60, 'Control', 64, 90),
                     row((bar+1)*3840-50, 'Control', 64, 0)])
    rows.append(row(8*3840, 'Control', 64, 0))
    return {'raw_rows': rows, 'selected_region_observation': {
        'name': name, 'kind': 'midi', 'track_index': channel-1, 'start_bar': start_bar, 'end_bar': start_bar+8},
        'event_list_region_path': name, 'row_selection_restored': True,
        'observed_rows_content_stable': True, 'event_list_item_count_text': f'{len(rows)} Events',
        'event_list_filter_states': dict.fromkeys(('noteEvents', 'controller', 'programChange',
                                                  'pitchBend', 'aftertouch', 'polyAftertouch', 'systemExclusive'), True)}


class LogicFixtureTests(unittest.TestCase):
    def test_all_known_notes_pedals_and_programs_at_both_positions(self):
        for name, notes in [('Target', 96), ('Untouched', 8)]:
            for bar in (1, 3):
                self.assertEqual(check_snapshot(snapshot(name, bar), name, start_bar=bar),
                                 {'notes': notes, 'pedals': 25, 'programs': 1})
        changed = snapshot('Target')
        changed['raw_rows'][1]['Num']['slider_value'] += 1
        check_snapshot(changed, 'Target', first_note_semitones=1)
        with self.assertRaises(ValueError): check_snapshot(changed, 'Target')

    def test_truncated_tail_missing_release_and_hidden_controller_refuse(self):
        before = snapshot('Target')
        bad = deepcopy(before); bad['raw_rows'].pop(); bad['event_list_item_count_text'] = '121 Events'
        hidden = deepcopy(before); hidden['event_list_filter_states']['controller'] = False
        stale = deepcopy(before); stale['observed_rows_content_stable'] = False
        for data in (bad, hidden, stale):
            with self.assertRaises(ValueError): check_snapshot(data, 'Target')

    def test_single_field_corruption_and_pedal_left_behind_refuse(self):
        for field, key, value in [('Num', 'slider_value', 61), ('Ch', 'slider_value', 1),
                                  ('Val', 'value_description', '99'), ('Length/Info', 'value_description', '0 0 2 0')]:
            data = snapshot('Target', 3); data['raw_rows'][1][field][key] = value
            with self.assertRaises(ValueError): check_snapshot(data, 'Target', start_bar=3)
        data = snapshot('Target', 3); data['raw_rows'][-1]['Position']['value_description'] = '9 1 1 1'
        with self.assertRaises(ValueError): check_snapshot(data, 'Target', start_bar=3)

    def test_fixture_creation_never_overwrites_and_duration_is_not_position(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'fixture'; create(target)
            midi = (target/'composition.mid').read_bytes()
            self.assertTrue(midi.startswith(b'MThd'))
            with self.assertRaises(FileExistsError): create(target)
            self.assertEqual((target/'composition.mid').read_bytes(), midi)
        self.assertEqual(position('1 1 1 1'), 0)
        self.assertEqual(position('0 0 1 0', duration=True), 240)

    def test_saved_check_reads_reopened_events_and_rejects_a_false_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'Original.logicx'; source.mkdir()
            (source/'ProjectData').write_bytes(b'fixture source')
            def write(name, value): (root/name).write_text(json.dumps(value))
            write('report.json', {'status': 'passed', 'saved_events_verified': True, 'source': str(source)})
            write('source-manifest.json', {'ProjectData': hashlib.sha256(b'fixture source').hexdigest()})
            for suffix, bar in [('before', 1), ('after', 3), ('reopened', 3)]:
                write(suffix+'.json', snapshot('Target', bar))
                write('other-0-'+suffix+'.json', snapshot('Untouched'))
            self.assertEqual(check(root)['scope'], 'saved_fixture_events')
            stale = snapshot('Target', 3); stale['raw_rows'][-1]['Val']['value_description'] = '90'
            write('reopened.json', stale)
            with self.assertRaisesRegex(ValueError, 'pedal'): check(root)
            write('reopened.json', snapshot('Target', 3))
            (source/'ProjectData').write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError, 'Original'): check(root)


if __name__ == '__main__':
    unittest.main()
