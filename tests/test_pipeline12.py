# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""The DeepChord half of the 12-command pipeline diagram (commands 1-9).

These tests keep the documented commands and their key options parseable,
and check the offline behaviour that needs no model or Logic Pro.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from sovereign_music import cli, core  # noqa: E402

DIAGRAM = {
    1: ['demo', '--out', 'x'],
    2: ['session', '--name', 'n', '--bars', '16', '--request', 'r'],
    3: ['compose', 'p', '--previous-run', 'run'],
    4: ['song', 'p', '--resume', 'run'],
    5: ['logic', 'open', 'run'],
    6: ['logic', 'build', 'run', '--out', 'x.logicx', '--mcp-config', 'c.toml'],
    7: ['logic', 'edit', 'p.logicx', 'tempo 92', '--out', 'x.logicx', '--mcp-config', 'c.toml'],
    8: ['logic', 'edit-note', 'p.logicx', 'raise one note', '--out', 'x.logicx', '--mcp-config', 'c.toml'],
    9: ['logic', 'move-region', 'p.logicx', 'move to bar 3', '--out', 'x.logicx', '--mcp-config', 'c.toml'],
}


def run_cli(*args, env=None):
    return subprocess.run([sys.executable, '-m', 'sovereign_music', *args], capture_output=True, text=True,
                          env={**os.environ, 'PYTHONPATH': str(ROOT/'src'), **(env or {})}, timeout=60)


class DiagramCommands(unittest.TestCase):
    def test_every_diagram_command_parses(self):
        for number, argv in DIAGRAM.items():
            with self.subTest(number=number):
                a = cli.parser().parse_args(argv)
                self.assertEqual(a.cmd, argv[0])

    def test_session_allows_1_to_16_bars_only(self):
        for bars in ('0', '17'):
            with self.assertRaises(SystemExit), patch('sys.stderr'):
                cli.parser().parse_args(['session', '--bars', bars])

    def test_demo_needs_no_model_and_writes_valid_midi(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'demo'
            result = run_cli('demo', '--out', str(out), env={'DEEPCHORD_MODEL': 'not-installed'})
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ('composition.json', 'composition.mid', 'validation.json', 'request.json'):
                self.assertTrue((out/name).is_file(), name)
            self.assertEqual((out/'composition.mid').read_bytes()[:4], b'MThd')
            self.assertEqual(json.loads((out/'request.json').read_text())['origin'], 'deterministic_installation_fixture_not_AI')
            self.assertTrue(json.loads((out/'validation.json').read_text())['valid'])
            self.assertNotEqual(run_cli('demo', '--out', str(out)).returncode, 0, 'demo must not overwrite')


class DefaultModel(unittest.TestCase):
    def test_env_sets_default_model_for_every_model_command(self):
        code = ('from sovereign_music import cli;p=cli.parser();'
                'print([p.parse_args(a).model for a in (["compose","x"],["session"],["song","x"],'
                '["logic","edit","p","r","--out","o","--mcp-config","c"]) ])')
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                                env={**os.environ, 'PYTHONPATH': str(ROOT/'src'), 'DEEPCHORD_MODEL': 'my-local:1b'})
        self.assertEqual(result.stdout.strip(), str(['my-local:1b']*4), result.stderr)

    def test_missing_model_names_installed_tags_and_is_not_replaced(self):
        tags = {'models': [{'name': 'gpt-oss:20b'}, {'name': 'x:cloud'}, {'name': 'remote', 'remote_host': 'https://example.com'}]}
        with patch.object(core, 'api', return_value=tags):
            with self.assertRaises(ValueError) as caught:
                core.local_model('gemma4:12b-mlx')
        message = str(caught.exception)
        self.assertIn('gemma4:12b-mlx', message)
        self.assertIn('gpt-oss:20b', message)
        self.assertNotIn('x:cloud', message)
        self.assertNotIn('remote', message.split('Installed local models:')[1])
        self.assertIn('DEEPCHORD_MODEL', message)


class ComposeOutput(unittest.TestCase):
    def test_compose_prints_run_folder_once(self):
        song = {'title': 'T', 'tempo': 80, 'bars': 1, 'chords': ['Cmaj7'], 'tracks': [
            {'name': 'Melody', 'notes': [{'pitch': 72, 'start': 0, 'duration': 2, 'velocity': 70}]},
            {'name': 'Accompaniment', 'notes': [{'pitch': p, 'start': 0, 'duration': 3.5, 'velocity': 60} for p in (48, 52, 55, 59)]}]}
        reply = {'message': {'content': json.dumps(song)}, 'done_reason': 'stop'}
        with tempfile.TemporaryDirectory() as d, patch.object(core, 'ORG', Path(d)), \
                patch.object(core, 'local_model', return_value={'name': 'm'}), patch.object(core, 'api', return_value=reply), \
                patch.object(core, 'retrieve', return_value='evidence'), patch('builtins.print') as printed:
            run = core.compose(cli.parser().parse_args(['compose', 'p', '--bars', '1', '--model', 'm']))
            self.assertTrue((run/'composition.mid').is_file())
        self.assertFalse(any(str(run) in ' '.join(map(str, c.args)) for c in printed.call_args_list))


class ReasoningModels(unittest.TestCase):
    PAYLOAD = {'model': 'plain:1b', 'think': False, 'options': {'num_ctx': 4096, 'num_predict': 128}, 'messages': []}

    def test_plain_model_payload_is_unchanged(self):
        with patch.object(core, 'api', return_value={'done_reason': 'stop', 'message': {'content': '{}'}}) as api:
            core.chat(self.PAYLOAD, timeout=7)
        api.assert_called_once_with('/api/chat', self.PAYLOAD, timeout=7)

    def test_known_reasoning_model_gets_low_effort_and_room(self):
        with patch.object(core, 'api', return_value={'done_reason': 'stop', 'message': {'content': '{}'}}) as api:
            core.chat({**self.PAYLOAD, 'model': 'gpt-oss:20b'})
        sent = api.call_args.args[1]
        self.assertEqual(sent['think'], 'low')
        self.assertEqual(sent['options']['num_predict'], 128+core.REASONING_HEADROOM)
        self.assertEqual(sent['options']['num_ctx'], 4096+core.REASONING_HEADROOM)
        self.assertEqual(self.PAYLOAD['options']['num_predict'], 128, 'caller payload must not be mutated')

    def test_composing_gets_medium_effort_and_twice_the_room(self):
        with patch.object(core, 'api', return_value={'done_reason': 'stop', 'message': {'content': '{}'}}) as api:
            core.chat({**self.PAYLOAD, 'model': 'gpt-oss:20b'}, effort='medium')
        sent = api.call_args.args[1]
        self.assertEqual(sent['think'], 'medium')
        self.assertEqual(sent['options']['num_predict'], 128+2*core.REASONING_HEADROOM)

    def test_unknown_reasoning_model_is_detected_once_and_retried(self):
        cut = {'done_reason': 'length', 'message': {'content': '', 'thinking': 'long reasoning'}}
        good = {'done_reason': 'stop', 'message': {'content': '{"ok":1}'}}
        with patch.object(core, '_reasoning_seen', set()), patch.object(core, 'api', side_effect=[cut, good, good]) as api:
            self.assertEqual(core.chat({**self.PAYLOAD, 'model': 'new-thinker:9b'}), good)
            self.assertEqual(api.call_count, 2)
            core.chat({**self.PAYLOAD, 'model': 'new-thinker:9b'})
            self.assertEqual(api.call_count, 3, 'second request goes straight to the roomier settings')
            self.assertEqual(api.call_args.args[1]['think'], 'low')

    def test_truncation_without_reasoning_is_not_retried(self):
        cut = {'done_reason': 'length', 'message': {'content': '{"a":'}}
        with patch.object(core, 'api', return_value=cut) as api:
            self.assertEqual(core.chat(self.PAYLOAD), cut)
        api.assert_called_once()


if __name__ == '__main__':
    unittest.main()
