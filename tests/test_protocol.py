"""Pruebas del protocolo de paquetes y del contador de secuencias."""

from __future__ import annotations

import unittest

from micro_remote import protocol


class PacketTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        payload = b"\x01\x02\x03\x04"
        raw = protocol.build_packet(7, payload)
        self.assertEqual(len(raw), protocol.HEADER_SIZE + len(payload))
        packet = protocol.parse_packet(raw)
        self.assertIsNotNone(packet)
        assert packet is not None
        self.assertEqual(packet.sequence, 7)
        self.assertEqual(packet.payload, payload)
        self.assertFalse(packet.legacy)

    def test_sequence_wraps(self) -> None:
        packet = protocol.parse_packet(protocol.build_packet(-1, b"\x00\x00"))
        assert packet is not None
        self.assertEqual(packet.sequence, protocol.MAX_SEQUENCE)

    def test_legacy_packet_without_header(self) -> None:
        packet = protocol.parse_packet(b"\x00\x01\x00\x02")
        assert packet is not None
        self.assertTrue(packet.legacy)
        self.assertEqual(packet.sequence, protocol.LEGACY_SEQUENCE)
        self.assertEqual(packet.payload, b"\x00\x01\x00\x02")

    def test_odd_length_is_rejected(self) -> None:
        self.assertIsNone(protocol.parse_packet(b"\x00\x01\x02"))
        header = protocol.HEADER_STRUCT.pack(protocol.MAGIC, protocol.VERSION, 0, 1)
        self.assertIsNone(protocol.parse_packet(header + b"\x00\x01\x02"))

    def test_oversized_datagram_is_rejected(self) -> None:
        data = protocol.MAGIC + b"\x00" * (protocol.MAX_DATAGRAM_BYTES + 1)
        self.assertIsNone(protocol.parse_packet(data))

    def test_unsupported_version_is_discarded(self) -> None:
        header = protocol.HEADER_STRUCT.pack(protocol.MAGIC, 99, 0, 1)
        self.assertIsNone(protocol.parse_packet(header + b"\x00\x00"))

    def test_empty_payload_is_rejected(self) -> None:
        self.assertIsNone(protocol.parse_packet(b""))
        self.assertIsNone(protocol.parse_packet(b"\x00"))
        header = protocol.HEADER_STRUCT.pack(protocol.MAGIC, protocol.VERSION, 0, 1)
        self.assertIsNone(protocol.parse_packet(header))


class SequenceTrackerTests(unittest.TestCase):
    def test_in_order(self) -> None:
        tracker = protocol.SequenceTracker()
        for sequence in range(10):
            self.assertEqual(tracker.update(sequence), "ok")
        self.assertEqual(tracker.received, 10)
        self.assertEqual(tracker.lost, 0)

    def test_gap_counts_lost(self) -> None:
        tracker = protocol.SequenceTracker()
        tracker.update(1)
        self.assertEqual(tracker.update(4), "lost")
        self.assertEqual(tracker.lost, 2)
        self.assertEqual(tracker.received, 2)

    def test_late_packet_decrements_lost(self) -> None:
        tracker = protocol.SequenceTracker()
        tracker.update(1)
        tracker.update(4)
        self.assertEqual(tracker.lost, 2)
        self.assertEqual(tracker.update(2), "late")
        self.assertEqual(tracker.lost, 1)
        self.assertEqual(tracker.update(3), "late")
        self.assertEqual(tracker.lost, 0)
        self.assertEqual(tracker.late, 2)

    def test_duplicates_and_late(self) -> None:
        tracker = protocol.SequenceTracker()
        tracker.update(10)
        self.assertEqual(tracker.update(10), "duplicate")
        self.assertEqual(tracker.update(9), "late")
        self.assertEqual(tracker.duplicates, 1)
        self.assertEqual(tracker.late, 1)

    def test_duplicates_do_not_inflate_loss_ratio(self) -> None:
        tracker = protocol.SequenceTracker()
        tracker.update(0)
        tracker.update(3)
        tracker.update(3)
        self.assertEqual(tracker.duplicates, 1)
        self.assertAlmostEqual(tracker.loss_ratio, 0.5)

    def test_wrap_around(self) -> None:
        tracker = protocol.SequenceTracker()
        tracker.update(protocol.MAX_SEQUENCE - 1)
        self.assertEqual(tracker.update(protocol.MAX_SEQUENCE), "ok")
        self.assertEqual(tracker.update(0), "ok")
        self.assertEqual(tracker.lost, 0)

    def test_legacy_is_counted_but_not_ordered(self) -> None:
        tracker = protocol.SequenceTracker()
        self.assertEqual(tracker.update(-1), "legacy")
        self.assertIsNone(tracker._last)
        self.assertEqual(tracker.received, 1)

    def test_loss_ratio(self) -> None:
        tracker = protocol.SequenceTracker()
        tracker.update(0)
        tracker.update(3)
        # 2 recibidos + 2 perdidos (secuencias 1 y 2) => 50 %
        self.assertAlmostEqual(tracker.loss_ratio, 0.5)


if __name__ == "__main__":
    unittest.main()
