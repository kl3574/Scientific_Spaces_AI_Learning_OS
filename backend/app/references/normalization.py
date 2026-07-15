from __future__ import annotations

import ipaddress
import posixpath
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit


DOI_VERSION = "doi/v2"
ARXIV_VERSION = "arxiv/v1"
URL_VERSION = "url/v3"
TEXT_VERSION = "citation-text/v1"
NORMALIZATION_VERSION = "p3-003-normalization/v3"

_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9+@%]+$", re.IGNORECASE)
_ARXIV_MODERN = re.compile(r"^(?P<base>\d{4}\.\d{4,5})(?:v(?P<version>[1-9]\d*))?$", re.IGNORECASE)
_ARXIV_LEGACY = re.compile(
    r"^(?P<base>[a-z][a-z0-9.-]*(?:\.[a-z]{2})?/\d{7})(?:v(?P<version>[1-9]\d*))?$",
    re.IGNORECASE,
)
_TRACKING_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_PERCENT_ESCAPE = re.compile(r"%([0-9A-Fa-f]{2})")


@dataclass(frozen=True)
class NormalizationResult:
    reference_type: str
    classification: str
    canonical_key: str | None
    normalized_identifier: str | None = None
    normalized_url: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    arxiv_version: int | None = None
    display_value: str | None = None
    confidence: float = 0.0


def normalize_doi(raw: str) -> NormalizationResult:
    value = unicodedata.normalize("NFKC", raw).strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi\s*:\s*", "", value, flags=re.IGNORECASE).strip()
    value = _strip_terminal_punctuation(value)
    value = value.lower()
    if not _DOI_PATTERN.fullmatch(value) or any(char.isspace() for char in value):
        return NormalizationResult("malformed", "malformed", None, display_value=_bounded(raw), confidence=0.0)
    return NormalizationResult(
        "doi",
        "normalized",
        f"doi:{value}",
        normalized_identifier=value,
        doi=value,
        display_value=value,
        confidence=1.0,
    )


def normalize_arxiv(raw: str) -> NormalizationResult:
    value = unicodedata.normalize("NFKC", raw).strip()
    value = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^arxiv\s*:\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\.pdf$", "", value, flags=re.IGNORECASE)
    value = _strip_terminal_punctuation(value).lower()
    match = _ARXIV_MODERN.fullmatch(value) or _ARXIV_LEGACY.fullmatch(value)
    if match is None:
        return NormalizationResult("malformed", "malformed", None, display_value=_bounded(raw), confidence=0.0)
    base = match.group("base").lower()
    version_text = match.group("version")
    version = int(version_text) if version_text else None
    version_key = f"v{version}" if version is not None else "none"
    normalized = f"{base}v{version}" if version is not None else base
    return NormalizationResult(
        "arxiv",
        "normalized",
        f"arxiv:{base}:{version_key}",
        normalized_identifier=normalized,
        arxiv_id=base,
        arxiv_version=version,
        display_value=normalized,
        confidence=1.0,
    )


def normalize_url(raw: str, *, article_url: str) -> NormalizationResult:
    candidate = unicodedata.normalize("NFKC", raw).strip().strip("<>")
    candidate = _strip_url_terminal_punctuation(candidate)
    try:
        parsed_initial = urlsplit(candidate)
    except ValueError:
        return NormalizationResult(
            "malformed",
            "malformed",
            None,
            display_value=_redact_url(candidate),
            confidence=0.0,
        )
    relative = not parsed_initial.scheme
    if parsed_initial.scheme and parsed_initial.scheme.lower() not in {"http", "https"}:
        return NormalizationResult(
            "unsupported",
            "rejected",
            None,
            display_value=_redact_url(candidate),
            confidence=0.0,
        )
    resolved = urljoin(article_url, candidate) if relative else candidate
    try:
        parsed = urlsplit(resolved)
    except ValueError:
        return NormalizationResult(
            "malformed",
            "malformed",
            None,
            display_value=_redact_url(candidate),
            confidence=0.0,
        )
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return NormalizationResult("malformed", "malformed", None, display_value=_redact_url(candidate), confidence=0.0)
    if parsed.username is not None or parsed.password is not None:
        return NormalizationResult("http_url", "rejected", None, display_value=_redact_url(candidate), confidence=0.0)
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port
    except (UnicodeError, ValueError):
        return NormalizationResult("malformed", "malformed", None, display_value=_redact_url(candidate), confidence=0.0)
    if _is_local_or_unsafe_host(host):
        return NormalizationResult("http_url", "rejected", None, display_value=_redact_url(candidate), confidence=0.0)
    if (parsed.scheme.lower() == "http" and port == 80) or (parsed.scheme.lower() == "https" and port == 443):
        port = None
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc = f"{netloc}:{port}"
    path = _normalize_url_path(parsed.path or "/")
    query = _remove_tracking_query(parsed.query)
    fragment = parsed.fragment
    normalized = urlunsplit((parsed.scheme.lower(), netloc, path, query, fragment))
    reference_type = "relative_or_internal_url" if relative or _same_origin(article_url, normalized) else "http_url"
    return NormalizationResult(
        reference_type,
        "normalized",
        f"url:{normalized}",
        normalized_identifier=normalized if reference_type == "relative_or_internal_url" else None,
        normalized_url=normalized,
        display_value=normalized,
        confidence=0.9 if reference_type == "http_url" else 0.7,
    )


def normalize_citation_text(raw: str) -> NormalizationResult:
    display = _bounded(re.sub(r"\s+", " ", unicodedata.normalize("NFKC", raw)).strip(), 500)
    key = display.casefold()
    if len(key) < 8:
        return NormalizationResult("malformed", "malformed", None, display_value=display, confidence=0.0)
    return NormalizationResult(
        "citation_text",
        "ambiguous",
        None,
        normalized_identifier=key,
        display_value=display,
        confidence=0.45,
    )


def _strip_terminal_punctuation(value: str) -> str:
    value = value.rstrip()
    while value and value[-1] in ".,;:":
        value = value[:-1].rstrip()
    pairs = {")": "(", "]": "[", "}": "{"}
    while value and value[-1] in pairs and value.count(value[-1]) > value.count(pairs[value[-1]]):
        value = value[:-1].rstrip()
    return value


def _strip_url_terminal_punctuation(value: str) -> str:
    value = value.rstrip()
    while value and value[-1] in ".,;:":
        value = value[:-1]
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value


def _normalize_url_path(path: str) -> str:
    decoded = _PERCENT_ESCAPE.sub(
        lambda match: (
            chr(int(match.group(1), 16))
            if chr(int(match.group(1), 16)) in _UNRESERVED
            else f"%{match.group(1).upper()}"
        ),
        path,
    )
    normalized = posixpath.normpath(decoded)
    if path.startswith("/") and not normalized.startswith("/"):
        normalized = "/" + normalized
    if path.endswith("/") and not normalized.endswith("/"):
        normalized += "/"
    if normalized == ".":
        normalized = "/"
    return quote(normalized, safe="/%:@!$&'()*+,;=-._~")


def _remove_tracking_query(query: str) -> str:
    kept: list[str] = []
    for component in query.split("&") if query else []:
        raw_key = component.split("=", 1)[0]
        if unquote(raw_key).casefold() in _TRACKING_KEYS:
            continue
        kept.append(component)
    return "&".join(kept)


def _same_origin(left: str, right: str) -> bool:
    try:
        left_parts = urlsplit(left)
        right_parts = urlsplit(right)
        left_port = left_parts.port or (443 if left_parts.scheme.lower() == "https" else 80)
        right_port = right_parts.port or (443 if right_parts.scheme.lower() == "https" else 80)
    except ValueError:
        return False
    return (
        left_parts.scheme.lower() == right_parts.scheme.lower()
        and (left_parts.hostname or "").casefold() == (right_parts.hostname or "").casefold()
        and left_port == right_port
    )


def _is_local_or_unsafe_host(host: str) -> bool:
    lowered = host.casefold().rstrip(".")
    if lowered == "localhost" or lowered.endswith((".localhost", ".local")):
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def _redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-url>"
    if parsed.username is None and parsed.password is None:
        return _bounded(value)
    host = parsed.hostname or "redacted-host"
    netloc = f"[redacted]@{host}"
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port:
        netloc = f"{netloc}:{port}"
    return _bounded(urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)))


def _bounded(value: str, limit: int = 240) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"
