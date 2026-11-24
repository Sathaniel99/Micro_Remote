"""Emisor de consola (compatibilidad con ``cmd_emisor.py`` de la v1).

Equivale a::

    python -m micro_remote emisor --cli --host <IP>

Se acepta también la forma posicional antigua ``python cmd_emisor.py <IP>``.
"""

from __future__ import annotations

import sys

from micro_remote.__main__ import main


def build_argv(argv: list[str]) -> list[str]:
    """Convierte la IP posicional de la v1 en ``--host``."""
    arguments = list(argv)
    if arguments and not arguments[0].startswith("-"):
        arguments = ["--host", arguments[0], *arguments[1:]]
    return arguments


if __name__ == "__main__":
    sys.exit(main(["emisor", "--cli", *build_argv(sys.argv[1:])]))
