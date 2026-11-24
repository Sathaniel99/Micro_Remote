"""Backend de audio sobre ``sounddevice`` (PortAudio).

``sounddevice`` se importa de forma diferida para que el paquete se pueda
importar, probar y documentar en equipos sin tarjeta de sonido. Los streams
"Raw" trabajan con buffers de bytes, así que **no se necesita NumPy**.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass


class AudioError(RuntimeError):
    """Fallo controlado del subsistema de audio."""


def load_sounddevice():
    """Importa ``sounddevice`` o lanza :class:`AudioError` con un consejo."""
    try:
        import sounddevice as sd  # importación diferida
    except Exception as exc:  # pragma: no cover - depende del entorno
        if "portaudio" in str(exc).lower():
            raise AudioError(
                "No se pudo cargar PortAudio. Reinstala sounddevice "
                "(«pip install --force-reinstall sounddevice»)."
            ) from exc
        raise AudioError(
            "sounddevice no está disponible. Instala las dependencias con "
            "«pip install -r requirements.txt» y vuelve a intentarlo."
        ) from exc
    return sd


@dataclass(frozen=True, slots=True)
class Device:
    """Dispositivo de entrada o salida de PortAudio."""

    index: int
    name: str
    channels: int
    default: bool = False
    hostapi: str = ""

    @property
    def display_name(self) -> str:
        """Etiqueta corta para el desplegable de la interfaz."""
        label = f"{self.name} · {self.hostapi}" if self.hostapi else self.name
        if len(label) > 46:
            label = label[:43] + "…"
        return f"{label} · predeterminado" if self.default else label


def _hostapi_names(sd) -> list[str]:
    try:
        return [str(api.get("name", "")) for api in sd.query_hostapis()]
    except Exception:
        return []


def audio_devices(kind: str) -> list[Device]:
    """Lista los dispositivos de ``"input"`` o ``"output"`` disponibles.

    Se descartan los dispositivos que no tienen canales del tipo pedido. Los
    índices son los globales de PortAudio y se usan tal cual al abrir un
    stream.
    """
    if kind not in ("input", "output"):
        raise ValueError("kind debe ser 'input' o 'output'")

    sd = load_sounddevice()
    try:
        queried = sd.query_devices()
    except Exception as exc:
        raise AudioError(friendly_error(exc)) from exc
    try:
        default_index = int(sd.default.device[0 if kind == "input" else 1])
    except (AttributeError, IndexError, TypeError, ValueError):
        default_index = -1

    hostapis = _hostapi_names(sd)
    channel_key = "max_input_channels" if kind == "input" else "max_output_channels"
    devices: list[Device] = []
    for index, info in enumerate(queried):
        try:
            channels = int(info.get(channel_key, 0) or 0)
        except (TypeError, ValueError):
            channels = 0
        if channels <= 0:
            continue

        name = str(info.get("name", "Dispositivo")).strip() or "Dispositivo"
        try:
            hostapi_index = int(info.get("hostapi", -1))
        except (TypeError, ValueError):
            hostapi_index = -1
        hostapi = (
            hostapis[hostapi_index]
            if 0 <= hostapi_index < len(hostapis)
            else ""
        )
        devices.append(
            Device(
                index=index,
                name=name,
                channels=channels,
                default=(index == default_index),
                hostapi=hostapi,
            )
        )
    return devices


def friendly_error(exc: BaseException) -> str:
    """Traduce errores de PortAudio, red y sistema a mensajes entendibles."""
    if isinstance(exc, AudioError):
        return str(exc)
    if isinstance(exc, socket.gaierror):
        return "La dirección de destino no es válida o no se pudo resolver."
    if isinstance(exc, OSError):
        if exc.errno in (10048, 98):  # WSAEADDRINUSE / EADDRINUSE
            return "El puerto ya está en uso. Elige otro puerto UDP."
        if exc.errno in (10049, 99):  # WSAEADDRNOTAVAIL / EADDRNOTAVAIL
            return "No se pudo abrir el puerto en este equipo."
        if exc.errno in (10051, 101):  # WSAENETUNREACH / ENETUNREACH
            return "La red de destino no es accesible. Revisa la conexión."
        if exc.errno in (10054, 104):  # WSAECONNRESET / ECONNRESET
            return "La conexión se interrumpió. Comprueba que el receptor siga activo."
        if exc.errno in (10061, 111):  # WSAECONNREFUSED / ECONNREFUSED
            return "El destino rechazó la conexión. Revisa el puerto y el receptor."
        if exc.errno in (10065, 113):  # WSAEHOSTUNREACH / EHOSTUNREACH
            return "El equipo de destino no es accesible. Revisa la red."

    text = str(exc).strip()
    lowered = text.lower()
    if "invalid device" in lowered or "-9996" in text:
        return "El dispositivo de audio seleccionado no está disponible."
    if (
        "invalid sample rate" in lowered
        or "unsupported sample rate" in lowered
        or "-9997" in text
    ):
        return "El dispositivo no admite este formato (44,1 kHz, mono, 16 bits)."
    if "device unavailable" in lowered or "-9985" in text:
        return "El dispositivo de audio está ocupado o no disponible."
    if "illegal combination" in lowered or "-9987" in text:
        return "La combinación de dispositivos de entrada/salida no es válida."
    if "insufficient memory" in lowered or "-9984" in text:
        return "No hay memoria suficiente para abrir el flujo de audio."
    if "unanticipated host error" in lowered or "-9999" in text:
        return "El sistema de audio devolvió un error inesperado."
    if "portaudio" in lowered and (
        "not found" in lowered or "failed to load" in lowered or "dlopen" in lowered
    ):
        return "No se pudo cargar PortAudio. Reinstala sounddevice."
    return text or type(exc).__name__


def close_stream(stream) -> None:
    """Detiene y cierra un stream ignorando errores de cierre."""
    if stream is None:
        return
    try:
        if stream.active:
            stream.stop()
    except Exception:
        pass
    try:
        stream.close()
    except Exception:
        pass


__all__ = [
    "AudioError",
    "Device",
    "audio_devices",
    "close_stream",
    "friendly_error",
    "load_sounddevice",
]
