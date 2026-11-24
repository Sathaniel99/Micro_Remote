"""Pruebas de utilidades de red y descubrimiento local."""

from __future__ import annotations

import socket
import time
import unittest

from micro_remote import net


class ValidationTests(unittest.TestCase):
    def test_ipv4(self) -> None:
        self.assertTrue(net.is_valid_ipv4("192.168.1.10"))
        self.assertTrue(net.is_valid_ipv4(" 10.0.0.1 "))
        self.assertFalse(net.is_valid_ipv4("999.1.1.1"))
        self.assertFalse(net.is_valid_ipv4("localhost"))
        self.assertFalse(net.is_valid_ipv4("192.168.1.1/24"))

    def test_port(self) -> None:
        self.assertTrue(net.is_valid_port("5000"))
        self.assertTrue(net.is_valid_port(65535))
        self.assertFalse(net.is_valid_port(0))
        self.assertFalse(net.is_valid_port(70000))
        self.assertFalse(net.is_valid_port("abc"))
        self.assertFalse(net.is_valid_port(None))

    def test_ip_key_orders_numerically(self) -> None:
        addresses = ["192.168.1.100", "10.0.0.2", "192.168.1.9"]
        ordered = sorted(addresses, key=net.ip_key)
        self.assertEqual(ordered, ["10.0.0.2", "192.168.1.9", "192.168.1.100"])

    def test_normalize_ipv4_strips_spaces(self) -> None:
        self.assertEqual(net.normalize_ipv4(" 10.0.0.1 "), "10.0.0.1")
        self.assertIsNone(net.normalize_ipv4(None))
        self.assertIsNone(net.normalize_ipv4("999.1.1.1"))


class LocalNetworkTests(unittest.TestCase):
    def test_local_ips_are_valid(self) -> None:
        addresses = net.local_ips()
        self.assertTrue(addresses)
        for address in addresses:
            self.assertTrue(net.is_valid_ipv4(address), address)

    def test_local_subnets_are_slash_24(self) -> None:
        for network in net.local_subnets():
            self.assertEqual(network.prefixlen, 24)
            self.assertFalse(network.is_loopback)


class DiscoveryTests(unittest.TestCase):
    def test_round_trip_on_loopback(self) -> None:
        port = 5099
        errors: list[str] = []
        responder = net.DiscoveryResponder(
            audio_port=6123,
            name="Sala de pruebas",
            port=port,
            on_error=errors.append,
        )
        responder.start()
        self.addCleanup(responder.stop)
        time.sleep(0.25)
        if errors:
            self.skipTest(f"No se pudo abrir UDP: {errors[0]}")

        peers = net.discover(timeout=0.8, port=port)
        self.assertTrue(peers, "el respondedor local debería ser visible")
        peer = next((item for item in peers if item.port == 6123), None)
        self.assertIsNotNone(peer)
        assert peer is not None
        self.assertEqual(peer.name, "Sala de pruebas")
        self.assertTrue(net.is_valid_ipv4(peer.ip))

    def test_no_responder_returns_empty(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        peers = net.discover(timeout=0.3, port=port)
        self.assertEqual(peers, [])

    def test_malformed_response_is_ignored(self) -> None:
        self.assertIsNone(net._parse_response(b"MRD1![1,2]", "1.2.3.4"))
        peer = net._parse_response(b"MRD1!{}", "1.2.3.4")
        self.assertIsNotNone(peer)
        assert peer is not None
        self.assertEqual(peer.port, 5000)
        peer = net._parse_response(b'MRD1!{"port": 6123, "name": 7}', "1.2.3.4")
        self.assertIsNotNone(peer)
        assert peer is not None
        self.assertEqual(peer.port, 6123)
        self.assertEqual(peer.name, "7")


if __name__ == "__main__":
    unittest.main()
