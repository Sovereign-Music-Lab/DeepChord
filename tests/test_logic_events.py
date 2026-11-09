# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest
from sovereign_music.logic_events import EVENT_FILTERS, verify_pitch_edit, expected_pitch_edit


def snapshot():
    return {'success':True,'observed_rows_content_stable':True,'row_selection_restored':True,
            'event_list_filter_states':dict.fromkeys(EVENT_FILTERS,True),
            'event_list_item_count_text':'3 Events',
            'selected_region_observation':{'name':'Piano','track_index':0},
            'event_list_region_path':'Piano','live_header_titles':['Position','Status','Num'],
            'raw_rows':[
                {'Status':{'value_description':'Note'},'Num':{'slider_value':60},'Position':{'value_description':'1 1 1 1'}},
                {'Status':{'value_description':'Control'},'Num':{'slider_value':64},'Position':{'value_description':'1 1 1 61'},'Val':{'value_description':'90'}},
                {'Status':{'value_description':'Note'},'Num':{'slider_value':60},'Position':{'value_description':'1 1 1 1'}},
            ]}

class LogicEventsTests(unittest.TestCase):
    def test_one_of_duplicate_notes_changes_without_collapsing_events(self):
        before=snapshot();after=deepcopy(before);after['raw_rows'][0]['Num']['slider_value']=62
        report=verify_pitch_edit(before,after,0,60,62)
        self.assertTrue(report['other_raw_fields_preserved'])
        self.assertFalse(report['canonical_owner_or_completeness_proven'])
        self.assertEqual(before['raw_rows'][0]['Num']['slider_value'],60)

    def test_moved_pedal_is_rejected_even_with_same_event_count(self):
        before=snapshot();after=deepcopy(before);after['raw_rows'][0]['Num']['slider_value']=62
        after['raw_rows'][1]['Position']['value_description']='5 1 1 61'
        with self.assertRaises(ValueError):verify_pitch_edit(before,after,0,60,62)

    def test_other_note_edit_and_missing_duplicate_are_rejected(self):
        before=snapshot()
        for missing in (False,True):
            after=deepcopy(before);after['raw_rows'][0]['Num']['slider_value']=62
            if missing:
                after['raw_rows'].pop();after['event_list_item_count_text']='2 Events'
            else:after['raw_rows'][2]['Num']['slider_value']=62
            with self.assertRaises(ValueError):verify_pitch_edit(before,after,0,60,62)

    def test_hidden_pedal_filter_and_stale_pitch_are_rejected(self):
        before=snapshot();before['event_list_filter_states']['controller']=False
        with self.assertRaises(ValueError):expected_pitch_edit(before,0,60,62)
        with self.assertRaises(ValueError):expected_pitch_edit(snapshot(),0,61,62)
        with self.assertRaises(ValueError):expected_pitch_edit(snapshot(),1,64,62)
        with self.assertRaises(ValueError):expected_pitch_edit(snapshot(),True,60,62)

if __name__=='__main__':unittest.main()
