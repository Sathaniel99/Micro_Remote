"""Utilidades de dibujo compartidas por los Canvas de la interfaz."""

from __future__ import annotations

import tkinter as tk


def rounded_rectangle(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float = 12,
    **kwargs,
) -> int:
    """Dibuja un rectángulo redondeado y devuelve su identificador de Canvas."""
    radius = max(0.0, min(float(radius), (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    points = (
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    )
    return canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=24,
        **kwargs,
    )
