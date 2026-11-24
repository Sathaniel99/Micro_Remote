"""Lanzador de la interfaz del receptor.

La aplicación real vive en :mod:`micro_remote.ui.receptor`.
"""

from __future__ import annotations

import sys

from micro_remote.ui.receptor import main


if __name__ == "__main__":
    if sys.argv[1:]:
        from micro_remote.__main__ import main as cli_main

        sys.exit(cli_main(["receptor", *sys.argv[1:]]))
    sys.exit(main())
