"""Genera iconos ``.ico`` multi-resolución a partir de imágenes.

Uso::

    python -m micro_remote.tools.icons
    python -m micro_remote.tools.icons --source icons --output icons/ico

Por cada ``.jpg``, ``.jpeg`` o ``.png`` de la carpeta de origen crea un
``.ico`` con resoluciones de 16 a 256 px, centrado y manteniendo la
proporción. Requiere Pillow (incluido en ``requirements-dev.txt``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..resources import app_root

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
CANVAS = (256, 256)


def _pillow():
    try:
        from PIL import Image
    except (ImportError, OSError) as exc:  # pragma: no cover - depende del entorno
        raise SystemExit(
            "Pillow no está instalado. Ejecuta: pip install -r requirements-dev.txt"
        ) from exc
    return Image


def convert_image(source: Path, destination: Path) -> None:
    """Convierte una imagen a un ``.ico`` multi-resolución."""
    Image = _pillow()
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    with Image.open(source) as original:
        image = original.convert("RGBA")
    image.thumbnail(CANVAS, resampling)

    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    offset = ((CANVAS[0] - image.width) // 2, (CANVAS[1] - image.height) // 2)
    canvas.paste(image, offset, image)

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="ICO", sizes=ICO_SIZES)


def convert_directory(source_dir: Path, output_dir: Path) -> tuple[int, int]:
    """Convierte todas las imágenes de ``source_dir``. Devuelve (ok, fallos)."""
    if not source_dir.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de origen: {source_dir}")

    images = sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        print(f"⚠ No se encontraron imágenes en {source_dir}")
        return 0, 0

    print(f"Origen : {source_dir}")
    print(f"Salida : {output_dir}")
    print(f"Imágenes: {len(images)}\n")

    converted = 0
    failed = 0
    for image in images:
        destination = output_dir / f"{image.stem}.ico"
        try:
            convert_image(image, destination)
        except Exception as exc:  # pragma: no cover - defensivo
            failed += 1
            print(f"✗ {image.name}: {exc}")
        else:
            converted += 1
            print(f"✓ {image.name} → {destination.name} (256×256 multi-res)")

    print(f"\nListo: {converted} convertidos, {failed} fallidos.")
    return converted, failed


def main(argv: list[str] | None = None) -> int:
    """Entrada de consola de la herramienta de iconos."""
    root = app_root()
    parser = argparse.ArgumentParser(
        prog="micro-remote-icons",
        description="Convierte imágenes a iconos .ico multi-resolución",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=root / "icons",
        help="Carpeta con las imágenes de origen (por defecto: icons/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "icons" / "ico",
        help="Carpeta de salida (por defecto: icons/ico/)",
    )
    args = parser.parse_args(argv)

    try:
        converted, failed = convert_directory(args.source, args.output)
    except FileNotFoundError as exc:
        print(f"✗ {exc}")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
