"""Genera los iconos ``.ico`` del proyecto.

Uso::

    python convert_to_ico.py

La implementación está en :mod:`micro_remote.tools.icons` y requiere Pillow.
"""

from __future__ import annotations

import sys

from micro_remote.tools.icons import main

if __name__ == "__main__":
    sys.exit(main())
