"""Lanzador de la interfaz del emisor.

Se mantiene en la raíz para que los accesos directos, los ``.spec`` de
PyInstaller y las instrucciones antiguas sigan funcionando. La aplicación
real vive en :mod:`micro_remote.ui.emisor`.
"""

from __future__ import annotations

import sys

from micro_remote.ui.emisor import main


if __name__ == "__main__":
    if sys.argv[1:]:
        from micro_remote.__main__ import main as cli_main

        sys.exit(cli_main(["emisor", *sys.argv[1:]]))
    sys.exit(main())
