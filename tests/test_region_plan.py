# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import json
import unittest
from unittest.mock import patch
from sovereign_music.logic_edit import choose_region


class RegionPlanTests(unittest.TestCase):
    def test_only_region_is_not_assumed_when_the_user_names_another(self):
        inventory={'complete':True,'regions':[{'kind':'midi','name':'Piano'}]}
        with patch('sovereign_music.logic_edit.core.local_model'),patch('sovereign_music.logic_edit.core.api',return_value={'message':{'content':'{"region_index":null}'}}) as model:
            with self.assertRaises(ValueError):choose_region('Edit the Flute region',inventory,'local')
            model.assert_called_once()

    def test_only_an_observed_midi_region_can_be_selected(self):
        regions=[{'kind':'audio','name':'Voice'},{'kind':'midi','name':'Piano'},{'kind':'midi','name':'Bass'}]
        for index in (True,-1,2,None):
            with patch('sovereign_music.logic_edit.core.local_model'),patch('sovereign_music.logic_edit.core.api',return_value={'message':{'content':json.dumps({'region_index':index})}}):
                with self.assertRaises(ValueError):choose_region('Bass',{'complete':True,'regions':regions},'local')
        with patch('sovereign_music.logic_edit.core.local_model'),patch('sovereign_music.logic_edit.core.api',return_value={'message':{'content':'{"region_index":1}'}}):
            self.assertEqual(choose_region('Bass',{'complete':True,'regions':regions},'local'),regions[2])

    def test_incomplete_inventory_never_invokes_model(self):
        with patch('sovereign_music.logic_edit.core.api') as model:
            with self.assertRaises(ValueError):choose_region('Piano',{'complete':False,'regions':[]},'local')
            model.assert_not_called()


if __name__=='__main__':unittest.main()
