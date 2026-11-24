"""Pruebas de lógica de UI que no necesitan abrir una ventana Tk."""

from __future__ import annotations

import unittest

from micro_remote.ui.scope import AUTO_MAX_GAIN, AutoGain
from micro_remote.ui.window import center_window


class FakeRoot:
    """Sustituto mínimo de ``tk.Tk`` para probar ``center_window``."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.geometry_value = ""
        self.min_size: tuple[int, int] | None = None
        self.resizable_value: tuple[bool, bool] | None = None

    def winfo_screenwidth(self) -> int:
        return self.screen_width

    def winfo_screenheight(self) -> int:
        return self.screen_height

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def minsize(self, width: int, height: int) -> None:
        self.min_size = (width, height)

    def resizable(self, width: bool, height: bool) -> None:
        self.resizable_value = (width, height)


class AutoGainTests(unittest.TestCase):
    def test_silence_keeps_neutral_gain(self) -> None:
        gain = AutoGain()
        self.assertEqual(gain.update(0.0), 1.0)
        self.assertEqual(gain.gain, 1.0)

    def test_weak_signal_increases_visual_gain(self) -> None:
        gain = AutoGain()
        for _ in range(200):
            gain.update(0.01)
        self.assertGreater(gain.gain, 1.0)
        self.assertLessEqual(gain.gain, AUTO_MAX_GAIN)

    def test_reset_returns_to_neutral(self) -> None:
        gain = AutoGain()
        gain.update(0.01)
        gain.reset()
        self.assertEqual(gain.gain, 1.0)


class CenterWindowTests(unittest.TestCase):
    def test_centers_on_regular_screen(self) -> None:
        root = FakeRoot(1920, 1080)
        self.assertEqual(center_window(root, 1120, 860), (1120, 860))
        self.assertEqual(root.geometry_value, "1120x860+400+110")

    def test_small_screen_keeps_usable_width(self) -> None:
        root = FakeRoot(500, 400)
        self.assertEqual(center_window(root, 1120, 860), (520, 400))
        self.assertEqual(root.geometry_value, "520x400+0+0")
        self.assertEqual(root.min_size, (520, 400))


if __name__ == "__main__":
    unittest.main()
