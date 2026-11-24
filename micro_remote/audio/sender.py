"""Emisor: captura el micrófono y envía paquetes UDP."""

from __future__ import annotations

import socket

from ..config import DEFAULT_AUDIO, DEFAULT_GAIN, DEFAULT_PORT, AudioConfig
from ..dsp import apply_gain, pcm_from_native, pcm_to_bytes, peak, rms
from ..protocol import build_packet
from .backend import close_stream, load_sounddevice
from .engine import AudioEngine


class Sender(AudioEngine):
    """Captura el micrófono y envía paquetes UDP al receptor."""

    def __init__(
        self,
        config: AudioConfig = DEFAULT_AUDIO,
        gain: float = DEFAULT_GAIN,
    ) -> None:
        super().__init__(config=config, gain=gain)
        self.destination: tuple[str, int] | None = None

    def start(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        device: int | None = None,
    ) -> None:
        """Abre el micrófono y comienza a transmitir a ``host:port``."""
        if not self.running:
            self.destination = (host, int(port))
        super().start(host, int(port), device)

    def _run(
        self, host: str, port: int, device: int | None, *, generation: int
    ) -> None:
        sd = load_sounddevice()
        stream = None
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._register_socket(generation, sock)
        try:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 18)
            except OSError:
                pass

            stream = sd.RawInputStream(
                samplerate=self.config.rate,
                blocksize=self.config.chunk,
                device=device,
                channels=self.config.channels,
                dtype="int16",
            )
            stream.start()

            sequence = 0
            while (
                not self._stop_event.is_set()
                and generation == self._generation
            ):
                data, overflowed = stream.read(self.config.chunk)
                if overflowed:
                    self.overflows += 1

                samples = pcm_from_native(bytes(data))
                if not samples:
                    continue
                gained = apply_gain(samples, self.gain)
                self.wave = gained
                self.level = rms(gained)
                self.peak = peak(gained)

                payload = pcm_to_bytes(gained)
                sock.sendto(build_packet(sequence, payload), (host, port))
                sequence = (sequence + 1) & 0xFFFFFFFF
                self.packets += 1
                self.unique_packets = self.packets
                self.bytes_total += len(payload)
        finally:
            close_stream(stream)
