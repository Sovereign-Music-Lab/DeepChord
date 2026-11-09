# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import Mock
from sovereign_music.mcp import Client, ToolError


class MCPErrorTests(unittest.TestCase):
    def test_failed_tool_keeps_evidence_and_does_not_repeat_request(self):
        response={'isError':True,'structuredContent':{
            'reason':'arrange_focus_not_verified','raw_rows':[{'large':'x'*10000}]}}
        client=object.__new__(Client)
        client.request=Mock(return_value=response)
        with self.assertRaises(ToolError) as caught:
            client.tool('logic_midi','move_prepared_region',{'preparation_id':'once'},timeout=330)
        self.assertIs(caught.exception.response,response)
        self.assertIn('arrange_focus_not_verified',str(caught.exception))
        self.assertLess(len(str(caught.exception)),300)
        client.request.assert_called_once()

    def test_unstructured_error_does_not_dump_its_payload(self):
        response={'isError':True,'content':[{'type':'text','text':'x'*20000}]}
        error=ToolError('logic_project','open',response)
        self.assertIs(error.response,response)
        self.assertEqual(str(error),'logic_project.open: tool reported failure')


if __name__=='__main__':unittest.main()
