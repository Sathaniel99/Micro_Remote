"""Osciloscopio ligero dibujado sobre un Canvas de Tkinter.

Sustituye al lienzo de Matplotlib del proyecto original: no requiere
dependencias extra, se redibuja en pocos milisegundos y muestra un sobre
(mínimo/máximo) por columna, de modo que los picos nunca se pierden.

La amplitud dibujada se normaliza con una **autoescala visual** suavizada.
Así una señal débil del micrófono llena el lienzo sin modificar el audio que
se transmite ni el nivel real que se muestra en dBFS.
"""

from __future__ import annotations

import math
import tkinter as tk
from array import array
from typing import Sequence

from ..config import DEFAULT_AUDIO
from ..dsp import envelope, peak
from .draw import rounded_rectangle
from .theme import (
    ACCENT,
    BORDER,
    BORDER_STRONG,
    DISABLED,
    FONT,
    GRID,
    GRID_STRONG,
    MUTED,
    SCOPE_BG,
    SCOPE_FILL,
    SCOPE_GLOW,
    SCOPE_LINE,
    SURFACE,
)

AUTO_GATE = 0.0005
AUTO_TARGET = 0.90
AUTO_MAX_GAIN = 160.0
AUTO_INCREASE = 0.10
AUTO_DECREASE = 0.45


class AutoGain:
    """Ganancia visual suavizada para señales débiles.

    La ganancia sube despacio (para no bombear con cada sílaba) y baja
    rápido cuando llega una señal fuerte (para no recortar la onda).
    """

    def __init__(
        self,
        gate: float = AUTO_GATE,
        target: float = AUTO_TARGET,
        max_gain: float = AUTO_MAX_GAIN,
    ) -> None:
        self.gate = gate
        self.target = target
        self.max_gain = max_gain
        self.gain = 1.0

    def update(self, level: float) -> float:
        if level >= self.gate:
            wanted = min(self.max_gain, max(1.0, self.target / level))
            rate = AUTO_DECREASE if wanted < self.gain else AUTO_INCREASE
            self.gain += (wanted - self.gain) * rate
            self.gain = max(1.0, min(self.max_gain, self.gain))
        return self.gain

    def reset(self) -> None:
        self.gain = 1.0


class AudioScope(tk.Canvas):
    """Forma de onda en tiempo real con rejilla y lectura de pico."""

    def __init__(self, parent, height: int = 240) -> None:
        super().__init__(
            parent,
            height=height,
            bg=SURFACE,
            highlightthickness=0,
            bd=0,
        )
        self._samples: array | None = None
        self._peak = 0.0
        self._active = False
        self._auto = AutoGain()
        self.bind("<Configure>", lambda _event: self.render())

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def update_samples(self, samples: Sequence[int] | None) -> None:
        self._samples = samples if samples else None
        self._active = bool(samples)
        self._peak = peak(samples) if samples else 0.0
        self._auto.update(self._peak)
        self.render()

    def clear(self) -> None:
        self._samples = None
        self._peak = 0.0
        self._active = False
        self._auto.reset()
        self.render()

    @property
    def auto_gain(self) -> float:
        """Factor de ganancia visual actual (útil para pruebas)."""
        return self._auto.gain

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def render(self) -> None:
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 30 or height < 30:
            return

        self.delete("all")
        rounded_rectangle(
            self,
            1,
            1,
            width - 1,
            height - 1,
            radius=14,
            fill=SCOPE_BG,
            outline=BORDER,
            width=1,
        )

        left = 22
        right = width - 22
        top = 38
        bottom = height - 34
        if bottom - top < 24:
            top = 18
            bottom = height - 18
        middle = (top + bottom) / 2.0
        amplitude = (bottom - top) / 2.0

        self._draw_grid(left, right, top, bottom, middle)
        if self._samples is None or not self._active:
            self.create_text(
                (left + right) / 2.0,
                middle,
                text="Sin señal",
                fill=DISABLED,
                font=(FONT, 8),
            )
        else:
            self._draw_waveform(left, right, middle, amplitude)

        self._draw_readings(left, right, height)

    def _draw_grid(
        self,
        left: float,
        right: float,
        top: float,
        bottom: float,
        middle: float,
    ) -> None:
        for step in range(5):
            y = top + (bottom - top) * step / 4.0
            color = GRID_STRONG if step == 2 else GRID
            self.create_line(left, y, right, y, fill=color)
        for step in range(1, 8):
            x = left + (right - left) * step / 8.0
            self.create_line(x, top, x, bottom, fill=GRID, dash=(2, 6))
        self.create_line(left, middle, right, middle, fill=BORDER_STRONG)

    def _draw_waveform(
        self, left: float, right: float, middle: float, amplitude: float
    ) -> None:
        width = max(2, int((right - left) / 2))
        lows, highs = envelope(self._samples, width)
        count = len(lows)
        if count == 0:
            return

        span = right - left
        xs = [
            left + (span * index / (count - 1) if count > 1 else span / 2.0)
            for index in range(count)
        ]
        gain = self._auto.gain
        top_y: list[float] = []
        bottom_y: list[float] = []
        for index in range(count):
            high = max(-1.0, min(1.0, highs[index] / 32768.0 * gain))
            low = max(-1.0, min(1.0, lows[index] / 32768.0 * gain))
            top_y.append(middle - high * amplitude)
            bottom_y.append(middle - low * amplitude)

        if count == 1:
            self.create_line(
                xs[0],
                top_y[0],
                xs[0],
                bottom_y[0],
                fill=SCOPE_LINE,
                width=2,
            )
            return

        polygon: list[float] = []
        for index in range(count):
            polygon.extend((xs[index], top_y[index]))
        for index in range(count - 1, -1, -1):
            polygon.extend((xs[index], bottom_y[index]))
        self.create_polygon(polygon, fill=SCOPE_FILL, outline="")

        top_points: list[float] = []
        bottom_points: list[float] = []
        for index in range(count):
            top_points.extend((xs[index], top_y[index]))
            bottom_points.extend((xs[index], bottom_y[index]))

        # Un trazo más ancho y oscuro hace de resplandor sin necesitar alfa.
        self.create_line(*top_points, fill=SCOPE_GLOW, width=3)
        self.create_line(*bottom_points, fill=SCOPE_GLOW, width=3)
        self.create_line(*top_points, fill=SCOPE_LINE, width=1)
        self.create_line(*bottom_points, fill=SCOPE_LINE, width=1)

    def _draw_readings(self, left: float, right: float, height: float) -> None:
        gain = self._auto.gain
        scale_text = f"AUTO ×{gain:.1f}"
        if self._peak > 1e-6:
            decibels = 20.0 * math.log10(self._peak)
            if abs(decibels) < 0.05:
                decibels = 0.0
            peak_text = f"PICO {decibels:.1f} dBFS"
        else:
            peak_text = "PICO -∞ dBFS"

        self.create_text(
            left,
            18,
            anchor="w",
            text=scale_text,
            fill=ACCENT,
            font=(FONT, 7, "bold"),
        )
        self.create_text(
            right,
            18,
            anchor="e",
            text=peak_text,
            fill=MUTED,
            font=(FONT, 7, "bold"),
        )

        rate = DEFAULT_AUDIO.rate / 1000.0
        channels = "MONO" if DEFAULT_AUDIO.channels == 1 else "ESTÉREO"
        footer_left = f"{rate:.1f} kHz · {channels}"
        footer_right = f"{DEFAULT_AUDIO.chunk:,} muestras".replace(",", " ")
        self.create_text(
            left,
            height - 16,
            anchor="w",
            text=footer_left,
            fill=DISABLED,
            font=(FONT, 7),
        )
        self.create_text(
            right,
            height - 16,
            anchor="e",
            text=footer_right,
            fill=DISABLED,
            font=(FONT, 7),
        )
