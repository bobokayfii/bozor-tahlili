from __future__ import annotations

import re
import socket
import tempfile
from contextlib import contextmanager
from pathlib import Path

import certifi
import requests
from bs4 import BeautifulSoup

_DOH_RESOLVER = "https://cloudflare-dns.com/dns-query"
_CERTS_DIR = Path(__file__).parent / "certs"
_ca_bundle_cache: dict[str, str] = {}

# xb.uz's authoritative nameserver actively refuses queries from outside
# Uzbekistan (confirmed directly against Google 8.8.8.8, Cloudflare 1.1.1.1,
# and Quad9 9.9.9.9 over raw UDP/53 — all three return an empty answer, not
# a timeout). No public DNS-over-HTTPS resolver can produce a fresh record
# for it from here, so _resolve_via_doh alone cannot reach it. This is a
# last-resort static fallback, used only when live resolution fails
# entirely: an IP observed serving xb.uz correctly over a verified TLS
# handshake (see _resolve_hostname_as — the certificate is still validated
# against the real hostname, this only substitutes the address). If xb.uz
# moves hosts, this will need updating; scraper failures for this bank
# specifically are the signal to check.
_STATIC_IP_FALLBACK: dict[str, str] = {
    "xb.uz": "89.249.62.181",
}


def _build_ca_bundle(extra_cert_file: str) -> str:
    """Some bank servers (e.g. infinbank.com) send only their leaf
    certificate and omit the intermediate CA cert, which browsers paper over
    by fetching the intermediate via the certificate's AIA extension and
    caching it — a fresh requests client with only root CAs has no such
    cache and fails verification. The missing intermediate for each such
    bank is fetched once (via that same AIA URL) and checked into
    scrapers/certs/; this appends it to certifi's current root bundle at
    runtime (never persisted — certifi's bundle changes with each upgrade,
    so a cached-on-disk combination could go stale) to build a temporary CA
    file, restoring full, correct chain verification with no bypass."""
    if extra_cert_file not in _ca_bundle_cache:
        root_bundle = Path(certifi.where()).read_text(encoding="utf-8")
        extra_cert = (_CERTS_DIR / extra_cert_file).read_text(encoding="utf-8")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pem", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(root_bundle + "\n" + extra_cert)
            _ca_bundle_cache[extra_cert_file] = tmp.name
    return _ca_bundle_cache[extra_cert_file]


def fetch_html(url: str, timeout: int = 15, extra_ca_cert: str | None = None) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BankAnalizBot/1.0)"}
    verify = _build_ca_bundle(extra_ca_cert) if extra_ca_cert else True
    try:
        response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
        response.raise_for_status()
        return response.text
    except requests.exceptions.ConnectionError:
        html = _fetch_with_doh_resolved_dns(url, headers, timeout, verify)
        if html is None:
            raise
        return html


def _fetch_with_doh_resolved_dns(url: str, headers: dict[str, str], timeout: int, verify: bool | str) -> str | None:
    """A handful of .uz bank domains (e.g. xb.uz) are only resolvable through
    Uzbekistan-local authoritative nameservers; this environment's own DNS
    resolver can't reach them, so requests.get fails with a connection error
    before it ever reaches the server. Resolve the hostname's A record via a
    public DNS-over-HTTPS service instead, then retry the exact same
    request with only address resolution for that one hostname redirected
    to the resolved IP — the URL, Host header, TLS SNI, and certificate
    hostname verification are all untouched, so this is not a verification
    bypass, just a substitute resolver."""
    hostname = requests.utils.urlparse(url).hostname
    if not hostname:
        return None
    ip = _resolve_via_doh(hostname) or _STATIC_IP_FALLBACK.get(hostname)
    if ip is None:
        return None
    with _resolve_hostname_as(hostname, ip):
        response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    response.raise_for_status()
    return response.text


@contextmanager
def _resolve_hostname_as(hostname: str, ip: str):
    original_getaddrinfo = socket.getaddrinfo

    def patched_getaddrinfo(host, *args, **kwargs):
        return original_getaddrinfo(ip if host == hostname else host, *args, **kwargs)

    socket.getaddrinfo = patched_getaddrinfo
    try:
        yield
    finally:
        socket.getaddrinfo = original_getaddrinfo


def _resolve_via_doh(hostname: str) -> str | None:
    try:
        response = requests.get(
            _DOH_RESOLVER,
            params={"name": hostname, "type": "A"},
            headers={"accept": "application/dns-json"},
            timeout=5,
        )
        response.raise_for_status()
        for answer in response.json().get("Answer", []):
            if answer.get("type") == 1:
                return answer["data"]
    except requests.RequestException:
        pass
    return None


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def extract_section(text: str, start_heading: str, end_heading: str | None) -> str:
    start_idx = text.find(start_heading)
    if start_idx == -1:
        return ""
    start_idx += len(start_heading)
    if end_heading:
        end_idx = text.find(end_heading, start_idx)
        if end_idx == -1:
            end_idx = len(text)
    else:
        end_idx = len(text)
    return text[start_idx:end_idx]


def extract_percentages(text: str) -> list[float]:
    matches = re.findall(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%", text)
    values = [float(m.replace(",", ".")) for m in matches]
    seen: list[float] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


_TERM_RANGE_RE = re.compile(r"(\d{1,3})\s*oydan\s*(\d{1,3})\s*oygacha")
_TERM_SINGLE_RE = re.compile(r"(\d{1,3})\s*oygacha")
_TERM_YEAR_RANGE_RE = re.compile(r"(\d{1,2})\s*yildan\s*(\d{1,2})\s*yilgacha")
_TERM_YEAR_SINGLE_RE = re.compile(r"(\d{1,2})\s*yilgacha")


def extract_term_months(text: str) -> list[int]:
    """Muddat oralig'ini "N oydan M oygacha" (masalan, "12 oydan 60 oygacha")
    range shaklidan topadi. Agar range topilmasa, yagona "N oygacha"
    ko'rsatkichiga tushadi. Ba'zi banklar muddatni oy o'rniga yilda beradi
    ("5 yilgacha" kabi) — bunday qiymatlar oyga aylantiriladi (1 yil = 12 oy).

    Range topilganda undan tashqaridagi bitta "N oygacha" iboralari (masalan,
    "Imtiyozli davr: 6 oygacha" kabi imtiyozli davr ko'rsatkichlari) e'tiborga
    olinmaydi — aks holda ular asosiy muddat oralig'iga aralashib, noto'g'ri
    term_min/term_max qiymatlarini keltirib chiqaradi.
    """
    range_matches = _TERM_RANGE_RE.findall(text)
    year_range_matches = _TERM_YEAR_RANGE_RE.findall(text)
    if range_matches or year_range_matches:
        values = {int(lo) for lo, hi in range_matches} | {int(hi) for lo, hi in range_matches}
        values |= {int(lo) * 12 for lo, hi in year_range_matches}
        values |= {int(hi) * 12 for lo, hi in year_range_matches}
    else:
        values = {int(m) for m in _TERM_SINGLE_RE.findall(text)}
        values |= {int(m) * 12 for m in _TERM_YEAR_SINGLE_RE.findall(text)}
    return sorted(v for v in values if v <= 120)


def extract_amount_som(text: str) -> int | None:
    mln_matches = re.findall(r"(\d{1,5})\s*mln\.?\s*so", text, flags=re.IGNORECASE)
    mlrd_matches = re.findall(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*mlrd\.?\s*so", text, flags=re.IGNORECASE)
    amounts = [int(m) * 1_000_000 for m in mln_matches]
    amounts += [int(float(m.replace(",", "."))) * 1_000_000_000 for m in mlrd_matches]
    return max(amounts) if amounts else None


def has_collateral_requirement(text: str) -> bool:
    lowered = text.lower()
    if "mavjud emas" in lowered or "garovsiz" in lowered:
        return False
    return "garov" in lowered
