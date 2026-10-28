"""Indicators of compromise found in DEX strings: URLs, IPs, risky endpoints."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from ..data.apis import DYNAMIC_DNS_SUFFIXES
from ..models import Finding, Report, Severity
from .dex import DexFacts

MODULE = "strings"
MAX_IOCS = 100

URL_RE = re.compile(r"https?://[^\s\"'<>\\]{4,300}", re.IGNORECASE)
IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
TELEGRAM_RE = re.compile(r"api\.telegram\.org/bot", re.IGNORECASE)
DISCORD_RE = re.compile(r"discord(?:app)?\.com/api/webhooks/", re.IGNORECASE)


def _public_ip(text: str) -> str | None:
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return None
    if ip.is_private or ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved:
        return None
    return text


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def analyze(facts: DexFacts, report: Report) -> None:
    urls: set[str] = set()
    ips: set[str] = set()
    for text in facts.strings:
        urls.update(URL_RE.findall(text))
        for match in IP_RE.findall(text):
            if (ip := _public_ip(match)):
                ips.add(ip)

    hosts = {h for h in map(_host, urls) if h}
    report.iocs = {
        "urls": sorted(urls)[:MAX_IOCS],
        "domains": sorted(h for h in hosts if not _public_ip(h))[:MAX_IOCS],
        "ips": sorted(ips)[:MAX_IOCS],
    }

    if any(TELEGRAM_RE.search(s) for s in facts.strings):
        report.add(Finding("strings.telegram_bot", Severity.HIGH, MODULE))
    if any(DISCORD_RE.search(s) for s in facts.strings):
        report.add(Finding("strings.discord_webhook", Severity.HIGH, MODULE))

    ip_hosts = sorted(h for h in hosts if _public_ip(h))
    if ip_hosts:
        report.add(Finding("strings.ip_endpoint", Severity.MEDIUM, MODULE,
                           {"count": len(ip_hosts), "examples": ip_hosts[:5]}))
    dyn = sorted(h for h in hosts if h.endswith(DYNAMIC_DNS_SUFFIXES))
    if dyn:
        report.add(Finding("strings.dynamic_dns", Severity.MEDIUM, MODULE,
                           {"hosts": dyn[:5]}))
    onion = sorted(h for h in hosts if h.endswith(".onion"))
    if onion:
        report.add(Finding("strings.onion", Severity.MEDIUM, MODULE,
                           {"hosts": onion[:5]}))
