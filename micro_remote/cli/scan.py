"""Búsqueda de receptores desde la consola."""

from __future__ import annotations

import argparse

from ..config import DEFAULT_PORT, DISCOVERY_TIMEOUT
from ..net import find_peers


def run(args: argparse.Namespace) -> int:
    """Lista los receptores visibles en la red local."""
    print("Buscando receptores (descubrimiento UDP)…")
    timeout = args.timeout if args.timeout is not None else DISCOVERY_TIMEOUT
    port = args.port if args.port is not None else DEFAULT_PORT
    peers = find_peers(
        timeout=timeout,
        sweep=not args.no_sweep,
        default_port=port,
        on_stage=lambda text: print(f"  {text}"),
    )

    if not peers:
        print(
            "\nSin resultados. Comprueba que el receptor esté en marcha y que "
            "el firewall permita UDP en los puertos 5000/5001."
        )
        return 1

    print(f"\n{len(peers)} receptor(es):\n")
    print(f"  {'IP':<16} {'PUERTO':<8} NOMBRE")
    print(f"  {'-' * 16} {'-' * 8} {'-' * 30}")
    for peer in peers:
        print(f"  {peer.ip:<16} {peer.port:<8} {peer.name or '—'}")
    print()
    return 0
