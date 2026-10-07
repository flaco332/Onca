import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from app import paths


class PathTests(unittest.TestCase):
    def test_explicit_data_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"ONCA_DATA_DIR": folder}):
                self.assertEqual(paths.get_data_dir(), os.path.abspath(folder))

    def test_relative_override_is_rejected(self):
        with patch.dict(os.environ, {"ONCA_DATA_DIR": "relative"}):
            with self.assertRaises(ValueError):
                paths.get_data_dir()

    def test_frozen_resources_use_bundle(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", "bundle", create=True):
            self.assertEqual(paths.get_resource_base_dir(), "bundle")

    def test_default_data_is_outside_source(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertNotEqual(paths.get_data_dir(), paths.PROJECT_ROOT)
