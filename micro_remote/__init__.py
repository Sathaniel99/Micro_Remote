"""Micro Remote: streaming de audio en vivo por UDP para redes locales.

El paquete está organizado en capas:

* ``micro_remote`` (raíz)   lógica pura: audio, red, protocolo, ajustes.
* ``micro_remote.ui``       interfaz Tkinter (emisor y receptor).
* ``micro_remote.cli``      versiones sin interfaz para pruebas/automatización.

Los módulos de lógica no importan Tkinter y ``sounddevice`` sólo se carga
cuando se abre un dispositivo, de modo que el paquete se puede importar y
probar en equipos sin tarjeta de sonido.
"""

from .config import APP_NAME, APP_VERSION

__all__ = ["APP_NAME", "APP_VERSION"]
__version__ = APP_VERSION
