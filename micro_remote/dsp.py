"""Procesamiento de PCM de 16 bits sin dependencias externas.

El audio se representa con :class:`array.array` de tipo ``'h'`` (enteros de
16 bits con signo). Se evita NumPy a propósito: para bloques de 1024 muestras
el coste en Python puro es despreciable y el ejecutable empaquetado pesa
mucho menos.
"""

from __future__ import annotations

import math
import sys
from array import array
from typing import Iterable, Sequence

from .config import DEFAULT_GAIN, MAX_GAIN, MIN_GAIN

INT16_MIN = -32768
INT16_MAX = 32767
FULL_SCALE = 32768.0


def pcm_from_bytes(data: bytes) -> array:
    """Convierte bytes PCM little-endian (red) a un ``array('h')`` local."""
    usable = len(data) - (len(data) % 2)
    samples = array("h")
    if usable <= 0:
        return samples
    samples.frombytes(bytes(data[:usable]))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def pcm_to_bytes(samples: Sequence[int]) -> bytes:
    """Convierte muestras a bytes PCM little-endian listos para la red."""
    if not isinstance(samples, array):
        samples = array("h", samples)
    if sys.byteorder == "little":
        return samples.tobytes()
    copy = array("h", samples)
    copy.byteswap()
    return copy.tobytes()


def pcm_from_native(data: bytes) -> array:
    """Convierte bytes PCM en el orden de bytes nativo del equipo.

    Es lo que entrega ``sounddevice`` al leer el micrófono.
    """
    usable = len(data) - (len(data) % 2)
    samples = array("h")
    if usable > 0:
        samples.frombytes(bytes(data[:usable]))
    return samples


def pcm_to_native(samples: Sequence[int]) -> bytes:
    """Convierte muestras al orden de bytes que espera la tarjeta de sonido."""
    if not isinstance(samples, array):
        samples = array("h", samples)
    return samples.tobytes()


def apply_gain(samples: Sequence[int], gain: float) -> array:
    """Multiplica las muestras por ``gain`` recortando a 16 bits.

    Un valor de ``1.0`` devuelve la misma secuencia sin copiarla.
    """
    gain = float(gain)
    if not math.isfinite(gain):
        gain = DEFAULT_GAIN
    gain = max(MIN_GAIN, min(MAX_GAIN, gain))
    if gain == 1.0:
        return samples if isinstance(samples, array) else array("h", samples)
    if gain <= 0.0:
        return array("h", bytes(len(samples) * 2))
    result = array("h")
    append = result.append
    for sample in samples:
        value = int(sample * gain)
        if value > INT16_MAX:
            value = INT16_MAX
        elif value < INT16_MIN:
            value = INT16_MIN
        append(value)
    return result


def rms(samples: Sequence[int]) -> float:
    """Nivel eficaz normalizado entre 0 y 1 (útil para medidores)."""
    if not samples:
        return 0.0
    total = 0
    for sample in samples:
        total += sample * sample
    value = math.sqrt(total / len(samples)) / FULL_SCALE
    return min(1.0, value)


def peak(samples: Sequence[int]) -> float:
    """Valor absoluto máximo normalizado entre 0 y 1."""
    if not samples:
        return 0.0
    largest = 0
    for sample in samples:
        magnitude = -sample if sample < 0 else sample
        if magnitude > largest:
            largest = magnitude
    return min(1.0, largest / FULL_SCALE)


def envelope(samples: Sequence[int], buckets: int) -> tuple[list[int], list[int]]:
    """Reduce la señal a ``buckets`` pares (mínimo, máximo).

    Se usa para dibujar la forma de onda en un ancho de píxeles limitado sin
    perder los picos: cada columna muestra el rango real de la señal.
    """
    total = len(samples)
    if total == 0 or buckets <= 0:
        return [], []
    buckets = min(int(buckets), total)
    lows: list[int] = []
    highs: list[int] = []
    for index in range(buckets):
        start = index * total // buckets
        end = max(start + 1, (index + 1) * total // buckets)
        low = high = samples[start]
        for position in range(start + 1, end):
            value = samples[position]
            if value < low:
                low = value
            if value > high:
                high = value
        lows.append(low)
        highs.append(high)
    return lows, highs


def normalized(samples: Sequence[int]) -> Iterable[float]:
    """Genera las muestras en el rango -1..1 (para visualizaciones)."""
    for sample in samples:
        yield sample / FULL_SCALE
