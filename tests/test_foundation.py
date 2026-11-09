# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import argparse,copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from sovereign_music import core,foundation,training,session
from sovereign_music.cli import demo
from sovereign_music.portable import export_run

class FoundationTests(unittest.TestCase):
    def test_all_formula_transpositions_and_spellings(self):
        for pc,root in enumerate(foundation.ROOTS):
            for quality,shape in foundation.QUALITIES.items():
                with self.subTest(root=root,quality=quality):
                    fact=foundation.chord(root+quality)
                    self.assertEqual(fact['pitch_classes'],[(pc+i)%12 for i in shape['intervals']])
                    self.assertEqual(len(fact['notes']),len(shape['intervals']))
        self.assertEqual(foundation.chord('Cdim7')['notes'],['C','Eb','Gb','Bbb'])
        self.assertEqual(foundation.chord('F#maj7')['notes'],['F#','A#','C#','E#'])
        self.assertEqual(foundation.chord('Dbmaj7')['pitch_classes'],foundation.chord('C#maj7')['pitch_classes'])
        with self.assertRaises(ValueError):foundation.chord('Calt-anything')
    def test_retrieval_and_public_provenance(self):
        self.assertEqual(foundation.retrieve('F#maj7')[0]['id'],'chord:Gbmaj7')
        self.assertIn('theory:major251',[r['id'] for r in foundation.retrieve('장조 투파이브')])
        self.assertFalse(any(r['kind']=='chord' for r in foundation.retrieve('A piano riff')))
        self.assertEqual(foundation.retrieve('qzxv blorb'),[])
        for record in foundation.records():
            self.assertNotIn('pages',record);self.assertNotIn('source_pdf',record)
    def test_export_is_reproducible_and_split_groups(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);foundation.export(p/'a');foundation.export(p/'b')
            self.assertEqual((p/'a/rag.jsonl').read_bytes(),(p/'b/rag.jsonl').read_bytes())
            training.prepare(p/'a/reviewed.jsonl',p/'splits')
            manifest=json.loads((p/'splits/manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(set(manifest['group_split'].values()),{'train','valid','test'})
            rows=training.records(p/'a/reviewed.jsonl');self.assertGreater(len(rows),700)
            for row in rows:
                if row['task']=='chord_lookup':self.assertEqual(row['group_id'],'chord-family:'+row['foundation_id'].split(':')[1].lstrip('CDEFGABb#'))
            rows[0]['messages'][1]['content']='Unreviewed invented answer'
            (p/'bad.jsonl').write_text(json.dumps(rows[0]),encoding='utf-8')
            with self.assertRaises(ValueError):training.records(p/'bad.jsonl')
    def test_explanation_distinguishes_candidate_from_detected(self):
        song={'chords':['Dm7','G7','Cmaj7'],'tracks':[]}
        report=foundation.explain(song,['theory:tritone'])
        self.assertEqual(report['detected_theory_patterns'][0]['theory_id'],'theory:major251')
        self.assertNotIn('theory:tritone',[r['theory_id'] for r in report['detected_theory_patterns']])
        self.assertEqual(report['retrieved_theory_candidates'],['theory:tritone'])
    def test_wrong_lora_chord_is_not_endorsed(self):
        report=foundation.check_review('{"symbol":"Cdim7","notes":["C","Eb","G"],"pitch_classes":[1,4,7]}')
        self.assertFalse(report['verified']);self.assertEqual(report['status'],'formula_mismatch')
        self.assertEqual(report['computed_chord']['notes'],['C','Eb','Gb','Bbb'])
        self.assertFalse(foundation.check_review('A plausible explanation')['verified'])
    def test_portable_export_keeps_existing_midi(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);demo(p/'run');before=(p/'run/composition.mid').read_bytes()
            report=export_run(p/'run',p/'export.mid');self.assertFalse(report['daw_import_verified'])
            self.assertEqual((p/'run/composition.mid').read_bytes(),before)
            with self.assertRaises(FileExistsError):export_run(p/'run',p/'export.mid')

class SessionTests(unittest.TestCase):
    def args(self,requests):
        return argparse.Namespace(name='test',bars=2,model='configured-local-only',adapter=None,logic=False,mcp_config=None,request=requests)
    def test_loop_revisions_failure_recovery_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);calls=[]
            def compose(args):
                calls.append(args)
                if args.prompt=='fail':raise ValueError('bad model output')
                run=p/f'run{len(calls)}';demo(run);foundation.write_explanation(json.loads((run/'composition.json').read_text(encoding='utf-8')),run);return run
            with patch.object(core,'ORG',p),patch.object(core,'compose',side_effect=compose):
                state=session.run(self.args(['first','fail','revise']),output=lambda _:None)
                self.assertEqual([t['status'] for t in state['turns']],['composed','failed','composed'])
                self.assertEqual(calls[2].previous_run,str(p/'run1'))
                state=session.run(self.args(['resume']),output=lambda _:None)
                self.assertEqual(calls[3].previous_run,str(p/'run3'))
                self.assertEqual(len(state['turns']),4)
                self.assertFalse((p/'sessions/test/active.lock').exists())
    def test_explicit_quit_and_new(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(core,'ORG',Path(d)),patch.object(core,'compose') as compose:
                session.run(self.args(['/new','/quit','must not run']),output=lambda _:None)
                compose.assert_not_called()
    def test_logic_build_uses_final_success_and_skips_failed_revision(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=self.args(['first','revise']);a.mcp_config=p/'logic.toml';a.logic_project=p/'new.logicx'
            def compose(args):
                if args.prompt=='revise':raise ValueError('invalid model output')
                run=p/'run';demo(run);foundation.write_explanation(json.loads((run/'composition.json').read_text(encoding='utf-8')),run);return run
            with patch.object(core,'ORG',p),patch.object(core,'compose',side_effect=compose),patch('sovereign_music.logic.build_project') as build:
                with self.assertRaises(RuntimeError):session.run(a,output=lambda _:None)
                build.assert_not_called()
                state=json.loads((p/'sessions/test/session.json').read_text())
                self.assertEqual(state['logic_build']['status'],'skipped')
                self.assertEqual(state['latest_run'],str(p/'run'))
    def test_platform_and_name_guard(self):
        a=self.args(['/quit']);a.name='../outside'
        with self.assertRaises(ValueError):session.run(a)
        a=self.args(['/quit']);a.logic=True
        with patch('sys.platform','win32'):
            with self.assertRaises(ValueError):session.run(a)
