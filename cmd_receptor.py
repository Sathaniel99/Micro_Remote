"""Receptor de consola (compatibilidad con ``cmd_receptor.py`` de la v1).

Equivale a::

    python -m micro_remote receptor --cli
"""

from __future__ import annotations

import sys

from micro_remote.__main__ import main

if __name__ == "__main__":
    sys.exit(main(["receptor", "--cli", *sys.argv[1:]]))
