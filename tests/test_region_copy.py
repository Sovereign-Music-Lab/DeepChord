# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sovereign_music import logic_edit
from sovereign_music.mcp import ToolError
from test_logic_events import snapshot


class RegionCopyTests(unittest.TestCase):
    def exercise(self, *, changed_other=False, stale_disk=False, native_failure=False):
        target={'kind':'midi','name':'Piano','trackIndex':0,'startBar':1,'endBar':9}
        other={**target,'name':'Bass','trackIndex':1}
        before=snapshot();before['preparation_id']='single-use'
        before['selected_region_observation'].update(start_bar=1,end_bar=9)
        after=deepcopy(before);after['selected_region_observation'].update(start_bar=3,end_bar=11)
        for row in after['raw_rows']:
            row['Position']['value_description']='3'+row['Position']['value_description'][1:]
        after.update(raw_bar_shift_verified=True,other_raw_fields_preserved=True,other_observed_region_bounds_preserved=True)
        other_before=deepcopy(before);other_before['selected_region_observation'].update(name='Bass',track_index=1)
        other_before['event_list_region_path']='Bass'
        other_after=deepcopy(other_before)
        if changed_other: other_after['raw_rows'][1]['Val']['value_description']='0'
        other_reopened=deepcopy(other_before)
        if stale_disk: other_reopened['raw_rows'][0]['Num']['slider_value']=61
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'Original.logicx';source.mkdir();(source/'data').write_bytes(b'original')
            output=root/'Result.logicx';current=None;calls=[]
            class Fake:
                def __init__(self,*a): pass
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def request(self,method,params,**kwargs):
                    if method=='tools/list':return {'description':'prepare_region_events move_prepared_region'}
                    raise AssertionError('Unexpected request; native move owns and verifies navigation')
                def tool(self,name,command,params=None,**kwargs):
                    nonlocal current
                    calls.append(command);value={}
                    if command=='is_running':value={'message':'true'}
                    if command=='open':current=Path(params['path'])
                    if command=='get_regions':value={'complete':True,'regions':[target,other]}
                    if command=='move_prepared_region':
                        self_outer.assertEqual(params,{'preparation_id':'single-use','start_bar':3})
                        if native_failure:
                            raise ToolError(name,command,{'isError':True,'structuredContent':{
                                'reason':'focus_lost','musical_event_write_attempted':False}})
                        value=after
                    if command=='save':
                        (current/'data').write_bytes(b'saved');value={'verified':True,'document_path':str(current)}
                    return {'structuredContent':value}
            self_outer=self
            readings=[other_before,before,other_after,after,other_reopened]
            with patch.object(logic_edit.sys,'platform','darwin'),patch.object(logic_edit.core,'local_model'),patch.object(logic_edit,'Client',Fake),patch.object(logic_edit,'project_identity',side_effect=lambda c:{'file_path':str(current)}),patch.object(logic_edit,'choose_region',return_value=target),patch.object(logic_edit,'region_move_plan',return_value={'start_bar':3}),patch.object(logic_edit,'prepare_region_events',side_effect=readings):
                if changed_other or stale_disk or native_failure:
                    with self.assertRaises(RuntimeError):logic_edit.move_region_copy(source,output,'move Piano to bar 3','local','config')
                else:
                    result=logic_edit.move_region_copy(source,output,'move Piano to bar 3','local','config')
                    self.assertEqual(result['status'],'passed')
                    self.assertEqual(result['verified_other_midi_regions'],1)
            self.assertEqual((source/'data').read_bytes(),b'original')
            self.assertEqual(calls.count('move_prepared_region'),1)
            self.assertEqual(calls.count('save'),0 if changed_other or native_failure else 1)
            if native_failure:
                error=json.loads((root/'Result.deepchord/tool-error.json').read_text())
                self.assertEqual(error['structuredContent']['reason'],'focus_lost')

    def test_native_verified_move_checks_other_region_and_saved_bytes(self):self.exercise()
    def test_changed_pedal_in_other_region_prevents_save(self):self.exercise(changed_other=True)
    def test_changed_other_region_on_disk_prevents_success(self):self.exercise(stale_disk=True)
    def test_failed_native_call_retains_tool_evidence_without_save_or_retry(self):self.exercise(native_failure=True)


class RegionMovePlanTests(unittest.TestCase):
    def test_invalid_unsupported_and_truncated_plans_never_pass(self):
        region={'name':'Piano','startBar':1,'endBar':9}
        for operation,start,reason in [('unsupported',None,'stop'),('move_region',True,'stop'),('move_region',1,'stop'),('move_region',10000,'stop'),('move_region',3,'length')]:
            answer={'message':{'content':json.dumps({'operation':operation,'start_bar':start})},'done_reason':reason}
            with patch.object(logic_edit.core,'local_model'),patch.object(logic_edit.core,'api',return_value=answer):
                with self.assertRaises(ValueError):logic_edit.region_move_plan('move Piano',region,'local')


if __name__=='__main__':unittest.main()
