"""Web fetcher with pinned IP, CIDR blocklist, monotonic deadline, async DNS.

Closes P1-3 (SSRF multi-A + deadline), P4-3 (blocking getaddrinfo), P3-7
(redirect chain counter on call stack).
"""
from __future__ import annotations
import concurrent.futures
import http.client
import ipaddress
import socket
import ssl
import time
from typing import Final
from urllib.parse import urlparse

_PRIVATE_NETS: Final = [
    ipaddress.ip_network(n) for n in (
        "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "169.254.0.0/16", "100.64.0.0/10",
        "::1/128", "fc00::/7", "fe80::/10", "ff00::/8",
    )
]

_DNS_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="bp-dns")


def _ip_is_blocked(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return (
            any(a in n for n in _PRIVATE_NETS)
            or a.is_reserved
            or a.is_multicast
            or a.is_unspecified
        )
    except ValueError:
        return True


def _resolve_all_and_pin(host: str, deadline: float) -> str:
    dns_budget = min(2.0, max(0.5, deadline - time.monotonic()))
    fut = _DNS_POOL.submit(
        socket.getaddrinfo, host, None, socket.AF_UNSPEC, socket.SOCK_STREAM
    )
    try:
        infos = fut.result(timeout=dns_budget)
    except concurrent.futures.TimeoutError:
        fut.cancel()
        raise TimeoutError(f"DNS timeout for {host}")
    if not infos:
        raise ValueError(f"unresolvable: {host}")
    ips = {info[4][0] for info in infos}
    for ip in ips:
        if _ip_is_blocked(ip):
            raise ValueError(f"private address in record set for {host}: {ip}")
    return next(iter(ips))


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, pinned_ip: str, port: int = 443,
                 context: ssl.SSLContext | None = None, timeout: float = 10.0):
        super().__init__(host, port=port, context=context, timeout=timeout)
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._pinned_ip, self.port),
            timeout=self.timeout,
        )
        peer = self.sock.getpeername()[0]
        if peer != self._pinned_ip:
            self.sock.close()
            raise ConnectionError(
                f"peer address {peer} != pinned {self._pinned_ip}"
            )
        if self._context is not None:
            self.sock = self._context.wrap_socket(
                self.sock, server_hostname=self.host
            )


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, pinned_ip: str, port: int = 80,
                 timeout: float = 10.0):
        super().__init__(host, port=port, timeout=timeout)
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._pinned_ip, self.port),
            timeout=self.timeout,
        )


def fetch(
    url: str,
    *,
    deadline: float,
    max_bytes: int,
    redirects_remaining: int = 2,
) -> bytes:
    """Fetch URL. Respects monotonic deadline, returns on 2xx or raises.

    §F3/G10: DNS async + resolve-all-and-check; pin + re-pin on redirect.
    §G7: redirect chain counter on call stack.
    """
    if time.monotonic() >= deadline:
        raise TimeoutError("research deadline exceeded before fetch")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"scheme not allowed: {parsed.scheme}")
    if parsed.hostname is None:
        raise ValueError("no host in url")
    pinned = _resolve_all_and_pin(parsed.hostname, deadline)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    remaining = max(0.5, deadline - time.monotonic())
    if parsed.scheme == "https":
        ctx = ssl.create_default_context()
        conn = _PinnedHTTPSConnection(parsed.hostname, pinned, port, context=ctx, timeout=remaining)
    else:
        conn = _PinnedHTTPConnection(parsed.hostname, pinned, port, timeout=remaining)
    try:
        path = parsed.path or "/"
        if parsed.query:
            path = path + "?" + parsed.query
        conn.request("GET", path, headers={
            "User-Agent": "BrainPass-Research/0.1 (github.com/coderook520/BrainPass)",
            "Accept": "text/html, text/plain, application/json",
        })
        resp = conn.getresponse()
        if resp.status in (301, 302, 303, 307, 308):
            if redirects_remaining <= 0:
                raise ValueError("redirect chain cap reached")
            loc = resp.getheader("Location")
            if not loc:
                raise ValueError("redirect without Location")
            conn.close()
            if loc.startswith("/"):
                # relative — resolve against original
                loc = f"{parsed.scheme}://{parsed.hostname}{loc}"
            return fetch(loc, deadline=deadline, max_bytes=max_bytes,
                          redirects_remaining=redirects_remaining - 1)
        content_type = resp.getheader("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in ("text/html", "text/plain", "application/json"):
            raise ValueError(f"content-type not allowed: {content_type}")
        if resp.status != 200:
            raise ValueError(f"HTTP {resp.status}")
        body = resp.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("response exceeds max_bytes")
        return body
    finally:
        try:
            conn.close()
        except Exception:
            pass


def fetch_with_retry(
    url: str,
    *,
    deadline: float,
    max_bytes: int,
    max_attempts: int = 2,
) -> bytes:
    import random
    last_exc: Exception | None = None
    for attempt in range(max_attempts + 1):
        if time.monotonic() >= deadline:
            raise TimeoutError("research deadline exceeded")
        try:
            return fetch(url, deadline=deadline, max_bytes=max_bytes)
        except (TimeoutError, ConnectionError, socket.gaierror) as e:
            last_exc = e
            if attempt >= max_attempts:
                raise
            remaining = deadline - time.monotonic()
            delay = min(max(0.0, remaining), (2 ** attempt) * 0.5 + random.random() * 0.5)
            if delay <= 0:
                raise
            time.sleep(delay)
        except http.client.HTTPException as e:
            last_exc = e
            raise  # fail-fast on protocol errors
    raise last_exc or TimeoutError("fetch retries exhausted")
