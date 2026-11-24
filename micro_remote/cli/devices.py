"""Listado de dispositivos de audio disponibles."""

from __future__ import annotations

import argparse

from ..audio import AudioError, audio_devices


def _print_group(title: str, devices) -> None:
    print(f"\n{title} ({len(devices)}):")
    if not devices:
        print("  (ninguno)")
        return
    for device in devices:
        default = " · predeterminado" if device.default else ""
        hostapi = f" · {device.hostapi}" if device.hostapi else ""
        print(
            f"  [{device.index:>2}] {device.name} "
            f"({device.channels} canal/es){hostapi}{default}"
        )


def run(_args: argparse.Namespace) -> int:
    """Muestra entradas y salidas detectadas por sounddevice/PortAudio."""
    try:
        inputs = audio_devices("input")
        outputs = audio_devices("output")
    except AudioError as exc:
        print(f"✗ {exc}")
        return 1

    _print_group("Entradas", inputs)
    _print_group("Salidas", outputs)
    print()
    return 0
