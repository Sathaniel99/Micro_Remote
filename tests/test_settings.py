"""Pruebas de persistencia de ajustes."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from micro_remote.config import DEFAULT_GAIN, DEFAULT_PORT
from micro_remote.settings import Settings, settings_path

ENV = "MICRO_REMOTE_HOME"


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        patcher = patch.dict(os.environ, {ENV: str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_round_trip(self) -> None:
        original = Settings(
            host="192.168.1.42",
            port=6200,
            gain=2.5,
            input_device=1,
            output_device=3,
        )
        path = original.save()
        self.assertEqual(path.parent, self.home)
        self.assertTrue(path.is_file())

        loaded = Settings.load()
        self.assertEqual(loaded.host, "192.168.1.42")
        self.assertEqual(loaded.port, 6200)
        self.assertAlmostEqual(loaded.gain, 2.5)
        self.assertEqual(loaded.input_device, 1)
        self.assertEqual(loaded.output_device, 3)

    def test_missing_file_uses_defaults(self) -> None:
        loaded = Settings.load()
        self.assertEqual(loaded.host, "127.0.0.1")
        self.assertEqual(loaded.port, DEFAULT_PORT)
        self.assertAlmostEqual(loaded.gain, DEFAULT_GAIN)
        self.assertIsNone(loaded.input_device)

    def test_corrupt_file_uses_defaults(self) -> None:
        settings_path().parent.mkdir(parents=True, exist_ok=True)
        settings_path().write_text("esto no es json", encoding="utf-8")
        loaded = Settings.load()
        self.assertEqual(loaded.port, DEFAULT_PORT)

    def test_invalid_values_are_sanitized(self) -> None:
        target = settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "host": "999.1.1.1",
                    "port": 99999,
                    "gain": 99,
                    "input_device": -4,
                    "output_device": "abc",
                }
            ),
            encoding="utf-8",
        )
        loaded = Settings.load()
        self.assertEqual(loaded.host, "127.0.0.1")
        self.assertEqual(loaded.port, DEFAULT_PORT)
        self.assertAlmostEqual(loaded.gain, 5.0)
        self.assertIsNone(loaded.input_device)
        self.assertIsNone(loaded.output_device)

    def test_save_creates_directory(self) -> None:
        nested = self.home / "sub" / "carpeta"
        path = Settings().save(nested / "settings.json")
        self.assertTrue(path.is_file())

    def test_save_leaves_no_temporary_files(self) -> None:
        Settings().save()
        self.assertEqual(list(self.home.glob("*.tmp")), [])

    def test_roles_do_not_overwrite_each_other(self) -> None:
        emisor = Settings(host="192.168.1.20", port=6000, input_device=3)
        receptor = Settings(port=7000, output_device=1)
        emisor_path = emisor.save(role="emisor")
        receptor_path = receptor.save(role="receptor")
        self.assertNotEqual(emisor_path, receptor_path)

        opened_receptor = Settings.load(role="receptor")
        opened_receptor.save(role="receptor")

        loaded_emisor = Settings.load(role="emisor")
        self.assertEqual(loaded_emisor.host, "192.168.1.20")
        self.assertEqual(loaded_emisor.port, 6000)
        self.assertEqual(loaded_emisor.input_device, 3)
        self.assertIsNone(loaded_emisor.output_device)

    def test_non_finite_gain_uses_default(self) -> None:
        target = settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"gain": float("nan")}), encoding="utf-8"
        )
        self.assertAlmostEqual(Settings.load().gain, DEFAULT_GAIN)


if __name__ == "__main__":
    unittest.main()
