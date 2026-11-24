"""Persistencia de preferencias del usuario en JSON.

Cada aplicación guarda su propio archivo (``settings-emisor.json`` y
``settings-receptor.json``) para que una no sobrescriba los ajustes de la
otra. Ubicación por defecto: ``%APPDATA%/MicroRemote`` en Windows y
``~/.config/MicroRemote`` en el resto. La variable de entorno
``MICRO_REMOTE_HOME`` permite usar otra carpeta (útil en pruebas).
"""

from __future__ import annotations

import json
import math
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import (
    DEFAULT_GAIN,
    DEFAULT_PORT,
    MAX_GAIN,
    MIN_GAIN,
    SETTINGS_DIRNAME,
    SETTINGS_ENV_VAR,
    SETTINGS_FILENAME,
    SETTINGS_ROLES,
)
from .net import is_valid_ipv4, is_valid_port


def settings_dir() -> Path:
    """Carpeta donde se guardan los ajustes."""
    override = os.environ.get(SETTINGS_ENV_VAR)
    if override:
        return Path(override).expanduser()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / SETTINGS_DIRNAME
    return Path.home() / ".config" / SETTINGS_DIRNAME


def _role_name(role: str | None) -> str | None:
    if role is None:
        return None
    name = str(role).strip().lower()
    if name not in SETTINGS_ROLES:
        raise ValueError(f"Rol de ajustes desconocido: {role!r}")
    return name


def settings_path(role: str | None = None) -> Path:
    """Ruta del archivo de ajustes; ``role`` separa emisor y receptor."""
    name = SETTINGS_FILENAME
    role = _role_name(role)
    if role is not None:
        path = Path(SETTINGS_FILENAME)
        name = f"{path.stem}-{role}{path.suffix or '.json'}"
    return settings_dir() / name


def _clamp_gain(value: object) -> float:
    try:
        gain = float(value)
    except (TypeError, ValueError):
        return DEFAULT_GAIN
    if not math.isfinite(gain):
        return DEFAULT_GAIN
    return max(MIN_GAIN, min(MAX_GAIN, gain))


def _clean_device(value: object) -> int | None:
    if value is None:
        return None
    try:
        index = int(value)
    except (TypeError, ValueError):
        return None
    return index if index >= 0 else None


@dataclass
class Settings:
    """Preferencias de una aplicación (emisor o receptor)."""

    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    gain: float = DEFAULT_GAIN
    input_device: int | None = None
    output_device: int | None = None

    # ------------------------------------------------------------------
    # Carga y guardado
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path | None = None, *, role: str | None = None) -> "Settings":
        """Lee los ajustes ignorando cualquier dato inválido.

        Si no existe el archivo del rol, se intenta migrar del antiguo
        ``settings.json`` compartido.
        """
        target = path if path is not None else settings_path(role)
        if path is None and role is not None and not target.exists():
            legacy = settings_path()
            if legacy.is_file():
                target = legacy
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(raw, dict):
            return cls()

        settings = cls()
        host = raw.get("host")
        if isinstance(host, str) and is_valid_ipv4(host):
            settings.host = host.strip()

        port = raw.get("port")
        if is_valid_port(port):
            settings.port = int(port)

        settings.gain = _clamp_gain(raw.get("gain", DEFAULT_GAIN))
        settings.input_device = _clean_device(raw.get("input_device"))
        settings.output_device = _clean_device(raw.get("output_device"))
        return settings

    def save(self, path: Path | None = None, *, role: str | None = None) -> Path:
        """Escribe los ajustes de forma atómica. Devuelve la ruta usada."""
        target = path if path is not None else settings_path(role)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(
            f"{target.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return target
