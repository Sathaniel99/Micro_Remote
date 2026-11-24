"""Pruebas del formato de magnitudes."""

from __future__ import annotations

import unittest

from micro_remote import formatting


class FormattingTests(unittest.TestCase):
    def test_gain(self) -> None:
        self.assertEqual(formatting.format_gain(1), "1.0x")
        self.assertEqual(formatting.format_gain(2.55), "2.5x")

    def test_level(self) -> None:
        self.assertEqual(formatting.format_level(0.0), "silencio")
        self.assertEqual(formatting.format_level(1.0), "0.0 dBFS")
        self.assertEqual(formatting.format_level(0.999), "0.0 dBFS")
        self.assertEqual(formatting.format_level(0.5), "-6.0 dBFS")

    def test_level_fraction_uses_decibels(self) -> None:
        self.assertEqual(formatting.level_fraction(0.0), 0.0)
        self.assertAlmostEqual(formatting.level_fraction(1.0), 1.0)
        self.assertAlmostEqual(formatting.level_fraction(0.01), 1.0 / 3.0)
        self.assertEqual(formatting.level_fraction(0.0001), 0.0)
        self.assertEqual(formatting.level_fraction(2.0), 1.0)

    def test_bitrate(self) -> None:
        self.assertEqual(formatting.format_bitrate(0), "0 kbps")
        self.assertEqual(formatting.format_bitrate(705.6), "706 kbps")
        self.assertEqual(formatting.format_bitrate(2048), "2.05 Mbps")

    def test_duration(self) -> None:
        self.assertEqual(formatting.format_duration(0), "00:00")
        self.assertEqual(formatting.format_duration(65), "01:05")
        self.assertEqual(formatting.format_duration(3725), "1:02:05")

    def test_bytes(self) -> None:
        self.assertEqual(formatting.format_bytes(512), "512 B")
        self.assertEqual(formatting.format_bytes(2048), "2.0 KB")


if __name__ == "__main__":
    unittest.main()
