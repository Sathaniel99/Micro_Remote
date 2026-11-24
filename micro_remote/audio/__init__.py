"""Capa de audio de Micro Remote.

Se apoya en ``sounddevice`` (PortAudio) y en streams "raw", por lo que no
requiere NumPy. El paquete se divide en:

* :mod:`.backend`  carga diferida, dispositivos y mensajes de error.
* :mod:`.engine`   ciclo de vida y estadísticas compartidas.
* :mod:`.sender`   captura y transmisión.
* :mod:`.receiver` recepción y reproducción.

La interfaz nunca toca PortAudio ni los hilos de audio: los motores publican
su estado y la ventana lo consulta periódicamente.
"""

from .backend import AudioError, Device, audio_devices, friendly_error
from .engine import AudioEngine, EngineStats
from .receiver import Receiver
from .sender import Sender

__all__ = [
    "AudioEngine",
    "AudioError",
    "Device",
    "EngineStats",
    "Receiver",
    "Sender",
    "audio_devices",
    "friendly_error",
]
