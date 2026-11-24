"""Configuración de ventanas Tkinter: tamaño, centrado e icono."""

from __future__ import annotations

import tkinter as tk

from ..config import MIN_WINDOW_SIZE, WINDOW_SIZE
from ..resources import icon_path
from .theme import BG


def center_window(
    root: tk.Tk,
    width: int,
    height: int,
    min_size: tuple[int, int] = MIN_WINDOW_SIZE,
) -> tuple[int, int]:
    """Centra la ventana y la limita al tamaño de la pantalla.

    Devuelve el tamaño final aplicado (puede ser menor que el solicitado en
    pantallas pequeñas).
    """
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    width = min(width, max(520, screen_width - 60))
    height = min(height, max(400, screen_height - 90))
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)

    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(min(min_size[0], width), min(min_size[1], height))
    root.resizable(True, True)
    return width, height


def apply_icon(root: tk.Tk, icon_name: str) -> None:
    """Aplica el icono de la ventana si el archivo existe.

    ``iconbitmap(default=...)`` también afecta a los diálogos nativos.
    """
    path = icon_path(icon_name)
    if path is None:
        return
    try:
        root.iconbitmap(default=str(path))
    except tk.TclError:
        pass


def configure_window(
    root: tk.Tk,
    title: str,
    icon_name: str,
    size: tuple[int, int] = WINDOW_SIZE,
    min_size: tuple[int, int] = MIN_WINDOW_SIZE,
) -> None:
    """Título, color de fondo, geometría centrada e icono."""
    root.title(title)
    root.configure(bg=BG)
    center_window(root, size[0], size[1], min_size)
    apply_icon(root, icon_name)
