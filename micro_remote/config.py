"""Constantes y configuración compartida de Micro Remote."""

from __future__ import annotations

import math
from dataclasses import dataclass

APP_NAME = "Micro Remote"
APP_VERSION = "2.0.0"
APP_TAGLINE = "Audio en vivo por tu red local"

# ---------------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------------
DEFAULT_PORT = 5000
DISCOVERY_PORT = 5001
DISCOVERY_TIMEOUT = 1.5
DISCOVERY_MAGIC = b"MRD1"

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
MIN_GAIN = 0.0
MAX_GAIN = 5.0
DEFAULT_GAIN = 1.0
GAIN_STEP = 0.1


def validate_gain(value: object) -> float:
    """Devuelve una ganancia finita dentro de ``MIN_GAIN``..``MAX_GAIN``."""
    try:
        gain = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("La ganancia debe ser un número") from exc
    if not math.isfinite(gain) or not MIN_GAIN <= gain <= MAX_GAIN:
        raise ValueError(f"La ganancia debe estar entre {MIN_GAIN} y {MAX_GAIN}")
    return gain


def validate_device(value: object) -> int:
    """Devuelve un índice de dispositivo válido (>= 0)."""
    try:
        device = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("El dispositivo debe ser un índice entero") from exc
    if device < 0:
        raise ValueError("El índice de dispositivo no puede ser negativo")
    return device


def validate_duration(value: object) -> float:
    """Devuelve una duración finita y no negativa."""
    try:
        duration = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("La duración debe ser un número") from exc
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("La duración no puede ser negativa ni infinita")
    return duration


def validate_port(value: object) -> int:
    """Devuelve un puerto UDP utilizable (1-65535)."""
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("El puerto debe ser un número entero") from exc
    if not 1 <= port <= 65535:
        raise ValueError("El puerto debe estar entre 1 y 65535")
    return port


@dataclass(frozen=True, slots=True)
class AudioConfig:
    """Parámetros del flujo PCM que comparten emisor y receptor.

    El audio viaja como PCM entero de 16 bits con signo, mono y
    *little-endian*. Un ``chunk`` de 1024 muestras a 44 100 Hz equivale a
    ~23 ms por paquete, un buen equilibrio entre latencia y carga de red.
    """

    rate: int = 44100
    channels: int = 1
    chunk: int = 1024
    sample_width: int = 2

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError("La frecuencia de muestreo debe ser positiva")
        if self.channels <= 0:
            raise ValueError("Debe existir al menos un canal")
        if self.chunk <= 0:
            raise ValueError("El tamaño de bloque debe ser positivo")
        if self.sample_width != 2:
            raise ValueError("Sólo se admite PCM de 16 bits")
        if self.packet_bytes > 65507:
            raise ValueError("El paquete supera el tamaño máximo de un datagrama UDP")

    @property
    def frame_bytes(self) -> int:
        """Bytes que ocupa una muestra de todos los canales."""
        return self.channels * self.sample_width

    @property
    def packet_bytes(self) -> int:
        """Bytes de audio que viajan en un paquete."""
        return self.chunk * self.frame_bytes

    @property
    def packet_ms(self) -> float:
        """Duración en milisegundos de un bloque de audio."""
        return 1000.0 * self.chunk / self.rate


DEFAULT_AUDIO = AudioConfig()

# ---------------------------------------------------------------------------
# Ventana
# ---------------------------------------------------------------------------
WINDOW_SIZE = (1120, 860)
MIN_WINDOW_SIZE = (980, 800)

# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------
SETTINGS_FILENAME = "settings.json"
SETTINGS_DIRNAME = "MicroRemote"
SETTINGS_ENV_VAR = "MICRO_REMOTE_HOME"
SETTINGS_ROLES = ("emisor", "receptor")
