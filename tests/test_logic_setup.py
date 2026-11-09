# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import hashlib
from importlib.resources import files
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from sovereign_music.logic_setup import install


class LogicSetupTests(unittest.TestCase):
    def test_bundle_pins_source_patch_and_license(self):
        assets=files('sovereign_music').joinpath('assets')
        metadata=tomllib.loads(assets.joinpath('logic-extension.toml').read_text())
        content=assets.joinpath('logic-region-edit.patch.txt').read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(),metadata['patch_sha256'])
        self.assertEqual(len(metadata['revision']),40)
        self.assertIn('MIT License',assets.joinpath('logic-mcp-LICENSE.txt').read_text())
        self.assertNotIn(b'/Users/',content)
        self.assertIn(b'harvestIndexedRowPass',content)

    def test_existing_installation_never_runs_a_command(self):
        with tempfile.TemporaryDirectory() as directory, patch('sovereign_music.logic_setup.sys.platform','darwin'),patch('sovereign_music.logic_setup.subprocess.run') as run:
            with self.assertRaises(ValueError): install(Path(directory))
            run.assert_not_called()

    def test_failed_fetch_retains_diagnostic_without_config(self):
        with tempfile.TemporaryDirectory() as directory, patch('sovereign_music.logic_setup.sys.platform','darwin'),patch('sovereign_music.logic_setup.subprocess.run',side_effect=OSError('offline')):
            target=Path(directory)/'install'
            with self.assertRaises(RuntimeError): install(target)
            self.assertTrue((target/'installation.json').is_file())
            self.assertFalse((target/'logic.toml').exists())


if __name__=='__main__': unittest.main()
