"""Formato de magnitudes para la interfaz y la consola."""

from __future__ import annotations

import math


def format_gain(value: float) -> str:
    """``1`` -> ``"1.0x"``."""
    return f"{float(value):.1f}x"


def format_level(level: float) -> str:
    """Nivel normalizado 0..1 a decibelios relativos a fondo de escala."""
    level = max(0.0, min(1.0, float(level)))
    if level < 1e-5:
        return "silencio"
    decibels = 20.0 * math.log10(level)
    if abs(decibels) < 0.05:
        decibels = 0.0
    return f"{decibels:.1f} dBFS"


def level_fraction(level: float, floor_db: float = -60.0) -> float:
    """Nivel lineal 0..1 a fracción 0..1 en una escala dBFS.

    El medidor necesita una escala logarítmica: una señal de -40 dBFS es
    perfectamente audible, pero en una barra lineal sólo encendería el 1 %.
    """
    value = max(0.0, min(1.0, float(level)))
    if value <= 0.0:
        return 0.0
    floor = float(floor_db)
    level_db = 20.0 * math.log10(value)
    if floor >= 0.0:
        return 1.0 if level_db >= 0.0 else 0.0
    return max(0.0, min(1.0, (level_db - floor) / -floor))


def format_bitrate(kbps: float) -> str:
    """Bits por segundo legibles."""
    kbps = max(0.0, float(kbps))
    if kbps >= 1000.0:
        return f"{kbps / 1000.0:.2f} Mbps"
    return f"{kbps:.0f} kbps"


def format_duration(seconds: float) -> str:
    """Segundos a ``mm:ss`` o ``h:mm:ss``."""
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_bytes(count: float) -> str:
    """Cantidad de bytes legible (KB, MB, GB)."""
    value = float(max(0.0, count))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} GB"
