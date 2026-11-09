import unittest
import math
from sovereign_music.core import harmony_repair_hints

class TestHarmonyHints(unittest.TestCase):
    def test_harmony_repair_hints(self):
        input_data = {
            'chords': ['G7'],
            'tracks': [{
                'name': 'Accompaniment',
                'notes': [
                    {'pitch': 60, 'start': 0},
                    {'pitch': 59, 'start': 1},
                    {'pitch': 65, 'start': 2},
                    None,
                    {'pitch': float('nan'), 'start': 3}
                ]
            }]
        }

        hints = harmony_repair_hints(input_data)
        hint = hints[0]

        # Assert invalid_accompaniment_notes has exactly one item, pitch 60, and 60 not in its allowed_midi
        self.assertEqual(len(hint['invalid_accompaniment_notes']), 1)
        hint_item = hint['invalid_accompaniment_notes'][0]
        self.assertEqual(hint_item['pitch'], 60)
        self.assertNotIn(60, hint_item['allowed_midi'])

        # Assert missing_required_pitch_classes is empty because B=11 and F=5 are present
        # (Note: G7 contains G, B, D, F. 59=B, 65=F. 11=B, 5=F)
        self.assertEqual(len(hint['missing_required_pitch_classes']), 0)

        # Assert G7 hint includes required_pitch_classes_midi_choices
        self.assertIn('required_pitch_classes_midi_choices', hint)

        # Assert harmony_repair_hints({'chords':['G7'],'tracks':None}) does not raise
        try:
            harmony_repair_hints({'chords': ['G7'], 'tracks': None})
        except Exception as e:
            self.fail(f"harmony_repair_hints raised {type(e).__name__} unexpectedly")

if __name__ == '__main__':
    unittest.main()
