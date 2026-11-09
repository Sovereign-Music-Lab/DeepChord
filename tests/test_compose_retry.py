import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
import json
import tempfile
from copy import deepcopy
from sovereign_music import core

class TestCompose(unittest.TestCase):
    def test_compose_retries_then_succeeds(self):
        valid = {
            'title': 'Test',
            'tempo': 80,
            'bars': 1,
            'chords': ['Cmaj7'],
            'tracks': [
                {
                    'name': 'Melody',
                    'notes': [{'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80}]
                },
                {
                    'name': 'Accompaniment',
                    'notes': [
                        {'pitch': 52, 'start': 0, 'duration': 1, 'velocity': 70},
                        {'pitch': 59, 'start': 0, 'duration': 1, 'velocity': 70}
                    ]
                }
            ]
        }

        a = deepcopy(valid)
        a['tracks'][0]['notes'][0]['start'] = 3
        a['tracks'][0]['notes'][0]['duration'] = 2

        b = deepcopy(valid)
        b['tracks'][1]['notes'] = [{'pitch': 61, 'start': 0, 'duration': 1, 'velocity': 70}]

        replies = [
            {'done_reason': 'stop', 'message': {'content': json.dumps(a)}},
            {'done_reason': 'stop', 'message': {'content': json.dumps(b)}},
            {'done_reason': 'stop', 'message': {'content': json.dumps(valid)}}
        ]

        with tempfile.TemporaryDirectory() as d:
            with patch.object(core, 'ORG', Path(d)), \
                 patch.object(core, 'local_model', return_value={'name': 'test'}), \
                 patch.object(core, 'retrieve', return_value=''), \
                 patch.object(core, 'api', side_effect=replies) as mock_api, \
                 patch('sovereign_music.foundation.write_explanation'):

                run = core.compose(SimpleNamespace(
                    model='test',
                    prompt='piano',
                    bars=1,
                    adapter=None,
                    previous_run=None,
                    theory_model=None,
                    theory_adapter=None
                ))

                self.assertEqual(mock_api.call_count, 3)
                self.assertTrue((run / 'composition.mid').exists())
                self.assertTrue(json.loads((run / 'validation.json').read_text())['valid'])
                self.assertIn('start + duration <= 4', json.dumps(mock_api.call_args_list[1].args[1]['messages']))
