"""Widgets reutilizables de la interfaz."""

from __future__ import annotations

import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Callable, Sequence

from ..formatting import level_fraction
from ..net import Peer
from .draw import rounded_rectangle
from .theme import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    BORDER_STRONG,
    DANGER,
    DISABLED,
    FONT,
    MONO,
    MUTED,
    SUCCESS,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TONE_BACKGROUNDS,
    TONE_BORDERS,
    TONE_COLORS,
    TONE_TEXT,
    WARNING,
)


class Card(tk.Frame):
    """Tarjeta con borde, superficie y título en versalitas."""

    def __init__(self, parent, title: str, **kwargs) -> None:
        super().__init__(
            parent,
            bg=SURFACE,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
            **kwargs,
        )

        header = tk.Frame(self, bg=SURFACE)
        header.pack(fill="x", padx=16, pady=(14, 0))
        dot = tk.Canvas(
            header,
            width=6,
            height=6,
            bg=SURFACE,
            highlightthickness=0,
            bd=0,
        )
        dot.create_oval(1, 1, 5, 5, fill=ACCENT, outline="")
        dot.pack(side="left", padx=(0, 8))
        tk.Label(
            header,
            text=title.upper(),
            bg=SURFACE,
            fg=MUTED,
            font=(FONT, 7, "bold"),
            anchor="w",
            bd=0,
            padx=0,
        ).pack(side="left")

        self.body = tk.Frame(self, bg=SURFACE)
        self.body.pack(fill="both", expand=True, padx=16, pady=(10, 16))


class StatusPill(tk.Canvas):
    """Indicador redondeado con punto de color y texto de estado."""

    HEIGHT = 30

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            width=112,
            height=self.HEIGHT,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self._font = tkfont.Font(family=FONT, size=9, weight="bold")
        self._text = "Inactivo"
        self._tone = "idle"
        self.bind("<Configure>", lambda _event: self._draw())
        self._draw()

    def set(self, text: str, tone: str = "idle") -> None:
        self._text = text
        self._tone = tone
        width = max(88, self._font.measure(text) + 44)
        if int(float(self.cget("width"))) != width:
            self.configure(width=width)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), int(float(self.cget("width"))), 88)
        height = max(self.winfo_height(), self.HEIGHT)
        fill = TONE_BACKGROUNDS.get(self._tone, SURFACE)
        border = TONE_BORDERS.get(self._tone, BORDER_STRONG)
        dot = TONE_COLORS.get(self._tone, MUTED)
        text = TONE_TEXT.get(self._tone, TEXT)

        rounded_rectangle(
            self,
            1,
            1,
            width - 1,
            height - 1,
            radius=(height - 2) / 2.0,
            fill=fill,
            outline=border,
            width=1,
        )
        middle = height / 2.0
        self.create_oval(13, middle - 3, 19, middle + 3, fill=dot, outline="")
        self.create_text(
            26,
            middle,
            anchor="w",
            text=self._text,
            fill=text,
            font=self._font,
        )


class MetricTile(tk.Frame):
    """Pequeña tarjeta de estadística (título + valor)."""

    def __init__(self, parent, title: str) -> None:
        super().__init__(
            parent,
            bg=SURFACE_ALT,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )
        self._title = tk.Label(
            self,
            text=title.upper(),
            bg=SURFACE_ALT,
            fg=MUTED,
            font=(FONT, 7, "bold"),
            anchor="w",
            bd=0,
            padx=0,
        )
        self._title.pack(fill="x", padx=12, pady=(10, 0))
        self._value = tk.Label(
            self,
            text="—",
            bg=SURFACE_ALT,
            fg=TEXT,
            font=(FONT, 12, "bold"),
            anchor="w",
            bd=0,
            padx=0,
        )
        self._value.pack(fill="x", padx=12, pady=(2, 10))
        self._fonts = {
            size: tkfont.Font(family=FONT, size=size, weight="bold")
            for size in (8, 9, 10, 11, 12)
        }
        self.bind("<Configure>", lambda _event: self._fit_value())

    def set_value(self, text: str, accent: bool = False) -> None:
        self._value.configure(text=text, fg=ACCENT if accent else TEXT)
        self._fit_value()

    def _fit_value(self) -> None:
        """Reduce la fuente si el valor no cabe en el ancho disponible."""
        text = self._value.cget("text")
        available = max(20, self.winfo_width() - 26)
        size = 8
        for candidate in (12, 11, 10, 9, 8):
            if self._fonts[candidate].measure(text) <= available:
                size = candidate
                break
        self._value.configure(font=self._fonts[size])


class LevelMeter(tk.Canvas):
    """Barra segmentada en dBFS con marcas verde, ámbar y roja."""

    def __init__(self, parent, segments: int = 42, height: int = 10) -> None:
        super().__init__(
            parent,
            height=height,
            bg=SURFACE,
            highlightthickness=0,
            bd=0,
        )
        self._segments = segments
        self._items: list[int] = []
        self._lit = 0
        self._peak = 0.0
        self._peak_item: int | None = None
        self.bind("<Configure>", self._layout)

    def _layout(self, _event=None) -> None:
        self.delete("all")
        self._items = []
        width = max(self.winfo_width(), 20)
        height = max(self.winfo_height(), 6)
        gap = 2
        segment_width = max(1.0, (width - gap * (self._segments - 1)) / self._segments)
        for index in range(self._segments):
            left = index * (segment_width + gap)
            self._items.append(
                self.create_rectangle(
                    left,
                    0,
                    left + segment_width,
                    height,
                    fill=SURFACE_ALT,
                    outline="",
                )
            )
        self._peak_item = self.create_line(
            0,
            -2,
            0,
            height + 2,
            fill=TEXT,
            width=2,
            state=tk.HIDDEN,
        )
        self._render()

    def set_level(self, level: float, peak: float | None = None) -> None:
        lit = int(round(level_fraction(level) * self._segments))
        marker = level_fraction(level if peak is None else peak)
        if lit != self._lit or abs(marker - self._peak) > 0.004:
            self._lit = lit
            self._peak = marker
            self._render()

    def _render(self) -> None:
        total = max(1, self._segments - 1)
        for index, item in enumerate(self._items):
            if index >= self._lit:
                color = SURFACE_ALT
            else:
                ratio = index / total
                color = SUCCESS if ratio < 0.65 else WARNING if ratio < 0.88 else DANGER
            self.itemconfigure(item, fill=color)

        if self._peak_item is not None:
            if self._peak > 0.01:
                width = max(self.winfo_width(), 20)
                x = self._peak * width
                height = max(self.winfo_height(), 6)
                self.coords(self._peak_item, x, -2, x, height + 2)
                self.itemconfigure(self._peak_item, state=tk.NORMAL)
            else:
                self.itemconfigure(self._peak_item, state=tk.HIDDEN)


class LogPanel(tk.Frame):
    """Consola de registro con marcas de tiempo y colores por severidad."""

    MAX_LINES = 400

    def __init__(self, parent, height: int = 6) -> None:
        super().__init__(
            parent,
            bg=SURFACE_ALT,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )
        self.text = tk.Text(
            self,
            height=height,
            bg=SURFACE_ALT,
            fg=TEXT,
            font=(MONO, 8),
            relief="flat",
            bd=0,
            wrap="word",
            padx=12,
            pady=10,
            insertbackground=TEXT,
            highlightthickness=0,
            state="disabled",
            cursor="arrow",
            spacing1=1,
            spacing3=1,
        )
        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.text.yview, style="Vertical.TScrollbar"
        )
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for name, color in (
            ("time", DISABLED),
            ("info", TEXT),
            ("ok", SUCCESS),
            ("warn", WARNING),
            ("error", DANGER),
            ("muted", MUTED),
        ):
            self.text.tag_configure(name, foreground=color)

    def log(self, message: str, level: str = "info") -> None:
        if level not in ("info", "ok", "warn", "error", "muted"):
            level = "info"
        self.text.configure(state="normal")
        self.text.insert("end", time.strftime("%H:%M:%S  "), "time")
        self.text.insert("end", f"{message}\n", level)
        lines = int(self.text.index("end-1c").split(".")[0])
        if lines > self.MAX_LINES:
            self.text.delete("1.0", f"{lines - self.MAX_LINES + 1}.0")
        self.text.configure(state="disabled")
        self.text.see("end")

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class PeerList(tk.Frame):
    """Lista de receptores descubiertos; avisa al seleccionar uno."""

    def __init__(
        self,
        parent,
        on_select: Callable[[Peer], None] | None = None,
        height: int = 4,
    ) -> None:
        super().__init__(parent, bg=SURFACE_ALT)
        self.on_select = on_select
        self._peers: list[Peer] = []
        self._placeholder = True

        self.listbox = tk.Listbox(
            self,
            height=height,
            width=34,
            bg=SURFACE_ALT,
            fg=TEXT,
            font=(MONO, 8),
            selectbackground=ACCENT_SOFT,
            selectforeground=TEXT,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            activestyle="none",
            relief="flat",
            bd=0,
            exportselection=False,
        )
        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.listbox.yview, style="Vertical.TScrollbar"
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._handle_select)
        self.set_peers([])

    def set_peers(self, peers: Sequence[Peer]) -> None:
        self._peers = list(peers)
        self._placeholder = not self._peers
        self.listbox.delete(0, "end")
        if not self._peers:
            self.listbox.insert("end", "  Sin dispositivos detectados")
            self.listbox.itemconfig(0, foreground=DISABLED)
            return
        for peer in self._peers:
            name = peer.name or "Dispositivo"
            label = f"{peer.ip:<15}  {name}"
            self.listbox.insert("end", label)

    def _handle_select(self, _event=None) -> None:
        if self._placeholder or self.on_select is None:
            return
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self._peers):
            self.on_select(self._peers[index])


def muted_note(
    parent,
    text: str,
    background: str = SURFACE,
    wraplength: int = 0,
) -> tk.Label:
    """Texto de ayuda pequeño, opcionalmente ajustado al ancho indicado."""
    return tk.Label(
        parent,
        text=text,
        bg=background,
        fg=MUTED,
        font=(FONT, 8),
        justify="left",
        anchor="w",
        wraplength=wraplength,
        bd=0,
        padx=0,
    )
