"""
Web scraper with SSRF protection.
Fetches a given public HTTP(S) URL and returns the BeautifulSoup tree.
"""

import re
import ipaddress
import logging
import socket
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("citelytics.scraper")

TIMEOUT = 15          # seconds
MAX_BYTES = 5_000_000  # 5 MB

# Private / reserved address blocks
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}

BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Citelytics/1.0; "
        "+https://github.com/stephinarnold) research-scraper"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class ScrapingError(Exception):
    """Raised when scraping cannot be completed."""


def _check_ssrf(url: str) -> None:
    """Raise ScrapingError if the URL targets a private/internal host."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ScrapingError("Only http/https URLs are allowed.")

    host = parsed.hostname or ""

    if host.lower() in BLOCKED_HOSTS:
        raise ScrapingError(f"Requests to '{host}' are not allowed.")

    # Check cloud metadata endpoint
    if host in ("169.254.169.254", "metadata.google.internal"):
        raise ScrapingError("Requests to cloud metadata endpoints are not allowed.")

    # Resolve host and check IP
    try:
        ip_str = socket.gethostbyname(host)
    except socket.gaierror as exc:
        raise ScrapingError(f"Could not resolve host '{host}': {exc}") from exc

    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        raise ScrapingError(f"Invalid IP resolved for '{host}'.")

    for network in BLOCKED_RANGES:
        if ip in network:
            raise ScrapingError(
                f"Requests to private/internal IP addresses are not allowed ({ip_str})."
            )


MAX_REDIRECTS = 5
_ROBOTS_CACHE: dict = {}


def _check_robots_txt(url: str) -> None:
    """Raise ScrapingError if robots.txt disallows our user-agent on this path.

    Cached per-host for the lifetime of the process so a batch pipeline run
    doesn't refetch robots.txt for every page on the same domain.
    """
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _ROBOTS_CACHE:
        rp = RobotFileParser()
        rp.set_url(urljoin(origin, "/robots.txt"))
        try:
            rp.read()
        except Exception:
            # If robots.txt can't be fetched/parsed, default to allow
            # (most sites with no robots.txt permit crawling).
            rp = None
        _ROBOTS_CACHE[origin] = rp

    rp = _ROBOTS_CACHE[origin]
    if rp is not None and not rp.can_fetch(HEADERS["User-Agent"], url):
        raise ScrapingError(f"robots.txt disallows fetching this URL for our user-agent.")


def scrape(url: str) -> dict:
    """
    Fetch the URL, parse HTML, and return a dict with:
      - soup: BeautifulSoup object
      - raw_html: str
      - status_code: int
      - final_url: str (after redirects)

    Redirects are followed manually (allow_redirects=False) with _check_ssrf
    re-run on every hop. requests' own allow_redirects=True does its own DNS
    resolution on each redirect target without re-validating it, which would
    let a malicious URL 302 to a private/internal IP and bypass the SSRF
    guard entirely.
    """
    current_url = url
    _check_ssrf(current_url)
    _check_robots_txt(current_url)

    try:
        for _ in range(MAX_REDIRECTS + 1):
            resp = requests.get(
                current_url,
                headers=HEADERS,
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
            if resp.is_redirect or resp.is_permanent_redirect:
                next_url = resp.headers.get("Location")
                if not next_url:
                    raise ScrapingError("Redirect response had no Location header.")
                current_url = urljoin(current_url, next_url)
                _check_ssrf(current_url)
                _check_robots_txt(current_url)
                continue
            resp.raise_for_status()
            break
        else:
            raise ScrapingError("Too many redirects while fetching the URL.")
    except requests.exceptions.Timeout:
        raise ScrapingError("The request timed out. The website may be slow or unreachable.")
    except requests.exceptions.TooManyRedirects:
        raise ScrapingError("Too many redirects while fetching the URL.")
    except requests.exceptions.ConnectionError as exc:
        raise ScrapingError(f"Could not connect to the website: {exc}")
    except requests.exceptions.HTTPError as exc:
        raise ScrapingError(f"HTTP error: {exc}")

    # Limit response size
    content_bytes = b""
    for chunk in resp.iter_content(chunk_size=65536):
        content_bytes += chunk
        if len(content_bytes) > MAX_BYTES:
            break

    raw_html = content_bytes.decode("utf-8", errors="replace")

    if len(raw_html.strip()) < 100:
        raise ScrapingError(
            "The page appears to be empty or contains insufficient readable content."
        )

    soup = BeautifulSoup(raw_html, "lxml")

    # Remove script/style noise
    for tag in soup(["script", "style", "noscript", "svg", "path"]):
        tag.decompose()

    return {
        "soup": soup,
        "raw_html": raw_html,
        "status_code": resp.status_code,
        "final_url": resp.url,
    }
