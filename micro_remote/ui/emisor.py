"""Ventana del emisor: micrófono, búsqueda de receptores y transmisión."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .. import formatting
from ..audio import Sender
from ..config import (
    APP_NAME,
    DEFAULT_AUDIO,
    DEFAULT_PORT,
    DISCOVERY_TIMEOUT,
    validate_device,
    validate_gain,
    validate_port,
)
from ..net import Peer, find_peers, is_valid_ipv4, is_valid_port, normalize_ipv4
from ..settings import Settings
from .base import BaseAudioApp
from .widgets import Card, PeerList, muted_note


class SenderApp(BaseAudioApp):
    """Interfaz del emisor."""

    window_title = f"{APP_NAME} · Emisor"
    subtitle = "Transmite el audio de tu micrófono a otro equipo de la red"
    icon_name = "emisor.ico"
    session_noun = "transmisión"
    running_text = "Transmitiendo"
    start_text = "Iniciar transmisión"
    metric_labels = ("Enviados", "Destino", "Bitrate", "Tiempo")
    settings_role = "emisor"

    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self._scanning = False
        self._scan_stop = threading.Event()
        super().__init__(root, settings)

    # ------------------------------------------------------------------
    # Motor
    # ------------------------------------------------------------------
    def create_engine(self) -> Sender:
        return Sender(DEFAULT_AUDIO, gain=self.settings.gain)

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------
    def build_connection(self, parent) -> None:
        card = Card(parent, "Conexión")
        card.pack(fill="x", pady=(0, 12))
        body = card.body

        ttk.Label(body, text="IP del receptor", style="Field.TLabel").pack(
            anchor="w", pady=(2, 4)
        )
        host_row = ttk.Frame(body, style="Card.TFrame")
        host_row.pack(fill="x")

        self.host_var = tk.StringVar(master=self.root, value=self.settings.host)
        ttk.Entry(
            host_row,
            textvariable=self.host_var,
            style="Dark.TEntry",
        ).pack(side="left", fill="x", expand=True)

        self.scan_button = ttk.Button(
            host_row,
            text="Buscar",
            style="Scan.TButton",
            command=self.start_scan,
        )
        self.scan_button.pack(side="left", padx=(8, 0))

        port_row = ttk.Frame(body, style="Card.TFrame")
        port_row.pack(fill="x", pady=(10, 0))
        ttk.Label(port_row, text="Puerto UDP", style="Field.TLabel").pack(side="left")
        self.port_var = tk.StringVar(master=self.root, value=str(self.settings.port))
        ttk.Entry(
            port_row,
            textvariable=self.port_var,
            style="Dark.TEntry",
            width=8,
            justify="right",
        ).pack(side="right")

        ttk.Label(
            body, text="Dispositivos detectados", style="Field.TLabel"
        ).pack(anchor="w", pady=(14, 4))
        self.peer_list = PeerList(body, on_select=self._select_peer, height=4)
        self.peer_list.pack(fill="x")

        self.scan_hint = muted_note(
            body, "Pulsa «Buscar» para localizar receptores en la red."
        )
        self.scan_hint.pack(anchor="w", pady=(6, 0))

    def build_audio(self, parent) -> None:
        self.build_audio_card(
            parent,
            title="Micrófono",
            device_label="Dispositivo de entrada",
            gain_label="Ganancia de entrada",
            kind="input",
            saved_device=self.settings.input_device,
        )

    # ------------------------------------------------------------------
    # Validación y arranque
    # ------------------------------------------------------------------
    def validate(self) -> str | None:
        if not is_valid_ipv4(self.host_var.get()):
            return (
                "La IP del receptor no es válida.\n"
                "Usa el formato 192.168.1.10 o pulsa «Buscar»."
            )
        if not is_valid_port(self.port_var.get()):
            return "El puerto debe ser un número entre 1 y 65535."
        return None

    def start_engine(self) -> None:
        host = self.host_var.get().strip()
        port = int(self.port_var.get())
        self.settings.host = host
        self.settings.port = port
        self.settings.input_device = self._selected_device()
        self.engine.start(host, port, self.settings.input_device)

    def collect_settings(self) -> None:
        super().collect_settings()
        host = self.host_var.get().strip()
        if is_valid_ipv4(host):
            self.settings.host = host
        if is_valid_port(self.port_var.get()):
            self.settings.port = int(self.port_var.get())
        self.settings.input_device = self._selected_device()

    def _metric_values(self, stats) -> tuple[str, str, str, str]:
        destination = self.engine.destination
        target = destination[0] if destination else "—"
        return (
            f"{stats.packets:,}",
            target,
            formatting.format_bitrate(stats.kbps),
            formatting.format_duration(stats.seconds),
        )

    def detail_text(self, stats) -> str:
        parts: list[str] = []
        destination = self.engine.destination
        if destination:
            parts.append(f"Destino: {destination[0]}:{destination[1]}")
        if stats.overflows:
            parts.append(f"{stats.overflows} desbordes de entrada")
        late = super().detail_text(stats)
        if late:
            parts.append(late)
        return " · ".join(parts)

    # ------------------------------------------------------------------
    # Descubrimiento
    # ------------------------------------------------------------------
    def _current_port(self) -> int:
        value = self.port_var.get()
        return int(value) if is_valid_port(value) else DEFAULT_PORT

    def start_scan(self) -> None:
        if self._scanning:
            self._scan_stop.set()
            return
        self._scanning = True
        self._scan_stop = threading.Event()
        self.scan_button.configure(state="disabled", text="Buscando…")
        self.scan_hint.configure(text="Buscando receptores en la red local…")
        self.log("Buscando receptores en la red local…", "muted")
        threading.Thread(
            target=self._scan_worker,
            args=(self._current_port(),),
            daemon=True,
            name="network-scan",
        ).start()

    def _scan_worker(self, port: int) -> None:
        try:
            peers = find_peers(
                timeout=DISCOVERY_TIMEOUT,
                sweep=True,
                should_stop=self._scan_stop.is_set,
                on_stage=lambda text: self.post("stage", text),
                default_port=port,
            )
            self.post("peers", peers)
        except Exception as exc:  # pragma: no cover - defensivo
            self.post("scan_error", str(exc))
        finally:
            self.post("scan_done")

    def on_peers(self, peers: list[Peer]) -> None:
        self.peer_list.set_peers(peers)
        if peers:
            self.scan_hint.configure(
                text=f"{len(peers)} receptor(es) encontrados. Selecciona uno."
            )
            self.log(f"Búsqueda completada: {len(peers)} receptor(es).", "ok")
            if not self.host_var.get().strip():
                self._select_peer(peers[0])
        else:
            self.scan_hint.configure(
                text="Sin resultados. Revisa el firewall o escribe la IP a mano."
            )
            self.log("La búsqueda no encontró receptores.", "warn")

    def on_scan_stage(self, message: str) -> None:
        self.scan_hint.configure(text=message)
        self.log(message, "muted")

    def on_scan_done(self) -> None:
        self._scanning = False
        self.scan_button.configure(state="normal", text="Buscar")

    def on_scan_error(self, message: str) -> None:
        self.scan_hint.configure(text="Error durante la búsqueda.")
        super().on_scan_error(message)

    def _select_peer(self, peer: Peer) -> None:
        self.host_var.set(peer.ip)
        self.port_var.set(str(peer.port))
        self.log(f"Receptor seleccionado: {peer.label}", "info")

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------
    def close(self) -> None:
        self._scan_stop.set()
        super().close()


def main(
    host: str | None = None,
    port: int | None = None,
    gain: float | None = None,
    device: int | None = None,
) -> int:
    """Punto de entrada de la interfaz del emisor.

    Los argumentos opcionales permiten arrancar desde la línea de comandos
    con valores que sustituyen a los guardados.
    """
    try:
        root = tk.Tk()
    except (ImportError, tk.TclError) as exc:
        print(f"No se pudo iniciar la interfaz: {exc}")
        return 1
    settings = Settings.load(role="emisor")
    try:
        if host is not None:
            normalized = normalize_ipv4(host)
            if normalized is None:
                raise ValueError(f"IP del receptor no válida: {host!r}")
            settings.host = normalized
        if port is not None:
            settings.port = validate_port(port)
        if gain is not None:
            settings.gain = validate_gain(gain)
        if device is not None:
            settings.input_device = validate_device(device)
        app = SenderApp(root, settings)
    except Exception as exc:
        messagebox.showerror(APP_NAME, f"No se pudo iniciar la ventana:\n{exc}")
        root.destroy()
        return 1
    root.mainloop()
    del app
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
