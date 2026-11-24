"""Protocolo de paquetes de audio sobre UDP.

Cada paquete lleva una cabecera de 8 bytes::

    +--------+---------+--------+------------------+---------------------+
    | magic  | version | flags  | secuencia (u32)  | PCM int16 LE ...    |
    | 2 B    | 1 B     | 1 B    | 4 B              | n B                 |
    +--------+--------+--------+------------------+---------------------+

La secuencia permite al receptor detectar paquetes perdidos o duplicados.
Si un datagrama no empieza por ``b"MR"`` se interpreta como PCM "heredado"
(sin cabecera); así un emisor antiguo sigue pudiendo alimentar al receptor
nuevo, y cualquier prueba manual con ``netcat`` o similar funciona.
"""

from __future__ import annotations

import struct
from collections import deque
from dataclasses import dataclass

MAGIC = b"MR"
VERSION = 1
HEADER_STRUCT = struct.Struct("!2sBBI")
HEADER_SIZE = HEADER_STRUCT.size  # 8
MAX_SEQUENCE = 0xFFFFFFFF
LEGACY_SEQUENCE = -1
MAX_DATAGRAM_BYTES = 65507  # carga útil máxima de un datagrama UDP IPv4
MAX_PAYLOAD_BYTES = MAX_DATAGRAM_BYTES - HEADER_SIZE
TRACK_WINDOW = 4096  # secuencias recordadas para detectar duplicados/tardíos


@dataclass(frozen=True, slots=True)
class AudioPacket:
    """Paquete recibido: secuencia (``-1`` si es heredado) y carga PCM."""

    sequence: int
    payload: bytes
    legacy: bool = False


def build_packet(sequence: int, payload: bytes) -> bytes:
    """Construye un datagrama listo para enviar."""
    if len(payload) % 2 or len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("La carga PCM debe ser par y caber en un datagrama UDP")
    header = HEADER_STRUCT.pack(MAGIC, VERSION, 0, sequence & MAX_SEQUENCE)
    return header + payload


def parse_packet(data: bytes) -> AudioPacket | None:
    """Interpreta un datagrama.

    Devuelve ``None`` si está vacío, tiene longitud impar, supera el tamaño
    UDP, usa una versión desconocida o no contiene audio utilizable.
    """
    if len(data) < 2 or len(data) > MAX_DATAGRAM_BYTES:
        return None
    if data[:2] == MAGIC:
        if len(data) < HEADER_SIZE:
            return None
        magic, version, _flags, sequence = HEADER_STRUCT.unpack_from(data)
        if magic != MAGIC or version != VERSION:
            return None
        payload = data[HEADER_SIZE:]
        if not payload or len(payload) % 2:
            return None
        return AudioPacket(sequence=sequence, payload=payload)

    # Formato heredado: PCM crudo sin cabecera, siempre de longitud par.
    if len(data) % 2:
        return None
    return AudioPacket(sequence=LEGACY_SEQUENCE, payload=data, legacy=True)


class SequenceTracker:
    """Contabiliza paquetes recibidos, perdidos, tardíos y duplicados.

    Mantiene una ventana limitada de secuencias vistas y de huecos contados,
    de modo que un paquete tardío descuenta la pérdida que se registró cuando
    se detectó el salto, y los duplicados no inflan el denominador de pérdida.
    """

    __slots__ = (
        "_last",
        "_seen",
        "_seen_set",
        "_missing",
        "_missing_set",
        "received",
        "unique",
        "lost",
        "late",
        "duplicates",
    )

    def __init__(self) -> None:
        self._last: int | None = None
        self._seen: deque[int] = deque(maxlen=TRACK_WINDOW)
        self._seen_set: set[int] = set()
        self._missing: deque[int] = deque(maxlen=TRACK_WINDOW)
        self._missing_set: set[int] = set()
        self.received = 0
        self.unique = 0
        self.lost = 0
        self.late = 0
        self.duplicates = 0

    @staticmethod
    def _remember(sequence: int, queue: deque[int], seen: set[int]) -> None:
        if len(queue) == queue.maxlen:
            seen.discard(queue[0])
        queue.append(sequence)
        seen.add(sequence)

    def _remember_missing(self, first: int, count: int) -> None:
        if count > TRACK_WINDOW:
            return
        for offset in range(count):
            self._remember(
                (first + offset) & MAX_SEQUENCE, self._missing, self._missing_set
            )

    def update(self, sequence: int) -> str:
        """Registra una secuencia y devuelve su clasificación.

        Valores posibles: ``"ok"``, ``"lost"`` (hubo un salto),
        ``"duplicate"``, ``"late"`` (llegó fuera de orden) o ``"legacy"``.
        """
        self.received += 1
        if sequence < 0:
            self.unique += 1
            return "legacy"

        if sequence in self._seen_set:
            self.duplicates += 1
            return "duplicate"

        if sequence in self._missing_set:
            self._missing_set.discard(sequence)
            self.lost = max(0, self.lost - 1)
            self.late += 1
            self.unique += 1
            self._remember(sequence, self._seen, self._seen_set)
            return "late"

        self.unique += 1
        self._remember(sequence, self._seen, self._seen_set)

        if self._last is None:
            self._last = sequence
            return "ok"

        delta = (sequence - self._last) & MAX_SEQUENCE
        if delta < 0x80000000:  # avance normal (con posible salto)
            if delta > 1:
                self._remember_missing((self._last + 1) & MAX_SEQUENCE, delta - 1)
                self.lost += delta - 1
                self._last = sequence
                return "lost"
            self._last = sequence
            return "ok"

        # La secuencia es anterior a la última vista: paquete reordenado.
        self.late += 1
        return "late"

    @property
    def loss_ratio(self) -> float:
        """Proporción de paquetes perdidos respecto a los esperados únicos."""
        expected = self.unique + self.lost
        return self.lost / expected if expected else 0.0
