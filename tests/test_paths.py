import unittest

from paths import BUNDLE_DIR, config_file, is_frozen, output_dir


class PathsTests(unittest.TestCase):
    def test_development_paths_keep_files_inside_project(self):
        self.assertFalse(is_frozen())
        self.assertEqual(config_file(), BUNDLE_DIR / 'config.json')
        self.assertEqual(output_dir('tmp/path-test'), BUNDLE_DIR / 'tmp/path-test')


if __name__ == '__main__':
    unittest.main()
