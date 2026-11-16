import json
import os
from pathlib import Path
import tempfile
import unittest

from open_webui import startup_config


class StartupConfigTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'settings.json'

    def tearDown(self):
        startup_config.startup.clear()
        startup_config.config.clear()
        self.directory.cleanup()

    def write(self, value):
        self.path.write_text(json.dumps(value))
        startup_config.load(self.path)

    def test_file_is_typed_and_does_not_change_environment(self):
        before = dict(os.environ)
        self.write({'startup': {'BYPASS_ADMIN_ACCESS_CONTROL': False}, 'config': {'ui.default_models': 'codex'}})
        self.assertIs(startup_config.startup['BYPASS_ADMIN_ACCESS_CONTROL'], False)
        self.assertEqual(startup_config.registered_values({'ui.default_models': ''}), {'ui.default_models': 'codex'})
        self.assertEqual(dict(os.environ), before)

    def test_invalid_settings_never_replace_loaded_configuration(self):
        self.write({'startup': {'ENABLE_TOOL_SERVERS': True}})
        for invalid in [[], {'unknown': {}}, {'startup': []}, {'startup': {'UNKNOWN': True}}, {'startup': {'ENABLE_TOOL_SERVERS': 'false'}}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.write(invalid)
            self.assertEqual(startup_config.startup, {'ENABLE_TOOL_SERVERS': True})

    def test_registered_settings_reject_unknown_keys_and_wrong_types(self):
        for value in [{'missing': True}, {'enabled': 'false'}, {'enabled': 1}]:
            self.write({'config': value})
            with self.assertRaises(ValueError):
                startup_config.registered_values({'enabled': True})

    def test_loading_replacement_removes_previous_file_values(self):
        self.write({'startup': {'ENABLE_TOOL_SERVERS': False}, 'config': {'ui.default_models': 'old'}})
        self.write({'startup': {'ENABLE_TOOL_SERVERS': True}})
        self.assertEqual(startup_config.startup, {'ENABLE_TOOL_SERVERS': True})
        self.assertEqual(startup_config.config, {})


if __name__ == '__main__':
    unittest.main()
