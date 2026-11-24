"""Emisor de audio sin interfaz gráfica."""

from __future__ import annotations

import argparse
import time

from .. import formatting
from ..audio import Sender
from ..config import DEFAULT_AUDIO, DEFAULT_PORT
from ..net import is_valid_port, normalize_ipv4
from ..settings import Settings


def run(args: argparse.Namespace) -> int:
    """Ejecuta el emisor hasta Ctrl+C o hasta agotar ``--duration``."""
    settings = Settings.load(role="emisor")
    port = args.port if args.port is not None else settings.port
    gain = args.gain if args.gain is not None else settings.gain
    device = args.device if args.device is not None else settings.input_device

    host = normalize_ipv4(args.host)
    if host is None:
        print(f"✗ IP de receptor no válida: {args.host!r}")
        return 2
    if not is_valid_port(port):
        print(f"✗ Puerto no válido: {port!r}")
        return 2

    sender = Sender(DEFAULT_AUDIO, gain=gain)
    print(f"Emisor · {DEFAULT_AUDIO.rate} Hz · {DEFAULT_AUDIO.chunk} muestras "
          f"({DEFAULT_AUDIO.packet_ms:.0f} ms)")
    print(f"Destino: {host}:{port} · ganancia {gain:.1f}x")
    print("Ctrl+C para detener.\n")

    sender.start(host, port, device)
    started = time.monotonic()
    try:
        while True:
            time.sleep(0.4)
            if sender.error:
                print(f"\n✗ {sender.error}")
                return 1

            stats = sender.stats()
            elapsed = time.monotonic() - started
            line = (
                f"\r{stats.packets:>8,} paquetes · "
                f"{formatting.format_bitrate(stats.kbps):>10} · "
                f"{formatting.format_duration(stats.seconds):>8}"
            )
            print(line.ljust(60), end="", flush=True)

            if args.duration and elapsed >= args.duration:
                print("\nDuración alcanzada.")
                break
            if not sender.running and elapsed > 1.0:
                print("\nLa captura de audio se detuvo.")
                return 1
    except KeyboardInterrupt:
        print("\nDeteniendo…")
    finally:
        sender.stop()
    return 0
