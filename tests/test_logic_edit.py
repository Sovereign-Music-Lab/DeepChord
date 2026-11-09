# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sovereign_music import logic_edit


class LogicEditTests(unittest.TestCase):
    def plan(self, content):
        return {'message':{'content':content},'done_reason':'stop'}

    def test_explicit_tempo_and_model_must_agree(self):
        with patch.object(logic_edit.core,'local_model'),patch.object(logic_edit.core,'api',return_value=self.plan('{"operation":"set_tempo","tempo":92}')):
            self.assertEqual(logic_edit.tempo_plan('템포를 92 BPM으로 바꿔줘','local')['tempo'],92)
            with self.assertRaises(ValueError):logic_edit.tempo_plan('템포를 92 BPM으로 바꿔줘 그리고 트랙을 지워줘','local')
            with self.assertRaises(ValueError):logic_edit.tempo_plan('템포를 93 BPM으로 바꿔줘','local')

    def test_existing_destination_is_never_opened_or_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.logicx';source.mkdir()
            dest=Path(d)/'existing.logicx';dest.mkdir()
            with patch('sovereign_music.logic_edit.sys.platform','darwin'),patch.object(logic_edit,'tempo_plan') as plan,patch.object(logic_edit,'Client') as client:
                with self.assertRaises(ValueError):logic_edit.edit_tempo_copy(source,dest,'92 BPM','local','config')
                plan.assert_not_called();client.assert_not_called()

    def test_wrong_current_project_does_not_save_or_edit(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.logicx';source.mkdir();other=Path(d)/'other.logicx';other.mkdir()
            class Fake:
                def __init__(self,*args):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def tool(self,*args,**kwargs):raise AssertionError('unexpected write')
            with patch('sovereign_music.logic_edit.sys.platform','darwin'),patch.object(logic_edit,'Client',Fake),patch.object(logic_edit,'tempo_plan',return_value={'operation':'set_tempo','tempo':92}),patch.object(logic_edit,'project_identity',return_value={'file_path':str(other)}):
                with self.assertRaises(RuntimeError):logic_edit.edit_tempo_copy(source,Path(d)/'new.logicx','92 BPM','local','config')


class RegionPreparationTests(unittest.TestCase):
    def test_rejects_incomplete_selector_before_calling_mcp(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d)/'song.logicx';project.mkdir()
            from unittest.mock import Mock
            client=Mock()
            with self.assertRaises(ValueError):
                logic_edit.prepare_region_events(client, project, {'name':'Piano'})
            client.tool.assert_not_called()

    def test_project_change_after_navigation_stops_work(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d)/'song.logicx';project.mkdir()
            from unittest.mock import Mock
            client=Mock()
            region={'name':'Piano','kind':'midi','trackIndex':0,'startBar':1,'endBar':9}
            with patch.object(logic_edit,'project_identity',side_effect=[
                {'file_path':str(project)}, {'file_path':str(Path(d)/'other.logicx')}
            ]):
                with self.assertRaises(RuntimeError):logic_edit.prepare_region_events(client,project,region)
            self.assertEqual(client.tool.call_count,1)
            self.assertEqual(client.tool.call_args.args[:2],('logic_midi','prepare_region_events'))

if __name__=='__main__':unittest.main()
