import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
import sovereign_music.song_generator as sg

class TestSongGenerator(unittest.TestCase):
    def setUp(self):
            self.PLAN = {
                'title': 'Example',
                'tempo': 100,
                'bars': 24,
                'key': 'C',
                'motif': 'up',
                'sections': [{'name': 'Intro', 'start_bar': 1, 'progression': ['C']}],
                'tracks': [{'name': 'Lead', 'role': 'melody', 'channel': 0, 'program': 0, 'pedal_allowed': False}]
            }

    def test_cache_and_composition(self):
        with TemporaryDirectory() as tmp_dir:
            directory = Path(tmp_dir)
            calls = []
            def fake(*args):
                calls.append(args[2]['start_bar'])
                return {'notes': [{'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80}], 'summary': 'same'}

            callback = sg.make_block_cache(directory, fake)

            song = sg.compose_arrangement('m', 'p', self.PLAN, block_fn=callback)
            sg.compose_arrangement('m', 'p', self.PLAN, block_fn=callback)

            assert calls == [1, 5, 9, 13, 17, 21]
            assert len(list(directory.glob('*.json'))) == 6
            assert [n['start'] for n in song['tracks'][0]['notes']] == [0, 16, 32, 48, 64, 80]

    def test_repair(self):
        notes = [
            {'pitch': 60, 'start': 0, 'duration': 2, 'velocity': 80},
            {'pitch': 60, 'start': 1, 'duration': 1, 'velocity': 70}
        ]

        corrected, changes = sg.repair_same_pitch_overlaps(notes)

        self.assertEqual(corrected[0]['duration'], 1)
        self.assertEqual(notes[0]['duration'], 2)
        self.assertEqual(changes[0]['old_duration'], 2)
        self.assertEqual(changes[0]['new_duration'], 1)

        for i in range(len(corrected)):
            self.assertEqual(corrected[i]['pitch'], notes[i]['pitch'])
            self.assertEqual(corrected[i]['start'], notes[i]['start'])
            self.assertEqual(corrected[i]['velocity'], notes[i]['velocity'])

        notes = [
            {'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80},
            {'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80}
        ]
        with self.assertRaises(ValueError):
            sg.repair_same_pitch_overlaps(notes)

    def test_harmony_review(self):
        original = {'notes': [{'pitch': 61, 'start': 0, 'duration': 1, 'velocity': 80}, {'pitch': 61, 'start': 4, 'duration': 1, 'velocity': 70}], 'summary': 'x'}
        track = {'name': 'Bass', 'role': 'bass', 'channel': 0, 'program': 32}
        progression = ['C', 'C']
        candidate = {'notes': [{'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80}, {'pitch': 60, 'start': 4, 'duration': 1, 'velocity': 70}]}

        with patch.object(sg, 'call_notes', return_value=('', candidate)):
            result = sg.review_block_harmony('m', original, track, progression)
            self.assertEqual(result['harmony_review']['status'], 'revised')
            self.assertEqual(len(result['harmony_review']['warnings']), 0)
            self.assertEqual(original['notes'][0]['pitch'], 61)
            self.assertEqual(result['notes'][0]['pitch'], 60)

        with patch.object(sg, 'call_notes', return_value=('', {'notes': []})):
            result = sg.review_block_harmony('m', original, track, progression)
            self.assertEqual(result['harmony_review']['status'], 'review_failed')
            self.assertEqual(original['notes'][0]['pitch'], 61)
