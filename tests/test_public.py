# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Guard the narrow public-brand exception without allowing private binaries."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('public_audit', ROOT / 'scripts/check_public.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PublicAssetsTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'site').is_dir(), 'website assets are source-checkout only')
    def test_only_reviewed_bytes_are_accepted(self):
        for name in audit.PUBLIC_ASSETS:
            with self.subTest(name=name):
                data = (ROOT / name).read_bytes()
                self.assertIsNone(audit.issue(name, data))
                self.assertIsNotNone(audit.issue(name, data + b'private payload'))
                self.assertIsNotNone(audit.issue(name, data, '120000'))

    def test_unknown_images_weights_and_private_paths_stay_blocked(self):
        for name in ['site/assets/private.png', 'site/weights.safetensors', '.private/data.md']:
            self.assertIsNotNone(audit.issue(name, b'private'))
        private_path = '/Users/' + 'example/private/book.pdf'
        self.assertIsNotNone(audit.issue('docs/sample.md', private_path.encode()))

    @unittest.skipUnless((ROOT / 'site').is_dir(), 'website assets are source-checkout only')
    def test_public_translations_and_notices(self):
        for name in ['README.ko.md', 'NOTICE', 'site/LICENSE', 'site/NOTICE', 'site/en/index.html']:
            self.assertIsNone(audit.issue(name, (ROOT / name).read_bytes()))


if __name__ == '__main__':
    unittest.main()
