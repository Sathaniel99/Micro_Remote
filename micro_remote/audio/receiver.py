"""Receptor: escucha paquetes UDP y los reproduce en los altavoces."""

from __future__ import annotations

import socket

from ..config import DEFAULT_AUDIO, DEFAULT_GAIN, DEFAULT_PORT, AudioConfig
from ..dsp import apply_gain, pcm_from_bytes, pcm_to_native, peak, rms
from ..protocol import SequenceTracker, parse_packet
from .backend import close_stream, load_sounddevice
from .engine import AudioEngine


class Receiver(AudioEngine):
    """Recibe paquetes UDP y los reproduce en los altavoces."""

    def __init__(
        self,
        config: AudioConfig = DEFAULT_AUDIO,
        gain: float = DEFAULT_GAIN,
    ) -> None:
        super().__init__(config=config, gain=gain)
        self.source: str | None = None

    def start(self, port: int = DEFAULT_PORT, device: int | None = None) -> None:
        """Escucha en ``port`` y reproduce por ``device`` (o el predeterminado)."""
        if not self.running:
            self.source = None
        super().start(int(port), device)

    def _run(
        self, port: int, device: int | None, *, generation: int
    ) -> None:
        sd = load_sounddevice()
        stream = None
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._register_socket(generation, sock)
        try:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
            except OSError:
                pass
            sock.bind(("", port))
            sock.settimeout(0.4)

            stream = sd.RawOutputStream(
                samplerate=self.config.rate,
                blocksize=self.config.chunk,
                device=device,
                channels=self.config.channels,
                dtype="int16",
            )
            stream.start()

            tracker = SequenceTracker()
            while (
                not self._stop_event.is_set()
                and generation == self._generation
            ):
                try:
                    data, address = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop_event.is_set() or generation != self._generation:
                        break
                    raise

                packet = parse_packet(data)
                if packet is None:
                    continue
                tracker.update(packet.sequence)
                self.lost = tracker.lost
                self.late = tracker.late
                self.unique_packets = tracker.unique

                samples = pcm_from_bytes(packet.payload)
                if not samples:
                    continue
                gained = apply_gain(samples, self.gain)
                self.source = f"{address[0]}:{address[1]}"
                self.wave = gained
                self.level = rms(gained)
                self.peak = peak(gained)
                underflowed = stream.write(pcm_to_native(gained))
                if underflowed:
                    self.underflows += 1
                self.packets += 1
                self.bytes_total += len(packet.payload)
        finally:
            close_stream(stream)
