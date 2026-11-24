"""Pruebas de la capa de audio (sin tarjeta de sonido ni sounddevice real)."""

from __future__ import annotations

import socket
import sys
import threading
import time
import unittest
from unittest import mock

from micro_remote.audio import Device, EngineStats, Receiver, Sender, friendly_error
from micro_remote.audio import backend
from micro_remote.audio.backend import AudioError, audio_devices
from micro_remote.audio.engine import AudioEngine


class _FakeDefault:
    def __init__(self, pair: tuple[int, int]) -> None:
        self.device = pair


class _FakeSoundDevice:
    """Imita la parte de sounddevice que usa ``audio_devices``."""

    def __init__(self, devices, default=(0, 1), hostapis=()) -> None:
        self._devices = devices
        self.default = _FakeDefault(default)
        self._hostapis = list(hostapis)

    def query_devices(self):
        return self._devices

    def query_hostapis(self):
        return self._hostapis


DEVICES = [
    {"name": "Micrófono", "max_input_channels": 2, "max_output_channels": 0, "hostapi": 0},
    {"name": "Altavoces", "max_input_channels": 0, "max_output_channels": 2, "hostapi": 1},
    {"name": "Auxiliar", "max_input_channels": 1, "max_output_channels": 0, "hostapi": 0},
]
HOSTAPIS = [{"name": "MME"}, {"name": "WASAPI"}]


class AudioDevicesTest(unittest.TestCase):
    def test_inputs_filter_channels_and_mark_default(self) -> None:
        fake = _FakeSoundDevice(DEVICES, default=(2, 1), hostapis=HOSTAPIS)
        with mock.patch.object(backend, "load_sounddevice", return_value=fake):
            devices = audio_devices("input")

        self.assertEqual([device.index for device in devices], [0, 2])
        self.assertEqual([device.name for device in devices], ["Micrófono", "Auxiliar"])
        self.assertEqual([device.hostapi for device in devices], ["MME", "MME"])
        self.assertEqual([device.default for device in devices], [False, True])

    def test_outputs_filter_channels_and_mark_default(self) -> None:
        fake = _FakeSoundDevice(DEVICES, default=(2, 1), hostapis=HOSTAPIS)
        with mock.patch.object(backend, "load_sounddevice", return_value=fake):
            devices = audio_devices("output")

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].index, 1)
        self.assertEqual(devices[0].hostapi, "WASAPI")
        self.assertTrue(devices[0].default)

    def test_missing_default_index_marks_nothing(self) -> None:
        fake = _FakeSoundDevice(DEVICES, default=(-1, -1), hostapis=HOSTAPIS)
        with mock.patch.object(backend, "load_sounddevice", return_value=fake):
            devices = audio_devices("input")

        self.assertFalse(any(device.default for device in devices))

    def test_invalid_kind_raises(self) -> None:
        with self.assertRaises(ValueError):
            audio_devices("duplex")

    def test_backend_error_is_wrapped(self) -> None:
        fake = _FakeSoundDevice(DEVICES)
        fake.query_devices = mock.Mock(side_effect=RuntimeError("PortAudio roto"))
        with mock.patch.object(backend, "load_sounddevice", return_value=fake):
            with self.assertRaises(AudioError) as context:
                audio_devices("input")
        self.assertEqual(str(context.exception), "PortAudio roto")


class LoadBackendTest(unittest.TestCase):
    def test_missing_sounddevice_gives_actionable_error(self) -> None:
        with mock.patch.dict(sys.modules, {"sounddevice": None}):
            with self.assertRaises(AudioError) as context:
                backend.load_sounddevice()
        self.assertIn("requirements.txt", str(context.exception))


class DeviceDisplayTest(unittest.TestCase):
    def test_default_suffix(self) -> None:
        device = Device(index=1, name="Altavoces", channels=2, default=True)
        self.assertEqual(device.display_name, "Altavoces · predeterminado")

    def test_hostapi_is_included(self) -> None:
        device = Device(index=1, name="Altavoces", channels=2, hostapi="WASAPI")
        self.assertEqual(device.display_name, "Altavoces · WASAPI")

    def test_long_names_are_truncated(self) -> None:
        device = Device(index=1, name="X" * 80, channels=2)
        self.assertLessEqual(len(device.display_name), 46)
        self.assertTrue(device.display_name.endswith("…"))


class FriendlyErrorTest(unittest.TestCase):
    def test_audio_error_passthrough(self) -> None:
        self.assertEqual(friendly_error(AudioError("fallo")), "fallo")

    def test_address_error(self) -> None:
        message = friendly_error(socket.gaierror("bad host"))
        self.assertIn("dirección", message)

    def test_port_in_use(self) -> None:
        message = friendly_error(OSError(10048, "in use"))
        self.assertIn("puerto", message.lower())

    def test_connection_reset(self) -> None:
        message = friendly_error(OSError(10054, "reset"))
        self.assertIn("conexión", message.lower())

    def test_connection_refused(self) -> None:
        message = friendly_error(OSError(10061, "refused"))
        self.assertIn("rechazó", message.lower())

    def test_invalid_device(self) -> None:
        exc = RuntimeError("Error opening InputStream: Invalid device [PaErrorCode -9996]")
        self.assertIn("dispositivo", friendly_error(exc).lower())

    def test_invalid_sample_rate(self) -> None:
        exc = RuntimeError("Invalid sample rate [PaErrorCode -9997]")
        self.assertIn("44,1 kHz", friendly_error(exc))

    def test_device_unavailable(self) -> None:
        exc = RuntimeError("Device unavailable [PaErrorCode -9985]")
        self.assertIn("ocupado", friendly_error(exc).lower())

    def test_unknown_error_uses_its_text(self) -> None:
        self.assertEqual(friendly_error(RuntimeError("inesperado")), "inesperado")

    def test_empty_error_uses_class_name(self) -> None:
        self.assertEqual(friendly_error(RuntimeError()), "RuntimeError")


class _FakeSocket:
    def __init__(self, generation: int) -> None:
        self.generation = generation
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _RaceEngine(AudioEngine):
    """Simula el solapamiento entre el cierre de una sesión y el inicio de otra."""

    def __init__(self) -> None:
        super().__init__()
        self.in_release = threading.Event()
        self.new_socket_ready = threading.Event()

    def _run(self, *, generation: int) -> None:
        sock = _FakeSocket(generation)
        self._register_socket(generation, sock)  # type: ignore[arg-type]
        if generation > 1:
            self.new_socket_ready.set()
        while not self._stop_event.is_set() and generation == self._generation:
            time.sleep(0.005)

    def _release(self, generation: int) -> None:
        if generation == 1:
            self.in_release.set()
            self.new_socket_ready.wait(2)
        super()._release(generation)


class EngineRestartRaceTest(unittest.TestCase):
    def test_old_thread_does_not_close_new_socket(self) -> None:
        engine = _RaceEngine()
        engine.start()
        engine._stop_event.set()
        self.assertTrue(engine.in_release.wait(2))

        engine._stop_event.clear()
        engine.start()  # la sesión nueva arranca mientras la vieja aún libera
        self.assertTrue(engine.new_socket_ready.wait(2))
        time.sleep(0.05)

        self.assertFalse(engine._sockets[2].closed)
        self.assertFalse(engine._sockets[1].closed if 1 in engine._sockets else False)
        engine.stop()


class EngineStatsTest(unittest.TestCase):
    def test_empty_engine_has_zeroed_stats(self) -> None:
        for engine in (Sender(), Receiver()):
            stats = engine.stats()
            self.assertEqual(stats.packets, 0)
            self.assertFalse(engine.running)
            self.assertEqual(stats.kbps, 0.0)
            self.assertEqual(stats.loss_ratio, 0.0)

    def test_bitrate_and_loss(self) -> None:
        stats = EngineStats(
            packets=90,
            lost=10,
            bytes_total=1_000_000,
            seconds=10.0,
            overflows=2,
            underflows=3,
        )
        self.assertAlmostEqual(stats.kbps, 800.0)
        self.assertAlmostEqual(stats.loss_ratio, 0.1)
        self.assertEqual(stats.overflows, 2)
        self.assertEqual(stats.underflows, 3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
