"""Pruebas del procesamiento PCM."""

from __future__ import annotations

import unittest
from array import array

from micro_remote import dsp


class PcmRoundTripTests(unittest.TestCase):
    def test_wire_round_trip(self) -> None:
        samples = array("h", [-32768, -1, 0, 1, 12345, 32767])
        encoded = dsp.pcm_to_bytes(samples)
        self.assertEqual(len(encoded), len(samples) * 2)
        self.assertEqual(dsp.pcm_from_bytes(encoded), samples)

    def test_odd_length_is_ignored(self) -> None:
        samples = dsp.pcm_from_bytes(b"\x00\x01\x02")
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0], 0x0100)

    def test_native_round_trip(self) -> None:
        samples = array("h", [-200, 0, 200])
        self.assertEqual(dsp.pcm_from_native(dsp.pcm_to_native(samples)), samples)


class GainTests(unittest.TestCase):
    def test_identity_returns_same_array(self) -> None:
        samples = array("h", [1, 2, 3])
        self.assertIs(dsp.apply_gain(samples, 1.0), samples)

    def test_gain_multiplies(self) -> None:
        samples = array("h", [100, -100, 0])
        self.assertEqual(dsp.apply_gain(samples, 2.0), array("h", [200, -200, 0]))

    def test_gain_clips(self) -> None:
        samples = array("h", [20000, -20000])
        self.assertEqual(
            dsp.apply_gain(samples, 5.0), array("h", [32767, -32768])
        )

    def test_zero_gain_is_silence(self) -> None:
        samples = array("h", [500, -500])
        self.assertEqual(dsp.apply_gain(samples, 0.0), array("h", [0, 0]))

    def test_non_finite_gain_is_neutral(self) -> None:
        samples = array("h", [100, -100])
        for invalid in (float("nan"), float("inf"), float("-inf")):
            self.assertEqual(dsp.apply_gain(samples, invalid), samples)

    def test_gain_is_clamped_to_supported_range(self) -> None:
        samples = array("h", [100, -100])
        self.assertEqual(
            dsp.apply_gain(samples, 99.0), dsp.apply_gain(samples, 5.0)
        )
        self.assertEqual(
            dsp.apply_gain(samples, -3.0), array("h", [0, 0])
        )


class LevelTests(unittest.TestCase):
    def test_silence(self) -> None:
        silence = array("h", [0] * 16)
        self.assertEqual(dsp.rms(silence), 0.0)
        self.assertEqual(dsp.peak(silence), 0.0)

    def test_full_scale(self) -> None:
        loud = array("h", [-32768, 32767] * 8)
        self.assertAlmostEqual(dsp.rms(loud), 1.0, places=4)
        self.assertAlmostEqual(dsp.peak(loud), 1.0, places=4)

    def test_empty(self) -> None:
        empty = array("h")
        self.assertEqual(dsp.rms(empty), 0.0)
        self.assertEqual(dsp.peak(empty), 0.0)


class EnvelopeTests(unittest.TestCase):
    def test_buckets_preserve_extremes(self) -> None:
        samples = array("h", [0, 10, -5, 20, -20, 0, 30, -30])
        lows, highs = dsp.envelope(samples, 4)
        self.assertEqual(len(lows), 4)
        self.assertEqual(len(highs), 4)
        self.assertEqual(min(lows), -30)
        self.assertEqual(max(highs), 30)

    def test_more_buckets_than_samples(self) -> None:
        samples = array("h", [1, 2, 3])
        lows, highs = dsp.envelope(samples, 100)
        self.assertEqual(len(lows), 3)
        self.assertEqual(lows, highs)

    def test_empty_and_invalid(self) -> None:
        self.assertEqual(dsp.envelope(array("h"), 10), ([], []))
        self.assertEqual(dsp.envelope(array("h", [1]), 0), ([], []))


if __name__ == "__main__":
    unittest.main()
