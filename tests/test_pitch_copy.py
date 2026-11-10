# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sovereign_music import logic_edit
from test_logic_events import snapshot


class PitchCopyTests(unittest.TestCase):
    def exercise(self, *, bad_pedal=False, bad_disk=False, old_server=False, timeout=False):
        before = snapshot(); before['preparation_id'] = 'one-use'
        after = deepcopy(before); after['raw_rows'][0]['Num']['slider_value'] = 62
        after.update(raw_pitch_diff_verified=True,other_raw_events_preserved=True)
        if bad_pedal:
            after['raw_rows'][1]['Position']['value_description'] = '5 1 1 61'
        reopened = deepcopy(after if not bad_disk else before)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'Source.logicx'; source.mkdir()
            (source/'ProjectData').write_bytes(b'untouched source')
            destination=root/'Result.logicx'; current=None; calls=[]
            class Fake:
                def __init__(self,*args): pass
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def request(self,method,params):
                    return {'description':'' if old_server else 'prepare_region_events edit_prepared_note_pitch'}
                def tool(self,name,command,params=None,**kwargs):
                    nonlocal current
                    calls.append(command)
                    result={}
                    if command=='is_running': result={'message':'false'}
                    if command=='open': current=Path(params['path'])
                    if command=='get_regions': result={'complete':True,'regions':[{'kind':'midi','name':'Piano'}]}
                    if command=='edit_prepared_note_pitch':
                        self_timeout=kwargs.get('timeout')
                        if self_timeout!=960: raise AssertionError('Full verification needs the extended operation timeout')
                        if timeout: raise TimeoutError('outcome unknown')
                        result=after
                    if command=='save':
                        (current/'ProjectData').write_bytes(b'saved pitch edit')
                        result={'verified':True,'document_path':str(current)}
                    return {'structuredContent':result}
            failed=bad_pedal or bad_disk or old_server or timeout
            with patch.object(logic_edit.sys,'platform','darwin'),patch.object(logic_edit,'Client',Fake),patch.object(logic_edit.core,'local_model'),patch.object(logic_edit,'project_identity',side_effect=lambda c:{'file_path':str(current)}),patch.object(logic_edit,'choose_region',return_value={'kind':'midi','name':'Piano'}),patch.object(logic_edit,'prepare_region_events',side_effect=[before,reopened]),patch.object(logic_edit,'pitch_plan',return_value={'row_index':0,'expected_pitch':60,'pitch':62}):
                if failed:
                    with self.assertRaises(RuntimeError):
                        logic_edit.edit_pitch_copy(source,destination,'first note to 62','local','config')
                else:
                    result=logic_edit.edit_pitch_copy(source,destination,'first note to 62','local','config')
                    self.assertEqual(result['status'],'passed')
                    self.assertTrue(result['saved_events_verified'])
                    self.assertEqual(current,destination)
            self.assertEqual((source/'ProjectData').read_bytes(),b'untouched source')
            report=json.loads((root/'Result.deepchord'/'report.json').read_text())
            self.assertEqual(report['status'],'failed' if failed else 'passed')
            if bad_pedal or timeout or old_server:
                self.assertNotIn('save',calls)
            if old_server:
                self.assertFalse(destination.exists())
                self.assertNotIn('open',calls)
            else:
                self.assertEqual(calls.count('edit_prepared_note_pitch'),1)
                self.assertIn('launch',calls)

    def test_closed_logic_launches_and_saved_bytes_are_reloaded(self): self.exercise()
    def test_pedal_movement_stops_before_save(self): self.exercise(bad_pedal=True)
    def test_stale_disk_data_never_reports_success(self): self.exercise(bad_disk=True)
    def test_missing_extension_stops_before_open(self): self.exercise(old_server=True)
    def test_timeout_never_repeats_or_saves(self): self.exercise(timeout=True)

    def test_package_links_are_refused_before_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); project=root/'Song.logicx'; project.mkdir()
            media=root/'media'; media.write_bytes(b'media')
            (project/'alias').symlink_to(media)
            with self.assertRaises(ValueError): logic_edit.package_manifest(project)


if __name__=='__main__': unittest.main()
