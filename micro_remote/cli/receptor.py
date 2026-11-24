"""Receptor de audio sin interfaz gráfica."""

from __future__ import annotations

import argparse
import time

from .. import formatting
from ..audio import Receiver
from ..config import DEFAULT_AUDIO, DEFAULT_PORT
from ..net import is_valid_port
from ..settings import Settings


def run(args: argparse.Namespace) -> int:
    """Escucha paquetes UDP hasta Ctrl+C o hasta agotar ``--duration``."""
    settings = Settings.load(role="receptor")
    port = args.port if args.port is not None else settings.port
    gain = args.gain if args.gain is not None else settings.gain
    device = args.device if args.device is not None else settings.output_device

    if not is_valid_port(port):
        print(f"✗ Puerto no válido: {port!r}")
        return 2

    receiver = Receiver(DEFAULT_AUDIO, gain=gain)
    print(f"Receptor · escuchando en 0.0.0.0:{port} · "
          f"volumen {gain:.1f}x")
    print("Ctrl+C para detener.\n")

    receiver.start(port, device)
    started = time.monotonic()
    try:
        while True:
            time.sleep(0.4)
            if receiver.error:
                print(f"\n✗ {receiver.error}")
                return 1

            stats = receiver.stats()
            elapsed = time.monotonic() - started
            source = receiver.source or "esperando…"
            line = (
                f"\r{stats.packets:>8,} recibidos · "
                f"{stats.lost:>5,} perdidos · "
                f"{formatting.format_bitrate(stats.kbps):>10} · "
                f"{source:>22}"
            )
            print(line.ljust(88), end="", flush=True)

            if args.duration and elapsed >= args.duration:
                print("\nDuración alcanzada.")
                break
            if not receiver.running and elapsed > 1.0:
                print("\nLa recepción se detuvo.")
                return 1
    except KeyboardInterrupt:
        print("\nDeteniendo…")
    finally:
        receiver.stop()
        stats = receiver.stats()
        print(
            f"Resumen: {stats.packets:,} paquetes · {stats.lost:,} perdidos · "
            f"{formatting.format_bytes(stats.bytes_total)}"
        )
    return 0
