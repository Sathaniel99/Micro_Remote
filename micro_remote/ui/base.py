"""Ventana base compartida por emisor y receptor.

Concentra el esqueleto visual (cabecera, tarjetas, medidores, registro) y la
máquina de estados de la sesión. Las subclases sólo aportan la tarjeta de
conexión, el tipo de dispositivo de audio y cómo arrancar su motor.

Regla de oro: **ningún hilo de audio toca Tkinter**. Los hilos publican
mensajes en una ``queue.Queue`` y la ventana la vacía desde su bucle de
sondeo, que corre siempre en el hilo principal.
"""

from __future__ import annotations

import abc
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .. import audio, formatting
from ..audio import AudioEngine
from ..config import (
    APP_NAME,
    APP_VERSION,
    MAX_GAIN,
    MIN_GAIN,
    MIN_WINDOW_SIZE,
    WINDOW_SIZE,
)
from ..settings import Settings
from .draw import rounded_rectangle
from .scope import AudioScope
from .theme import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    BORDER_STRONG,
    FONT,
    MUTED,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    apply_theme,
)
from .widgets import Card, LevelMeter, LogPanel, MetricTile, StatusPill, muted_note
from .window import configure_window

POLL_MS = 50


class BaseAudioApp(abc.ABC):
    """Esqueleto de la aplicación de audio."""

    window_title = APP_NAME
    subtitle = ""
    icon_name = "emisor.ico"
    session_noun = "sesión"
    running_text = "En ejecución"
    start_text = "Iniciar"
    metric_labels: tuple[str, str, str, str] = (
        "Paquetes",
        "Perdidos",
        "Bitrate",
        "Tiempo",
    )
    settings_role: str | None = None

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self.engine = self.create_engine()
        self.state = "idle"
        self._closed = False
        self._events: queue.Queue[tuple] = queue.Queue()
        self._level_smooth = 0.0
        self._peak_smooth = 0.0
        self._poll_id: str | None = None
        self._devices: list[audio.Device | None] = [None]
        self._device_combo: ttk.Combobox | None = None
        self._device_var = tk.StringVar(master=root)

        configure_window(
            root,
            title=self.window_title,
            icon_name=self.icon_name,
            size=WINDOW_SIZE,
            min_size=MIN_WINDOW_SIZE,
        )
        apply_theme(root)
        self._build()
        self._set_state("idle")
        self.status_pill.set("Inactivo", "idle")

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<F5>", lambda _event: self.start_session())
        root.bind("<F6>", lambda _event: self.stop_session())
        self.log(f"{APP_NAME} {APP_VERSION} · interfaz lista", "muted")
        self._poll()

    @abc.abstractmethod
    def create_engine(self) -> AudioEngine:
        """Crea el motor de audio concreto (emisor o receptor)."""

    @abc.abstractmethod
    def build_connection(self, parent) -> None:
        """Construye la tarjeta de conexión propia de cada rol."""

    @abc.abstractmethod
    def build_audio(self, parent) -> None:
        """Construye la tarjeta de selección de dispositivo y ganancia."""

    @abc.abstractmethod
    def start_engine(self) -> None:
        """Arranca el motor con los valores actuales de la interfaz."""

    def stop_engine(self) -> None:
        """Detiene recursos propios antes/después del motor."""

    def validate(self) -> str | None:
        """Devuelve un mensaje de error si la configuración no es válida."""
        return None

    def collect_settings(self) -> None:
        """Guarda en ``settings`` los valores actuales de la interfaz."""
        self.settings.gain = float(self.gain_var.get())

    # ------------------------------------------------------------------
    # Estructura visual
    # ------------------------------------------------------------------
    def _build(self) -> None:
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill="x")

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=28, pady=(20, 18))

        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")

        logo = tk.Canvas(
            brand,
            width=40,
            height=40,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        rounded_rectangle(
            logo,
            1,
            1,
            39,
            39,
            radius=12,
            fill=ACCENT,
            outline="",
        )
        logo.create_text(
            20,
            20,
            text="MR",
            fill="#FFFFFF",
            font=(FONT, 10, "bold"),
        )
        logo.pack(side="left", padx=(0, 12))

        titles = tk.Frame(brand, bg=BG)
        titles.pack(side="left")
        tk.Label(
            titles,
            text=APP_NAME,
            bg=BG,
            fg=TEXT,
            font=(FONT, 17, "bold"),
        ).pack(anchor="w")
        tk.Label(
            titles,
            text=self.subtitle,
            bg=BG,
            fg=MUTED,
            font=(FONT, 9),
        ).pack(anchor="w", pady=(2, 0))

        status_area = tk.Frame(header, bg=BG)
        status_area.pack(side="right")
        self.status_pill = StatusPill(status_area)
        self.status_pill.pack(side="right")
        tk.Label(
            status_area,
            text=f"v{APP_VERSION}",
            bg=SURFACE_ALT,
            fg=MUTED,
            font=(FONT, 7, "bold"),
            padx=8,
            pady=4,
            highlightthickness=1,
            highlightbackground=BORDER,
        ).pack(side="right", padx=(0, 10))

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=28)

        content = tk.Frame(self.root, bg=BG)
        content.pack(fill="both", expand=True, padx=28, pady=18)
        left_min = 420 if self.root.winfo_reqwidth() >= 900 else 300
        content.columnconfigure(0, weight=0, minsize=left_min)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        right_column = tk.Frame(content, bg=BG)
        right_column.grid(row=0, column=1, sticky="nsew")
        right_column.columnconfigure(0, weight=1)
        right_column.rowconfigure(1, weight=1)
        self._build_right_column(right_column)

        left_column = tk.Frame(content, bg=BG)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        self.build_connection(left_column)
        self.build_audio(left_column)
        self._build_controls(left_column)

    def _build_right_column(self, parent) -> None:
        summary = Card(parent, "Resumen")
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        tiles = ttk.Frame(summary.body, style="Card.TFrame")
        tiles.pack(fill="x")
        self.tiles: list[MetricTile] = []
        for index, label in enumerate(self.metric_labels):
            tiles.columnconfigure(index, weight=1, uniform="metric")
            tile = MetricTile(tiles, label)
            tile.grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 8) if index < 3 else 0,
            )
            self.tiles.append(tile)

        self.detail_label = ttk.Label(
            summary.body,
            text="",
            style="CardMuted.TLabel",
        )
        self.detail_label.pack(anchor="w", pady=(10, 0))

        scope_card = Card(parent, "Señal de audio")
        scope_card.grid(row=1, column=0, sticky="nsew", pady=(0, 14))
        self.scope = AudioScope(scope_card.body, height=150)
        self.scope.pack(fill="both", expand=True)

        meter_row = ttk.Frame(scope_card.body, style="Card.TFrame")
        meter_row.pack(fill="x", pady=(12, 0))
        ttk.Label(meter_row, text="NIVEL", style="CardOverline.TLabel").pack(side="left")
        self.level_text = ttk.Label(
            meter_row, text="—", style="CardReading.TLabel"
        )
        self.level_text.pack(side="right")
        self.meter = LevelMeter(scope_card.body, height=10)
        self.meter.pack(fill="x", pady=(6, 0))

        ticks = ttk.Frame(scope_card.body, style="Card.TFrame")
        ticks.pack(fill="x", pady=(3, 0))
        for column in range(3):
            ticks.columnconfigure(column, weight=1)
        ttk.Label(ticks, text="-60", style="CardMuted.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(ticks, text="-30 dB", style="CardMuted.TLabel").grid(
            row=0, column=1
        )
        ttk.Label(ticks, text="0 dBFS", style="CardMuted.TLabel").grid(
            row=0, column=2, sticky="e"
        )

        muted_note(
            scope_card.body,
            "Onda con autoescala visual · nivel y pico reales en dBFS.",
        ).pack(anchor="w", pady=(8, 0))

        log_card = Card(parent, "Registro")
        log_card.grid(row=2, column=0, sticky="ew")
        self.log_panel = LogPanel(log_card.body, height=6)
        self.log_panel.pack(fill="both", expand=True)

    def _build_controls(self, parent) -> None:
        card = Card(parent, "Controles")
        card.pack(side="bottom", fill="x")

        buttons = ttk.Frame(card.body, style="Card.TFrame")
        buttons.pack(fill="x", pady=(2, 0))
        buttons.columnconfigure(0, weight=3, uniform="action")
        buttons.columnconfigure(1, weight=2, uniform="action")

        self.start_button = ttk.Button(
            buttons,
            text=f"►  {self.start_text}",
            style="Accent.TButton",
            command=self.start_session,
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.stop_button = ttk.Button(
            buttons,
            text="■  Detener",
            style="Danger.TButton",
            command=self.stop_session,
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, sticky="ew")

        shortcuts = ttk.Frame(card.body, style="Card.TFrame")
        shortcuts.pack(anchor="w", pady=(12, 0))
        for index, (key, action) in enumerate((("F5", "iniciar"), ("F6", "detener"))):
            if index:
                tk.Frame(
                    shortcuts,
                    bg=SURFACE,
                    width=12,
                    height=1,
                ).pack(side="left")
            tk.Label(
                shortcuts,
                text=key,
                bg=SURFACE_ALT,
                fg=MUTED,
                font=(FONT, 7, "bold"),
                padx=5,
                pady=2,
                highlightthickness=1,
                highlightbackground=BORDER_STRONG,
            ).pack(side="left")
            tk.Label(
                shortcuts,
                text=action,
                bg=SURFACE,
                fg=MUTED,
                font=(FONT, 8),
            ).pack(side="left", padx=(5, 0))

    # ------------------------------------------------------------------
    # Ayudantes para las subclases
    # ------------------------------------------------------------------
    def build_audio_card(
        self,
        parent,
        *,
        title: str,
        device_label: str,
        gain_label: str,
        kind: str,
        saved_device: int | None,
    ) -> None:
        """Tarjeta de audio completa (selector de dispositivo + ganancia)."""
        card = Card(parent, title)
        card.pack(fill="x", pady=(0, 12))
        self._build_device_selector(card.body, device_label, kind, saved_device)
        self._build_gain(card.body, gain_label)

    def _build_device_selector(
        self,
        parent,
        label: str,
        kind: str,
        saved_device: int | None,
    ) -> None:
        ttk.Label(parent, text=label, style="Field.TLabel").pack(
            anchor="w", pady=(2, 4)
        )

        names = ["Sistema (predeterminado)"]
        self._devices = [None]
        try:
            for device in audio.audio_devices(kind):
                self._devices.append(device)
                names.append(device.display_name)
        except audio.AudioError as exc:
            self.post("log", f"Audio no disponible: {exc}", "error")
        except Exception as exc:  # pragma: no cover - defensivo
            self.post("log", f"No se pudieron listar dispositivos: {exc}", "warn")

        combo = ttk.Combobox(
            parent,
            textvariable=self._device_var,
            values=names,
            state="readonly",
            style="Dark.TCombobox",
            width=30,
        )
        combo.pack(fill="x")

        selected = 0
        if saved_device is not None:
            for position, device in enumerate(self._devices):
                if device is not None and device.index == saved_device:
                    selected = position
                    break
        combo.current(selected)
        self._device_combo = combo

    def _build_gain(self, parent, label: str) -> None:
        head = ttk.Frame(parent, style="Card.TFrame")
        head.pack(fill="x", pady=(14, 2))
        ttk.Label(head, text=label, style="Field.TLabel").pack(side="left")
        self.gain_value_label = tk.Label(
            head,
            text=formatting.format_gain(self.settings.gain),
            bg=ACCENT_SOFT,
            fg="#C7D2FE",
            font=(FONT, 8, "bold"),
            padx=8,
            pady=3,
        )
        self.gain_value_label.pack(side="right")

        self.gain_var = tk.DoubleVar(master=self.root, value=self.settings.gain)
        scale = ttk.Scale(
            parent,
            from_=MIN_GAIN,
            to=MAX_GAIN,
            variable=self.gain_var,
            orient="horizontal",
            style="Accent.Horizontal.TScale",
            command=self._on_gain_change,
        )
        scale.pack(fill="x", pady=(6, 1))

        limits = ttk.Frame(parent, style="Card.TFrame")
        limits.pack(fill="x", pady=(0, 4))
        ttk.Label(limits, text="0.0x", style="CardMuted.TLabel").pack(side="left")
        ttk.Label(
            limits, text=f"{MAX_GAIN:.1f}x", style="CardMuted.TLabel"
        ).pack(side="right")

        muted_note(parent, "Se aplica en tiempo real, sin cortar el audio.").pack(
            anchor="w"
        )

    def _selected_device(self) -> int | None:
        if self._device_combo is None:
            return None
        index = self._device_combo.current()
        if 0 <= index < len(self._devices):
            device = self._devices[index]
            if device is not None:
                return device.index
        return None

    def _on_gain_change(self, value) -> None:
        try:
            gain = float(value)
        except (TypeError, ValueError):
            return
        self.gain_value_label.configure(text=formatting.format_gain(gain))
        self.settings.gain = gain
        self.engine.gain = gain

    # ------------------------------------------------------------------
    # Eventos entre hilos
    # ------------------------------------------------------------------
    def post(self, kind: str, *payload) -> None:
        """Publica un evento para que lo procese el hilo de Tk."""
        self._events.put((kind, *payload))

    def post_log(self, message: str, level: str = "info") -> None:
        self.post("log", message, level)

    def log(self, message: str, level: str = "info") -> None:
        if hasattr(self, "log_panel"):
            self.log_panel.log(message, level)
        else:  # pragma: no cover - sólo durante la construcción
            print(message)

    def _drain_events(self) -> None:
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            payload = event[1:]
            if kind == "log" and payload:
                self.log(str(payload[0]), payload[1] if len(payload) > 1 else "info")
            elif kind == "peers" and payload:
                self.on_peers(payload[0])
            elif kind == "stage" and payload:
                self.on_scan_stage(str(payload[0]))
            elif kind == "scan_done":
                self.on_scan_done()
            elif kind == "scan_error" and payload:
                self.on_scan_error(str(payload[0]))

    def on_peers(self, peers) -> None:
        """Hook: se han descubierto dispositivos."""

    def on_scan_stage(self, message: str) -> None:
        """Hook: progreso del escaneo."""

    def on_scan_done(self) -> None:
        """Hook: fin del escaneo."""

    def on_scan_error(self, message: str) -> None:
        """Hook: error durante el escaneo."""
        self.log(f"Error de búsqueda: {message}", "error")

    # ------------------------------------------------------------------
    # Sesión
    # ------------------------------------------------------------------
    def start_session(self) -> None:
        if self.state not in ("idle", "error"):
            return
        problem = self.validate()
        if problem:
            messagebox.showwarning(APP_NAME, problem, parent=self.root)
            return

        self.engine.error = None
        self.engine.gain = float(self.gain_var.get())
        self._level_smooth = 0.0
        self._peak_smooth = 0.0
        self.scope.clear()
        self.meter.set_level(0, 0)
        self.level_text.configure(text="—")
        for tile in self.tiles:
            tile.set_value("—")
        self.detail_label.configure(text="")

        self._set_state("starting")
        self.status_pill.set("Preparando…", "warn")
        self.log(f"Iniciando {self.session_noun}…")

        try:
            self.start_engine()
        except Exception as exc:  # pragma: no cover - defensivo
            self._fail(exc)

    def stop_session(self) -> None:
        if self.state not in ("starting", "running"):
            return
        self._set_state("stopping")
        self.status_pill.set("Deteniendo…", "warn")
        self.log("Deteniendo la sesión…", "muted")
        self._shutdown_async()

    def _shutdown_async(self) -> None:
        threading.Thread(target=self._shutdown_sync, daemon=True).start()

    def _shutdown_sync(self) -> None:
        try:
            self.stop_engine()
        except Exception as exc:  # pragma: no cover - defensivo
            self.post_log(f"Error al detener: {exc}", "warn")
        try:
            self.engine.stop(2.5)
        except Exception:
            pass

    def _sync(self) -> None:
        engine = self.engine
        if self.state == "starting":
            if engine.error:
                self._fail(engine.error)
            elif engine.running:
                self._set_state("running")
                self.status_pill.set(self.running_text, "ok")
                self.log(f"{self.running_text}.", "ok")
        elif self.state in ("running", "stopping"):
            if engine.error:
                self._fail(engine.error)
            elif not engine.running:
                self._finish_session()

    def _finish_session(self) -> None:
        self._set_state("idle")
        self.status_pill.set("Inactivo", "idle")
        self.scope.clear()
        self._level_smooth = 0.0
        self._peak_smooth = 0.0
        self.meter.set_level(0, 0)
        self.level_text.configure(text="—")
        self.log("Sesión finalizada.", "muted")

    def _fail(self, exc: BaseException) -> None:
        if self.state == "error":
            return
        message = str(exc).strip() or exc.__class__.__name__
        self._set_state("error")
        self.status_pill.set("Error", "error")
        self.scope.clear()
        self._level_smooth = 0.0
        self._peak_smooth = 0.0
        self.meter.set_level(0, 0)
        self.level_text.configure(text="—")
        self.log(message, "error")
        self._shutdown_async()
        self.root.after(
            10,
            lambda: messagebox.showerror(APP_NAME, message, parent=self.root),
        )

    def _set_state(self, state: str) -> None:
        self.state = state
        if state in ("idle", "error"):
            start_state, stop_state = "normal", "disabled"
        elif state in ("starting", "running"):
            start_state, stop_state = "disabled", "normal"
        else:
            start_state, stop_state = "disabled", "disabled"
        self.start_button.configure(state=start_state)
        self.stop_button.configure(state=stop_state)

    # ------------------------------------------------------------------
    # Actualización periódica
    # ------------------------------------------------------------------
    def _poll(self) -> None:
        if self._closed or not self.root.winfo_exists():
            return
        self._drain_events()
        self._sync()
        if self.state == "running":
            self._refresh_live()
        self._poll_id = self.root.after(POLL_MS, self._poll)

    def _refresh_live(self) -> None:
        engine = self.engine
        if engine.wave:
            self.scope.update_samples(engine.wave)

        self._level_smooth = max(engine.level, self._level_smooth * 0.82)
        self._peak_smooth = max(engine.peak, self._peak_smooth * 0.94)
        self.meter.set_level(self._level_smooth, self._peak_smooth)
        self.level_text.configure(text=formatting.format_level(engine.level))

        stats = engine.stats()
        for tile, value in zip(self.tiles, self._metric_values(stats)):
            tile.set_value(value)
        self.detail_label.configure(text=self.detail_text(stats))

    def _metric_values(self, stats) -> tuple[str, str, str, str]:
        return (
            f"{stats.packets:,}",
            f"{stats.lost:,}",
            formatting.format_bitrate(stats.kbps),
            formatting.format_duration(stats.seconds),
        )

    def detail_text(self, stats) -> str:
        """Línea informativa bajo las métricas."""
        return f"{stats.late:,} tardíos" if stats.late else ""

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------
    def save_settings(self) -> None:
        try:
            self.collect_settings()
            self.settings.save(role=self.settings_role)
        except OSError as exc:  # pragma: no cover - depende del sistema
            print(f"No se pudieron guardar los ajustes: {exc}")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._poll_id is not None:
            try:
                self.root.after_cancel(self._poll_id)
            except tk.TclError:
                pass
            self._poll_id = None
        self.save_settings()
        self._shutdown_sync()
        try:
            self.root.destroy()
        except tk.TclError:
            pass
