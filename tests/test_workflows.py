# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from sovereign_music.cli import demo
from sovereign_music import training,logic

class WorkflowTests(unittest.TestCase):
    def test_demo_no_model(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'demo';demo(p)
            self.assertTrue((p/'composition.mid').is_file())
            with self.assertRaises(FileExistsError):demo(p)
    def test_group_split(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);training.smoke_data(p/'input.jsonl');training.prepare(p/'input.jsonl',p/'data')
            m=json.loads((p/'data/manifest.json').read_text(encoding='utf-8'));self.assertEqual(sum(m['counts'].values()),12)
            self.assertEqual(set(m['group_split'].values()),{'train','valid','test'})
    def test_unreviewed_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.jsonl';training.smoke_data(p)
            rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()];rows[0]['reviewed']=False;p.write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):training.prepare(p,Path(d)/'data')
    def test_insufficient_groups(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.jsonl';training.smoke_data(p)
            rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
            for r in rows:r['group_id']='same-song'
            p.write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):training.prepare(p,Path(d)/'data')
    def test_duplicate_targets_across_splits(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.jsonl';training.smoke_data(p)
            rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
            for r in rows:r['messages'][1]['content']=rows[0]['messages'][1]['content']
            p.write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):training.prepare(p,Path(d)/'data')
    def test_model_tag_not_local_path(self):
        with self.assertRaises(ValueError):training.local_path('not-installed/model')
    def test_launch_preserves_original_and_is_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'song';demo(p);before=(p/'composition.mid').read_bytes()
            with patch('sovereign_music.logic.sys.platform','darwin'),patch('sovereign_music.logic.subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
                result=logic.open_run(p)
                self.assertFalse(result['import_verified']);self.assertFalse(result['audio_verified'])
                self.assertEqual(run.call_args.args[0][:3],['/usr/bin/open','-b','com.apple.logic10'])
            self.assertEqual((p/'composition.mid').read_bytes(),before)
            self.assertNotEqual(Path(result['midi']),p/'composition.mid')
    def test_launch_failed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'song';demo(p)
            with patch('sovereign_music.logic.sys.platform','darwin'),patch('sovereign_music.logic.subprocess.run',return_value=subprocess.CompletedProcess([],1,'','missing app')):
                with self.assertRaises(RuntimeError):logic.open_run(p)
            self.assertEqual(json.loads((p/'logic-handoff.json').read_text(encoding='utf-8'))['status'],'launch_failed')

if __name__=='__main__':unittest.main()
