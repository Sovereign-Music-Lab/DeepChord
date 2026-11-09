# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest
from sovereign_music.logic_events import verify_region_shift
from test_logic_events import snapshot


class RegionShiftTests(unittest.TestCase):
    def pair(self):
        before=snapshot()
        before['selected_region_observation'].update(start_bar=1,end_bar=9)
        for row in before['raw_rows']:
            row['Position']['group_slider_values']=list(map(int,row['Position']['value_description'].split()))
        after=deepcopy(before)
        after['selected_region_observation'].update(start_bar=3,end_bar=11)
        for row in after['raw_rows']:
            parts=row['Position']['group_slider_values']; parts[0]+=2
            row['Position']['value_description']=' '.join(map(str,parts))
        return before,after

    def test_every_event_moves_including_pedal_and_duplicate_note(self):
        before,after=self.pair()
        self.assertTrue(verify_region_shift(before,after,2)['exact_requested_bar_shift'])
        self.assertTrue(verify_region_shift(after,before,-2)['other_raw_fields_preserved'])

    def test_pedal_left_behind_is_rejected(self):
        before,after=self.pair();after['raw_rows'][1]=deepcopy(before['raw_rows'][1])
        with self.assertRaises(ValueError):verify_region_shift(before,after,2)

    def test_shift_plus_unrequested_note_or_controller_edit_is_rejected(self):
        for index in (0,1):
            before,after=self.pair();after['raw_rows'][index]['Num']['slider_value']+=1
            with self.assertRaises(ValueError):verify_region_shift(before,after,2)

    def test_wrong_region_or_missing_event_is_rejected(self):
        before,after=self.pair();after['selected_region_observation']['track_index']=1
        with self.assertRaises(ValueError):verify_region_shift(before,after,2)
        before,after=self.pair();after['raw_rows'].pop();after['event_list_item_count_text']='2 Events'
        with self.assertRaises(ValueError):verify_region_shift(before,after,2)


if __name__=='__main__':unittest.main()
