"""Paleta y estilos ttk de Micro Remote.

El lenguaje visual imita una interfaz moderna construida con *Tailwind CSS*:
fondo ``slate-950``, superficies ``slate-900``/``slate-800``, acento
``indigo-500``, bordes de 1 px, etiquetas en versalitas y una jerarquía
tipográfica muy marcada. Todo se define aquí para que emisor y receptor
compartan exactamente el mismo aspecto.
"""

from __future__ import annotations

import sys

from tkinter import ttk

FONT = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"
MONO = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"

# ---------------------------------------------------------------------------
# Fondo y superficies
# ---------------------------------------------------------------------------
BG = "#020617"  # slate-950
SURFACE = "#0F172A"  # slate-900
SURFACE_ALT = "#1E293B"  # slate-800
SURFACE_HOVER = "#334155"  # slate-700
BORDER = "#1E293B"  # slate-800
BORDER_STRONG = "#334155"  # slate-700

# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------
TEXT = "#F8FAFC"  # slate-50
MUTED = "#94A3B8"  # slate-400
DISABLED = "#64748B"  # slate-500

# ---------------------------------------------------------------------------
# Acento y estados
# ---------------------------------------------------------------------------
ACCENT = "#6366F1"  # indigo-500
ACCENT_HOVER = "#818CF8"  # indigo-400
ACCENT_DARK = "#4F46E5"  # indigo-600
ACCENT_SOFT = "#312E81"  # indigo-900
SUCCESS = "#34D399"  # emerald-400
SUCCESS_SOFT = "#064E3B"  # emerald-900
WARNING = "#FBBF24"  # amber-400
WARNING_SOFT = "#78350F"  # amber-900
DANGER = "#FB7185"  # rose-400
DANGER_SOFT = "#881337"  # rose-900
DANGER_HOVER = "#9F1239"  # rose-800

# ---------------------------------------------------------------------------
# Visualizador
# ---------------------------------------------------------------------------
SCOPE_BG = "#020617"
SCOPE_FILL = "#1E1B4B"  # indigo-950
SCOPE_GLOW = "#312E81"  # indigo-900
SCOPE_LINE = "#A5B4FC"  # indigo-300
GRID = "#1E293B"
GRID_STRONG = "#334155"

TONE_COLORS = {
    "idle": MUTED,
    "ok": SUCCESS,
    "warn": WARNING,
    "error": DANGER,
}

TONE_BACKGROUNDS = {
    "idle": SURFACE,
    "ok": SUCCESS_SOFT,
    "warn": WARNING_SOFT,
    "error": DANGER_SOFT,
}

TONE_BORDERS = {
    "idle": BORDER_STRONG,
    "ok": "#065F46",
    "warn": "#92400E",
    "error": "#9F1239",
}

TONE_TEXT = {
    "idle": MUTED,
    "ok": "#A7F3D0",
    "warn": "#FDE68A",
    "error": "#FECDD3",
}


def apply_theme(root) -> ttk.Style:
    """Aplica la paleta a todos los widgets ttk de la ventana ``root``."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:  # pragma: no cover - tema no disponible
        pass

    # ------------------------------------------------------------------
    # Base y tipografía
    # ------------------------------------------------------------------
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 9))

    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(FONT, 8))
    style.configure(
        "Overline.TLabel", background=BG, foreground=MUTED, font=(FONT, 7, "bold")
    )
    style.configure(
        "Title.TLabel", background=BG, foreground=TEXT, font=(FONT, 17, "bold")
    )
    style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
    style.configure("Version.TLabel", background=BG, foreground=DISABLED, font=(FONT, 8))

    # ------------------------------------------------------------------
    # Interiores de tarjeta
    # ------------------------------------------------------------------
    style.configure("Card.TFrame", background=SURFACE)
    style.configure("Card.TLabel", background=SURFACE, foreground=TEXT, font=(FONT, 9))
    style.configure("CardMuted.TLabel", background=SURFACE, foreground=MUTED, font=(FONT, 8))
    style.configure(
        "CardOverline.TLabel",
        background=SURFACE,
        foreground=MUTED,
        font=(FONT, 7, "bold"),
    )
    style.configure(
        "CardReading.TLabel",
        background=SURFACE,
        foreground=TEXT,
        font=(MONO, 8, "bold"),
    )
    style.configure(
        "CardStrong.TLabel",
        background=SURFACE,
        foreground=TEXT,
        font=(FONT, 9, "bold"),
    )
    style.configure(
        "Field.TLabel", background=SURFACE, foreground=MUTED, font=(FONT, 8, "bold")
    )
    style.configure("Value.TLabel", background=SURFACE, foreground=ACCENT, font=(FONT, 10, "bold"))
    style.configure("Ip.TLabel", background=SURFACE, foreground=ACCENT, font=(MONO, 12, "bold"))

    # ------------------------------------------------------------------
    # Botones
    # ------------------------------------------------------------------
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        focusthickness=0,
        focuscolor=ACCENT,
        relief="flat",
        borderwidth=1,
        padding=(16, 10),
        font=(FONT, 9, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[
            ("disabled", SURFACE_ALT),
            ("pressed", ACCENT_DARK),
            ("active", ACCENT_HOVER),
        ],
        foreground=[("disabled", DISABLED)],
        bordercolor=[("disabled", BORDER), ("active", ACCENT_HOVER)],
        lightcolor=[("disabled", BORDER), ("active", ACCENT_HOVER)],
        darkcolor=[("disabled", BORDER), ("active", ACCENT_DARK)],
    )

    style.configure(
        "Ghost.TButton",
        background=SURFACE_ALT,
        foreground=TEXT,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        focusthickness=0,
        relief="flat",
        borderwidth=1,
        padding=(12, 8),
        font=(FONT, 8),
    )
    style.map(
        "Ghost.TButton",
        background=[("disabled", SURFACE), ("pressed", BG), ("active", SURFACE_HOVER)],
        foreground=[("disabled", DISABLED), ("active", TEXT)],
        bordercolor=[("active", MUTED)],
    )

    style.configure(
        "Danger.TButton",
        background=SURFACE,
        foreground=DANGER,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        focusthickness=0,
        relief="flat",
        borderwidth=1,
        padding=(14, 10),
        font=(FONT, 9, "bold"),
    )
    style.map(
        "Danger.TButton",
        background=[
            ("disabled", SURFACE),
            ("pressed", DANGER_HOVER),
            ("active", DANGER_SOFT),
        ],
        foreground=[("disabled", DISABLED), ("active", "#FECDD3")],
        bordercolor=[("active", DANGER)],
    )

    style.configure(
        "Scan.TButton",
        background=ACCENT_SOFT,
        foreground="#C7D2FE",
        bordercolor="#3730A3",
        lightcolor="#3730A3",
        darkcolor="#3730A3",
        focusthickness=0,
        relief="flat",
        borderwidth=1,
        padding=(12, 8),
        font=(FONT, 8, "bold"),
    )
    style.map(
        "Scan.TButton",
        background=[("disabled", SURFACE), ("pressed", ACCENT_DARK), ("active", "#3730A3")],
        foreground=[("disabled", DISABLED), ("active", "#E0E7FF")],
        bordercolor=[("disabled", BORDER), ("active", ACCENT_HOVER)],
    )

    # ------------------------------------------------------------------
    # Entradas
    # ------------------------------------------------------------------
    entry_options = dict(
        fieldbackground=SURFACE_ALT,
        foreground=TEXT,
        insertcolor=TEXT,
        selectbackground=ACCENT_SOFT,
        selectforeground=TEXT,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        padding=(10, 8),
    )
    style.configure("Dark.TEntry", **entry_options)
    style.map(
        "Dark.TEntry",
        bordercolor=[("focus", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        darkcolor=[("focus", ACCENT)],
    )

    style.configure(
        "Dark.TCombobox",
        fieldbackground=SURFACE_ALT,
        background=SURFACE_ALT,
        foreground=TEXT,
        arrowcolor=MUTED,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        padding=(10, 7),
    )
    style.map(
        "Dark.TCombobox",
        fieldbackground=[("readonly", SURFACE_ALT), ("disabled", SURFACE)],
        foreground=[("readonly", TEXT), ("disabled", DISABLED)],
        selectbackground=[("readonly", SURFACE_ALT)],
        selectforeground=[("readonly", TEXT)],
        arrowcolor=[("active", TEXT), ("disabled", DISABLED)],
        bordercolor=[("focus", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        darkcolor=[("focus", ACCENT)],
    )

    root.option_add("*TCombobox*Listbox.background", SURFACE_ALT)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.font", (FONT, 9))
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # ------------------------------------------------------------------
    # Deslizador
    # ------------------------------------------------------------------
    style.configure(
        "Accent.Horizontal.TScale",
        background=ACCENT,
        troughcolor=SURFACE_ALT,
        bordercolor=BORDER_STRONG,
        lightcolor=ACCENT_HOVER,
        darkcolor=ACCENT_DARK,
        gripcount=0,
        sliderlength=14,
    )
    style.map(
        "Accent.Horizontal.TScale",
        background=[("active", ACCENT_HOVER), ("disabled", BORDER_STRONG)],
    )

    # ------------------------------------------------------------------
    # Barras de desplazamiento
    # ------------------------------------------------------------------
    style.configure(
        "Vertical.TScrollbar",
        background=BORDER_STRONG,
        troughcolor=SURFACE,
        bordercolor=SURFACE,
        lightcolor=SURFACE,
        darkcolor=SURFACE,
        arrowcolor=MUTED,
        gripcount=0,
        arrowsize=10,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", MUTED), ("pressed", ACCENT)],
    )

    return style
