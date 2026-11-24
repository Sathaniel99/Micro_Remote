"""Pruebas de los lanzadores y validación de argumentos CLI."""

from __future__ import annotations

import io
import unittest
from unittest import mock

from cmd_emisor import build_argv
from micro_remote.__main__ import build_parser, main


class LegacyWrappersTests(unittest.TestCase):
    def test_positional_host_is_converted(self) -> None:
        self.assertEqual(
            build_argv(["192.168.1.20", "--port", "6000"]),
            ["--host", "192.168.1.20", "--port", "6000"],
        )

    def test_options_are_left_untouched(self) -> None:
        self.assertEqual(
            build_argv(["--host", "192.168.1.20"]),
            ["--host", "192.168.1.20"],
        )


class ParserValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = build_parser()
        self.stderr = io.StringIO()
        patcher = mock.patch("sys.stderr", self.stderr)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_invalid_gain_is_rejected(self) -> None:
        for value in ("nan", "inf", "-1", "5.1"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                self.parser.parse_args(
                    ["emisor", "--cli", "--host", "1.2.3.4", "--gain", value]
                )

    def test_invalid_device_duration_and_port_are_rejected(self) -> None:
        cases = (
            ["emisor", "--device", "-1"],
            ["receptor", "--duration", "-2"],
            ["receptor", "--port", "70000"],
            ["scan", "--timeout", "0"],
        )
        for argv in cases:
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                self.parser.parse_args(argv)

    def test_valid_arguments_are_accepted(self) -> None:
        args = self.parser.parse_args(
            [
                "emisor",
                "--cli",
                "--host",
                "192.168.1.20",
                "--port",
                "6000",
                "--gain",
                "2.5",
                "--device",
                "1",
                "--duration",
                "3",
            ]
        )
        self.assertEqual(args.host, "192.168.1.20")
        self.assertEqual(args.port, 6000)
        self.assertEqual(args.gain, 2.5)
        self.assertEqual(args.device, 1)
        self.assertEqual(args.duration, 3.0)

    def test_cli_without_host_exits(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main(["emisor", "--cli"])
        self.assertEqual(context.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
