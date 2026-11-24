"""Red local: direcciones propias, descubrimiento de receptores y escaneo.

El descubrimiento propio es la vía rápida: el emisor envía un ``probe`` UDP
a la dirección de broadcast y a ``127.0.0.1``; cada receptor en escucha
responde con su nombre y el puerto de audio. Tarda milisegundos.

Si no hay respuestas (por ejemplo, un receptor antiguo o un firewall que
bloquea el broadcast), se puede recurrir a un barrido ICMP de la subred.
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterable

from .config import (
    DEFAULT_PORT,
    DISCOVERY_MAGIC,
    DISCOVERY_PORT,
    DISCOVERY_TIMEOUT,
)

PROBE = DISCOVERY_MAGIC + b"?"
RESPONSE_PREFIX = DISCOVERY_MAGIC + b"!"
MAX_SCAN_HOSTS = 1024


# ---------------------------------------------------------------------------
# Direcciones
# ---------------------------------------------------------------------------
def primary_ip() -> str:
    """IP de la interfaz principal (sin enviar tráfico real)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def local_ips() -> list[str]:
    """Todas las IPv4 no loopback del equipo, la principal primero."""
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in addresses:
                addresses.append(ip)
    except OSError:
        pass

    primary = primary_ip()
    if primary and not primary.startswith("127.") and primary not in addresses:
        addresses.insert(0, primary)

    return addresses or [primary or "127.0.0.1"]


def ip_key(ip: str) -> tuple[int, ...]:
    """Clave de ordenación numérica para direcciones IPv4."""
    try:
        return tuple(int(part) for part in ip.split("."))
    except ValueError:
        return (999, 999, 999, 999)


def local_subnets(ips: Iterable[str] | None = None) -> list[ipaddress.IPv4Network]:
    """Redes /24 a las que pertenece el equipo (sin loopback)."""
    networks: list[ipaddress.IPv4Network] = []
    seen: set[ipaddress.IPv4Network] = set()
    for ip in ips if ips is not None else local_ips():
        try:
            network = ipaddress.ip_network(f"{ip}/24", strict=False)
        except ValueError:
            continue
        if network.is_loopback or network in seen:
            continue
        seen.add(network)
        networks.append(network)
    return networks


def normalize_ipv4(text: object) -> str | None:
    """Devuelve la IPv4 canónica, recortando espacios, o ``None``."""
    if not isinstance(text, str):
        return None
    try:
        return str(ipaddress.IPv4Address(text.strip()))
    except (ipaddress.AddressValueError, ValueError):
        return None


def is_valid_ipv4(text: str) -> bool:
    """Valida una IPv4 sin permitir espacios ni máscaras."""
    return normalize_ipv4(text) is not None


def is_valid_port(value: object) -> bool:
    """Valida un puerto UDP utilizable (1-65535)."""
    try:
        port = int(value)
    except (TypeError, ValueError):
        return False
    return 1 <= port <= 65535


# ---------------------------------------------------------------------------
# Descubrimiento
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Peer:
    """Receptor descubierto en la red."""

    ip: str
    port: int = DEFAULT_PORT
    name: str = ""

    @property
    def label(self) -> str:
        display = self.name or "Dispositivo"
        return f"{display} · {self.ip}:{self.port}"


class DiscoveryResponder:
    """Responde a los ``probe`` de descubrimiento mientras el receptor vive.

    ``on_error`` se invoca desde el hilo interno: debe ser thread-safe (por
    ejemplo, depositar el mensaje en una ``queue.Queue``).
    """

    def __init__(
        self,
        audio_port: int,
        name: str | None = None,
        port: int = DISCOVERY_PORT,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.audio_port = int(audio_port)
        self.name = (name or socket.gethostname() or "Receptor")[:60]
        self.port = int(port)
        self.on_error = on_error
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        payload = {"name": self.name, "port": self.audio_port}
        self._payload = RESPONSE_PREFIX + json.dumps(payload).encode("utf-8")

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, name="discovery-responder", daemon=True
            )
            self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        with self._lock:
            self._stop.set()
            thread = self._thread
            if (
                thread
                and thread.is_alive()
                and thread is not threading.current_thread()
            ):
                thread.join(timeout)
            if thread is None or not thread.is_alive():
                self._thread = None

    def _run(self) -> None:
        sock: socket.socket | None = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("", self.port))
            sock.settimeout(0.4)
            while not self._stop.is_set():
                try:
                    data, address = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if data.strip() != PROBE:
                    continue
                try:
                    sock.sendto(self._payload, address)
                except OSError:
                    pass
        except OSError as exc:
            if not self._stop.is_set() and self.on_error:
                self.on_error(
                    f"no se pudo escuchar en el puerto {self.port} ({exc})"
                )
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass


def _parse_response(data: bytes, ip: str) -> Peer | None:
    if not data.startswith(RESPONSE_PREFIX):
        return None
    try:
        payload = json.loads(data[len(RESPONSE_PREFIX):].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    port = payload.get("port", DEFAULT_PORT)
    if not is_valid_port(port):
        port = DEFAULT_PORT
    name = payload.get("name", "")
    name = name if isinstance(name, str) else str(name)
    name = name[:60]
    return Peer(ip=ip, port=int(port), name=name)


def discover(
    timeout: float = DISCOVERY_TIMEOUT,
    port: int = DISCOVERY_PORT,
) -> list[Peer]:
    """Busca receptores activos mediante broadcast UDP.

    También consulta ``127.0.0.1``, de modo que emisor y receptor pueden
    probarse en el mismo equipo.
    """
    sock: socket.socket | None = None
    peers: dict[tuple[str, int], Peer] = {}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", 0))
        sock.settimeout(0.15)
        targets = {"255.255.255.255", "127.0.0.1"}
        for network in local_subnets():
            targets.add(str(network.broadcast_address))

        for target in targets:
            try:
                sock.sendto(PROBE, (target, port))
            except OSError:
                continue

        deadline = time.monotonic() + max(0.2, float(timeout))
        while time.monotonic() < deadline:
            try:
                data, address = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            peer = _parse_response(data, address[0])
            if peer:
                peers[(peer.ip, peer.port)] = peer
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    return sorted(peers.values(), key=lambda peer: (ip_key(peer.ip), peer.port))


# ---------------------------------------------------------------------------
# Escaneo ICMP (alternativa)
# ---------------------------------------------------------------------------
def ping_host(
    ip: str,
    timeout_ms: int = 600,
    should_stop: Callable[[], bool] | None = None,
) -> bool:
    """Hace un ping a ``ip`` sin abrir ventanas de consola."""
    if should_stop and should_stop():
        return False

    if os.name == "nt":
        command = ["ping", "-n", "1", "-w", str(timeout_ms), "-4", ip]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        command = ["ping", "-c", "1", "-W", str(max(1, round(timeout_ms / 1000))), ip]
        creationflags = 0

    try:
        process = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_ms / 1000.0 + 1.5,
            creationflags=creationflags,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return process.returncode == 0


def scan_network(
    networks: Iterable[ipaddress.IPv4Network] | None = None,
    own_ips: Iterable[str] | None = None,
    max_workers: int = 64,
    should_stop: Callable[[], bool] | None = None,
) -> list[str]:
    """Barrido ICMP de las redes indicadas (por defecto las locales)."""
    networks = list(networks if networks is not None else local_subnets())
    ours = set(own_ips if own_ips is not None else local_ips())

    hosts: list[str] = []
    for network in networks:
        if network.is_loopback or network.num_addresses > MAX_SCAN_HOSTS:
            continue
        for host in network.hosts():
            ip = str(host)
            if ip not in ours:
                hosts.append(ip)

    if not hosts:
        return []

    found: set[str] = set()
    workers = max(1, min(max_workers, len(hosts)))
    executor: ThreadPoolExecutor | None = None
    try:
        executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ping")
        futures = {
            executor.submit(ping_host, ip, 600, should_stop): ip for ip in hosts
        }
        for future in as_completed(futures):
            if should_stop and should_stop():
                for pending in futures:
                    pending.cancel()
                break
            try:
                if future.result():
                    found.add(futures[future])
            except Exception:  # pragma: no cover - defensivo
                continue
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

    return sorted(found, key=ip_key)


def find_peers(
    timeout: float = DISCOVERY_TIMEOUT,
    sweep: bool = True,
    should_stop: Callable[[], bool] | None = None,
    on_stage: Callable[[str], None] | None = None,
    default_port: int = DEFAULT_PORT,
) -> list[Peer]:
    """Descubrimiento rápido con caída opcional a barrido ICMP.

    ``on_stage`` se invoca desde el hilo que llama a la función.
    """
    peers = discover(timeout=timeout)
    if peers or not sweep:
        return peers

    if on_stage:
        on_stage("Sin respuestas rápidas; escaneando la subred (puede tardar)…")
    addresses = scan_network(should_stop=should_stop)
    return [Peer(ip=ip, port=default_port) for ip in addresses]
