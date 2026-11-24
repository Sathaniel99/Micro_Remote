"""Localización de recursos (iconos, documentación) en desarrollo y empaquetado."""

from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Carpeta raíz de la aplicación.

    En desarrollo es la carpeta que contiene ``micro_remote/``. Cuando el
    programa corre desde un ejecutable de PyInstaller es ``sys._MEIPASS``.
    """
    bundled = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and bundled:
        return Path(bundled)
    return Path(__file__).resolve().parent.parent


def asset_path(*parts: str) -> Path:
    """Ruta absoluta a un recurso dentro de la carpeta de la aplicación."""
    return app_root().joinpath(*parts)


def icon_path(name: str) -> Path | None:
    """Busca un icono ``.ico`` y devuelve su ruta, o ``None`` si no existe."""
    for candidate in (
        asset_path("icons", "ico", name),
        asset_path("icons", name),
        Path(__file__).resolve().parent / "assets" / name,
    ):
        if candidate.is_file():
            return candidate
    return None
