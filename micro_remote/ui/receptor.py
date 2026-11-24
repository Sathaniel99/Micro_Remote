"""Ventana del receptor: puerto de escucha, salida de audio y descubrimiento."""

from __future__ import annotations

import socket
import tkinter as tk
from tkinter import messagebox, ttk

from ..audio import Receiver
from ..config import (
    APP_NAME,
    DEFAULT_AUDIO,
    validate_device,
    validate_gain,
    validate_port,
)
from ..net import DiscoveryResponder, is_valid_port, local_ips, primary_ip
from ..settings import Settings
from .base import BaseAudioApp
from .widgets import Card, muted_note


class ReceiverApp(BaseAudioApp):
    """Interfaz del receptor."""

    window_title = f"{APP_NAME} · Receptor"
    subtitle = "Escucha en vivo el audio que llega desde el emisor"
    icon_name = "receptor.ico"
    session_noun = "recepción"
    running_text = "Escuchando"
    start_text = "Iniciar recepción"
    metric_labels = ("Recibidos", "Perdidos", "Bitrate", "Tiempo")
    settings_role = "receptor"

    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.responder: DiscoveryResponder | None = None
        super().__init__(root, settings)

    # ------------------------------------------------------------------
    # Motor
    # ------------------------------------------------------------------
    def create_engine(self) -> Receiver:
        return Receiver(DEFAULT_AUDIO, gain=self.settings.gain)

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------
    def build_connection(self, parent) -> None:
        card = Card(parent, "Recepción")
        card.pack(fill="x", pady=(0, 12))
        body = card.body

        port_row = ttk.Frame(body, style="Card.TFrame")
        port_row.pack(fill="x", pady=(2, 0))
        ttk.Label(port_row, text="Puerto de escucha", style="Field.TLabel").pack(
            side="left"
        )
        self.port_var = tk.StringVar(master=self.root, value=str(self.settings.port))
        ttk.Entry(
            port_row,
            textvariable=self.port_var,
            style="Dark.TEntry",
            width=8,
            justify="right",
        ).pack(side="right")

        ttk.Label(
            body, text="Tu dirección en la red", style="Field.TLabel"
        ).pack(anchor="w", pady=(14, 2))

        self._primary_ip = primary_ip()
        ip_row = ttk.Frame(body, style="Card.TFrame")
        ip_row.pack(fill="x")
        ttk.Label(
            ip_row,
            text=self._primary_ip,
            style="Ip.TLabel",
        ).pack(side="left")
        ttk.Button(
            ip_row,
            text="Copiar",
            style="Ghost.TButton",
            command=self._copy_ip,
        ).pack(side="right")

        addresses = [
            address for address in local_ips() if address != self._primary_ip
        ]
        if addresses:
            ttk.Label(
                body,
                text="Otras interfaces: " + " · ".join(addresses),
                style="CardMuted.TLabel",
                wraplength=330,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))

        muted_note(
            body,
            "Comparte esta IP con el emisor o deja que te encuentre "
            "automáticamente con «Buscar».",
            wraplength=330,
        ).pack(anchor="w", pady=(8, 0))

    def build_audio(self, parent) -> None:
        self.build_audio_card(
            parent,
            title="Altavoces",
            device_label="Dispositivo de salida",
            gain_label="Volumen de salida",
            kind="output",
            saved_device=self.settings.output_device,
        )

    # ------------------------------------------------------------------
    # Validación y arranque
    # ------------------------------------------------------------------
    def validate(self) -> str | None:
        if not is_valid_port(self.port_var.get()):
            return "El puerto debe ser un número entre 1 y 65535."
        return None

    def start_engine(self) -> None:
        port = int(self.port_var.get())
        self.settings.port = port
        self.settings.output_device = self._selected_device()

        self.responder = DiscoveryResponder(
            audio_port=port,
            name=socket.gethostname(),
            on_error=lambda message: self.post_log(
                f"Descubrimiento inactivo: {message}", "warn"
            ),
        )
        self.responder.start()

        self.engine.start(port, self.settings.output_device)

    def stop_engine(self) -> None:
        if self.responder is not None:
            self.responder.stop()
            self.responder = None

    def collect_settings(self) -> None:
        super().collect_settings()
        if is_valid_port(self.port_var.get()):
            self.settings.port = int(self.port_var.get())
        self.settings.output_device = self._selected_device()

    def detail_text(self, stats) -> str:
        if stats.packets == 0:
            return "Esperando audio del emisor…"
        parts = [f"Fuente: {self.engine.source or 'desconocida'}"]
        if stats.underflows:
            parts.append(f"{stats.underflows} cortes de salida")
        late = super().detail_text(stats)
        if late:
            parts.append(late)
        return " · ".join(parts)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _copy_ip(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self._primary_ip)
        self.log(f"IP copiada al portapapeles: {self._primary_ip}", "muted")

    def close(self) -> None:
        if self.responder is not None:
            self.responder.stop()
            self.responder = None
        super().close()


def main(
    port: int | None = None,
    gain: float | None = None,
    device: int | None = None,
) -> int:
    """Punto de entrada de la interfaz del receptor.

    Los argumentos opcionales permiten arrancar desde la línea de comandos
    con valores que sustituyen a los guardados.
    """
    try:
        root = tk.Tk()
    except (ImportError, tk.TclError) as exc:
        print(f"No se pudo iniciar la interfaz: {exc}")
        return 1
    settings = Settings.load(role="receptor")
    try:
        if port is not None:
            settings.port = validate_port(port)
        if gain is not None:
            settings.gain = validate_gain(gain)
        if device is not None:
            settings.output_device = validate_device(device)
        app = ReceiverApp(root, settings)
    except Exception as exc:
        messagebox.showerror(APP_NAME, f"No se pudo iniciar la ventana:\n{exc}")
        root.destroy()
        return 1
    root.mainloop()
    del app
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
