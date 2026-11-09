# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import json
import unittest
from unittest.mock import patch
from sovereign_music.logic_edit import pitch_plan
from sovereign_music.logic_events import EVENT_FILTERS

class PitchPlanTests(unittest.TestCase):
    def snapshot(self):
        return {'success':True,'observed_rows_content_stable':True,'row_selection_restored':True,
                'event_list_filter_states':dict.fromkeys(EVENT_FILTERS,True),
                'event_list_item_count_text':'2 Events','raw_rows':[
                    {'Status':{'value_description':'Control'},'Num':{'slider_value':64}},
                    {'Status':{'value_description':'Note'},'Num':{'slider_value':60},
                     'Position':{'value_description':'1 1 1 1 '}}]}
    def response(self, plan, reason='stop'):
        return {'message':{'content':json.dumps(plan)},'done_reason':reason}
    def test_expected_pitch_comes_from_snapshot_not_model(self):
        with patch('sovereign_music.logic_edit.core.local_model') as local, patch(
            'sovereign_music.logic_edit.core.api',return_value=self.response({'operation':'set_pitch','row_index':1,'pitch':62})):
            self.assertEqual(pitch_plan('첫 음표를 MIDI 62로',self.snapshot(),'gemma'),
                             {'row_index':1,'expected_pitch':60,'pitch':62})
            local.assert_called_once_with('gemma')
    def test_controller_rows_and_invented_rows_never_become_note_targets(self):
        for index in (0, 99, True):
            with patch('sovereign_music.logic_edit.core.local_model'),patch(
                'sovereign_music.logic_edit.core.api',return_value=self.response({'operation':'set_pitch','row_index':index,'pitch':62})):
                with self.assertRaises(ValueError):pitch_plan('첫 음표',self.snapshot(),'gemma')
    def test_unsupported_and_truncated_plans_refuse(self):
        for plan,reason in [({'operation':'unsupported','row_index':None,'pitch':None},'stop'),
                            ({'operation':'set_pitch','row_index':1,'pitch':62},'length')]:
            with patch('sovereign_music.logic_edit.core.local_model'),patch(
                'sovereign_music.logic_edit.core.api',return_value=self.response(plan,reason)):
                with self.assertRaises(ValueError):pitch_plan('첫 음표',self.snapshot(),'gemma')

if __name__=='__main__':unittest.main()
