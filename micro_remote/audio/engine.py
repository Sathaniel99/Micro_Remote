"""Ciclo de vida compartido de los motores de audio.

Un motor vive en su propio hilo, publica su estado en atributos simples y
nunca toca Tkinter. La interfaz consulta esos atributos desde el hilo
principal; los errores se traducen con :func:`friendly_error`.

Cada sesión tiene una generación propia: el socket se registra con esa
generación y solo el hilo que lo creó lo cierra. Así, un reinicio rápido no
puede hacer que el hilo anterior cierre el socket de la sesión nueva.
"""

from __future__ import annotations

import socket
import threading
import time
from array import array
from dataclasses import dataclass

from ..config import DEFAULT_AUDIO, DEFAULT_GAIN, AudioConfig
from .backend import friendly_error


@dataclass(frozen=True, slots=True)
class EngineStats:
    """Instantánea de contadores para la interfaz y la consola."""

    packets: int = 0
    lost: int = 0
    late: int = 0
    bytes_total: int = 0
    seconds: float = 0.0
    overflows: int = 0
    underflows: int = 0
    unique: int | None = None

    @property
    def kbps(self) -> float:
        if self.seconds <= 0.01:
            return 0.0
        return (self.bytes_total * 8 / 1000.0) / self.seconds

    @property
    def loss_ratio(self) -> float:
        received = self.packets if self.unique is None else self.unique
        expected = received + self.lost
        return self.lost / expected if expected else 0.0


class AudioEngine:
    """Base común de emisor y receptor."""

    def __init__(
        self,
        config: AudioConfig = DEFAULT_AUDIO,
        gain: float = DEFAULT_GAIN,
    ) -> None:
        self.config = config
        self.gain = float(gain)
        self.error: str | None = None
        self.level = 0.0
        self.peak = 0.0
        self.wave: array | None = None
        self.packets = 0
        self.unique_packets = 0
        self.lost = 0
        self.late = 0
        self.bytes_total = 0
        self.overflows = 0
        self.underflows = 0

        self._stop_event = threading.Event()
        self._active = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._generation = 0
        self._sockets: dict[int, socket.socket] = {}
        self._started_at = 0.0
        self._ended_at = 0.0

    # ------------------------------------------------------------------
    # Propiedades y ciclo de vida
    # ------------------------------------------------------------------
    @property
    def running(self) -> bool:
        """``True`` mientras el hilo de audio esté activo."""
        return self._active.is_set()

    def start(self, *args, **kwargs) -> None:
        """Arranca el hilo de audio con los argumentos del motor concreto."""
        with self._lock:
            if self.running:
                return
            self._stop_event.clear()
            self._active.clear()
            self.error = None
            self.level = 0.0
            self.peak = 0.0
            self.wave = None
            self.packets = 0
            self.unique_packets = 0
            self.lost = 0
            self.late = 0
            self.bytes_total = 0
            self.overflows = 0
            self.underflows = 0
            self._started_at = 0.0
            self._ended_at = 0.0
            self._generation += 1
            generation = self._generation
            self._thread = threading.Thread(
                target=self._run_guarded,
                args=(generation, *args),
                kwargs=kwargs,
                daemon=True,
                name=type(self).__name__.lower(),
            )
            thread = self._thread
        thread.start()

    def _run_guarded(self, generation: int, *args, **kwargs) -> None:
        self._active.set()
        self._started_at = time.monotonic()
        try:
            self._run(*args, generation=generation, **kwargs)
        except Exception as exc:  # noqa: BLE001 - se informa en la interfaz
            if generation == self._generation and not self._stop_event.is_set():
                self.error = friendly_error(exc)
        finally:
            if generation == self._generation:
                self._ended_at = time.monotonic()
                self._active.clear()
            self._release(generation)

    def _run(self, *args, **kwargs) -> None:  # pragma: no cover - abstracto
        raise NotImplementedError

    def stop(self, timeout: float = 3.0) -> None:
        """Solicita la parada y espera a que el hilo libere los recursos."""
        self._stop_event.set()
        self._close_socket()
        with self._lock:
            thread = self._thread
            if (
                thread
                and thread.is_alive()
                and thread is not threading.current_thread()
            ):
                thread.join(timeout)
            if thread is None or not thread.is_alive():
                self._thread = None

    def _release(self, generation: int) -> None:
        self._close_socket(generation)

    def _register_socket(self, generation: int, sock: socket.socket) -> None:
        """Asocia un socket a una generación para poder cerrarlo con precisión."""
        with self._lock:
            previous = self._sockets.get(generation)
            self._sockets[generation] = sock
        if previous is not None and previous is not sock:
            self._close_socket_object(previous)

    def _close_socket(self, generation: int | None = None) -> None:
        """Cierra el socket de una generación, o todos si no se indica."""
        with self._lock:
            if generation is None:
                sockets = list(self._sockets.values())
                self._sockets.clear()
            else:
                sock = self._sockets.pop(generation, None)
                sockets = [sock] if sock is not None else []
        for sock in sockets:
            self._close_socket_object(sock)

    @staticmethod
    def _close_socket_object(sock: socket.socket) -> None:
        try:
            sock.close()
        except OSError:
            pass

    def stats(self) -> EngineStats:
        """Contadores actuales y duración de la sesión."""
        end = self._ended_at or time.monotonic()
        seconds = max(0.0, end - self._started_at) if self._started_at else 0.0
        return EngineStats(
            packets=self.packets,
            lost=self.lost,
            late=self.late,
            bytes_total=self.bytes_total,
            seconds=seconds,
            overflows=self.overflows,
            underflows=self.underflows,
            unique=self.unique_packets,
        )
