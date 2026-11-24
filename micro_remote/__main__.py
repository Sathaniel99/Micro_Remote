"""Punto de entrada unificado: ``python -m micro_remote``.

Ejemplos::

    python -m micro_remote emisor
    python -m micro_remote emisor --cli --host 192.168.1.20
    python -m micro_remote receptor --cli
    python -m micro_remote scan
    python -m micro_remote devices
"""

from __future__ import annotations

import argparse
import sys

from .config import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_GAIN,
    DEFAULT_PORT,
    DISCOVERY_TIMEOUT,
    MAX_GAIN,
    MIN_GAIN,
    validate_device,
    validate_duration,
    validate_gain,
    validate_port,
)


def _arg_type(function):
    """Adapta un validador de :mod:`config` a ``type=`` de argparse."""

    def convert(value: str):
        try:
            return function(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc

    return convert


_gain_type = _arg_type(validate_gain)
_device_type = _arg_type(validate_device)
_duration_type = _arg_type(validate_duration)
_port_type = _arg_type(validate_port)


def _positive_timeout(value: str) -> float:
    timeout = _arg_type(validate_duration)(value)
    if timeout <= 0:
        raise argparse.ArgumentTypeError("El tiempo de espera debe ser mayor que 0")
    return timeout


def _add_audio_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--gain",
        type=_gain_type,
        default=None,
        help=f"Ganancia/volumen inicial ({MIN_GAIN}-{MAX_GAIN}; por defecto se "
        f"usa el valor guardado o {DEFAULT_GAIN})",
    )
    parser.add_argument(
        "--device",
        type=_device_type,
        default=None,
        help="Índice de dispositivo de audio (ver «devices»)",
    )
    parser.add_argument(
        "--duration",
        type=_duration_type,
        default=0.0,
        help="Detener tras N segundos (0 = sin límite)",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Ejecutar sin interfaz gráfica",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micro-remote",
        description=f"{APP_NAME} {APP_VERSION} · audio en vivo por UDP en la red local",
    )
    subparsers = parser.add_subparsers(dest="command")

    sender = subparsers.add_parser("emisor", help="Emitir el micrófono")
    sender.set_defaults(_subparser=sender)
    sender.add_argument(
        "--host",
        default=None,
        help="IP del receptor (obligatoria con --cli; en la interfaz se puede "
        "elegir en la ventana)",
    )
    sender.add_argument(
        "--port",
        type=_port_type,
        default=None,
        help=f"Puerto UDP (por defecto: el guardado o {DEFAULT_PORT})",
    )
    _add_audio_options(sender)

    receiver = subparsers.add_parser("receptor", help="Escuchar audio")
    receiver.set_defaults(_subparser=receiver)
    receiver.add_argument(
        "--port",
        type=_port_type,
        default=None,
        help=f"Puerto UDP (por defecto: el guardado o {DEFAULT_PORT})",
    )
    _add_audio_options(receiver)

    scan = subparsers.add_parser("scan", help="Buscar receptores en la red")
    scan.set_defaults(_subparser=scan)
    scan.add_argument("--timeout", type=_positive_timeout, default=DISCOVERY_TIMEOUT)
    scan.add_argument(
        "--port",
        type=_port_type,
        default=None,
        help=f"Puerto a mostrar para hosts encontrados solo por ICMP "
        f"(por defecto: {DEFAULT_PORT})",
    )
    scan.add_argument(
        "--no-sweep",
        action="store_true",
        help="No hacer barrido ICMP si el descubrimiento no responde",
    )

    devices = subparsers.add_parser("devices", help="Listar dispositivos de audio")
    devices.set_defaults(_subparser=devices)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command_parser = getattr(args, "_subparser", parser)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "emisor":
        if args.cli:
            if not args.host:
                command_parser.error("el emisor por consola requiere --host")
            from .cli.emisor import run

            return run(args)
        from .ui.emisor import main as gui_main

        return gui_main(
            host=args.host, port=args.port, gain=args.gain, device=args.device
        )

    if args.command == "receptor":
        if args.cli:
            from .cli.receptor import run

            return run(args)
        from .ui.receptor import main as gui_main

        return gui_main(port=args.port, gain=args.gain, device=args.device)

    if args.command == "scan":
        from .cli.scan import run

        return run(args)

    if args.command == "devices":
        from .cli.devices import run

        return run(args)

    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
