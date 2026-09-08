#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Iterator
from urllib.error import URLError
from urllib.parse import parse_qs, parse_qsl, unquote, unquote_plus, urlencode, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
FRONTEND_ROOT = ROOT / "frontend"
ARTICLE_FIXTURE = BACKEND_ROOT / "tests" / "fixtures" / "evaluation" / "articles.json"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.graph.builder import KnowledgeGraphBuilder
from app.graph.store import GraphStore
from app.rag.full_corpus import compute_corpus_fingerprint
from app.references.deduplication import build_reference_data
from app.references.extraction import extract_article_references
from app.references.matching import match_reference_records
from app.references.store import install_reference_store
from app.storage.article_store import StoredArticle


API_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:3000"
# NEXT_PUBLIC_API_BASE_URL is compiled into the checked production build.
BROWSER_API_URL = "http://localhost:8000"
ACTIVE_FRONTEND_MODE = "start"
CRB_ARTICLE_ID = "crb-formula"
CRB_TITLE = "CRB公式与估计下界"
ATTENTION_ARTICLE_ID = "attention-basics"
ATTENTION_TITLE = "Attention机制入门"
RESEARCH_ARTICLE_ID = "local-research-map"
RESEARCH_TITLE = "本地研究路径与来源边界"
ATTENTION_CONCEPT_ID = "concept:attention"
ATTENTION_CONCEPT_RETURN = "/graph?node_id=concept%3Aattention"
ATTENTION_CONCEPT_QUERY_RETURN = f"{ATTENTION_CONCEPT_RETURN}&q=Attention"
EXPECTED_ARTICLE_COUNT = 3
CONTROLLED_HTTP_EXPECTATION_HEADER = "x-scientific-spaces-e2e-expectation"
POST_TERMINAL_DESTINATION_COMMIT_MAX_SECONDS = 0.25
ALLOWED_HTTP_ORIGINS = frozenset(
    {
        ("http", "127.0.0.1", 3000),
        ("http", "127.0.0.1", 8000),
        ("http", "localhost", 8000),
    }
)
ALLOWED_WEBSOCKET_ORIGINS = frozenset({("ws", "127.0.0.1", 3000)})


class E2EFailure(AssertionError):
    """Raised when an end-to-end product assertion fails."""


class LocalOnlyBrowser:
    """Create every E2E context with service workers disabled."""

    def __init__(self, browser) -> None:
        self._browser = browser

    @property
    def version(self) -> str:
        return self._browser.version

    def new_context(self, **options):
        _require(
            "service_workers" not in options,
            "E2E context attempted to override the service-worker policy",
        )
        return LocalOnlyContext(
            self._browser.new_context(service_workers="block", **options)
        )

    def close(self) -> None:
        self._browser.close()


class LocalOnlyContext:
    """Proxy context closure through the request-evidence ledger."""

    def __init__(self, context) -> None:
        self._context = context

    def __getattr__(self, name: str):
        return getattr(self._context, name)

    def close(self, *args, **kwargs) -> None:
        for page in list(self._context.pages):
            ledger = getattr(page, "_scientific_spaces_console_error_log", None)
            if isinstance(ledger, ConsoleErrorLog) and not page.is_closed():
                ledger.mark_page_close_intent(page)
        self._context.close(*args, **kwargs)


class NetworkGuardLog(list[str]):
    """Keep external-network and context-page provenance in one iteration ledger."""

    def __init__(self) -> None:
        super().__init__()
        self.page_trackers: list[dict[str, object]] = []


class ConsoleErrorLog(list[str]):
    """Keep console text and provenance aligned through legacy slice checks."""

    def __init__(self) -> None:
        super().__init__()
        self.evidence: list[dict[str, object]] = []
        self.cdp_console_evidence: list[dict[str, object]] = []
        self.response_evidence: list[dict[str, object]] = []
        self.expectations: list[dict[str, object]] = []
        self.no_content_expectations: list[dict[str, object]] = []
        self.route_transition_expectations: list[dict[str, object]] = []
        self.binding_failures: list[dict[str, object]] = []
        self.request_evidence: dict[str, dict[str, object]] = {}
        self._observed_pages: dict[str, str] = {}
        self._page_navigation_generations: dict[str, int] = {}
        self._page_navigation_events: dict[str, list[dict[str, object]]] = {}
        self._page_close_intent_sequences: dict[str, int] = {}
        self._closed_page_ids: set[str] = set()
        self._observed_contexts: set[str] = set()
        self._cdp_sessions: dict[str, object] = {}
        self._next_cdp_session_number = 1
        self._cdp_requests: dict[str, dict[str, object]] = {}
        self._expected_request_ids: dict[str, str] = {}
        self._expected_network_request_ids: dict[str, str] = {}
        self._expected_no_content_request_ids: dict[str, str] = {}
        self._event_sequence = 0

    def _next_event_sequence(self) -> int:
        self._event_sequence += 1
        return self._event_sequence

    def mark_page_close_intent(self, page) -> None:
        page_id = _page_identity(page)
        if page_id not in self._page_close_intent_sequences:
            self._page_close_intent_sequences[page_id] = (
                self._next_event_sequence()
            )

    def capture(self, message, *, label: str, page) -> None:
        if message.type != "error":
            return
        producer_page = message.page
        page_id = _page_identity(producer_page) if producer_page is not None else ""
        effective_label = self._observed_pages.get(page_id, label)
        super().append(message.text)
        self.evidence.append(
            _console_error_evidence(message, label=effective_label, page=page)
        )

    def observe_http_errors(self, page, *, label: str) -> None:
        page_id = _page_identity(page)
        previous_label = self._observed_pages.get(page_id)
        _require(
            previous_label in (None, label),
            f"HTTP error observer label changed for one page: {previous_label} -> {label}",
        )
        if previous_label is not None:
            return
        self._observed_pages[page_id] = label
        self._page_navigation_generations.setdefault(page_id, 0)
        self._page_navigation_events.setdefault(page_id, [])
        setattr(page, "_scientific_spaces_console_error_log", self)
        original_close = page.close

        def close_with_evidence(*args, **kwargs):
            if not page.is_closed():
                self.mark_page_close_intent(page)
            return original_close(*args, **kwargs)

        page.close = close_with_evidence
        for evidence in self.request_evidence.values():
            if evidence["page_id"] == page_id and not evidence["label"]:
                evidence["label"] = label
        for evidence in self.response_evidence:
            if evidence["page_id"] == page_id and not evidence["label"]:
                evidence["label"] = label
        for evidence in self._cdp_requests.values():
            if evidence["page_id"] == page_id and not evidence["label"]:
                evidence["label"] = label

        def capture_navigation(frame) -> None:
            if frame is page.main_frame:
                self._page_navigation_generations[page_id] += 1
                self._page_navigation_events[page_id].append(
                    {
                        "sequence": self._next_event_sequence(),
                        "generation": self._page_navigation_generations[page_id],
                        "url": frame.url,
                        "monotonic": time.monotonic(),
                    }
                )

        page.on("framenavigated", capture_navigation)

        context = page.context
        context_id = str(
            getattr(getattr(context, "_impl_obj", context), "_guid", id(context))
        )
        if context_id not in self._observed_contexts:
            self._observed_contexts.add(context_id)
            context.on("request", self._capture_request_start)
            context.on("response", self._capture_response)
            context.on("requestfinished", self._mark_request_finished)
            context.on("requestfailed", self._mark_request_failed)

        session_id = f"cdp-session-{self._next_cdp_session_number}"
        self._next_cdp_session_number += 1
        session = context.new_cdp_session(page)
        session.on(
            "Network.requestWillBeSent",
            lambda event: self._capture_cdp_request(
                event,
                label=label,
                page=page,
                session_id=session_id,
            ),
        )
        session.on(
            "Network.responseReceived",
            lambda event: self._capture_cdp_response(event, session_id=session_id),
        )
        session.on(
            "Log.entryAdded",
            lambda event: self._capture_cdp_log(
                event,
                label=label,
                page=page,
                session_id=session_id,
            ),
        )
        session.send("Network.enable")
        session.send("Log.enable")
        self._cdp_sessions[session_id] = session

        def detach_session() -> None:
            self._closed_page_ids.add(page_id)
            tracked_session = self._cdp_sessions.get(session_id)
            if tracked_session is not session:
                return
            self._cdp_sessions.pop(session_id)
            try:
                tracked_session.detach()
            except Exception:
                pass

        page.on("close", detach_session)

    def declare_http_errors(
        self,
        *,
        label: str,
        page_url: str,
        source_url: str,
        status: int,
        method: str,
        resource_type: str,
        navigation_request: bool,
        count: int = 1,
    ) -> tuple[str, ...]:
        _require(count >= 1, f"controlled HTTP error count must be positive: {count}")
        expectation_ids: list[str] = []
        for _ in range(count):
            expectation_id = f"controlled-http-{len(self.expectations) + 1}"
            expectation_ids.append(expectation_id)
            self.expectations.append(
                {
                    "expectation_id": expectation_id,
                    "label": label,
                    "page_url": page_url,
                    "source_url": source_url,
                    "status": status,
                    "method": method,
                    "resource_type": resource_type,
                    "navigation_request": navigation_request,
                    "response_header_required": True,
                    "page_id": None,
                    "request_id": None,
                    "network_request_id": None,
                }
            )
        return tuple(expectation_ids)

    def bind_http_error_request(
        self,
        expectation_ids: tuple[str, ...],
        *,
        request,
        page,
    ) -> dict[str, object]:
        request_id = _request_identity(request)
        _require(
            request_id not in self._expected_request_ids,
            f"controlled HTTP request was registered twice: {request_id}",
        )
        _require(
            request.service_worker is None,
            "controlled HTTP request originated from a service worker",
        )
        actual = self._request_actual(request)
        if not actual["page_id"] and actual["navigation_request"] is True:
            actual["label"] = self._observed_pages.get(_page_identity(page), "")
            actual["page_id"] = _page_identity(page)
            actual["page_url"] = request.url
            actual["frame_url_at_request"] = request.url
            actual["main_frame"] = True
            self.request_evidence[request_id] = actual
        candidates = [
            item
            for item in self.expectations
            if item["expectation_id"] in expectation_ids
            and item["request_id"] is None
            and {
                "page_url": item["page_url"],
                "source_url": item["source_url"],
                "method": item["method"],
                "resource_type": item["resource_type"],
                "navigation_request": item["navigation_request"],
            }
            == {
                "page_url": actual["page_url"],
                "source_url": actual["source_url"],
                "method": actual["method"],
                "resource_type": actual["resource_type"],
                "navigation_request": actual["navigation_request"],
            }
        ]
        _require(
            candidates,
            f"controlled HTTP route intercepted an undeclared request: {actual}",
        )
        _require(
            actual["page_id"] == _page_identity(page)
            and actual["main_frame"] is True,
            f"controlled HTTP request did not originate from the main frame: {actual}",
        )
        expectation = candidates[0]
        self._bind_playwright_request(expectation, request_id=request_id, actual=actual)
        return expectation

    def declare_no_content_response(
        self,
        *,
        page,
        source_url: str,
        method: str,
    ) -> str:
        page_id = _page_identity(page)
        label = self._observed_pages.get(page_id, "")
        _require(label, "204 response expectation requires an observed page")
        expectation_id = f"controlled-204-{len(self.no_content_expectations) + 1}"
        self.no_content_expectations.append(
            {
                "expectation_id": expectation_id,
                "label": label,
                "page_id": page_id,
                "page_url": page.url,
                "source_url": source_url,
                "method": method,
                "declaration_sequence": self._next_event_sequence(),
                "request_id": None,
                "response_status": None,
                "response_url": None,
                "finished": False,
                "failure": None,
            }
        )
        return expectation_id

    def declare_route_transition(
        self,
        *,
        page,
        destination_url: str,
        request_page_url: str | None = None,
        allow_speculative_cancellations: bool = False,
        allow_post_terminal_destination_commit: bool = False,
        allow_complete_precursor_snapshot: bool = True,
        cancelled_route_urls: tuple[str, ...] = (),
        cancelled_read_urls: tuple[str, ...] = (),
    ) -> str:
        page_id = _page_identity(page)
        label = self._observed_pages.get(page_id, "")
        effective_request_page_url = request_page_url or page.url
        cancelled_route_keys = tuple(
            _route_document_key(url) for url in cancelled_route_urls
        )
        cancelled_read_keys = tuple(
            _network_url_key(url) for url in cancelled_read_urls
        )
        endpoint_route_keys = {
            _route_document_key(effective_request_page_url),
            _route_document_key(destination_url),
        }
        _require(label, "route transition expectation requires an observed page")
        _require(
            _is_allowed_frontend_url(destination_url),
            f"route transition destination is not the exact Frontend origin: {destination_url}",
        )
        _require(
            _is_allowed_frontend_url(effective_request_page_url),
            "route transition request page is not the exact Frontend origin: "
            f"{effective_request_page_url}",
        )
        _require(
            len(cancelled_route_keys) == len(set(cancelled_route_keys))
            and all(_is_allowed_frontend_url(url) for url in cancelled_route_urls),
            "route transition declared invalid cancelled route URLs: "
            f"{cancelled_route_urls}",
        )
        _require(
            not set(cancelled_route_keys) & endpoint_route_keys,
            "cancelled route identities overlap the transition endpoints: "
            f"{cancelled_route_urls}",
        )
        _require(
            len(cancelled_read_keys) == len(set(cancelled_read_keys))
            and all(
                _is_allowed_http_url(url) and urlparse(url).port == 8000
                for url in cancelled_read_urls
            ),
            f"route transition declared invalid cancelled read URLs: {cancelled_read_urls}",
        )
        declaration_sequence = self._next_event_sequence()
        cache_precursor_request_ids = ()
        if allow_complete_precursor_snapshot:
            cache_precursor_request_ids = tuple(
                request_id
                for request_id, evidence in sorted(
                    self.request_evidence.items(),
                    key=lambda item: int(item[1].get("start_sequence") or -1),
                )
                if _is_valid_route_cache_precursor(
                    evidence,
                    page_id=page_id,
                    label=label,
                    destination_url=destination_url,
                    declaration_sequence=declaration_sequence,
                )
            )
        expectation_id = (
            f"controlled-route-{len(self.route_transition_expectations) + 1}"
        )
        self.route_transition_expectations.append(
            {
                "expectation_id": expectation_id,
                "label": label,
                "page_id": page_id,
                "request_page_url": effective_request_page_url,
                "destination_url": destination_url,
                "allow_speculative_cancellations": allow_speculative_cancellations,
                "allow_post_terminal_destination_commit": (
                    allow_post_terminal_destination_commit
                ),
                "allow_complete_precursor_snapshot": (
                    allow_complete_precursor_snapshot
                ),
                "cancelled_route_urls": cancelled_route_urls,
                "cancelled_read_urls": cancelled_read_urls,
                "declaration_sequence": declaration_sequence,
                "declaration_navigation_generation": (
                    self._page_navigation_generations.get(page_id, 0)
                ),
                "completion_sequence": None,
                "completion_url": None,
                "completion_navigation_generation": None,
                "bound_request_ids": None,
                "post_terminal_request_id": None,
                "cache_precursor_request_ids": cache_precursor_request_ids,
            }
        )
        return expectation_id

    def complete_route_transition(self, *, page, expectation_id: str) -> None:
        candidates = [
            item
            for item in self.route_transition_expectations
            if item["expectation_id"] == expectation_id
        ]
        _require(
            len(candidates) == 1,
            f"route transition expectation is missing or ambiguous: {expectation_id}",
        )
        expectation = candidates[0]
        _require(
            expectation["completion_sequence"] is None,
            f"route transition expectation completed twice: {expectation_id}",
        )
        _require(
            expectation["page_id"] == _page_identity(page),
            f"route transition expectation changed page identity: {expectation_id}",
        )
        _require(
            _route_url_key(page.url)
            == _route_url_key(str(expectation["destination_url"])),
            "route transition completed at the wrong URL: "
            f"expected={expectation['destination_url']} actual={page.url}",
        )
        declaration_sequence = int(expectation["declaration_sequence"])
        declared_route_keys = {
            _route_document_key(
                str(expectation.get("request_page_url") or "")
            ),
            _route_document_key(str(expectation.get("destination_url") or "")),
            *(
                _route_document_key(str(url))
                for url in expectation.get("cancelled_route_urls") or ()
            ),
        }
        pending_route_request_ids = [
            request_id
            for request_id, evidence in self.request_evidence.items()
            if evidence.get("page_id") == expectation["page_id"]
            and evidence.get("label") == expectation["label"]
            and isinstance(evidence.get("start_sequence"), int)
            and declaration_sequence < int(evidence["start_sequence"])
            and evidence.get("terminal_sequence") is None
            and evidence.get("method") == "GET"
            and evidence.get("resource_type") in {"fetch", "xhr"}
            and evidence.get("navigation_request") is False
            and evidence.get("main_frame") is True
            and not evidence.get("service_worker_url")
            and evidence.get("rsc_request") is True
            and evidence.get("next_router_prefetch") is not True
            and evidence.get("purpose") != "prefetch"
            and str(evidence.get("sec_purpose") or "").split(";", 1)[0]
            != "prefetch"
            and _route_document_key(str(evidence.get("source_url") or ""))
            in declared_route_keys
        ]
        _require(
            not pending_route_request_ids,
            "route transition cannot complete with pending exact RSC requests: "
            f"{pending_route_request_ids}",
        )
        completion_sequence = self._next_event_sequence()
        expectation["completion_sequence"] = completion_sequence
        expectation["completion_url"] = page.url
        expectation["completion_navigation_generation"] = (
            self._page_navigation_generations.get(_page_identity(page), 0)
        )
        already_bound = {
            str(request_id)
            for item in self.route_transition_expectations
            if item is not expectation
            for request_id in item.get("bound_request_ids") or ()
        }
        bound_request_ids = tuple(
            request_id
            for request_id, evidence in self.request_evidence.items()
            if request_id not in already_bound
            and _route_transition_request_kind(self, expectation, evidence) is not None
            and isinstance(evidence.get("terminal_sequence"), int)
            and int(evidence["terminal_sequence"]) < completion_sequence
        )
        expectation["bound_request_ids"] = bound_request_ids

    def bind_post_terminal_destination_request(
        self,
        *,
        expectation_id: str,
        evidence: dict[str, object],
    ) -> None:
        candidates = [
            item
            for item in self.route_transition_expectations
            if item["expectation_id"] == expectation_id
        ]
        _require(
            len(candidates) == 1,
            f"post-terminal route expectation is missing or ambiguous: {expectation_id}",
        )
        expectation = candidates[0]
        request_ids = [
            request_id
            for request_id, candidate in self.request_evidence.items()
            if candidate is evidence
        ]
        _require(
            expectation.get("allow_post_terminal_destination_commit") is True
            and expectation.get("post_terminal_request_id") is None
            and expectation.get("completion_sequence") is None
            and expectation.get("completion_url") is None
            and expectation.get("completion_navigation_generation") is None
            and expectation.get("bound_request_ids") is None
            and len(request_ids) == 1,
            "post-terminal destination request was not uniquely bindable",
        )
        request_id = request_ids[0]
        _require(
            all(
                item.get("post_terminal_request_id") != request_id
                for item in self.route_transition_expectations
                if item is not expectation
            ),
            f"post-terminal destination request was already bound: {request_id}",
        )
        source_url = str(evidence.get("source_url") or "")
        _require(
            expectation.get("page_id") == evidence.get("page_id")
            and expectation.get("label") == evidence.get("label")
            and evidence.get("method") == "GET"
            and evidence.get("resource_type") in {"fetch", "xhr"}
            and evidence.get("navigation_request") is False
            and evidence.get("main_frame") is True
            and not evidence.get("service_worker_url")
            and evidence.get("rsc_request") is True
            and evidence.get("next_router_prefetch") is not True
            and evidence.get("purpose") != "prefetch"
            and str(evidence.get("sec_purpose") or "").split(";", 1)[0]
            != "prefetch"
            and evidence.get("response_status") == 200
            and evidence.get("response_url") == source_url
            and evidence.get("failure") == "net::ERR_ABORTED"
            and evidence.get("finished") is not True
            and _route_document_key(source_url)
            == _route_document_key(str(expectation.get("destination_url") or "")),
            "post-terminal destination request did not match its exact route lifecycle",
        )
        expectation["post_terminal_request_id"] = request_id

    def _capture_request_start(self, request) -> None:
        request_id = _request_identity(request)
        if request_id in self.request_evidence:
            return
        self.request_evidence[request_id] = self._request_actual(request)

    def _request_actual(self, request) -> dict[str, object]:
        request_id = _request_identity(request)
        existing = self.request_evidence.get(request_id)
        if existing is not None:
            return existing
        service_worker = request.service_worker
        navigation_request = request.is_navigation_request()
        frame = None
        if service_worker is None:
            try:
                frame = request.frame
            except Exception:
                _require(
                    navigation_request,
                    "non-navigation request had no owning frame",
                )
        producer_page = frame.page if frame is not None else None
        page_url = (
            request.url
            if navigation_request
            else frame.url if frame is not None else ""
        )
        page_id = _page_identity(producer_page) if producer_page is not None else ""
        request_headers = request.headers
        rsc_request = _header_value(request_headers, "rsc") == "1"
        next_router_prefetch = (
            _header_value(request_headers, "next-router-prefetch") == "1"
        )
        purpose = _header_value(request_headers, "purpose").casefold()
        sec_purpose = _header_value(request_headers, "sec-purpose").casefold()
        start_sequence = self._next_event_sequence()
        explicit_prefetch = (
            next_router_prefetch
            or purpose == "prefetch"
            or sec_purpose.split(";", 1)[0] == "prefetch"
        )
        return {
            "label": self._observed_pages.get(page_id, ""),
            "page_id": page_id,
            "page_url": page_url,
            "frame_url_at_request": frame.url if frame is not None else "",
            "source_url": request.url,
            "method": request.method,
            "resource_type": request.resource_type,
            "navigation_request": navigation_request,
            "main_frame": (
                frame is producer_page.main_frame
                if frame is not None and producer_page is not None
                else False
            ),
            "service_worker_url": service_worker.url if service_worker is not None else "",
            "rsc_request": rsc_request,
            "next_router_prefetch": next_router_prefetch,
            "purpose": purpose,
            "sec_purpose": sec_purpose,
            "route_intent_sequence": (
                start_sequence if rsc_request and not explicit_prefetch else None
            ),
            "start_sequence": start_sequence,
            "start_monotonic": time.monotonic(),
            "response_sequence": None,
            "response_monotonic": None,
            "terminal_sequence": None,
            "terminal_monotonic": None,
            "navigation_generation": self._page_navigation_generations.get(page_id, 0),
            "terminal_page_url": None,
            "terminal_navigation_generation": None,
            "response_status": None,
            "response_url": None,
            "finished": False,
            "failure": None,
        }

    def _capture_cdp_request(
        self,
        event,
        *,
        label: str,
        page,
        session_id: str,
    ) -> None:
        raw_request_id = str(event.get("requestId") or "")
        if not raw_request_id:
            return
        network_request_id = f"{session_id}:{raw_request_id}"
        request = event.get("request") or {}
        resource_type = str(event.get("type") or "").lower()
        navigation_request = resource_type == "document"
        page_id = _page_identity(page)
        actual = {
            "label": self._observed_pages.get(page_id, label),
            "page_id": page_id,
            "page_url": (
                str(request.get("url") or "")
                if navigation_request
                else str(event.get("documentURL") or "")
            ),
            "source_url": str(request.get("url") or ""),
            "method": str(request.get("method") or ""),
            "resource_type": resource_type,
            "navigation_request": navigation_request,
            "session_id": session_id,
        }
        candidates = [
            item
            for item in self.expectations
            if self._cdp_request_matches_expectation(item, actual=actual)
        ]
        if not candidates:
            return
        self._cdp_requests[network_request_id] = {
            **actual,
            "network_request_id": network_request_id,
            "claimed": False,
        }

    @staticmethod
    def _cdp_request_matches_expectation(
        expectation: dict[str, object],
        *,
        actual: dict[str, object],
    ) -> bool:
        return (
            expectation["label"] == actual["label"]
            and expectation["page_id"] in (None, actual["page_id"])
            and expectation["page_url"] == actual["page_url"]
            and expectation["source_url"] == actual["source_url"]
            and expectation["method"] == actual["method"]
            and expectation["resource_type"] == actual["resource_type"]
            and expectation["navigation_request"] == actual["navigation_request"]
        )

    def _capture_cdp_response(self, event, *, session_id: str) -> None:
        raw_request_id = str(event.get("requestId") or "")
        network_request_id = f"{session_id}:{raw_request_id}"
        response = event.get("response") or {}
        try:
            status = int(response.get("status"))
        except (TypeError, ValueError):
            return
        cdp_request = self._cdp_requests.get(network_request_id)
        if cdp_request is None or cdp_request["claimed"] is True:
            return
        bridge_id = _header_value(
            response.get("headers") or {}, CONTROLLED_HTTP_EXPECTATION_HEADER
        )
        candidates = self._cdp_expectation_candidates(
            cdp_request,
            status=status,
            bridge_id=bridge_id,
        )
        if not candidates:
            if bridge_id:
                self.binding_failures.append(
                    {
                        "kind": "unmatched_cdp_response_bridge",
                        "bridge_id": bridge_id,
                        "status": status,
                        "request": dict(cdp_request),
                    }
                )
            return
        if len(candidates) != 1:
            self.binding_failures.append(
                {
                    "kind": "ambiguous_cdp_response_binding",
                    "bridge_id": bridge_id,
                    "status": status,
                    "candidate_ids": [item["expectation_id"] for item in candidates],
                    "request": dict(cdp_request),
                }
            )
            return
        self._bind_network_request(candidates[0], cdp_request)

    def _cdp_expectation_candidates(
        self,
        cdp_request: dict[str, object],
        *,
        status: int,
        bridge_id: str,
    ) -> list[dict[str, object]]:
        return [
            item
            for item in self.expectations
            if item["network_request_id"] is None
            and item["status"] == status
            and item["expectation_id"] == bridge_id
            and item["label"] == cdp_request["label"]
            and item["page_id"] in (None, cdp_request["page_id"])
            and item["page_url"] == cdp_request["page_url"]
            and item["source_url"] == cdp_request["source_url"]
            and item["method"] == cdp_request["method"]
            and item["resource_type"] == cdp_request["resource_type"]
            and item["navigation_request"] == cdp_request["navigation_request"]
        ]

    def _bind_network_request(
        self,
        expectation: dict[str, object],
        cdp_request: dict[str, object],
    ) -> None:
        expectation_id = str(expectation["expectation_id"])
        network_request_id = str(cdp_request["network_request_id"])
        _require(
            network_request_id
            and network_request_id not in self._expected_network_request_ids,
            "controlled CDP request identity was missing or reused: "
            f"{network_request_id}",
        )
        _require(
            cdp_request["claimed"] is False
            and expectation["network_request_id"] is None,
            f"controlled CDP request was bound twice: {network_request_id}",
        )
        _require(
            expectation["page_id"] in (None, cdp_request["page_id"]),
            "controlled CDP request changed page identity: "
            f"{expectation['expectation_id']}",
        )
        cdp_request["claimed"] = True
        expectation["page_id"] = cdp_request["page_id"]
        expectation["network_request_id"] = network_request_id
        self._expected_network_request_ids[network_request_id] = expectation_id
        for evidence in self.cdp_console_evidence:
            if (
                evidence.get("network_request_id") == network_request_id
                and evidence.get("expectation_id") is None
            ):
                evidence["expectation_id"] = expectation_id
                evidence["label"] = expectation["label"]
                evidence["page_id"] = expectation["page_id"]
                evidence["page_url"] = expectation["page_url"]
        for evidence in self.response_evidence:
            if (
                evidence.get("expectation_id") == expectation_id
                and evidence.get("network_request_id") is None
            ):
                evidence["network_request_id"] = network_request_id

    def _capture_cdp_log(
        self,
        event,
        *,
        label: str,
        page,
        session_id: str,
    ) -> None:
        entry = event.get("entry") or {}
        if entry.get("source") != "network" or entry.get("level") != "error":
            return
        raw_request_id = str(entry.get("networkRequestId") or "")
        network_request_id = f"{session_id}:{raw_request_id}"
        expectation_id = self._expected_network_request_ids.get(network_request_id)
        expectation = self._expectation(expectation_id)
        cdp_request = self._cdp_requests.get(network_request_id)
        page_id = _page_identity(page)
        text_value = str(entry.get("text") or "")
        self.cdp_console_evidence.append(
            {
                "expectation_id": expectation_id,
                "network_request_id": network_request_id,
                "label": (
                    expectation["label"]
                    if expectation is not None
                    else cdp_request["label"] if cdp_request is not None else label
                ),
                "listener_page_id": page_id,
                "listener_page_url": page.url,
                "page_id": (
                    expectation["page_id"]
                    if expectation is not None
                    else cdp_request["page_id"] if cdp_request is not None else page_id
                ),
                "page_url": (
                    expectation["page_url"]
                    if expectation is not None
                    else cdp_request["page_url"] if cdp_request is not None else page.url
                ),
                "same_page": (
                    expectation["page_id"] == page_id
                    if expectation is not None
                    else cdp_request["page_id"] == page_id
                    if cdp_request is not None
                    else True
                ),
                "worker_url": str(entry.get("workerId") or ""),
                "text": text_value,
                "url": str(entry.get("url") or ""),
            }
        )

    def _capture_response(self, response) -> None:
        request = response.request
        request_id = _request_identity(request)
        actual = self.request_evidence.get(request_id) or self._request_actual(request)
        self.request_evidence.setdefault(request_id, actual)
        actual["response_status"] = response.status
        actual["response_url"] = response.url
        actual["response_sequence"] = self._next_event_sequence()
        actual["response_monotonic"] = time.monotonic()
        if response.status == 204:
            self._bind_no_content_response(
                request_id=request_id,
                actual=actual,
                response_url=response.url,
            )
        if response.status < 400:
            return
        if not actual["page_id"] and request.service_worker is None:
            frame = response.frame
            producer_page = frame.page
            actual["label"] = self._observed_pages.get(
                _page_identity(producer_page), ""
            )
            actual["page_id"] = _page_identity(producer_page)
            actual["frame_url_at_request"] = frame.url
            actual["main_frame"] = frame is producer_page.main_frame
        if any(item["request_id"] == request_id for item in self.response_evidence):
            return
        bridge_id = _header_value(response.headers, CONTROLLED_HTTP_EXPECTATION_HEADER)
        expectation_id = self._expected_request_ids.get(request_id)
        expectation = self._expectation(expectation_id)
        if bridge_id:
            bridged_expectation = self._expectation(bridge_id)
            if bridged_expectation is None or expectation not in (None, bridged_expectation):
                self.binding_failures.append(
                    {
                        "kind": "invalid_playwright_response_bridge",
                        "bridge_id": bridge_id,
                        "mapped_expectation_id": expectation_id,
                        "request_id": request_id,
                    }
                )
            elif expectation is None and self._playwright_expectation_matches(
                bridged_expectation, actual=actual, status=response.status
            ):
                self._bind_playwright_request(
                    bridged_expectation, request_id=request_id, actual=actual
                )
                expectation = bridged_expectation
                expectation_id = bridge_id
            elif expectation is None:
                self.binding_failures.append(
                    {
                        "kind": "mismatched_playwright_response_bridge",
                        "bridge_id": bridge_id,
                        "request_id": request_id,
                        "request": dict(actual),
                    }
                )
        elif expectation is not None:
            self.binding_failures.append(
                {
                    "kind": "missing_playwright_response_bridge",
                    "expectation_id": expectation_id,
                    "request_id": request_id,
                }
            )
        self.response_evidence.append(
            {
                "label": actual["label"],
                "listener_page_id": actual["page_id"],
                "listener_page_url": actual["page_url"],
                "page_url": actual["page_url"],
                "frame_url_at_request": actual["frame_url_at_request"],
                "same_page": bool(actual["page_id"]),
                "main_frame": actual["main_frame"],
                "service_worker_url": actual["service_worker_url"],
                "from_service_worker": response.from_service_worker,
                "status": response.status,
                "source_url": response.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "navigation_request": request.is_navigation_request(),
                "request_id": request_id,
                "network_request_id": (
                    expectation["network_request_id"] if expectation is not None else None
                ),
                "expectation_id": expectation_id,
                "bridge_expectation_id": bridge_id or None,
                "page_id": actual["page_id"],
                "finished": bool(actual["finished"]),
                "failure": actual["failure"],
            }
        )

    def _bind_no_content_response(
        self,
        *,
        request_id: str,
        actual: dict[str, object],
        response_url: str,
    ) -> None:
        candidates = [
            item
            for item in self.no_content_expectations
            if item["request_id"] is None
            and isinstance(item.get("declaration_sequence"), int)
            and isinstance(actual.get("start_sequence"), int)
            and int(item["declaration_sequence"]) < int(actual["start_sequence"])
            and item["label"] == actual["label"]
            and item["page_id"] == actual["page_id"]
            and item["page_url"] == actual["page_url"]
            and item["source_url"] == actual["source_url"]
            and item["method"] == actual["method"]
            and actual["main_frame"] is True
            and not actual["service_worker_url"]
        ]
        if not candidates:
            return
        if len(candidates) != 1:
            self.binding_failures.append(
                {
                    "kind": "ambiguous_no_content_response_binding",
                    "candidate_ids": [item["expectation_id"] for item in candidates],
                    "request_id": request_id,
                    "request": dict(actual),
                }
            )
            return
        expectation = candidates[0]
        expectation_id = str(expectation["expectation_id"])
        if request_id in self._expected_no_content_request_ids:
            self.binding_failures.append(
                {
                    "kind": "duplicate_no_content_response_binding",
                    "expectation_id": expectation_id,
                    "request_id": request_id,
                }
            )
            return
        expectation["request_id"] = request_id
        expectation["response_status"] = 204
        expectation["response_url"] = response_url
        self._expected_no_content_request_ids[request_id] = expectation_id

    def _expectation(self, expectation_id: object) -> dict[str, object] | None:
        return next(
            (
                item
                for item in self.expectations
                if item["expectation_id"] == expectation_id
            ),
            None,
        )

    def _playwright_expectation_matches(
        self,
        expectation: dict[str, object],
        *,
        actual: dict[str, object],
        status: int,
    ) -> bool:
        return (
            expectation["status"] == status
            and expectation["label"] == actual["label"]
            and expectation["page_id"] in (None, actual["page_id"])
            and expectation["page_url"] == actual["page_url"]
            and expectation["source_url"] == actual["source_url"]
            and expectation["method"] == actual["method"]
            and expectation["resource_type"] == actual["resource_type"]
            and expectation["navigation_request"] == actual["navigation_request"]
            and actual["main_frame"] is True
            and not actual["service_worker_url"]
        )

    def _bind_playwright_request(
        self,
        expectation: dict[str, object],
        *,
        request_id: str,
        actual: dict[str, object],
    ) -> None:
        expectation_id = str(expectation["expectation_id"])
        _require(
            request_id not in self._expected_request_ids,
            f"controlled HTTP request was registered twice: {request_id}",
        )
        _require(
            expectation["request_id"] is None,
            f"controlled HTTP expectation was bound twice: {expectation_id}",
        )
        expectation["request_id"] = request_id
        expectation["page_id"] = actual["page_id"]
        self._expected_request_ids[request_id] = expectation_id

    def _mark_request_finished(self, request) -> None:
        request_id = _request_identity(request)
        request_evidence = self.request_evidence.get(request_id)
        if request_evidence is not None:
            request_evidence["finished"] = True
            self._record_request_terminal_page(request, request_evidence)
        no_content_expectation = self._no_content_expectation_for_request(request_id)
        if no_content_expectation is not None:
            no_content_expectation["finished"] = True
        for evidence in self.response_evidence:
            if evidence["request_id"] == request_id:
                evidence["finished"] = True

    def _mark_request_failed(self, request) -> None:
        request_id = _request_identity(request)
        failure = request.failure or "request failed"
        request_evidence = self.request_evidence.get(request_id)
        if request_evidence is not None:
            request_evidence["failure"] = failure
            self._record_request_terminal_page(request, request_evidence)
        no_content_expectation = self._no_content_expectation_for_request(request_id)
        if no_content_expectation is not None:
            no_content_expectation["failure"] = failure
        for evidence in self.response_evidence:
            if evidence["request_id"] == request_id:
                evidence["failure"] = failure

    def _record_request_terminal_page(
        self,
        request,
        evidence: dict[str, object],
    ) -> None:
        if request.service_worker is not None:
            return
        try:
            page = request.frame.page
        except Exception:
            return
        page_id = _page_identity(page)
        if page_id != evidence.get("page_id"):
            return
        evidence["terminal_page_url"] = page.url
        evidence["terminal_navigation_generation"] = (
            self._page_navigation_generations.get(page_id, 0)
        )
        evidence["terminal_sequence"] = self._next_event_sequence()
        evidence["terminal_monotonic"] = time.monotonic()

    def _no_content_expectation_for_request(
        self, request_id: str
    ) -> dict[str, object] | None:
        expectation_id = self._expected_no_content_request_ids.get(request_id)
        return next(
            (
                item
                for item in self.no_content_expectations
                if item["expectation_id"] == expectation_id
            ),
            None,
        )

def main() -> int:
    global ACTIVE_FRONTEND_MODE, BROWSER_API_URL
    parser = argparse.ArgumentParser(description="Run the local-only Scientific Spaces product E2E suite.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of complete desktop/mobile passes.")
    parser.add_argument(
        "--frontend-mode",
        choices=("start", "dev"),
        default="start",
        help="Use the built Next.js server or the development server.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON result path; temporary output is preferred.")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.frontend_mode == "start" and not (
        FRONTEND_ROOT / ".next" / "BUILD_ID"
    ).is_file():
        parser.error(
            "frontend/.next/BUILD_ID is absent; run npm run build before "
            "--frontend-mode start"
        )
    if args.frontend_mode == "dev":
        BROWSER_API_URL = API_URL
    ACTIVE_FRONTEND_MODE = args.frontend_mode

    result: dict[str, object]
    with tempfile.TemporaryDirectory(prefix="scientific-spaces-p3-011-e2e-") as temporary:
        runtime_root = Path(temporary)
        try:
            runtime = prepare_runtime(runtime_root)
            with product_servers(runtime, frontend_mode=args.frontend_mode) as logs:
                result = run_browser_suite(runtime, repeat=args.repeat)
            restart_result = verify_backend_restart_persistence(runtime)
            result["restart_persistence"] = restart_result
            if restart_result["status"] != "PASS":
                result["status"] = "BLOCKED"
            result["server_logs"] = {
                "backend": _bounded_log_summary(logs["backend"]),
                "frontend": _bounded_log_summary(logs["frontend"]),
                "restart_backend": _bounded_log_summary(Path(runtime["root"]) / "restart-backend.log"),
            }
        except Exception as exc:
            result = {
                "status": "BLOCKED",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=12),
            }
            backend_log = runtime_root / "backend.log"
            frontend_log = runtime_root / "frontend.log"
            result["server_logs"] = {
                "backend": _bounded_log_summary(backend_log),
                "frontend": _bounded_log_summary(frontend_log),
            }

    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(serialized)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    return 0 if result.get("status") == "PASS" else 1


def prepare_runtime(runtime_root: Path) -> dict[str, Path | dict[str, str]]:
    data_root = runtime_root / ".local_data" / "scientific_spaces"
    articles_path = data_root / "articles.json"
    graph_path = data_root / "knowledge_graph.json"
    learning_path = data_root / "learning.json"
    tutor_path = data_root / "tutor_sessions.json"
    zotero_path = data_root / "zotero_links.json"
    reference_store = data_root / "references" / "full-corpus" / "current"
    data_root.mkdir(parents=True, exist_ok=True)

    articles = _load_fixture_articles()
    articles_path.write_text(
        json.dumps([article.to_dict() for article in articles], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    environment = {
        "SCIENTIFIC_SPACES_DATA_DIR": str(data_root),
        "SCIENTIFIC_SPACES_ARTICLES_FILE": str(articles_path),
        "SCIENTIFIC_SPACES_ARTICLE_STORE": str(articles_path),
        "SCIENTIFIC_SPACES_GRAPH_FILE": str(graph_path),
        "SCIENTIFIC_SPACES_LEARNING_FILE": str(learning_path),
        "SCIENTIFIC_SPACES_TUTOR_FILE": str(tutor_path),
        "SCIENTIFIC_SPACES_ZOTERO_FILE": str(zotero_path),
        "SCIENTIFIC_SPACES_REFERENCE_STORE": str(reference_store),
        "SCIENTIFIC_SPACES_ZOTERO_PROVIDER": "fake",
        "SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER": "fake",
        "NEXT_PUBLIC_API_BASE_URL": API_URL,
    }

    with temporary_environment(environment):
        GraphStore(graph_path).save(
            KnowledgeGraphBuilder(articles=articles, include_personalization=False).build()
        )
        corpus_fingerprint = compute_corpus_fingerprint(articles)
        build_data = build_reference_data(
            [extract_article_references(article) for article in articles],
            corpus_fingerprint=corpus_fingerprint,
            build_id="p3-011-product-e2e",
        )
        match_summary = match_reference_records(build_data.records, [])
        install_reference_store(
            reference_store,
            build_data=build_data,
            zotero_candidates=match_summary.candidates,
            article_ids=[article.id for article in articles],
            corpus_fingerprint=corpus_fingerprint,
            configuration_fingerprint="p3-011-product-e2e-config",
            build_fingerprint="p3-011-product-e2e-build",
            source_asset_id="article-store:p3-011-e2e-fixture",
            network_request_count=0,
            extra_counts={"silent_drops": 0},
        )

    return {
        "root": runtime_root,
        "articles": articles_path,
        "graph": graph_path,
        "learning": learning_path,
        "tutor": tutor_path,
        "zotero": zotero_path,
        "references": reference_store,
        "environment": environment,
    }


def _load_fixture_articles() -> list[StoredArticle]:
    payload = json.loads(ARTICLE_FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != EXPECTED_ARTICLE_COUNT:
        raise E2EFailure(f"expected {EXPECTED_ARTICLE_COUNT} fixture Articles")
    articles: list[StoredArticle] = []
    for raw in payload:
        item = dict(raw)
        metadata = dict(item["metadata"])
        if item["id"] == CRB_ARTICLE_ID:
            item["content"] = (
                f"{item['content']}\n\n"
                "## 推导步骤\n\n"
                "在正则条件下，信息矩阵给出参数不确定性的局部尺度。\n\n"
                "### 正则条件\n\n"
                "分数函数的期望为零，且 Fisher 信息有限。\n\n"
                "## 数值检查\n\n"
                "| quantity | value |\n| --- | ---: |\n| dimension | 1 |\n\n"
                "```python\nvariance_bound = 1 / fisher_information\n```\n\n"
                "## 数值检查\n\n重复标题用于验证唯一锚点。\n\n"
                "## References\n\n"
                "DOI: 10.1000/example\n\n"
                "https://arxiv.org/abs/1706.03762\n\n"
                "![External payment image](https://spaces.ac.cn/usr/themes/geekg/payment/wx.png)\n"
            )
            metadata["references"] = [
                *list(metadata.get("references") or []),
                "DOI: 10.1000/example",
                "arXiv:1706.03762",
            ]
        item["metadata"] = metadata
        articles.append(
            StoredArticle(
                id=str(item["id"]),
                title=str(item["title"]),
                url=str(item["url"]),
                content=str(item["content"]),
                metadata=dict(item["metadata"]),
            )
        )
    return articles


@contextmanager
def temporary_environment(updates: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def product_servers(
    runtime: dict[str, Path | dict[str, str]],
    *,
    frontend_mode: str,
) -> Iterator[dict[str, Path]]:
    environment = os.environ.copy()
    environment.update(runtime["environment"])
    backend_log = Path(runtime["root"]) / "backend.log"
    frontend_log = Path(runtime["root"]) / "frontend.log"
    backend_process: subprocess.Popen[str] | None = None
    frontend_process: subprocess.Popen[str] | None = None
    _require_port_free(8000)
    _require_port_free(3000)
    try:
        with backend_log.open("w", encoding="utf-8") as backend_handle:
            backend_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--app-dir",
                    str(BACKEND_ROOT),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT,
                env=environment,
                stdout=backend_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
            _wait_for_url(f"{API_URL}/health", backend_process, backend_log)

        frontend_script = "start" if frontend_mode == "start" else "dev"
        with frontend_log.open("w", encoding="utf-8") as frontend_handle:
            frontend_process = subprocess.Popen(
                [
                    "npm",
                    "run",
                    frontend_script,
                    "--",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    "3000",
                ],
                cwd=FRONTEND_ROOT,
                env=environment,
                stdout=frontend_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
            _wait_for_url(FRONTEND_URL, frontend_process, frontend_log, timeout=60)

        yield {"backend": backend_log, "frontend": frontend_log}
    finally:
        _stop_process(frontend_process)
        _stop_process(backend_process)


def run_browser_suite(
    runtime: dict[str, Path | dict[str, str]],
    *,
    repeat: int,
) -> dict[str, object]:
    from playwright.sync_api import sync_playwright

    _verify_http_error_evidence_contract()
    runs: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = LocalOnlyBrowser(playwright.chromium.launch(headless=True))
        browser_version = browser.version
        for iteration in range(1, repeat + 1):
            _reset_mutable_runtime(runtime)
            run_result = _run_single_iteration(browser, iteration=iteration)
            runs.append(run_result)
        browser.close()

    all_checks = [
        check
        for run in runs
        for check in dict(run["checks"]).values()
    ]
    return {
        "status": "PASS" if all(all_checks) else "BLOCKED",
        "browser": "Chromium",
        "browser_version": browser_version,
        "repeat_count": repeat,
        "successful_repeat_count": sum(1 for run in runs if run["status"] == "PASS"),
        "external_network_request_count": sum(
            int(run["external_network_request_count"]) for run in runs
        ),
        "framework_prefetch_cancellation_count": sum(
            int(run["framework_prefetch_cancellation_count"]) for run in runs
        ),
        "route_transition_cancellation_count": sum(
            int(run["route_transition_cancellation_count"]) for run in runs
        ),
        "route_with_complete_precursor_snapshot_count": sum(
            int(run["route_with_complete_precursor_snapshot_count"])
            for run in runs
        ),
        "declared_cancelled_route_request_count": sum(
            int(run["declared_cancelled_route_request_count"]) for run in runs
        ),
        "declared_route_read_cancellation_count": sum(
            int(run["declared_route_read_cancellation_count"]) for run in runs
        ),
        "route_transition_expectation_count": sum(
            int(run["route_transition_expectation_count"]) for run in runs
        ),
        "bound_route_transition_request_count": sum(
            int(run["bound_route_transition_request_count"]) for run in runs
        ),
        "superseded_successful_read_count": sum(
            int(run["superseded_successful_read_count"]) for run in runs
        ),
        "next_static_chunk_cancellation_count": sum(
            int(run["next_static_chunk_cancellation_count"]) for run in runs
        ),
        "successful_no_content_response_count": sum(
            int(run["successful_no_content_response_count"]) for run in runs
        ),
        "runs": runs,
    }


def _run_single_iteration(browser, *, iteration: int) -> dict[str, object]:
    from playwright.sync_api import expect

    checks: dict[str, bool] = {}
    blocked_external = NetworkGuardLog()
    console_errors = ConsoleErrorLog()
    page_errors: list[str] = []
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    page = context.new_page()
    _mark_expected_context_page(context, page)
    page.on(
        "console",
        lambda message: console_errors.capture(message, label="primary", page=page),
    )
    console_errors.observe_http_errors(page, label="primary")
    page.on("pageerror", lambda error: _capture_page_error(page_errors, "primary", page, error))
    page.add_init_script(
        """
        (() => {
          window.__p3030HydrationFocusEvents = [];
          window.__p3030HydrationFocusObserver = event => {
            if (event.target instanceof HTMLElement) {
              window.__p3030HydrationFocusEvents.push(
                event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
              );
            }
          };
          document.addEventListener('focusin', window.__p3030HydrationFocusObserver, true);
        })();
        """
    )

    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    _wait_for_animation_frames(page, 5)
    hydration_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030HydrationFocusObserver, true);
          return window.__p3030HydrationFocusEvents;
        }
        """
    )
    _require(
        not hydration_focus_events and page.evaluate("document.activeElement === document.body"),
        f"initial Shell hydration moved focus without user input: {hydration_focus_events}",
    )
    checks["shell_initial_hydration_focus_stable"] = True
    _verify_worker_network_surfaces_blocked(page)
    checks["worker_network_surfaces_blocked"] = True
    expect(
        page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(page.get_by_text(str(EXPECTED_ARTICLE_COUNT), exact=True).first).to_be_visible()
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-command-center")).to_be_visible()
    expect(page.get_by_role("heading", name="Learning Overview", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Focused Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    expect(
        page.get_by_test_id("dashboard-study-session").get_by_role(
            "link", name="Build from saved learning", exact=True
        )
    ).to_be_visible()
    dashboard_sync_payload = json.dumps(
        {
            "version": 1,
            "active_article_id": CRB_ARTICLE_ID,
            "updated_at": "2026-08-31T01:00:00.000Z",
            "items": [
                {
                    "article_id": CRB_ARTICLE_ID,
                    "title": CRB_TITLE,
                    "section_id": "regularity",
                    "added_at": "2026-08-31T01:00:00.000Z",
                }
            ],
        },
        ensure_ascii=False,
    )
    page.evaluate(
        """
        ([key, eventName, payload]) => {
          localStorage.setItem(key, payload);
          window.dispatchEvent(new Event(eventName));
        }
        """,
        [
            "scientific-spaces-study-session-v1",
            "scientific-spaces-study-session-change",
            dashboard_sync_payload,
        ],
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "ready"
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_contain_text(CRB_TITLE)
    page.evaluate(
        """
        ([key, eventName]) => {
          localStorage.removeItem(key);
          window.dispatchEvent(new Event(eventName));
        }
        """,
        ["scientific-spaces-study-session-v1", "scientific-spaces-study-session-change"],
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    checks["dashboard_session_same_tab_sync"] = True

    sync_page = context.new_page()
    _mark_expected_context_page(context, sync_page)
    sync_page.on(
        "console",
        lambda message: console_errors.capture(
            message, label="dashboard-cross-tab", page=sync_page
        ),
    )
    console_errors.observe_http_errors(sync_page, label="dashboard-cross-tab")
    sync_page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "dashboard-cross-tab", sync_page, error),
    )
    sync_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(sync_page)
    sync_page.evaluate(
        "([key, payload]) => localStorage.setItem(key, payload)",
        ["scientific-spaces-study-session-v1", dashboard_sync_payload],
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "ready"
    )
    sync_page.evaluate(
        "key => localStorage.removeItem(key)", "scientific-spaces-study-session-v1"
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    _wait_for_page_requests_to_settle(sync_page, console_errors)
    sync_page.close()
    checks["dashboard_session_cross_tab_sync"] = True
    expect(page.get_by_role("heading", name="Next Actions", exact=True)).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "dashboard")
    expect(page.get_by_test_id("workspace-context").locator('[aria-current="page"]')).to_have_text(
        "Dashboard"
    )
    _require(
        page.locator('nav[aria-label="Primary"] a').count() == 7,
        "desktop Application Shell does not expose seven primary workspaces",
    )
    next_actions = page.get_by_test_id("dashboard-next-actions")
    for action in ("Open saved learning", "Ask tutor", "Explore graph", "Review sources"):
        expect(next_actions.get_by_role("link", name=re.compile(rf"^{re.escape(action)}"))).to_be_visible()
    _require(
        page.locator('nav[aria-label="Primary"] [aria-current="page"]').get_attribute("href") == "/",
        "Dashboard navigation item is not marked as current",
    )
    checks["dashboard"] = True
    checks["dashboard_command_center"] = True
    checks["desktop_application_shell"] = True
    _verify_ordinary_shell_route_focus(
        browser,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["shell_ordinary_route_focus_continuity"] = True
    _verify_reader_fragment_focus_ownership(
        browser,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["reader_fragment_route_focus_ownership"] = True
    _verify_overlapping_shell_route_supersession(
        browser,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["shell_overlapping_route_supersession"] = True
    _verify_shell_reader_focus_ownership(
        browser,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["shell_reader_destination_focus_ownership"] = True
    checks["shell_superseding_ordinary_route_focus"] = True

    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    expect(search_trigger).to_be_visible()
    _require(
        search_trigger.inner_text().strip() == "Search",
        "desktop search trigger exposes shortcut instructions",
    )
    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    expect(search_dialog).to_be_visible()
    search_input = search_dialog.get_by_label("Search library")
    expect(search_input).to_be_focused()
    _require(
        search_dialog.locator('[data-testid="global-search-result-workspace"]').count() == 7,
        "global quick navigation does not expose seven stable workspaces",
    )
    last_workspace_result = search_dialog.locator(
        '[data-testid="global-search-result-workspace"]'
    ).last
    search_input.press("Shift+Tab")
    expect(last_workspace_result).to_be_focused()
    last_workspace_result.press("Tab")
    expect(search_input).to_be_focused()
    search_input.press("Escape")
    expect(search_dialog).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["global_search_entry_focus_and_quick_navigation"] = True

    page.evaluate("window.scrollTo(0, 300)")
    page.wait_for_function("() => window.scrollY > 0")
    search_trigger.click()
    same_url_dialog = page.get_by_test_id("global-search-dialog")
    same_url_dashboard = same_url_dialog.get_by_test_id(
        "global-search-result-workspace"
    ).filter(has_text=re.compile(r"^Dashboard"))
    same_url_history = page.evaluate("history.length")
    same_url_location = page.url
    same_url_scroll = page.evaluate("window.scrollY")
    page.evaluate(
        """
        () => {
          const originalFetch = window.fetch;
          const originalPushState = history.pushState;
          const originalReplaceState = history.replaceState;
          window.__p3030SameUrlActivity = { fetches: [], pushes: 0, replaces: 0 };
          window.__p3030SameUrlOriginals = {
            fetch: originalFetch,
            pushState: originalPushState,
            replaceState: originalReplaceState,
          };
          window.fetch = function (...args) {
            window.__p3030SameUrlActivity.fetches.push(String(args[0]));
            return originalFetch.apply(this, args);
          };
          history.pushState = function (...args) {
            window.__p3030SameUrlActivity.pushes += 1;
            return originalPushState.apply(this, args);
          };
          history.replaceState = function (...args) {
            window.__p3030SameUrlActivity.replaces += 1;
            return originalReplaceState.apply(this, args);
          };
        }
        """
    )
    same_url_dashboard.focus()
    same_url_dashboard.press("Enter")
    expect(same_url_dialog).to_have_count(0)
    shell_main = page.get_by_test_id("shell-main-content")
    expect(shell_main).to_be_focused(timeout=30_000)
    _require_visible_focus(shell_main, "same-URL Shell main")
    _require(page.evaluate("history.length") == same_url_history, "same-URL Search added history")
    _require(page.url == same_url_location, "same-URL Search changed the current URL")
    _require(page.evaluate("window.scrollY") == same_url_scroll, "same-URL Search changed scroll")
    _wait_for_animation_frames(page, 5)
    same_url_activity = page.evaluate(
        """
        () => {
          const activity = window.__p3030SameUrlActivity;
          const originals = window.__p3030SameUrlOriginals;
          window.fetch = originals.fetch;
          history.pushState = originals.pushState;
          history.replaceState = originals.replaceState;
          delete window.__p3030SameUrlActivity;
          delete window.__p3030SameUrlOriginals;
          return activity;
        }
        """
    )
    _require(
        same_url_activity == {"fetches": [], "pushes": 0, "replaces": 0},
        f"same-URL Search reached the Router despite preventDefault: {same_url_activity}",
    )
    page.evaluate("window.scrollTo(0, 0)")
    checks["shell_search_same_url_focus"] = True

    search_trigger.click()
    event_identity_search = page.get_by_test_id("global-search-dialog")
    expect(event_identity_search.get_by_label("Search library")).to_be_focused()
    page.evaluate(
        """
        () => {
          history.replaceState(history.state, '', '/session');
          const dashboardLink = document.querySelector(
            '[data-testid="global-search-dialog"] '
              + '[data-testid="global-search-result-workspace"][href="/"]'
          );
          if (!(dashboardLink instanceof HTMLElement)) {
            throw new Error('Search Dashboard link is unavailable');
          }
          dashboardLink.click();
        }
        """
    )
    expect(event_identity_search).to_have_count(0)
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    checks["shell_event_time_route_identity"] = True

    search_trigger.click()
    backdrop_search = page.get_by_test_id("global-search-dialog")
    expect(backdrop_search.get_by_label("Search library")).to_be_focused()
    page.mouse.click(10, 500)
    expect(backdrop_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_search_backdrop_dismissal"] = True

    search_trigger.click()
    close_button_search = page.get_by_test_id("global-search-dialog")
    expect(close_button_search.get_by_label("Search library")).to_be_focused()
    close_button_search.get_by_role("button", name="Close", exact=True).click()
    expect(close_button_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_search_close_button_dismissal"] = True

    search_trigger.click()
    breakpoint_search = page.get_by_test_id("global-search-dialog")
    breakpoint_input = breakpoint_search.get_by_label("Search library")
    expect(breakpoint_input).to_be_focused()
    page.set_viewport_size({"width": 800, "height": 1000})
    breakpoint_input.press("Escape")
    expect(breakpoint_search).to_have_count(0)
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "hidden-opener main fallback")
    page.set_viewport_size({"width": 1440, "height": 1000})
    expect(search_trigger).to_be_visible()
    checks["shell_hidden_opener_fallback"] = True

    search_trigger.click()
    reopened_search = page.get_by_test_id("global-search-dialog")
    reopened_search_input = reopened_search.get_by_label("Search library")
    expect(reopened_search_input).to_be_focused()
    page.evaluate(
        """
        () => {
          window.__p3030ReopenFocusBehindModal = [];
          window.__p3030ReopenFocusObserver = event => {
            const activeDialog = document.querySelector('[data-testid="global-search-dialog"]');
            if (activeDialog && event.target instanceof Node && !activeDialog.contains(event.target)) {
              window.__p3030ReopenFocusBehindModal.push(
                event.target instanceof Element
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030ReopenFocusObserver, true);
          const dialog = document.querySelector('[data-testid="global-search-dialog"]');
          const close = Array.from(dialog?.querySelectorAll('button') || [])
            .find(button => button.textContent?.trim() === 'Close');
          const trigger = document.querySelector('[data-testid="global-search-trigger-desktop"]');
          close?.click();
          trigger?.click();
        }
        """
    )
    expect(reopened_search).to_be_visible()
    expect(reopened_search_input).to_be_focused(timeout=30_000)
    _wait_for_animation_frames(page, 5)
    reopen_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030ReopenFocusObserver, true);
          return window.__p3030ReopenFocusBehindModal;
        }
        """
    )
    _require(
        reopen_focus_events == [],
        f"stale dismissal focused behind the reopened Search modal: {reopen_focus_events}",
    )
    reopened_search_input.press("Escape")
    expect(reopened_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_stale_dismiss_focus_cancelled"] = True

    search_trigger.click()
    superseded_search = page.get_by_test_id("global-search-dialog")
    expect(superseded_search.get_by_label("Search library")).to_be_focused()
    page.evaluate(
        """
        () => {
          window.__p3030OriginalRequestAnimationFrame = window.requestAnimationFrame.bind(window);
          window.__p3030HeldFocusFrames = [];
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 900000 + window.__p3030HeldFocusFrames.length;
          };
        }
        """
    )
    superseded_search.get_by_test_id("global-search-result-workspace").filter(
        has_text=re.compile(r"^Dashboard")
    ).click()
    expect(superseded_search).to_have_count(0)
    page.evaluate(
        """
        () => {
          if (window.__p3030HeldFocusFrames.length !== 1) {
            throw new Error(
              `expected one first-generation main-focus frame, got ${window.__p3030HeldFocusFrames.length}`
            );
          }
          const firstGeneration = window.__p3030HeldFocusFrames.shift();
          firstGeneration(performance.now());
          if (window.__p3030HeldFocusFrames.length !== 1) {
            throw new Error(
              `first-generation frame did not schedule exactly one nested frame: ${window.__p3030HeldFocusFrames.length}`
            );
          }
        }
        """
    )
    page.evaluate(
        "() => { window.requestAnimationFrame = window.__p3030OriginalRequestAnimationFrame; }"
    )
    session_navigation = page.get_by_test_id("primary-nav-session")
    session_navigation.click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    page.wait_for_timeout(50)
    session_navigation = page.get_by_test_id("primary-nav-session")
    session_navigation.focus()
    page.evaluate(
        """
        () => {
          const originalRequestAnimationFrame = window.__p3030OriginalRequestAnimationFrame;
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 920000 + window.__p3030HeldFocusFrames.length;
          };
          try {
            for (let generation = 0; generation < 4; generation += 1) {
              const callbacks = window.__p3030HeldFocusFrames.splice(0);
              if (callbacks.length === 0) break;
              callbacks.forEach(callback => callback(performance.now()));
            }
            if (window.__p3030HeldFocusFrames.length > 0) {
              throw new Error('stale main-focus RAF chain exceeded its bound');
            }
          } finally {
            window.requestAnimationFrame = originalRequestAnimationFrame;
          }
        }
        """
    )
    expect(session_navigation).to_be_focused()
    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["shell_new_route_invalidates_stale_focus"] = True

    search_trigger.click()
    stale_opener_search = page.get_by_test_id("global-search-dialog")
    stale_opener_input = stale_opener_search.get_by_label("Search library")
    expect(stale_opener_input).to_be_focused()
    page.evaluate(
        """
        () => {
          window.__p3030OriginalRequestAnimationFrame = window.requestAnimationFrame.bind(window);
          window.__p3030HeldFocusFrames = [];
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 910000 + window.__p3030HeldFocusFrames.length;
          };
        }
        """
    )
    stale_opener_input.press("Escape")
    expect(stale_opener_search).to_have_count(0)
    page.evaluate(
        "() => { window.requestAnimationFrame = window.__p3030OriginalRequestAnimationFrame; }"
    )
    page.go_back()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    page.wait_for_timeout(50)
    session_navigation = page.get_by_test_id("primary-nav-session")
    session_navigation.focus()
    page.evaluate(
        """
        () => {
          const originalRequestAnimationFrame = window.__p3030OriginalRequestAnimationFrame;
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 930000 + window.__p3030HeldFocusFrames.length;
          };
          try {
            for (let generation = 0; generation < 4; generation += 1) {
              const callbacks = window.__p3030HeldFocusFrames.splice(0);
              if (callbacks.length === 0) break;
              callbacks.forEach(callback => callback(performance.now()));
            }
            if (window.__p3030HeldFocusFrames.length > 0) {
              throw new Error('stale opener RAF chain exceeded its bound');
            }
          } finally {
            window.requestAnimationFrame = originalRequestAnimationFrame;
          }
        }
        """
    )
    expect(session_navigation).to_be_focused()
    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["shell_new_route_invalidates_stale_opener"] = True

    search_trigger.click()
    modified_search = page.get_by_test_id("global-search-dialog")
    modified_session = modified_search.get_by_test_id(
        "global-search-result-workspace"
    ).filter(has_text=re.compile(r"^Session"))
    modified_location = page.url
    page.evaluate(
        """
        () => {
          window.__p3030ModifiedFocusBehindModal = [];
          window.__p3030ModifiedFocusObserver = event => {
            const dialog = document.querySelector('[data-testid="global-search-dialog"]');
            if (dialog && event.target instanceof Node && !dialog.contains(event.target)) {
              window.__p3030ModifiedFocusBehindModal.push(
                event.target instanceof Element
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030ModifiedFocusObserver, true);
        }
        """
    )

    def attach_modified_page_observers(candidate) -> None:
        candidate.on(
            "console",
            lambda message: console_errors.capture(
                message, label="modified-search", page=candidate
            ),
        )
        candidate.on(
            "pageerror",
            lambda error: _capture_page_error(page_errors, "modified-search", candidate, error),
        )
        console_errors.observe_http_errors(candidate, label="modified-search")

    context.on("page", attach_modified_page_observers)
    with context.expect_page(timeout=10_000) as modified_page_info:
        modified_session.click(modifiers=["Control"])
    modified_page = modified_page_info.value
    _mark_expected_popup(blocked_external, context, modified_page)
    context.remove_listener("page", attach_modified_page_observers)
    modified_page.wait_for_load_state("domcontentloaded")
    _wait_for_application_shell(modified_page)
    expect(modified_page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    _require(modified_page.url.endswith("/session"), f"modified Search opened wrong URL: {modified_page.url}")
    _wait_for_page_requests_to_settle(modified_page, console_errors)
    modified_page.close()
    page.bring_to_front()
    expect(modified_search).to_be_visible()
    _require(page.url == modified_location, "modified Search navigation changed the current page")
    _wait_for_animation_frames(page, 5)
    _require(
        page.evaluate(
            """
            () => document.querySelector('[data-testid="global-search-dialog"]')
              ?.contains(document.activeElement) === true
            """
        ),
        "modified Search activation moved focus behind the open modal",
    )
    modified_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030ModifiedFocusObserver, true);
          return window.__p3030ModifiedFocusBehindModal;
        }
        """
    )
    _require(
        modified_focus_events == [],
        f"modified Search activation armed focus behind the modal: {modified_focus_events}",
    )
    page.keyboard.press("Escape")
    expect(modified_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_modified_navigation_preserves_modal"] = True

    search_trigger.click()
    slow_route_search = page.get_by_test_id("global-search-dialog")
    slow_route_search.get_by_label("Search library").fill("CRB")
    slow_graph_result = slow_route_search.get_by_role(
        "link", name=re.compile(r"^crb\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(slow_graph_result).to_be_visible(timeout=30_000)
    slow_graph_href = str(slow_graph_result.get_attribute("href") or "")
    _require(slow_graph_href.startswith("/graph?"), f"slow Graph target is invalid: {slow_graph_href}")
    page.evaluate(
        """
        targetHref => {
          const originalFetch = window.fetch;
          const target = new URL(targetHref, location.href);
          window.__p3030SlowRouteActivity = {
            delayedRequests: [],
            frameCount: 0,
            prematureMainFocus: false,
            originalFetch,
            targetRoute: `${target.pathname}${target.search}`,
          };
          window.__p3030SlowRouteFocusObserver = event => {
            const activity = window.__p3030SlowRouteActivity;
            if (
              `${location.pathname}${location.search}` !== activity.targetRoute
              && event.target instanceof Element
              && event.target.getAttribute('data-testid') === 'shell-main-content'
            ) {
              activity.prematureMainFocus = true;
            }
          };
          document.addEventListener('focusin', window.__p3030SlowRouteFocusObserver, true);
          window.fetch = async function (...args) {
            const input = args[0];
            const url = input instanceof Request ? input.url : String(input);
            const activity = window.__p3030SlowRouteActivity;
            if (
              url.includes('/graph?')
              && url.includes('_rsc=')
              && activity.delayedRequests.length === 0
            ) {
              activity.delayedRequests.push(url);
              await new Promise(resolve => {
                const nextFrame = () => {
                  activity.frameCount += 1;
                  if (activity.frameCount > 120) {
                    resolve();
                    return;
                  }
                  requestAnimationFrame(nextFrame);
                };
                requestAnimationFrame(nextFrame);
              });
            }
            return originalFetch.apply(this, args);
          };
        }
        """,
        slow_graph_href,
    )
    slow_graph_result.click()
    expect(slow_route_search).to_have_count(0)
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
        timeout=30_000
    )
    slow_route_main = page.get_by_test_id("shell-main-content")
    expect(slow_route_main).to_be_focused(timeout=30_000)
    _wait_for_animation_frames(page, 5)
    expect(slow_route_main).to_be_focused()
    _require_visible_focus(slow_route_main, "slow Search route destination")
    slow_route_activity = page.evaluate(
        """
        () => {
          const activity = window.__p3030SlowRouteActivity;
          document.removeEventListener('focusin', window.__p3030SlowRouteFocusObserver, true);
          window.fetch = activity.originalFetch;
          delete window.__p3030SlowRouteActivity;
          delete window.__p3030SlowRouteFocusObserver;
          return {
            delayedRequests: activity.delayedRequests,
            frameCount: activity.frameCount,
            prematureMainFocus: activity.prematureMainFocus,
          };
        }
        """
    )
    _require(
        len(slow_route_activity["delayedRequests"]) == 1,
        "slow Shell route probe did not delay one RSC request: "
        f"{slow_route_activity['delayedRequests']}",
    )
    _require(
        slow_route_activity["frameCount"] > 120,
        f"slow Shell route probe observed too few frames: {slow_route_activity['frameCount']}",
    )
    _require(
        slow_route_activity["prematureMainFocus"] is False,
        "Shell focused main before the delayed route committed",
    )
    checks["shell_slow_route_focus_ownership"] = True
    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")

    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    search_dialog.get_by_label("Search library").fill("")
    session_workspace_result = search_dialog.get_by_test_id(
        "global-search-result-workspace"
    ).filter(has_text=re.compile(r"^Session"))
    expect(session_workspace_result).to_be_visible()
    session_workspace_result.click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("study-session-empty")).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "session")
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "Search workspace destination")
    checks["shell_search_workspace_route_focus"] = True
    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["study_session_empty_and_quick_navigation"] = True

    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    saved_workspace_result = search_dialog.get_by_test_id("global-search-result-workspace").filter(
        has_text=re.compile(r"^Saved")
    )
    expect(saved_workspace_result).to_be_visible()
    quick_saved_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/library",
    )
    saved_workspace_result.click()
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_test_id("saved-library-empty")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "library")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, quick_saved_transition)
    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    search_trigger.focus()
    checks["saved_library_empty_and_quick_navigation"] = True

    primary_reference_failure = _declare_expected_http_errors(
        console_errors,
        label="primary",
        page_url=f"{FRONTEND_URL}/",
        source_url=f"{BROWSER_API_URL}/v1.2/references?page=1&page_size=5&q=Attention",
    )
    page.route(
        re.compile(r".*/v1\.2/references(?:\?.*)?$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=primary_reference_failure,
            body='{"detail":"intentional P3-019 partial Reference failure"}',
        ),
        times=1,
    )
    page.keyboard.press("Control+K")
    search_dialog = page.get_by_test_id("global-search-dialog")
    expect(search_dialog).to_be_visible()
    search_input = search_dialog.get_by_label("Search library")
    expect(search_input).to_be_focused()
    page.keyboard.press("Control+K")
    expect(search_input).to_be_focused()
    search_input.fill("Attention")
    article_search_result = search_dialog.get_by_test_id("global-search-result-article").first
    graph_search_result = search_dialog.get_by_role(
        "link", name=re.compile(r"^attention\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(article_search_result).to_be_visible(timeout=30_000)
    expect(graph_search_result).to_be_visible(timeout=30_000)
    expect(search_dialog.get_by_text("Some sources are unavailable", exact=True)).to_be_visible()
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=primary_reference_failure,
    )
    _require(
        "q%3DAttention%26sort%3Drelevance" in (article_search_result.get_attribute("href") or ""),
        "global Article result does not preserve its relevance-search return path",
    )
    visible_search_text = search_dialog.inner_text()
    _require(
        "attention-basics" not in visible_search_text and "concept:attention" not in visible_search_text,
        "global search exposes raw internal identifiers",
    )
    search_input.press("ArrowDown")
    expect(article_search_result).to_be_focused()
    article_search_result.press("Escape")
    expect(search_dialog).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["global_search_partial_failure_and_keyboard"] = True

    search_trigger.click()
    article_route_search = page.get_by_test_id("global-search-dialog")
    article_route_transition = _declare_expected_route_transition(
        page,
        destination_url=(
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}"
            "?from=%2Farticles%3Fq%3DCRB%26sort%3Drelevance"
        ),
    )
    article_route_search.get_by_label("Search library").fill("CRB")
    article_route_result = article_route_search.get_by_test_id("global-search-result-article").first
    expect(article_route_result).to_be_visible(timeout=30_000)
    article_route_graph_result = article_route_search.get_by_role(
        "link", name=re.compile(r"^crb\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(article_route_graph_result).to_be_visible(timeout=30_000)
    page.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-030-shell-focus-probe",
                    "article_id": CRB_ARTICLE_ID,
                    "started_at": "2026-09-05T01:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    article_route_result.click()
    expect(article_route_search).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "Search Article destination")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, article_route_transition)
    page.go_back()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["shell_search_article_route_focus"] = True

    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    search_input = search_dialog.get_by_label("Search library")
    page.evaluate(
        """
        () => {
          const originalFetch = window.fetch.bind(window);
          let delayed = false;
          window.fetch = (...args) => {
            const url = String(args[0]);
            if (!delayed && url.includes('/v1.1/articles') && url.includes('q=CRB')) {
              delayed = true;
              const response = originalFetch(...args);
              return new Promise((resolve, reject) => {
                window.setTimeout(() => response.then(resolve, reject), 1000);
              });
            }
            return originalFetch(...args);
          };
        }
        """
    )
    search_input.fill("CRB")
    stale_search_graph_result = search_dialog.get_by_role(
        "link", name=re.compile(r"^crb\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(stale_search_graph_result).to_be_visible(timeout=30_000)
    search_input.fill("Attention")
    current_article_result = search_dialog.get_by_test_id("global-search-result-article").first
    expect(current_article_result).to_contain_text("Attention机制入门", timeout=30_000)
    page.wait_for_timeout(1100)
    expect(current_article_result).to_contain_text("Attention机制入门")
    expect(search_input).to_have_value("Attention")
    checks["global_search_stale_response_guard"] = True

    search_input.fill("1706.03762")
    expect(search_dialog.get_by_test_id("global-search-result-reference").first).to_be_visible(
        timeout=30_000
    )
    graph_search_url = (
        f"{FRONTEND_URL}/graph?node_id=concept%3Aattention&q=Attention"
    )
    graph_search_route_anchor = console_errors._event_sequence
    graph_search_transition = _declare_expected_route_transition(
        page,
        destination_url=graph_search_url,
    )
    search_input.fill("Attention")
    graph_search_result = search_dialog.get_by_role(
        "link", name=re.compile(r"^attention\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(graph_search_result).to_be_visible(timeout=30_000)
    graph_search_href = str(graph_search_result.get_attribute("href") or "")
    _require(
        graph_search_href.startswith("/graph?"),
        f"global search Graph result exposed an invalid route: {graph_search_href}",
    )
    _require(
        f"{FRONTEND_URL}{graph_search_href}" == graph_search_url,
        "global search Graph result diverged from its declared route: "
        f"href={graph_search_href} expected={graph_search_url}",
    )
    graph_search_result.click()
    expect(search_dialog).to_have_count(0)
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    expect(page.get_by_placeholder("Title, concept, or formula")).to_have_value("Attention")
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "Search Graph destination")
    _require("node_id=concept%3Aattention" in page.url, f"Graph deep link was not preserved: {page.url}")
    initial_attention_route_request = _wait_for_exact_route_request_to_finish(
        page,
        console_errors,
        source_url=graph_search_url,
        after_sequence=graph_search_route_anchor,
        expect_prefetch=False,
        require_observed_request=True,
        allow_response_backed_route_abort=True,
        cache_precursor_expectation_id=graph_search_transition,
    )
    _require(
        isinstance(initial_attention_route_request, dict)
        and initial_attention_route_request.get("finished") is True
        and initial_attention_route_request.get("failure") is None,
        "completed-precursor revisit coverage requires a successful initial Attention response: "
        f"{initial_attention_route_request}",
    )
    _complete_expected_route_transition(page, graph_search_transition)
    checks["global_search_reference_and_graph_deep_link"] = True

    page.get_by_test_id("global-search-trigger-desktop").click()
    same_route_search = page.get_by_test_id("global-search-dialog")
    same_route_graph_url = f"{FRONTEND_URL}/graph?node_id=concept%3Acrb&q=CRB"
    same_route_graph_route_anchor = console_errors._event_sequence
    same_route_graph_transition = _declare_expected_route_transition(
        page,
        destination_url=same_route_graph_url,
        allow_post_terminal_destination_commit=True,
    )
    same_route_search_input = same_route_search.get_by_label("Search library")
    same_route_search_input.fill("CRB")
    same_route_graph_result = same_route_search.get_by_role(
        "link", name=re.compile(r"^crb\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(same_route_graph_result).to_be_visible(timeout=30_000)
    same_route_graph_result.hover()
    expect(same_route_graph_result).to_have_class(re.compile(r"\bborder-emerald-600\b"))
    same_route_search_input.focus()
    expect(same_route_search_input).to_be_focused()
    same_route_search_input.press("Enter")
    expect(same_route_search).to_have_count(0)
    same_route_selected = page.get_by_test_id("graph-selected-region")
    expect(same_route_selected).to_be_focused(timeout=30_000)
    _require_visible_focus(same_route_selected, "same-route global-search Graph detail")
    expect(same_route_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    _require(
        "node_id=concept%3Acrb" in page.url and "q=CRB" in page.url,
        f"same-route Graph navigation diverged from its URL: {page.url}",
    )
    checks["global_search_same_route_graph_navigation"] = True
    same_route_graph_request = _wait_for_exact_route_request_to_finish(
        page,
        console_errors,
        source_url=same_route_graph_url,
        after_sequence=same_route_graph_route_anchor,
        expect_prefetch=False,
        require_observed_request=True,
        allow_response_backed_route_abort=True,
        cache_precursor_expectation_id=same_route_graph_transition,
    )
    _require(
        isinstance(same_route_graph_request, dict),
        "same-route Graph transition did not expose its exact RSC request",
    )
    same_route_graph_expectation = next(
        item
        for item in console_errors.route_transition_expectations
        if item["expectation_id"] == same_route_graph_transition
    )
    if (
        same_route_graph_request.get("failure") == "net::ERR_ABORTED"
        and _route_document_key(str(same_route_graph_request.get("page_url") or ""))
        not in {
            _route_document_key(str(same_route_graph_expectation["request_page_url"])),
            _route_document_key(same_route_graph_url),
        }
        and not _has_pre_start_route_navigation(
            console_errors, same_route_graph_expectation, same_route_graph_request
        )
    ):
        _bind_expected_post_terminal_destination_request(
            page,
            expectation_id=same_route_graph_transition,
            evidence=same_route_graph_request,
        )
    _complete_expected_route_transition(page, same_route_graph_transition)
    _require(
        same_route_graph_request.get("failure") != "net::ERR_ABORTED"
        or _is_route_transition_cancellation(
            console_errors,
            same_route_graph_request,
        ),
        "same-route Graph response-backed cancellation lost its exact lifecycle: "
        f"expectation={same_route_graph_expectation} "
        f"request={same_route_graph_request} "
        f"navigation_events={console_errors._page_navigation_events.get(_page_identity(page), ())}",
    )

    same_route_selected.press("Control+k")
    shortcut_search = page.get_by_test_id("global-search-dialog")
    shortcut_input = shortcut_search.get_by_label("Search library")
    expect(shortcut_input).to_be_focused()
    shortcut_graph_url = (
        f"{FRONTEND_URL}/graph?node_id=concept%3Aattention&q=Attention"
    )
    shortcut_graph_route_anchor = console_errors._event_sequence
    shortcut_graph_transition = _declare_expected_route_transition(
        page,
        destination_url=shortcut_graph_url,
        allow_complete_precursor_snapshot=True,
    )
    shortcut_input.fill("Attention")
    shortcut_graph_result = shortcut_search.get_by_role(
        "link", name=re.compile(r"^attention\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(shortcut_graph_result).to_be_visible(timeout=30_000)
    page.evaluate(
        """
        () => {
          window.__p3030ShortcutRouteFocusEvents = [];
          window.__p3030ShortcutRouteFocusObserver = event => {
            if (event.target instanceof HTMLElement) {
              window.__p3030ShortcutRouteFocusEvents.push(
                event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
              );
            }
          };
          document.addEventListener('focusin', window.__p3030ShortcutRouteFocusObserver, true);
        }
        """
    )
    shortcut_graph_result.focus()
    shortcut_graph_result.press("Enter")
    expect(shortcut_search).to_have_count(0)
    shortcut_selected = page.get_by_test_id("graph-selected-region")
    expect(shortcut_selected.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(shortcut_selected).to_be_focused(timeout=30_000)
    _wait_for_animation_frames(page, 5)
    shortcut_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030ShortcutRouteFocusObserver, true);
          return window.__p3030ShortcutRouteFocusEvents;
        }
        """
    )
    expect(shortcut_selected).to_be_focused()
    _require(
        "shell-main-content" not in shortcut_focus_events,
        f"Shell stole shortcut-origin Graph focus: {shortcut_focus_events}",
    )
    _wait_for_exact_route_request_to_finish(
        page,
        console_errors,
        source_url=shortcut_graph_url,
        after_sequence=shortcut_graph_route_anchor,
        expect_prefetch=False,
        require_observed_request=True,
        allow_response_backed_route_abort=True,
        cache_precursor_expectation_id=shortcut_graph_transition,
    )
    _complete_expected_route_transition(page, shortcut_graph_transition)
    shortcut_graph_back_transition = _declare_expected_route_transition(
        page,
        destination_url=same_route_graph_url,
    )
    page.go_back()
    same_route_selected = page.get_by_test_id("graph-selected-region")
    expect(same_route_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(same_route_selected).to_be_focused(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, shortcut_graph_back_transition)
    checks["shell_shortcut_destination_focus_ownership"] = True

    page.evaluate(
        """
        () => {
          window.__p3030FocusBehindModal = [];
          window.__p3030FocusObserver = event => {
            const modal = document.querySelector('[aria-modal="true"]');
            if (modal && event.target instanceof Node && !modal.contains(event.target)) {
              window.__p3030FocusBehindModal.push(
                event.target instanceof HTMLElement
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030FocusObserver, true);
        }
        """
    )
    page.get_by_test_id("global-search-trigger-desktop").click()
    history_search = page.get_by_test_id("global-search-dialog")
    expect(history_search).to_be_visible()
    page.go_back()
    expect(history_search).to_have_count(0)
    history_selected = page.get_by_test_id("graph-selected-region")
    expect(history_selected.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(history_selected).to_be_focused(timeout=30_000)
    _require_visible_focus(history_selected, "Graph Back destination")
    _wait_for_animation_frames(page, 5)
    expect(history_selected).to_be_focused()

    page.get_by_test_id("global-search-trigger-desktop").click()
    history_search = page.get_by_test_id("global-search-dialog")
    expect(history_search).to_be_visible()
    page.go_forward()
    expect(history_search).to_have_count(0)
    history_selected = page.get_by_test_id("graph-selected-region")
    expect(history_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(history_selected).to_be_focused(timeout=30_000)
    _require_visible_focus(history_selected, "Graph Forward destination")
    _wait_for_animation_frames(page, 5)
    expect(history_selected).to_be_focused()
    focus_behind_modal = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030FocusObserver, true);
          return window.__p3030FocusBehindModal;
        }
        """
    )
    _require(not focus_behind_modal, f"route focus escaped a mounted Shell modal: {focus_behind_modal}")
    checks["shell_query_history_modal_focus"] = True

    page.get_by_test_id("primary-nav-session").click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    page.evaluate(
        """
        () => {
          window.__p3030PathFocusBehindModal = [];
          window.__p3030PathFocusObserver = event => {
            const modal = document.querySelector('[aria-modal="true"]');
            if (modal && event.target instanceof Node && !modal.contains(event.target)) {
              window.__p3030PathFocusBehindModal.push(
                event.target instanceof HTMLElement
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030PathFocusObserver, true);
        }
        """
    )
    page.get_by_test_id("global-search-trigger-desktop").click()
    pathname_history_search = page.get_by_test_id("global-search-dialog")
    expect(pathname_history_search.get_by_label("Search library")).to_be_focused()
    page.go_back()
    expect(pathname_history_search).to_have_count(0)
    pathname_history_selected = page.get_by_test_id("graph-selected-region")
    expect(pathname_history_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    pathname_history_main = page.get_by_test_id("shell-main-content")
    expect(pathname_history_main).to_be_focused(timeout=30_000)
    _require_visible_focus(pathname_history_main, "pathname Back destination")
    _wait_for_animation_frames(page, 5)
    expect(pathname_history_main).to_be_focused()

    page.get_by_test_id("global-search-trigger-desktop").click()
    pathname_history_search = page.get_by_test_id("global-search-dialog")
    expect(pathname_history_search.get_by_label("Search library")).to_be_focused()
    page.go_forward()
    expect(pathname_history_search).to_have_count(0)
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    pathname_history_main = page.get_by_test_id("shell-main-content")
    expect(pathname_history_main).to_be_focused(timeout=30_000)
    _require_visible_focus(pathname_history_main, "pathname Forward destination")
    _wait_for_animation_frames(page, 5)
    expect(pathname_history_main).to_be_focused()
    pathname_focus_behind_modal = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030PathFocusObserver, true);
          return window.__p3030PathFocusBehindModal;
        }
        """
    )
    _require(
        not pathname_focus_behind_modal,
        f"pathname history focus escaped a mounted Shell modal: {pathname_focus_behind_modal}",
    )
    checks["shell_pathname_history_modal_focus"] = True

    primary_dashboard_transition = _declare_expected_route_transition(
        page,
        destination_url=FRONTEND_URL,
    )
    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, primary_dashboard_transition)

    primary_articles_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    page.get_by_role("link", name="Articles", exact=True).click()
    expect(page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(page.locator('nav[aria-label="Primary"] [aria-current="page"]')).to_have_text("Articles")
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "articles")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, primary_articles_transition)
    page.get_by_placeholder("Search title or keyword").fill("CRB")
    page.get_by_role("button", name="Search", exact=True).click()
    article_link = page.get_by_role("link", name=CRB_TITLE, exact=True)
    expect(article_link).to_be_visible(timeout=30_000)
    preview_text = article_link.locator("xpath=ancestor::article[1]").get_by_test_id("article-preview").inner_text()
    _require("# " not in preview_text and "](" not in preview_text, "article preview exposes Markdown syntax")
    checks["title_and_keyword_search"] = True

    capture_url = page.url
    page.evaluate(
        """
        () => {
          window.__p3026LearningWrites = 0;
          window.__p3026SessionWrites = 0;
          const originalFetch = window.fetch.bind(window);
          const originalSetItem = Storage.prototype.setItem;
          window.fetch = (...args) => {
            const url = String(args[0]);
            const method = String(args[1]?.method || "GET").toUpperCase();
            if (url.includes("/learning/") && method !== "GET") {
              window.__p3026LearningWrites += 1;
            }
            return originalFetch(...args);
          };
          Storage.prototype.setItem = function (key, value) {
            if (key === "scientific-spaces-study-session-v1") {
              window.__p3026SessionWrites += 1;
            }
            return originalSetItem.call(this, key, value);
          };
        }
        """
    )
    capture_checkbox = page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    _focus_via_tab(page, capture_checkbox)
    capture_checkbox.press("Space")
    expect(capture_checkbox).to_be_checked()
    capture_action = page.get_by_role("button", name="Add selected to session", exact=True)
    _focus_via_tab(page, capture_action)
    capture_action.press("Enter")
    capture_feedback = page.get_by_test_id("article-session-capture-feedback")
    expect(capture_feedback).to_be_focused()
    expect(capture_feedback).to_have_attribute("aria-live", "polite")
    expect(capture_feedback).to_have_attribute("aria-atomic", "true")
    expect(capture_feedback).to_contain_text(
        "1 added; 0 already present; 0 invalid; 0 omitted by capacity."
    )
    _require_visible_focus(capture_feedback, "Article capture feedback")
    capture_feedback_box = capture_feedback.bounding_box()
    _require(
        capture_feedback_box is not None
        and capture_feedback_box["y"] < page.viewport_size["height"]
        and capture_feedback_box["y"] + capture_feedback_box["height"] > 0,
        f"Article capture feedback does not intersect the viewport: {capture_feedback_box}",
    )
    captured_session = page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        [item["article_id"] for item in captured_session["items"]] == [CRB_ARTICLE_ID]
        and captured_session["active_article_id"] == CRB_ARTICLE_ID,
        f"Article capture persisted the wrong Session: {captured_session}",
    )
    _require(page.url == capture_url, "Article capture navigated or changed list URL state")
    _require(
        page.evaluate("window.__p3026LearningWrites") == 0,
        "Article capture mutated Learning State or Bookmark data",
    )
    _require(
        page.evaluate("window.__p3026SessionWrites") == 1,
        "Article capture did not use exactly one Session storage write",
    )
    expect(article_link.locator("xpath=ancestor::article[1]")).to_contain_text("In session")
    page.evaluate(
        """
        () => {
          localStorage.removeItem("scientific-spaces-study-session-v1");
          window.dispatchEvent(new Event("scientific-spaces-study-session-change"));
        }
        """
    )
    expect(article_link.locator("xpath=ancestor::article[1]")).not_to_contain_text("In session")
    checks["article_session_capture_keyboard_and_truthful_write"] = True
    checks["article_session_capture_no_server_mutation_or_navigation"] = True

    page.get_by_placeholder("Search title or keyword").fill("__p3_011_no_matching_article__")
    page.get_by_role("button", name="Search", exact=True).click()
    expect(page.get_by_text("No articles found.", exact=True)).to_be_visible(timeout=30_000)
    page.get_by_placeholder("Search title or keyword").fill("CRB")
    page.get_by_role("button", name="Search", exact=True).click()
    article_link = page.get_by_role("link", name=CRB_TITLE, exact=True)
    expect(article_link).to_be_visible(timeout=30_000)
    checks["empty_search_state"] = True

    article_link.click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    article_trail = page.get_by_test_id("workspace-context")
    expect(article_trail).to_contain_text("Articles")
    expect(article_trail).to_contain_text("Article")
    expect(article_trail).not_to_contain_text(CRB_ARTICLE_ID)
    expect(page.locator(".reader-markdown")).to_contain_text("Fisher")
    expect(page.locator(".reader-markdown .katex").first).to_be_visible()
    expect(page.get_by_text("External image not loaded automatically.", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Structured References", exact=True)).to_be_visible()
    expect(page.get_by_text("10.1000/example", exact=False).first).to_be_visible(timeout=30_000)
    checks["article_markdown_formula_and_reference"] = True

    outline = page.get_by_test_id("article-outline")
    expect(outline).to_be_visible()
    heading_ids = page.locator(".reader-markdown h2, .reader-markdown h3, .reader-markdown h4").evaluate_all(
        "nodes => nodes.map(node => node.id)"
    )
    _require(heading_ids and all(heading_ids), "reader headings are missing anchors")
    _require(len(heading_ids) == len(set(heading_ids)), "reader heading anchors are not unique")
    target_outline_link = outline.get_by_role("link", name="数值检查", exact=True).first
    target_section_id = unquote((target_outline_link.get_attribute("href") or "").lstrip("#"))
    target_outline_link.click()
    _require(
        page.evaluate("() => document.activeElement?.id") == target_section_id,
        "outline navigation did not move focus to the target heading",
    )
    page.wait_for_function("() => window.scrollY > 0")
    page.wait_for_function(
        "() => Number(document.querySelector('[data-testid=reading-progress]')?.getAttribute('aria-valuenow') || 0) > 0"
    )
    expect(target_outline_link).to_have_attribute("aria-current", "location")
    expect(outline.locator('[aria-current="location"]')).to_have_text("数值检查")
    progress_value = int(page.get_by_test_id("reading-progress").get_attribute("aria-valuenow") or "0")
    _require(0 < progress_value <= 100, f"reader progress is out of bounds: {progress_value}")
    page.get_by_role("button", name="Large text", exact=True).click()
    page.get_by_role("button", name="Wide", exact=True).click()
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-size", "large")
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-width", "wide")
    checks["reader_outline_progress_and_preferences"] = True

    end_session_button = page.get_by_role("button", name="End session", exact=True)
    expect(end_session_button).to_be_enabled(timeout=30_000)
    sessions = _api_json(context, "GET", "/learning/sessions")
    _require(sessions["total"] == 1, f"expected one reader session, got {sessions['total']}")
    checks["single_reader_session"] = True

    completed_button = page.get_by_role("button", name="completed", exact=True)
    completed_button.click()
    expect(completed_button).to_have_class(re.compile(r"\bbg-slate-950\b"), timeout=30_000)
    learning_state_controls = page.get_by_test_id("learning-state-controls")
    expect(learning_state_controls).to_be_focused(timeout=30_000)
    _require_visible_focus(learning_state_controls, "Reader learning-state result")
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("button", name="Remove", exact=True)).to_be_visible(timeout=30_000)
    bookmark_controls = page.get_by_test_id("bookmark-controls")
    expect(bookmark_controls).to_be_focused(timeout=30_000)
    _require_visible_focus(bookmark_controls, "Reader bookmark result")
    note_text = f"P3-011 iteration {iteration}"
    page.get_by_placeholder("Write a learning note").fill(note_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    expect(page.get_by_text(note_text, exact=True)).to_be_visible()
    note_status = page.get_by_test_id("note-mutation-status")
    expect(note_status).to_be_focused(timeout=30_000)
    _require_visible_focus(note_status, "Reader note-create result")
    end_session_button.click()
    expect(end_session_button).to_be_disabled()
    reader_session_controls = page.get_by_test_id("reader-session-controls")
    expect(reader_session_controls).to_be_focused(timeout=30_000)
    _require_visible_focus(reader_session_controls, "Reader standalone session result")

    stats = _api_json(context, "GET", "/learning/stats")
    _require(stats["completed_count"] == 1, "completed learning state was not persisted")
    _require(stats["bookmark_count"] == 1, "bookmark was not persisted")
    _require(stats["note_count"] == 1, "note was not persisted")
    ended_sessions = _api_json(context, "GET", "/learning/sessions")
    _require(
        ended_sessions["items"][0]["ended_at"] is not None,
        "reader session did not end",
    )
    checks["learning_state_bookmark_note_and_session"] = True

    persisted_reader_state = page.evaluate(
        "() => JSON.parse(localStorage.getItem('scientific-spaces-reader-progress-v1') || '{\"items\":[]}').items[0] || null"
    )
    _require(
        persisted_reader_state is not None
        and persisted_reader_state.get("section_id") == target_section_id,
        f"reader state lost the last meaningful section: {persisted_reader_state}",
    )

    tutor_action = page.get_by_role("link", name="Ask tutor", exact=True)
    expect(tutor_action).to_be_visible()
    tutor_action.click()
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(page.get_by_test_id("learning-workflow-context")).to_contain_text(CRB_TITLE)
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(CRB_TITLE)
    _require(page.get_by_label("Article ID").count() == 0, "Tutor still exposes a raw Article ID input")
    tutor_return = page.get_by_role("link", name="Return to article", exact=True)
    tutor_return_href = tutor_return.get_attribute("href") or ""
    _require(
        tutor_return_href.startswith(f"/articles/{CRB_ARTICLE_ID}")
        and "from=" in tutor_return_href
        and "#" in tutor_return_href,
        f"Tutor return context is incomplete: {tutor_return_href}",
    )
    tutor_return.click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("article-outline").locator('[aria-current="location"]')).to_be_visible()
    tutor_return_session = page.get_by_role("button", name="End session", exact=True)
    expect(tutor_return_session).to_be_enabled(timeout=30_000)
    tutor_return_session.click()
    expect(tutor_return_session).to_be_disabled()

    graph_action = page.get_by_role("link", name="Explore graph", exact=True)
    expect(graph_action).to_be_visible()
    graph_action.click()
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    expect(page.get_by_test_id("learning-workflow-context")).to_contain_text(CRB_TITLE)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    graph_workspace_modes = page.get_by_role("group", name="Graph workspace view")
    expect(graph_workspace_modes.get_by_role("button", name="Explore", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    graph_workspace_modes.get_by_role("button", name="Knowledge context", exact=True).click()
    desktop_context_region = page.locator("#graph-context-workspace")
    expect(desktop_context_region).to_be_focused()
    _require_visible_focus(desktop_context_region, "desktop Knowledge Context region")
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    selected_article_map_node = page.get_by_role(
        "button", name=f"Selected Article: {CRB_TITLE}", exact=True
    )
    expect(selected_article_map_node).to_be_visible(timeout=30_000)
    desktop_canvas_box = page.locator(".knowledge-graph-canvas").bounding_box()
    desktop_map_node_box = selected_article_map_node.bounding_box()
    _require_box_inside(
        desktop_canvas_box,
        desktop_map_node_box,
        "desktop selected Graph node",
        minimum_width=80,
        minimum_height=30,
    )
    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.locator('select[name="node_type"]').select_option("concept")
    filter_history_length = page.evaluate("history.length")
    page.get_by_role("button", name="Apply", exact=True).click()
    page.wait_for_function("() => new URLSearchParams(location.search).get('q') === 'Attention'")
    _require(
        "node_id=article%3Acrb-formula" in page.url,
        f"Graph filter replacement lost the selected Article: {page.url}",
    )
    _require(
        page.evaluate("history.length") == filter_history_length,
        "applying Graph filters created a browser history entry",
    )
    page.get_by_role("button", name="Clear", exact=True).click()
    page.wait_for_function("() => !new URLSearchParams(location.search).has('q')")
    _require(
        "node_id=article%3Acrb-formula" in page.url,
        f"clearing Graph filters lost the selected Article: {page.url}",
    )
    _require(
        page.evaluate("history.length") == filter_history_length,
        "clearing Graph filters created a browser history entry",
    )
    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.locator('select[name="node_type"]').select_option("concept")
    page.get_by_role("button", name="Apply", exact=True).click()
    graph_workspace_modes.get_by_role("button", name="Explore", exact=True).click()
    context_graph_node = (
        page.get_by_test_id("graph-node-results")
        .locator("button")
        .filter(has_text=re.compile(r"^Attention", re.I))
        .first
    )
    expect(context_graph_node).to_be_visible(timeout=30_000)
    context_graph_node.focus()
    expect(context_graph_node).to_be_focused()
    history_before_selection = page.evaluate("history.length")
    context_graph_node.press("Enter")
    expect(page.get_by_test_id("graph-selected-region")).to_be_focused()
    _require_visible_focus(page.get_by_test_id("graph-selected-region"), "desktop selected Graph region")
    _require(
        "node_id=concept%3Aattention" in page.url
        and "q=Attention" in page.url
        and "article_id=crb-formula" in page.url,
        f"Graph selection URL is incomplete: {page.url}",
    )
    _require(
        page.evaluate("history.length") == history_before_selection + 1,
        "different-node selection did not create exactly one history entry",
    )
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
    desktop_detail_region = page.get_by_test_id("graph-selected-region")
    _require(
        desktop_detail_region.evaluate("node => getComputedStyle(node).overflowY") == "auto",
        "desktop selected-node inspector is not independently scrollable",
    )
    _require(
        desktop_detail_region.evaluate("node => getComputedStyle(node).position") == "sticky",
        "desktop selected-node inspector is not sticky at runtime",
    )
    desktop_detail_first_control = desktop_detail_region.get_by_role(
        "button", name="Knowledge context", exact=True
    )
    page.keyboard.press("Tab")
    expect(desktop_detail_first_control).to_be_focused()
    desktop_detail_last_control = desktop_detail_region.get_by_role(
        "link", name="Open concept quiz", exact=True
    )
    _focus_via_tab(page, desktop_detail_last_control, max_steps=40)
    expect(desktop_detail_last_control).to_be_focused()
    _require(
        desktop_detail_region.evaluate("node => node.scrollTop") > 0,
        "keyboard focus did not reveal the final control in the sticky inspector",
    )
    checks["graph_sticky_detail_keyboard_reach"] = True
    selected_history_length = page.evaluate("history.length")
    context_graph_node.click()
    _require(
        page.evaluate("history.length") == selected_history_length,
        "same-node selection created another history entry",
    )
    page.go_back()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    _require("node_id=article%3Acrb-formula" in page.url, f"Graph Back state diverged: {page.url}")
    page.go_forward()
    expect(page.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(timeout=30_000)
    _require("node_id=concept%3Aattention" in page.url, f"Graph Forward state diverged: {page.url}")

    graph_reload_url = page.url
    page.close()
    page = _new_observed_page(context, console_errors, page_errors, label="graph-reload")
    page.goto(graph_reload_url, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(timeout=30_000)
    page.wait_for_load_state("networkidle")
    _require(not page_errors, f"Graph deep-link reopen emitted page errors: {page_errors}")
    page.reload(wait_until="networkidle")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(timeout=30_000)
    _require(not page_errors, f"Graph hard reload emitted page errors: {page_errors}")
    expect(page.get_by_placeholder("Title, concept, or formula")).to_have_value("Attention")
    expect(page.get_by_test_id("learning-workflow-context")).to_contain_text(CRB_TITLE)
    checks["graph_canonical_history_and_focus"] = True
    graph_workspace_modes = page.get_by_role("group", name="Graph workspace view")
    graph_workspace_modes.get_by_role("button", name="Knowledge context", exact=True).click()
    expect(
        page.get_by_role("button", name=re.compile(r"^Selected Concept: Attention", re.I))
    ).to_be_visible(timeout=30_000)
    page.get_by_test_id("graph-view-list").click()
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    page.get_by_test_id("graph-view-map").click()
    expect(page.get_by_test_id("graph-visualization")).to_be_visible()
    graph_return = page.get_by_role("link", name="Return to article", exact=True)
    graph_return_href = graph_return.get_attribute("href") or ""
    _require(
        graph_return_href.startswith(f"/articles/{CRB_ARTICLE_ID}")
        and "from=" in graph_return_href
        and "#" in graph_return_href,
        f"Graph return context is incomplete: {graph_return_href}",
    )
    graph_return.click()
    page.wait_for_function(
        "expected => location.pathname + location.search + location.hash === expected",
        arg=graph_return_href,
        timeout=30_000,
    )
    returned_reader = page.locator("article#article-start")
    expect(returned_reader.locator(":scope > h1")).to_have_text(
        CRB_TITLE,
        timeout=30_000
    )
    expect(page.get_by_role("status").filter(has_text="Loading article")).to_have_count(0)
    expect(page.get_by_test_id("article-outline").locator('[aria-current="location"]')).to_be_visible()
    graph_return_session = page.get_by_role("button", name="End session", exact=True)
    expect(graph_return_session).to_be_enabled(timeout=30_000)
    graph_return_session.click()
    expect(graph_return_session).to_be_disabled()

    back_to_results = page.get_by_role("link", name="Back to articles", exact=True)
    back_to_results_href = back_to_results.get_attribute("href") or ""
    _require(
        back_to_results_href == "/articles?q=CRB",
        f"Article search return context is missing: {back_to_results_href}",
    )
    back_to_results.click()
    expect(page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(page.get_by_placeholder("Search title or keyword")).to_have_value("CRB")
    expect(page.get_by_role("link", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    _require("q=CRB" in page.url, f"Article search URL state was not restored: {page.url}")
    checks["integrated_learning_workflow"] = True

    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible()
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    _require(
        page.get_by_role("link", name=re.compile(r"^Continue learning CRB")).count() == 0,
        "Dashboard Continue still includes a confirmed completed Article",
    )
    continue_href = f"/articles/{CRB_ARTICLE_ID}#{target_section_id}"
    expect(page.get_by_role("heading", name="Learning Activity", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="New in Library", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-activity")).to_contain_text(CRB_TITLE)
    expect(page.get_by_test_id("dashboard-activity")).not_to_contain_text(CRB_ARTICLE_ID)
    checks["dashboard_history"] = True
    checks["dashboard_excludes_completed_continue"] = True

    attention_state_response = context.request.put(
        f"{API_URL}/learning/state/{ATTENTION_ARTICLE_ID}",
        data={"status": "reading"},
    )
    _require(
        attention_state_response.ok,
        f"failed to prepare an in-progress Library fixture: {attention_state_response.status}",
    )
    saved_library_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/library",
    )
    page.get_by_role("link", name="Saved", exact=True).click()
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "library")
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_role("heading", name="Bookmarked", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Recently Read", exact=True)).to_be_visible()
    expect(page.get_by_test_id("saved-library-section-continue")).to_contain_text(ATTENTION_TITLE)
    expect(page.get_by_test_id("saved-library-section-bookmarked")).to_contain_text(CRB_TITLE)
    expect(page.get_by_test_id("saved-library-section-recent")).to_contain_text(CRB_TITLE)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, saved_library_transition)

    attention_library_item = page.get_by_test_id("saved-library-section-continue").locator(
        '[data-testid="saved-library-item"]'
    ).filter(has_text=ATTENTION_TITLE).first
    attention_library_title = attention_library_item.get_by_role(
        "link", name=ATTENTION_TITLE, exact=True
    )
    attention_library_add = attention_library_item.get_by_role(
        "button", name=f"Add {ATTENTION_TITLE} to study session", exact=True
    )
    attention_library_add.focus()
    attention_library_add.press("Enter")
    expect(
        attention_library_item.get_by_role(
            "button", name=f"{ATTENTION_TITLE} is in study session", exact=True
        )
    ).to_be_disabled()
    expect(attention_library_title).to_be_focused()
    _require_visible_focus(attention_library_title, "Saved Learning exact-item capture result")

    page.get_by_role("button", name=re.compile(r"^Saved \(1\)$")).click()
    page.get_by_label("Sort saved learning", exact=True).select_option("progress")
    page.get_by_label("Filter saved learning", exact=True).fill("CRB")
    page.get_by_role("button", name="Filter", exact=True).click()
    expect(page).to_have_url(re.compile(r"/library\?q=CRB&view=bookmarked&sort=progress$"))
    saved_filter = page.get_by_label("Filter saved learning", exact=True)
    saved_clear = page.get_by_role("button", name="Clear", exact=True)
    saved_clear.focus()
    saved_clear.press("Enter")
    expect(saved_filter).to_be_focused()
    _require_visible_focus(saved_filter, "Saved Learning cleared filter")
    saved_filter.fill("CRB")
    page.get_by_role("button", name="Filter", exact=True).click()
    expect(page).to_have_url(re.compile(r"/library\?q=CRB&view=bookmarked&sort=progress$"))
    saved_crb_link = page.get_by_test_id("saved-library-section-bookmarked").get_by_role(
        "link", name=CRB_TITLE, exact=True
    )
    expect(saved_crb_link).to_be_visible()
    saved_crb_href = saved_crb_link.get_attribute("href") or ""
    _require(
        "from=%2Flibrary%3Fq%3DCRB%26view%3Dbookmarked%26sort%3Dprogress" in saved_crb_href
        and "#" in saved_crb_href,
        f"Saved Library Reader destination is incomplete: {saved_crb_href}",
    )
    saved_crb_link.click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    saved_return = page.get_by_role("link", name="Back to saved library", exact=True)
    expect(saved_return).to_have_attribute(
        "href", "/library?q=CRB&view=bookmarked&sort=progress"
    )
    saved_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(saved_reader_session).to_be_enabled(timeout=30_000)
    saved_reader_session.click()
    expect(saved_reader_session).to_be_disabled()
    saved_return.click()
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_label("Filter saved learning", exact=True)).to_have_value("CRB")
    expect(page.get_by_label("Sort saved learning", exact=True)).to_have_value("progress")
    expect(page.get_by_role("button", name=re.compile(r"^Saved \(1\)$"))).to_have_attribute(
        "aria-pressed", "true"
    )
    session_url_before_add = page.url
    saved_crb_item = page.get_by_test_id("saved-library-section-bookmarked").locator(
        '[data-testid="saved-library-item"]'
    ).filter(has_text=CRB_TITLE).first
    saved_crb_title = saved_crb_item.get_by_role("link", name=CRB_TITLE, exact=True)
    saved_crb_add = saved_crb_item.get_by_role(
        "button", name=f"Add {CRB_TITLE} to study session", exact=True
    )
    saved_crb_add.focus()
    saved_crb_add.press("Enter")
    _require(page.url == session_url_before_add, "adding to Session discarded Saved Library URL state")
    expect(page.get_by_role("link", name="Open study session (2)", exact=True)).to_be_visible()
    expect(saved_crb_title).to_be_focused()
    _require_visible_focus(saved_crb_title, "Saved Learning second exact-item capture result")
    page.get_by_role("link", name="Dashboard", exact=True).click()
    dashboard_session = page.get_by_test_id("dashboard-study-session")
    expect(dashboard_session).to_have_attribute("data-state", "ready")
    expect(dashboard_session).to_contain_text("2 Articles")
    expect(dashboard_session).to_contain_text(ATTENTION_TITLE)
    expect(dashboard_session).to_contain_text("1 completed · 1 remaining")
    expect(dashboard_session.get_by_role("link", name="Open session", exact=True)).to_have_attribute(
        "href", "/session"
    )
    expect(page.get_by_role("link", name="Resume focused session", exact=True)).to_be_visible()
    checks["saved_learning_library"] = True

    page.get_by_role("link", name="Resume focused session", exact=True).click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "session")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("2 Articles")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("Completed")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("Remaining")
    expect(page.get_by_test_id("study-session-item").filter(has_text=ATTENTION_TITLE).first).to_contain_text(
        "Current · Reading"
    )
    crb_queue_item = page.get_by_test_id("study-session-item").filter(has_text=CRB_TITLE).first
    move_crb_up = crb_queue_item.get_by_role("button", name=f"Move {CRB_TITLE} up", exact=True)
    move_crb_up.focus()
    move_crb_up.press("Enter")
    crb_queue_title = crb_queue_item.get_by_role("link", name=CRB_TITLE, exact=True)
    expect(crb_queue_title).to_be_focused()
    _require_visible_focus(crb_queue_title, "Focused Session boundary-move result")
    set_crb_current = crb_queue_item.get_by_role(
        "button", name=f"Set {CRB_TITLE} as current", exact=True
    )
    set_crb_current.focus()
    set_crb_current.press("Enter")
    expect(crb_queue_item).to_contain_text("Current · Completed")
    expect(crb_queue_title).to_be_focused()
    _require_visible_focus(crb_queue_title, "Focused Session current-item result")
    page.wait_for_load_state("networkidle")
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )
    _require(not page_errors, f"Study Session state update emitted page errors: {page_errors}")
    page.reload(wait_until="networkidle")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    crb_queue_item = page.get_by_test_id("study-session-item").first
    expect(crb_queue_item).to_contain_text(CRB_TITLE)
    expect(crb_queue_item).to_contain_text("Current · Completed")
    _require(not page_errors, f"Study Session hard reload emitted page errors: {page_errors}")
    page.evaluate(
        """
        () => {
          window.__p3034GuidedReaderEvents = [];
          window.__p3034GuidedReaderFocus = event => {
            if (event.target instanceof Element) {
              window.__p3034GuidedReaderEvents.push({
                kind: 'focus',
                target: event.target.getAttribute('data-testid')
                  || event.target.id
                  || event.target.tagName,
              });
            }
          };
          window.__p3034GuidedReaderCommit = () => {
            window.__p3034GuidedReaderEvents.push({kind: 'route-commit'});
          };
          window.__p3034GuidedReaderOperation = () => {
            window.__p3034GuidedReaderEvents.push({kind: 'focus-operation'});
          };
          document.addEventListener('focusin', window.__p3034GuidedReaderFocus, true);
          window.addEventListener(
            'scientific-spaces:shell-route-commit',
            window.__p3034GuidedReaderCommit,
          );
          window.addEventListener(
            'scientific-spaces:shell-focus-operation',
            window.__p3034GuidedReaderOperation,
          );
        }
        """
    )
    session_reader_link = page.get_by_role(
        "link", name=f"Review current Article: {CRB_TITLE}", exact=True
    )
    session_reader_href = session_reader_link.get_attribute("href") or ""
    session_reader_link.click()
    crb_heading = page.get_by_role("heading", name=CRB_TITLE, exact=True)
    expect(crb_heading).to_be_visible(timeout=30_000)
    try:
        expect(crb_heading).to_be_focused(timeout=30_000)
    except AssertionError as exc:
        guided_reader_diagnostics = page.evaluate(
            """
            () => ({
              active: document.activeElement instanceof Element
                ? document.activeElement.getAttribute('data-testid')
                  || document.activeElement.id
                  || document.activeElement.tagName
                : null,
              events: window.__p3034GuidedReaderEvents,
              owner: document.querySelector('article#article-start')
                ?.getAttribute('data-shell-focus-owner'),
              url: location.href,
            })
            """
        )
        raise AssertionError(
            "guided Reader destination did not claim focus "
            f"for {session_reader_href}: {guided_reader_diagnostics}"
        ) from exc
    page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3034GuidedReaderFocus, true);
          window.removeEventListener(
            'scientific-spaces:shell-route-commit',
            window.__p3034GuidedReaderCommit,
          );
          window.removeEventListener(
            'scientific-spaces:shell-focus-operation',
            window.__p3034GuidedReaderOperation,
          );
        }
        """
    )
    session_reader_navigation = page.get_by_test_id("study-session-reader-navigation")
    expect(session_reader_navigation).to_contain_text("Article 1 of 2")
    expect(session_reader_navigation.get_by_role(
        "link", name=f"Next in session: {ATTENTION_TITLE}", exact=True
    )).to_be_visible()
    completion_region = page.get_by_test_id("focused-session-completion")
    expect(completion_region).to_be_visible()
    completion_status = page.get_by_test_id("focused-session-completion-status")
    expect(completion_status).to_have_attribute("aria-live", "polite")
    expect(completion_status).to_have_attribute("aria-atomic", "true")
    crb_state_before = _api_json(context, "GET", f"/learning/state/{CRB_ARTICLE_ID}")
    mark_complete = completion_region.get_by_role("button", name="Mark Article complete", exact=True)
    expect(mark_complete).to_be_enabled(timeout=30_000)
    _install_mutation_response_gate(
        page,
        f"/learning/state/{CRB_ARTICLE_ID}",
        "GET",
    )
    page.keyboard.press("Tab")
    expect(mark_complete).to_be_focused()
    mark_complete.press("Enter")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    crb_heading.focus()
    _release_mutation_response_gate(page)
    expect(completion_region).to_have_attribute("data-state", "ready-to-advance", timeout=30_000)
    expect(crb_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(crb_heading, "Reader completion newer focus owner")
    _restore_mutation_response_gate(page)
    expect(completion_status).to_contain_text("Article completion is confirmed")
    expect(completion_region.get_by_role("button", name="Article completion confirmed", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="End session", exact=True)).to_be_disabled(timeout=30_000)
    crb_state_after = _api_json(context, "GET", f"/learning/state/{CRB_ARTICLE_ID}")
    _require(
        crb_state_after["read_count"] == crb_state_before["read_count"],
        "confirming an already completed Article duplicated its completion write",
    )
    open_next = completion_region.get_by_role("button", name="Open next unfinished Article", exact=True)
    open_next.focus()
    expect(open_next).to_be_focused()
    open_next_transition = _declare_expected_route_transition(
        page,
        destination_url=(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Fsession"
        ),
    )
    open_next.press("Enter")
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    session_reader_navigation = page.get_by_test_id("study-session-reader-navigation")
    expect(session_reader_navigation).to_contain_text("Article 2 of 2")
    expect(
        session_reader_navigation.get_by_role(
            "link", name=f"Previous in session: {CRB_TITLE}", exact=True
        )
    ).to_be_visible()
    _complete_expected_route_transition(page, open_next_transition)
    persisted_guided_session = page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        persisted_guided_session["active_article_id"] == ATTENTION_ARTICLE_ID,
        f"guided advance did not persist the next active Article: {persisted_guided_session}",
    )
    attention_state_before = _api_json(context, "GET", f"/learning/state/{ATTENTION_ARTICLE_ID}")
    completion_region = page.get_by_test_id("focused-session-completion")
    attention_mark_complete = completion_region.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(attention_mark_complete).to_be_enabled(timeout=30_000)
    completion_region.focus()
    page.keyboard.press("Tab")
    expect(attention_mark_complete).to_be_focused()
    attention_mark_complete.press("Enter")
    expect(completion_region).to_have_attribute("data-state", "ready-to-advance", timeout=30_000)
    expect(completion_region).to_be_focused(timeout=30_000)
    attention_state_after = _api_json(context, "GET", f"/learning/state/{ATTENTION_ARTICLE_ID}")
    _require(
        attention_state_after["status"] == "completed"
        and attention_state_after["read_count"] == attention_state_before["read_count"] + 1,
        f"Attention completion was not persisted exactly once: {attention_state_after}",
    )
    terminal_url = page.url
    terminal_action = completion_region.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    )
    _install_mutation_response_gate(
        page,
        f"/learning/state/{ATTENTION_ARTICLE_ID}",
        "GET",
    )
    page.keyboard.press("Tab")
    expect(terminal_action).to_be_focused()
    terminal_action.press("Enter")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    attention_heading.focus()
    _release_mutation_response_gate(page)
    expect(completion_region).to_have_attribute("data-state", "complete", timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(attention_heading, "Reader terminal advance newer focus owner")
    _restore_mutation_response_gate(page)
    expect(completion_region).to_contain_text("Every queued Article is confirmed complete")
    _require(page.url == terminal_url, "terminal completion navigated without an unfinished Article")
    completion_region.get_by_role("link", name="Review completed session", exact=True).click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("2")
    expect(page.get_by_test_id("study-session-complete")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("study-session-item")).to_have_count(2)
    checks["focused_session_completion_and_guided_advance"] = True
    checks["focused_session_duplicate_safe_completion"] = True
    checks["focused_session_retained_terminal_queue"] = True

    page.get_by_role("link", name="Dashboard", exact=True).click()
    dashboard_session = page.get_by_test_id("dashboard-study-session")
    expect(dashboard_session).to_contain_text("2 completed · 0 remaining", timeout=30_000)
    expect(dashboard_session).to_contain_text("Session complete")
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    dashboard_session.get_by_role("link", name="Review completed session", exact=True).click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    crb_queue_item = page.get_by_test_id("study-session-item").filter(has_text=CRB_TITLE).first
    remove_crb = crb_queue_item.get_by_role(
        "button", name=f"Remove {CRB_TITLE} from session", exact=True
    )
    remove_crb.focus()
    remove_crb.press("Enter")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("1 Article")
    surviving_attention = page.get_by_test_id("study-session-item").get_by_role(
        "link", name=ATTENTION_TITLE, exact=True
    )
    expect(surviving_attention).to_be_focused()
    _require_visible_focus(surviving_attention, "Focused Session removal result")
    clear_queue = page.get_by_role("button", name="Clear queue", exact=True)
    clear_queue.focus()
    clear_queue.press("Enter")
    confirm_clear = page.get_by_role("button", name="Confirm clear queue", exact=True)
    expect(confirm_clear).to_be_focused()
    _require_visible_focus(confirm_clear, "Focused Session clear confirmation")
    cancel_clear = page.get_by_role("button", name="Cancel", exact=True)
    cancel_clear.focus()
    cancel_clear.press("Enter")
    clear_queue = page.get_by_role("button", name="Clear queue", exact=True)
    expect(clear_queue).to_be_focused()
    _require_visible_focus(clear_queue, "Focused Session cancelled clear")
    clear_queue.press("Enter")
    confirm_clear = page.get_by_role("button", name="Confirm clear queue", exact=True)
    expect(confirm_clear).to_be_focused()
    confirm_clear.press("Enter")
    expect(page.get_by_test_id("study-session-empty")).to_be_visible()
    empty_recovery = page.get_by_role("link", name="Browse saved learning", exact=True)
    expect(empty_recovery).to_be_focused()
    _require_visible_focus(empty_recovery, "Focused Session cleared-queue recovery")
    checks["focused_study_session_workflow"] = True

    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    checks["dashboard_focused_session"] = True
    page.goto(f"{FRONTEND_URL}{continue_href}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    page.wait_for_function("() => window.scrollY > 0")
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-size", "large")
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-width", "wide")
    expect(page.get_by_test_id("article-outline").locator('[aria-current="location"]')).to_be_visible()
    resumed_end_session = page.get_by_role("button", name="End session", exact=True)
    expect(resumed_end_session).to_be_enabled(timeout=30_000)
    resumed_end_session.click()
    expect(resumed_end_session).to_be_disabled()
    checks["continue_reading_resume"] = True

    primary_graph_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/graph",
    )
    page.get_by_role("link", name="Graph", exact=True).click()
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    expect(page.get_by_text(re.compile(r"^Showing \d+-\d+ of \d+$"))).to_be_visible(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, primary_graph_transition)

    graph_pagination_pattern = re.compile(r".*/v1\.1/graph/nodes\?.*")

    def provide_graph_pagination(route) -> None:
        query = parse_qs(urlparse(route.request.url).query)
        if query.get("q", [""])[0] != "p3-036-pagination":
            route.continue_()
            return
        requested_page = int(query.get("page", ["1"])[0])
        first_index = (requested_page - 1) * 20
        remaining = max(0, 41 - first_index)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [
                        {
                            "node_id": f"concept:p3-036-{first_index + offset + 1}",
                            "node_type": "concept",
                            "label": f"P3-036 Graph page {requested_page} result {offset + 1}",
                            "source_id": None,
                            "source_url": None,
                            "metadata": {},
                        }
                        for offset in range(min(20, remaining))
                    ],
                    "total": 41,
                    "page": requested_page,
                    "page_size": 20,
                    "pages": 3,
                },
                ensure_ascii=False,
            ),
        )

    page.route(graph_pagination_pattern, provide_graph_pagination)
    graph_search = page.get_by_placeholder("Title, concept, or formula")
    graph_search.fill("p3-036-pagination")
    graph_apply = page.get_by_role("button", name="Apply", exact=True)
    graph_apply.focus()
    graph_apply.press("Enter")
    graph_results_heading = page.get_by_role("heading", name="Nodes", exact=True)
    expect(page.get_by_text("Showing 1-20 of 41", exact=True)).to_be_visible(timeout=30_000)
    expect(graph_results_heading).to_be_focused()
    _require_visible_focus(graph_results_heading, "Graph Apply result heading")
    graph_next = page.get_by_role("button", name="Next", exact=True)
    graph_next.focus()
    graph_next.press("Enter")
    expect(page.get_by_text("Showing 21-40 of 41", exact=True)).to_be_visible(timeout=30_000)
    expect(graph_results_heading).to_be_focused()
    _require_visible_focus(graph_results_heading, "Graph Next-page result heading")
    graph_previous = page.get_by_role("button", name="Previous", exact=True)
    graph_previous.focus()
    graph_previous.press("Enter")
    expect(page.get_by_text("Showing 1-20 of 41", exact=True)).to_be_visible(timeout=30_000)
    expect(graph_results_heading).to_be_focused()
    _require_visible_focus(graph_results_heading, "Graph Previous-page result heading")
    graph_clear = page.get_by_role("button", name="Clear", exact=True)
    graph_clear.focus()
    graph_clear.press("Enter")
    expect(graph_search).to_be_focused()
    _require_visible_focus(graph_search, "Graph cleared search")
    page.unroute(graph_pagination_pattern, provide_graph_pagination)

    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.locator('select[name="node_type"]').select_option("concept")
    page.get_by_role("button", name="Apply", exact=True).click()
    expect(page.get_by_text(re.compile(r"^Showing 1-\d+ of \d+$"))).to_be_visible(timeout=30_000)
    expect(graph_results_heading).to_be_focused()
    _require_visible_focus(graph_results_heading, "Graph filtered result heading")
    graph_node = (
        page.get_by_test_id("graph-node-results")
        .locator("button")
        .filter(has_text=re.compile(r"^Attention", re.I))
        .first
    )
    expect(graph_node).to_be_visible()
    graph_node.click()
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
    concept_study_set = page.get_by_test_id("concept-study-set")
    expect(concept_study_set).to_have_attribute("data-state", "ready")
    expect(concept_study_set.get_by_role("heading", name="Concept Study Set", exact=True)).to_be_visible()
    expect(concept_study_set).to_contain_text("not a complete or recommended learning sequence")
    expect(concept_study_set.get_by_test_id("concept-study-article")).to_have_count(1)
    expect(concept_study_set.get_by_test_id("concept-study-article").first).to_contain_text(
        ATTENTION_TITLE
    )
    for fact_label in ("Source records", "Returned", "Eligible", "Duplicates", "Invalid", "Omitted"):
        expect(concept_study_set.locator("dt").filter(has_text=fact_label)).to_be_visible()
    _require(
        ATTENTION_CONCEPT_ID not in concept_study_set.inner_text(),
        "Concept Study Set exposes a raw Graph node identifier",
    )
    concept_study_set.get_by_role("button", name="Go to Knowledge Context", exact=True).click()
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    expect(
        page.get_by_role("group", name="Graph workspace view").get_by_role(
            "button", name="Knowledge context", exact=True
        )
    ).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name="Inspect selected", exact=True).click()
    expect(page.get_by_test_id("concept-study-set")).to_be_visible()
    checks["graph_context_mode_and_inspect_selected"] = True

    concept_article_link = concept_study_set.get_by_role(
        "link", name=ATTENTION_TITLE, exact=True
    )
    expect(concept_article_link).to_have_attribute(
        "href",
        f"/articles/{ATTENTION_ARTICLE_ID}?"
        + urlencode({"from": ATTENTION_CONCEPT_QUERY_RETURN}),
    )
    page.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-023-isolated-concept-reader",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-08-31T04:00:00+00:00",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    _focus_via_tab(page, concept_article_link)
    concept_article_href = str(concept_article_link.get_attribute("href") or "")
    concept_article_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{concept_article_href}",
    )
    concept_article_link.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=concept_article_href,
        timeout=30_000,
    )
    concept_reader_heading = page.locator("article#article-start > h1")
    expect(concept_reader_heading).to_have_text(ATTENTION_TITLE, timeout=30_000)
    expect(concept_reader_heading).to_be_focused()
    _require_visible_focus(concept_reader_heading, "Concept Study Set Reader heading")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, concept_article_transition)
    reader_concept_return = page.get_by_role("link", name="Back to concept", exact=True).first
    expect(reader_concept_return).to_have_attribute("href", ATTENTION_CONCEPT_QUERY_RETURN)
    _focus_via_tab(page, reader_concept_return)
    reader_concept_return_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{ATTENTION_CONCEPT_QUERY_RETURN}",
    )
    reader_concept_return.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=ATTENTION_CONCEPT_QUERY_RETURN,
        timeout=30_000,
    )
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    returned_concept_study_set = page.get_by_test_id("concept-study-set")
    expect(returned_concept_study_set).to_be_visible(timeout=30_000)
    returned_concept_article_link = returned_concept_study_set.get_by_role(
        "link", name=ATTENTION_TITLE, exact=True
    )
    expect(returned_concept_article_link).to_be_focused(timeout=30_000)
    _require_visible_focus(
        returned_concept_article_link,
        "returned Concept Study Set Article action",
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, reader_concept_return_transition)

    concept_ask_payloads: list[dict[str, object]] = []

    def fulfill_concept_explain(route) -> None:
        concept_ask_payloads.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "answer": "## Attention\n\nLocal Article evidence explains the selected Concept.",
                    "mode": "explain",
                    "sources": [
                        {
                            "source_type": "article_chunk",
                            "source_id": f"{ATTENTION_ARTICLE_ID}:0",
                            "title": ATTENTION_TITLE,
                            "url": "https://spaces.ac.cn/archives/12345",
                            "section_title": "Attention",
                            "chunk_index": 0,
                            "evidence": None,
                            "metadata": {"article_id": ATTENTION_ARTICLE_ID},
                        }
                    ],
                    "graph_context": {"nodes": [], "edges": []},
                    "zotero_context": [],
                    "follow_up_questions": [],
                    "refusal_reason": None,
                    "selection_summary": None,
                    "evidence_summary": None,
                },
                ensure_ascii=False,
            ),
        )

    page.route(re.compile(r".*/tutor/ask$"), fulfill_concept_explain, times=1)
    concept_explain_link = page.get_by_test_id("concept-study-set").get_by_role(
        "link", name="Explain concept", exact=True
    )
    _focus_via_tab(page, concept_explain_link)
    concept_explain_href = str(concept_explain_link.get_attribute("href") or "")
    concept_explain_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{concept_explain_href}",
    )
    concept_explain_link.press("Enter")
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(page.get_by_test_id("concept-learning-context")).to_contain_text("attention")
    expect(page.get_by_role("button", name="Explain", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.get_by_label("Question")).to_have_value(
        "Explain attention using intuition, mathematics, and cited local evidence."
    )
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(ATTENTION_TITLE)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, concept_explain_transition)
    concept_return = page.get_by_role("link", name="Return to concept", exact=True)
    expect(concept_return).to_have_attribute("href", ATTENTION_CONCEPT_RETURN)
    _require(not concept_ask_payloads, "Concept Explain auto-submitted before user action")
    page.get_by_role("button", name="Quiz", exact=True).click()
    expect(page.get_by_test_id("concept-learning-context")).to_contain_text(
        "Quiz uses the selected local Article and concept topic."
    )
    expect(page.get_by_text("Concept topic", exact=True)).to_be_visible()
    page.get_by_role("button", name="Explain", exact=True).click()
    expect(page.get_by_test_id("concept-learning-context")).to_contain_text(
        "Graph context supplements the selected local Article evidence."
    )
    concept_submit = page.get_by_role("button", name="Ask tutor", exact=True)
    _focus_via_tab(page, concept_submit)
    concept_submit.press("Enter")
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    _require(
        concept_ask_payloads
        == [
            {
                "question": "Explain attention using intuition, mathematics, and cited local evidence.",
                "mode": "explain",
                "article_id": ATTENTION_ARTICLE_ID,
                "node_id": ATTENTION_CONCEPT_ID,
                "top_k": 5,
                "include_graph_context": True,
                "include_zotero_context": True,
            }
        ],
        f"Concept Explain payload is incorrect: {concept_ask_payloads}",
    )
    _focus_via_tab(page, concept_return)
    concept_explain_return_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}",
    )
    concept_return.press("Enter")
    expect(page.get_by_test_id("concept-study-set")).to_be_visible(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, concept_explain_return_transition)

    concept_quiz_payloads: list[dict[str, object]] = []

    def fulfill_concept_quiz(route) -> None:
        concept_quiz_payloads.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "questions": [
                        {
                            "question": "What does Attention select?",
                            "options": ["Relevant local evidence", "Unbounded external data"],
                            "correct_answer": "Relevant local evidence",
                            "explanation": "The local Article describes evidence-weighted selection.",
                            "sources": [
                                {
                                    "source_type": "article_chunk",
                                    "source_id": f"{ATTENTION_ARTICLE_ID}:0",
                                    "title": ATTENTION_TITLE,
                                    "url": "https://spaces.ac.cn/archives/12345",
                                    "section_title": "Attention",
                                    "chunk_index": 0,
                                    "evidence": None,
                                    "metadata": {"article_id": ATTENTION_ARTICLE_ID},
                                }
                            ],
                        }
                    ],
                    "total": 1,
                },
                ensure_ascii=False,
            ),
        )

    page.route(re.compile(r".*/tutor/quiz$"), fulfill_concept_quiz, times=1)
    concept_quiz_link = page.get_by_test_id("concept-study-set").get_by_role(
        "link", name="Open concept quiz", exact=True
    )
    _focus_via_tab(page, concept_quiz_link)
    concept_quiz_href = str(concept_quiz_link.get_attribute("href") or "")
    concept_quiz_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{concept_quiz_href}",
    )
    concept_quiz_link.press("Enter")
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Quiz", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.get_by_label("Prompt")).to_have_value("attention")
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(ATTENTION_TITLE)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, concept_quiz_transition)
    concept_return = page.get_by_role("link", name="Return to concept", exact=True)
    expect(concept_return).to_have_attribute("href", ATTENTION_CONCEPT_RETURN)
    _require(not concept_quiz_payloads, "Concept Quiz auto-submitted before user action")
    concept_quiz_submit = page.get_by_role("button", name="Generate quiz", exact=True)
    _focus_via_tab(page, concept_quiz_submit)
    concept_quiz_submit.press("Enter")
    expect(page.get_by_role("heading", name="Quiz", exact=True)).to_be_visible(timeout=30_000)
    _require(
        concept_quiz_payloads
        == [
            {
                "article_id": ATTENTION_ARTICLE_ID,
                "node_id": ATTENTION_CONCEPT_ID,
                "num_questions": 3,
                "topic": "attention",
            }
        ],
        f"Concept Quiz payload is incorrect: {concept_quiz_payloads}",
    )
    _focus_via_tab(page, concept_return)
    concept_quiz_return_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}",
    )
    concept_return.press("Enter")
    expect(page.get_by_test_id("concept-study-set")).to_be_visible(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, concept_quiz_return_transition)

    page.evaluate(
        """
        () => {
          window.__p3023SessionWrites = 0;
          const originalSetItem = Storage.prototype.setItem;
          Storage.prototype.setItem = function (key, value) {
            if (key === "scientific-spaces-study-session-v1") {
              window.__p3023SessionWrites += 1;
            }
            return originalSetItem.call(this, key, value);
          };
        }
        """
    )
    study_set = page.get_by_test_id("concept-study-set")
    bulk_add = study_set.get_by_role("button", name="Add eligible Articles", exact=True)
    _focus_via_tab(page, bulk_add)
    bulk_add.press("Enter")
    concept_session_status = study_set.get_by_test_id("concept-study-session-status")
    expect(concept_session_status).to_contain_text(
        "1 added; 0 already present; 0 invalid; 0 omitted by capacity."
    )
    expect(concept_session_status).to_be_focused()
    _require_visible_focus(concept_session_status, "Concept Study Set capture result")
    _require(
        page.evaluate("window.__p3023SessionWrites") == 1,
        "Concept Study Set bulk append did not use exactly one storage write",
    )
    persisted_concept_session = page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        [item["article_id"] for item in persisted_concept_session["items"]]
        == [ATTENTION_ARTICLE_ID]
        and persisted_concept_session["active_article_id"] == ATTENTION_ARTICLE_ID,
        f"Concept Study Set saved the wrong Session state: {persisted_concept_session}",
    )
    bulk_add.press("Enter")
    expect(concept_session_status).to_contain_text(
        "0 added; 1 already present; 0 invalid; 0 omitted by capacity."
    )
    expect(concept_session_status).to_be_focused()
    _require_visible_focus(concept_session_status, "Concept Study Set duplicate result")
    _require(
        page.evaluate("window.__p3023SessionWrites") == 1,
        "idempotent Concept Study Set append performed an extra storage write",
    )
    page.evaluate(
        """
        () => {
          localStorage.removeItem("scientific-spaces-study-session-v1");
          window.dispatchEvent(new Event("scientific-spaces-study-session-change"));
        }
        """
    )
    checks["concept_study_set_workflow"] = True
    checks["concept_reader_and_tutor_round_trip"] = True
    checks["concept_tutor_explicit_payloads"] = True
    checks["concept_study_set_session_append"] = True
    checks["concept_study_set_keyboard_focus"] = True

    concept_graph_return = page.evaluate(
        """
        () => {
          const source = new URLSearchParams(location.search);
          const target = new URLSearchParams();
          const nodeId = source.get("node_id");
          const query = source.get("q");
          if (nodeId) target.set("node_id", nodeId);
          if (query) target.set("q", query);
          return `/graph?${target.toString()}`;
        }
        """
    )
    provenance_article_links = page.get_by_role("link", name="Open article", exact=True)
    _require(
        provenance_article_links.count() > 0,
        "Concept provenance did not expose an Article link",
    )
    for index in range(provenance_article_links.count()):
        provenance_href = provenance_article_links.nth(index).get_attribute("href") or ""
        provenance_from = parse_qs(urlparse(provenance_href).query).get("from", [])
        _require(
            provenance_from == [concept_graph_return],
            f"Concept provenance Article link lost Graph context: {provenance_href}",
        )
    provenance_article_link = provenance_article_links.first
    provenance_article_href = str(provenance_article_link.get_attribute("href") or "")
    _focus_via_tab(page, provenance_article_link)
    provenance_article_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{provenance_article_href}",
    )
    provenance_article_link.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=provenance_article_href,
        timeout=30_000,
    )
    provenance_reader = page.locator("article#article-start")
    provenance_reader_heading = provenance_reader.locator(":scope > h1")
    expect(provenance_reader_heading).to_be_visible(timeout=30_000)
    expect(provenance_reader_heading).to_be_focused()
    _require_visible_focus(provenance_reader_heading, "provenance-origin Reader heading")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, provenance_article_transition)
    provenance_return = page.get_by_role("link", name="Back to concept", exact=True).first
    expect(provenance_return).to_have_attribute("href", concept_graph_return)
    provenance_session = page.get_by_role("button", name="End session", exact=True)
    expect(provenance_session).to_be_enabled(timeout=30_000)
    provenance_session.click()
    expect(provenance_session).to_be_disabled()
    _focus_via_tab(page, provenance_return)
    provenance_return_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{concept_graph_return}",
    )
    provenance_return.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=concept_graph_return,
        timeout=30_000,
    )
    returned_provenance_link = page.locator(
        '[data-graph-article-focus="provenance-0"]'
    )
    expect(returned_provenance_link).to_be_focused(timeout=30_000)
    _require_visible_focus(returned_provenance_link, "returned provenance Article action")
    checks["graph_provenance_article_return_context"] = True
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, provenance_return_transition)

    page.evaluate(
        """
        ([key, value]) => sessionStorage.setItem(key, JSON.stringify(value))
        """,
        [
            "scientific-spaces:graph-article-return-focus:v1",
            {
                "articleId": ATTENTION_ARTICLE_ID,
                "focusTarget": "provenance-9",
                "returnTo": concept_graph_return,
            },
        ],
    )
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    missing_origin_region = page.get_by_test_id("graph-selected-region")
    expect(missing_origin_region).to_be_visible(timeout=30_000)
    expect(missing_origin_region).to_be_focused(timeout=30_000)
    _require_visible_focus(missing_origin_region, "missing provenance origin fallback")
    checks["graph_missing_exact_origin_focus_fallback"] = True

    page.get_by_role("group", name="Graph workspace view").get_by_role(
        "button", name="Knowledge context", exact=True
    ).click()
    concept_context_region = page.locator("#graph-context-workspace")
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("graph-map-counts")).to_contain_text("relationships")
    graph_edge = page.locator('.react-flow__edge[tabindex="0"]').first
    expect(graph_edge).to_be_visible(timeout=30_000)
    graph_edge.focus()
    expect(graph_edge).to_be_focused()
    graph_edge.press("Control+k")
    svg_opener_search = page.get_by_test_id("global-search-dialog")
    expect(svg_opener_search.get_by_label("Search library")).to_be_focused()
    svg_opener_search.get_by_label("Search library").press("Escape")
    expect(svg_opener_search).to_have_count(0)
    expect(graph_edge).to_be_focused()
    checks["shell_svg_opener_focus_restoration"] = True
    graph_article_node = page.get_by_role("button", name=re.compile(r"^Article: ")).first
    expect(graph_article_node).to_be_visible()
    _wait_for_page_requests_to_settle(page, console_errors)
    attention_graph_read_urls = (
        f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention",
        (
            f"{BROWSER_API_URL}/v1.1/graph/subgraph?node_id=concept%3Aattention"
            "&depth=1&node_limit=25&edge_limit=50"
        ),
    )
    graph_article_selection = _declare_expected_route_transition(
        page,
        destination_url=(
            f"{FRONTEND_URL}/graph?node_id=article%3A{ATTENTION_ARTICLE_ID}"
        ),
    )
    graph_article_node.press("Enter")
    page.wait_for_function("() => new URL(location.href).searchParams.get('node_id')?.startsWith('article:')")
    _require_visible_focus(concept_context_region, "desktop Context region after map selection")
    expect(page.get_by_role("button", name=re.compile(r"^Selected Article: ")).first).to_be_visible(
        timeout=30_000
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_article_selection)
    expect(
        page.get_by_role("group", name="Graph workspace view").get_by_role(
            "button", name="Knowledge context", exact=True
        )
    ).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name="Inspect selected", exact=True).click()
    graph_article_link = page.get_by_role("link", name="Open article").first
    expect(graph_article_link).to_be_visible()
    graph_article_return = page.evaluate(
        """
        () => {
          const source = new URLSearchParams(location.search);
          const target = new URLSearchParams();
          const nodeId = source.get("node_id");
          const query = source.get("q");
          if (nodeId) target.set("node_id", nodeId);
          if (query) target.set("q", query);
          return target.size ? `/graph?${target.toString()}` : "/graph";
        }
        """
    )
    graph_article_href = str(graph_article_link.get_attribute("href") or "")
    parsed_graph_article_href = urlparse(graph_article_href)
    _require(
        parsed_graph_article_href.path.startswith("/articles/")
        and parse_qs(parsed_graph_article_href.query).get("from") == [graph_article_return],
        "Graph Article deep link is invalid",
    )
    graph_browser_origin = page.evaluate("location.pathname + location.search")
    graph_history_before_article = page.evaluate("history.length")
    graph_article_link.focus()
    expect(graph_article_link).to_be_focused()
    graph_reader_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{graph_article_href}",
    )
    graph_article_link.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_href,
        timeout=30_000,
    )
    graph_reader = page.locator("article#article-start")
    graph_reader_heading = graph_reader.locator(":scope > h1")
    expect(graph_reader_heading).to_be_visible(timeout=30_000)
    expect(graph_reader_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(graph_reader_heading, "Graph-origin Reader heading")
    _require(
        page.evaluate("history.length") == graph_history_before_article + 1,
        "Graph Article navigation did not create exactly one history entry",
    )
    expect(page.get_by_role("status").filter(has_text="Loading article")).to_have_count(0)
    graph_reader_return = page.get_by_role("link", name="Return to graph", exact=True)
    expect(graph_reader_return).to_have_attribute("href", graph_article_return)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_reader_transition)
    graph_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(graph_reader_session).to_be_enabled(timeout=30_000)
    graph_reader_session.click()
    expect(graph_reader_session).to_be_disabled()
    graph_reader_back_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{graph_browser_origin}",
        cancelled_read_urls=attention_graph_read_urls,
    )
    page.go_back()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_browser_origin,
        timeout=30_000,
    )
    browser_back_article_link = page.locator(
        '[data-graph-article-focus="selected-node"]'
    )
    expect(browser_back_article_link).to_be_focused(timeout=30_000)
    _require_visible_focus(browser_back_article_link, "browser-Back Graph Article action")
    _require(
        page.evaluate("history.length") == graph_history_before_article + 1,
        "browser Back changed Graph-Reader history length",
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_reader_back_transition)
    graph_reader_forward_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{graph_article_href}",
    )
    page.go_forward()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_href,
        timeout=30_000,
    )
    forward_reader_heading = page.locator("article#article-start > h1")
    expect(forward_reader_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(forward_reader_heading, "browser-Forward Reader heading")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_reader_forward_transition)
    forward_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(forward_reader_session).to_be_enabled(timeout=30_000)
    forward_reader_session.click()
    expect(forward_reader_session).to_be_disabled()
    repeated_graph_back_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{graph_browser_origin}",
        cancelled_read_urls=attention_graph_read_urls,
    )
    page.go_back()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_browser_origin,
        timeout=30_000,
    )
    repeated_back_article_link = page.locator(
        '[data-graph-article-focus="selected-node"]'
    )
    expect(repeated_back_article_link).to_be_focused(timeout=30_000)
    _require_visible_focus(repeated_back_article_link, "repeated browser-Back Graph Article action")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, repeated_graph_back_transition)
    repeated_graph_forward_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{graph_article_href}",
    )
    page.go_forward()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_href,
        timeout=30_000,
    )
    repeated_forward_heading = page.locator("article#article-start > h1")
    expect(repeated_forward_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(repeated_forward_heading, "repeated browser-Forward Reader heading")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, repeated_graph_forward_transition)
    repeated_forward_session = page.get_by_role("button", name="End session", exact=True)
    expect(repeated_forward_session).to_be_enabled(timeout=30_000)
    repeated_forward_session.click()
    expect(repeated_forward_session).to_be_disabled()
    graph_reader_reload_transition = _declare_expected_route_transition(
        page,
        destination_url=page.url,
        allow_speculative_cancellations=True,
    )
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.locator("article#article-start > h1")).to_be_visible(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_reader_reload_transition)
    graph_reader_return = page.get_by_role("link", name="Return to graph", exact=True)
    expect(graph_reader_return).to_have_attribute("href", graph_article_return)
    graph_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(graph_reader_session).to_be_enabled(timeout=30_000)
    graph_reader_session.click()
    expect(graph_reader_session).to_be_disabled()
    _install_mutation_response_gate(page, "/graph/nodes/", "GET")
    graph_reader_return.focus()
    expect(graph_reader_return).to_be_focused()
    _start_zotero_focus_trace(page)
    graph_reader_return_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{graph_article_return}",
    )
    graph_reader_return.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_return,
        timeout=30_000,
    )
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    returned_graph_search = page.get_by_placeholder("Title, concept, or formula")
    returned_graph_search.focus()
    _release_mutation_response_gate(page)
    returned_graph_article_link = page.locator(
        '[data-graph-article-focus="selected-node"]'
    )
    expect(returned_graph_article_link).to_be_visible(timeout=30_000)
    expect(returned_graph_search).to_be_focused(timeout=30_000)
    _require_visible_focus(returned_graph_search, "newer Graph search focus owner")
    _assert_zotero_focus_continuity(
        page,
        "deferred Graph return owner",
        ("input:",),
        ("A",),
    )
    _restore_mutation_response_gate(page)
    checks["graph_reader_exact_round_trip"] = True
    checks["graph_reader_keyboard_focus"] = True
    checks["graph_reader_reload_return"] = True
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_reader_return_transition)
    page.get_by_role("group", name="Graph workspace view").get_by_role(
        "button", name="Knowledge context", exact=True
    ).click()
    page.get_by_test_id("graph-view-list").click()
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    list_selection_url = page.url
    related_context_node = page.get_by_test_id("graph-context-list").locator("button").first
    expect(related_context_node).to_be_visible(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    graph_related_selection = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/graph?node_id=concept%3Aattention",
    )
    _install_mutation_response_gate(page, "/v1.1/graph/subgraph", "GET")
    page.evaluate(
        """
        () => {
          const related = document.querySelector('[data-testid="graph-context-list"] button');
          const map = document.querySelector('[data-testid="graph-view-map"]');
          if (!(related instanceof HTMLButtonElement) || !(map instanceof HTMLButtonElement)) {
            throw new Error("Graph context focus-race controls are unavailable");
          }
          related.click();
          map.focus();
        }
        """
    )
    context_map_focus_owner = page.get_by_test_id("graph-view-map")
    expect(context_map_focus_owner).to_be_focused()
    _require_visible_focus(context_map_focus_owner, "initial Graph context focus owner")
    page.wait_for_function("previous => location.href !== previous", arg=list_selection_url)
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    _release_mutation_response_gate(page)
    expect(
        page.get_by_role("group", name="Graph workspace view").get_by_role(
            "button", name="Knowledge context", exact=True
        )
    ).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(context_map_focus_owner).to_be_focused()
    _require_visible_focus(context_map_focus_owner, "newer Graph context focus owner")
    _restore_mutation_response_gate(page)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_related_selection)
    page.get_by_test_id("graph-view-map").click()
    expect(page.get_by_test_id("graph-visualization")).to_be_visible()
    page.wait_for_load_state("networkidle")
    checks["knowledge_graph"] = True
    checks["visual_knowledge_explorer"] = True

    graph_tutor_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/tutor",
    )
    page.get_by_role("link", name="Tutor", exact=True).click()
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_tutor_transition)
    _install_tutor_article_search_delays(page)
    _set_tutor_article_search_delays(page, {"CRB": 700})
    tutor_article_search = page.get_by_label("Search articles")
    tutor_article_search.fill("CRB")
    tutor_search_submit = page.get_by_role("button", name="Search library", exact=True)
    tutor_search_submit.focus()
    tutor_search_submit.press("Enter")
    expect(page.get_by_role("button", name="Searching...", exact=True)).to_be_visible()
    tutor_question_focus_owner = page.get_by_label("Question")
    tutor_question_focus_owner.click()
    tutor_crb_result = page.get_by_role("button", name=f"Select {CRB_TITLE}", exact=True)
    expect(tutor_crb_result).to_be_visible(timeout=30_000)
    expect(tutor_question_focus_owner).to_be_focused()
    _require_visible_focus(tutor_question_focus_owner, "newer Tutor question focus owner")
    _set_tutor_article_search_delays(page, {})
    tutor_article_search.fill("CRB")
    tutor_search_submit = page.get_by_role("button", name="Search library", exact=True)
    tutor_search_submit.focus()
    tutor_search_submit.press("Enter")
    expect(tutor_crb_result).to_be_focused(timeout=30_000)
    _require_visible_focus(tutor_crb_result, "Tutor Article search result")
    tutor_crb_result.press("Enter")
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(CRB_TITLE)
    _require(page.get_by_label("Article ID").count() == 0, "Tutor primary flow exposes Article ID")
    clear_tutor_context = page.get_by_role("button", name="Clear article context", exact=True)
    clear_tutor_context.focus()
    clear_tutor_context.press("Enter")
    expect(tutor_article_search).to_be_focused()
    _require_visible_focus(tutor_article_search, "Tutor cleared Article context")

    _set_tutor_article_search_delays(page, {"CRB": 800, "Attention": 80})
    tutor_article_search.fill("CRB")
    tutor_search_submit = page.get_by_role("button", name="Search library", exact=True)
    tutor_search_submit.focus()
    tutor_search_submit.press("Enter")
    expect(page.get_by_role("button", name="Searching...", exact=True)).to_be_visible()
    tutor_article_search.fill("Attention")
    page.evaluate(
        """
        () => document.querySelector('input[aria-label="Search articles"]')
          ?.closest('form')
          ?.dispatchEvent(new SubmitEvent('submit', { bubbles: true, cancelable: true }))
        """
    )
    tutor_attention_result = page.get_by_role(
        "button", name=f"Select {ATTENTION_TITLE}", exact=True
    )
    expect(tutor_attention_result).to_be_focused(timeout=30_000)
    page.wait_for_timeout(1_000)
    expect(tutor_attention_result).to_be_focused()
    expect(tutor_crb_result).to_have_count(0)

    _set_tutor_article_search_delays(page, {})
    tutor_article_search.fill("CRB")
    tutor_search_submit = page.get_by_role("button", name="Search library", exact=True)
    tutor_search_submit.focus()
    tutor_search_submit.press("Enter")
    tutor_crb_result = page.get_by_role("button", name=f"Select {CRB_TITLE}", exact=True)
    expect(tutor_crb_result).to_be_focused(timeout=30_000)
    _restore_tutor_article_search_delays(page)
    tutor_crb_result.focus()
    tutor_crb_result.press("Enter")
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(CRB_TITLE)
    checks["tutor_article_search_newer_focus_owner"] = True
    checks["tutor_article_search_stale_response_guard"] = True

    markdown_response = {
        "answer": (
            "## Core idea\n\n"
            "**Fisher information** controls the local variance scale $I(\\theta)$.\n\n"
            "$$\\operatorname{Var}(\\hat\\theta) \\ge I(\\theta)^{-1}$$\n\n"
            "```python\nbound = 1 / fisher_information\n```"
        ),
        "mode": "explain",
        "sources": [
            {
                "source_type": "article_chunk",
                "source_id": f"{CRB_ARTICLE_ID}:0",
                "title": CRB_TITLE,
                "url": "https://spaces.ac.cn/archives/6508",
                "section_title": "推导步骤",
                "chunk_index": 0,
                "evidence": None,
                "metadata": {"article_id": CRB_ARTICLE_ID},
            }
        ],
        "graph_context": {"nodes": [], "edges": []},
        "zotero_context": [],
        "follow_up_questions": ["How is the lower bound derived?"],
        "refusal_reason": None,
        "selection_summary": {
            "candidate_count": 1,
            "selected_article_count": 1,
            "selected_chunk_count": 1,
            "graph_node_count": 0,
            "graph_edge_count": 0,
            "graph_latency_ms": None,
            "graph_error_code": None,
            "context_character_count": 320,
            "estimated_token_count": 80,
            "truncated": False,
            "supplement_omitted_count": 0,
        },
        "evidence_summary": {
            "source_count": 1,
            "article_count": 1,
            "has_formula_evidence": True,
            "has_definition_evidence": True,
            "has_answerable_evidence": True,
            "source_schema_valid": True,
            "unsupported_or_out_of_scope": False,
            "refusal_reason": None,
        },
    }
    tutor_workflow_query = urlencode(
        {
            "article_id": CRB_ARTICLE_ID,
            "article_title": CRB_TITLE,
            "return_to": f"/articles/{CRB_ARTICLE_ID}",
        }
    )
    stale_markdown_response = {
        **markdown_response,
        "answer": "P3-027 stale Article response must never be displayed.",
    }
    stale_activity_posts: list[str] = []

    def track_stale_activity(request) -> None:
        if request.method == "POST" and urlparse(request.url).path == "/tutor/sessions":
            stale_activity_posts.append(request.url)

    page.on("request", track_stale_activity)
    _install_fetch_response_gate(page, "/tutor/ask")
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(stale_markdown_response, ensure_ascii=False),
        ),
        times=1,
    )
    page.get_by_label("Question").fill("Stale Article request that must not publish")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_test_id("tutor-request-status")).to_have_text(
        "Tutor request in progress."
    )
    page.get_by_label("Search articles").fill("Attention")
    page.get_by_role("button", name="Search library", exact=True).click()
    page.get_by_role("button", name=f"Select {ATTENTION_TITLE}", exact=True).click()
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(ATTENTION_TITLE)
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    _release_fetch_response_gate(page)
    _require(
        page.get_by_test_id("tutor-result").count() == 0
        and page.get_by_text("P3-027 stale Article response must never be displayed.").count() == 0,
        "stale Tutor response published after the selected Article changed",
    )
    _require(
        not stale_activity_posts,
        f"stale Tutor response wrote recent activity: {stale_activity_posts}",
    )
    _restore_fetch_response_gate(page)
    page.get_by_label("Search articles").fill("CRB")
    page.get_by_role("button", name="Search library", exact=True).click()
    page.get_by_role("button", name=f"Select {CRB_TITLE}", exact=True).click()
    page.get_by_label("Question").fill("什么是 CRB 和 Fisher 信息下界？")
    checks["tutor_article_request_and_activity_ownership"] = True

    page.get_by_text("Advanced context", exact=True).click()
    page.get_by_label("Graph concept key").fill("concept:crb")
    stale_failure_console_start = len(console_errors)
    _install_fetch_response_gate(page, "/tutor/ask")
    stale_tutor_failure = _declare_expected_http_errors(
        console_errors,
        label="graph-reload",
        page_url=f"{FRONTEND_URL}/tutor",
        source_url=f"{BROWSER_API_URL}/tutor/ask",
        method="POST",
    )
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=stale_tutor_failure,
            body='{"detail":"intentional stale Tutor failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    page.get_by_label("Question").fill("Updated prompt after stale failure submission")
    page.get_by_label("Graph concept key").fill("concept:attention")
    _release_fetch_response_gate(page)
    _require(
        page.get_by_test_id("tutor-error").count() == 0,
        "stale Tutor failure published after prompt and Graph context changed",
    )
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    _wait_for_declared_http_errors(
        page, console_errors, expectation_ids=stale_tutor_failure
    )
    stale_failure_console = console_errors[stale_failure_console_start:]
    _require(
        len(stale_failure_console) == 1 and "status of 503" in stale_failure_console[0],
        f"unexpected stale Tutor failure console output: {stale_failure_console}",
    )
    _restore_fetch_response_gate(page)
    page.get_by_label("Graph concept key").fill("")

    stale_quiz_response = {
        "questions": [
            {
                "question": "P3-027 stale Quiz must never be displayed",
                "options": ["Stale", "Current"],
                "correct_answer": "Current",
                "explanation": "This delayed Quiz belongs to an invalidated mode.",
                "sources": [],
            }
        ],
        "total": 1,
    }
    page.get_by_role("button", name="Quiz", exact=True).click()
    page.get_by_label("Prompt").fill("stale quiz")
    _install_fetch_response_gate(page, "/tutor/quiz")
    page.route(
        re.compile(r".*/tutor/quiz$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(stale_quiz_response),
        ),
        times=1,
    )
    page.get_by_role("button", name="Generate quiz", exact=True).click()
    page.get_by_role("button", name="Explain", exact=True).click()
    _release_fetch_response_gate(page)
    _require(
        page.get_by_test_id("tutor-quiz-workspace").count() == 0
        and page.get_by_text("P3-027 stale Quiz must never be displayed").count() == 0,
        "stale Quiz published after the Tutor mode changed",
    )
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    _restore_fetch_response_gate(page)
    page.get_by_label("Question").fill("什么是 CRB 和 Fisher 信息下界？")
    checks["tutor_prompt_node_failure_and_mode_quiz_ownership"] = True

    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(markdown_response, ensure_ascii=False),
        ),
        times=1,
    )
    tutor_follow_up_console_start = len(console_errors)
    _install_fetch_response_gate(page, "/tutor/sessions", method="POST")
    tutor_follow_up_failure = _declare_expected_http_errors(
        console_errors,
        label="graph-reload",
        page_url=f"{FRONTEND_URL}/tutor",
        source_url=f"{BROWSER_API_URL}/tutor/sessions",
        method="POST",
    )
    page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=tutor_follow_up_failure,
            body='{"detail":"intentional delayed Tutor activity failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-result")).to_be_focused()
    expect(page.get_by_test_id("tutor-request-status")).to_have_text("Tutor answer ready.")
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_test_id("tutor-answer").locator("strong")).to_contain_text("Fisher information")
    expect(page.get_by_test_id("tutor-answer").locator(".katex").first).to_be_visible()
    expect(page.get_by_test_id("tutor-answer").locator("code")).to_contain_text("fisher_information")
    tutor_article_link = page.get_by_role("link", name="Open local article").first
    expect(tutor_article_link).to_be_visible()
    _require(
        tutor_article_link.get_attribute("href") == f"/articles/{CRB_ARTICLE_ID}",
        "Tutor Article deep link is invalid",
    )
    page.get_by_role("button", name="How is the lower bound derived?", exact=True).click()
    expect(page.get_by_label("Question")).to_have_value("How is the lower bound derived?")
    expect(page.get_by_label("Question")).to_be_focused()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible()
    _release_fetch_response_gate(page)
    expect(
        page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        )
    ).to_be_visible(timeout=30_000)
    _wait_for_declared_http_errors(
        page, console_errors, expectation_ids=tutor_follow_up_failure
    )
    tutor_follow_up_console = console_errors[tutor_follow_up_console_start:]
    _require(
        len(tutor_follow_up_console) == 1
        and "status of 503" in tutor_follow_up_console[0],
        f"unexpected delayed Tutor activity failure console output: {tutor_follow_up_console}",
    )
    _restore_fetch_response_gate(page)
    checks["tutor_explain"] = True
    checks["guided_tutor_article_markdown_and_follow_up"] = True
    checks["tutor_follow_up_preserves_activity_failure"] = True
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("tutor-activity").get_by_role("alert")).to_have_count(0)
    expect(page.get_by_test_id("tutor-result")).to_be_focused(timeout=30_000)
    checks["tutor_follow_up_submission_clears_previous_activity_failure"] = True

    page.get_by_role("button", name="Derive", exact=True).click()
    page.get_by_label("Question").fill("Activity completion that will become stale")
    stale_activity_console_start = len(console_errors)
    _install_fetch_response_gate(page, "/tutor/sessions", method="POST")
    stale_activity_failure = _declare_expected_http_errors(
        console_errors,
        label="graph-reload",
        page_url=f"{FRONTEND_URL}/tutor",
        source_url=f"{BROWSER_API_URL}/tutor/sessions",
        method="POST",
    )
    page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=stale_activity_failure,
            body='{"detail":"intentional stale Tutor activity failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("tutor-result")).to_be_focused(timeout=30_000)
    page.get_by_label("Question").fill("Superseding ordinary prompt edit")
    _release_fetch_response_gate(page)
    _require(
        page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        ).count()
        == 0,
        "superseded Tutor activity failure published after an ordinary prompt edit",
    )
    _wait_for_declared_http_errors(
        page, console_errors, expectation_ids=stale_activity_failure
    )
    stale_activity_console = console_errors[stale_activity_console_start:]
    _require(
        len(stale_activity_console) == 1
        and "status of 503" in stale_activity_console[0],
        f"unexpected stale Tutor activity console output: {stale_activity_console}",
    )
    _restore_fetch_response_gate(page)
    checks["tutor_superseded_activity_completion_is_silent"] = True

    page.get_by_label("Question").fill("根据文章公式推导 CRB 下界")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-activity")).to_contain_text(CRB_TITLE, timeout=30_000)
    expect(page.get_by_test_id("tutor-activity")).not_to_contain_text(CRB_ARTICLE_ID)
    checks["tutor_derive"] = True

    page.get_by_role("button", name="Quiz", exact=True).click()
    page.get_by_label("Prompt").fill("CRB")
    page.get_by_role("button", name="Generate quiz", exact=True).click()
    expect(page.get_by_role("heading", name="Quiz", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-quiz-workspace")).to_be_focused()
    expect(page.get_by_test_id("tutor-request-status")).to_contain_text("Quiz ready with")
    tutor_mode_group = page.get_by_test_id("tutor-mode-group")
    expect(tutor_mode_group.locator("legend")).to_have_text("Study mode")
    _require(
        tutor_mode_group.locator('button[aria-pressed]').count() == 5,
        "Tutor mode group does not expose five pressed buttons",
    )
    _require(
        tutor_mode_group.locator('button[aria-pressed="true"]').count() == 1,
        "Tutor mode group does not expose exactly one active mode",
    )
    _require(page.get_by_role("tablist").count() == 0, "Tutor mode exposes a partial tab pattern")
    _require(page.get_by_text(re.compile(r"^Correct answer:")).count() == 0, "Quiz disclosed answers before submission")
    quiz_articles = page.get_by_test_id("tutor-quiz-workspace").locator("article")
    _require(quiz_articles.count() >= 2, "Quiz did not return enough grounded questions for choices")
    for quiz_index in range(quiz_articles.count()):
        quiz_articles.nth(quiz_index).locator('input[type="radio"]').first.check()
    page.get_by_role("button", name="Check answers", exact=True).click()
    expect(page.get_by_test_id("tutor-quiz-score")).to_be_visible()
    expect(page.get_by_test_id("tutor-quiz-score")).to_be_focused()
    expect(page.get_by_test_id("tutor-quiz-score")).to_have_attribute("role", "status")
    expect(page.get_by_test_id("tutor-quiz-score")).to_have_attribute("aria-live", "polite")
    expect(page.get_by_text(re.compile(r"^Correct answer:")).first).to_be_visible()
    expect(page.get_by_role("heading", name="题目来源", exact=True).first).to_be_visible()
    page.get_by_role("button", name="Try again", exact=True).click()
    _require(page.get_by_text(re.compile(r"^Correct answer:")).count() == 0, "Quiz retry retained answer disclosure")
    expect(quiz_articles.first.locator('input[type="radio"]').first).to_be_focused()
    checks["tutor_quiz"] = True
    checks["tutor_quiz_hidden_review_and_score"] = True
    checks["tutor_accessible_result_and_quiz_focus"] = True

    page.get_by_role("button", name="Research", exact=True).click()
    page.get_by_label("Question").fill("基于本地资料给出 CRB 研究方向")
    tutor_session_failure = _declare_expected_http_errors(
        console_errors,
        label="graph-reload",
        page_url=f"{FRONTEND_URL}/tutor",
        source_url=f"{BROWSER_API_URL}/tutor/sessions",
        method="POST",
    )
    page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=tutor_session_failure,
            body='{"detail":"intentional P3-017 session write failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name=re.compile(r"^(Answer|Refusal)$"))).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_role("heading", name="Research 模式范围", exact=True)).to_be_visible()
    expect(page.get_by_text("The answer is ready, but recent activity could not be updated.", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_role("heading", name=re.compile(r"^(Answer|Refusal)$"))).to_be_visible()
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=tutor_session_failure,
    )
    checks["tutor_research"] = True
    checks["tutor_session_failure_isolation"] = True

    page.get_by_role("button", name="Q&A", exact=True).click()
    expect(page.get_by_test_id("tutor-activity").get_by_role("alert")).to_have_count(0)
    checks["tutor_context_change_clears_previous_activity_failure"] = True
    page.get_by_label("Question").fill("Trigger one controlled Tutor failure")
    tutor_error_console_start = len(console_errors)
    tutor_request_failure = _declare_expected_http_errors(
        console_errors,
        label="graph-reload",
        page_url=f"{FRONTEND_URL}/tutor",
        source_url=f"{BROWSER_API_URL}/tutor/ask",
        method="POST",
    )
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=tutor_request_failure,
            body='{"detail":"intentional Tutor request failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("tutor-error")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-error")).to_be_focused()
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({**markdown_response, "mode": "qa"}, ensure_ascii=False),
        ),
        times=1,
    )
    page.get_by_role("button", name="Retry request", exact=True).press("Enter")
    expect(page.get_by_test_id("tutor-result")).to_be_focused(timeout=30_000)
    _wait_for_declared_http_errors(
        page, console_errors, expectation_ids=tutor_request_failure
    )
    tutor_error_console = console_errors[tutor_error_console_start:]
    _require(
        len(tutor_error_console) == 1 and "status of 503" in tutor_error_console[0],
        f"unexpected controlled Tutor failure console output: {tutor_error_console}",
    )
    checks["tutor_accessible_error_and_retry_focus"] = True

    _require(not page_errors, f"primary workflow emitted page errors: {page_errors}")
    page.close()

    activity_order_page = _new_observed_page(
        context, console_errors, page_errors, label="tutor-activity-read-order"
    )
    activity_order_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(activity_order_page)
    _install_fetch_response_gate(activity_order_page, "/tutor/sessions", method="GET")
    activity_route_anchor = console_errors._event_sequence
    activity_route_transition = _declare_expected_route_transition(
        activity_order_page,
        destination_url=f"{FRONTEND_URL}/tutor",
    )
    activity_order_page.get_by_role("link", name="Tutor", exact=True).click()
    expect(
        activity_order_page.get_by_role(
            "heading", name="AI Research Tutor", exact=True
        )
    ).to_be_visible(timeout=30_000)
    _wait_for_exact_route_request_to_finish(
        activity_order_page,
        console_errors,
        source_url=f"{FRONTEND_URL}/tutor",
        after_sequence=activity_route_anchor,
        expect_prefetch=False,
        require_observed_request=True,
        allow_response_backed_route_abort=True,
        cache_precursor_expectation_id=activity_route_transition,
    )
    _complete_expected_route_transition(
        activity_order_page,
        activity_route_transition,
    )
    _wait_for_fetch_response_gate_pending(activity_order_page)
    activity_order_console_start = len(console_errors)
    activity_order_failure = _declare_expected_http_errors(
        console_errors,
        label="tutor-activity-read-order",
        page_url=f"{FRONTEND_URL}/tutor",
        source_url=f"{BROWSER_API_URL}/tutor/sessions",
        method="POST",
    )
    activity_order_page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=activity_order_page,
            expectation_ids=activity_order_failure,
            body='{"detail":"intentional activity ordering failure"}',
        ),
        times=1,
    )
    activity_order_page.get_by_label("Question").fill(
        "Keep the newer activity failure after an older read completes"
    )
    activity_order_page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(
        activity_order_page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        )
    ).to_be_visible(timeout=30_000)
    _release_fetch_response_gate(activity_order_page)
    expect(
        activity_order_page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        )
    ).to_be_visible()
    _wait_for_declared_http_errors(
        activity_order_page,
        console_errors,
        expectation_ids=activity_order_failure,
    )
    activity_order_console = console_errors[activity_order_console_start:]
    _require(
        len(activity_order_console) == 1
        and "status of 503" in activity_order_console[0],
        f"unexpected Tutor activity ordering console output: {activity_order_console}",
    )
    _restore_fetch_response_gate(activity_order_page)
    activity_retry = activity_order_page.get_by_role("button", name="Retry activity", exact=True)
    activity_retry.focus()
    activity_retry.press("Enter")
    activity_region = activity_order_page.get_by_test_id("tutor-activity")
    expect(activity_region).to_be_focused(timeout=30_000)
    _require_visible_focus(activity_region, "Tutor activity retry result")
    expect(activity_region.get_by_role("alert")).to_have_count(0)
    checks["tutor_newer_activity_failure_supersedes_older_read"] = True
    checks["tutor_activity_retry_focus"] = True
    activity_order_page.close()

    activity_focus_console_start = len(console_errors)
    activity_focus_page = _new_observed_page(
        context, console_errors, page_errors, label="tutor-activity-retry-focus-owner"
    )
    activity_focus_failure = _declare_expected_http_errors(
        console_errors,
        label="tutor-activity-retry-focus-owner",
        page_url=f"{FRONTEND_URL}/tutor",
        source_url=f"{BROWSER_API_URL}/tutor/sessions",
        method="GET",
    )
    activity_focus_page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=activity_focus_page,
            expectation_ids=activity_focus_failure,
            body='{"detail":"intentional P3-036 activity focus failure"}',
        ),
        times=1,
    )
    activity_focus_page.goto(f"{FRONTEND_URL}/tutor", wait_until="domcontentloaded")
    _wait_for_application_shell(activity_focus_page)
    activity_focus_retry = activity_focus_page.get_by_role(
        "button", name="Retry activity", exact=True
    )
    expect(activity_focus_retry).to_be_visible(timeout=30_000)
    _install_fetch_response_gate(activity_focus_page, "/tutor/sessions", method="GET")
    activity_focus_retry.focus()
    activity_focus_retry.press("Enter")
    _wait_for_fetch_response_gate_pending(activity_focus_page)
    activity_question_focus_owner = activity_focus_page.get_by_label("Question")
    activity_question_focus_owner.click()
    _release_fetch_response_gate(activity_focus_page)
    expect(activity_focus_retry).to_have_count(0, timeout=30_000)
    expect(activity_question_focus_owner).to_be_focused()
    _require_visible_focus(
        activity_question_focus_owner,
        "newer Tutor activity focus owner",
    )
    _restore_fetch_response_gate(activity_focus_page)
    _wait_for_declared_http_errors(
        activity_focus_page,
        console_errors,
        expectation_ids=activity_focus_failure,
    )
    activity_focus_page.close()
    activity_focus_console = console_errors[activity_focus_console_start:]
    _require(
        len(activity_focus_console) == 1
        and "status of 503" in activity_focus_console[0],
        f"unexpected Tutor activity focus console output: {activity_focus_console}",
    )
    checks["tutor_activity_retry_newer_focus_owner"] = True

    route_context_page = _new_observed_page(
        context, console_errors, page_errors, label="tutor-route-context-removal"
    )
    route_context_page.goto(
        f"{FRONTEND_URL}/tutor?{tutor_workflow_query}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(route_context_page)
    expect(route_context_page.get_by_test_id("tutor-selected-article")).to_contain_text(
        CRB_TITLE
    )
    same_route_activity_posts: list[str] = []

    def track_same_route_activity(request) -> None:
        if request.method == "POST" and urlparse(request.url).path == "/tutor/sessions":
            same_route_activity_posts.append(request.url)

    route_context_page.on("request", track_same_route_activity)
    _install_fetch_response_gate(route_context_page, "/tutor/ask")
    route_context_page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    **markdown_response,
                    "answer": "P3-027 stale same-route response must not publish.",
                },
                ensure_ascii=False,
            ),
        ),
        times=1,
    )
    route_context_page.get_by_label("Question").fill(
        "Pending response before same-route context removal"
    )
    route_context_page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(route_context_page.get_by_test_id("guided-tutor-workspace")).to_have_attribute(
        "aria-busy", "true"
    )
    tutor_context_removal_transition = _declare_expected_route_transition(
        route_context_page,
        destination_url=f"{FRONTEND_URL}/tutor",
    )
    route_context_page.get_by_role("link", name="Tutor", exact=True).click()
    expect(route_context_page).to_have_url(f"{FRONTEND_URL}/tutor")
    expect(route_context_page.get_by_test_id("tutor-selected-article")).to_have_count(0)
    expect(route_context_page.get_by_label("Question")).to_have_value("")
    _release_fetch_response_gate(route_context_page)
    expect(route_context_page.get_by_test_id("tutor-result")).to_have_count(0)
    expect(route_context_page.get_by_test_id("tutor-error")).to_have_count(0)
    _require(
        route_context_page.get_by_text(
            "P3-027 stale same-route response must not publish.", exact=True
        ).count()
        == 0,
        "same-route context removal published a stale Tutor response",
    )
    _require(
        not same_route_activity_posts,
        f"same-route context removal wrote stale Tutor activity: {same_route_activity_posts}",
    )
    _restore_fetch_response_gate(route_context_page)
    _wait_for_page_requests_to_settle(route_context_page, console_errors)
    _complete_expected_route_transition(
        route_context_page,
        tutor_context_removal_transition,
    )
    checks["tutor_route_context_removal"] = True
    route_context_page.close()

    unmount_page = _new_observed_page(
        context, console_errors, page_errors, label="tutor-pending-navigation"
    )
    pending_navigation_activity: list[str] = []

    def track_pending_navigation_activity(request) -> None:
        if request.method == "POST" and urlparse(request.url).path == "/tutor/sessions":
            pending_navigation_activity.append(request.url)

    unmount_page.on("request", track_pending_navigation_activity)
    unmount_page.goto(
        f"{FRONTEND_URL}/tutor?{tutor_workflow_query}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(unmount_page)
    _install_fetch_response_gate(unmount_page, "/tutor/ask")
    unmount_page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    **markdown_response,
                    "answer": "P3-027 pending navigation response must not persist.",
                },
                ensure_ascii=False,
            ),
        ),
        times=1,
    )
    unmount_page.get_by_label("Question").fill("Navigate away before this completes")
    unmount_page.get_by_role("button", name="Ask tutor", exact=True).click()
    pending_navigation_transition = _declare_expected_route_transition(
        unmount_page,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    unmount_page.get_by_role("link", name="Articles", exact=True).click()
    expect(
        unmount_page.get_by_role("heading", name="Article List", exact=True)
    ).to_be_visible(timeout=30_000)
    _release_fetch_response_gate(unmount_page)
    _require(
        not pending_navigation_activity,
        f"unmounted Tutor request persisted activity: {pending_navigation_activity}",
    )
    checks["tutor_pending_navigation_has_no_activity"] = True
    _restore_fetch_response_gate(unmount_page)
    _wait_for_page_requests_to_settle(unmount_page, console_errors)
    _complete_expected_route_transition(
        unmount_page,
        pending_navigation_transition,
    )
    unmount_page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="graph-route-boundary")
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    graph_boundary_open_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/graph",
    )
    page.get_by_role("link", name="Graph", exact=True).click()
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_boundary_open_transition)
    graph_boundary_back_transition = _declare_expected_route_transition(
        page,
        destination_url=FRONTEND_URL,
    )
    page.go_back()
    expect(
        page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible(timeout=30_000)
    _require(
        page.url.rstrip("/") == FRONTEND_URL,
        f"Graph popstate handler replaced a non-Graph destination: {page.url}",
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, graph_boundary_back_transition)
    _require(not page_errors, f"Graph route-boundary Back emitted page errors: {page_errors}")
    checks["graph_route_boundary_back"] = True
    page.close()

    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="article-not-found",
    )
    article_not_found_expectations = console_errors.declare_http_errors(
        label="article-not-found",
        page_url=f"{FRONTEND_URL}/articles/not-a-real-article",
        source_url=f"{BROWSER_API_URL}/articles/not-a-real-article",
        status=404,
        method="GET",
        resource_type="fetch",
        navigation_request=False,
    )
    page.route(
        lambda url: url == f"{BROWSER_API_URL}/articles/not-a-real-article",
        lambda route: _forward_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=article_not_found_expectations,
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}/articles/not-a-real-article", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_text("Article not found", exact=True)).to_be_visible(timeout=30_000)
    _require(not page_errors, f"Article not-found route emitted page errors: {page_errors}")
    checks["article_not_found_state"] = True
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=article_not_found_expectations,
    )

    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="route-not-found",
    )
    route_not_found_expectations = console_errors.declare_http_errors(
        label="route-not-found",
        page_url=f"{FRONTEND_URL}/not-a-product-route",
        source_url=f"{FRONTEND_URL}/not-a-product-route",
        status=404,
        method="GET",
        resource_type="document",
        navigation_request=True,
    )
    page.route(
        lambda url: url == f"{FRONTEND_URL}/not-a-product-route",
        lambda route: _forward_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=route_not_found_expectations,
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}/not-a-product-route", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(
        page.get_by_test_id("route-not-found-state").get_by_text("Page not found", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "unknown")
    _require(not page_errors, f"route not-found state emitted page errors: {page_errors}")
    checks["route_not_found_state"] = True
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=route_not_found_expectations,
    )

    page = _new_observed_page(context, console_errors, page_errors, label="article-controlled-error")
    article_list_failure = _declare_expected_http_errors(
        console_errors,
        label="article-controlled-error",
        page_url=f"{FRONTEND_URL}/articles",
        source_url=f"{BROWSER_API_URL}/v1.1/articles?page=1&page_size=20&sort=date_desc",
    )
    page.route(
        re.compile(r".*/v1\.1/articles(?:\?.*)?$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=article_list_failure,
            body='{"detail":"intentional P3-011 E2E failure"}',
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}/articles", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_text("Failed to load articles: 503", exact=True)).to_be_visible(timeout=30_000)
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=article_list_failure,
    )
    _require(not page_errors, f"Article error state emitted page errors: {page_errors}")
    checks["controlled_backend_error_state"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="graph-controlled-error")
    graph_error_console_start = len(console_errors)
    page.add_init_script(
        script=f"""
        sessionStorage.setItem(
          "scientific-spaces:graph-article-return-focus:v1",
          {json.dumps(json.dumps({
              "articleId": ATTENTION_ARTICLE_ID,
              "focusTarget": "provenance-0",
              "returnTo": ATTENTION_CONCEPT_RETURN,
          }))}
        );
        """
    )
    graph_detail_failure = _declare_expected_http_errors(
        console_errors,
        label="graph-controlled-error",
        page_url=f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}",
        source_url=f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention",
    )
    page.route(
        re.compile(r".*/graph/nodes/concept%3Aattention$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=graph_detail_failure,
            body='{"detail":"intentional P3-024 Graph detail failure"}',
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    graph_error_region = page.get_by_test_id("graph-selected-region")
    expect(graph_error_region.get_by_role("alert")).to_contain_text(
        "Graph request failed: 503", timeout=30_000
    )
    expect(graph_error_region).to_be_focused()
    _require_visible_focus(graph_error_region, "returned Graph detail error region")
    graph_error_region.get_by_role("button", name="Retry", exact=True).click()
    expect(graph_error_region).to_be_focused()
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_test_id("graph-selection-status")).to_contain_text("Details ready.")
    _wait_for_declared_http_errors(
        page, console_errors, expectation_ids=graph_detail_failure
    )
    expected_graph_console = console_errors[graph_error_console_start:]
    _require(
        expected_graph_console
        and all("status of 503" in message for message in expected_graph_console),
        f"unexpected Graph failure console output: {expected_graph_console}",
    )
    _require(not page_errors, f"Graph detail recovery emitted page errors: {page_errors}")
    checks["graph_detail_error_focus_and_retry"] = True
    _wait_for_page_requests_to_settle(page, console_errors)
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="dashboard-partial")
    dashboard_stats_failure = _declare_expected_http_errors(
        console_errors,
        label="dashboard-partial",
        page_url=f"{FRONTEND_URL}/",
        source_url=f"{BROWSER_API_URL}/learning/stats",
    )
    page.route(
        re.compile(r".*/learning/stats$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=dashboard_stats_failure,
            body='{"detail":"intentional P3-016 partial dashboard failure"}',
        ),
        times=1,
    )
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_attribute("data-state", "partial")
    expect(page.get_by_role("heading", name="New in Library", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name=CRB_TITLE, exact=True).first).to_be_visible()
    page.get_by_role("button", name="Retry", exact=True).click()
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_count(0, timeout=30_000)
    expect(page.get_by_role("heading", name="Learning Activity", exact=True)).to_be_visible()
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=dashboard_stats_failure,
    )
    _require(not page_errors, f"Dashboard partial state emitted page errors: {page_errors}")
    checks["dashboard_partial_failure"] = True
    _wait_for_page_requests_to_settle(page, console_errors)
    page.close()

    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="dashboard-completion-status-unavailable",
    )
    dashboard_completion_console_start = len(console_errors)
    dashboard_state_failure = _declare_expected_http_errors(
        console_errors,
        label="dashboard-completion-status-unavailable",
        page_url=f"{FRONTEND_URL}/",
        source_url=f"{BROWSER_API_URL}/learning/state",
    )
    page.route(
        re.compile(r".*/learning/state$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=dashboard_state_failure,
            body='{"detail":"intentional P3-025 completion-state list failure"}',
        ),
        times=1,
    )
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_attribute(
        "data-state", "partial"
    )
    continue_region = page.get_by_test_id("continue-reading")
    expect(continue_region).to_contain_text("Completion status is unavailable")
    expect(
        continue_region.get_by_role("link", name=re.compile(r"^Continue learning "))
    ).to_be_visible()
    page.get_by_role("button", name="Retry", exact=True).click()
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_count(0, timeout=30_000)
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    _wait_for_declared_http_errors(
        page, console_errors, expectation_ids=dashboard_state_failure
    )
    expected_dashboard_completion_console = console_errors[
        dashboard_completion_console_start:
    ]
    _require(
        len(expected_dashboard_completion_console) == 1
        and "status of 503" in expected_dashboard_completion_console[0],
        "unexpected Dashboard completion-state fallback console output: "
        f"{expected_dashboard_completion_console}",
    )
    _require(
        not page_errors,
        f"Dashboard completion-state fallback emitted page errors: {page_errors}",
    )
    checks["dashboard_completion_status_fallback"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="library-partial")
    library_bookmark_failure = _declare_expected_http_errors(
        console_errors,
        label="library-partial",
        page_url=f"{FRONTEND_URL}/library",
        source_url=f"{BROWSER_API_URL}/learning/bookmarks",
    )
    page.route(
        re.compile(r".*/learning/bookmarks$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=page,
            expectation_ids=library_bookmark_failure,
            body='{"detail":"intentional P3-020 partial Bookmark failure"}',
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}/library", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("saved-library-remote-state")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("saved-library-remote-state")).to_contain_text(
        "Some saved-learning data is unavailable"
    )
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_text(CRB_TITLE, exact=True).first).to_be_visible()
    page.get_by_test_id("saved-library-remote-state").get_by_role(
        "button", name="Retry", exact=True
    ).click()
    expect(page.get_by_test_id("saved-library-remote-state")).to_have_count(0, timeout=30_000)
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=library_bookmark_failure,
    )
    _require(not page_errors, f"Saved Library partial state emitted page errors: {page_errors}")
    checks["saved_library_partial_failure"] = True
    _wait_for_page_requests_to_settle(page, console_errors)
    page.close()
    context.close()

    article_race_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    article_race_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          let delayedCrb = false;
          let delayedSuccess = false;
          let delayedSort = false;
          let delayedPage = false;
          let retryRaceCount = 0;
          const articleResponse = (id, title, query, sort, page, hasNext = false) =>
            new Response(JSON.stringify({
              items: [{
                id,
                title,
                url: `https://spaces.ac.cn/archives/${id}`,
                metadata: {},
                content_preview: `${title} preview`,
              }],
              total: hasNext ? 40 : 1,
              query,
              category: null,
              sort,
              page,
              page_size: 20,
              total_pages: hasNext ? 2 : 1,
              has_next: hasNext && page === 1,
              has_previous: page > 1,
            }), { status: 200, headers: { "Content-Type": "application/json" } });
          window.fetch = (...args) => {
            const url = String(args[0]);
            if (!delayedCrb && url.includes('/v1.1/articles') && url.includes('q=CRB')) {
              delayedCrb = true;
              return new Promise((_, reject) => {
                window.setTimeout(() => reject(new Error('intentional stale Article failure')), 900);
              });
            }
            if (!delayedSuccess && url.includes('/v1.1/articles') && url.includes('q=slow-success')) {
              delayedSuccess = true;
              return new Promise((resolve) => {
                window.setTimeout(
                  () => resolve(articleResponse('stale-success', 'Stale success result', 'slow-success', 'date_desc', 1)),
                  900,
                );
              });
            }
            if (!delayedSort && url.includes('/v1.1/articles') && url.includes('q=CRB') && url.includes('sort=title_asc')) {
              delayedSort = true;
              return new Promise((resolve) => {
                window.setTimeout(
                  () => resolve(articleResponse('stale-sort', 'Stale sort result', 'CRB', 'title_asc', 1)),
                  900,
                );
              });
            }
            if (url.includes('/v1.1/articles') && url.includes('q=page-fixture')) {
              const page = Number(new URL(url).searchParams.get('page') || '1');
              if (page === 2 && !delayedPage) {
                delayedPage = true;
                return new Promise((resolve) => {
                  window.setTimeout(
                    () => resolve(articleResponse('stale-page', 'Stale page 2 result', 'page-fixture', 'archive_desc', 2, true)),
                    900,
                  );
                });
              }
              return Promise.resolve(articleResponse('page-one', 'Page fixture 1', 'page-fixture', 'date_desc', 1, true));
            }
            if (url.includes('/v1.1/articles') && url.includes('q=retry-race')) {
              retryRaceCount += 1;
              if (retryRaceCount === 1) {
                return Promise.resolve(new Response('{', {
                  status: 200,
                  headers: { "Content-Type": "application/json" },
                }));
              }
              return new Promise((resolve) => {
                window.setTimeout(
                  () => resolve(articleResponse('stale-retry', 'Stale retry result', 'retry-race', 'date_desc', 1)),
                  900,
                );
              });
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    _install_network_guard(article_race_context, blocked_external)
    article_race_page = _new_observed_page(
        article_race_context,
        console_errors,
        page_errors,
        label="article-result-race",
    )
    article_race_page.goto(f"{FRONTEND_URL}/articles", wait_until="domcontentloaded")
    _wait_for_application_shell(article_race_page)
    expect(article_race_page.get_by_text("Showing 1-3 of 3", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(article_race_page.get_by_test_id("article-pagination")).to_have_count(0)
    race_search = article_race_page.get_by_placeholder("Search title or keyword")
    race_submit = article_race_page.get_by_role("button", name="Search", exact=True)
    race_search.fill("temporary query")
    clear_search = article_race_page.get_by_role("button", name="Clear", exact=True)
    clear_search.focus()
    clear_search.press("Enter")
    expect(race_search).to_be_focused()
    _require_visible_focus(race_search, "Article List cleared search")
    expect(race_search).to_have_value("")
    race_search.fill("CRB")
    race_submit.click()
    expect(article_race_page.get_by_text("Loading articles", exact=True)).to_be_visible()
    _require(
        article_race_page.get_by_role("link", name=CRB_TITLE, exact=True).count() == 0,
        "pending Article request left stale rows actionable",
    )
    race_search.fill("Attention")
    race_submit.click()
    race_search.fill("CRB")
    race_submit.click()
    race_crb_link = article_race_page.get_by_role("link", name=CRB_TITLE, exact=True)
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Article library unavailable", exact=True)).to_have_count(0)

    race_search.fill("slow-success")
    race_submit.click()
    race_search.fill("CRB")
    race_submit.click()
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Stale success result", exact=True)).to_have_count(0)

    race_sort = article_race_page.get_by_test_id(
        "article-discovery-workspace"
    ).locator("select")
    race_sort.select_option("title_asc")
    race_sort.select_option("archive_desc")
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Stale sort result", exact=True)).to_have_count(0)

    race_search.fill("page-fixture")
    race_submit.click()
    expect(article_race_page.get_by_text("Page fixture 1", exact=True)).to_be_visible(
        timeout=30_000
    )
    article_race_page.get_by_role("button", name="Next", exact=True).click()
    race_sort.select_option("date_desc")
    expect(article_race_page.get_by_text("Page fixture 1", exact=True)).to_be_visible(
        timeout=30_000
    )
    article_race_page.wait_for_timeout(1_000)
    expect(article_race_page.get_by_text("Stale page 2 result", exact=True)).to_have_count(0)
    expect(article_race_page.get_by_text("Page 1 / 2", exact=True)).to_be_visible()

    race_search.fill("retry-race")
    race_submit.click()
    expect(article_race_page.get_by_text("Article library unavailable", exact=True)).to_be_visible(
        timeout=30_000
    )
    article_race_page.get_by_role("button", name="Retry articles", exact=True).click()
    race_search.fill("CRB")
    race_submit.click()
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Stale retry result", exact=True)).to_have_count(0)

    race_checkbox = article_race_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    race_checkbox.check()
    expect(race_checkbox).to_be_checked()
    race_search.fill("Attention")
    race_submit.click()
    expect(
        article_race_page.get_by_role("link", name=ATTENTION_TITLE, exact=True)
    ).to_be_visible(timeout=30_000)
    expect(article_race_page.get_by_test_id("article-session-capture")).to_contain_text(
        "0 selected on this page"
    )

    article_race_page.route(
        re.compile(r".*/v1\.1/articles\?.*q=__p3026_error__.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="{",
        ),
        times=1,
    )
    race_search.fill("__p3026_error__")
    race_submit.click()
    expect(article_race_page.get_by_text("Article library unavailable", exact=True)).to_be_visible(
        timeout=30_000
    )
    _require(
        article_race_page.locator('[data-testid="article-discovery-workspace"] article').count() == 0,
        "failed Article request exposed actionable stale rows",
    )
    article_retry = article_race_page.get_by_role("button", name="Retry articles", exact=True)
    article_retry.focus()
    article_retry.press("Enter")
    expect(article_race_page.get_by_text("No articles found.", exact=True)).to_be_visible(
        timeout=30_000
    )
    article_status = article_race_page.get_by_test_id("article-list-status")
    expect(article_status).to_be_focused()
    _require_visible_focus(article_status, "Article List retry result")
    checks["article_result_generation_and_stale_failure_guard"] = True
    checks["article_result_stale_success_sort_page_retry_guard"] = True
    checks["article_result_failure_retry_and_selection_reset"] = True
    article_race_context.close()

    article_recovery_context = browser.new_context(
        viewport={"width": 320, "height": 844}, locale="zh-CN", is_mobile=True
    )
    article_recovery_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          let deferOnce = true;
          window.__p3028LateArticleResolved = false;
          window.fetch = async (...args) => {
            const input = args[0];
            const target = new URL(
              typeof input === "string" || input instanceof URL ? input : input.url,
              window.location.href
            );
            if (deferOnce && target.pathname === "/articles/crb-formula") {
              deferOnce = false;
              return new Promise((resolve) => {
                window.setTimeout(() => {
                  window.__p3028LateArticleResolved = true;
                  resolve(new Response(JSON.stringify({
                    id: "crb-formula",
                    title: "STALE ARTICLE RESPONSE",
                    url: "https://spaces.ac.cn/archives/stale",
                    content: "# Stale response",
                    metadata: { date: null, category: null, references: [], images: [] },
                  }), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                  }));
                }, 12_000);
              });
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    _install_network_guard(article_recovery_context, blocked_external)
    article_recovery_page = _new_observed_page(
        article_recovery_context,
        console_errors,
        page_errors,
        label="graph-reader-recovery",
    )
    graph_recovery_return = "/graph?node_id=article%3Acrb-formula&q=CRB"
    graph_recovery_reader = (
        f"/articles/{CRB_ARTICLE_ID}?"
        + urlencode({"from": graph_recovery_return})
    )
    recovery_session_posts: list[str] = []
    recovery_learning_gets: list[str] = []

    def track_recovery_session(request) -> None:
        request_path = urlparse(request.url).path
        if request.method == "POST" and request_path == "/learning/sessions":
            recovery_session_posts.append(request.url)
        if request.method == "GET" and request_path in {
            f"/learning/state/{CRB_ARTICLE_ID}",
            "/learning/bookmarks",
            f"/learning/notes/{CRB_ARTICLE_ID}",
        }:
            recovery_learning_gets.append(request_path)

    article_recovery_page.on("request", track_recovery_session)
    article_recovery_page.goto(
        f"{FRONTEND_URL}{graph_recovery_reader}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(article_recovery_page)
    recovery_loading = article_recovery_page.get_by_role("status").filter(
        has_text="Loading article"
    )
    expect(recovery_loading).to_have_count(1)
    expect(recovery_loading.locator("xpath=parent::section")).to_have_attribute(
        "aria-busy", "true"
    )
    expect(
        recovery_loading.get_by_role("link", name="Return to graph", exact=True)
    ).to_have_attribute("href", graph_recovery_return)
    _require(
        not recovery_session_posts,
        "pending Article request created a learning session before Article acceptance",
    )
    expect(
        article_recovery_page.get_by_text("Article unavailable", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(article_recovery_page.get_by_text("Article loading timed out. Try again.")).to_be_visible()
    recovery_retry = article_recovery_page.get_by_role(
        "button", name="Retry article", exact=True
    )
    recovery_return = article_recovery_page.get_by_role(
        "link", name="Return to graph", exact=True
    )
    expect(recovery_retry).to_be_visible()
    _require(
        article_recovery_page.evaluate("document.activeElement === document.body"),
        "hard-loaded Reader recovery moved focus without user interaction",
    )
    recovery_retry.focus()
    expect(recovery_retry).to_be_focused()
    _require_visible_focus(recovery_retry, "narrow Article retry action")
    expect(recovery_return).to_have_attribute("href", graph_recovery_return)
    recovery_retry.scroll_into_view_if_needed()
    recovery_return.scroll_into_view_if_needed()
    _require_viewport_containment(
        recovery_retry.bounding_box(), 320, 844, "narrow Article retry action"
    )
    _require_viewport_containment(
        recovery_return.bounding_box(), 320, 844, "narrow Article return action"
    )
    _require(
        _document_width(article_recovery_page) <= 320,
        "narrow Article recovery surface overflows horizontally",
    )
    recovery_retry.press("Enter")
    recovery_heading = article_recovery_page.locator("article#article-start > h1")
    expect(recovery_heading).to_have_text(CRB_TITLE, timeout=30_000)
    expect(recovery_heading).to_be_focused()
    _require_visible_focus(recovery_heading, "retried Graph-origin Reader heading")
    _require(
        len(recovery_session_posts) == 1,
        f"Article retry created an unexpected number of learning sessions: {recovery_session_posts}",
    )
    history_before_late_response = article_recovery_page.evaluate(
        "localStorage.getItem('scientific-spaces-reading-history-v1')"
    )
    learning_gets_before_late_response = list(recovery_learning_gets)
    article_recovery_page.wait_for_function(
        "() => window.__p3028LateArticleResolved === true",
        timeout=30_000,
    )
    expect(recovery_heading).to_have_text(CRB_TITLE)
    expect(article_recovery_page.get_by_text("STALE ARTICLE RESPONSE", exact=True)).to_have_count(0)
    _require(
        len(recovery_session_posts) == 1,
        "late stale Article success created a second learning session",
    )
    _require(
        article_recovery_page.evaluate(
            "localStorage.getItem('scientific-spaces-reading-history-v1')"
        )
        == history_before_late_response,
        "late stale Article success changed reading history",
    )
    _require(
        recovery_learning_gets == learning_gets_before_late_response,
        "late stale Article success started learning-context reads",
    )
    recovery_end_session = article_recovery_page.get_by_role(
        "button", name="End session", exact=True
    )
    expect(recovery_end_session).to_be_enabled(timeout=30_000)
    recovery_end_session.click()
    expect(recovery_end_session).to_be_disabled()
    checks["graph_reader_loading_and_recovery"] = True
    checks["graph_reader_latest_generation_side_effects"] = True
    article_recovery_context.close()

    stale_session_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    stale_session_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          let deferSessionOnce = true;
          window.__p3028StaleSessionId = null;
          window.fetch = async (...args) => {
            const input = args[0];
            const target = new URL(
              typeof input === "string" || input instanceof URL ? input : input.url,
              window.location.href
            );
            const method = (
              input instanceof Request ? input.method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (deferSessionOnce && method === "POST" && target.pathname === "/learning/sessions") {
              deferSessionOnce = false;
              const response = await originalFetch(...args);
              const payload = await response.clone().json();
              window.__p3028StaleSessionId = payload.session_id;
              await new Promise((resolve) => window.setTimeout(resolve, 1_500));
              return response;
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    _install_network_guard(stale_session_context, blocked_external)
    stale_session_page = _new_observed_page(
        stale_session_context,
        console_errors,
        page_errors,
        label="graph-reader-stale-session",
    )
    stale_session_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(stale_session_page)
    expect(stale_session_page.locator("article#article-start > h1")).to_have_text(
        CRB_TITLE, timeout=30_000
    )
    stale_session_page.wait_for_function(
        "() => typeof window.__p3028StaleSessionId === 'string'",
        timeout=30_000,
    )
    stale_session_id = str(stale_session_page.evaluate("window.__p3028StaleSessionId"))

    def is_stale_session_end(response) -> bool:
        return (
            response.request.method == "PUT"
            and urlparse(response.url).path == f"/learning/sessions/{stale_session_id}/end"
        )

    stale_reader_return_transition = _declare_expected_route_transition(
        stale_session_page,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    with stale_session_page.expect_response(is_stale_session_end, timeout=30_000) as stale_end_info:
        stale_session_page.get_by_role("link", name="Back to articles", exact=True).first.click()
    stale_end_response = stale_end_info.value
    _require(stale_end_response.ok, "stale Reader session reconciliation failed")
    stale_session_page.wait_for_function(
        "() => location.pathname === '/articles'", timeout=30_000
    )
    _complete_expected_route_transition(
        stale_session_page, stale_reader_return_transition
    )
    persisted_sessions = _api_json(stale_session_context, "GET", "/learning/sessions")
    reconciled_session = next(
        (
            item
            for item in persisted_sessions.get("items", [])
            if item.get("session_id") == stale_session_id
        ),
        None,
    )
    _require(
        reconciled_session is not None and reconciled_session.get("ended_at"),
        "stale Reader session remained open after navigation",
    )
    checks["graph_reader_stale_session_reconciled"] = True
    stale_session_context.close()

    learning_partial_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    _install_network_guard(learning_partial_context, blocked_external)
    learning_partial_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="{",
        ),
        times=1,
    )
    learning_partial_page = _new_observed_page(
        learning_partial_context,
        console_errors,
        page_errors,
        label="article-learning-partial",
    )
    learning_partial_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(learning_partial_page)
    learning_partial_row = learning_partial_page.get_by_role(
        "link", name=CRB_TITLE, exact=True
    ).locator("xpath=ancestor::article[1]")
    expect(learning_partial_row).to_contain_text("Status unavailable", timeout=30_000)
    expect(learning_partial_row).to_contain_text("Bookmarked")
    learning_partial_page.evaluate(
        """
        () => {
          const originalFetch = window.fetch.bind(window);
          let delayed = false;
          window.fetch = (...args) => {
            const input = args[0];
            const url = typeof input === "string" ? input : input.url;
            if (!delayed && new URL(url, window.location.href).pathname === "/learning/state") {
              delayed = true;
              return new Promise((resolve, reject) => {
                window.setTimeout(() => originalFetch(...args).then(resolve, reject), 900);
              });
            }
            return originalFetch(...args);
          };
        }
        """
    )
    learning_retry = learning_partial_page.get_by_role(
        "button", name="Retry learning status", exact=True
    )
    learning_retry.click()
    learning_availability = learning_partial_page.get_by_test_id(
        "article-badge-availability"
    )
    expect(learning_retry).to_be_disabled()
    expect(learning_availability).to_have_attribute("aria-busy", "true")
    expect(learning_availability).to_contain_text(
        "Learning status retry in progress. Article rows remain unavailable."
    )
    expect(learning_availability).to_be_focused()
    _require_visible_focus(learning_availability, "Learning badge retry progress")
    learning_search = learning_partial_page.get_by_placeholder("Search title or keyword")
    learning_search.focus()
    expect(learning_search).to_be_focused()
    expect(learning_partial_row).to_contain_text("completed", timeout=30_000)
    expect(learning_availability).to_contain_text("Learning status is available.")
    expect(learning_search).to_be_focused()
    checks["article_learning_failure_preserves_bookmarks"] = True
    learning_partial_context.close()

    bookmark_partial_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    _install_network_guard(bookmark_partial_context, blocked_external)
    bookmark_partial_context.route(
        re.compile(r".*/learning/bookmarks$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="{",
        ),
        times=1,
    )
    bookmark_partial_page = _new_observed_page(
        bookmark_partial_context,
        console_errors,
        page_errors,
        label="article-bookmark-partial",
    )
    bookmark_partial_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(bookmark_partial_page)
    bookmark_partial_row = bookmark_partial_page.get_by_role(
        "link", name=CRB_TITLE, exact=True
    ).locator("xpath=ancestor::article[1]")
    expect(bookmark_partial_row).to_contain_text("completed", timeout=30_000)
    expect(bookmark_partial_row).not_to_contain_text("Bookmarked")
    bookmark_partial_page.evaluate(
        """
        () => {
          const originalFetch = window.fetch.bind(window);
          let delayed = false;
          window.fetch = (...args) => {
            const input = args[0];
            const url = typeof input === "string" ? input : input.url;
            if (!delayed && new URL(url, window.location.href).pathname === "/learning/bookmarks") {
              delayed = true;
              return new Promise((resolve, reject) => {
                window.setTimeout(() => originalFetch(...args).then(resolve, reject), 900);
              });
            }
            return originalFetch(...args);
          };
        }
        """
    )
    bookmark_retry = bookmark_partial_page.get_by_role(
        "button", name="Retry saved status", exact=True
    )
    bookmark_retry.click()
    bookmark_availability = bookmark_partial_page.get_by_test_id(
        "article-badge-availability"
    )
    expect(bookmark_retry).to_be_disabled()
    expect(bookmark_availability).to_have_attribute("aria-busy", "true")
    expect(bookmark_availability).to_contain_text(
        "Saved status retry in progress. Article rows remain unavailable."
    )
    expect(bookmark_availability).to_be_focused()
    _require_visible_focus(bookmark_availability, "Saved badge retry progress")
    expect(bookmark_partial_row).to_contain_text("Bookmarked", timeout=30_000)
    expect(bookmark_availability).to_contain_text("Saved status is available.")
    expect(bookmark_availability).to_be_focused()
    _require_visible_focus(bookmark_availability, "Saved badge retry result")
    checks["article_bookmark_failure_preserves_learning_state"] = True
    bookmark_partial_context.close()

    capture_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    _install_network_guard(capture_context, blocked_external)
    capture_page = _new_observed_page(
        capture_context, console_errors, page_errors, label="article-capture-reload"
    )
    capture_observer = _new_observed_page(
        capture_context, console_errors, page_errors, label="article-capture-observer"
    )
    for capture_target in (capture_page, capture_observer):
        capture_target.goto(f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded")
        _wait_for_application_shell(capture_target)
        expect(capture_target.get_by_role("link", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
    capture_page.evaluate(
        """
        ([attentionId, attentionTitle, researchId, researchTitle]) => {
          localStorage.setItem("scientific-spaces-study-session-v1", JSON.stringify({
            version: 1,
            active_article_id: attentionId,
            updated_at: "2026-09-05T01:00:00.000Z",
            items: [
              {
                article_id: attentionId,
                title: attentionTitle,
                section_id: null,
                added_at: "2026-09-05T01:00:00.000Z",
              },
              {
                article_id: researchId,
                title: researchTitle,
                section_id: null,
                added_at: "2026-09-05T01:01:00.000Z",
              },
            ],
          }));
        }
        """,
        [ATTENTION_ARTICLE_ID, ATTENTION_TITLE, RESEARCH_ARTICLE_ID, RESEARCH_TITLE],
    )
    expect(capture_observer.get_by_test_id("article-session-capture")).to_contain_text(
        "2/20 in session", timeout=30_000
    )
    capture_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    ).check()
    capture_page_url = capture_page.url
    capture_page.get_by_role("button", name="Add selected to session", exact=True).click()
    capture_payload = capture_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        [item["article_id"] for item in capture_payload["items"]]
        == [ATTENTION_ARTICLE_ID, RESEARCH_ARTICLE_ID, CRB_ARTICLE_ID]
        and capture_payload["active_article_id"] == ATTENTION_ARTICLE_ID,
        f"Article capture did not reload or preserve the current Session: {capture_payload}",
    )
    _require(capture_page.url == capture_page_url, "Article capture auto-navigated")
    expect(
        capture_page.get_by_role("link", name=CRB_TITLE, exact=True).locator(
            "xpath=ancestor::article[1]"
        )
    ).to_contain_text("In session")
    expect(
        capture_observer.get_by_role("link", name=CRB_TITLE, exact=True).locator(
            "xpath=ancestor::article[1]"
        )
    ).to_contain_text("In session", timeout=30_000)
    capture_feedback = capture_page.get_by_test_id("article-session-capture-feedback")
    expect(capture_feedback).to_be_focused()
    expect(capture_feedback).to_contain_text("Focused Session contains 3 of 20 Articles.")
    capture_observer.evaluate(
        "localStorage.removeItem('scientific-spaces-study-session-v1')"
    )
    capture_region = capture_page.get_by_test_id("article-session-capture")
    expect(capture_region).to_contain_text("0/20 in session", timeout=30_000)
    expect(capture_feedback).to_have_text("")
    expect(capture_region).to_be_focused()
    _require_visible_focus(capture_region, "Article capture region after external queue change")
    checks["article_capture_reloads_queue_and_preserves_active"] = True
    checks["article_capture_same_and_cross_tab_refresh"] = True
    checks["article_capture_external_change_invalidates_feedback"] = True
    capture_context.close()

    write_failure_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    write_failure_context.add_init_script(
        script="""
        const originalSetItem = Storage.prototype.setItem;
        Storage.prototype.setItem = function (key, value) {
          if (key === "scientific-spaces-study-session-v1") {
            throw new Error("intentional Article capture write failure");
          }
          return originalSetItem.call(this, key, value);
        };
        """
    )
    _install_network_guard(write_failure_context, blocked_external)
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="article-capture-write-failure",
    )
    write_failure_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(write_failure_page)
    write_failure_checkbox = write_failure_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    write_failure_checkbox.check()
    write_failure_page.get_by_role(
        "button", name="Add selected to session", exact=True
    ).click()
    write_failure_feedback = write_failure_page.get_by_test_id(
        "article-session-capture-feedback"
    )
    expect(write_failure_feedback).to_be_focused()
    expect(write_failure_feedback).to_contain_text(
        "Focused Session storage failed. No changes were saved. Selection is ready to retry."
    )
    expect(write_failure_checkbox).to_be_checked()
    _require(
        write_failure_page.evaluate(
            "localStorage.getItem('scientific-spaces-study-session-v1')"
        )
        is None,
        "failed Article capture persisted a Session",
    )
    checks["article_capture_write_failure_preserves_selection"] = True
    write_failure_context.close()

    full_capture_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    full_capture_items = [
        {
            "article_id": CRB_ARTICLE_ID,
            "title": CRB_TITLE,
            "section_id": None,
            "added_at": "2026-09-05T02:00:00.000Z",
        },
        *[
            {
                "article_id": f"article-capture-capacity-{index}",
                "title": f"Article capture capacity fixture {index}",
                "section_id": None,
                "added_at": f"2026-09-05T02:{index + 1:02d}:00.000Z",
            }
            for index in range(19)
        ],
    ]
    full_capture_payload = json.dumps(
        {
            "version": 1,
            "active_article_id": CRB_ARTICLE_ID,
            "updated_at": "2026-09-05T02:20:00.000Z",
            "items": full_capture_items,
        },
        ensure_ascii=False,
    )
    full_capture_context.add_init_script(
        script=f"localStorage.setItem('scientific-spaces-study-session-v1', {json.dumps(full_capture_payload)});"
    )
    _install_network_guard(full_capture_context, blocked_external)
    full_capture_page = _new_observed_page(
        full_capture_context,
        console_errors,
        page_errors,
        label="article-capture-full",
    )
    full_capture_page.goto(f"{FRONTEND_URL}/articles", wait_until="domcontentloaded")
    _wait_for_application_shell(full_capture_page)
    expect(full_capture_page.get_by_role("link", name=CRB_TITLE, exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(full_capture_page.get_by_test_id("article-pagination")).to_have_count(0)
    full_capture_page.get_by_role("button", name="Select page", exact=True).click()
    expect(full_capture_page.get_by_test_id("article-session-capture")).to_contain_text(
        "3 selected on this page"
    )
    full_capture_page.get_by_role(
        "button", name="Add selected to session", exact=True
    ).click()
    full_feedback = full_capture_page.get_by_test_id("article-session-capture-feedback")
    expect(full_feedback).to_be_focused()
    expect(full_feedback).to_contain_text(
        "0 added; 1 already present; 0 invalid; 2 omitted by capacity."
    )
    expect(full_capture_page.get_by_test_id("article-session-capture")).to_contain_text(
        "2 selected on this page"
    )
    persisted_full_capture = full_capture_page.evaluate(
        "localStorage.getItem('scientific-spaces-study-session-v1')"
    )
    _require(
        persisted_full_capture == full_capture_payload,
        "duplicate/full Article capture rewrote the unchanged queue",
    )
    checks["article_capture_duplicate_and_capacity_truth"] = True
    full_capture_context.close()

    unavailable_context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(unavailable_context, blocked_external)
    unavailable_expectations = {
        endpoint: _declare_expected_http_errors(
            console_errors,
            label="session-storage-unavailable",
            page_url=f"{FRONTEND_URL}/library",
            source_url=f"{BROWSER_API_URL}/learning/{endpoint}",
        )
        for endpoint in ("state", "bookmarks", "stats")
    }

    def unavailable_handler(endpoint: str):
        def fulfill(route) -> None:
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=unavailable_page,
                expectation_ids=unavailable_expectations[endpoint],
                body='{"detail":"intentional P3-020 unavailable state"}',
            )

        return fulfill

    for endpoint in ("state", "bookmarks", "stats"):
        unavailable_context.route(
            re.compile(rf".*/learning/{endpoint}$"),
            unavailable_handler(endpoint),
            times=1,
        )
    unavailable_page = unavailable_context.new_page()
    _mark_expected_context_page(unavailable_context, unavailable_page)
    unavailable_page.on(
        "console",
        lambda message: console_errors.capture(
            message, label="session-storage-unavailable", page=unavailable_page
        ),
    )
    console_errors.observe_http_errors(unavailable_page, label="session-storage-unavailable")
    unavailable_page.on(
        "pageerror",
        lambda error: _capture_page_error(
            page_errors, "session-storage-unavailable", unavailable_page, error
        ),
    )
    unavailable_page.goto(f"{FRONTEND_URL}/library", wait_until="domcontentloaded")
    _wait_for_application_shell(unavailable_page)
    expect(unavailable_page.get_by_test_id("saved-library-unavailable")).to_be_visible(
        timeout=30_000
    )
    expect(unavailable_page.get_by_test_id("saved-library-unavailable")).not_to_contain_text(
        CRB_ARTICLE_ID
    )
    saved_retry = unavailable_page.get_by_role("button", name="Retry", exact=True)
    saved_retry.focus()
    saved_retry.press("Enter")
    saved_summary = unavailable_page.get_by_test_id("saved-library-result-summary")
    expect(saved_summary).to_be_focused(timeout=30_000)
    _require_visible_focus(saved_summary, "Saved Library retry result")
    expect(unavailable_page.get_by_test_id("saved-library-unavailable")).to_have_count(0)
    _wait_for_declared_http_errors(
        unavailable_page,
        console_errors,
        expectation_ids=tuple(
            expectation_id
            for endpoint_ids in unavailable_expectations.values()
            for expectation_id in endpoint_ids
        ),
    )
    checks["saved_library_unavailable_state"] = True
    unavailable_context.close()

    recovered_session_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    recovered_session_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": "missing-article",
              "updated_at": "invalid timestamp",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": "regularity",
                      "added_at": "2026-08-31T02:00:00.000Z",
                  },
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-08-31T02:01:00.000Z",
                  },
                  {
                      "article_id": "raw-title-id",
                      "title": "raw-title-id",
                      "section_id": None,
                      "added_at": "2026-08-31T02:02:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(recovered_session_context, blocked_external)
    recovered_session_page = _new_observed_page(
        recovered_session_context,
        console_errors,
        page_errors,
        label="dashboard-storage-recovery",
    )
    recovered_session_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(recovered_session_page)
    recovered_dashboard_session = recovered_session_page.get_by_test_id(
        "dashboard-study-session"
    )
    expect(recovered_dashboard_session).to_have_attribute("data-state", "recovered")
    expect(recovered_dashboard_session).to_contain_text(CRB_TITLE)
    expect(recovered_dashboard_session).not_to_contain_text("raw-title-id")
    _wait_for_page_requests_to_settle(recovered_session_page, console_errors)
    recovered_session_page.close()
    recovered_session_page = _new_observed_page(
        recovered_session_context,
        console_errors,
        page_errors,
        label="session-storage-recovery",
    )
    recovered_session_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(recovered_session_page)
    expect(
        recovered_session_page.get_by_text(
            re.compile(r"^The saved queue was recovered safely\.")
        )
    ).to_be_visible()
    expect(recovered_session_page.get_by_test_id("study-session-summary")).to_contain_text(
        "1 Article"
    )
    expect(recovered_session_page.get_by_test_id("study-session-item")).to_contain_text(CRB_TITLE)
    expect(recovered_session_page.get_by_test_id("focused-study-session")).not_to_contain_text(
        "raw-title-id"
    )
    recovered_session_page.close()
    recovered_session_page = _new_observed_page(
        recovered_session_context,
        console_errors,
        page_errors,
        label="concept-storage-recovery",
    )
    recovered_session_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(recovered_session_page)
    recovered_concept_set = recovered_session_page.get_by_test_id("concept-study-set")
    expect(recovered_concept_set).to_be_visible(timeout=30_000)
    expect(recovered_concept_set.get_by_role("status")).to_contain_text(
        "recovered valid entries from browser storage"
    )
    checks["study_session_stale_record_recovery"] = True
    checks["concept_study_set_storage_recovery"] = True
    _wait_for_page_requests_to_settle(recovered_session_page, console_errors)
    recovered_session_context.close()

    read_failure_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    read_failure_context.add_init_script(
        script="""
        const originalGetItem = Storage.prototype.getItem;
        const originalSetItem = Storage.prototype.setItem;
        window.__p3026ReadFailureSessionWrites = 0;
        Storage.prototype.getItem = function (key) {
          if (key === "scientific-spaces-study-session-v1") {
            throw new Error("intentional study session read failure");
          }
          return originalGetItem.call(this, key);
        };
        Storage.prototype.setItem = function (key, value) {
          if (key === "scientific-spaces-study-session-v1") {
            window.__p3026ReadFailureSessionWrites += 1;
          }
          return originalSetItem.call(this, key, value);
        };
        """
    )
    _install_network_guard(read_failure_context, blocked_external)
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="dashboard-storage-read-failure",
    )
    read_failure_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(read_failure_page)
    expect(read_failure_page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "unavailable"
    )
    expect(read_failure_page.get_by_role("heading", name="Learning Overview", exact=True)).to_be_visible()
    _wait_for_page_requests_to_settle(read_failure_page, console_errors)
    read_failure_page.close()
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="articles-storage-read-failure",
    )
    read_failure_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(read_failure_page)
    expect(
        read_failure_page.get_by_role("link", name=CRB_TITLE, exact=True)
    ).to_be_visible(timeout=30_000)
    unavailable_capture = read_failure_page.get_by_test_id("article-session-capture")
    expect(unavailable_capture).to_contain_text("Focused Session unavailable")
    _require(
        "0/20 in session" not in unavailable_capture.inner_text(),
        "Article capture falsely reported an empty Session after a storage read failure",
    )
    expect(
        unavailable_capture.get_by_role("button", name="Retry session status", exact=True)
    ).to_be_visible()
    unavailable_checkbox = read_failure_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    unavailable_checkbox.check()
    unavailable_capture.get_by_role(
        "button", name="Add selected to session", exact=True
    ).click()
    unavailable_feedback = read_failure_page.get_by_test_id(
        "article-session-capture-feedback"
    )
    expect(unavailable_feedback).to_be_focused()
    expect(unavailable_feedback).to_contain_text(
        "Browser-local storage is unavailable. No Articles were added."
    )
    expect(unavailable_checkbox).to_be_checked()
    _require(
        read_failure_page.evaluate("window.__p3026ReadFailureSessionWrites") == 0,
        "Article capture wrote Session storage after its read failed",
    )
    checks["article_session_storage_read_unavailable"] = True
    read_failure_page.close()
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="session-storage-read-failure",
    )
    read_failure_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(read_failure_page)
    expect(read_failure_page.get_by_test_id("study-session-unavailable")).to_be_visible()
    _wait_for_page_requests_to_settle(read_failure_page, console_errors)
    read_failure_page.close()
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="concept-storage-read-failure",
    )
    read_failure_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(read_failure_page)
    unavailable_concept_set = read_failure_page.get_by_test_id("concept-study-set")
    expect(unavailable_concept_set).to_be_visible(timeout=30_000)
    expect(unavailable_concept_set.get_by_role("alert")).to_contain_text(
        "Browser-local Focused Session storage is unavailable."
    )
    expect(
        unavailable_concept_set.get_by_role(
            "button", name="Add eligible Articles", exact=True
        )
    ).to_be_disabled()
    checks["study_session_storage_unavailable"] = True
    checks["concept_study_set_storage_unavailable"] = True
    read_failure_context.close()

    write_failure_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    write_failure_context.add_init_script(
        script=f"""
        const studySessionKey = "scientific-spaces-study-session-v1";
        const originalSetItem = Storage.prototype.setItem;
        originalSetItem.call(
          localStorage,
          studySessionKey,
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": ATTENTION_ARTICLE_ID,
              "updated_at": "2026-08-31T02:00:00.000Z",
              "items": [
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-08-31T02:00:00.000Z",
                  },
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": "regularity",
                      "added_at": "2026-08-31T02:01:00.000Z",
                  },
                  {
                      "article_id": "p3-025-advance-target",
                      "title": "Guided advance target",
                      "section_id": None,
                      "added_at": "2026-08-31T02:02:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        Storage.prototype.setItem = function (key, value) {{
          if (key === studySessionKey) {{
            throw new Error("intentional study session write failure");
          }}
          return originalSetItem.call(this, key, value);
        }};
        """
    )
    _install_network_guard(write_failure_context, blocked_external)
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="session-storage-write-failure",
    )
    write_failure_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(write_failure_page)
    crb_write_failure_item = write_failure_page.get_by_test_id("study-session-item").filter(
        has_text=CRB_TITLE
    ).first
    crb_write_failure_item.get_by_role(
        "button", name=f"Move {CRB_TITLE} up", exact=True
    ).click()
    expect(write_failure_page.get_by_test_id("study-session-item").first).to_contain_text(CRB_TITLE)
    expect(
        write_failure_page.get_by_role("status").filter(
            has_text="browser-local storage could not save it"
        )
    ).to_be_visible()
    non_boundary_item = write_failure_page.get_by_test_id("study-session-item").filter(
        has_text="Guided advance target"
    ).first
    non_boundary_move = non_boundary_item.get_by_role(
        "button", name="Move Guided advance target up", exact=True
    )
    non_boundary_move.focus()
    non_boundary_move.press("Enter")
    expect(non_boundary_move).to_be_focused()
    _require_visible_focus(non_boundary_move, "Focused Session non-boundary reorder")
    write_failure_page.close()
    write_failure_context.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-025-write-failure-timer",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-09-04T06:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    write_failure_context.route(
        re.compile(r".*/learning/sessions/p3-025-write-failure-timer/end$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-025-write-failure-timer",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-09-04T06:00:00Z",
                    "ended_at": "2026-09-04T06:01:00Z",
                    "duration_seconds": 60,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="guided-advance-storage-write-failure",
    )
    write_failure_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(write_failure_page)
    write_failure_completion = write_failure_page.get_by_test_id(
        "focused-session-completion"
    )
    write_failure_mark = write_failure_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(write_failure_mark).to_be_enabled(timeout=30_000)
    write_failure_mark.focus()
    write_failure_mark.press("Enter")
    expect(write_failure_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    expect(write_failure_completion).to_be_focused(timeout=30_000)
    write_failure_url = write_failure_page.url
    write_failure_advance = write_failure_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    )
    write_failure_advance.focus()
    write_failure_advance.press("Enter")
    expect(write_failure_completion.get_by_role("alert")).to_contain_text(
        "Navigation was cancelled", timeout=30_000
    )
    expect(write_failure_completion).to_be_focused(timeout=30_000)
    _require(
        write_failure_page.url == write_failure_url,
        "guided advance navigated after browser-local pointer persistence failed",
    )
    checks["focused_session_advance_write_failure"] = True
    write_failure_page.close()
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="concept-storage-write-failure",
    )
    write_failure_page.goto(
        f"{FRONTEND_URL}/graph?node_id=concept%3Aresearch", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(write_failure_page)
    write_failure_concept_set = write_failure_page.get_by_test_id("concept-study-set")
    expect(write_failure_concept_set).to_be_visible(timeout=30_000)
    write_failure_concept_set.get_by_role(
        "button", name="Add eligible Articles", exact=True
    ).click()
    expect(write_failure_concept_set.get_by_role("status")).to_contain_text(
        "Focused Session storage failed. No saved change is being reported."
    )
    checks["study_session_storage_write_failure"] = True
    checks["concept_study_set_storage_write_failure"] = True
    _wait_for_page_requests_to_settle(write_failure_page, console_errors)
    write_failure_context.close()

    timer_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    timer_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T06:00:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:00:00.000Z",
                  },
                  {
                      "article_id": RESEARCH_ARTICLE_ID,
                      "title": RESEARCH_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:01:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(timer_context, blocked_external)
    timer_record = {
        "session_id": "p3-025-retry-timer",
        "article_id": CRB_ARTICLE_ID,
        "started_at": "2026-09-04T06:00:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }
    timer_end_attempts = {"count": 0}
    timer_end_failure = _declare_expected_http_errors(
        console_errors,
        label="focused-session-timer-reconciliation",
        page_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        source_url=(
            f"{BROWSER_API_URL}/learning/sessions/p3-025-retry-timer/end"
        ),
        method="PUT",
    )

    def fulfill_timer_collection(route) -> None:
        payload = timer_record if route.request.method == "POST" else {
            "items": [timer_record],
            "total": 1,
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    def fulfill_timer_end(route) -> None:
        timer_end_attempts["count"] += 1
        if timer_end_attempts["count"] == 1:
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=timer_page,
                expectation_ids=timer_end_failure,
                body='{"detail":"intentional uncertain timer end"}',
            )
            return
        timer_record["ended_at"] = "2026-09-04T06:02:00Z"
        timer_record["duration_seconds"] = 120
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(timer_record),
        )

    timer_context.route(re.compile(r".*/learning/sessions$"), fulfill_timer_collection)
    timer_context.route(
        re.compile(r".*/learning/sessions/p3-025-retry-timer/end$"),
        fulfill_timer_end,
    )
    timer_console_start = len(console_errors)
    timer_page = _new_observed_page(
        timer_context,
        console_errors,
        page_errors,
        label="focused-session-timer-reconciliation",
    )
    timer_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(timer_page)
    timer_completion = timer_page.get_by_test_id("focused-session-completion")
    timer_mark_complete = timer_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(timer_mark_complete).to_be_enabled(timeout=30_000)
    timer_mark_complete.focus()
    timer_mark_complete.press("Enter")
    expect(timer_page.get_by_test_id("focused-session-timer-warning")).to_contain_text(
        "exact timer is still open", timeout=30_000
    )
    expect(timer_completion).to_be_focused(timeout=30_000)
    _require(
        timer_end_attempts["count"] == 1,
        f"uncertain timer end was replayed without user action: {timer_end_attempts}",
    )
    timer_retry = timer_completion.get_by_role("button", name="Retry timer check", exact=True)
    _install_mutation_response_gate(timer_page, "/learning/sessions", "GET")
    timer_retry.focus()
    timer_retry.press("Enter")
    timer_page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    timer_heading = timer_page.get_by_role("heading", name=CRB_TITLE, exact=True)
    timer_heading.focus()
    _release_mutation_response_gate(timer_page)
    expect(timer_page.get_by_test_id("focused-session-timer-warning")).to_have_count(
        0, timeout=30_000
    )
    expect(timer_completion).to_contain_text("Reader timer end confirmed")
    expect(timer_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(timer_heading, "Reader timer retry newer focus owner")
    _restore_mutation_response_gate(timer_page)
    _require(
        timer_end_attempts["count"] == 2,
        f"confirmed-open timer retry did not perform exactly one end request: {timer_end_attempts}",
    )
    timer_advance_transition = _declare_expected_route_transition(
        timer_page,
        destination_url=(
            f"{FRONTEND_URL}/articles/{RESEARCH_ARTICLE_ID}?from=%2Fsession"
        ),
    )
    timer_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    ).click()
    research_heading = timer_page.get_by_role("heading", name=RESEARCH_TITLE, exact=True)
    expect(research_heading).to_be_visible(timeout=30_000)
    expect(research_heading).to_be_focused(timeout=30_000)
    _wait_for_page_requests_to_settle(timer_page, console_errors)
    _complete_expected_route_transition(timer_page, timer_advance_transition)
    checks["focused_session_timer_reconciliation"] = True
    _wait_for_declared_http_errors(
        timer_page, console_errors, expectation_ids=timer_end_failure
    )
    timer_context.close()
    expected_timer_console = console_errors[timer_console_start:]
    _require(
        len(expected_timer_console) == 1
        and "status of 503" in expected_timer_console[0],
        f"unexpected timer-reconciliation console output: {expected_timer_console}",
    )

    manual_timer_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    manual_timer_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T06:30:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:30:00.000Z",
                  },
                  {
                      "article_id": RESEARCH_ARTICLE_ID,
                      "title": RESEARCH_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:31:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(manual_timer_context, blocked_external)
    manual_timer_record = {
        "session_id": "p3-025-manual-uncertain-timer",
        "article_id": CRB_ARTICLE_ID,
        "started_at": "2026-09-04T06:30:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }
    manual_timer_gets = {"count": 0}
    manual_timer_ends = {"count": 0}
    manual_timer_read_failure = _declare_expected_http_errors(
        console_errors,
        label="manual-timer-uncertainty",
        page_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        source_url=f"{BROWSER_API_URL}/learning/sessions",
    )
    manual_timer_end_failure = _declare_expected_http_errors(
        console_errors,
        label="manual-timer-uncertainty",
        page_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        source_url=(
            f"{BROWSER_API_URL}/learning/sessions/p3-025-manual-uncertain-timer/end"
        ),
        method="PUT",
    )

    def fulfill_manual_timer_collection(route) -> None:
        if route.request.method == "POST":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(manual_timer_record),
            )
            return
        manual_timer_gets["count"] += 1
        if manual_timer_gets["count"] == 2:
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=manual_timer_page,
                expectation_ids=manual_timer_read_failure,
                body='{"detail":"intentional manual timer readback failure"}',
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"items": [manual_timer_record], "total": 1}),
        )

    def fulfill_manual_timer_end(route) -> None:
        manual_timer_ends["count"] += 1
        if manual_timer_ends["count"] == 1:
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=manual_timer_page,
                expectation_ids=manual_timer_end_failure,
                body='{"detail":"intentional manual timer uncertainty"}',
            )
            return
        manual_timer_record["ended_at"] = "2026-09-04T06:34:00Z"
        manual_timer_record["duration_seconds"] = 240
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(manual_timer_record),
        )

    manual_timer_context.route(
        re.compile(r".*/learning/sessions$"), fulfill_manual_timer_collection
    )
    manual_timer_context.route(
        re.compile(r".*/learning/sessions/p3-025-manual-uncertain-timer/end$"),
        fulfill_manual_timer_end,
    )
    manual_timer_console_start = len(console_errors)
    manual_timer_page = _new_observed_page(
        manual_timer_context,
        console_errors,
        page_errors,
        label="manual-timer-uncertainty",
    )
    manual_timer_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(manual_timer_page)
    manual_end = manual_timer_page.get_by_role("button", name="End session", exact=True)
    expect(manual_end).to_be_enabled(timeout=30_000)
    manual_end.click()
    expect(manual_timer_page.get_by_text("Learning request failed: 503", exact=True)).to_be_visible(
        timeout=30_000
    )
    manual_completion = manual_timer_page.get_by_test_id("focused-session-completion")
    manual_mark = manual_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(manual_mark).to_be_enabled(timeout=30_000)
    manual_mark.press("Enter")
    expect(manual_timer_page.get_by_test_id("focused-session-timer-warning")).to_contain_text(
        "exact timer is still open", timeout=30_000
    )
    _require(
        manual_timer_ends["count"] == 1,
        f"completion blindly replayed an uncertain manual timer end: {manual_timer_ends}",
    )
    manual_retry = manual_completion.get_by_role(
        "button", name="Retry timer check", exact=True
    )
    manual_retry.focus()
    manual_retry.press("Enter")
    expect(manual_timer_page.get_by_test_id("focused-session-timer-warning")).to_have_count(
        0, timeout=30_000
    )
    expect(manual_completion).to_be_focused(timeout=30_000)
    _require_visible_focus(manual_completion, "Reader timer retry result")
    _require(
        manual_timer_ends["count"] == 2,
        f"explicit timer retry did not issue exactly one new end request: {manual_timer_ends}",
    )
    checks["focused_session_manual_timer_uncertainty"] = True
    _wait_for_declared_http_errors(
        manual_timer_page,
        console_errors,
        expectation_ids=manual_timer_read_failure + manual_timer_end_failure,
    )
    manual_timer_context.close()
    expected_manual_timer_console = console_errors[manual_timer_console_start:]
    _require(
        len(expected_manual_timer_console) == 2
        and all("status of 503" in message for message in expected_manual_timer_console),
        f"unexpected manual timer uncertainty console output: {expected_manual_timer_console}",
    )

    uncertain_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    uncertain_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": RESEARCH_ARTICLE_ID,
              "updated_at": "2026-09-04T07:00:00.000Z",
              "items": [
                  {
                      "article_id": RESEARCH_ARTICLE_ID,
                      "title": RESEARCH_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:00:00.000Z",
                  },
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:01:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(uncertain_context, blocked_external)
    uncertain_state = {"completed": False, "put_count": 0}
    uncertain_completion_failure = _declare_expected_http_errors(
        console_errors,
        label="focused-session-completion-reconciliation",
        page_url=f"{FRONTEND_URL}/articles/{RESEARCH_ARTICLE_ID}?from=%2Fsession",
        source_url=f"{BROWSER_API_URL}/learning/state/{RESEARCH_ARTICLE_ID}",
        method="PUT",
    )

    def uncertain_learning_state_payload() -> dict[str, object]:
        completed = bool(uncertain_state["completed"])
        return {
            "article_id": RESEARCH_ARTICLE_ID,
            "status": "completed" if completed else "unread",
            "last_read_at": "2026-09-04T07:02:00Z" if completed else None,
            "completed_at": "2026-09-04T07:02:00Z" if completed else None,
            "read_count": 1 if completed else 0,
            "updated_at": "2026-09-04T07:02:00Z" if completed else None,
        }

    def fulfill_uncertain_state(route) -> None:
        if route.request.method == "PUT":
            uncertain_state["completed"] = True
            uncertain_state["put_count"] += 1
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=uncertain_page,
                expectation_ids=uncertain_completion_failure,
                body='{"detail":"intentional lost completion response"}',
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(uncertain_learning_state_payload()),
        )

    uncertain_context.route(
        re.compile(rf".*/learning/state/{RESEARCH_ARTICLE_ID}$"),
        fulfill_uncertain_state,
    )
    uncertain_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [
                        uncertain_learning_state_payload(),
                        {
                            "article_id": CRB_ARTICLE_ID,
                            "status": "completed",
                            "last_read_at": "2026-09-04T07:00:00Z",
                            "completed_at": "2026-09-04T07:00:00Z",
                            "read_count": 1,
                            "updated_at": "2026-09-04T07:00:00Z",
                        },
                    ],
                    "total": 2,
                }
            ),
        ),
    )
    uncertain_timer = {
        "session_id": "p3-025-uncertain-completion-timer",
        "article_id": RESEARCH_ARTICLE_ID,
        "started_at": "2026-09-04T07:00:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }
    uncertain_context.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(uncertain_timer),
        ),
        times=1,
    )
    uncertain_context.route(
        re.compile(r".*/learning/sessions/p3-025-uncertain-completion-timer/end$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    **uncertain_timer,
                    "ended_at": "2026-09-04T07:03:00Z",
                    "duration_seconds": 180,
                }
            ),
        ),
        times=1,
    )
    uncertain_console_start = len(console_errors)
    uncertain_page = _new_observed_page(
        uncertain_context,
        console_errors,
        page_errors,
        label="focused-session-completion-reconciliation",
    )
    uncertain_page.goto(
        f"{FRONTEND_URL}/articles/{RESEARCH_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(uncertain_page)
    uncertain_completion = uncertain_page.get_by_test_id("focused-session-completion")
    uncertain_mark = uncertain_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(uncertain_mark).to_be_enabled(timeout=30_000)
    uncertain_mark.focus()
    uncertain_mark.press("Enter")
    expect(uncertain_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    expect(uncertain_completion).to_be_focused(timeout=30_000)
    _require(
        uncertain_state["put_count"] == 1,
        f"uncertain completion response caused duplicate writes: {uncertain_state}",
    )
    uncertain_advance = uncertain_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    )
    _install_mutation_response_gate(
        uncertain_page,
        f"/learning/state/{RESEARCH_ARTICLE_ID}",
        "GET",
    )
    uncertain_advance.focus()
    uncertain_advance.press("Enter")
    uncertain_page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    uncertain_page.evaluate(
        """
        () => localStorage.setItem(
          "scientific-spaces-study-session-v1",
          JSON.stringify({
            version: 1,
            active_article_id: null,
            updated_at: new Date().toISOString(),
            items: [],
          }),
        )
        """
    )
    uncertain_heading = uncertain_page.get_by_role(
        "heading", name=RESEARCH_TITLE, exact=True
    )
    uncertain_heading.focus()
    _release_mutation_response_gate(uncertain_page)
    expect(uncertain_completion).to_contain_text(
        "This Article is no longer the active item in the focused session.",
        timeout=30_000,
    )
    expect(uncertain_heading).to_be_focused()
    _require_visible_focus(uncertain_heading, "Reader advance error newer focus owner")
    _restore_mutation_response_gate(uncertain_page)
    checks["focused_session_uncertain_completion_reconciliation"] = True
    _wait_for_declared_http_errors(
        uncertain_page,
        console_errors,
        expectation_ids=uncertain_completion_failure,
    )
    uncertain_context.close()
    expected_uncertain_console = console_errors[uncertain_console_start:]
    _require(
        len(expected_uncertain_console) == 1
        and "status of 503" in expected_uncertain_console[0],
        f"unexpected completion-reconciliation console output: {expected_uncertain_console}",
    )

    race_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    race_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T07:30:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:30:00.000Z",
                  },
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:31:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        window.__p3025CompletionRace = {{ exactGets: 0 }};
        const originalFetch = window.fetch.bind(window);
        window.fetch = async (...args) => {{
          const request = args[0];
          const init = args[1] || {{}};
          const url = typeof request === "string"
            ? request
            : request instanceof URL
              ? request.toString()
              : request && typeof request.url === "string"
                ? request.url
                : String(request);
          const method = String(
            init.method || (request instanceof Request ? request.method : "GET")
          ).toUpperCase();
          const response = await originalFetch(...args);
          if (method === "POST" && url.endsWith("/learning/sessions")) {{
            await new Promise(resolve => setTimeout(resolve, 2000));
          }}
          if (method === "GET" && url.endsWith("/learning/state/{CRB_ARTICLE_ID}")) {{
            window.__p3025CompletionRace.exactGets += 1;
            if (window.__p3025CompletionRace.exactGets > 1) {{
              await new Promise(resolve => setTimeout(resolve, 800));
            }}
          }}
          return response;
        }};
        """
    )
    _install_network_guard(race_context, blocked_external)
    race_state = {"put_count": 0}

    def fulfill_race_state(route) -> None:
        if route.request.method == "PUT":
            race_state["put_count"] += 1
            status = "completed"
        else:
            status = "unread"
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "article_id": CRB_ARTICLE_ID,
                    "status": status,
                    "last_read_at": None,
                    "completed_at": None,
                    "read_count": 0,
                    "updated_at": None,
                }
            ),
        )

    race_context.route(
        re.compile(rf".*/learning/state/{CRB_ARTICLE_ID}$"),
        fulfill_race_state,
    )
    race_sessions: list[dict[str, object]] = []

    def fulfill_race_sessions(route) -> None:
        if route.request.method == "POST":
            request_payload = route.request.post_data_json
            session = {
                "session_id": f"p3-025-race-timer-{len(race_sessions) + 1}",
                "article_id": request_payload["article_id"],
                "started_at": "2026-09-04T07:32:00Z",
                "ended_at": None,
                "duration_seconds": None,
                "source": "reader",
            }
            race_sessions.append(session)
            payload: object = session
        else:
            payload = {"items": race_sessions, "total": len(race_sessions)}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    def fulfill_race_timer_end(route) -> None:
        session_id = route.request.url.rsplit("/", 2)[-2]
        session = next(item for item in race_sessions if item["session_id"] == session_id)
        session["ended_at"] = "2026-09-04T07:33:00Z"
        session["duration_seconds"] = 60
        route.fulfill(status=200, content_type="application/json", body=json.dumps(session))

    race_context.route(re.compile(r".*/learning/sessions$"), fulfill_race_sessions)
    race_context.route(
        re.compile(r".*/learning/sessions/[^/]+/end$"),
        fulfill_race_timer_end,
    )
    race_page = _new_observed_page(
        race_context,
        console_errors,
        page_errors,
        label="focused-session-navigation-race",
    )
    race_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(race_page)
    race_completion = race_page.get_by_test_id("focused-session-completion")
    expect(race_completion).to_be_visible(timeout=30_000)
    expect(race_completion).to_have_attribute("data-state", "preparing", timeout=1_000)
    race_mark = race_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(race_mark).to_be_disabled()
    expect(race_mark).to_be_enabled(timeout=30_000)
    checks["focused_session_initial_readiness_gate"] = True
    race_mark.press("Enter")
    race_next = race_page.get_by_test_id("study-session-reader-navigation").get_by_role(
        "link", name=f"Next in session: {ATTENTION_TITLE}", exact=True
    )
    expect(race_next).to_have_attribute("aria-disabled", "true")
    race_url = race_page.url
    race_next.click(force=True)
    _require(race_page.url == race_url, "manual navigation escaped while completion was pending")
    race_heading = race_page.get_by_role("heading", name=CRB_TITLE, exact=True)
    race_heading.focus()
    expect(race_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    expect(race_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(race_heading, "pending completion newer focus owner")
    expect(race_next).to_have_attribute("aria-disabled", "false")
    _require(
        race_state["put_count"] == 1,
        f"completion did not persist exactly once after the pending-navigation guard: {race_state}",
    )
    race_next_href = str(race_next.get_attribute("href") or "")
    _require(
        race_next_href.startswith(f"/articles/{ATTENTION_ARTICLE_ID}"),
        f"focused-session next route is invalid: {race_next_href}",
    )
    race_next_transition = _declare_expected_route_transition(
        race_page,
        destination_url=f"{FRONTEND_URL}{race_next_href}",
    )
    race_next.click()
    expect(
        race_page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    ).to_be_visible(timeout=30_000)
    expect(race_page.get_by_test_id("focused-session-completion")).to_have_count(0)
    race_session = race_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        race_session["active_article_id"] == CRB_ARTICLE_ID,
        f"manual review navigation changed active state: {race_session}",
    )
    expect(race_page.get_by_test_id("study-session-reader-navigation")).to_contain_text(
        "Review-only view"
    )
    _wait_for_page_requests_to_settle(race_page, console_errors)
    _complete_expected_route_transition(race_page, race_next_transition)
    race_previous = race_page.get_by_test_id("study-session-reader-navigation").get_by_role(
        "link", name=f"Previous in session: {CRB_TITLE}", exact=True
    )
    race_previous_href = str(race_previous.get_attribute("href") or "")
    _require(
        race_previous_href.startswith(f"/articles/{CRB_ARTICLE_ID}"),
        f"focused-session previous route is invalid: {race_previous_href}",
    )
    race_previous_transition = _declare_expected_route_transition(
        race_page,
        destination_url=f"{FRONTEND_URL}{race_previous_href}",
    )
    race_previous.click()
    expect(race_page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
        timeout=30_000
    )
    stale_completion = race_page.get_by_test_id("focused-session-completion")
    stale_mark = stale_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(stale_mark).to_be_enabled(timeout=30_000)
    _wait_for_page_requests_to_settle(race_page, console_errors)
    _complete_expected_route_transition(race_page, race_previous_transition)
    race_page.evaluate(
        """
        const state = JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'));
        state.active_article_id = 'attention-basics';
        state.updated_at = new Date().toISOString();
        localStorage.setItem('scientific-spaces-study-session-v1', JSON.stringify(state));
        """
    )
    stale_mark.click()
    expect(stale_completion.get_by_role("alert")).to_contain_text(
        "no longer the active item", timeout=30_000
    )
    expect(stale_completion).to_be_focused(timeout=30_000)
    expect(stale_completion).to_have_count(1)
    _require(
        race_state["put_count"] == 1,
        f"stale active validation issued another completion write: {race_state}",
    )
    checks["focused_session_manual_navigation_review_only"] = True
    checks["focused_session_navigation_race_guard"] = True
    checks["focused_session_stale_active_failure_focus"] = True
    race_context.close()

    advance_cancel_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    advance_cancel_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T07:45:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:45:00.000Z",
                  },
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:46:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        const originalFetch = window.fetch.bind(window);
        window.fetch = async (...args) => {{
          const request = args[0];
          const init = args[1] || {{}};
          const url = typeof request === "string"
            ? request
            : request instanceof URL
              ? request.toString()
              : request && typeof request.url === "string"
                ? request.url
                : String(request);
          const method = String(
            init.method || (request instanceof Request ? request.method : "GET")
          ).toUpperCase();
          const response = await originalFetch(...args);
          if (method === "GET" && url.endsWith("/learning/state")) {{
            await new Promise(resolve => setTimeout(resolve, 1200));
          }}
          return response;
        }};
        """
    )
    _install_network_guard(advance_cancel_context, blocked_external)
    advance_cancel_state = {
        "article_id": CRB_ARTICLE_ID,
        "status": "completed",
        "last_read_at": "2026-09-04T07:45:00Z",
        "completed_at": "2026-09-04T07:45:30Z",
        "read_count": 1,
        "updated_at": "2026-09-04T07:45:30Z",
    }
    advance_cancel_context.route(
        re.compile(rf".*/learning/state/{CRB_ARTICLE_ID}$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(advance_cancel_state),
        ),
    )
    advance_cancel_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [
                        advance_cancel_state,
                        {
                            "article_id": ATTENTION_ARTICLE_ID,
                            "status": "unread",
                            "last_read_at": None,
                            "completed_at": None,
                            "read_count": 0,
                            "updated_at": None,
                        },
                    ],
                    "total": 2,
                }
            ),
        ),
    )
    advance_cancel_timer = {
        "session_id": "p3-025-cancelled-advance-timer",
        "article_id": CRB_ARTICLE_ID,
        "started_at": "2026-09-04T07:45:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }

    def fulfill_advance_cancel_sessions(route) -> None:
        payload = advance_cancel_timer if route.request.method == "POST" else {
            "items": [advance_cancel_timer],
            "total": 1,
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    def fulfill_advance_cancel_timer_end(route) -> None:
        advance_cancel_timer["ended_at"] = "2026-09-04T07:46:00Z"
        advance_cancel_timer["duration_seconds"] = 60
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(advance_cancel_timer),
        )

    advance_cancel_context.route(
        re.compile(r".*/learning/sessions$"), fulfill_advance_cancel_sessions
    )
    advance_cancel_context.route(
        re.compile(r".*/learning/sessions/p3-025-cancelled-advance-timer/end$"),
        fulfill_advance_cancel_timer_end,
    )
    advance_cancel_page = _new_observed_page(
        advance_cancel_context,
        console_errors,
        page_errors,
        label="focused-session-cancelled-advance",
    )
    advance_cancel_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(advance_cancel_page)
    advance_cancel_completion = advance_cancel_page.get_by_test_id(
        "focused-session-completion"
    )
    advance_cancel_mark = advance_cancel_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(advance_cancel_mark).to_be_enabled(timeout=30_000)
    advance_cancel_mark.click()
    expect(advance_cancel_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    advance_cancel_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    ).click()
    advance_cancel_page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(
        advance_cancel_page.get_by_role(
            "heading", name="Scientific Spaces AI Learning OS", exact=True
        )
    ).to_be_visible(timeout=30_000)
    advance_cancel_page.wait_for_timeout(1800)
    _require(
        advance_cancel_page.url == f"{FRONTEND_URL}/",
        f"stale guided advance overrode newer Dashboard navigation: {advance_cancel_page.url}",
    )
    cancelled_advance_session = advance_cancel_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        cancelled_advance_session["active_article_id"] == CRB_ARTICLE_ID,
        f"stale guided advance rewrote the active queue pointer: {cancelled_advance_session}",
    )
    checks["focused_session_cancelled_advance_guard"] = True
    advance_cancel_context.close()

    completion_retry_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    completion_retry_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T08:00:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T08:00:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(completion_retry_context, blocked_external)
    completion_list_failure = _declare_expected_http_errors(
        console_errors,
        label="focused-session-completion-list-retry",
        page_url=f"{FRONTEND_URL}/session",
        source_url=f"{BROWSER_API_URL}/learning/state",
    )
    completion_retry_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: _fulfill_expected_http_error(
            route,
            console_errors=console_errors,
            page=completion_retry_page,
            expectation_ids=completion_list_failure,
            body='{"detail":"intentional completion-list failure"}',
        ),
        times=1,
    )
    completion_retry_console_start = len(console_errors)
    completion_retry_page = _new_observed_page(
        completion_retry_context,
        console_errors,
        page_errors,
        label="focused-session-completion-list-retry",
    )
    completion_retry_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(completion_retry_page)
    expect(
        completion_retry_page.get_by_text("Completion status is unavailable.", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(completion_retry_page.get_by_test_id("study-session-item")).to_contain_text(
        "Status unavailable"
    )
    expect(completion_retry_page.get_by_test_id("study-session-complete")).to_have_count(0)
    completion_status_retry = completion_retry_page.get_by_role(
        "button", name="Retry status", exact=True
    )
    completion_status_retry.focus()
    completion_status_retry.press("Enter")
    expect(completion_retry_page.get_by_test_id("study-session-complete")).to_be_visible(
        timeout=30_000
    )
    session_completion_status = completion_retry_page.get_by_test_id(
        "study-session-completion-status"
    )
    expect(session_completion_status).to_be_focused()
    _require_visible_focus(session_completion_status, "Focused Session retry result")
    checks["focused_session_completion_status_retry"] = True
    _wait_for_declared_http_errors(
        completion_retry_page,
        console_errors,
        expectation_ids=completion_list_failure,
    )
    completion_retry_context.close()
    expected_completion_retry_console = console_errors[completion_retry_console_start:]
    _require(
        len(expected_completion_retry_console) == 1
        and "status of 503" in expected_completion_retry_console[0],
        f"unexpected completion-list retry console output: {expected_completion_retry_console}",
    )

    full_session_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    full_session_items = [
        {
            "article_id": f"capacity-{index}",
            "title": f"Capacity fixture Article {index}",
            "section_id": None,
            "added_at": f"2026-08-31T03:{index:02d}:00.000Z",
        }
        for index in range(20)
    ]
    full_session_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": "capacity-7",
              "updated_at": "2026-08-31T03:20:00.000Z",
              "items": full_session_items,
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(full_session_context, blocked_external)
    full_session_page = full_session_context.new_page()
    _mark_expected_context_page(full_session_context, full_session_page)
    full_session_page.on(
        "console",
        lambda message: console_errors.capture(
            message, label="session-full-capacity", page=full_session_page
        ),
    )
    console_errors.observe_http_errors(full_session_page, label="session-full-capacity")
    full_session_page.on(
        "pageerror",
        lambda error: _capture_page_error(
            page_errors, "session-full-capacity", full_session_page, error
        ),
    )
    full_session_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(full_session_page)
    full_concept_set = full_session_page.get_by_test_id("concept-study-set")
    expect(full_concept_set).to_be_visible(timeout=30_000)
    expect(full_concept_set.get_by_text("Open Focused Session (20/20)", exact=True)).to_be_visible()
    expect(
        full_concept_set.get_by_role(
            "button", name=f"Add {ATTENTION_TITLE} to study session", exact=True
        )
    ).to_be_disabled()
    full_concept_set.get_by_role("button", name="Add eligible Articles", exact=True).click()
    expect(full_concept_set.get_by_role("status")).to_contain_text(
        "0 added; 0 already present; 0 invalid; 1 omitted by capacity."
    )
    full_session_payload = full_session_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        len(full_session_payload["items"]) == 20
        and full_session_payload["active_article_id"] == "capacity-7",
        f"full Concept Study Set mutation changed the Session: {full_session_payload}",
    )
    checks["concept_study_set_full_capacity"] = True
    full_session_context.close()

    zoom_context = browser.new_context(
        viewport={"width": 720, "height": 450},
        screen={"width": 1440, "height": 900},
        locale="zh-CN",
        reduced_motion="reduce",
    )
    _install_network_guard(zoom_context, blocked_external)
    zoom_page = zoom_context.new_page()
    _mark_expected_context_page(zoom_context, zoom_page)
    zoom_page.on(
        "console",
        lambda message: console_errors.capture(message, label="graph-zoom", page=zoom_page),
    )
    console_errors.observe_http_errors(zoom_page, label="graph-zoom")
    zoom_page.on(
        "pageerror", lambda error: _capture_page_error(page_errors, "graph-zoom", zoom_page, error)
    )
    zoom_page.goto(
        f"{FRONTEND_URL}/graph?unknown=discard&node_id=concept%3Aattention&q=%20Attention%20#unknown",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(zoom_page)
    zoom_page.wait_for_function(
        "() => location.pathname + location.search + location.hash === "
        "'/graph?node_id=concept%3Aattention&q=Attention'"
    )
    zoom_concept_set = zoom_page.get_by_test_id("concept-study-set")
    expect(zoom_concept_set).to_be_visible(timeout=30_000)
    _wait_for_test_id_near_viewport_top(zoom_page, "graph-selected-region")
    zoom_selected_box = zoom_page.get_by_test_id("graph-selected-region").bounding_box()
    _require(
        zoom_selected_box is not None
        and zoom_selected_box["y"] < 200
        and zoom_selected_box["y"] + zoom_selected_box["height"] > 0,
        f"200-percent zoom-equivalent selected detail is below the viewport: {zoom_selected_box}",
    )
    expect(zoom_concept_set.get_by_role("link", name="Explain concept", exact=True)).to_be_visible()
    expect(zoom_concept_set.get_by_role("link", name="Open concept quiz", exact=True)).to_be_visible()
    zoom_metrics = zoom_page.evaluate(
        "({ viewportWidth: window.innerWidth, viewportHeight: window.innerHeight, "
        "screenWidth: window.screen.width, screenHeight: window.screen.height })"
    )
    _require(
        zoom_metrics["screenWidth"] == 1440
        and zoom_metrics["screenHeight"] == 900
        and zoom_metrics["viewportWidth"] == 720
        and zoom_metrics["viewportHeight"] == 450
        and zoom_metrics["screenWidth"] / zoom_metrics["viewportWidth"] == 2
        and zoom_metrics["screenHeight"] / zoom_metrics["viewportHeight"] == 2,
        f"Chromium did not apply the 200-percent zoom-equivalent layout boundary: {zoom_metrics}",
    )
    zoom_concept_box = zoom_concept_set.bounding_box()
    zoom_document_width = _document_width(zoom_page)
    _require(
        zoom_concept_box is not None
        and zoom_concept_box["x"] >= 0
        and zoom_concept_box["x"] + zoom_concept_box["width"] <= zoom_metrics["viewportWidth"],
        f"200-percent display-scale Concept Study Set is clipped: {zoom_concept_box}",
    )
    _require(
        zoom_document_width <= zoom_metrics["viewportWidth"],
        f"200-percent display-scale Graph page overflowed to {zoom_document_width}px",
    )
    for zoom_control in (
        zoom_concept_set.get_by_role("link", name="Explain concept", exact=True),
        zoom_concept_set.get_by_role("link", name="Open concept quiz", exact=True),
        zoom_concept_set.get_by_role("button", name="Add eligible Articles", exact=True),
    ):
        control_box = zoom_control.bounding_box()
        _require(
            control_box is not None
            and zoom_concept_box is not None
            and control_box["x"] >= zoom_concept_box["x"]
            and control_box["x"] + control_box["width"]
            <= zoom_concept_box["x"] + zoom_concept_box["width"],
            f"200-percent zoom-equivalent control is clipped: {control_box}",
        )
    checks["concept_study_set_200_percent_reflow"] = True
    checks["concept_study_set_200_percent_zoom_equivalent"] = True
    zoom_context.close()

    narrow_context = browser.new_context(
        viewport={"width": 320, "height": 640},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    _install_network_guard(narrow_context, blocked_external)
    narrow_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          window.fetch = (...args) => {
            const url = String(args[0]);
            if (url.includes('/graph/summary')) {
              return new Promise(() => {});
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    narrow_page = narrow_context.new_page()
    _mark_expected_context_page(narrow_context, narrow_page)
    narrow_page.on(
        "console",
        lambda message: console_errors.capture(message, label="graph-320", page=narrow_page),
    )
    console_errors.observe_http_errors(narrow_page, label="graph-320")
    narrow_page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "graph-320", narrow_page, error),
    )
    narrow_page.goto(f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded")
    _wait_for_application_shell(narrow_page)
    expect(narrow_page.get_by_text("Loading graph summary...", exact=True)).to_be_visible()
    expect(narrow_page.get_by_test_id("concept-study-set")).to_be_visible(timeout=30_000)
    _wait_for_test_id_near_viewport_top(narrow_page, "graph-selected-region")
    narrow_selected_box = narrow_page.get_by_test_id("graph-selected-region").bounding_box()
    _require(
        narrow_selected_box is not None
        and narrow_selected_box["y"] < 200
        and narrow_selected_box["y"] + narrow_selected_box["height"] > 0,
        f"320px Graph selected detail is below the viewport: {narrow_selected_box}",
    )
    _require(_document_width(narrow_page) <= 320, "320px Graph workspace overflows horizontally")
    checks["graph_selected_detail_320px"] = True
    checks["graph_detail_reachability_with_pending_summary"] = True
    narrow_context.close()

    deep_link_context = browser.new_context(
        viewport={"width": 390, "height": 844},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    _install_network_guard(deep_link_context, blocked_external)
    deep_link_page = _new_observed_page(
        deep_link_context, console_errors, page_errors, label="graph-390-deep-link"
    )
    deep_link_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(deep_link_page)
    deep_link_selected = deep_link_page.get_by_test_id("graph-selected-region")
    expect(deep_link_selected.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(
        timeout=30_000
    )
    _wait_for_test_id_near_viewport_top(deep_link_page, "graph-selected-region")
    deep_link_selected_box = deep_link_selected.bounding_box()
    _require(
        deep_link_selected_box is not None
        and deep_link_selected_box["y"] < 200
        and deep_link_selected_box["y"] + deep_link_selected_box["height"] > 0,
        f"390px deep-linked Graph detail is below the viewport: {deep_link_selected_box}",
    )
    _require(
        _document_width(deep_link_page) <= 390,
        "390px deep-linked Graph workspace overflows horizontally",
    )
    checks["graph_selected_detail_390px_deep_link"] = True
    deep_link_context.close()

    responsive_tutor_response = {
        **markdown_response,
        "answer": (
            f"{markdown_response['answer']}\n\n"
            "## Extended grounded explanation\n\n"
            + "\n\n".join(
                "This local evidence paragraph keeps the scientific explanation readable on narrow screens "
                "while preserving cited context, inline notation $I(\\theta)$, and explicit uncertainty."
                for _ in range(8)
            )
        ),
    }
    responsive_tutor_body = json.dumps(responsive_tutor_response, ensure_ascii=False)
    tutor_workflow_query = urlencode(
        {
            "article_id": CRB_ARTICLE_ID,
            "article_title": CRB_TITLE,
            "return_to": f"/articles/{CRB_ARTICLE_ID}",
        }
    )

    for viewport_width, viewport_height, viewport_label in (
        (1440, 900, "desktop"),
        (390, 844, "mobile"),
        (320, 844, "narrow"),
        (720, 450, "zoom-equivalent"),
    ):
        completion_viewport_context = browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            screen={"width": 1440, "height": 900}
            if viewport_label == "zoom-equivalent"
            else None,
            locale="zh-CN",
            is_mobile=viewport_width <= 390,
            reduced_motion="reduce",
        )
        fail_article_capture_write = viewport_label == "narrow"
        completion_viewport_context.add_init_script(
            script=f"""
            if (!sessionStorage.getItem("p3-026-viewport-seeded")) {{
              localStorage.setItem(
                "scientific-spaces-study-session-v1",
                {json.dumps(json.dumps({
                    "version": 1,
                    "active_article_id": CRB_ARTICLE_ID,
                    "updated_at": "2026-09-04T09:00:00.000Z",
                    "items": [
                        {
                            "article_id": CRB_ARTICLE_ID,
                            "title": CRB_TITLE,
                            "section_id": None,
                            "added_at": "2026-09-04T09:00:00.000Z",
                        },
                        {
                            "article_id": RESEARCH_ARTICLE_ID,
                            "title": RESEARCH_TITLE,
                            "section_id": None,
                            "added_at": "2026-09-04T09:01:00.000Z",
                        },
                    ],
                }, ensure_ascii=False))}
              );
              sessionStorage.setItem("p3-026-viewport-seeded", "true");
            }}
            if ({str(fail_article_capture_write).lower()}) {{
              const originalSetItem = Storage.prototype.setItem;
              Storage.prototype.setItem = function (key, value) {{
                if (key === "scientific-spaces-study-session-v1") {{
                  throw new Error("intentional narrow viewport Article capture failure");
                }}
                return originalSetItem.call(this, key, value);
              }};
            }}
            """
        )
        _install_network_guard(completion_viewport_context, blocked_external)
        viewport_timer = {
            "session_id": f"p3-025-{viewport_label}-timer",
            "article_id": CRB_ARTICLE_ID,
            "started_at": "2026-09-04T09:00:00Z",
            "ended_at": None,
            "duration_seconds": None,
            "source": "reader",
        }
        completion_viewport_context.route(
            re.compile(r".*/learning/sessions$"),
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(viewport_timer),
            ),
            times=1,
        )
        completion_viewport_page = _new_observed_page(
            completion_viewport_context,
            console_errors,
            page_errors,
            label=f"focused-completion-{viewport_label}",
        )
        completion_viewport_page.goto(
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(completion_viewport_page)
        viewport_heading = completion_viewport_page.get_by_role(
            "heading", name=CRB_TITLE, exact=True
        )
        expect(viewport_heading).to_be_visible(timeout=30_000)
        _wait_for_animation_frames(completion_viewport_page, 5)
        _require(
            completion_viewport_page.evaluate("document.activeElement === document.body"),
            f"{viewport_label} hard-loaded guided Reader moved focus during hydration",
        )
        viewport_heading.focus()
        expect(viewport_heading).to_be_focused()
        heading_box = viewport_heading.bounding_box()
        _require(
            heading_box is not None
            and heading_box["y"] < viewport_height
            and heading_box["y"] + heading_box["height"] > 0,
            f"{viewport_label} guided Reader heading does not intersect the viewport: {heading_box}",
        )
        if viewport_width < 1024:
            viewport_outline_link = completion_viewport_page.get_by_role(
                "link", name="Outline", exact=True
            )
            viewport_tools_link = completion_viewport_page.get_by_role(
                "link", name="Reading tools", exact=True
            )
            viewport_outline_link.click()
            viewport_outline_target = completion_viewport_page.locator("#article-outline")
            expect(viewport_outline_target).to_be_focused(timeout=30_000)
            _require_visible_focus(
                viewport_outline_target,
                f"{viewport_label} Reader outline target",
            )
            viewport_tools_link.click()
            viewport_tools_target = completion_viewport_page.locator("#reading-tools")
            expect(viewport_tools_target).to_be_focused(timeout=30_000)
            _require_visible_focus(
                viewport_tools_target,
                f"{viewport_label} Reader tools target",
            )
            viewport_back_link = completion_viewport_page.get_by_role(
                "link", name="Back to article", exact=True
            )
            viewport_back_link.click()
            viewport_article_target = completion_viewport_page.locator("article#article-start")
            expect(viewport_article_target).to_be_focused(timeout=30_000)
            _require_visible_focus(
                viewport_article_target,
                f"{viewport_label} Reader article target",
            )
            checks[f"reader_hash_focus_{viewport_label}_viewport"] = True
        viewport_completion = completion_viewport_page.get_by_test_id(
            "focused-session-completion"
        )
        viewport_completion.scroll_into_view_if_needed()
        completion_box = viewport_completion.bounding_box()
        _require(
            completion_box is not None
            and completion_box["x"] >= 0
            and completion_box["x"] + completion_box["width"] <= viewport_width,
            f"{viewport_label} completion region is horizontally clipped: {completion_box}",
        )
        for action_name in ("Mark Article complete", "Open next unfinished Article"):
            action_box = viewport_completion.get_by_role(
                "button", name=action_name, exact=True
            ).bounding_box()
            _require(
                action_box is not None
                and completion_box is not None
                and action_box["x"] >= completion_box["x"]
                and action_box["x"] + action_box["width"]
                <= completion_box["x"] + completion_box["width"],
                f"{viewport_label} completion action is clipped: {action_box}",
            )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} focused Reader overflows horizontally",
        )
        viewport_mark = viewport_completion.get_by_role(
            "button", name="Mark Article complete", exact=True
        )
        expect(viewport_mark).to_be_enabled(timeout=30_000)
        viewport_heading.focus()
        expect(viewport_heading).to_be_focused()
        completion_viewport_page.keyboard.press("Tab")
        expect(viewport_mark).to_be_focused()
        checks[f"focused_session_completion_{viewport_label}_viewport"] = True

        if fail_article_capture_write:
            completion_viewport_page.evaluate(
                "localStorage.removeItem('scientific-spaces-study-session-v1')"
            )

        completion_viewport_page.goto(
            f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
        )
        _wait_for_application_shell(completion_viewport_page)
        viewport_first_article = completion_viewport_page.get_by_role(
            "link", name=CRB_TITLE, exact=True
        )
        expect(viewport_first_article).to_be_visible(timeout=30_000)
        _wait_for_animation_frames(completion_viewport_page, 3)
        _require(
            completion_viewport_page.evaluate("window.scrollY") == 0,
            f"{viewport_label} Article discovery did not begin at the top of the page",
        )
        first_article_box = viewport_first_article.bounding_box()
        _require(
            first_article_box is not None
            and first_article_box["y"] < viewport_height
            and first_article_box["y"] + first_article_box["height"] > 0,
            f"{viewport_label} first Article title is outside the initial viewport: "
            f"{first_article_box}",
        )
        if viewport_width <= 390:
            first_preview_box = completion_viewport_page.get_by_test_id(
                "article-preview"
            ).first.bounding_box()
            _require(
                first_preview_box is not None
                and first_preview_box["y"] < viewport_height
                and first_preview_box["y"] + first_preview_box["height"] > 0,
                f"{viewport_label} first Article preview is outside the initial viewport: "
                f"{first_preview_box}",
            )
        checks[f"article_discovery_initial_result_{viewport_label}_viewport"] = True
        viewport_capture = completion_viewport_page.get_by_test_id(
            "article-session-capture"
        )
        viewport_capture.scroll_into_view_if_needed()
        viewport_capture_box = viewport_capture.bounding_box()
        _require(
            viewport_capture_box is not None
            and viewport_capture_box["x"] >= 0
            and viewport_capture_box["x"] + viewport_capture_box["width"]
            <= viewport_width,
            f"{viewport_label} Article capture region is horizontally clipped: "
            f"{viewport_capture_box}",
        )
        for role, name in (
            ("button", "Select page"),
            ("link", "Open Focused Session"),
        ):
            control_box = completion_viewport_page.get_by_role(
                role, name=name, exact=True
            ).bounding_box()
            _require(
                control_box is not None
                and viewport_capture_box is not None
                and control_box["x"] >= viewport_capture_box["x"]
                and control_box["x"] + control_box["width"]
                <= viewport_capture_box["x"] + viewport_capture_box["width"],
                f"{viewport_label} Article capture control is clipped: {control_box}",
            )
        viewport_checkbox = completion_viewport_page.get_by_role(
            "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
        )
        viewport_select_page = completion_viewport_page.get_by_role(
            "button", name="Select page", exact=True
        )
        expect(viewport_checkbox).not_to_be_checked()
        expect(viewport_select_page).to_be_enabled()
        expect(
            completion_viewport_page.get_by_role(
                "button", name="Clear selection", exact=True
            )
        ).to_have_count(0)
        expect(
            completion_viewport_page.get_by_role(
                "button", name="Add selected to session", exact=True
            )
        ).to_have_count(0)
        checkbox_box = viewport_checkbox.bounding_box()
        _require(
            checkbox_box is not None
            and checkbox_box["x"] >= 0
            and checkbox_box["x"] + checkbox_box["width"] <= viewport_width,
            f"{viewport_label} Article capture checkbox is clipped: {checkbox_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Article capture workspace overflows horizontally",
        )
        _focus_via_tab(completion_viewport_page, viewport_checkbox)
        expect(viewport_checkbox).to_be_focused()
        viewport_checkbox.press("Space")
        expect(viewport_checkbox).to_be_checked()
        viewport_clear = completion_viewport_page.get_by_role(
            "button", name="Clear selection", exact=True
        )
        viewport_add = completion_viewport_page.get_by_role(
            "button", name="Add selected to session", exact=True
        )
        expect(viewport_clear).to_be_enabled()
        expect(viewport_add).to_be_enabled()
        _focus_via_tab(completion_viewport_page, viewport_clear)
        viewport_clear.press("Enter")
        expect(viewport_capture).to_be_focused()
        _require_visible_focus(
            viewport_capture,
            f"{viewport_label} Article capture after clearing selection",
        )
        expect(viewport_checkbox).not_to_be_checked()
        viewport_checkbox.press("Space")
        expect(viewport_checkbox).to_be_checked()
        viewport_add = completion_viewport_page.get_by_role(
            "button", name="Add selected to session", exact=True
        )
        completion_viewport_page.keyboard.press("Shift+Tab")
        expect(
            completion_viewport_page.get_by_role(
                "link", name="Open Focused Session", exact=True
            )
        ).to_be_focused()
        completion_viewport_page.keyboard.press("Shift+Tab")
        expect(viewport_add).to_be_focused()
        completion_viewport_page.keyboard.press("Enter")
        viewport_feedback = completion_viewport_page.get_by_test_id(
            "article-session-capture-feedback"
        )
        expect(viewport_feedback).to_be_focused()
        expect(viewport_feedback).to_have_attribute("aria-live", "polite")
        expect(viewport_feedback).to_have_attribute("aria-atomic", "true")
        if fail_article_capture_write:
            expect(viewport_feedback).to_contain_text(
                "Focused Session storage failed. No changes were saved. Selection is ready to retry."
            )
            expect(viewport_checkbox).to_be_checked()
        else:
            expect(viewport_feedback).to_contain_text(
                "0 added; 1 already present; 0 invalid; 0 omitted by capacity."
            )
        _require_visible_focus(
            viewport_feedback, f"{viewport_label} Article capture feedback"
        )
        feedback_box = viewport_feedback.bounding_box()
        _require(
            feedback_box is not None
            and feedback_box["x"] >= 0
            and feedback_box["x"] + feedback_box["width"] <= viewport_width
            and feedback_box["y"] < viewport_height
            and feedback_box["y"] + feedback_box["height"] > 0,
            f"{viewport_label} Article capture feedback is clipped or off-screen: "
            f"{feedback_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Article capture feedback caused horizontal overflow",
        )
        checks[f"article_session_capture_{viewport_label}_viewport"] = True
        checks[f"article_session_capture_{viewport_label}_keyboard_feedback"] = True

        completion_viewport_context.route(
            re.compile(r".*/tutor/ask$"),
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=responsive_tutor_body,
            ),
            times=1,
        )
        completion_viewport_page.goto(
            f"{FRONTEND_URL}/tutor?{tutor_workflow_query}",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(completion_viewport_page)
        expect(
            completion_viewport_page.get_by_role(
                "heading", name="AI Research Tutor", exact=True
            )
        ).to_be_visible(timeout=30_000)
        viewport_question = completion_viewport_page.get_by_label("Question")
        viewport_question.fill("Explain the CRB evidence for this responsive check")
        viewport_ask = completion_viewport_page.get_by_role(
            "button", name="Ask tutor", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_ask)
        viewport_ask.press("Enter")
        viewport_result = completion_viewport_page.get_by_test_id("tutor-result")
        expect(viewport_result).to_be_focused(timeout=30_000)
        expect(
            completion_viewport_page.get_by_test_id("tutor-request-status")
        ).to_have_text("Tutor answer ready.")
        _require_visible_focus(
            viewport_result, f"{viewport_label} Tutor answer result"
        )
        result_box = viewport_result.bounding_box()
        _require(
            result_box is not None
            and result_box["x"] >= 0
            and result_box["x"] + result_box["width"] <= viewport_width
            and result_box["y"] < viewport_height
            and result_box["y"] + result_box["height"] > 0,
            f"{viewport_label} Tutor answer is clipped or off-screen: {result_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Tutor answer caused horizontal overflow",
        )

        viewport_quiz_mode = completion_viewport_page.get_by_role(
            "button", name="Quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_quiz_mode)
        viewport_quiz_mode.press("Enter")
        completion_viewport_page.get_by_label("Prompt").fill("CRB")
        viewport_generate = completion_viewport_page.get_by_role(
            "button", name="Generate quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_generate)
        viewport_generate.press("Enter")
        viewport_quiz = completion_viewport_page.get_by_test_id(
            "tutor-quiz-workspace"
        )
        expect(viewport_quiz).to_be_focused(timeout=30_000)
        viewport_quiz_articles = viewport_quiz.locator("article")
        _require(
            viewport_quiz_articles.count() >= 2,
            f"{viewport_label} Tutor Quiz returned too few questions",
        )
        for quiz_index in range(viewport_quiz_articles.count()):
            viewport_answer = viewport_quiz_articles.nth(quiz_index).locator(
                'input[type="radio"]'
            ).first
            _focus_via_tab(completion_viewport_page, viewport_answer)
            viewport_answer.press("Space")
        viewport_check = completion_viewport_page.get_by_role(
            "button", name="Check answers", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_check)
        viewport_check.press("Enter")
        viewport_score = completion_viewport_page.get_by_test_id(
            "tutor-quiz-score"
        )
        expect(viewport_score).to_be_focused()
        _require_visible_focus(
            viewport_score, f"{viewport_label} Tutor Quiz score"
        )
        score_box = viewport_score.bounding_box()
        _require(
            score_box is not None
            and score_box["x"] >= 0
            and score_box["x"] + score_box["width"] <= viewport_width
            and score_box["y"] < viewport_height
            and score_box["y"] + score_box["height"] > 0,
            f"{viewport_label} Tutor Quiz score is clipped or off-screen: {score_box}",
        )
        quiz_document_width = _document_width(completion_viewport_page)
        quiz_overflowing_elements = completion_viewport_page.evaluate(
            """
            (viewportWidth) => Array.from(document.querySelectorAll("body *"))
              .map((element) => {
                const rect = element.getBoundingClientRect();
                return {
                  tag: element.tagName.toLowerCase(),
                  testId: element.getAttribute("data-testid"),
                  className: typeof element.className === "string" ? element.className : "",
                  left: Math.round(rect.left),
                  right: Math.round(rect.right),
                  width: Math.round(rect.width),
                };
              })
              .filter((item) => item.right > viewportWidth + 1 || item.left < -1)
              .slice(0, 12)
            """,
            viewport_width,
        )
        _require(
            quiz_document_width <= viewport_width,
            f"{viewport_label} Tutor Quiz review caused horizontal overflow to "
            f"{quiz_document_width}px: {quiz_overflowing_elements}",
        )
        viewport_retry = completion_viewport_page.get_by_role(
            "button", name="Try again", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_retry)
        viewport_retry.press("Enter")
        expect(
            viewport_quiz_articles.first.locator('input[type="radio"]').first
        ).to_be_focused()

        viewport_error_console_start = len(console_errors)
        viewport_explain_mode = completion_viewport_page.get_by_role(
            "button", name="Explain", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_explain_mode)
        viewport_explain_mode.press("Enter")
        viewport_tutor_failure = _declare_expected_http_errors(
            console_errors,
            label=f"focused-completion-{viewport_label}",
            page_url=f"{FRONTEND_URL}/tutor?{tutor_workflow_query}",
            source_url=f"{BROWSER_API_URL}/tutor/ask",
            method="POST",
        )
        completion_viewport_page.route(
            re.compile(r".*/tutor/ask$"),
            lambda route: _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=completion_viewport_page,
                expectation_ids=viewport_tutor_failure,
                body='{"detail":"intentional responsive Tutor failure"}',
            ),
            times=1,
        )
        viewport_error_submit = completion_viewport_page.get_by_role(
            "button", name="Ask tutor", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_error_submit)
        viewport_error_submit.press("Enter")
        viewport_error = completion_viewport_page.get_by_test_id("tutor-error")
        expect(viewport_error).to_be_focused(timeout=30_000)
        _require_visible_focus(
            viewport_error, f"{viewport_label} Tutor error feedback"
        )
        error_box = viewport_error.bounding_box()
        _require(
            error_box is not None
            and error_box["x"] >= 0
            and error_box["x"] + error_box["width"] <= viewport_width
            and error_box["y"] < viewport_height
            and error_box["y"] + error_box["height"] > 0,
            f"{viewport_label} Tutor error is clipped or off-screen: {error_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Tutor error caused horizontal overflow",
        )
        _wait_for_declared_http_errors(
            completion_viewport_page,
            console_errors,
            expectation_ids=viewport_tutor_failure,
        )
        viewport_error_console = console_errors[viewport_error_console_start:]
        _require(
            len(viewport_error_console) == 1
            and "status of 503" in viewport_error_console[0],
            f"unexpected {viewport_label} Tutor error console output: "
            f"{viewport_error_console}",
        )

        viewport_quiz_mode = completion_viewport_page.get_by_role(
            "button", name="Quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_quiz_mode)
        viewport_quiz_mode.press("Enter")
        completion_viewport_page.route(
            re.compile(r".*/tutor/quiz$"),
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"questions":[],"total":0}',
            ),
            times=1,
        )
        viewport_empty_submit = completion_viewport_page.get_by_role(
            "button", name="Generate quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_empty_submit)
        viewport_empty_submit.press("Enter")
        viewport_empty = completion_viewport_page.get_by_test_id(
            "tutor-empty-result"
        )
        expect(viewport_empty).to_be_focused(timeout=30_000)
        _require_visible_focus(
            viewport_empty, f"{viewport_label} Tutor empty Quiz feedback"
        )
        empty_box = viewport_empty.bounding_box()
        _require(
            empty_box is not None
            and empty_box["x"] >= 0
            and empty_box["x"] + empty_box["width"] <= viewport_width
            and empty_box["y"] < viewport_height
            and empty_box["y"] + empty_box["height"] > 0,
            f"{viewport_label} Tutor empty Quiz result is clipped or off-screen: "
            f"{empty_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Tutor empty Quiz result caused horizontal overflow",
        )
        checks[f"tutor_dynamic_{viewport_label}_viewport"] = True
        checks[f"tutor_keyboard_feedback_{viewport_label}"] = True
        checks[f"tutor_error_feedback_{viewport_label}"] = True
        checks[f"tutor_empty_quiz_feedback_{viewport_label}"] = True
        completion_viewport_context.close()

    graph_round_trip_path = "/graph?node_id=article%3Acrb-formula&q=CRB"
    for viewport_width, viewport_height, viewport_label in (
        (1440, 900, "desktop"),
        (390, 844, "mobile"),
        (320, 844, "narrow"),
        (720, 450, "zoom-equivalent"),
    ):
        graph_reader_context = browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            locale="zh-CN",
            is_mobile=viewport_width <= 390,
            reduced_motion="reduce",
        )
        if viewport_label == "desktop":
            graph_reader_context.add_init_script(
                script=f"""
                localStorage.setItem(
                  "scientific-spaces-reader-progress-v1",
                  {json.dumps(json.dumps({
                      "version": 1,
                      "items": [{
                          "article_id": CRB_ARTICLE_ID,
                          "section_id": "regularity",
                          "section_title": "正则条件",
                          "progress": 42,
                          "updated_at": "2026-08-31T02:00:00.000Z",
                      }],
                  }, ensure_ascii=False))}
                );
                """
            )
        _install_network_guard(graph_reader_context, blocked_external)
        graph_reader_page = _new_observed_page(
            graph_reader_context,
            console_errors,
            page_errors,
            label=f"graph-reader-{viewport_label}",
        )
        graph_reader_page.goto(
            f"{FRONTEND_URL}{graph_round_trip_path}", wait_until="domcontentloaded"
        )
        _wait_for_application_shell(graph_reader_page)
        saved_reader_progress = (
            graph_reader_page.evaluate(
                "localStorage.getItem('scientific-spaces-reader-progress-v1')"
            )
            if viewport_label == "desktop"
            else None
        )
        selected_region = graph_reader_page.get_by_test_id("graph-selected-region")
        expect(selected_region).to_be_visible(timeout=30_000)
        viewport_article_link = selected_region.get_by_role(
            "link", name="Open article", exact=True
        ).first
        expect(viewport_article_link).to_be_visible(timeout=30_000)
        viewport_article_href = str(viewport_article_link.get_attribute("href") or "")
        _require(
            viewport_article_href.startswith(f"/articles/{CRB_ARTICLE_ID}"),
            f"{viewport_label} Graph Article action lost its Reader route: "
            f"{viewport_article_href}",
        )
        selected_region.scroll_into_view_if_needed()
        viewport_article_link.scroll_into_view_if_needed()
        selected_box = selected_region.bounding_box()
        graph_link_box = viewport_article_link.bounding_box()
        _require_viewport_intersection(
            selected_box,
            viewport_width,
            viewport_height,
            f"{viewport_label} selected Graph region",
        )
        _require_viewport_containment(
            graph_link_box,
            viewport_width,
            viewport_height,
            f"{viewport_label} Graph Article action",
        )
        _focus_via_tab(graph_reader_page, viewport_article_link, max_steps=40)
        viewport_article_transition = _declare_expected_route_transition(
            graph_reader_page,
            destination_url=f"{FRONTEND_URL}{viewport_article_href}",
        )
        viewport_article_link.press("Enter")
        graph_reader_page.wait_for_function(
            "articleId => location.pathname === `/articles/${articleId}`",
            arg=CRB_ARTICLE_ID,
            timeout=30_000,
        )
        viewport_reader_heading = graph_reader_page.locator("article#article-start > h1")
        expect(viewport_reader_heading).to_have_text(CRB_TITLE, timeout=30_000)
        expect(viewport_reader_heading).to_be_focused()
        _require_visible_focus(
            viewport_reader_heading, f"{viewport_label} Graph-origin Reader heading"
        )
        _wait_for_page_requests_to_settle(graph_reader_page, console_errors)
        _complete_expected_route_transition(
            graph_reader_page, viewport_article_transition
        )
        if viewport_label == "desktop":
            graph_reader_page.evaluate("window.dispatchEvent(new Event('resize'))")
            graph_reader_page.wait_for_timeout(450)
            _require_viewport_containment(
                viewport_reader_heading.bounding_box(),
                viewport_width,
                viewport_height,
                "Graph-origin Reader heading with saved progress",
            )
            _require(
                graph_reader_page.evaluate(
                    "localStorage.getItem('scientific-spaces-reader-progress-v1')"
                )
                == saved_reader_progress,
                "Graph-origin Reader overwrote saved progress before user movement",
            )
            checks["graph_reader_saved_progress_heading_focus"] = True
        viewport_return = graph_reader_page.get_by_role(
            "link", name="Return to graph", exact=True
        )
        expect(viewport_return).to_have_attribute("href", graph_round_trip_path)
        viewport_reader_heading.scroll_into_view_if_needed()
        viewport_return.scroll_into_view_if_needed()
        _require_viewport_containment(
            viewport_reader_heading.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} Reader heading",
        )
        _require_viewport_containment(
            viewport_return.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} Reader return action",
        )
        _require(
            _document_width(graph_reader_page) <= viewport_width,
            f"{viewport_label} Graph-origin Reader overflows horizontally",
        )
        viewport_end_session = graph_reader_page.get_by_role(
            "button", name="End session", exact=True
        )
        expect(viewport_end_session).to_be_enabled(timeout=30_000)
        viewport_end_session.click()
        expect(viewport_end_session).to_be_disabled()
        viewport_graph_return_transition = _declare_expected_route_transition(
            graph_reader_page,
            destination_url=f"{FRONTEND_URL}{graph_round_trip_path}",
        )
        viewport_return.press("Enter")
        graph_reader_page.wait_for_function(
            "expected => location.pathname + location.search === expected",
            arg=graph_round_trip_path,
            timeout=30_000,
        )
        returned_viewport_link = graph_reader_page.get_by_role(
            "link", name="Open article", exact=True
        ).first
        expect(returned_viewport_link).to_be_focused(timeout=30_000)
        _require_visible_focus(
            returned_viewport_link, f"{viewport_label} restored Graph Article action"
        )
        _wait_for_page_requests_to_settle(graph_reader_page, console_errors)
        _complete_expected_route_transition(
            graph_reader_page, viewport_graph_return_transition
        )
        if viewport_label == "desktop":
            _require(
                graph_reader_page.evaluate(
                    "localStorage.getItem('scientific-spaces-reader-progress-v1')"
                )
                == saved_reader_progress,
                "Graph-origin Reader cleanup overwrote saved progress without scrolling",
            )
        returned_viewport_link.scroll_into_view_if_needed()
        _require_viewport_containment(
            returned_viewport_link.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} restored Graph Article action",
        )
        _require(
            _document_width(graph_reader_page) <= viewport_width,
            f"{viewport_label} returned Graph workspace overflows horizontally",
        )
        checks[f"graph_reader_{viewport_label}_viewport"] = True
        graph_reader_context.close()

    storage_denied_context = browser.new_context(
        viewport={"width": 320, "height": 844},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    storage_denied_context.add_init_script(
        script="""
        (() => {
          const originalSetItem = Storage.prototype.setItem;
          Storage.prototype.setItem = function (key, value) {
            if (this === window.sessionStorage) {
              throw new DOMException("session storage write denied", "QuotaExceededError");
            }
            if (key === "scientific-spaces-reading-history-v1") {
              throw new DOMException("reading history denied", "QuotaExceededError");
            }
            return originalSetItem.call(this, key, value);
          };
        })();
        """
    )
    _install_network_guard(storage_denied_context, blocked_external)
    storage_denied_page = _new_observed_page(
        storage_denied_context,
        console_errors,
        page_errors,
        label="graph-reader-storage-denied",
    )
    storage_denied_reader = (
        f"/articles/{CRB_ARTICLE_ID}?"
        + urlencode({"from": graph_round_trip_path})
    )
    storage_denied_page.goto(
        f"{FRONTEND_URL}{storage_denied_reader}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(storage_denied_page)
    storage_denied_page.wait_for_function(
        "articleId => location.pathname === `/articles/${articleId}`",
        arg=CRB_ARTICLE_ID,
        timeout=30_000,
    )
    storage_denied_heading = storage_denied_page.locator("article#article-start > h1")
    expect(storage_denied_heading).to_have_text(CRB_TITLE, timeout=30_000)
    _wait_for_animation_frames(storage_denied_page, 5)
    _require(
        storage_denied_page.evaluate("document.activeElement === document.body"),
        "storage-denied hard-loaded Reader moved focus during hydration",
    )
    storage_denied_heading.focus()
    expect(storage_denied_heading).to_be_focused()
    _require_visible_focus(storage_denied_heading, "storage-denied Reader heading")
    expect(
        storage_denied_page.get_by_text(
            "Reading history is unavailable in this browser session.", exact=True
        )
    ).to_be_visible()
    expect(
        storage_denied_page.get_by_text("Article unavailable", exact=True)
    ).to_have_count(0)
    storage_denied_return = storage_denied_page.get_by_role(
        "link", name="Return to graph", exact=True
    )
    expect(storage_denied_return).to_have_attribute("href", graph_round_trip_path)
    storage_denied_end_session = storage_denied_page.get_by_role(
        "button", name="End session", exact=True
    )
    expect(storage_denied_end_session).to_be_enabled(timeout=30_000)
    storage_denied_end_session.click()
    expect(storage_denied_end_session).to_be_disabled()
    _focus_via_tab(storage_denied_page, storage_denied_return)
    storage_denied_return_transition = _declare_expected_route_transition(
        storage_denied_page,
        destination_url=f"{FRONTEND_URL}{graph_round_trip_path}",
    )
    storage_denied_return.press("Enter")
    storage_denied_page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_round_trip_path,
        timeout=30_000,
    )
    storage_denied_selected_region = storage_denied_page.get_by_test_id(
        "graph-selected-region"
    )
    expect(storage_denied_selected_region).to_be_visible(timeout=30_000)
    expect(storage_denied_selected_region).to_be_focused(timeout=30_000)
    _wait_for_page_requests_to_settle(storage_denied_page, console_errors)
    _complete_expected_route_transition(
        storage_denied_page, storage_denied_return_transition
    )
    _require_visible_focus(
        storage_denied_selected_region,
        "storage-denied returned Graph selected region",
    )
    storage_denied_selected_region.scroll_into_view_if_needed()
    _require_viewport_containment(
        storage_denied_selected_region.bounding_box(),
        320,
        844,
        "storage-denied returned Graph selected region",
    )
    _require(
        _document_width(storage_denied_page) <= 320,
        "storage-denied Graph round trip overflows horizontally",
    )
    checks["graph_reader_storage_unavailable_fallback"] = True
    storage_denied_context.close()

    mobile_context = browser.new_context(
        viewport={"width": 390, "height": 844},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    mobile_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-reading-history-v1",
          {json.dumps(json.dumps([{
              "id": CRB_ARTICLE_ID,
              "title": CRB_TITLE,
              "url": "https://spaces.ac.cn/archives/6508",
              "last_read_at": "2026-08-31T02:00:00.000Z",
          }], ensure_ascii=False))}
        );
        localStorage.setItem(
          "scientific-spaces-reader-progress-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "items": [{
                  "article_id": CRB_ARTICLE_ID,
                  "section_id": "regularity",
                  "section_title": "正则条件",
                  "progress": 42,
                  "updated_at": "2026-08-31T02:00:00.000Z",
              }],
          }, ensure_ascii=False))}
        );
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-08-31T02:03:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": "regularity",
                      "added_at": "2026-08-31T02:00:00.000Z",
                  },
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-08-31T02:01:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(mobile_context, blocked_external)
    mobile_page = mobile_context.new_page()
    _mark_expected_context_page(mobile_context, mobile_page)
    mobile_page.on(
        "console",
        lambda message: console_errors.capture(message, label="mobile", page=mobile_page),
    )
    console_errors.observe_http_errors(mobile_page, label="mobile")
    mobile_page.on(
        "pageerror", lambda error: _capture_page_error(page_errors, "mobile", mobile_page, error)
    )
    mobile_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(mobile_page)
    expect(
        mobile_page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "dashboard"
    )
    mobile_search_trigger = mobile_page.get_by_test_id("global-search-trigger-mobile")
    expect(mobile_search_trigger).to_be_visible()
    _require(
        mobile_search_trigger.inner_text().strip() == "Search",
        "mobile search trigger exposes shortcut instructions",
    )
    mobile_search_trigger.click()
    mobile_search_dialog = mobile_page.get_by_test_id("global-search-dialog")
    expect(mobile_search_dialog).to_be_visible()
    mobile_search_input = mobile_search_dialog.get_by_label("Search library")
    expect(mobile_search_input).to_be_focused()
    _require(
        mobile_search_dialog.locator('[data-testid="global-search-result-workspace"]').count() == 7,
        "mobile quick navigation does not expose seven stable workspaces",
    )
    mobile_search_box = mobile_search_dialog.locator('[role="dialog"]').bounding_box()
    _require(
        mobile_search_box is not None and mobile_search_box["width"] <= 390,
        f"mobile global search dialog overflowed: {mobile_search_box}",
    )
    mobile_search_input.fill("CRB")
    mobile_article_result = mobile_search_dialog.get_by_test_id("global-search-result-article").first
    expect(mobile_article_result).to_contain_text(CRB_TITLE, timeout=30_000)
    mobile_search_input.press("Escape")
    expect(mobile_search_dialog).to_have_count(0)
    expect(mobile_search_trigger).to_be_focused()
    _require(_document_width(mobile_page) <= 390, "mobile Shell overflows after global search")
    checks["mobile_global_search"] = True

    mobile_menu_button = mobile_page.get_by_role("button", name="Open navigation", exact=True)
    expect(mobile_menu_button).to_have_attribute("aria-expanded", "false")
    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    expect(mobile_menu_button).to_have_attribute("aria-expanded", "true")
    close_navigation = mobile_page.get_by_role("button", name="Close navigation", exact=True)
    expect(close_navigation).to_be_focused()
    _require(
        mobile_navigation.locator('nav[aria-label="Primary"] a').count() == 7,
        "mobile drawer does not expose seven primary workspaces",
    )
    expect(
        mobile_navigation.locator('nav[aria-label="Primary"] [aria-current="page"]')
    ).to_have_text("Dashboard")
    close_navigation.press("Escape")
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_menu_button).to_be_focused()
    checks["mobile_navigation_focus_and_escape"] = True

    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    close_navigation = mobile_page.get_by_role("button", name="Close navigation", exact=True)
    expect(close_navigation).to_be_focused()
    close_navigation.click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_menu_button).to_be_focused()
    checks["shell_drawer_close_button_dismissal"] = True

    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_page.get_by_role("button", name="Close navigation overlay", exact=True).click(
        position={"x": 10, "y": 200}
    )
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_menu_button).to_be_focused()
    checks["shell_drawer_backdrop_dismissal"] = True

    stat_boxes = mobile_page.locator('[data-testid="dashboard-stats"] > div').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect()).map(box => ({x: box.x, y: box.y}))"
    )
    _require(len({round(item["x"]) for item in stat_boxes}) == 2, "mobile dashboard statistics are not two columns")
    expect(mobile_page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    continue_learning_action = mobile_page.get_by_role(
        "link",
        name="Resume focused session",
        exact=True,
    ).bounding_box()
    _require(
        continue_learning_action is not None
        and continue_learning_action["y"] + continue_learning_action["height"] <= 844,
        "Focused Session resume action is clipped by the first mobile viewport",
    )
    _require(_document_width(mobile_page) <= 390, "mobile Dashboard overflows the viewport")
    expect(mobile_page.get_by_role("heading", name="Next Actions", exact=True)).to_be_visible()
    checks["mobile_dashboard_density"] = True

    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_library_transition = _declare_expected_route_transition(
        mobile_page,
        destination_url=f"{FRONTEND_URL}/library",
    )
    mobile_navigation.get_by_role("link", name="Saved", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "library"
    )
    mobile_shell_main = mobile_page.get_by_test_id("shell-main-content")
    expect(mobile_shell_main).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_shell_main, "mobile Drawer destination")
    _wait_for_page_requests_to_settle(mobile_page, console_errors)
    _complete_expected_route_transition(mobile_page, mobile_library_transition)
    mobile_same_url_history = mobile_page.evaluate("history.length")
    mobile_same_url_location = mobile_page.url
    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_navigation.get_by_role("link", name="Saved", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_shell_main).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_shell_main, "mobile same-URL Drawer destination")
    _require(
        mobile_page.evaluate("history.length") == mobile_same_url_history,
        "mobile same-URL Drawer navigation added history",
    )
    _require(mobile_page.url == mobile_same_url_location, "mobile same-URL Drawer changed URL")
    checks["shell_mobile_drawer_route_focus"] = True
    expect(mobile_page.get_by_role("button", name="Continue (0)", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(mobile_page.get_by_role("heading", name="Continue Learning", exact=True)).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Bookmarked", exact=True)).to_be_visible()
    expect(mobile_page.get_by_role("heading", name="Recently Read", exact=True)).to_be_visible()
    library_stat_boxes = mobile_page.locator('[data-testid="saved-library-summary"] > div').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect()).map(box => ({x: box.x, y: box.y}))"
    )
    _require(
        len({round(item["x"]) for item in library_stat_boxes}) == 2,
        "mobile Saved Library statistics are not two columns",
    )
    library_width = _document_width(mobile_page)
    _require(library_width <= 390, f"mobile Saved Library overflowed to {library_width}px")
    checks["mobile_saved_learning_library"] = True

    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_navigation.get_by_role("link", name="Session", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "session"
    )
    expect(mobile_page.get_by_test_id("study-session-summary")).to_contain_text("2 Articles")
    expect(mobile_page.get_by_test_id("study-session-item")).to_have_count(2)
    session_width = _document_width(mobile_page)
    first_session_item_box = mobile_page.get_by_test_id("study-session-item").first.bounding_box()
    _require(
        first_session_item_box is not None
        and first_session_item_box["x"] >= 0
        and first_session_item_box["x"] + first_session_item_box["width"] <= 390,
        f"mobile Session queue item is clipped: {first_session_item_box}",
    )
    _require(session_width <= 390, f"mobile Session overflowed to {session_width}px")
    checks["mobile_focused_study_session"] = True

    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_articles_transition = _declare_expected_route_transition(
        mobile_page,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    mobile_navigation.get_by_role("link", name="Articles", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "articles"
    )
    expect(mobile_page.get_by_text("Showing 1-3 of 3", exact=True)).to_be_visible(timeout=30_000)
    expect(mobile_page.get_by_test_id("article-pagination")).to_have_count(0)
    _wait_for_page_requests_to_settle(mobile_page, console_errors)
    _complete_expected_route_transition(mobile_page, mobile_articles_transition)
    checks["mobile_navigation_route_selection"] = True
    list_width = _document_width(mobile_page)
    mobile_reader_transition = _declare_expected_route_transition(
        mobile_page,
        destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
    )
    mobile_page.get_by_role("link", name=CRB_TITLE, exact=True).click()
    expect(mobile_page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(mobile_page.locator(".reader-markdown .katex").first).to_be_visible()
    _wait_for_page_requests_to_settle(mobile_page, console_errors)
    _complete_expected_route_transition(mobile_page, mobile_reader_transition)
    reading_tools_link = mobile_page.get_by_role("link", name="Reading tools", exact=True)
    outline_link = mobile_page.get_by_role("link", name="Outline", exact=True)
    expect(reading_tools_link).to_be_visible()
    expect(outline_link).to_be_visible()
    reading_tools_box = reading_tools_link.bounding_box()
    _require(
        reading_tools_box is not None and reading_tools_box["y"] < 844,
        "mobile Reading tools entry is below the first viewport",
    )
    detail_width = _document_width(mobile_page)
    formula_overflow = mobile_page.locator(".reader-markdown .katex-display").first.evaluate(
        "(node) => getComputedStyle(node).overflowX"
    )
    _require(list_width <= 390, f"mobile Article List overflowed to {list_width}px")
    _require(detail_width <= 390, f"mobile Article Detail overflowed to {detail_width}px")
    _require(formula_overflow == "auto", "display formula does not retain local horizontal scrolling")
    _require(
        mobile_page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches"),
        "reduced-motion browser preference is not active",
    )
    mobile_hash_history = int(mobile_page.evaluate("history.length"))
    outline_link.click()
    mobile_outline_target = mobile_page.locator("#article-outline")
    expect(mobile_outline_target).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_outline_target, "mobile Reader outline target")
    reading_tools_link.click()
    mobile_tools_target = mobile_page.locator("#reading-tools")
    expect(mobile_tools_target).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_tools_target, "mobile Reader tools target")
    expect(mobile_page.get_by_role("link", name="Ask tutor", exact=True)).to_be_visible()
    expect(mobile_page.get_by_role("link", name="Explore graph", exact=True)).to_be_visible()
    mobile_page.get_by_role("link", name="Back to article", exact=True).click()
    mobile_article_target = mobile_page.locator("article#article-start")
    expect(mobile_article_target).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_article_target, "mobile Reader article target")
    _require(
        int(mobile_page.evaluate("history.length")) == mobile_hash_history + 3,
        "Reader fragment navigation did not add exactly one entry per changed hash",
    )
    mobile_page.go_back()
    expect(mobile_page).to_have_url(re.compile(r"#reading-tools$"), timeout=30_000)
    expect(mobile_tools_target).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_tools_target, "mobile Reader hash Back target")
    mobile_page.go_forward()
    expect(mobile_page).to_have_url(re.compile(r"#article-start$"), timeout=30_000)
    expect(mobile_article_target).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_article_target, "mobile Reader hash Forward target")
    checks["reader_hash_history_focus"] = True
    mobile_end_button = mobile_page.get_by_role("button", name="End session", exact=True)
    expect(mobile_end_button).to_be_enabled(timeout=30_000)
    mobile_end_button.click()
    expect(mobile_end_button).to_be_disabled()
    checks["mobile_layout_and_formula_scroll"] = True

    mobile_page.get_by_role("link", name="Ask tutor", exact=True).click()
    expect(mobile_page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("tutor-selected-article")).to_contain_text(CRB_TITLE)
    expect(mobile_page.get_by_text("Advanced context", exact=True)).to_be_visible()
    tutor_width = _document_width(mobile_page)
    _require(tutor_width <= 390, f"mobile Tutor page overflowed to {tutor_width}px")
    checks["mobile_guided_tutor_workspace"] = True

    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_graph_transition = _declare_expected_route_transition(
        mobile_page,
        destination_url=f"{FRONTEND_URL}/graph",
    )
    mobile_navigation.get_by_role("link", name="Graph", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    _wait_for_page_requests_to_settle(mobile_page, console_errors)
    _complete_expected_route_transition(mobile_page, mobile_graph_transition)
    mobile_page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    mobile_page.locator('select[name="node_type"]').select_option("concept")
    mobile_page.get_by_role("button", name="Apply", exact=True).click()
    mobile_graph_node = (
        mobile_page.get_by_test_id("graph-node-results")
        .locator("button")
        .filter(has_text=re.compile(r"^Attention", re.I))
        .first
    )
    expect(mobile_graph_node).to_be_visible(timeout=30_000)
    mobile_graph_node.click()
    mobile_selected_region = mobile_page.get_by_test_id("graph-selected-region")
    expect(mobile_selected_region).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_selected_region, "mobile selected Graph region")
    _wait_for_test_id_near_viewport_top(mobile_page, "graph-selected-region")
    mobile_selected_box = mobile_selected_region.bounding_box()
    _require(
        mobile_selected_box is not None
        and mobile_selected_box["y"] < 200
        and mobile_selected_box["y"] + mobile_selected_box["height"] > 0,
        f"mobile selected detail does not intersect the viewport: {mobile_selected_box}",
    )
    _require(
        "node_id=concept%3Aattention" in mobile_page.url and "q=Attention" in mobile_page.url,
        f"mobile Graph selection URL is incomplete: {mobile_page.url}",
    )
    mobile_concept_set = mobile_page.get_by_test_id("concept-study-set")
    expect(mobile_concept_set).to_be_visible(timeout=30_000)
    expect(mobile_concept_set.get_by_role("link", name="Explain concept", exact=True)).to_be_visible()
    expect(mobile_concept_set.get_by_role("link", name="Open concept quiz", exact=True)).to_be_visible()
    mobile_concept_box = mobile_concept_set.bounding_box()
    _require(
        mobile_concept_box is not None
        and mobile_concept_box["x"] >= 0
        and mobile_concept_box["x"] + mobile_concept_box["width"] <= 390,
        f"mobile Concept Study Set is clipped: {mobile_concept_box}",
    )
    mobile_graph_width = _document_width(mobile_page)
    _require(mobile_graph_width <= 390, f"mobile Graph page overflowed to {mobile_graph_width}px")
    checks["mobile_concept_study_set"] = True
    mobile_page.get_by_role("button", name="Back to results", exact=True).click()
    expect(mobile_graph_node).to_be_focused()
    mobile_page.get_by_placeholder("Title, concept, or formula").fill("No matching graph node")
    mobile_page.get_by_role("button", name="Apply", exact=True).click()
    expect(mobile_page.get_by_text("No nodes match the current filters.", exact=True)).to_be_visible(
        timeout=30_000
    )
    mobile_page.get_by_role("group", name="Explore panel").get_by_role(
        "button", name="Selected", exact=True
    ).click()
    expect(mobile_selected_region).to_be_focused()
    mobile_page.get_by_role("button", name="Back to results", exact=True).click()
    expect(mobile_page.get_by_role("heading", name="Nodes", exact=True)).to_be_focused()
    mobile_page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    mobile_page.get_by_role("button", name="Apply", exact=True).click()
    expect(mobile_graph_node).to_be_visible(timeout=30_000)
    checks["mobile_graph_missing_origin_focus_fallback"] = True
    mobile_graph_node.click()
    expect(mobile_selected_region).to_be_focused()
    mobile_page.get_by_role("group", name="Graph workspace view").get_by_role(
        "button", name="Knowledge context", exact=True
    ).click()
    mobile_context_region = mobile_page.locator("#graph-context-workspace")
    expect(mobile_context_region).to_be_focused()
    _require_visible_focus(mobile_context_region, "mobile Knowledge Context region")
    expect(mobile_page.get_by_test_id("graph-context-explorer")).to_be_visible()
    expect(mobile_page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    mobile_graph_box = mobile_page.locator(".knowledge-graph-canvas").bounding_box()
    mobile_map_node_box = mobile_page.get_by_role(
        "button", name=re.compile(r"^Selected Concept: Attention", re.I)
    ).bounding_box()
    _require(
        mobile_graph_box is not None and mobile_graph_box["width"] <= 390,
        f"mobile visual Graph canvas overflowed: {mobile_graph_box}",
    )
    _require_box_inside(
        mobile_graph_box,
        mobile_map_node_box,
        "mobile selected Graph node",
        minimum_width=80,
        minimum_height=30,
    )
    expect(mobile_page.locator("#graph-context-workspace")).to_be_focused()
    expect(mobile_page.locator(".react-flow__controls")).to_be_visible()
    mobile_page.get_by_test_id("graph-view-list").click()
    expect(mobile_page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    checks["mobile_visual_knowledge_explorer"] = True
    mobile_context.close()

    checks.update(
        _verify_structured_reference_review_round_trip(
            browser,
            blocked_external=blocked_external,
            console_errors=console_errors,
            page_errors=page_errors,
        )
    )

    checks.update(
        _verify_zotero_links_panel_integrity(
            browser,
            iteration=iteration,
            blocked_external=blocked_external,
            console_errors=console_errors,
            page_errors=page_errors,
        )
    )

    _verify_reader_learning_mutation_integrity(
        browser,
        iteration=iteration,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["reader_learning_mutation_integrity"] = True

    framework_prefetch_cancellations = _framework_prefetch_cancellations(console_errors)
    route_transition_cancellations = _route_transition_cancellations(console_errors)
    precursor_snapshot_route_cancellations = (
        _route_cancellations_with_complete_precursor_snapshot(
            console_errors
        )
    )
    declared_cancelled_route_requests = _declared_cancelled_route_requests(
        console_errors
    )
    declared_route_read_cancellations = _declared_route_read_cancellations(
        console_errors
    )
    superseded_successful_reads = _superseded_successful_reads(console_errors)
    next_static_chunk_cancellations = _next_static_chunk_cancellations(console_errors)
    successful_no_content_responses = _successful_no_content_responses(console_errors)
    unexpected_console_errors = _unexpected_console_errors(console_errors)
    unexpected_context_pages = _unexpected_context_pages(blocked_external)
    _require(not blocked_external, f"unexpected external requests: {blocked_external}")
    _require(
        not unexpected_context_pages,
        f"unexpected browser context pages: {unexpected_context_pages}",
    )
    _require(not unexpected_console_errors, f"unexpected console errors: {unexpected_console_errors}")
    _require(not page_errors, f"uncaught page errors: {page_errors}")
    checks["local_only_network_and_console"] = True

    return {
        "iteration": iteration,
        "status": "PASS" if all(checks.values()) else "BLOCKED",
        "checks": checks,
        "mobile_widths": {
            "viewport": 390,
            "saved_library": library_width,
            "study_session": session_width,
            "article_list": list_width,
            "article_detail": detail_width,
            "tutor": tutor_width,
            "graph": mobile_graph_width,
        },
        "external_network_request_count": len(blocked_external),
        "framework_prefetch_cancellation_count": len(framework_prefetch_cancellations),
        "route_transition_cancellation_count": len(route_transition_cancellations),
        "route_with_complete_precursor_snapshot_count": len(
            precursor_snapshot_route_cancellations
        ),
        "declared_cancelled_route_request_count": len(
            declared_cancelled_route_requests
        ),
        "declared_route_read_cancellation_count": len(
            declared_route_read_cancellations
        ),
        "route_transition_expectation_count": len(
            console_errors.route_transition_expectations
        ),
        "bound_route_transition_request_count": sum(
            len(expectation.get("bound_request_ids") or ())
            for expectation in console_errors.route_transition_expectations
        ),
        "superseded_successful_read_count": len(superseded_successful_reads),
        "next_static_chunk_cancellation_count": len(next_static_chunk_cancellations),
        "successful_no_content_response_count": len(successful_no_content_responses),
        "console_error_count": len(unexpected_console_errors),
        "page_error_count": len(page_errors),
    }


def _verify_structured_reference_review_round_trip(
    browser,
    *,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> dict[str, bool]:
    from playwright.sync_api import expect

    checks: dict[str, bool] = {}
    context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    context.add_init_script(
        """
        window.IntersectionObserver = class {
          constructor() {}
          observe() {}
          unobserve() {}
          disconnect() {}
          takeRecords() { return []; }
        };
        """
    )
    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="P3-033 reference review",
    )
    reference_api_requests: list[str] = []

    def track_reference_api_request(request) -> None:
        parsed = urlparse(request.url)
        if (
            parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            and parsed.path.startswith("/v1.2/references")
        ):
            reference_api_requests.append(request.url)

    page.on("request", track_reference_api_request)

    def selected_reference_url(selected_reference_id: str) -> str:
        parsed = urlparse(page.url)
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in {"reference_id", "candidate"}
        ]
        query.append(("reference_id", selected_reference_id))
        return parsed._replace(query=urlencode(query), fragment="").geturl()

    def candidate_filter_url(candidate: str | None) -> str:
        parsed = urlparse(page.url)
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key != "candidate"
        ]
        if candidate is not None:
            query.append(("candidate", candidate))
        return parsed._replace(query=urlencode(query), fragment="").geturl()

    inbound_reference_url = (
        f"{FRONTEND_URL}/zotero?page=1&candidate=all&unknown=discard&q=%20attention%20"
    )
    canonical_reference_url = f"{FRONTEND_URL}/zotero?q=attention"
    inbound_canonicalization = _declare_expected_route_transition(
        page,
        destination_url=canonical_reference_url,
        request_page_url=inbound_reference_url,
        allow_speculative_cancellations=True,
    )
    page.goto(inbound_reference_url, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page).to_have_url(canonical_reference_url, timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, inbound_canonicalization)
    checks["reference_inbound_url_canonicalization"] = True

    initial_review_prefetch_anchor = console_errors._event_sequence
    page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Farticles%3Fq%3DCRB",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    review_link = page.get_by_role(
        "link",
        name=re.compile(r"^Review Zotero candidates for "),
    ).first
    expect(review_link).to_be_visible(timeout=30_000)
    source_row = review_link.locator("xpath=ancestor::li[1]")
    reference_id = source_row.get_attribute("data-reference-id")
    _require(bool(reference_id), "Article review action is missing its exact reference identity")
    source_row_id = source_row.get_attribute("id")
    _require(bool(source_row_id), "Article structured reference row is missing its focus target id")
    review_destination_href = str(review_link.get_attribute("href") or "")
    _require(
        review_destination_href.startswith("/zotero?"),
        f"Article review action has an invalid destination: {review_destination_href}",
    )
    review_link.hover()
    _wait_for_exact_route_request_to_finish(
        page,
        console_errors,
        source_url=f"{FRONTEND_URL}{review_destination_href}",
        after_sequence=initial_review_prefetch_anchor,
    )
    provenance_requests = {"count": 0}
    provenance_pattern = re.compile(
        rf".*/v1\.2/references/{re.escape(str(reference_id))}(?:\?.*)?$"
    )

    def provide_bounded_provenance(route) -> None:
        time.sleep(0.5)
        response = route.fetch(max_redirects=0)
        _require(
            response.url == route.request.url and 200 <= response.status < 300,
            "bounded provenance source redirected or failed: "
            f"expected_url={route.request.url} actual_url={response.url} "
            f"status={response.status}",
        )
        payload = response.json()
        base_evidence = dict(payload["evidence"][0])
        payload["record"]["source_count"] = 25
        payload["evidence"] = [
            {
                **base_evidence,
                "evidence_id": f"p3-033-evidence-{index + 1}",
                "source_article_id": (
                    CRB_ARTICLE_ID if index % 2 == 0 else ATTENTION_ARTICLE_ID
                ),
                "source_article_title": (
                    CRB_TITLE if index % 2 == 0 else ATTENTION_TITLE
                ),
                "source_article_url": (
                    "https://spaces.ac.cn/archives/crb"
                    if index % 2 == 0
                    else "https://spaces.ac.cn/archives/attention"
                ),
                "source_section": f"Evidence section {index + 1}",
                "evidence_text": f"Bounded provenance occurrence {index + 1}",
                "candidate_ordinal": index,
            }
            for index in range(20)
        ]
        payload["evidence_total"] = 25
        payload["provenance_limit"] = 20
        payload["provenance_truncated"] = True
        provenance_requests["count"] += 1
        route.fulfill(
            status=response.status,
            content_type="application/json",
            body=json.dumps(payload),
        )

    page.route(provenance_pattern, provide_bounded_provenance)
    initial_reference_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(initial_reference_reader_session).to_be_enabled(timeout=30_000)
    initial_reference_reader_session.click()
    expect(initial_reference_reader_session).to_be_disabled()
    review_link.focus()
    expect(review_link).to_be_focused()
    _start_zotero_focus_trace(page)
    initial_review_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{review_destination_href}",
    )
    review_link.press("Enter")

    page.wait_for_function(
        "expected => new URL(location.href).searchParams.get('reference_id') === expected",
        arg=str(reference_id),
        timeout=30_000,
    )
    selected_detail = page.get_by_test_id("selected-reference-detail")
    review_workspace = page.get_by_test_id("reference-review-workspace")
    expect(selected_detail).to_have_attribute("data-reference-id", str(reference_id), timeout=30_000)
    expect(selected_detail).to_be_focused(timeout=30_000)
    _require_visible_focus(selected_detail, "selected structured reference")
    _assert_zotero_focus_continuity(
        page,
        "deferred structured Reference detail owner",
        ("testid:selected-reference-detail",),
        ("testid:shell-main-content",),
    )
    expect(selected_detail).to_contain_text(CRB_TITLE)
    expect(selected_detail).to_contain_text("References")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, initial_review_transition)
    selected_reference_deep_link_url = page.url
    _require(
        any("provenance_limit=20" in request for request in reference_api_requests),
        f"selected reference did not request the frozen maximum provenance bound: {reference_api_requests}",
    )
    provenance_disclosure = selected_detail.locator("details")
    provenance_disclosure.get_by_text("Show provenance occurrences", exact=True).click()
    expect(provenance_disclosure.locator("li")).to_have_count(20)
    expect(provenance_disclosure.get_by_role("link", name=CRB_TITLE, exact=True).first).to_be_visible()
    expect(provenance_disclosure.get_by_role("link", name=ATTENTION_TITLE, exact=True).first).to_be_visible()
    expect(provenance_disclosure).to_contain_text(
        "Showing the API-bounded 20 of 25 occurrences; the complete count remains visible."
    )
    _require(provenance_requests["count"] == 1, "bounded provenance fixture did not own one detail request")
    _require(
        "return_to=" in page.url and "%23structured-reference-" in page.url,
        f"reference deep link lost its bounded Article return: {page.url}",
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    reference_detail_reload = _declare_expected_route_transition(
        page,
        destination_url=page.url,
        allow_speculative_cancellations=True,
    )
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    selected_detail = page.get_by_test_id("selected-reference-detail")
    expect(selected_detail).to_have_attribute("data-reference-id", str(reference_id), timeout=30_000)
    _require(provenance_requests["count"] == 2, "reload did not restore bounded provenance detail")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, reference_detail_reload)
    page.unroute(provenance_pattern, provide_bounded_provenance)
    checks["reference_exact_deep_link_and_detail_focus"] = True
    checks["reference_reload_and_bounded_provenance"] = True

    initial_source_return_href = str(
        page.get_by_role(
            "link", name="Back to source reference", exact=True
        ).get_attribute("href")
        or ""
    )
    initial_source_return_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{initial_source_return_href}",
    )
    page.get_by_role("link", name="Back to source reference", exact=True).click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    returned_row = page.locator(f'[data-reference-id="{reference_id}"]')
    expect(returned_row).to_have_attribute("id", str(source_row_id))
    expect(returned_row).to_be_focused(timeout=30_000)
    _require_visible_focus(returned_row, "returned structured reference row")
    _require("reference_page=" not in page.url, f"page-one return persisted redundant state: {page.url}")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, initial_source_return_transition)
    reference_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(reference_reader_session).to_be_enabled(timeout=30_000)
    reference_reader_session.click()
    expect(reference_reader_session).to_be_disabled()
    checks["reference_owned_article_return_focus"] = True

    selected_reference_back_transition = _declare_expected_route_transition(
        page,
        destination_url=selected_reference_deep_link_url,
    )
    page.go_back()
    expect(selected_detail).to_have_attribute("data-reference-id", str(reference_id), timeout=30_000)
    selected_url = page.url
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, selected_reference_back_transition)

    selected_reference_payload = _api_json(
        context,
        "GET",
        f"/v1.2/references/{reference_id}?provenance_limit=1",
    )
    selected_record = selected_reference_payload["record"]
    alternate_article_pattern = re.compile(
        rf".*/v1\.2/articles/{re.escape(ATTENTION_ARTICLE_ID)}/references(?:\?.*)?$"
    )
    alternate_article_requests = {"count": 0}
    alternate_review_page_url = {"value": ""}
    alternate_failure_expectations: tuple[str, ...] = ()

    def provide_alternate_article_reference(route) -> None:
        alternate_article_requests["count"] += 1
        if alternate_article_requests["count"] == 2:
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=page,
                expectation_ids=alternate_failure_expectations,
                body=json.dumps({"detail": "intentional Article return verification failure"}),
            )
            return
        requested_page = parse_qs(urlparse(route.request.url).query).get("page", ["1"])[0]
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [selected_record] if requested_page == "1" else [],
                    "total": 1,
                    "page": int(requested_page),
                    "page_size": 20,
                    "total_pages": 1,
                    "has_next": False,
                    "has_previous": False,
                    "article_id": ATTENTION_ARTICLE_ID,
                    "reference_type": None,
                    "classification": None,
                }
            ),
        )

    page.route(alternate_article_pattern, provide_alternate_article_reference)
    page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Farticles%3Fq%3DAttention",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)).to_be_visible(
        timeout=30_000
    )
    alternate_review_link = page.get_by_role(
        "link", name=re.compile(r"^Review Zotero candidates for ")
    ).first
    alternate_row = alternate_review_link.locator("xpath=ancestor::li[1]")
    expect(alternate_row).to_have_attribute("data-reference-id", str(reference_id))
    alternate_review_href = alternate_review_link.get_attribute("href") or ""
    _require(
        alternate_review_href.startswith("/zotero?"),
        f"alternate review link is not an internal Zotero URL: {alternate_review_href}",
    )
    alternate_review_page_url["value"] = f"{FRONTEND_URL}{alternate_review_href}"
    alternate_failure_expectations = _declare_expected_http_errors(
        console_errors,
        label="P3-033 reference review",
        page_url=alternate_review_page_url["value"],
        source_url=(
            f"{BROWSER_API_URL}/v1.2/articles/{ATTENTION_ARTICLE_ID}"
            "/references?page=1&page_size=20"
        ),
    )
    alternate_session = page.get_by_role("button", name="End session", exact=True)
    expect(alternate_session).to_be_enabled(timeout=30_000)
    alternate_session.click()
    expect(alternate_session).to_be_disabled()
    alternate_review_transition = _declare_expected_route_transition(
        page,
        destination_url=alternate_review_page_url["value"],
    )
    alternate_review_link.click()
    page.wait_for_function(
        "expected => new URL(location.href).searchParams.get('reference_id') === expected",
        arg=str(reference_id),
        timeout=30_000,
    )
    alternate_selected_detail = page.get_by_test_id("selected-reference-detail")
    expect(alternate_selected_detail).to_have_attribute(
        "data-reference-id", str(reference_id), timeout=30_000
    )
    expect(alternate_selected_detail.get_by_role("alert")).to_contain_text(
        "Return verification failed: intentional Article return verification failure",
        timeout=30_000,
    )
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=alternate_failure_expectations,
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, alternate_review_transition)
    page.evaluate(
        """
        articleId => {
          const originalFetch = window.fetch.bind(window);
          window.__p3033PendingReturnRetryFetch = originalFetch;
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const url = new URL(target);
            if (url.pathname === `/v1.2/articles/${encodeURIComponent(articleId)}/references`) {
              await new Promise(resolve => setTimeout(resolve, 600));
            }
            return originalFetch(...args);
          };
        }
        """,
        ATTENTION_ARTICLE_ID,
    )
    page.get_by_role("button", name="Retry return verification", exact=True).click()
    expect(alternate_selected_detail).to_be_focused(timeout=1_000)
    expect(page.get_by_text("Verifying originating Article return...", exact=True)).to_be_visible(
        timeout=1_000
    )
    alternate_return = page.get_by_role("link", name="Back to source reference", exact=True)
    expect(alternate_return).to_be_visible(timeout=30_000)
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3033PendingReturnRetryFetch;
          delete window.__p3033PendingReturnRetryFetch;
        }
        """
    )
    expect(alternate_selected_detail).to_be_focused()
    expect(alternate_return).to_have_attribute(
        "href", re.compile(rf"^/articles/{re.escape(ATTENTION_ARTICLE_ID)}\?")
    )
    alternate_return_href = str(alternate_return.get_attribute("href") or "")
    alternate_return_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}{alternate_return_href}",
    )
    alternate_return.click()
    expect(page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)).to_be_visible(
        timeout=30_000
    )
    alternate_returned_row = page.locator(f'[data-reference-id="{reference_id}"]')
    expect(alternate_returned_row).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(
        alternate_returned_row,
        "alternate source Article reference return",
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, alternate_return_transition)
    alternate_return_session = page.get_by_role("button", name="End session", exact=True)
    expect(alternate_return_session).to_be_enabled(timeout=30_000)
    alternate_return_session.click()
    expect(alternate_return_session).to_be_disabled()
    page.unroute(alternate_article_pattern, provide_alternate_article_reference)
    _require(
        alternate_article_requests["count"] >= 4,
        f"Article return failure/retry/readback path was incomplete: {alternate_article_requests}",
    )
    checks["reference_multi_article_owned_return"] = True
    checks["reference_return_verification_retry_focus"] = True

    page.goto(selected_url, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    page_two_pattern = re.compile(
        rf".*/v1\.2/articles/{re.escape(CRB_ARTICLE_ID)}/references(?:\?.*)?$"
    )
    page_two_only_reference_id = f"p3-034-page-two-only-{reference_id}"
    page_two_only_record = {
        **selected_record,
        "reference_id": page_two_only_reference_id,
        "evidence_text": "P3-034 page-two request ownership probe",
    }

    def provide_reference_page_two(route) -> None:
        requested_page = parse_qs(urlparse(route.request.url).query).get("page", ["1"])[0]
        if requested_page != "2":
            route.continue_()
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [selected_record, page_two_only_record],
                    "total": 22,
                    "page": 2,
                    "page_size": 20,
                    "total_pages": 2,
                    "has_next": False,
                    "has_previous": True,
                    "article_id": CRB_ARTICLE_ID,
                    "reference_type": None,
                    "classification": None,
                }
            ),
        )

    page.route(page_two_pattern, provide_reference_page_two)
    page_two_return = (
        f"/articles/{CRB_ARTICLE_ID}?from=%2Farticles%3Fq%3DCRB&reference_page=2"
        f"#structured-reference-{reference_id}"
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    page.goto(
        f"{FRONTEND_URL}/zotero?{urlencode({'reference_id': reference_id, 'return_to': page_two_return})}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("selected-reference-detail")).to_have_attribute(
        "data-reference-id", str(reference_id), timeout=30_000
    )
    page.get_by_role("link", name="Back to source reference", exact=True).click()
    expect(page).to_have_url(re.compile(r"reference_page=2.*#structured-reference-"), timeout=30_000)
    page_two_row = page.locator(f'[data-reference-id="{reference_id}"]')
    expect(page_two_row).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(page_two_row, "page-two structured reference return")
    reference_panel = page.locator("[data-structured-references-state]")
    expect(reference_panel).to_have_attribute(
        "data-structured-references-article-id", CRB_ARTICLE_ID
    )
    expect(reference_panel).to_have_attribute("data-structured-references-page", "2")
    expect(reference_panel).to_have_attribute("data-structured-references-state", "ready")

    page_two_only_return = (
        f"/articles/{CRB_ARTICLE_ID}?from=%2Farticles%3Fq%3DCRB&reference_page=2"
        f"#structured-reference-{page_two_only_reference_id}"
    )
    page_one_route = (
        f"/articles/{CRB_ARTICLE_ID}?from=%2Farticles%3Fq%3DCRB&reference_page=1"
        "#article-outline"
    )
    page.evaluate(
        "url => history.replaceState(history.state, '', url)",
        page_two_only_return,
    )
    page.evaluate(
        """
        url => {
          history.replaceState(history.state, '', url);
          dispatchEvent(new PopStateEvent('popstate', { state: history.state }));
        }
        """,
        page_one_route,
    )
    expect(page).to_have_url(re.compile(r"reference_page=1.*#article-outline$"), timeout=30_000)
    expect(reference_panel).to_have_attribute("data-structured-references-page", "1")
    expect(reference_panel).to_have_attribute(
        "data-structured-references-state", "ready", timeout=30_000
    )
    page.evaluate(
        f"""
        () => {{
          const originalFetch = window.fetch.bind(window);
          let delayPageTwo = true;
          window.__p3034ReferencePageTransitionFetch = originalFetch;
          window.__p3034ReferencePageTransitionRequests = 0;
          window.fetch = async (input, init) => {{
            const rawUrl = typeof input === 'string' ? input : input.url;
            const url = new URL(rawUrl, location.href);
            if (
              delayPageTwo
              && ['127.0.0.1', 'localhost'].includes(url.hostname)
              && url.port === '8000'
              && url.pathname === '/v1.2/articles/{CRB_ARTICLE_ID}/references'
              && url.searchParams.get('page') === '2'
            ) {{
              delayPageTwo = false;
              window.__p3034ReferencePageTransitionRequests += 1;
              await new Promise(resolve => setTimeout(resolve, 1500));
            }}
            return originalFetch(input, init);
          }};
        }}
        """
    )
    page.evaluate(
        """
        url => {
          history.replaceState(history.state, '', url);
          dispatchEvent(new PopStateEvent('popstate', { state: history.state }));
        }
        """,
        page_two_only_return,
    )
    expect(page).to_have_url(
        re.compile(
            rf"reference_page=2.*#structured-reference-{re.escape(page_two_only_reference_id)}$"
        ),
        timeout=30_000,
    )
    expect(reference_panel).to_have_attribute(
        "data-structured-references-page", "2", timeout=2_000
    )
    expect(reference_panel).to_have_attribute("data-structured-references-state", "loading")
    page_two_row = page.locator(f'[data-reference-id="{page_two_only_reference_id}"]')
    _require(
        page.evaluate(
            "targetId => document.activeElement?.id !== targetId",
            f"structured-reference-{page_two_only_reference_id}",
        ),
        "stale page-one state focused the page-two Reference target before its request settled",
    )
    expect(page_two_row).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(page_two_row, "request-keyed page-two Reference target")
    _require(
        page.evaluate("window.__p3034ReferencePageTransitionRequests") == 1,
        "same-mounted Reference page transition did not delay exactly one page-two request",
    )
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3034ReferencePageTransitionFetch;
          delete window.__p3034ReferencePageTransitionFetch;
        }
        """
    )
    page_two_history_length = int(page.evaluate("history.length"))
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("link", name="Outline", exact=True).click()
    page_two_outline = page.locator("#article-outline")
    expect(page_two_outline).to_be_focused(timeout=30_000)
    page.go_back()
    expect(page).to_have_url(re.compile(r"#structured-reference-"), timeout=30_000)
    expect(page_two_row).to_be_focused(timeout=30_000)
    page.go_forward()
    expect(page).to_have_url(re.compile(r"#article-outline$"), timeout=30_000)
    expect(page_two_outline).to_be_focused(timeout=30_000)
    page.go_back()
    expect(page_two_row).to_be_focused(timeout=30_000)
    _require(
        int(page.evaluate("history.length")) == page_two_history_length + 1,
        "structured Reference hash Back/Forward changed history length",
    )
    page.set_viewport_size({"width": 1440, "height": 900})
    page_two_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(page_two_reader_session).to_be_enabled(timeout=30_000)
    page_two_reader_session.click()
    expect(page_two_reader_session).to_be_disabled()

    isolated_focus_sessions: dict[str, dict[str, object]] = {}

    def provide_isolated_focus_session(route) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        payload = route.request.post_data_json
        session_id = f"p3-034-reference-focus-{len(isolated_focus_sessions) + 1}"
        session = {
            "session_id": session_id,
            "article_id": payload["article_id"],
            "started_at": "2026-09-06T00:00:00Z",
            "ended_at": None,
            "duration_seconds": None,
            "source": "reader",
        }
        isolated_focus_sessions[session_id] = session
        route.fulfill(status=200, content_type="application/json", body=json.dumps(session))

    def provide_isolated_focus_session_end(route) -> None:
        session_id = route.request.url.rsplit("/", 2)[-2]
        session = isolated_focus_sessions[session_id]
        session["ended_at"] = "2026-09-06T00:01:00Z"
        session["duration_seconds"] = 60
        route.fulfill(status=200, content_type="application/json", body=json.dumps(session))

    isolated_focus_session_pattern = re.compile(r".*/learning/sessions$")
    isolated_focus_session_end_pattern = re.compile(r".*/learning/sessions/[^/]+/end$")
    page.route(isolated_focus_session_pattern, provide_isolated_focus_session)
    page.route(isolated_focus_session_end_pattern, provide_isolated_focus_session_end)

    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=30_000)
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    persistent_history_origin = page.get_by_test_id("primary-nav-dashboard")
    page.evaluate(
        f"""
        () => {{
          const originalFetch = window.fetch.bind(window);
          let delayArticle = true;
          let delayReferences = true;
          window.__p3034DeferredHistoryFetch = originalFetch;
          window.fetch = async (input, init) => {{
            const rawUrl = typeof input === 'string' ? input : input.url;
            const url = new URL(rawUrl, location.href);
            const localApi = ['127.0.0.1', 'localhost'].includes(url.hostname)
              && url.port === '8000';
            if (
              localApi
              && delayArticle
              && url.pathname === '/articles/{CRB_ARTICLE_ID}'
            ) {{
              delayArticle = false;
              await new Promise(resolve => setTimeout(resolve, 5000));
            }} else if (
              localApi
              && delayReferences
              && url.pathname === '/v1.2/articles/{CRB_ARTICLE_ID}/references'
            ) {{
              delayReferences = false;
              await new Promise(resolve => setTimeout(resolve, 11000));
            }}
            return originalFetch(input, init);
          }};
          window.__p3034DeferredHistoryFocusEvents = [];
          window.__p3034DeferredHistoryFocusObserver = event => {{
            if (event.target instanceof Element) {{
              window.__p3034DeferredHistoryFocusEvents.push(
                event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
              );
            }}
          }};
          document.addEventListener(
            'focusin',
            window.__p3034DeferredHistoryFocusObserver,
            true
          );
        }}
        """
    )
    deferred_history_started = time.monotonic()
    persistent_history_origin.evaluate("element => { element.focus(); history.back(); }")
    expect(page).to_have_url(re.compile(r"reference_page=2.*#structured-reference-"), timeout=30_000)
    expect(page_two_row).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(page_two_row, "deferred structured Reference history target")
    _require(
        time.monotonic() - deferred_history_started >= 15,
        "deferred structured Reference history probe did not cross the old Reader deadline",
    )
    deferred_history_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener(
            'focusin',
            window.__p3034DeferredHistoryFocusObserver,
            true
          );
          window.fetch = window.__p3034DeferredHistoryFetch;
          delete window.__p3034DeferredHistoryFetch;
          return window.__p3034DeferredHistoryFocusEvents;
        }
        """
    )
    _require(
        "shell-main-content" not in deferred_history_focus_events,
        "Shell focused main before the deferred structured Reference owner: "
        f"{deferred_history_focus_events}",
    )

    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=30_000)
    page.evaluate(
        f"""
        () => {{
          const originalFetch = window.fetch.bind(window);
          let delayArticle = true;
          let delayReferences = true;
          window.__p3034CanceledHistoryFetch = originalFetch;
          window.fetch = async (input, init) => {{
            const rawUrl = typeof input === 'string' ? input : input.url;
            const url = new URL(rawUrl, location.href);
            if (
              delayArticle
              && ['127.0.0.1', 'localhost'].includes(url.hostname)
              && url.port === '8000'
              && url.pathname === '/articles/{CRB_ARTICLE_ID}'
            ) {{
              delayArticle = false;
              await new Promise(resolve => setTimeout(resolve, 2500));
            }} else if (
              delayReferences
              && ['127.0.0.1', 'localhost'].includes(url.hostname)
              && url.port === '8000'
              && url.pathname === '/v1.2/articles/{CRB_ARTICLE_ID}/references'
            ) {{
              delayReferences = false;
              await new Promise(resolve => setTimeout(resolve, 2500));
            }}
            return originalFetch(input, init);
          }};
          window.__p3034CanceledHistoryFocusEvents = [];
          window.__p3034CanceledHistoryFocusObserver = event => {{
            if (event.target instanceof Element) {{
              window.__p3034CanceledHistoryFocusEvents.push(
                event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
              );
            }}
          }};
          document.addEventListener(
            'focusin',
            window.__p3034CanceledHistoryFocusObserver,
            true
          );
        }}
        """
    )
    canceled_history_origin = page.get_by_test_id("primary-nav-dashboard")
    canceled_history_origin.evaluate("element => { element.focus(); history.back(); }")
    expect(page).to_have_url(re.compile(r"reference_page=2.*#structured-reference-"), timeout=30_000)
    expect(page.get_by_text("Loading article", exact=True)).to_be_visible(timeout=5_000)
    page.keyboard.press("Tab")
    canceled_history_user_focus = page.get_by_test_id("primary-nav-library")
    expect(canceled_history_user_focus).to_be_focused()
    expect(page.get_by_text("Loading references...", exact=True)).to_be_visible(timeout=30_000)
    expect(page_two_row).to_be_visible(timeout=30_000)
    _wait_for_animation_frames(page, 5)
    expect(page_two_row).not_to_be_focused()
    expect(canceled_history_user_focus).to_be_focused()
    canceled_history_focus_events = page.evaluate(
        """
        targetId => {
          document.removeEventListener(
            'focusin',
            window.__p3034CanceledHistoryFocusObserver,
            true
          );
          window.fetch = window.__p3034CanceledHistoryFetch;
          delete window.__p3034CanceledHistoryFetch;
          return {
            events: window.__p3034CanceledHistoryFocusEvents,
            targetId,
          };
        }
        """,
        f"structured-reference-{page_two_only_reference_id}",
    )
    _require(
        canceled_history_focus_events["targetId"]
        not in canceled_history_focus_events["events"],
        "user keyboard focus did not cancel deferred structured Reference focus: "
        f"{canceled_history_focus_events['events']}",
    )
    _require(
        "shell-main-content" not in canceled_history_focus_events["events"],
        "Shell main fallback overrode acquisition-time user focus: "
        f"{canceled_history_focus_events['events']}",
    )

    def provide_empty_reference_page_two(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [],
                    "total": 0,
                    "page": 2,
                    "page_size": 20,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False,
                    "article_id": CRB_ARTICLE_ID,
                    "reference_type": None,
                    "classification": None,
                }
            ),
        )

    page.route(page_two_pattern, provide_empty_reference_page_two)
    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=30_000)
    terminal_history_origin = page.get_by_test_id("primary-nav-dashboard")
    terminal_history_started = time.monotonic()
    terminal_history_origin.evaluate("element => { element.focus(); history.back(); }")
    expect(page).to_have_url(
        re.compile(r"reference_page=2.*#structured-reference-"),
        timeout=30_000,
    )
    expect(page.get_by_text("No structured references for this article.", exact=True)).to_be_visible(
        timeout=5_000
    )
    terminal_history_main = page.get_by_test_id("shell-main-content")
    expect(terminal_history_main).to_be_focused(timeout=5_000)
    _require_visible_focus(terminal_history_main, "terminal structured Reference fallback")
    _require(
        time.monotonic() - terminal_history_started < 8,
        "terminal structured Reference state held focus ownership until the timeout",
    )
    page.unroute(page_two_pattern, provide_empty_reference_page_two)

    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=30_000)
    page.evaluate(
        f"""
        () => {{
          const originalFetch = window.fetch.bind(window);
          window.__p3034ReferenceTimeoutFetch = originalFetch;
          window.fetch = (input, init) => {{
            const rawUrl = typeof input === 'string' ? input : input.url;
            const url = new URL(rawUrl, location.href);
            if (
              ['127.0.0.1', 'localhost'].includes(url.hostname)
              && url.port === '8000'
              && url.pathname === '/v1.2/articles/{CRB_ARTICLE_ID}/references'
              && url.searchParams.get('page') === '2'
            ) {{
              return new Promise(() => {{}});
            }}
            return originalFetch(input, init);
          }};
        }}
        """
    )
    timeout_history_origin = page.get_by_test_id("primary-nav-dashboard")
    timeout_history_started = time.monotonic()
    timeout_history_origin.evaluate("element => { element.focus(); history.back(); }")
    expect(page).to_have_url(
        re.compile(r"reference_page=2.*#structured-reference-"),
        timeout=30_000,
    )
    expect(page.get_by_text("Loading references...", exact=True)).to_be_visible(timeout=30_000)
    timeout_history_main = page.get_by_test_id("shell-main-content")
    page.wait_for_timeout(2_000)
    expect(timeout_history_main).not_to_be_focused()
    expect(timeout_history_main).to_be_focused(timeout=23_000)
    _require_visible_focus(timeout_history_main, "timed-out structured Reference fallback")
    _require(
        19 <= time.monotonic() - timeout_history_started < 28,
        "deferred structured Reference timeout did not release Reader focus ownership on time",
    )
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3034ReferenceTimeoutFetch;
          delete window.__p3034ReferenceTimeoutFetch;
        }
        """
    )

    page.unroute(isolated_focus_session_pattern, provide_isolated_focus_session)
    page.unroute(isolated_focus_session_end_pattern, provide_isolated_focus_session_end)
    page.unroute(page_two_pattern, provide_reference_page_two)
    checks["reference_page_two_owned_return_focus"] = True

    out_of_range_pattern = re.compile(r".*/v1\.2/references\?.*")
    out_of_range_requests: list[int] = []

    def provide_out_of_range_page(route) -> None:
        parsed = urlparse(route.request.url)
        query = parse_qs(parsed.query)
        if query.get("q", [""])[0] != "p3-033-out-of-range":
            route.continue_()
            return
        requested_page = int(query.get("page", ["1"])[0])
        out_of_range_requests.append(requested_page)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [
                        {**selected_record, "source_article_title": "LAST AVAILABLE PAGE"}
                    ] if requested_page == 3 else [],
                    "total": 41,
                    "page": requested_page,
                    "page_size": 20,
                    "total_pages": 3,
                    "has_next": requested_page < 3,
                    "has_previous": requested_page > 1,
                    "reference_type": None,
                    "classification": None,
                    "query": "p3-033-out-of-range",
                }
            ),
        )

    page.route(out_of_range_pattern, provide_out_of_range_page)
    out_of_range_url = f"{FRONTEND_URL}/zotero?q=p3-033-out-of-range&page=100000"
    corrected_range_url = f"{FRONTEND_URL}/zotero?q=p3-033-out-of-range&page=3"
    out_of_range_canonicalization = _declare_expected_route_transition(
        page,
        destination_url=corrected_range_url,
        request_page_url=out_of_range_url,
    )
    page.goto(out_of_range_url, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page).to_have_url(corrected_range_url, timeout=30_000)
    _complete_expected_route_transition(page, out_of_range_canonicalization)
    expect(page.get_by_text("LAST AVAILABLE PAGE", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_text("No references match these filters.", exact=True)).to_have_count(0)
    _require(
        out_of_range_requests == [100000, 3],
        f"out-of-range page did not canonicalize exactly once: {out_of_range_requests}",
    )
    page.unroute(out_of_range_pattern, provide_out_of_range_page)
    checks["reference_out_of_range_page_canonicalization"] = True

    pagination_pattern = re.compile(r".*/v1\.2/references\?.*")

    def provide_reference_pagination(route) -> None:
        query = parse_qs(urlparse(route.request.url).query)
        if query.get("q", [""])[0] != "p3-033-pagination":
            route.continue_()
            return
        requested_page = int(query.get("page", ["1"])[0])
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [
                        {
                            **selected_record,
                            "source_article_title": f"PAGINATION PAGE {requested_page}",
                        }
                    ],
                    "total": 41,
                    "page": requested_page,
                    "page_size": 20,
                    "total_pages": 3,
                    "has_next": requested_page < 3,
                    "has_previous": requested_page > 1,
                    "reference_type": None,
                    "classification": None,
                    "query": "p3-033-pagination",
                }
            ),
        )

    page.route(pagination_pattern, provide_reference_pagination)
    page.goto(
        f"{FRONTEND_URL}/zotero?q=p3-033-pagination",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(page)
    review_workspace = page.get_by_test_id("reference-review-workspace")
    results_heading = page.get_by_role("heading", name="Reference results", exact=True)
    result_pages = review_workspace.get_by_role(
        "navigation", name="Reference result pages", exact=True
    )
    expect(review_workspace.get_by_text("PAGINATION PAGE 1", exact=True)).to_be_visible(
        timeout=30_000
    )
    pagination_page_two_url = f"{FRONTEND_URL}/zotero?q=p3-033-pagination&page=2"
    pagination_next_transition = _declare_expected_route_transition(
        page,
        destination_url=pagination_page_two_url,
    )
    result_pages.get_by_role("button", name="Next", exact=True).click()
    expect(page).to_have_url(pagination_page_two_url, timeout=30_000)
    expect(review_workspace.get_by_text("PAGINATION PAGE 2", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(results_heading).to_be_focused(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, pagination_next_transition)
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    review_workspace = page.get_by_test_id("reference-review-workspace")
    results_heading = page.get_by_role("heading", name="Reference results", exact=True)
    result_pages = review_workspace.get_by_role(
        "navigation", name="Reference result pages", exact=True
    )
    expect(review_workspace.get_by_text("PAGINATION PAGE 2", exact=True)).to_be_visible(
        timeout=30_000
    )
    pagination_page_one_url = f"{FRONTEND_URL}/zotero?q=p3-033-pagination"
    pagination_previous_transition = _declare_expected_route_transition(
        page,
        destination_url=pagination_page_one_url,
    )
    result_pages.get_by_role("button", name="Previous", exact=True).click()
    expect(page).to_have_url(pagination_page_one_url, timeout=30_000)
    expect(review_workspace.get_by_text("PAGINATION PAGE 1", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(results_heading).to_be_focused(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, pagination_previous_transition)
    pagination_back_transition = _declare_expected_route_transition(
        page,
        destination_url=pagination_page_two_url,
    )
    page.go_back()
    expect(page).to_have_url(pagination_page_two_url, timeout=30_000)
    expect(review_workspace.get_by_text("PAGINATION PAGE 2", exact=True)).to_be_visible(
        timeout=30_000
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, pagination_back_transition)
    pagination_forward_transition = _declare_expected_route_transition(
        page,
        destination_url=pagination_page_one_url,
    )
    page.go_forward()
    expect(page).to_have_url(pagination_page_one_url, timeout=30_000)
    expect(review_workspace.get_by_text("PAGINATION PAGE 1", exact=True)).to_be_visible(
        timeout=30_000
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, pagination_forward_transition)
    page.unroute(pagination_pattern, provide_reference_pagination)
    checks["reference_pagination_reload_history"] = True

    page.goto(selected_url, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    review_workspace = page.get_by_test_id("reference-review-workspace")
    expect(page.get_by_test_id("selected-reference-detail")).to_have_attribute(
        "data-reference-id", str(reference_id), timeout=30_000
    )
    review_workspace.get_by_label("Search references", exact=True).fill("10.1000")
    review_workspace.locator("#reference-type").select_option("doi")
    filtered_url = f"{FRONTEND_URL}/zotero?q=10.1000&reference_type=doi"
    filtered_transition = _declare_expected_route_transition(
        page,
        destination_url=filtered_url,
    )
    review_workspace.get_by_role(
        "button", name="Search structured references", exact=True
    ).click()
    results_heading = page.get_by_role("heading", name="Reference results", exact=True)
    expect(results_heading).to_be_focused(timeout=30_000)
    expect(page).to_have_url(re.compile(r"/zotero\?q=10\.1000&reference_type=doi"), timeout=30_000)
    expect(page.get_by_test_id("selected-reference-detail")).to_have_count(0)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, filtered_transition)
    filtered_url = page.url
    filtered_back_transition = _declare_expected_route_transition(
        page,
        destination_url=selected_url,
    )
    page.go_back()
    expect(page).to_have_url(selected_url, timeout=30_000)
    expect(page.get_by_test_id("selected-reference-detail")).to_have_attribute(
        "data-reference-id", str(reference_id), timeout=30_000
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, filtered_back_transition)
    filtered_forward_transition = _declare_expected_route_transition(
        page,
        destination_url=filtered_url,
    )
    page.go_forward()
    expect(page).to_have_url(filtered_url, timeout=30_000)
    expect(page.get_by_role("heading", name="Reference results", exact=True)).to_be_visible()
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, filtered_forward_transition)
    checks["reference_filter_url_history_restore"] = True

    result_buttons = page.get_by_test_id("reference-result-list").locator("button")
    expect(result_buttons.first).to_be_visible(timeout=30_000)
    selected_filter_reference_id = str(
        result_buttons.first.get_attribute("data-reference-id") or ""
    )
    _require(
        bool(selected_filter_reference_id),
        "filtered reference result is missing its reference identity",
    )
    selected_filter_url = (
        f"{filtered_url}&{urlencode({'reference_id': selected_filter_reference_id})}"
    )
    selected_filter_transition = _declare_expected_route_transition(
        page,
        destination_url=selected_filter_url,
    )
    result_buttons.first.click()
    selected_detail = page.get_by_test_id("selected-reference-detail")
    expect(selected_detail).to_be_focused(timeout=30_000)
    _complete_expected_route_transition(page, selected_filter_transition)
    requests_before_candidate_filter = len(reference_api_requests)
    review_workspace.get_by_label("Search references", exact=True).fill(
        "unsaved candidate navigation draft"
    )
    unmatched_url = f"{page.url}&candidate=unmatched"
    unmatched_transition = _declare_expected_route_transition(
        page,
        destination_url=unmatched_url,
    )
    page.get_by_role("button", name="Unmatched", exact=True).click()
    unmatched_filter = page.get_by_role("button", name="Unmatched", exact=True)
    expect(unmatched_filter).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(unmatched_filter, "candidate filter")
    expect(unmatched_filter).to_have_attribute("aria-pressed", "true")
    expect(review_workspace.get_by_label("Search references", exact=True)).to_have_value(
        "unsaved candidate navigation draft"
    )
    _require("candidate=unmatched" in page.url, f"candidate filter is not canonical URL state: {page.url}")
    page.wait_for_timeout(250)
    _require(
        len(reference_api_requests) == requests_before_candidate_filter,
        "local candidate filtering unexpectedly re-fetched reference APIs: "
        f"before={requests_before_candidate_filter}, after={len(reference_api_requests)}",
    )
    checks["reference_candidate_filter_focus_and_url"] = True
    checks["reference_candidate_filter_is_local"] = True
    _complete_expected_route_transition(page, unmatched_transition)
    unmatched_url = page.url
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    review_workspace = page.get_by_test_id("reference-review-workspace")
    expect(review_workspace.get_by_role("button", name="Unmatched", exact=True)).to_have_attribute(
        "aria-pressed", "true", timeout=30_000
    )
    candidate_filter_back_transition = _declare_expected_route_transition(
        page,
        destination_url=selected_filter_url,
        request_page_url=selected_filter_url,
    )
    page.go_back()
    expect(review_workspace.get_by_role("button", name="All", exact=True)).to_have_attribute(
        "aria-pressed", "true", timeout=30_000
    )
    _complete_expected_route_transition(page, candidate_filter_back_transition)
    candidate_filter_forward_transition = _declare_expected_route_transition(
        page,
        destination_url=unmatched_url,
        request_page_url=unmatched_url,
    )
    page.go_forward()
    expect(page).to_have_url(unmatched_url, timeout=30_000)
    expect(review_workspace.get_by_role("button", name="Unmatched", exact=True)).to_have_attribute(
        "aria-pressed", "true", timeout=30_000
    )
    _complete_expected_route_transition(page, candidate_filter_forward_transition)
    checks["reference_candidate_filter_reload_history"] = True

    failure_pattern = re.compile(r".*/v1\.2/references\?.*")
    failed_attempts = {"count": 0}
    reference_list_failures = _declare_expected_http_errors(
        console_errors,
        label="P3-033 reference review",
        page_url=f"{FRONTEND_URL}/zotero?q=p3-033-failure",
        source_url=(
            f"{BROWSER_API_URL}/v1.2/references?page=1&page_size=20&q=p3-033-failure"
        ),
        count=2,
    )

    def fail_reference_results_once(route) -> None:
        parsed = urlparse(route.request.url)
        query = parse_qs(parsed.query).get("q", [""])[0]
        if query == "p3-033-failure" and failed_attempts["count"] < 2:
            failed_attempts["count"] += 1
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=page,
                expectation_ids=reference_list_failures,
                body=json.dumps(
                    {
                        "detail": (
                            "intentional P3-033 reference result failure "
                            f"{failed_attempts['count']}"
                        )
                    }
                ),
            )
            return
        route.continue_()

    page.route(failure_pattern, fail_reference_results_once)
    review_workspace.get_by_label("Search references", exact=True).fill("p3-033-failure")
    review_workspace.locator("#reference-type").select_option("")
    failure_results_url = f"{FRONTEND_URL}/zotero?q=p3-033-failure"
    failure_results_transition = _declare_expected_route_transition(
        page,
        destination_url=failure_results_url,
    )
    review_workspace.get_by_role(
        "button", name="Search structured references", exact=True
    ).click()
    expect(review_workspace.get_by_role("alert")).to_contain_text(
        "intentional P3-033 reference result failure 1", timeout=30_000
    )
    expect(page).to_have_url(failure_results_url, timeout=30_000)
    _complete_expected_route_transition(page, failure_results_transition)
    page.evaluate(
        """
        () => {
          const originalFetch = window.fetch.bind(window);
          window.__p3033PendingListRetryFetch = originalFetch;
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const url = new URL(target);
            if (url.pathname === '/v1.2/references'
                && url.searchParams.get('q') === 'p3-033-failure') {
              await new Promise(resolve => setTimeout(resolve, 600));
            }
            return originalFetch(...args);
          };
        }
        """
    )
    review_workspace.get_by_role("button", name="Retry reference results", exact=True).click()
    expect(results_heading).to_be_focused(timeout=1_000)
    expect(page.get_by_text("Loading reference results...", exact=True)).to_be_visible(
        timeout=1_000
    )
    expect(review_workspace.get_by_role("alert")).to_contain_text(
        "intentional P3-033 reference result failure 2", timeout=30_000
    )
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=reference_list_failures,
    )
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3033PendingListRetryFetch;
          delete window.__p3033PendingListRetryFetch;
        }
        """
    )
    expect(results_heading).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(results_heading, "failed reference result retry destination")
    review_workspace.get_by_role("button", name="Retry reference results", exact=True).click()
    expect(page.get_by_text("No references match these filters.", exact=True)).to_be_visible(timeout=30_000)
    expect(results_heading).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(results_heading, "reference result retry destination")
    _require(failed_attempts["count"] == 2, "reference failure/retry probe did not intercept twice")
    page.unroute(failure_pattern, fail_reference_results_once)
    checks["reference_result_failure_retry_truth"] = True
    _wait_for_page_requests_to_settle(page, console_errors)

    reference_reset_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/zotero",
        allow_speculative_cancellations=True,
    )
    page.goto(f"{FRONTEND_URL}/zotero", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    review_workspace = page.get_by_test_id("reference-review-workspace")
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, reference_reset_transition)
    page.evaluate(
        """
        async apiBase => {
          const originalFetch = window.fetch.bind(window);
          const response = await originalFetch(`${apiBase}/v1.2/references?page=1&page_size=1`);
          const seed = (await response.json()).items[0];
          window.__p3033ListOriginalFetch = originalFetch;
          window.__p3033ListRequests = [];
          const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const url = new URL(target);
            if (url.pathname !== '/v1.2/references') return originalFetch(...args);
            const query = url.searchParams.get('q');
            if (!['p3-033-slow-list', 'p3-033-fast-list'].includes(query)) {
              return originalFetch(...args);
            }
            window.__p3033ListRequests.push(query);
            if (query === 'p3-033-slow-list') await wait(800);
            const label = query === 'p3-033-slow-list' ? 'STALE LIST A' : 'CURRENT LIST B';
            return new Response(JSON.stringify({
              items: [{ ...seed, source_article_title: label }],
              total: 1, page: 1, page_size: 20, total_pages: 1,
              has_next: false, has_previous: false, query,
            }), { status: 200, headers: { 'Content-Type': 'application/json' } });
          };
        }
        """,
        "http://localhost:8000",
    )
    review_workspace.get_by_label("Search references", exact=True).fill("p3-033-slow-list")
    slow_list_url = f"{FRONTEND_URL}/zotero?q=p3-033-slow-list"
    slow_list_transition = _declare_expected_route_transition(
        page,
        destination_url=slow_list_url,
    )
    review_workspace.get_by_role(
        "button", name="Search structured references", exact=True
    ).click()
    page.wait_for_function(
        "() => window.__p3033ListRequests?.includes('p3-033-slow-list')",
        timeout=30_000,
    )
    expect(page).to_have_url(slow_list_url, timeout=30_000)
    _complete_expected_route_transition(page, slow_list_transition)
    expect(review_workspace.get_by_role(
        "button", name="Search structured references", exact=True
    )).to_be_enabled(
        timeout=30_000
    )
    review_workspace.get_by_label("Search references", exact=True).fill("p3-033-fast-list")
    fast_list_url = f"{FRONTEND_URL}/zotero?q=p3-033-fast-list"
    fast_list_transition = _declare_expected_route_transition(
        page,
        destination_url=fast_list_url,
    )
    review_workspace.get_by_role(
        "button", name="Search structured references", exact=True
    ).click()
    expect(review_workspace.get_by_text("CURRENT LIST B", exact=True)).to_be_visible(timeout=30_000)
    expect(page).to_have_url(fast_list_url, timeout=30_000)
    _complete_expected_route_transition(page, fast_list_transition)
    page.wait_for_timeout(1_000)
    expect(review_workspace.get_by_text("STALE LIST A", exact=True)).to_have_count(0)
    _require(
        page.evaluate("window.__p3033ListRequests")
        == ["p3-033-slow-list", "p3-033-fast-list"],
        f"list ownership probe emitted unexpected requests: "
        f"{page.evaluate('window.__p3033ListRequests')}",
    )
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3033ListOriginalFetch;
          delete window.__p3033ListOriginalFetch;
          delete window.__p3033ListRequests;
        }
        """
    )
    checks["reference_list_request_ownership"] = True
    _wait_for_page_requests_to_settle(page, console_errors)

    page.goto(f"{FRONTEND_URL}/zotero", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    review_workspace = page.get_by_test_id("reference-review-workspace")
    race_buttons = review_workspace.get_by_test_id("reference-result-list").locator("button")
    page.wait_for_function(
        "() => document.querySelectorAll('[data-testid=reference-result-list] button[data-reference-id]').length >= 2",
        timeout=30_000,
    )
    race_ids = race_buttons.evaluate_all(
        "nodes => nodes.slice(0, 2).map(node => node.getAttribute('data-reference-id'))"
    )
    _require(
        len(race_ids) == 2 and all(race_ids) and race_ids[0] != race_ids[1],
        f"reference race needs two distinct result records: {race_ids}",
    )
    race_a, race_b = map(str, race_ids)

    outside_record = _api_json(
        context,
        "GET",
        f"/v1.2/references/{race_b}?provenance_limit=1",
    )["record"]
    outside_page_pattern = re.compile(r".*/v1\.2/references\?.*")

    def provide_outside_selected_page(route) -> None:
        query = parse_qs(urlparse(route.request.url).query)
        if query.get("q", [""])[0] != "p3-033-outside-page":
            route.continue_()
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [outside_record],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 1,
                    "has_next": False,
                    "has_previous": False,
                    "reference_type": None,
                    "classification": None,
                    "query": "p3-033-outside-page",
                }
            ),
        )

    page.route(outside_page_pattern, provide_outside_selected_page)
    page.goto(
        f"{FRONTEND_URL}/zotero?{urlencode({'q': 'p3-033-outside-page', 'reference_id': race_a})}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("selected-reference-detail")).to_have_attribute(
        "data-reference-id", race_a, timeout=30_000
    )
    expect(page.get_by_text(
        "The selected deep-linked reference is outside this result page and remains available below.",
        exact=True,
    )).to_be_visible()
    page.unroute(outside_page_pattern, provide_outside_selected_page)
    checks["reference_outside_page_deep_link"] = True

    zero_candidate_pattern = re.compile(
        r".*/v1\.2/references/[^/?]+/zotero-candidates(?:\?.*)?$"
    )

    def provide_zero_candidates(route) -> None:
        selected_id = unquote(urlparse(route.request.url).path.split("/")[-2])
        if selected_id != race_a:
            route.continue_()
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [],
                    "total": 0,
                    "limit": 20,
                    "truncated": False,
                    "reference_id": race_a,
                    "decision": None,
                }
            ),
        )

    page.route(zero_candidate_pattern, provide_zero_candidates)
    zero_candidate_url = (
        f"{FRONTEND_URL}/zotero?{urlencode({'reference_id': race_a})}"
    )
    zero_candidate_transition = _declare_expected_route_transition(
        page,
        destination_url=zero_candidate_url,
        allow_speculative_cancellations=True,
    )
    page.goto(
        zero_candidate_url,
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(page)
    expect(page.get_by_text(
        "No Zotero match candidates were recorded for this reference.", exact=True
    )).to_be_visible(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, zero_candidate_transition)
    page.unroute(zero_candidate_pattern, provide_zero_candidates)
    checks["reference_zero_candidate_state"] = True

    page.goto(f"{FRONTEND_URL}/zotero", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    review_workspace = page.get_by_test_id("reference-review-workspace")
    race_buttons = review_workspace.get_by_test_id("reference-result-list").locator("button")
    page.wait_for_function(
        "() => document.querySelectorAll('[data-testid=reference-result-list] button[data-reference-id]').length >= 2",
        timeout=30_000,
    )
    expect(race_buttons.nth(0)).to_have_attribute("data-reference-id", race_a)
    expect(race_buttons.nth(1)).to_have_attribute("data-reference-id", race_b)

    wrong_detail_attempts = {"identity": False, "retry_failure": False}
    detail_pattern = re.compile(r".*/v1\.2/references/[^/?]+(?:\?.*)?$")
    detail_retry_failure = _declare_expected_http_errors(
        console_errors,
        label="P3-033 reference review",
        page_url=f"{FRONTEND_URL}/zotero?{urlencode({'reference_id': race_a})}",
        source_url=f"{BROWSER_API_URL}/v1.2/references/{race_a}?provenance_limit=20",
    )

    def return_wrong_detail_identity_once(route) -> None:
        selected_id = unquote(urlparse(route.request.url).path.rsplit("/", 1)[-1])
        if selected_id != race_a:
            route.continue_()
            return
        if wrong_detail_attempts["identity"]:
            if not wrong_detail_attempts["retry_failure"]:
                wrong_detail_attempts["retry_failure"] = True
                _fulfill_expected_http_error(
                    route,
                    console_errors=console_errors,
                    page=page,
                    expectation_ids=detail_retry_failure,
                    body=json.dumps({"detail": "intentional detail retry failure"}),
                )
                return
            route.continue_()
            return
        wrong_detail_attempts["identity"] = True
        response = route.fetch(max_redirects=0)
        _require(
            response.url == route.request.url and 200 <= response.status < 300,
            "reference detail source redirected or failed: "
            f"expected_url={route.request.url} actual_url={response.url} "
            f"status={response.status}",
        )
        payload = response.json()
        payload["record"]["reference_id"] = "unexpected-detail-identity"
        route.fulfill(
            status=response.status,
            content_type="application/json",
            body=json.dumps(payload),
        )

    page.route(detail_pattern, return_wrong_detail_identity_once)
    wrong_detail_selection = _declare_expected_route_transition(
        page,
        destination_url=selected_reference_url(race_a),
    )
    race_buttons.nth(0).click()
    expect(review_workspace.get_by_role("alert")).to_contain_text(
        "unexpected identity", timeout=30_000
    )
    _complete_expected_route_transition(page, wrong_detail_selection)
    page.evaluate(
        """
        referenceId => {
          const originalFetch = window.fetch.bind(window);
          window.__p3033PendingDetailRetryFetch = originalFetch;
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const url = new URL(target);
            if (url.pathname === `/v1.2/references/${encodeURIComponent(referenceId)}`) {
              await new Promise(resolve => setTimeout(resolve, 600));
            }
            return originalFetch(...args);
          };
        }
        """,
        race_a,
    )
    review_workspace.get_by_role("button", name="Retry selected reference", exact=True).click()
    selected_reference_region = review_workspace.get_by_test_id("selected-reference-region")
    expect(selected_reference_region).to_be_focused(timeout=1_000)
    expect(page.get_by_text("Loading selected reference...", exact=True)).to_be_visible(
        timeout=1_000
    )
    expect(review_workspace.get_by_role("alert")).to_contain_text(
        "intentional detail retry failure", timeout=30_000
    )
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=detail_retry_failure,
    )
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3033PendingDetailRetryFetch;
          delete window.__p3033PendingDetailRetryFetch;
        }
        """
    )
    expect(review_workspace.get_by_role("alert")).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(
        review_workspace.get_by_role("alert"),
        "failed detail retry destination",
    )
    page.unroute(detail_pattern, return_wrong_detail_identity_once)
    review_workspace.get_by_role("button", name="Retry selected reference", exact=True).click()
    selected_a = page.get_by_test_id("selected-reference-detail")
    expect(selected_a).to_have_attribute("data-reference-id", race_a, timeout=30_000)
    expect(selected_a).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(selected_a, "detail identity retry destination")
    _require(
        all(wrong_detail_attempts.values()),
        f"detail identity/retry probes did not both run: {wrong_detail_attempts}",
    )

    wrong_candidate_attempts = {"identity": False, "retry_failure": False}
    candidate_identity_pattern = re.compile(
        r".*/v1\.2/references/[^/?]+/zotero-candidates(?:\?.*)?$"
    )
    candidate_retry_failure = _declare_expected_http_errors(
        console_errors,
        label="P3-033 reference review",
        page_url=f"{FRONTEND_URL}/zotero?{urlencode({'reference_id': race_b})}",
        source_url=(
            f"{BROWSER_API_URL}/v1.2/references/{race_b}/zotero-candidates?limit=20"
        ),
    )

    def return_wrong_candidate_identity_once(route) -> None:
        selected_id = unquote(urlparse(route.request.url).path.split("/")[-2])
        if selected_id != race_b:
            route.continue_()
            return
        if wrong_candidate_attempts["identity"]:
            if not wrong_candidate_attempts["retry_failure"]:
                wrong_candidate_attempts["retry_failure"] = True
                _fulfill_expected_http_error(
                    route,
                    console_errors=console_errors,
                    page=page,
                    expectation_ids=candidate_retry_failure,
                    body=json.dumps({"detail": "intentional candidate retry failure"}),
                )
                return
            route.continue_()
            return
        wrong_candidate_attempts["identity"] = True
        response = route.fetch(max_redirects=0)
        _require(
            response.url == route.request.url and 200 <= response.status < 300,
            "reference candidate source redirected or failed: "
            f"expected_url={route.request.url} actual_url={response.url} "
            f"status={response.status}",
        )
        payload = response.json()
        payload["reference_id"] = "unexpected-candidate-identity"
        route.fulfill(
            status=response.status,
            content_type="application/json",
            body=json.dumps(payload),
        )

    page.route(candidate_identity_pattern, return_wrong_candidate_identity_once)
    wrong_candidate_selection = _declare_expected_route_transition(
        page,
        destination_url=selected_reference_url(race_b),
    )
    race_buttons.nth(1).click()
    expect(selected_a).to_have_count(0, timeout=1_000)
    expect(page.get_by_test_id("selected-reference-detail")).to_have_attribute(
        "data-reference-id", race_b, timeout=30_000
    )
    expect(review_workspace.get_by_role("alert")).to_contain_text(
        "unexpected reference identity", timeout=30_000
    )
    _complete_expected_route_transition(page, wrong_candidate_selection)
    page.evaluate(
        """
        referenceId => {
          const originalFetch = window.fetch.bind(window);
          window.__p3033PendingCandidateRetryFetch = originalFetch;
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const url = new URL(target);
            if (url.pathname === `/v1.2/references/${encodeURIComponent(referenceId)}/zotero-candidates`) {
              await new Promise(resolve => setTimeout(resolve, 600));
            }
            return originalFetch(...args);
          };
        }
        """,
        race_b,
    )
    review_workspace.get_by_role("button", name="Retry Zotero candidates", exact=True).click()
    all_filter = review_workspace.get_by_role("button", name="All", exact=True)
    expect(all_filter).to_be_focused(timeout=1_000)
    expect(page.get_by_text("Loading Zotero candidates...", exact=True)).to_be_visible(
        timeout=1_000
    )
    expect(review_workspace.get_by_role("alert")).to_contain_text(
        "intentional candidate retry failure", timeout=30_000
    )
    _wait_for_declared_http_errors(
        page,
        console_errors,
        expectation_ids=candidate_retry_failure,
    )
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3033PendingCandidateRetryFetch;
          delete window.__p3033PendingCandidateRetryFetch;
        }
        """
    )
    expect(all_filter).to_be_focused(timeout=30_000)
    page.unroute(candidate_identity_pattern, return_wrong_candidate_identity_once)
    review_workspace.get_by_role("button", name="Retry Zotero candidates", exact=True).click()
    expect(all_filter).to_be_focused(timeout=30_000)
    _require_focus_in_viewport(all_filter, "candidate identity retry destination")
    expect(review_workspace.get_by_test_id("candidate-result-list")).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Loading Zotero candidates...", exact=True)).to_have_count(
        0, timeout=30_000
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    expect(all_filter).to_be_focused(timeout=30_000)
    matched_filter = review_workspace.get_by_role("button", name="Matched", exact=True)
    matched_candidate_transition = _declare_expected_route_transition(
        page,
        destination_url=candidate_filter_url("matched"),
    )
    matched_filter.click()
    expect(
        review_workspace.get_by_text(
            "No candidates in the loaded bounded set match the selected result filter.", exact=True
        )
    ).to_be_visible(timeout=30_000)
    expect(matched_filter).to_be_focused(timeout=30_000)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, matched_candidate_transition)
    _require(
        all(wrong_candidate_attempts.values()),
        f"candidate identity/retry probes did not both run: {wrong_candidate_attempts}",
    )
    checks["reference_identity_mismatch_retry_truth"] = True
    checks["reference_selection_immediate_invalidation"] = True

    page.evaluate(
        """
        ({ raceA, raceB }) => {
          const originalFetch = window.fetch.bind(window);
          window.__p3033OriginalFetch = originalFetch;
          window.__p3033CandidateRequests = [];
          window.__p3033DetailRequests = [];
          const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const detailMatch = target.match(/\/v1\.2\/references\/([^/?]+)(?:\?.*)?$/);
            if (detailMatch) {
              const referenceId = decodeURIComponent(detailMatch[1]);
              window.__p3033DetailRequests.push(referenceId);
              if (referenceId === raceA) await wait(800);
              const response = await originalFetch(...args);
              if (!window.__p3033LongResponsiveContent) return response;
              const payload = await response.json();
              payload.record.normalized_identifier =
                `10.9999/${'LONG_IDENTIFIER_SEGMENT_'.repeat(32)}`;
              payload.record.evidence_text =
                `LONG_EVIDENCE_SEGMENT_${'evidence'.repeat(120)}`;
              if (payload.evidence?.length) {
                payload.evidence[0].evidence_text =
                  `LONG_PROVENANCE_SEGMENT_${'provenance'.repeat(120)}`;
              }
              return new Response(JSON.stringify(payload), {
                status: response.status,
                headers: { 'Content-Type': 'application/json' },
              });
            }
            const match = target.match(/\/v1\.2\/references\/([^/]+)\/zotero-candidates/);
            if (!match) return originalFetch(...args);
            const referenceId = decodeURIComponent(match[1]);
            window.__p3033CandidateRequests.push(referenceId);
            if (referenceId === raceA) await wait(800);
            const title = referenceId === raceA ? 'STALE CANDIDATE A' : 'CURRENT CANDIDATE B';
            const matchedFields = window.__p3033LongResponsiveContent
              ? ['title', `LONG_CANDIDATE_FIELD_${'field'.repeat(100)}`]
              : ['title'];
            return new Response(JSON.stringify({
              items: [{
                schema_version: '1.0', candidate_id: `candidate-${referenceId}`,
                reference_id: referenceId, zotero_item_key: 'ITEM1', item_type: 'journalArticle',
                title, doi: null, url: null, arxiv_id: null, arxiv_version: null,
                match_method: 'fixture', match_score: 0.8, matched_fields: matchedFields,
                conflicting_fields: [], provenance: { evidence_ids: [], matcher_version: 'fixture' },
                decision: 'probable', matcher_version: 'fixture', zotero_snapshot_fingerprint: null,
              }],
              total: 1, limit: 20, truncated: false, reference_id: referenceId, decision: null,
            }), { status: 200, headers: { 'Content-Type': 'application/json' } });
          };
        }
        """,
        {"raceA": race_a, "raceB": race_b},
    )
    delayed_race_a_route_anchor = console_errors._event_sequence
    delayed_race_a_url = selected_reference_url(race_a)
    delayed_race_a_transition = _declare_expected_route_transition(
        page,
        destination_url=delayed_race_a_url,
    )
    race_buttons.nth(0).click()
    page.wait_for_function(
        "expected => new URL(location.href).searchParams.get('reference_id') === expected",
        arg=race_a,
        timeout=30_000,
    )
    page.wait_for_function(
        "expected => window.__p3033CandidateRequests?.includes(expected)",
        arg=race_a,
        timeout=30_000,
    )
    page.wait_for_function(
        "expected => window.__p3033DetailRequests?.includes(expected)",
        arg=race_a,
        timeout=30_000,
    )
    _wait_for_exact_route_request_to_finish(
        page,
        console_errors,
        source_url=delayed_race_a_url,
        after_sequence=delayed_race_a_route_anchor,
        expect_prefetch=False,
        require_observed_request=True,
        allow_response_backed_route_abort=True,
        cache_precursor_expectation_id=delayed_race_a_transition,
    )
    _complete_expected_route_transition(page, delayed_race_a_transition)
    second_race_button = review_workspace.get_by_test_id("reference-result-list").locator("button").nth(1)
    current_race_b_route_anchor = console_errors._event_sequence
    current_race_b_url = selected_reference_url(race_b)
    current_race_b_transition = _declare_expected_route_transition(
        page,
        destination_url=current_race_b_url,
    )
    second_race_button.click()
    expect(page.get_by_test_id("selected-reference-detail")).to_have_attribute(
        "data-reference-id", race_b, timeout=30_000
    )
    expect(page.get_by_text("CURRENT CANDIDATE B", exact=True)).to_be_visible(timeout=30_000)
    _wait_for_exact_route_request_to_finish(
        page,
        console_errors,
        source_url=current_race_b_url,
        after_sequence=current_race_b_route_anchor,
        expect_prefetch=False,
        require_observed_request=True,
        allow_response_backed_route_abort=True,
        cache_precursor_expectation_id=current_race_b_transition,
    )
    _complete_expected_route_transition(page, current_race_b_transition)
    page.wait_for_timeout(1_000)
    expect(page.get_by_test_id("selected-reference-detail")).to_have_attribute(
        "data-reference-id", race_b
    )
    expect(page.get_by_text("STALE CANDIDATE A", exact=True)).to_have_count(0)
    _require(
        page.evaluate("window.__p3033CandidateRequests") == [race_a, race_b],
        f"candidate race emitted unexpected requests: {page.evaluate('window.__p3033CandidateRequests')}",
    )
    _require(
        page.evaluate("window.__p3033DetailRequests") == [race_a, race_b],
        f"detail race emitted unexpected requests: {page.evaluate('window.__p3033DetailRequests')}",
    )
    checks["reference_candidate_request_ownership"] = True

    page.evaluate("window.__p3033LongResponsiveContent = true")
    responsive_filters = ("Matched", "Needs review", "Unmatched", "Matched")
    responsive_candidate_values = ("matched", "ambiguous", "unmatched", "matched")
    for index, viewport in enumerate((
        {"width": 1440, "height": 900},
        {"width": 390, "height": 844},
        {"width": 320, "height": 844},
        {"width": 720, "height": 450},
    )):
        page.set_viewport_size(viewport)
        target_index = index % 2
        target_id = (race_a, race_b)[target_index]
        responsive_selection_route_anchor = console_errors._event_sequence
        responsive_selection_url = selected_reference_url(target_id)
        responsive_selection_transition = _declare_expected_route_transition(
            page,
            destination_url=responsive_selection_url,
            allow_complete_precursor_snapshot=True,
        )
        review_workspace.get_by_test_id("reference-result-list").locator("button").nth(target_index).click()
        responsive_detail = page.get_by_test_id("selected-reference-detail")
        expect(responsive_detail).to_have_attribute("data-reference-id", target_id, timeout=30_000)
        expect(responsive_detail).to_be_focused(timeout=30_000)
        expect(responsive_detail).to_contain_text("LONG_IDENTIFIER_SEGMENT_")
        expect(responsive_detail).to_contain_text("LONG_EVIDENCE_SEGMENT_")
        responsive_candidates = review_workspace.get_by_test_id("candidate-result-list")
        expect(responsive_candidates).to_be_visible(timeout=30_000)
        expect(responsive_candidates).to_contain_text(
            "LONG_CANDIDATE_FIELD_", timeout=30_000
        )
        _wait_for_exact_route_request_to_finish(
            page,
            console_errors,
            source_url=responsive_selection_url,
            after_sequence=responsive_selection_route_anchor,
            expect_prefetch=False,
            require_observed_request=True,
            allow_response_backed_route_abort=True,
            cache_precursor_expectation_id=responsive_selection_transition,
        )
        _complete_expected_route_transition(page, responsive_selection_transition)
        _require_visible_focus(responsive_detail, f"{viewport['width']}x{viewport['height']} reference detail")
        _require_focus_in_viewport(responsive_detail, f"{viewport['width']}x{viewport['height']} reference detail")
        width_with_candidates = _document_width(page)
        _require(
            width_with_candidates <= viewport["width"],
            "visible candidate metadata overflowed "
            f"{viewport['width']}x{viewport['height']} to {width_with_candidates}px",
        )
        filter_button = review_workspace.get_by_role(
            "button", name=responsive_filters[index], exact=True
        )
        responsive_filter_route_anchor = console_errors._event_sequence
        responsive_filter_url = candidate_filter_url(
            responsive_candidate_values[index]
        )
        responsive_filter_transition = _declare_expected_route_transition(
            page,
            destination_url=responsive_filter_url,
            allow_complete_precursor_snapshot=True,
        )
        filter_button.click()
        expect(filter_button).to_be_focused(timeout=30_000)
        expect(filter_button).to_have_attribute("aria-pressed", "true")
        expect(responsive_detail).to_have_attribute("data-reference-id", target_id)
        if responsive_candidate_values[index] == "matched":
            expect(responsive_candidates.locator("li")).to_have_count(1)
            expect(responsive_candidates).to_contain_text(
                "STALE CANDIDATE A" if target_id == race_a else "CURRENT CANDIDATE B"
            )
        else:
            expect(responsive_candidates).to_have_count(0)
            expect(review_workspace.get_by_text(
                "No candidates in the loaded bounded set match the selected result filter.",
                exact=True,
            )).to_be_visible(timeout=30_000)
        _wait_for_exact_route_request_to_finish(
            page,
            console_errors,
            source_url=responsive_filter_url,
            after_sequence=responsive_filter_route_anchor,
            expect_prefetch=False,
            require_observed_request=True,
            allow_response_backed_route_abort=True,
            cache_precursor_expectation_id=responsive_filter_transition,
        )
        _complete_expected_route_transition(page, responsive_filter_transition)
        _require_focus_in_viewport(
            filter_button,
            f"{viewport['width']}x{viewport['height']} candidate filter",
        )
        width = _document_width(page)
        _require(
            width <= viewport["width"],
            f"reference review overflowed {viewport['width']}x{viewport['height']} to {width}px",
        )
    checks["reference_review_required_viewports"] = True

    page.evaluate(
        """
        () => {
          if (typeof window.__p3033OriginalFetch === 'function') {
            window.fetch = window.__p3033OriginalFetch;
            delete window.__p3033OriginalFetch;
            delete window.__p3033CandidateRequests;
            delete window.__p3033DetailRequests;
            delete window.__p3033LongResponsiveContent;
          }
        }
        """
    )
    context.close()
    return checks


def _verify_zotero_links_panel_integrity(
    browser,
    *,
    iteration: int,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> dict[str, bool]:
    from playwright.sync_api import expect

    checks: dict[str, bool] = {}
    kay_title = "Fundamentals of Statistical Signal Processing"
    session_sequence = 0

    def new_context(
        *,
        settings: dict[str, object] | None = None,
        viewport: dict[str, int] | None = None,
        is_mobile: bool = False,
        device_scale_factor: int = 1,
    ):
        nonlocal session_sequence
        context = browser.new_context(
            viewport=viewport or {"width": 1440, "height": 900},
            locale="zh-CN",
            is_mobile=is_mobile,
            device_scale_factor=device_scale_factor,
        )
        _install_network_guard(context, blocked_external)

        def provide_isolated_reader_session(route) -> None:
            nonlocal session_sequence
            if route.request.method != "POST":
                route.continue_()
                return
            session_sequence += 1
            route.fulfill(
                status=201,
                content_type="application/json",
                body=json.dumps(
                    {
                        "session_id": f"p3-032-{iteration}-{session_sequence}",
                        "article_id": json.loads(route.request.post_data or "{}").get(
                            "article_id"
                        ),
                        "started_at": "2026-09-05T00:00:00Z",
                        "ended_at": None,
                        "duration_seconds": None,
                        "source": "reader",
                    }
                ),
            )

        context.route(re.compile(r".*/learning/sessions$"), provide_isolated_reader_session)
        context.add_init_script(_zotero_panel_controller_script(settings or {}))
        return context

    def clear_links(context) -> None:
        for target_article in (ATTENTION_ARTICLE_ID, CRB_ARTICLE_ID):
            for item_key in ("ABCD1234", "EFGH5678"):
                response = context.request.delete(
                    f"{API_URL}/zotero/links/{target_article}/{item_key}"
                )
                _require(response.status == 204, "failed to reset isolated Zotero links")

    def seed_link(
        context,
        target_article: str,
        item_key: str,
        *,
        relation_type: str = "related",
        note: str | None = None,
    ) -> None:
        response = context.request.post(
            f"{API_URL}/zotero/links/{target_article}",
            data={
                "item_key": item_key,
                "relation_type": relation_type,
                "note": note,
            },
        )
        _require(response.status == 200, "failed to seed isolated Zotero link")

    def request_count(page, method: str, path_fragment: str) -> int:
        return int(
            page.evaluate(
                """
                ([method, pathFragment]) => window.__p3032.requests.filter(
                  request => request.method === method && request.target.includes(pathFragment)
                ).length
                """,
                [method, path_fragment],
            )
        )

    def exact_requests(page, method: str, path: str) -> list[dict[str, object]]:
        return list(
            page.evaluate(
                """
                ([method, path]) => window.__p3032.requests.filter(
                  request => request.method === method && request.path === path
                )
                """,
                [method, path],
            )
        )

    def exact_requests(page, method: str, path: str) -> list[dict[str, object]]:
        return list(
            page.evaluate(
                """
                ([method, path]) => window.__p3032.requests.filter(
                  request => request.method === method && request.path === path
                )
                """,
                [method, path],
            )
        )

    def navigate_to_crb_from_recent(page) -> None:
        recent_section = page.locator("section").filter(
            has=page.get_by_role("heading", name="Recent Reading", exact=True)
        )
        crb_reader_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
        )
        recent_section.get_by_role(
            "link", name=re.compile(rf"^{re.escape(CRB_TITLE)}")
        ).click()
        expect(page.locator("article#article-start > h1")).to_have_text(
            CRB_TITLE,
            timeout=30_000,
        )
        _wait_for_page_requests_to_settle(page, console_errors)
        _complete_expected_route_transition(page, crb_reader_transition)

    cross_context = new_context(
        settings={
            "ignoreLinksAbort": True,
            "linkDelays": {
                f"/zotero/links/{ATTENTION_ARTICLE_ID}": 700,
                f"/zotero/links/{CRB_ARTICLE_ID}": 60,
            },
            "history": {
                "id": CRB_ARTICLE_ID,
                "title": CRB_TITLE,
                "url": "https://spaces.ac.cn/archives/11787",
                "last_read_at": "2026-09-05T10:00:00.000Z",
            },
        }
    )
    clear_links(cross_context)
    seed_link(cross_context, ATTENTION_ARTICLE_ID, "ABCD1234", note="Attention context")
    seed_link(cross_context, CRB_ARTICLE_ID, "EFGH5678", relation_type="background")
    cross_page = _new_observed_page(
        cross_context,
        console_errors,
        page_errors,
        label=f"p3-032-cross-article-{iteration}",
    )
    cross_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(cross_page)
    cross_panel = cross_page.get_by_test_id("zotero-links-panel")
    expect(cross_panel.get_by_text("Loading related papers...", exact=True)).to_be_visible()
    recent_section = cross_page.locator("section").filter(
        has=cross_page.get_by_role("heading", name="Recent Reading", exact=True)
    )
    crb_history_link = recent_section.get_by_role(
        "link", name=re.compile(rf"^{re.escape(CRB_TITLE)}")
    )
    expect(crb_history_link).to_be_visible(timeout=30_000)
    cross_article_transition = _declare_expected_route_transition(
        cross_page,
        destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
    )
    crb_history_link.click()
    expect(cross_page.locator("article#article-start > h1")).to_have_text(
        CRB_TITLE,
        timeout=30_000,
    )
    crb_panel = cross_page.get_by_test_id("zotero-links-panel")
    expect(crb_panel.get_by_role("heading", name=kay_title, exact=True)).to_be_visible(
        timeout=30_000
    )
    _wait_for_page_requests_to_settle(cross_page, console_errors)
    _complete_expected_route_transition(cross_page, cross_article_transition)
    cross_page.wait_for_timeout(900)
    expect(
        crb_panel.get_by_role("heading", name="Attention Is All You Need", exact=True)
    ).to_have_count(0)
    _require(
        request_count(cross_page, "GET", f"/zotero/links/{CRB_ARTICLE_ID}") == 1,
        "Article B did not issue exactly one canonical Zotero link-list request",
    )
    _require(
        request_count(cross_page, "POST", "/zotero/links/") == 0
        and request_count(cross_page, "DELETE", "/zotero/links/") == 0,
        "Article transition issued an unintended Zotero mutation",
    )
    checks["zotero_cross_article_context_ownership"] = True
    cross_context.close()

    cross_settings = {
        "history": {
            "id": CRB_ARTICLE_ID,
            "title": CRB_TITLE,
            "url": "https://spaces.ac.cn/archives/11787",
            "last_read_at": "2026-09-05T10:00:00.000Z",
        }
    }

    stale_search_context = new_context(
        settings={
            **cross_settings,
            "ignoreSearchAbort": True,
            "searchDelays": {"attention": 700},
        }
    )
    clear_links(stale_search_context)
    seed_link(stale_search_context, ATTENTION_ARTICLE_ID, "ABCD1234")
    seed_link(stale_search_context, CRB_ARTICLE_ID, "EFGH5678")
    stale_search_page = _new_observed_page(
        stale_search_context,
        console_errors,
        page_errors,
        label=f"p3-032-cross-search-{iteration}",
    )
    stale_search_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(stale_search_page)
    stale_search_panel = stale_search_page.get_by_test_id("zotero-links-panel")
    expect(stale_search_panel.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible(timeout=30_000)
    stale_search_panel.get_by_label("Paper title or keyword", exact=True).fill("attention")
    stale_search_panel.get_by_label("Paper title or keyword", exact=True).press("Enter")
    expect(stale_search_panel.get_by_text("Searching Zotero...", exact=True)).to_be_visible()
    navigate_to_crb_from_recent(stale_search_page)
    stale_search_b_panel = stale_search_page.get_by_test_id("zotero-links-panel")
    expect(stale_search_b_panel.get_by_role(
        "heading", name=kay_title, exact=True
    )).to_be_visible(timeout=30_000)
    stale_search_b_query = stale_search_b_panel.get_by_label(
        "Paper title or keyword", exact=True
    )
    stale_search_b_query.focus()
    stale_search_page.wait_for_timeout(850)
    expect(stale_search_b_query).to_be_focused()
    expect(stale_search_b_panel.get_by_test_id("zotero-search-results")).to_be_empty()
    expect(stale_search_b_panel.get_by_test_id("zotero-panel-feedback")).to_have_count(0)
    _require(
        request_count(stale_search_page, "GET", "/zotero/items?") == 1,
        "cross-Article delayed search emitted an unexpected request count",
    )
    stale_search_context.close()

    stale_export_context = new_context(
        settings={
            **cross_settings,
            "exportDelayMs": 700,
            "ignoreExportAbort": True,
        }
    )
    clear_links(stale_export_context)
    seed_link(stale_export_context, ATTENTION_ARTICLE_ID, "ABCD1234")
    seed_link(stale_export_context, CRB_ARTICLE_ID, "EFGH5678")
    stale_export_page = _new_observed_page(
        stale_export_context,
        console_errors,
        page_errors,
        label=f"p3-032-cross-export-{iteration}",
    )
    stale_export_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(stale_export_page)
    stale_export_panel = stale_export_page.get_by_test_id("zotero-links-panel")
    expect(stale_export_panel.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible(timeout=30_000)
    stale_export_panel.get_by_role("button", name="Export BibTeX", exact=True).click()
    expect(stale_export_panel.get_by_text("Requesting BibTeX...", exact=True)).to_be_visible()
    navigate_to_crb_from_recent(stale_export_page)
    stale_export_b_panel = stale_export_page.get_by_test_id("zotero-links-panel")
    expect(stale_export_b_panel.get_by_role(
        "heading", name=kay_title, exact=True
    )).to_be_visible(timeout=30_000)
    stale_export_b_query = stale_export_b_panel.get_by_label(
        "Paper title or keyword", exact=True
    )
    stale_export_b_query.focus()
    stale_export_page.wait_for_timeout(850)
    expect(stale_export_b_query).to_be_focused()
    expect(stale_export_b_panel.get_by_test_id("zotero-bibtex-region")).to_have_count(0)
    expect(stale_export_b_panel.get_by_test_id("zotero-panel-feedback")).to_have_count(0)
    _require(
        request_count(stale_export_page, "POST", "/zotero/export/bibtex") == 1,
        "cross-Article delayed export emitted an unexpected request count",
    )
    stale_export_requests = exact_requests(
        stale_export_page, "POST", "/zotero/export/bibtex"
    )
    _require(
        len(stale_export_requests) == 1
        and stale_export_requests[0].get("body") == {"item_keys": ["ABCD1234"]},
        f"BibTeX export did not carry the exact linked-item set: {stale_export_requests}",
    )
    stale_export_context.close()

    stale_intent_context = new_context(settings=cross_settings)
    clear_links(stale_intent_context)
    seed_link(stale_intent_context, ATTENTION_ARTICLE_ID, "ABCD1234")
    seed_link(stale_intent_context, CRB_ARTICLE_ID, "EFGH5678")
    stale_intent_page = _new_observed_page(
        stale_intent_context,
        console_errors,
        page_errors,
        label=f"p3-032-cross-unlink-intent-{iteration}",
    )
    stale_intent_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(stale_intent_page)
    stale_intent_panel = stale_intent_page.get_by_test_id("zotero-links-panel")
    stale_intent_panel.get_by_role(
        "button", name="Unlink Attention Is All You Need", exact=True
    ).click(timeout=30_000)
    expect(stale_intent_panel.get_by_test_id("zotero-unlink-confirmation")).to_be_visible()
    expect(stale_intent_panel.get_by_role(
        "button", name="Cancel unlink Attention Is All You Need", exact=True
    )).to_be_focused()
    _start_zotero_focus_trace(stale_intent_page)
    navigate_to_crb_from_recent(stale_intent_page)
    stale_intent_heading = stale_intent_page.locator("article#article-start > h1")
    expect(stale_intent_heading).to_be_focused(timeout=30_000)
    _assert_zotero_focus_continuity(
        stale_intent_page,
        "Related Papers Article navigation",
        (
            "testid:shell-main-content",
            f"heading:{CRB_TITLE}",
        ),
    )
    stale_intent_b_panel = stale_intent_page.get_by_test_id("zotero-links-panel")
    expect(stale_intent_b_panel.get_by_role(
        "heading", name=kay_title, exact=True
    )).to_be_visible(timeout=30_000)
    expect(stale_intent_b_panel.get_by_test_id("zotero-unlink-confirmation")).to_have_count(0)
    _require(
        request_count(stale_intent_page, "DELETE", "/zotero/links/") == 0,
        "navigating away from an Unlink intent emitted DELETE",
    )
    stale_intent_context.close()

    stale_mutation_context = new_context(
        settings={**cross_settings, "linkDelayMs": 700}
    )
    clear_links(stale_mutation_context)
    seed_link(stale_mutation_context, ATTENTION_ARTICLE_ID, "ABCD1234")
    seed_link(stale_mutation_context, CRB_ARTICLE_ID, "ABCD1234")
    stale_mutation_page = _new_observed_page(
        stale_mutation_context,
        console_errors,
        page_errors,
        label=f"p3-032-cross-mutation-{iteration}",
    )
    stale_mutation_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(stale_mutation_page)
    stale_mutation_panel = stale_mutation_page.get_by_test_id("zotero-links-panel")
    expect(stale_mutation_panel.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible(timeout=30_000)
    stale_mutation_panel.get_by_label("Paper title or keyword", exact=True).fill("Kay")
    stale_mutation_panel.get_by_label("Paper title or keyword", exact=True).press("Enter")
    stale_link = stale_mutation_panel.get_by_role(
        "button", name=f"Link {kay_title}", exact=True
    )
    expect(stale_link).to_be_visible(timeout=30_000)
    stale_link.click()
    navigate_to_crb_from_recent(stale_mutation_page)
    stale_mutation_b_panel = stale_mutation_page.get_by_test_id("zotero-links-panel")
    expect(stale_mutation_b_panel.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible(timeout=30_000)
    stale_mutation_b_query = stale_mutation_b_panel.get_by_label(
        "Paper title or keyword", exact=True
    )
    stale_mutation_b_query.focus()
    stale_mutation_page.wait_for_timeout(850)
    expect(stale_mutation_b_query).to_be_focused()
    expect(stale_mutation_b_panel.get_by_role(
        "heading", name=kay_title, exact=True
    )).to_have_count(0)
    expect(stale_mutation_b_panel.get_by_test_id("zotero-panel-feedback")).to_have_count(0)
    expect(stale_mutation_b_panel.get_by_test_id("zotero-bibtex-region")).to_have_count(0)
    _require(
        request_count(
            stale_mutation_page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
        ) == 1
        and request_count(
            stale_mutation_page, "POST", f"/zotero/links/{CRB_ARTICLE_ID}"
        ) == 0,
        "cross-Article delayed mutation targeted the wrong Article",
    )
    stale_mutation_context.close()

    stale_reconcile_context = new_context(
        settings={**cross_settings, "ignoreLinksAbort": True}
    )
    clear_links(stale_reconcile_context)
    seed_link(stale_reconcile_context, ATTENTION_ARTICLE_ID, "ABCD1234")
    seed_link(stale_reconcile_context, CRB_ARTICLE_ID, "ABCD1234")
    stale_reconcile_page = _new_observed_page(
        stale_reconcile_context,
        console_errors,
        page_errors,
        label=f"p3-032-cross-reconcile-{iteration}",
    )
    stale_reconcile_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(stale_reconcile_page)
    stale_reconcile_panel = stale_reconcile_page.get_by_test_id("zotero-links-panel")
    expect(stale_reconcile_panel.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible(timeout=30_000)
    stale_reconcile_panel.get_by_label("Paper title or keyword", exact=True).fill("Kay")
    stale_reconcile_panel.get_by_label("Paper title or keyword", exact=True).press("Enter")
    stale_reconcile_link = stale_reconcile_panel.get_by_role(
        "button", name=f"Link {kay_title}", exact=True
    )
    expect(stale_reconcile_link).to_be_visible(timeout=30_000)
    stale_reconcile_initial_reads = request_count(
        stale_reconcile_page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    )
    stale_reconcile_page.evaluate(
        """
        ([path]) => {
          window.__p3032.dropNextLinkPost = true;
          window.__p3032.linkDelays = { [path]: 700 };
        }
        """,
        [f"/zotero/links/{ATTENTION_ARTICLE_ID}"],
    )
    stale_reconcile_link.click()
    stale_reconcile_page.wait_for_function(
        """
        ([path, baseline]) => window.__p3032.requests.filter(
          request => request.method === "GET" && request.target.includes(path)
        ).length === baseline + 1
        """,
        arg=[f"/zotero/links/{ATTENTION_ARTICLE_ID}", stale_reconcile_initial_reads],
        timeout=30_000,
    )
    navigate_to_crb_from_recent(stale_reconcile_page)
    stale_reconcile_b_panel = stale_reconcile_page.get_by_test_id("zotero-links-panel")
    expect(stale_reconcile_b_panel.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible(timeout=30_000)
    stale_reconcile_b_query = stale_reconcile_b_panel.get_by_label(
        "Paper title or keyword", exact=True
    )
    stale_reconcile_b_query.focus()
    stale_reconcile_page.wait_for_timeout(850)
    expect(stale_reconcile_b_query).to_be_focused()
    expect(stale_reconcile_b_panel.get_by_role(
        "heading", name=kay_title, exact=True
    )).to_have_count(0)
    expect(stale_reconcile_b_panel.get_by_test_id("zotero-panel-feedback")).to_have_count(0)
    expect(stale_reconcile_b_panel.get_by_test_id("zotero-bibtex-region")).to_have_count(0)
    _require(
        request_count(
            stale_reconcile_page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
        ) == 1
        and request_count(
            stale_reconcile_page, "POST", f"/zotero/links/{CRB_ARTICLE_ID}"
        ) == 0,
        "cross-Article delayed reconciliation changed the mutation target",
    )
    stale_reconcile_context.close()
    checks["zotero_cross_article_deferred_operations"] = True

    context = new_context(settings={"linksDelayMs": 450})
    clear_links(context)
    seed_link(context, ATTENTION_ARTICLE_ID, "ABCD1234", note="Foundational context")
    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label=f"p3-032-workspace-{iteration}",
    )
    page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(page)
    panel = page.get_by_test_id("zotero-links-panel")
    linked_papers = panel.get_by_test_id("zotero-linked-papers")
    expect(linked_papers).to_have_attribute("aria-busy", "true")
    expect(panel.get_by_text("Loading related papers...", exact=True)).to_be_visible()
    expect(panel.get_by_text("No related papers linked.", exact=True)).to_have_count(0)
    expect(panel.get_by_role("heading", name="Attention Is All You Need", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(linked_papers).to_have_attribute("aria-busy", "false")
    expect(panel.get_by_test_id("zotero-links-announcement")).to_have_text(
        "1 related paper loaded."
    )
    expect(panel.get_by_text("No related papers linked.", exact=True)).to_have_count(0)
    expect(panel.get_by_label("Paper title or keyword", exact=True)).to_be_visible()
    expect(panel.get_by_label("Relationship", exact=True)).to_be_visible()
    expect(panel.get_by_label("Relationship note (optional)", exact=True)).to_be_visible()
    checks["zotero_truthful_load_and_control_labels"] = True
    page.evaluate("window.__p3032.linksDelayMs = 0")

    query = panel.get_by_label("Paper title or keyword", exact=True)
    search_form = panel.get_by_role("form", name="Search Zotero papers", exact=True)
    search_button = search_form.locator('button[type="submit"]')
    keyboard_search_start = request_count(page, "GET", "/zotero/items?")
    query.fill("no-match-p3-032")
    query.press("Enter")
    expect(
        panel.get_by_test_id("zotero-search-results").get_by_text(
            "No Zotero papers matched “no-match-p3-032”.", exact=True
        )
    ).to_be_visible(timeout=30_000)
    _require(
        request_count(page, "GET", "/zotero/items?") - keyboard_search_start == 1,
        "keyboard Enter search did not emit exactly one request",
    )
    page.evaluate(
        """
        () => {
          window.__p3032.ignoreSearchAbort = true;
          window.__p3032.searchDelays = { attention: 700, Kay: 60 };
        }
        """
    )
    search_start = request_count(page, "GET", "/zotero/items?")
    query.fill("attention")
    search_button.click()
    query.fill("Kay")
    expect(search_button).to_have_text("Search")
    search_button.click()
    search_results = panel.get_by_test_id("zotero-search-results")
    expect(search_results.get_by_role("heading", name=kay_title, exact=True)).to_be_visible(
        timeout=30_000
    )
    page.wait_for_timeout(850)
    expect(
        search_results.get_by_role("heading", name="Attention Is All You Need", exact=True)
    ).to_have_count(0)
    _require(
        request_count(page, "GET", "/zotero/items?") - search_start == 2,
        "superseded Zotero searches did not issue exactly one request per query",
    )

    page.evaluate("window.__p3032.searchDelays = { Kay: 350 }")
    duplicate_search_start = request_count(page, "GET", "/zotero/items?")
    search_form.evaluate("form => { form.requestSubmit(); form.requestSubmit(); }")
    expect(search_button).to_have_text("Searching...")
    expect(search_button).to_be_disabled()
    query.fill("Kay ")
    query.press("Enter")
    expect(search_results.get_by_role("heading", name=kay_title, exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(search_results.get_by_role("status")).to_have_text(
        "1 paper found for “Kay”."
    )
    _require(
        request_count(page, "GET", "/zotero/items?") - duplicate_search_start == 1,
        "duplicate pending Zotero search emitted more than one request",
    )
    _require(
        exact_requests(page, "GET", "/zotero/items")[-1].get("target")
        == "/zotero/items?q=Kay&limit=10",
        f"normalized search did not preserve exact query identity: {exact_requests(page, 'GET', '/zotero/items')[-1:]}",
    )
    checks["zotero_latest_search_and_duplicate_guard"] = True

    note = panel.get_by_label("Relationship note (optional)", exact=True)
    link_note = "CRB background " + "evidence " * 12
    note.fill(link_note)
    link_button = search_results.get_by_role("button", name=f"Link {kay_title}", exact=True)
    link_post_start = request_count(page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}")
    link_read_start = request_count(page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}")
    page.evaluate(
        """
        () => {
          window.__p3032.linkDelayMs = 300;
          window.__p3032.dropNextLinkPost = true;
        }
        """
    )
    relation = panel.get_by_label("Relationship", exact=True)
    link_button.focus()
    _start_zotero_focus_trace(page)
    link_button.evaluate("button => { button.click(); button.click(); }")
    expect(search_results.get_by_role("button", name=f"Linking {kay_title}", exact=True)).to_be_disabled()
    expect(note).to_be_disabled()
    expect(relation).to_be_disabled()
    expect(linked_papers).to_have_attribute("aria-busy", "true")
    expect(panel.get_by_test_id("zotero-mutation-announcement")).to_have_text(
        f"Linking {kay_title} to this Article."
    )
    feedback = panel.get_by_test_id("zotero-panel-feedback")
    expect(feedback).to_contain_text("link confirmed after reloading project storage", timeout=30_000)
    expect(feedback).to_be_focused()
    _require_visible_focus(feedback, "Related Papers Link reconciliation feedback")
    expect(panel.get_by_role("heading", name=kay_title, exact=True).first).to_be_visible()
    expect(linked_papers).to_have_attribute("aria-busy", "false")
    expect(search_results.get_by_role("button", name=f"Linked {kay_title}", exact=True)).to_be_disabled()
    _require(
        request_count(page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}") - link_post_start == 1,
        "rapid Link activation emitted more than one POST",
    )
    link_requests = exact_requests(
        page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    )
    _require(
        link_requests[-1].get("body") == {
            "item_key": "EFGH5678",
            "relation_type": "related",
            "note": link_note.strip(),
        },
        f"Link request did not preserve exact item/relation/note identity: {link_requests[-1:]}",
    )
    _require(
        request_count(page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}") - link_read_start == 1,
        "lost Link response did not trigger exactly one read-only reconciliation",
    )
    _assert_zotero_focus_continuity(
        page,
        "Related Papers Link reconciliation",
        (
            "testid:zotero-linked-papers",
            "testid:zotero-panel-feedback",
        ),
    )
    checks["zotero_link_response_loss_reconciliation"] = True

    export_button = panel.locator('button[aria-controls="linked-bibtex-region"]')
    expect(export_button).to_have_text("Export BibTeX")
    export_start = request_count(page, "POST", "/zotero/export/bibtex")
    page.evaluate("window.__p3032.exportDelayMs = 300")
    export_button.focus()
    _start_zotero_focus_trace(page)
    export_button.press("Space")
    export_button.evaluate("button => button.click()")
    expect(panel.get_by_role("button", name="Exporting...", exact=True)).to_be_disabled()
    export_locked_unlink = panel.get_by_role(
        "button", name="Unlink Attention Is All You Need", exact=True
    )
    expect(export_locked_unlink).to_be_disabled()
    export_delete_start = request_count(
        page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/"
    )
    export_locked_unlink.evaluate("button => button.click()")
    expect(panel.get_by_test_id("zotero-unlink-confirmation")).to_have_count(0)
    _require(
        request_count(page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/")
        == export_delete_start,
        "a mutation launched while BibTeX export owned the panel",
    )
    bibtex_region = panel.get_by_test_id("zotero-bibtex-region")
    expect(bibtex_region).to_be_focused(timeout=30_000)
    _require_visible_focus(bibtex_region, "Related Papers BibTeX result")
    bibtex_pre = bibtex_region.get_by_label("BibTeX export", exact=True)
    expect(bibtex_pre).to_contain_text("@article{vaswani_attention_2017")
    expect(bibtex_pre).to_contain_text("@book{kay_crb_1993")
    expect(bibtex_pre).to_have_attribute("tabindex", "0")
    _require(
        request_count(page, "POST", "/zotero/export/bibtex") - export_start == 1,
        "duplicate BibTeX activation emitted more than one export request",
    )
    exported_keys = exact_requests(page, "POST", "/zotero/export/bibtex")[-1].get(
        "body", {}
    ).get("item_keys", [])
    _require(
        sorted(exported_keys) == ["ABCD1234", "EFGH5678"],
        f"BibTeX export did not match the current link set: {exported_keys}",
    )
    _assert_zotero_focus_continuity(
        page,
        "Related Papers BibTeX export",
        (
            "testid:zotero-linked-papers",
            "testid:zotero-bibtex-region",
        ),
    )
    panel.get_by_role("button", name="Hide BibTeX", exact=True).click()
    page.evaluate("window.__p3032.failNextExport = true")
    export_error_start = request_count(page, "POST", "/zotero/export/bibtex")
    panel.get_by_role("button", name="Export BibTeX", exact=True).click()
    bibtex_region = panel.get_by_test_id("zotero-bibtex-region")
    expect(bibtex_region.get_by_role("alert")).to_have_text(
        "BibTeX could not be requested for the current links.", timeout=30_000
    )
    expect(bibtex_region).to_be_focused()
    _require(
        request_count(page, "POST", "/zotero/export/bibtex") - export_error_start == 1,
        "BibTeX error path did not emit exactly one request",
    )
    panel.get_by_role("button", name="Hide BibTeX", exact=True).click()
    page.evaluate("window.__p3032.syntheticBibtex = ''")
    empty_export_start = request_count(page, "POST", "/zotero/export/bibtex")
    panel.get_by_role("button", name="Export BibTeX", exact=True).click()
    bibtex_region = panel.get_by_test_id("zotero-bibtex-region")
    expect(bibtex_region.get_by_text(
        "No BibTeX text was returned for the requested links.", exact=True
    )).to_be_visible(timeout=30_000)
    expect(bibtex_region).to_be_focused()
    _require(
        request_count(page, "POST", "/zotero/export/bibtex") - empty_export_start == 1,
        "empty BibTeX path did not emit exactly one request",
    )
    page.evaluate("window.__p3032.syntheticBibtex = null")
    checks["zotero_bibtex_owned_disclosure"] = True

    attention_unlink = panel.get_by_role(
        "button", name="Unlink Attention Is All You Need", exact=True
    )
    delete_start = request_count(page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/")
    attention_unlink.focus()
    _start_zotero_focus_trace(page)
    attention_unlink.press("Space")
    confirmation = panel.get_by_test_id("zotero-unlink-confirmation")
    cancel = confirmation.get_by_role(
        "button", name="Cancel unlink Attention Is All You Need", exact=True
    )
    expect(cancel).to_be_focused()
    expect(cancel).to_have_attribute("aria-describedby", "zotero-unlink-consequence")
    _require(
        request_count(page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/") == delete_start,
        "opening Unlink confirmation emitted a DELETE",
    )
    cancel.press("Escape")
    expect(attention_unlink).to_be_focused()
    _assert_zotero_focus_continuity(
        page,
        "Related Papers Unlink Escape",
        (
            "testid:zotero-linked-papers",
            "button:Cancel unlink Attention Is All You Need",
            "testid:zotero-linked-papers",
            "button:Unlink Attention Is All You Need",
        ),
    )
    attention_unlink.click()
    cancel = panel.get_by_test_id("zotero-unlink-confirmation").get_by_role(
        "button", name="Cancel unlink Attention Is All You Need", exact=True
    )
    cancel.click()
    expect(attention_unlink).to_be_focused()
    _require(
        request_count(page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/") == delete_start,
        "cancelled Unlink confirmation emitted a DELETE",
    )

    attention_unlink.click()
    confirmation = panel.get_by_test_id("zotero-unlink-confirmation")
    confirm = confirmation.get_by_role(
        "button", name="Unlink Attention Is All You Need permanently", exact=True
    )
    link_reads_before_unlink = request_count(
        page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    )
    page.evaluate("window.__p3032.deleteDelayMs = 300")
    _declare_expected_no_content_response(
        page,
        source_url=(
            f"{BROWSER_API_URL}/zotero/links/{ATTENTION_ARTICLE_ID}/ABCD1234"
        ),
        method="DELETE",
    )
    confirm.focus()
    _start_zotero_focus_trace(page)
    confirm.press("Enter")
    confirm.evaluate("button => button.click()")
    expect(
        confirmation.get_by_role("button", name="Unlink Attention Is All You Need permanently", exact=True)
    ).to_be_disabled()
    expect(confirmation.get_by_text("Unlinking...", exact=True)).to_be_visible()
    expect(confirmation).to_have_attribute("aria-busy", "true")
    expect(linked_papers).to_have_attribute("aria-busy", "true")
    expect(panel.get_by_test_id("zotero-mutation-announcement")).to_have_text(
        "Unlinking Attention Is All You Need from this Article."
    )
    expect(feedback).to_contain_text("The Zotero library item was not deleted", timeout=30_000)
    expect(feedback).to_be_focused()
    _require_visible_focus(feedback, "Related Papers Unlink success feedback")
    expect(panel.get_by_role("heading", name="Attention Is All You Need", exact=True)).to_have_count(0)
    expect(panel.get_by_test_id("zotero-bibtex-region")).to_have_count(0)
    expect(linked_papers).to_have_attribute("aria-busy", "false")
    _require(
        request_count(page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/") - delete_start == 1,
        "confirmed Unlink emitted more than one DELETE",
    )
    _require(
        request_count(page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}")
        == link_reads_before_unlink,
        "successful Unlink performed an unnecessary list reload",
    )
    _assert_zotero_focus_continuity(
        page,
        "Related Papers confirmed Unlink",
        (
            "testid:zotero-linked-papers",
            "testid:zotero-panel-feedback",
        ),
    )
    checks["zotero_unlink_confirmation_and_exact_delete"] = True

    kay_unlink = panel.get_by_role("button", name=f"Unlink {kay_title}", exact=True)
    uncertain_delete_start = request_count(
        page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/"
    )
    uncertain_read_start = request_count(
        page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    )
    page.evaluate(
        """
        () => {
          window.__p3032.deleteDelayMs = 100;
          window.__p3032.dropNextDelete = true;
          window.__p3032.failNextLinksGet = true;
        }
        """
    )
    _declare_expected_no_content_response(
        page,
        source_url=(
            f"{BROWSER_API_URL}/zotero/links/{ATTENTION_ARTICLE_ID}/EFGH5678"
        ),
        method="DELETE",
    )
    kay_unlink.click()
    panel.get_by_role("button", name=f"Unlink {kay_title} permanently", exact=True).click()
    reload_links = panel.get_by_role("button", name="Reload related papers", exact=True)
    expect(reload_links).to_be_focused(timeout=30_000)
    _require_visible_focus(reload_links, "Related Papers reconciliation reload")
    expect(feedback).to_contain_text("Persistence remains unconfirmed")
    expect(panel.get_by_role("alert")).to_have_count(1)
    expect(panel.get_by_role("heading", name=kay_title, exact=True).first).to_be_visible()
    _require(
        request_count(page, "DELETE", f"/zotero/links/{ATTENTION_ARTICLE_ID}/")
        - uncertain_delete_start == 1,
        "lost Unlink response emitted an unexpected DELETE count",
    )
    _require(
        request_count(page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}")
        - uncertain_read_start == 1,
        "lost Unlink response did not perform exactly one failed reconciliation",
    )
    reload_links.click()
    expect(panel.get_by_text("No related papers linked.", exact=True)).to_be_visible(timeout=30_000)
    expect(feedback).to_contain_text("Related papers reloaded from project storage")
    expect(feedback).to_be_focused()
    _require_visible_focus(feedback, "Related Papers reload success feedback")
    _require(
        request_count(page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}")
        - uncertain_read_start == 2,
        "manual reconciliation did not issue exactly one additional read",
    )
    checks["zotero_unconfirmed_result_and_manual_reload"] = True
    context.close()

    rejected_context = new_context()
    clear_links(rejected_context)
    seed_link(rejected_context, ATTENTION_ARTICLE_ID, "ABCD1234")
    rejected_page = _new_observed_page(
        rejected_context,
        console_errors,
        page_errors,
        label=f"p3-032-rejected-mutations-{iteration}",
    )
    rejected_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(rejected_page)
    rejected_panel = rejected_page.get_by_test_id("zotero-links-panel")
    rejected_links = rejected_panel.get_by_test_id("zotero-linked-papers")
    expect(rejected_links.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible(timeout=30_000)
    rejected_query = rejected_panel.get_by_label("Paper title or keyword", exact=True)
    rejected_query.fill("Kay")
    rejected_query.press("Enter")
    rejected_link = rejected_panel.get_by_role(
        "button", name=f"Link {kay_title}", exact=True
    )
    expect(rejected_link).to_be_visible(timeout=30_000)
    rejected_note = rejected_panel.get_by_label("Relationship note (optional)", exact=True)
    rejected_note.fill("Rejected relationship remains editable")
    rejected_panel.get_by_label("Relationship", exact=True).select_option("background")
    rejected_link_post_start = len(exact_requests(
        rejected_page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    ))
    rejected_link_read_start = len(exact_requests(
        rejected_page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    ))
    rejected_page.evaluate("window.__p3032.rejectNextLinkPost = true")
    rejected_link.focus()
    _start_zotero_focus_trace(rejected_page)
    rejected_link.press("Enter")
    rejected_feedback = rejected_panel.get_by_test_id("zotero-panel-feedback")
    expect(rejected_feedback).to_have_text(
        f"{kay_title} was not linked. You can retry.", timeout=30_000
    )
    expect(rejected_link).to_be_focused()
    expect(rejected_link).to_be_enabled()
    expect(rejected_note).to_have_value("Rejected relationship remains editable")
    expect(rejected_links.get_by_role("heading", name=kay_title, exact=True)).to_have_count(0)
    _require(
        len(exact_requests(
            rejected_page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
        )) - rejected_link_post_start == 1,
        "rejected Link did not emit exactly one mutation request",
    )
    _require(
        len(exact_requests(
            rejected_page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
        )) - rejected_link_read_start == 1,
        "rejected Link did not emit exactly one read-only reconciliation",
    )
    rejected_link_request = exact_requests(
        rejected_page, "POST", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    )[-1]
    _require(
        rejected_link_request.get("body") == {
            "item_key": "EFGH5678",
            "relation_type": "background",
            "note": "Rejected relationship remains editable",
        },
        f"rejected Link lost request identity: {rejected_link_request}",
    )
    _assert_zotero_focus_continuity(
        rejected_page,
        "Related Papers rejected Link",
        (
            "testid:zotero-linked-papers",
            f"button:Link {kay_title}",
        ),
    )

    rejected_unlink = rejected_panel.get_by_role(
        "button", name="Unlink Attention Is All You Need", exact=True
    )
    rejected_unlink.click()
    rejected_confirm = rejected_panel.get_by_role(
        "button", name="Unlink Attention Is All You Need permanently", exact=True
    )
    rejected_delete_start = len(exact_requests(
        rejected_page,
        "DELETE",
        f"/zotero/links/{ATTENTION_ARTICLE_ID}/ABCD1234",
    ))
    rejected_unlink_read_start = len(exact_requests(
        rejected_page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    ))
    rejected_page.evaluate("window.__p3032.rejectNextDelete = true")
    rejected_confirm.focus()
    _start_zotero_focus_trace(rejected_page)
    rejected_confirm.press("Space")
    expect(rejected_feedback).to_have_text(
        "Attention Is All You Need was not unlinked. You can retry.", timeout=30_000
    )
    expect(rejected_unlink).to_be_focused()
    expect(rejected_unlink).to_be_enabled()
    expect(rejected_links.get_by_role(
        "heading", name="Attention Is All You Need", exact=True
    )).to_be_visible()
    expect(rejected_panel.get_by_test_id("zotero-unlink-confirmation")).to_have_count(0)
    _require(
        len(exact_requests(
            rejected_page,
            "DELETE",
            f"/zotero/links/{ATTENTION_ARTICLE_ID}/ABCD1234",
        )) - rejected_delete_start == 1,
        "rejected Unlink did not emit exactly one mutation request",
    )
    _require(
        len(exact_requests(
            rejected_page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
        )) - rejected_unlink_read_start == 1,
        "rejected Unlink did not emit exactly one read-only reconciliation",
    )
    _assert_zotero_focus_continuity(
        rejected_page,
        "Related Papers rejected Unlink",
        (
            "testid:zotero-linked-papers",
            "button:Unlink Attention Is All You Need",
        ),
    )
    checks["zotero_rejected_mutation_reconciliation"] = True
    rejected_context.close()

    unavailable_context = new_context(settings={"forceProviderUnavailable": True})
    clear_links(unavailable_context)
    seed_link(unavailable_context, ATTENTION_ARTICLE_ID, "ABCD1234")
    unavailable_page = _new_observed_page(
        unavailable_context,
        console_errors,
        page_errors,
        label=f"p3-032-provider-unavailable-{iteration}",
    )
    unavailable_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(unavailable_page)
    unavailable_panel = unavailable_page.get_by_test_id("zotero-links-panel")
    expect(unavailable_panel.get_by_text("Zotero is unavailable. Existing project links remain visible.", exact=True)).to_be_visible(timeout=30_000)
    expect(unavailable_panel.get_by_role("heading", name="Attention Is All You Need", exact=True)).to_be_visible()
    expect(unavailable_panel.get_by_role("button", name="Export BibTeX", exact=True)).to_be_disabled()
    expect(unavailable_panel.get_by_role("form", name="Search Zotero papers", exact=True).locator('button[type="submit"]')).to_be_disabled()
    expect(unavailable_panel.get_by_role("button", name="Unlink Attention Is All You Need", exact=True)).to_be_enabled()
    unavailable_page.evaluate("window.__p3032.forceProviderUnavailable = false")
    provider_retry = unavailable_panel.get_by_role(
        "button", name="Retry availability", exact=True
    )
    provider_retry.focus()
    _start_zotero_focus_trace(unavailable_page)
    provider_retry.click()
    provider_region = unavailable_panel.get_by_test_id("zotero-provider-state")
    expect(provider_region.get_by_text("Zotero is available.", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(provider_region).to_be_focused()
    _assert_zotero_focus_continuity(
        unavailable_page,
        "Related Papers provider retry",
        (
            "testid:zotero-linked-papers",
            "testid:zotero-provider-state",
        ),
    )
    checks["zotero_provider_unavailable_preserves_local_links"] = True
    unavailable_context.close()

    list_failure_context = new_context(settings={"failNextLinksGet": True})
    clear_links(list_failure_context)
    list_failure_page = _new_observed_page(
        list_failure_context,
        console_errors,
        page_errors,
        label=f"p3-032-list-failure-{iteration}",
    )
    list_failure_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(list_failure_page)
    list_failure_panel = list_failure_page.get_by_test_id("zotero-links-panel")
    expect(
        list_failure_panel.get_by_role("alert").filter(
            has_text="Related papers could not be loaded"
        )
    ).to_be_visible(timeout=30_000)
    expect(
        list_failure_panel.get_by_text("No related papers linked.", exact=True)
    ).to_have_count(0)
    list_failure_panel.get_by_label("Paper title or keyword", exact=True).fill("Kay")
    list_failure_panel.get_by_role(
        "form", name="Search Zotero papers", exact=True
    ).locator('button[type="submit"]').click()
    failed_list_result = list_failure_panel.get_by_role(
        "button", name=f"Link {kay_title}", exact=True
    )
    expect(failed_list_result).to_be_disabled(timeout=30_000)
    retry_related = list_failure_panel.get_by_role(
        "button", name="Retry related papers", exact=True
    )
    failed_retry_read_start = request_count(
        list_failure_page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
    )
    list_failure_page.evaluate("window.__p3032.failNextLinksGet = true")
    retry_related.focus()
    _start_zotero_focus_trace(list_failure_page)
    retry_related.click()
    retry_related = list_failure_panel.get_by_role(
        "button", name="Retry related papers", exact=True
    )
    expect(list_failure_panel.get_by_role("alert")).to_have_text(
        "Related papers still could not be loaded.", timeout=30_000
    )
    expect(retry_related).to_be_focused()
    expect(
        list_failure_panel.get_by_text("No related papers linked.", exact=True)
    ).to_have_count(0)
    expect(failed_list_result).to_be_disabled()
    _require(
        request_count(
            list_failure_page, "GET", f"/zotero/links/{ATTENTION_ARTICLE_ID}"
        ) - failed_retry_read_start == 1,
        "failed list retry did not emit exactly one read",
    )
    _assert_zotero_focus_continuity(
        list_failure_page,
        "Related Papers failed list retry",
        (
            "testid:zotero-linked-papers",
            "button:Retry related papers",
        ),
    )
    retry_related.focus()
    _start_zotero_focus_trace(list_failure_page)
    retry_related.click()
    expect(
        list_failure_panel.get_by_text("No related papers linked.", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(list_failure_panel.get_by_test_id("zotero-links-announcement")).to_have_text(
        "No related papers are linked."
    )
    expect(failed_list_result).to_be_enabled()
    expect(list_failure_panel.get_by_role("alert")).to_have_count(0)
    _assert_zotero_focus_continuity(
        list_failure_page,
        "Related Papers successful list retry",
        (
            "testid:zotero-linked-papers",
            "testid:zotero-panel-feedback",
        ),
    )
    checks["zotero_failed_list_never_claims_empty_or_allows_upsert"] = True
    list_failure_context.close()

    long_title = (
        "Paper-" + "t" * 140
        + " A very long locally indexed title about estimation, attention, and uncertainty"
    )
    long_note = "Long relationship evidence with unbroken-token-" + "x" * 120
    long_bibtex = "@article{long_key_" + "x" * 180 + ",\n  title = {" + long_title + "}\n}"
    long_item = {
        "item_key": "LONG1234",
        "bibtex_key": "long_key",
        "title": long_title,
        "creators": ["Researcher With A Very Long Display Name"],
        "year": "2026",
        "item_type": "journalArticle",
        "publication_title": "Journal of Long Metadata and Responsive Learning Interfaces",
        "doi": None,
        "url": None,
        "abstract_note": None,
        "tags": [],
        "collections": [],
        "updated_at": None,
    }
    long_link = {
        "link": {
            "article_id": ATTENTION_ARTICLE_ID,
            "zotero_item_key": "LONG1234",
            "relation_type": "related",
            "created_at": "2026-09-05T12:00:00Z",
            "note": long_note,
        },
        "item": long_item,
    }
    for viewport_width, viewport_height, viewport_label in (
        (1440, 900, "desktop"),
        (390, 844, "mobile"),
        (320, 844, "narrow"),
        (720, 450, "zoom-equivalent"),
    ):
        responsive_context = new_context(
            settings={
                "syntheticLink": long_link,
                "syntheticBibtex": long_bibtex,
                "exportDelayMs": 250,
            },
            viewport={"width": viewport_width, "height": viewport_height},
            is_mobile=viewport_width <= 390,
            device_scale_factor=2 if viewport_label == "zoom-equivalent" else 1,
        )
        responsive_page = _new_observed_page(
            responsive_context,
            console_errors,
            page_errors,
            label=f"p3-032-responsive-{viewport_label}-{iteration}",
        )
        responsive_page.goto(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(responsive_page)
        responsive_panel = responsive_page.get_by_test_id("zotero-links-panel")
        responsive_panel.scroll_into_view_if_needed()
        expect(responsive_panel.get_by_role("heading", name=long_title, exact=True)).to_be_visible(
            timeout=30_000
        )
        responsive_export = responsive_panel.locator(
            'button[aria-controls="linked-bibtex-region"]'
        )
        expect(responsive_export).to_have_text("Export BibTeX")
        responsive_export.click()
        expect(responsive_panel.get_by_role("button", name="Exporting...", exact=True)).to_be_disabled()
        responsive_bibtex = responsive_panel.get_by_label("BibTeX export", exact=True)
        expect(responsive_bibtex).to_contain_text("@article{long_key_", timeout=30_000)
        _require(
            responsive_bibtex.evaluate("element => element.scrollWidth > element.clientWidth"),
            f"{viewport_label} long BibTeX did not remain in a local scroll region",
        )
        responsive_bibtex.focus()
        for _ in range(8):
            responsive_bibtex.press("ArrowRight")
        responsive_page.wait_for_timeout(100)
        _require(
            responsive_bibtex.evaluate("element => element.scrollLeft > 0"),
            f"{viewport_label} long BibTeX was not keyboard-scrollable",
        )
        long_query = "doi-token-" + "q" * 180
        responsive_query = responsive_panel.get_by_label(
            "Paper title or keyword", exact=True
        )
        responsive_query.fill(long_query)
        responsive_query.press("Enter")
        long_query_status = responsive_panel.get_by_test_id(
            "zotero-search-results"
        ).get_by_role("status")
        expect(long_query_status).to_contain_text(long_query, timeout=30_000)
        long_query_status.evaluate(
            "element => element.scrollIntoView({ block: 'center', inline: 'nearest' })"
        )
        _require_viewport_containment(
            long_query_status.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} Related Papers long-query status",
        )
        _require(
            _document_width(responsive_page) <= viewport_width,
            f"{viewport_label} unbroken search query overflowed the page",
        )
        responsive_page.evaluate("window.__p3032.failNextSearch = true")
        responsive_query.fill("responsive failure")
        responsive_panel.get_by_role("form", name="Search Zotero papers", exact=True).locator('button[type="submit"]').click()
        responsive_alert = responsive_panel.get_by_role("alert", name="").filter(
            has_text="Zotero search failed"
        )
        expect(responsive_alert).to_be_visible(timeout=30_000)
        responsive_unlink = responsive_panel.get_by_role(
            "button", name=f"Unlink {long_title}", exact=True
        )
        responsive_unlink.scroll_into_view_if_needed()
        responsive_unlink.click()
        responsive_confirmation = responsive_panel.get_by_test_id("zotero-unlink-confirmation")
        responsive_cancel = responsive_confirmation.get_by_role(
            "button", name=f"Cancel unlink {long_title}", exact=True
        )
        responsive_confirm = responsive_confirmation.get_by_role(
            "button", name=f"Unlink {long_title} permanently", exact=True
        )
        expect(responsive_cancel).to_be_focused()
        for locator, label in (
            (responsive_export, "BibTeX action"),
            (responsive_alert, "search alert"),
            (responsive_cancel, "Unlink Cancel"),
            (responsive_confirm, "permanent Unlink action"),
        ):
            locator.evaluate(
                "element => element.scrollIntoView({ block: 'center', inline: 'nearest' })"
            )
            _require_viewport_containment(
                locator.bounding_box(),
                viewport_width,
                viewport_height,
                f"{viewport_label} Related Papers {label}",
            )
        _require(
            _document_width(responsive_page) <= viewport_width,
            f"{viewport_label} Related Papers workspace overflowed horizontally",
        )
        responsive_cancel.click()
        expect(responsive_unlink).to_be_focused()
        responsive_page.evaluate("window.__p3032.rejectNextDelete = true")
        responsive_delete_start = request_count(
            responsive_page,
            "DELETE",
            f"/zotero/links/{ATTENTION_ARTICLE_ID}/LONG1234",
        )
        responsive_unlink.press("Space")
        responsive_confirm = responsive_panel.get_by_role(
            "button", name=f"Unlink {long_title} permanently", exact=True
        )
        responsive_confirm.press("Enter")
        responsive_feedback = responsive_panel.get_by_test_id("zotero-panel-feedback")
        expect(responsive_feedback).to_contain_text(
            f"{long_title} was not unlinked", timeout=30_000
        )
        expect(responsive_unlink).to_be_focused()
        _require(
            request_count(
                responsive_page,
                "DELETE",
                f"/zotero/links/{ATTENTION_ARTICLE_ID}/LONG1234",
            ) - responsive_delete_start == 1,
            f"{viewport_label} rejected Unlink emitted an unexpected request count",
        )
        responsive_feedback.evaluate(
            "element => element.scrollIntoView({ block: 'center', inline: 'nearest' })"
        )
        _require_viewport_containment(
            responsive_feedback.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} Related Papers long mutation feedback",
        )
        _require(
            _document_width(responsive_page) <= viewport_width,
            f"{viewport_label} long mutation feedback overflowed horizontally",
        )
        responsive_context.close()
    checks["zotero_responsive_populated_pending_error_and_bibtex"] = True

    cleanup_context = new_context()
    clear_links(cleanup_context)
    cleanup_context.close()
    return checks


def _zotero_panel_controller_script(settings: dict[str, object]) -> str:
    serialized = json.dumps(settings, ensure_ascii=False)
    return """
    (() => {
      const settings = __SETTINGS__;
      const originalFetch = window.fetch.bind(window);
      const state = {
        requests: [],
        linksDelayMs: 0,
        linkDelays: {},
        searchDelays: {},
        linkDelayMs: 0,
        deleteDelayMs: 0,
        exportDelayMs: 0,
        ignoreSearchAbort: false,
        ignoreLinksAbort: false,
        ignoreExportAbort: false,
        forceProviderUnavailable: false,
        dropNextLinkPost: false,
        dropNextDelete: false,
        rejectNextLinkPost: false,
        rejectNextDelete: false,
        failNextLinksGet: false,
        failNextSearch: false,
        failNextExport: false,
        syntheticLink: null,
        syntheticBibtex: null,
        ...settings,
      };
      window.__p3032 = state;
      if (settings.history && !sessionStorage.getItem("p3-032-history-seeded")) {
        localStorage.setItem(
          "scientific-spaces-reading-history-v1",
          JSON.stringify([settings.history])
        );
        sessionStorage.setItem("p3-032-history-seeded", "true");
      }
      const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
      window.fetch = async (...args) => {
        const input = args[0];
        const init = args[1] || {};
        const target = String(input instanceof Request ? input.url : input);
        const parsed = new URL(target, window.location.href);
        const method = String(
          input instanceof Request ? input.method : init.method || "GET"
        ).toUpperCase();
        const path = parsed.pathname;
        const isLinksList = method === "GET" && /^\/zotero\/links\/[^/]+$/.test(path);
        const isLinkPost = method === "POST" && /^\/zotero\/links\/[^/]+$/.test(path);
        const isDelete = method === "DELETE" && /^\/zotero\/links\/[^/]+\/[^/]+$/.test(path);
        const isSearch = method === "GET" && path === "/zotero/items";
        const isExport = method === "POST" && path === "/zotero/export/bibtex";
        if (path.startsWith("/zotero/")) {
          let body = null;
          const rawBody = typeof init.body === "string"
            ? init.body
            : input instanceof Request
              ? await input.clone().text()
              : "";
          if (rawBody) {
            try {
              body = JSON.parse(rawBody);
            } catch {
              body = rawBody;
            }
          }
          state.requests.push({
            method,
            path,
            query: parsed.search,
            target: `${path}${parsed.search}`,
            body,
          });
        }
        if (isLinkPost && state.rejectNextLinkPost) {
          state.rejectNextLinkPost = false;
          throw new TypeError("intentional P3-032 pre-persistence Link rejection");
        }
        if (isDelete && state.rejectNextDelete) {
          state.rejectNextDelete = false;
          throw new TypeError("intentional P3-032 pre-persistence Unlink rejection");
        }
        if (method === "GET" && path === "/zotero/status" && state.forceProviderUnavailable) {
          return new Response(
            JSON.stringify({ provider: "fake", available: false, read_only: true }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }
        if (isLinksList && state.syntheticLink) {
          return new Response(
            JSON.stringify({ items: [state.syntheticLink], total: 1 }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }
        if (isExport && state.failNextExport) {
          state.failNextExport = false;
          if (state.exportDelayMs) await wait(state.exportDelayMs);
          throw new TypeError("intentional P3-032 BibTeX response loss");
        }
        if (isExport && state.syntheticBibtex !== null) {
          if (state.exportDelayMs) await wait(state.exportDelayMs);
          return new Response(
            JSON.stringify({ bibtex: state.syntheticBibtex, item_count: 1 }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }
        if (isLinksList && state.failNextLinksGet) {
          state.failNextLinksGet = false;
          throw new TypeError("intentional P3-032 link-list response loss");
        }
        if (isSearch && state.failNextSearch) {
          state.failNextSearch = false;
          throw new TypeError("intentional P3-032 search failure");
        }
        let fetchArgs = args;
        if (
          (isSearch && state.ignoreSearchAbort)
          || (isLinksList && state.ignoreLinksAbort)
          || (isExport && state.ignoreExportAbort)
        ) {
          const nextInit = { ...init };
          delete nextInit.signal;
          fetchArgs = [target, nextInit];
        }
        const response = await originalFetch(...fetchArgs);
        let delay = 0;
        if (isLinksList) delay = state.linkDelays[path] || state.linksDelayMs;
        if (isSearch) delay = state.searchDelays[parsed.searchParams.get("q") || ""] || 0;
        if (isLinkPost) delay = state.linkDelayMs;
        if (isDelete) delay = state.deleteDelayMs;
        if (isExport) delay = state.exportDelayMs;
        if (delay) await wait(delay);
        if (isLinkPost && state.dropNextLinkPost) {
          state.dropNextLinkPost = false;
          await response.clone().arrayBuffer();
          throw new TypeError("intentional P3-032 post-persistence Link response loss");
        }
        if (isDelete && state.dropNextDelete) {
          state.dropNextDelete = false;
          await response.clone().arrayBuffer();
          throw new TypeError("intentional P3-032 post-persistence Unlink response loss");
        }
        return response;
      };
    })();
    """.replace("__SETTINGS__", serialized)


def _start_zotero_focus_trace(page) -> None:
    page.evaluate(
        """
        () => {
          window.__p3032FocusTrace = [];
          const describe = (node) => {
            if (!(node instanceof HTMLElement)) return "missing";
            const testId = node.dataset.testid;
            if (testId) return `testid:${testId}`;
            if (node instanceof HTMLButtonElement) {
              return `button:${node.getAttribute("aria-label") || node.textContent?.trim() || ""}`;
            }
            if (node instanceof HTMLInputElement) return `input:${node.id}`;
            if (/^H[1-6]$/.test(node.tagName)) {
              return `heading:${node.textContent?.trim() || ""}`;
            }
            return node.tagName;
          };
          const record = (source) => {
            const active = document.activeElement;
            window.__p3032FocusTrace.push({
              source,
              target: describe(active),
              connected: active instanceof HTMLElement && active.isConnected,
              href: location.pathname + location.search + location.hash,
              owner: document.querySelector('[data-shell-focus-owner="pending"]')
                ?.getAttribute('data-shell-route-ready') || null,
              at: Math.round(performance.now()),
            });
          };
          const listener = () => record("focusin");
          window.__p3032FocusListener = listener;
          document.addEventListener("focusin", listener, true);
          const observer = new MutationObserver(() => record("mutation"));
          observer.observe(document.body, {
            attributes: true,
            childList: true,
            subtree: true,
            attributeFilter: [
              "disabled",
              "aria-busy",
              "data-shell-focus-owner",
              "data-shell-route-ready",
            ],
          });
          window.__p3032FocusObserver = observer;
          window.__p3032FocusSignals = {
            history: () => record("history-event"),
            route: () => record("route-commit"),
            operation: () => record("focus-operation"),
            hash: () => record("hashchange"),
          };
          window.addEventListener(
            'scientific-spaces:shell-history-navigation',
            window.__p3032FocusSignals.history,
          );
          window.addEventListener(
            'scientific-spaces:shell-route-commit',
            window.__p3032FocusSignals.route,
          );
          window.addEventListener(
            'scientific-spaces:shell-focus-operation',
            window.__p3032FocusSignals.operation,
          );
          window.addEventListener('hashchange', window.__p3032FocusSignals.hash);
          record("start");
        }
        """
    )


def _assert_zotero_focus_continuity(
    page,
    label: str,
    expected_focus_sequence: tuple[str, ...],
    forbidden_focus_targets: tuple[str, ...] = (),
) -> None:
    trace = page.evaluate(
        """
        () => {
          window.__p3032FocusObserver?.disconnect();
          if (typeof window.__p3032FocusListener === "function") {
            document.removeEventListener("focusin", window.__p3032FocusListener, true);
          }
          if (window.__p3032FocusSignals) {
            window.removeEventListener(
              'scientific-spaces:shell-history-navigation',
              window.__p3032FocusSignals.history,
            );
            window.removeEventListener(
              'scientific-spaces:shell-route-commit',
              window.__p3032FocusSignals.route,
            );
            window.removeEventListener(
              'scientific-spaces:shell-focus-operation',
              window.__p3032FocusSignals.operation,
            );
            window.removeEventListener('hashchange', window.__p3032FocusSignals.hash);
          }
          const result = [...(window.__p3032FocusTrace ?? [])];
          delete window.__p3032FocusObserver;
          delete window.__p3032FocusListener;
          delete window.__p3032FocusSignals;
          delete window.__p3032FocusTrace;
          return result;
        }
        """
    )
    _require(bool(trace), f"{label} produced no focus trace evidence")
    _require(
        all(entry.get("connected") for entry in trace),
        f"{label} observed disconnected focus: {trace}",
    )
    focus_events = [entry.get("target") for entry in trace if entry.get("source") == "focusin"]
    _require(
        not any(target in focus_events for target in forbidden_focus_targets),
        f"{label} observed a forbidden intermediate focus target: {trace}",
    )
    for index, entry in enumerate(trace):
        if entry.get("source") not in {"start", "focusin", "mutation"}:
            continue
        if entry.get("target") not in {"BODY", "missing"}:
            continue
        recovered = any(
            later.get("source") == "focusin"
            and later.get("target") in expected_focus_sequence
            for later in trace[index + 1 :]
        )
        _require(
            entry.get("source") == "mutation" and recovered,
            f"{label} settled on body or a missing element: {trace}",
        )
    next_index = 0
    for expected in expected_focus_sequence:
        try:
            next_index = focus_events.index(expected, next_index) + 1
        except ValueError as error:
            raise AssertionError(
                f"{label} missed focus target {expected}: {trace}"
            ) from error


def _verify_reader_learning_mutation_integrity(
    browser,
    *,
    iteration: int,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          window.__p3029InitialLoadOriginalFetch = originalFetch;
          window.__p3029InitialLoadGate = { pendingCount: 0, releases: [] };
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const method = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            const response = await originalFetch(...args);
            if (
              method === "GET"
              && (target.endsWith("/learning/bookmarks") || target.includes("/learning/notes/"))
            ) {
              window.__p3029InitialLoadGate.pendingCount += 1;
              await new Promise((resolve) => window.__p3029InitialLoadGate.releases.push(resolve));
            }
            return response;
          };
        })();
        """
    )
    _install_network_guard(context, blocked_external)
    session_sequence = 0

    def provide_isolated_reader_session(route) -> None:
        nonlocal session_sequence
        if route.request.method != "POST":
            route.continue_()
            return
        session_sequence += 1
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": f"p3-029-{iteration}-{session_sequence}",
                    "article_id": json.loads(route.request.post_data or "{}").get("article_id"),
                    "started_at": "2026-09-05T00:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        )

    context.route(re.compile(r".*/learning/sessions$"), provide_isolated_reader_session)
    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="reader-mutation-integrity",
    )
    page.goto(f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    page.wait_for_function(
        "() => window.__p3029InitialLoadGate?.pendingCount === 2",
        timeout=30_000,
    )
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_disabled()
    expect(page.get_by_text("Loading bookmark status.", exact=True)).to_be_visible()
    initial_draft = page.get_by_label("New learning note", exact=True)
    initial_draft.fill("P3-029 initial load guard")
    expect(page.get_by_role("button", name="Add note", exact=True)).to_be_disabled()
    expect(page.get_by_text("Loading notes...", exact=True)).to_be_visible()
    page.evaluate(
        """
        () => {
          for (const release of window.__p3029InitialLoadGate.releases.splice(0)) release();
        }
        """
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_role("button", name="Add note", exact=True)).to_be_enabled()
    initial_draft.fill("")
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3029InitialLoadOriginalFetch;
          delete window.__p3029InitialLoadOriginalFetch;
          delete window.__p3029InitialLoadGate;
        }
        """
    )

    context.close()
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    context.route(re.compile(r".*/learning/sessions$"), provide_isolated_reader_session)
    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="reader-mutation-integrity",
    )
    page.goto(f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )

    baseline_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    baseline_note_count = int(baseline_notes["total"])
    baseline_note_content = f"P3-011 iteration {iteration}"
    baseline_note_records = [
        item for item in baseline_notes["items"] if item["content"] == baseline_note_content
    ]
    _require(len(baseline_note_records) == 1, f"Reader mutation baseline note is ambiguous: {baseline_notes}")
    baseline_note_id = baseline_note_records[0]["note_id"]
    duplicate_text = f"P3-029 duplicate guard {iteration}"
    _install_mutation_response_gate(page, f"/learning/notes/{CRB_ARTICLE_ID}", "POST")
    page.get_by_label("New learning note", exact=True).fill(duplicate_text)
    add_note = page.get_by_role("button", name="Add note", exact=True)
    add_note.evaluate("button => { button.click(); button.click(); }")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_role("button", name="Saving note...", exact=True)).to_be_disabled()
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("Saving note...")
    pending_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        pending_notes["total"] == baseline_note_count + 1,
        f"rapid note activation did not persist exactly one record: {pending_notes}",
    )
    _release_mutation_response_gate(page)
    note_mutation_status = page.get_by_test_id("note-mutation-status")
    expect(note_mutation_status).to_have_text("Note saved.")
    expect(note_mutation_status).to_be_focused()
    _require_visible_focus(note_mutation_status, "Reader duplicate-safe note-create result")
    duplicate_note = page.get_by_test_id("learning-note").filter(has_text=duplicate_text)
    expect(duplicate_note).to_have_count(1)
    confirmed_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    duplicate_records = [item for item in confirmed_notes["items"] if item["content"] == duplicate_text]
    _require(
        confirmed_notes["total"] == baseline_note_count + 1
        and len(duplicate_records) == 1,
        f"note persistence and Reader identity diverged: {confirmed_notes}",
    )
    _restore_mutation_response_gate(page)

    updated_duplicate_text = f"P3-036 updated note {iteration}"
    duplicate_edit = duplicate_note.get_by_role("button", name="Edit", exact=True)
    duplicate_edit.focus()
    duplicate_edit.press("Enter")
    duplicate_edit_field = page.get_by_label("Edit learning note", exact=True)
    expect(duplicate_edit_field).to_be_focused()
    _require_visible_focus(duplicate_edit_field, "Reader note edit field")
    duplicate_edit_field.fill(updated_duplicate_text)
    duplicate_editor = duplicate_edit_field.locator(
        "xpath=ancestor::article[@data-testid='learning-note']"
    )
    _install_mutation_response_gate(
        page,
        f"/learning/notes/{duplicate_records[0]['note_id']}",
        "PUT",
    )
    duplicate_save = duplicate_editor.get_by_role("button", name="Save", exact=True)
    duplicate_save.focus()
    duplicate_save.press("Enter")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    _release_mutation_response_gate(page)
    expect(note_mutation_status).to_have_text("Note updated.")
    expect(note_mutation_status).to_be_focused()
    _require_visible_focus(note_mutation_status, "Reader note-update result")
    duplicate_note = page.get_by_test_id("learning-note").filter(has_text=updated_duplicate_text)
    expect(duplicate_note).to_have_count(1)
    updated_duplicate_records = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        any(
            item["note_id"] == duplicate_records[0]["note_id"]
            and item["content"] == updated_duplicate_text
            for item in updated_duplicate_records["items"]
        ),
        f"note update did not preserve the exact record identity: {updated_duplicate_records}",
    )
    _restore_mutation_response_gate(page)

    duplicate_delete = duplicate_note.get_by_role("button", name="Delete", exact=True)
    _install_mutation_response_gate(
        page,
        f"/learning/notes/{duplicate_records[0]['note_id']}",
        "DELETE",
    )
    duplicate_delete.focus()
    _start_note_delete_focus_trace(page)
    duplicate_delete.press("Enter")
    delete_confirmation = duplicate_note.get_by_test_id("note-delete-confirmation")
    expect(delete_confirmation).to_be_visible()
    expect(delete_confirmation).to_contain_text("cannot be undone")
    cancel_delete = delete_confirmation.get_by_role("button", name="Cancel", exact=True)
    confirm_delete = delete_confirmation.get_by_role(
        "button", name="Delete permanently", exact=True
    )
    expect(cancel_delete).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "opening note deletion confirmation",
        (
            ("testid:note-mutation-status", False),
            ("button:Cancel", True),
        ),
    )
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
        "opening note deletion confirmation issued a DELETE request",
    )
    expect(page.get_by_label("New learning note", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Add note", exact=True)).to_be_disabled()
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    expect(baseline_note.get_by_role("button", name="Edit", exact=True)).to_be_disabled()
    expect(baseline_note.get_by_role("button", name="Delete", exact=True)).to_be_disabled()
    expect(cancel_delete).to_be_enabled()
    expect(confirm_delete).to_be_enabled()
    cancel_delete.press("Tab")
    expect(confirm_delete).to_be_focused()
    confirm_delete.press("Shift+Tab")
    expect(cancel_delete).to_be_focused()
    _start_note_delete_focus_trace(page)
    cancel_delete.press("Escape")
    expect(delete_confirmation).to_have_count(0)
    duplicate_delete = duplicate_note.get_by_role("button", name="Delete", exact=True)
    expect(duplicate_delete).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "escaping note deletion confirmation",
        (
            ("testid:note-mutation-status", True),
            ("button:Delete", False),
        ),
    )
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
        "Escape from note deletion confirmation issued a DELETE request",
    )

    duplicate_delete.press(" ")
    delete_confirmation = duplicate_note.get_by_test_id("note-delete-confirmation")
    cancel_delete = delete_confirmation.get_by_role("button", name="Cancel", exact=True)
    expect(cancel_delete).to_be_focused()
    cancel_delete.click()
    duplicate_delete = duplicate_note.get_by_role("button", name="Delete", exact=True)
    expect(duplicate_delete).to_be_focused()
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
        "Cancel from note deletion confirmation issued a DELETE request",
    )

    duplicate_delete.click()
    delete_confirmation = duplicate_note.get_by_test_id("note-delete-confirmation")
    expect(delete_confirmation.get_by_role("button", name="Cancel", exact=True)).to_be_focused()
    confirm_delete = delete_confirmation.get_by_role(
        "button", name="Delete permanently", exact=True
    )
    confirm_delete.press("Enter")
    page.keyboard.press("Enter")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(delete_confirmation).to_be_visible()
    expect(delete_confirmation).to_have_attribute("aria-busy", "true")
    expect(delete_confirmation).to_be_focused()
    expect(delete_confirmation.get_by_role("button", name="Cancel", exact=True)).to_be_disabled()
    expect(delete_confirmation.get_by_role("button", name="Deleting...", exact=True)).to_be_disabled()
    expect(page.get_by_label("New learning note", exact=True)).to_be_disabled()
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    expect(baseline_note.get_by_role("button", name="Edit", exact=True)).to_be_disabled()
    expect(baseline_note.get_by_role("button", name="Delete", exact=True)).to_be_disabled()
    _start_note_delete_focus_trace(page)
    delete_wait_heading = page.get_by_role("heading", name=CRB_TITLE, exact=True)
    delete_wait_heading.focus()
    _release_mutation_response_gate(page)
    note_status = page.get_by_test_id("note-mutation-status")
    expect(note_status).to_have_text("Note deleted.")
    expect(delete_wait_heading).to_be_focused()
    _require_visible_focus(delete_wait_heading, "Reader note-delete newer focus owner")
    _assert_note_delete_focus_continuity(
        page,
        "completing confirmed note deletion",
        ((f"heading:{CRB_TITLE}", True),),
    )
    expect(duplicate_note).to_have_count(0)
    deleted_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        deleted_notes["total"] == baseline_note_count,
        f"confirmed note deletion did not persist exactly once: {deleted_notes}",
    )
    _restore_mutation_response_gate(page)

    response_loss_text = f"P3-031 unconfirmed delete {iteration}"
    note_draft = page.get_by_label("New learning note", exact=True)
    note_draft.fill(response_loss_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("Note saved.")
    response_loss_note = page.get_by_test_id("learning-note").filter(
        has_text=response_loss_text
    )
    expect(response_loss_note).to_have_count(1)
    response_loss_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    response_loss_records = [
        item for item in response_loss_notes["items"] if item["content"] == response_loss_text
    ]
    _require(
        len(response_loss_records) == 1,
        f"response-loss note identity is ambiguous: {response_loss_notes}",
    )
    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/notes/{response_loss_records[0]['note_id']}",
        "DELETE",
        "intentional P3-029 unconfirmed delete result",
    )
    response_loss_note.get_by_role("button", name="Delete", exact=True).click()
    response_loss_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).focus()
    _start_note_delete_focus_trace(page)
    response_loss_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).click()
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "deletion could not be confirmed"
    )
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "Reload this Article before retrying"
    )
    expect(response_loss_note).to_have_count(1)
    expect(
        response_loss_note.get_by_role("button", name="Delete", exact=True)
    ).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "handling lost note deletion response",
        (("button:Delete", False),),
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "false")
    page.wait_for_timeout(250)
    _require(
        page.evaluate("() => window.__p3029FailureGate?.callCount") == 1,
        "lost delete response was replayed automatically",
    )
    cleaned_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        cleaned_notes["total"] == baseline_note_count
        and all(
            item["note_id"] != response_loss_records[0]["note_id"]
            for item in cleaned_notes["items"]
        ),
        f"lost delete response did not preserve the exact unknown persistence result: {cleaned_notes}",
    )
    _restore_one_shot_mutation_failure(page)

    failed_text = f"P3-029 unconfirmed draft {iteration}"
    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/notes/{CRB_ARTICLE_ID}",
        "POST",
        "intentional P3-029 unconfirmed note result",
    )
    note_draft = page.get_by_label("New learning note", exact=True)
    note_draft.fill(failed_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    failed_feedback = page.get_by_test_id("note-mutation-error")
    expect(failed_feedback).to_have_attribute("role", "alert")
    expect(failed_feedback).to_contain_text("could not be confirmed")
    expect(failed_feedback).to_be_focused()
    _require_visible_focus(failed_feedback, "Reader note-create failure")
    expect(note_draft).to_have_value(failed_text)
    expect(
        page.get_by_test_id("learning-note").filter(has_text=failed_text)
    ).to_have_count(0)
    failed_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    unknown_note_records = [item for item in failed_notes["items"] if item["content"] == failed_text]
    _require(
        failed_notes["total"] == baseline_note_count + 1 and len(unknown_note_records) == 1,
        f"lost note response did not preserve the exact unknown persistence result: {failed_notes}",
    )
    unknown_cleanup = context.request.delete(
        f"{API_URL}/learning/notes/{unknown_note_records[0]['note_id']}"
    )
    _require(unknown_cleanup.status == 204, "unknown-result note cleanup failed")
    _restore_one_shot_mutation_failure(page)

    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    expect(baseline_note).to_have_count(1)
    baseline_edit = baseline_note.get_by_role("button", name="Edit", exact=True)
    baseline_edit.focus()
    baseline_edit.press("Enter")
    retained_edit = f"P3-029 retained edit {iteration}"
    edit_field = page.get_by_label("Edit learning note", exact=True)
    expect(edit_field).to_be_focused()
    _require_visible_focus(edit_field, "Reader existing-note edit field")
    editing_note = edit_field.locator("xpath=ancestor::article[@data-testid='learning-note']")
    edit_field.fill(retained_edit)
    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/notes/{baseline_note_id}",
        "PUT",
        "intentional P3-029 unconfirmed update result",
    )
    editing_note.get_by_role("button", name="Save", exact=True).click()
    update_failure = page.get_by_test_id("note-mutation-error")
    expect(update_failure).to_contain_text(
        "update could not be confirmed"
    )
    expect(update_failure).to_be_focused()
    _require_visible_focus(update_failure, "Reader note-update failure")
    expect(edit_field).to_have_value(retained_edit)
    update_failure_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    updated_unknown_records = [
        item
        for item in update_failure_notes["items"]
        if item["note_id"] == baseline_note_id and item["content"] == retained_edit
    ]
    _require(
        len(updated_unknown_records) == 1,
        f"lost update response did not preserve the exact unknown persistence result: {update_failure_notes}",
    )
    restore_update = context.request.put(
        f"{API_URL}/learning/notes/{baseline_note_id}",
        data={"content": baseline_note_content},
    )
    _require(restore_update.status == 200, "unknown-result note update restore failed")
    restored_update_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        any(
            item["note_id"] == baseline_note_id and item["content"] == baseline_note_content
            for item in restored_update_notes["items"]
        ),
        f"unknown-result note update restore did not read back exactly: {restored_update_notes}",
    )
    _restore_one_shot_mutation_failure(page)
    cancel_note_edit = editing_note.get_by_role("button", name="Cancel", exact=True)
    cancel_note_edit.focus()
    cancel_note_edit.press("Enter")

    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    restored_edit = baseline_note.get_by_role("button", name="Edit", exact=True)
    expect(restored_edit).to_be_focused()
    _require_visible_focus(restored_edit, "Reader cancelled note edit")

    _install_one_shot_mutation_failure(
        page,
        "/learning/notes/",
        "DELETE",
        "intentional P3-029 unconfirmed delete result",
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    baseline_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).focus()
    _start_note_delete_focus_trace(page)
    baseline_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).click()
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "deletion could not be confirmed"
    )
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "Reload this Article before retrying"
    )
    expect(baseline_note).to_have_count(1)
    expect(
        baseline_note.get_by_role("button", name="Delete", exact=True)
    ).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "handling rejected note deletion request",
        (("button:Delete", False),),
    )
    page.wait_for_timeout(250)
    _require(
        page.evaluate("() => window.__p3029FailureGate?.callCount") == 1,
        "rejected delete request was replayed automatically",
    )
    delete_failure_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(delete_failure_notes["total"] == baseline_note_count, "unconfirmed delete changed persistence")
    _restore_one_shot_mutation_failure(page)

    session_payload = {
        "version": 1,
        "active_article_id": CRB_ARTICLE_ID,
        "updated_at": "2026-09-05T00:00:00.000Z",
        "items": [
            {
                "article_id": CRB_ARTICLE_ID,
                "title": CRB_TITLE,
                "section_id": None,
                "added_at": "2026-09-05T00:00:00.000Z",
            },
            {
                "article_id": ATTENTION_ARTICLE_ID,
                "title": ATTENTION_TITLE,
                "section_id": None,
                "added_at": "2026-09-05T00:01:00.000Z",
            },
        ],
    }
    page.evaluate(
        "([key, value]) => localStorage.setItem(key, value)",
        ["scientific-spaces-study-session-v1", json.dumps(session_payload, ensure_ascii=False)],
    )
    page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )

    transition_delete_requests: list[str] = []

    def record_unconfirmed_delete_request(request) -> None:
        if (
            request.method == "DELETE"
            and request.url.endswith(f"/learning/notes/{baseline_note_id}")
        ):
            transition_delete_requests.append(request.url)

    page.on("request", record_unconfirmed_delete_request)
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    _start_note_delete_focus_trace(page)
    page.evaluate(
        "() => window.history.pushState(null, '', '?from=%2Farticles%3Fq%3Dcrb')"
    )
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/articles?q=crb'"
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "invalidating an awaiting query intent",
        ((f"heading:{CRB_TITLE}", True),),
    )
    _require(
        not transition_delete_requests,
        f"query transition issued an unconfirmed DELETE: {transition_delete_requests}",
    )

    page.go_back(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/session'"
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    page.go_forward(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/articles?q=crb'"
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    _require(
        not transition_delete_requests,
        f"query history issued an unconfirmed DELETE: {transition_delete_requests}",
    )
    page.go_back(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/session'"
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    _wait_for_page_requests_to_settle(page, console_errors)
    initial_attention_transition = _declare_expected_route_transition(
        page,
        destination_url=(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Fsession"
        ),
    )
    page.get_by_role("link", name=f"Next in session: {ATTENTION_TITLE}", exact=True).click()
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    _require(
        not transition_delete_requests,
        f"Article switch issued an unconfirmed DELETE: {transition_delete_requests}",
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, initial_attention_transition)

    initial_crb_back_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
    )
    page.go_back(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, initial_crb_back_transition)
    initial_attention_forward_transition = _declare_expected_route_transition(
        page,
        destination_url=(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Fsession"
        ),
    )
    page.go_forward(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, initial_attention_forward_transition)
    second_crb_back_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
    )
    page.go_back(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    _wait_for_page_requests_to_settle(page, console_errors)
    _complete_expected_route_transition(page, second_crb_back_transition)
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    _require(
        not transition_delete_requests,
        f"history or reload issued an unconfirmed DELETE: {transition_delete_requests}",
    )
    transition_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        transition_notes["total"] == baseline_note_count,
        f"unconfirmed navigation changed note persistence: {transition_notes}",
    )

    stale_delete_text = f"P3-031 stale delete completion {iteration}"
    stale_delete_create = context.request.post(
        f"{API_URL}/learning/notes/{CRB_ARTICLE_ID}",
        data={"content": stale_delete_text},
    )
    _require(stale_delete_create.status == 200, "stale delete note setup failed")
    stale_delete_record = stale_delete_create.json()
    stale_delete_id = str(stale_delete_record["note_id"])
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    stale_delete_note = page.get_by_test_id("learning-note").filter(has_text=stale_delete_text)
    expect(stale_delete_note).to_have_count(1)
    _install_mutation_response_gate(
        page,
        f"/learning/notes/{stale_delete_id}",
        "DELETE",
    )
    stale_delete_note.get_by_role("button", name="Delete", exact=True).click()
    stale_delete_confirmation = stale_delete_note.get_by_test_id("note-delete-confirmation")
    expect(stale_delete_confirmation).to_be_visible()
    stale_delete_confirmation.get_by_role(
        "button", name="Delete permanently", exact=True
    ).press("Enter")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    _start_note_delete_focus_trace(page)
    page.evaluate(
        "() => window.history.pushState(null, '', '?from=%2Farticles%3Fq%3Dcrb')"
    )
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/articles?q=crb'"
    )
    expect(stale_delete_confirmation).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "false")
    stale_delete_note = page.get_by_test_id("learning-note").filter(has_text=stale_delete_text)
    expect(stale_delete_note).to_have_count(1)
    expect(stale_delete_note.get_by_role("button", name="Delete", exact=True)).to_be_disabled()
    stale_delete_warning = page.get_by_test_id("note-mutation-error")
    expect(stale_delete_warning).to_contain_text("could not be confirmed after navigation")
    expect(stale_delete_warning).to_contain_text("Reload this Article before retrying")
    _assert_note_delete_focus_continuity(
        page,
        "invalidating a stale note deletion",
        ((f"heading:{CRB_TITLE}", True),),
    )
    _release_mutation_response_gate(page)
    page.wait_for_timeout(250)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    expect(stale_delete_note).to_have_count(1)
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("")
    expect(stale_delete_warning).to_contain_text("could not be confirmed after navigation")
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 1,
        "stale delete completion created another DELETE request",
    )
    stale_delete_persisted = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        all(item["note_id"] != stale_delete_id for item in stale_delete_persisted["items"]),
        f"stale delete persistence result was not recorded exactly: {stale_delete_persisted}",
    )
    _restore_mutation_response_gate(page)
    page.go_back(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/session'"
    )
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_text(stale_delete_text, exact=True)).to_have_count(0)
    page.evaluate(
        "([key, value]) => localStorage.setItem(key, value)",
        ["scientific-spaces-study-session-v1", json.dumps(session_payload, ensure_ascii=False)],
    )
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )

    stale_text = f"P3-029 stale Article A {iteration}"
    _install_mutation_response_gate(page, f"/learning/notes/{CRB_ARTICLE_ID}", "POST")
    page.get_by_label("New learning note", exact=True).fill(stale_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    page.wait_for_function("() => window.__p3029MutationGate?.pendingCount === 1", timeout=30_000)
    stale_note_attention_transition = _declare_expected_route_transition(
        page,
        destination_url=(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Fsession"
        ),
    )
    page.get_by_role("link", name=f"Next in session: {ATTENTION_TITLE}", exact=True).click()
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_label("New learning note", exact=True)).to_have_value("")
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("note-mutation-error")).to_have_text("")
    _complete_expected_route_transition(page, stale_note_attention_transition)
    _release_mutation_response_gate(page)
    page.wait_for_timeout(250)
    expect(attention_heading).to_be_focused()
    expect(page.get_by_text(stale_text, exact=True)).to_have_count(0)
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("note-mutation-error")).to_have_text("")
    stale_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    stale_records = [item for item in stale_notes["items"] if item["content"] == stale_text]
    _require(len(stale_records) == 1, f"stale Article A request accounting failed: {stale_notes}")
    cleanup_response = context.request.delete(
        f"{API_URL}/learning/notes/{stale_records[0]['note_id']}"
    )
    _require(cleanup_response.status == 204, "stale Article A note cleanup failed")
    _restore_mutation_response_gate(page)

    original_stale_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    restore_crb_bookmark = any(
        item["article_id"] == CRB_ARTICLE_ID for item in original_stale_bookmarks["items"]
    )
    if restore_crb_bookmark:
        normalize_crb_bookmark = context.request.delete(
            f"{API_URL}/learning/bookmarks/{CRB_ARTICLE_ID}"
        )
        _require(normalize_crb_bookmark.status == 204, "stale bookmark destination setup failed")
    stale_bookmark_baseline = _api_json(context, "GET", "/learning/bookmarks")
    stale_bookmark_count = int(stale_bookmark_baseline["total"])
    _install_mutation_response_gate(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "POST",
    )
    page.get_by_role("button", name="Save", exact=True).click()
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    stale_bookmark_crb_transition = _declare_expected_route_transition(
        page,
        destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
    )
    page.get_by_role("link", name=f"Previous in session: {CRB_TITLE}", exact=True).click()
    crb_heading = page.get_by_role("heading", name=CRB_TITLE, exact=True)
    expect(crb_heading).to_be_visible(timeout=30_000)
    expect(crb_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_visible()
    expect(page.get_by_text("This article is not bookmarked.", exact=True)).to_be_visible()
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("bookmark-mutation-error")).to_have_text("")
    _complete_expected_route_transition(page, stale_bookmark_crb_transition)
    _release_mutation_response_gate(page)
    page.wait_for_timeout(250)
    expect(crb_heading).to_be_focused()
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_visible()
    expect(page.get_by_text("This article is not bookmarked.", exact=True)).to_be_visible()
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("bookmark-mutation-error")).to_have_text("")
    stale_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        stale_bookmarks["total"] == stale_bookmark_count + 1
        and sum(item["article_id"] == ATTENTION_ARTICLE_ID for item in stale_bookmarks["items"]) == 1,
        f"stale bookmark response accounting failed: {stale_bookmarks}",
    )
    stale_bookmark_cleanup = context.request.delete(
        f"{API_URL}/learning/bookmarks/{ATTENTION_ARTICLE_ID}"
    )
    _require(stale_bookmark_cleanup.status == 204, "stale bookmark cleanup failed")
    if restore_crb_bookmark:
        restore_crb_response = context.request.post(
            f"{API_URL}/learning/bookmarks/{CRB_ARTICLE_ID}"
        )
        _require(restore_crb_response.status == 200, "stale bookmark destination restore failed")
    _restore_mutation_response_gate(page)
    final_attention_transition = _declare_expected_route_transition(
        page,
        destination_url=(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Fsession"
        ),
    )
    page.get_by_role("link", name=f"Next in session: {ATTENTION_TITLE}", exact=True).click()
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    _complete_expected_route_transition(page, final_attention_transition)

    baseline_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    baseline_bookmark_count = int(baseline_bookmarks["total"])
    save_bookmark = page.get_by_role("button", name="Save", exact=True)
    expect(save_bookmark).to_be_visible(timeout=30_000)
    _install_mutation_response_gate(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "POST",
    )
    save_bookmark.focus()
    save_bookmark.evaluate("button => { button.click(); button.click(); }")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_role("button", name="Saving...", exact=True)).to_be_disabled()
    _release_mutation_response_gate(page)
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("Bookmark saved.")
    expect(page.get_by_role("button", name="Remove", exact=True)).to_be_visible()
    bookmark_controls = page.get_by_test_id("bookmark-controls")
    expect(bookmark_controls).to_be_focused()
    _require_visible_focus(bookmark_controls, "Reader duplicate-safe bookmark result")
    stored_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        stored_bookmarks["total"] == baseline_bookmark_count + 1
        and sum(item["article_id"] == ATTENTION_ARTICLE_ID for item in stored_bookmarks["items"]) == 1,
        f"rapid bookmark activation did not persist exactly one record: {stored_bookmarks}",
    )
    _restore_mutation_response_gate(page)
    _install_mutation_response_gate(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "DELETE",
    )
    remove_bookmark = page.get_by_role("button", name="Remove", exact=True)
    remove_bookmark.focus()
    remove_bookmark.evaluate("button => { button.click(); button.click(); }")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(page.get_by_role("button", name="Removing...", exact=True)).to_be_disabled()
    removed_before_release = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        removed_before_release["total"] == baseline_bookmark_count,
        f"rapid bookmark removal did not persist exactly once: {removed_before_release}",
    )
    attention_heading.focus()
    _release_mutation_response_gate(page)
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("Bookmark removed.")
    expect(attention_heading).to_be_focused()
    _require_visible_focus(attention_heading, "Reader newer focus after bookmark removal")
    cleaned_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(cleaned_bookmarks["total"] == baseline_bookmark_count, "bookmark cleanup failed")
    _restore_mutation_response_gate(page)

    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "POST",
        "intentional P3-029 unconfirmed bookmark result",
    )
    page.get_by_role("button", name="Save", exact=True).click()
    bookmark_failure = page.get_by_test_id("bookmark-mutation-error")
    expect(bookmark_failure).to_have_attribute("role", "alert")
    expect(bookmark_failure).to_contain_text("displayed bookmark state was kept")
    expect(bookmark_controls).to_be_focused()
    _require_visible_focus(bookmark_controls, "Reader bookmark failure result")
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_visible()
    failed_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        failed_bookmarks["total"] == baseline_bookmark_count + 1
        and sum(item["article_id"] == ATTENTION_ARTICLE_ID for item in failed_bookmarks["items"]) == 1,
        f"lost bookmark response did not preserve the exact unknown persistence result: {failed_bookmarks}",
    )
    unknown_bookmark_cleanup = context.request.delete(
        f"{API_URL}/learning/bookmarks/{ATTENTION_ARTICLE_ID}"
    )
    _require(unknown_bookmark_cleanup.status == 204, "unknown-result bookmark cleanup failed")
    _restore_one_shot_mutation_failure(page)
    context.close()

    _verify_reader_note_delete_confirmation_viewports(
        browser,
        iteration=iteration,
        baseline_note_content=baseline_note_content,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )


def _verify_reader_note_delete_confirmation_viewports(
    browser,
    *,
    iteration: int,
    baseline_note_content: str,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    session_sequence = 0

    def provide_isolated_viewport_session(route) -> None:
        nonlocal session_sequence
        if route.request.method != "POST":
            route.continue_()
            return
        session_sequence += 1
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": f"p3-031-viewport-{iteration}-{session_sequence}",
                    "article_id": json.loads(route.request.post_data or "{}").get("article_id"),
                    "started_at": "2026-09-05T00:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        )

    for viewport_width, viewport_height, viewport_label in (
        (1440, 900, "desktop"),
        (390, 844, "mobile"),
        (320, 844, "narrow"),
        (720, 450, "zoom-equivalent"),
    ):
        context = browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            locale="zh-CN",
            is_mobile=viewport_width <= 390,
        )
        _install_network_guard(context, blocked_external)
        context.route(re.compile(r".*/learning/sessions$"), provide_isolated_viewport_session)
        viewport_note_content = f"P3-031 {viewport_label} deletion focus {iteration}"
        viewport_note_create = context.request.post(
            f"{API_URL}/learning/notes/{CRB_ARTICLE_ID}",
            data={"content": viewport_note_content},
        )
        _require(
            viewport_note_create.status == 200,
            f"{viewport_label} note deletion setup failed",
        )
        viewport_note_id = str(viewport_note_create.json()["note_id"])
        page = _new_observed_page(
            context,
            console_errors,
            page_errors,
            label=f"reader-note-delete-{viewport_label}",
        )
        page.goto(f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        expect(page.get_by_test_id("notes-controls")).to_have_attribute(
            "aria-busy", "false", timeout=30_000
        )
        note = page.get_by_test_id("learning-note").filter(has_text=viewport_note_content)
        expect(note).to_have_count(1)
        delete_trigger = note.get_by_role("button", name="Delete", exact=True)
        delete_trigger.scroll_into_view_if_needed()
        _install_mutation_response_gate(
            page,
            f"/learning/notes/{viewport_note_id}",
            "DELETE",
        )
        delete_trigger.focus()
        delete_trigger.press(" ")
        confirmation = note.get_by_test_id("note-delete-confirmation")
        expect(confirmation).to_be_visible()
        cancel = confirmation.get_by_role("button", name="Cancel", exact=True)
        destructive = confirmation.get_by_role(
            "button", name="Delete permanently", exact=True
        )
        expect(cancel).to_be_focused()
        _require_visible_focus(cancel, f"{viewport_label} note delete Cancel")
        confirmation.scroll_into_view_if_needed()
        _require_viewport_containment(
            confirmation.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} note deletion confirmation",
        )
        _require_viewport_containment(
            cancel.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} note deletion Cancel",
        )
        _require_viewport_containment(
            destructive.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} permanent deletion action",
        )
        _require(
            _document_width(page) <= viewport_width,
            f"{viewport_label} note deletion confirmation caused horizontal overflow",
        )
        cancel.press("Escape")
        expect(note.get_by_test_id("note-delete-confirmation")).to_have_count(0)
        expect(note.get_by_role("button", name="Delete", exact=True)).to_be_focused()
        _require(
            page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
            f"{viewport_label} confirmation cancellation issued a DELETE request",
        )
        persisted = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
        _require(
            any(item["note_id"] == viewport_note_id for item in persisted["items"]),
            f"{viewport_label} cancellation did not preserve the exact note: {persisted}",
        )
        delete_trigger = note.get_by_role("button", name="Delete", exact=True)
        delete_trigger.click()
        confirmation = note.get_by_test_id("note-delete-confirmation")
        destructive = confirmation.get_by_role(
            "button", name="Delete permanently", exact=True
        )
        destructive.press("Enter")
        page.wait_for_function(
            "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
            timeout=30_000,
        )
        expect(confirmation).to_have_attribute("aria-busy", "true")
        expect(confirmation).to_be_focused()
        _require_visible_focus(confirmation, f"{viewport_label} pending deletion confirmation")
        pending_destructive = confirmation.get_by_role("button", name="Deleting...", exact=True)
        expect(confirmation.get_by_role("button", name="Cancel", exact=True)).to_be_disabled()
        expect(pending_destructive).to_be_disabled()
        expect(page.get_by_label("New learning note", exact=True)).to_be_disabled()
        expect(page.get_by_role("button", name="Add note", exact=True)).to_be_disabled()
        for edit_button in page.get_by_role("button", name="Edit", exact=True).all():
            expect(edit_button).to_be_disabled()
        for other_delete in page.get_by_role("button", name="Delete", exact=True).all():
            expect(other_delete).to_be_disabled()
        confirmation.scroll_into_view_if_needed()
        _require_viewport_containment(
            confirmation.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} pending deletion confirmation",
        )
        _require(
            _document_width(page) <= viewport_width,
            f"{viewport_label} pending deletion caused horizontal overflow",
        )
        _release_mutation_response_gate(page)
        note_status = page.get_by_test_id("note-mutation-status")
        expect(note_status).to_have_text("Note deleted.")
        expect(note_status).to_be_focused()
        _require_visible_focus(note_status, f"{viewport_label} deletion status")
        _require_viewport_containment(
            note_status.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} deletion status",
        )
        expect(note).to_have_count(0)
        persisted_after_delete = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
        _require(
            all(item["note_id"] != viewport_note_id for item in persisted_after_delete["items"]),
            f"{viewport_label} confirmed deletion did not remove the exact note: {persisted_after_delete}",
        )
        _require(
            any(item["content"] == baseline_note_content for item in persisted_after_delete["items"]),
            f"{viewport_label} confirmed deletion changed the baseline note: {persisted_after_delete}",
        )
        _require(
            _document_width(page) <= viewport_width,
            f"{viewport_label} deletion status caused horizontal overflow",
        )
        _restore_mutation_response_gate(page)
        context.close()


def _start_note_delete_focus_trace(page) -> None:
    page.evaluate(
        """
        () => {
          window.__p3031FocusTrace = [];
          const describe = (node) => {
            if (!(node instanceof HTMLElement)) return "missing";
            const testId = node.dataset.testid;
            if (testId) return `testid:${testId}`;
            if (node instanceof HTMLButtonElement) {
              return `button:${node.textContent?.trim() ?? ""}`;
            }
            if (/^H[1-6]$/.test(node.tagName)) {
              return `heading:${node.textContent?.trim() ?? ""}`;
            }
            return node.tagName;
          };
          const recordFocus = (source) => {
            window.__p3031FocusTrace.push({
              source,
              target: describe(document.activeElement),
              confirmationMounted: Boolean(
                document.querySelector('[data-testid="note-delete-confirmation"]')
              ),
            });
          };
          const focusListener = () => recordFocus("focusin");
          window.__p3031FocusListener = focusListener;
          document.addEventListener("focusin", focusListener, true);
          const observer = new MutationObserver(() => recordFocus("mutation"));
          observer.observe(document.body, { childList: true, subtree: true });
          window.__p3031FocusObserver = observer;
          recordFocus("start");
        }
        """
    )


def _assert_note_delete_focus_continuity(
    page,
    label: str,
    expected_focus_sequence: tuple[tuple[str, bool], ...],
) -> None:
    focus_trace = page.evaluate(
        """
        () => {
          window.__p3031FocusObserver?.disconnect();
          if (typeof window.__p3031FocusListener === "function") {
            document.removeEventListener("focusin", window.__p3031FocusListener, true);
          }
          const trace = [...(window.__p3031FocusTrace ?? [])];
          delete window.__p3031FocusObserver;
          delete window.__p3031FocusListener;
          delete window.__p3031FocusTrace;
          return trace;
        }
        """
    )
    _require(bool(focus_trace), f"{label} produced no focus trace evidence")
    _require(
        all(entry.get("target") != "BODY" for entry in focus_trace),
        f"{label} dropped focus to body: {focus_trace}",
    )
    focus_events = [entry for entry in focus_trace if entry.get("source") == "focusin"]
    next_index = 0
    for expected_target, expected_confirmation in expected_focus_sequence:
        for index in range(next_index, len(focus_events)):
            entry = focus_events[index]
            if (
                entry.get("target") == expected_target
                and entry.get("confirmationMounted") is expected_confirmation
            ):
                next_index = index + 1
                break
        else:
            raise AssertionError(
                f"{label} missed focus bridge {expected_target} "
                f"with confirmationMounted={expected_confirmation}: {focus_trace}"
            )


def _install_mutation_response_gate(page, endpoint: str, method: str) -> None:
    if method == "DELETE":
        _declare_expected_no_content_response(
            page,
            source_url=f"{BROWSER_API_URL}{endpoint}",
            method=method,
        )
    page.evaluate(
        """
        ({ endpoint, method }) => {
          if (typeof window.__p3029MutationOriginalFetch === "function") {
            throw new Error("P3-029 mutation response gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3029MutationOriginalFetch = originalFetch;
          window.__p3029MutationGate = {
            endpoint,
            method,
            callCount: 0,
            pendingCount: 0,
            completedCount: 0,
            release: null,
          };
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (!target.includes(endpoint) || requestMethod !== method) {
              return originalFetch(...args);
            }
            const gate = window.__p3029MutationGate;
            gate.callCount += 1;
            const response = await originalFetch(...args);
            gate.pendingCount += 1;
            await new Promise((resolve) => { gate.release = resolve; });
            gate.release = null;
            gate.completedCount += 1;
            return response;
          };
        }
        """,
        {"endpoint": endpoint, "method": method},
    )


def _release_mutation_response_gate(page) -> None:
    page.wait_for_function(
        "() => typeof window.__p3029MutationGate?.release === 'function'",
        timeout=30_000,
    )
    expected_count = page.evaluate(
        """
        () => {
          const gate = window.__p3029MutationGate;
          const release = gate.release;
          gate.release = null;
          release();
          return gate.pendingCount;
        }
        """
    )
    page.wait_for_function(
        "expected => window.__p3029MutationGate?.completedCount >= expected",
        arg=expected_count,
        timeout=30_000,
    )


def _restore_mutation_response_gate(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3029MutationOriginalFetch === "function") {
            window.fetch = window.__p3029MutationOriginalFetch;
            delete window.__p3029MutationOriginalFetch;
            delete window.__p3029MutationGate;
          }
        }
        """
    )


def _install_one_shot_mutation_failure(
    page,
    endpoint: str,
    method: str,
    message: str,
) -> None:
    page.evaluate(
        """
        ({ endpoint, method, message }) => {
          if (typeof window.__p3029FailureOriginalFetch === "function") {
            throw new Error("P3-029 failure gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3029FailureOriginalFetch = originalFetch;
          window.__p3029FailureGate = { callCount: 0 };
          let rejected = false;
          window.fetch = (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (target.includes(endpoint) && requestMethod === method) {
              window.__p3029FailureGate.callCount += 1;
              if (!rejected) {
                rejected = true;
                return Promise.reject(new Error(message));
              }
            }
            return originalFetch(...args);
          };
        }
        """,
        {"endpoint": endpoint, "method": method, "message": message},
    )


def _install_one_shot_mutation_response_loss(
    page,
    endpoint: str,
    method: str,
    message: str,
) -> None:
    if method == "DELETE":
        _declare_expected_no_content_response(
            page,
            source_url=f"{BROWSER_API_URL}{endpoint}",
            method=method,
        )
    page.evaluate(
        """
        ({ endpoint, method, message }) => {
          if (typeof window.__p3029FailureOriginalFetch === "function") {
            throw new Error("P3-029 response-loss gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3029FailureOriginalFetch = originalFetch;
          window.__p3029FailureGate = { callCount: 0 };
          let rejected = false;
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (target.includes(endpoint) && requestMethod === method) {
              window.__p3029FailureGate.callCount += 1;
              if (!rejected) {
                rejected = true;
                const response = await originalFetch(...args);
                await response.clone().arrayBuffer();
                throw new Error(message);
              }
            }
            return originalFetch(...args);
          };
        }
        """,
        {"endpoint": endpoint, "method": method, "message": message},
    )


def _restore_one_shot_mutation_failure(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3029FailureOriginalFetch === "function") {
            window.fetch = window.__p3029FailureOriginalFetch;
            delete window.__p3029FailureOriginalFetch;
            delete window.__p3029FailureGate;
          }
        }
        """
    )


def _install_network_guard(context, blocked_external: list[str]) -> None:
    _require(
        not context.pages,
        "network guard must be installed before any context page is created",
    )
    context.add_init_script(
        """
        (() => {
          class BlockedWorker {
            constructor() {
              throw new Error("Worker network surfaces are disabled in Product E2E");
            }
          }
          Object.defineProperties(globalThis, {
            Worker: {
              configurable: false,
              enumerable: true,
              value: BlockedWorker,
              writable: false,
            },
            SharedWorker: {
              configurable: false,
              enumerable: true,
              value: BlockedWorker,
              writable: false,
            },
            __scientificSpacesWorkerNetworkBlocked: {
              configurable: false,
              value: true,
              writable: false,
            },
          });
        })();
        """
    )
    if isinstance(blocked_external, NetworkGuardLog):
        tracker: dict[str, object] = {
            "context": context,
            "pages": [],
            "expected_page_ids": set(),
        }
        blocked_external.page_trackers.append(tracker)
        setattr(context, "_scientific_spaces_page_tracker", tracker)

        def track_page(page) -> None:
            opener = page.opener()
            pages = tracker["pages"]
            assert isinstance(pages, list)
            pages.append(
                {
                    "page_id": _page_identity(page),
                    "opener_id": _page_identity(opener) if opener is not None else None,
                    "page": page,
                }
            )

        context.on("page", track_page)

    def record_blocked(value: str) -> None:
        blocked_external.append(value)

    def audit_request_origin(request) -> None:
        parsed = urlparse(request.url)
        if parsed.scheme in {"http", "https"} and not _is_allowed_http_url(
            request.url
        ):
            record_blocked(request.url)

    context.on("request", audit_request_origin)

    def route_request(route) -> None:
        parsed = urlparse(route.request.url)
        if parsed.scheme in {"about", "blob", "data"} or _is_allowed_http_url(
            route.request.url
        ):
            route.continue_()
            return
        record_blocked(route.request.url)
        route.abort("blockedbyclient")

    def route_web_socket(web_socket) -> None:
        if _is_allowed_websocket_url(web_socket.url):
            web_socket.connect_to_server()
            return
        record_blocked(f"websocket:{web_socket.url}")
        web_socket.close(code=1008, reason="external network blocked by Product E2E")

    context.route("**/*", route_request)
    context.route_web_socket("**/*", route_web_socket)


def _mark_expected_popup(
    blocked_external: list[str],
    context,
    page,
) -> None:
    _require(
        isinstance(blocked_external, NetworkGuardLog),
        "popup expectation requires the structured network guard",
    )
    assert isinstance(blocked_external, NetworkGuardLog)
    tracker = next(
        (
            item
            for item in blocked_external.page_trackers
            if item["context"] is context
        ),
        None,
    )
    _require(tracker is not None, "popup context was not registered")
    assert tracker is not None
    page_id = _page_identity(page)
    pages = tracker["pages"]
    expected_page_ids = tracker["expected_page_ids"]
    assert isinstance(pages, list) and isinstance(expected_page_ids, set)
    _require(
        any(item["page_id"] == page_id for item in pages),
        f"expected page was not observed by the context guard: {page_id}",
    )
    expected_page_ids.add(page_id)


def _mark_expected_context_page(context, page) -> None:
    tracker = getattr(context, "_scientific_spaces_page_tracker", None)
    _require(tracker is not None, "page context was not registered")
    page_id = _page_identity(page)
    pages = tracker["pages"]
    expected_page_ids = tracker["expected_page_ids"]
    assert isinstance(pages, list) and isinstance(expected_page_ids, set)
    _require(
        any(item["page_id"] == page_id for item in pages),
        f"expected page was not observed by the context guard: {page_id}",
    )
    expected_page_ids.add(page_id)


def _unexpected_context_pages(blocked_external: list[str]) -> list[dict[str, object]]:
    if not isinstance(blocked_external, NetworkGuardLog):
        return []
    unexpected: list[dict[str, object]] = []
    for tracker in blocked_external.page_trackers:
        pages = tracker["pages"]
        expected_page_ids = tracker["expected_page_ids"]
        assert isinstance(pages, list) and isinstance(expected_page_ids, set)
        for item in pages:
            if item["page_id"] in expected_page_ids:
                continue
            page = item["page"]
            unexpected.append(
                {
                    "page_id": item["page_id"],
                    "opener_id": item["opener_id"],
                    "url": page.url if not page.is_closed() else "<closed>",
                }
            )
    return unexpected


def verify_backend_restart_persistence(
    runtime: dict[str, Path | dict[str, str]],
) -> dict[str, object]:
    environment = os.environ.copy()
    environment.update(runtime["environment"])
    log_path = Path(runtime["root"]) / "restart-backend.log"
    process: subprocess.Popen[str] | None = None
    _require_port_free(8000)
    try:
        with log_path.open("w", encoding="utf-8") as handle:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--app-dir",
                    str(BACKEND_ROOT),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT,
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            _wait_for_url(f"{API_URL}/health", process, log_path)
        stats = _read_json_url(f"{API_URL}/learning/stats")
        sessions = _read_json_url(f"{API_URL}/learning/sessions")
        checks = {
            "completed_states": stats.get("completed_count") == 2,
            "bookmark": stats.get("bookmark_count") == 1,
            "note": stats.get("note_count") == 1,
            "ended_sessions": sessions.get("total") == 25
            and all(item.get("ended_at") for item in sessions.get("items", [])),
        }
        _require(all(checks.values()), f"restart persistence checks failed: {checks}")
        return {"status": "PASS", "checks": checks}
    finally:
        _stop_process(process)


def _api_json(context, method: str, path: str) -> dict[str, object]:
    response = context.request.fetch(f"{API_URL}{path}", method=method)
    _require(response.ok, f"{method} {path} returned {response.status}")
    payload = response.json()
    _require(isinstance(payload, dict), f"{method} {path} did not return an object")
    return payload


def _read_json_url(url: str) -> dict[str, object]:
    with urlopen(url, timeout=5) as response:
        payload = json.load(response)
    _require(isinstance(payload, dict), f"{url} did not return an object")
    return payload


def _new_observed_page(
    context,
    console_errors: list[str],
    page_errors: list[str],
    *,
    label: str,
):
    page = context.new_page()
    _mark_expected_context_page(context, page)

    def capture_console(message) -> None:
        if message.type != "error":
            return
        _capture_console_error(console_errors, message, label=label, page=page)

    page.on("console", capture_console)
    if isinstance(console_errors, ConsoleErrorLog):
        console_errors.observe_http_errors(page, label=label)
    page.on("pageerror", lambda error: _capture_page_error(page_errors, label, page, error))
    return page


def _console_error_evidence(message, *, label: str, page) -> dict[str, object]:
    producer_page = message.page
    worker = message.worker
    listener_page_id = _page_identity(page)
    producer_page_id = (
        _page_identity(producer_page) if producer_page is not None else ""
    )
    return {
        "expectation_id": None,
        "network_request_id": None,
        "label": label,
        "listener_page_id": listener_page_id,
        "listener_page_url": page.url,
        "page_id": producer_page_id,
        "page_url": producer_page.url if producer_page is not None else "",
        "same_page": producer_page_id == listener_page_id,
        "worker_url": worker.url if worker is not None else "",
        "text": message.text,
        "url": str(message.location.get("url") or ""),
    }


def _capture_console_error(
    console_errors: list[str],
    message,
    *,
    label: str,
    page,
) -> None:
    if message.type != "error":
        return
    if isinstance(console_errors, ConsoleErrorLog):
        console_errors.capture(message, label=label, page=page)
        return
    console_errors.append(message.text)


def _fulfill_expected_http_error(
    route,
    *,
    console_errors: ConsoleErrorLog,
    page,
    expectation_ids: tuple[str, ...],
    body: str,
) -> None:
    request = route.request
    expectation = console_errors.bind_http_error_request(
        expectation_ids,
        request=request,
        page=page,
    )
    route.fulfill(
        status=int(expectation["status"]),
        headers={
            "content-type": "application/json",
            CONTROLLED_HTTP_EXPECTATION_HEADER: str(expectation["expectation_id"]),
        },
        body=body,
    )


def _forward_expected_http_error(
    route,
    *,
    console_errors: ConsoleErrorLog,
    page,
    expectation_ids: tuple[str, ...],
) -> None:
    expectation = console_errors.bind_http_error_request(
        expectation_ids,
        request=route.request,
        page=page,
    )
    response = route.fetch(max_redirects=0)
    _require(
        response.url == route.request.url
        and response.status == expectation["status"],
        "forwarded controlled HTTP request returned an unexpected status: "
        f"expected_url={route.request.url} actual_url={response.url} "
        f"expected_status={expectation['status']} actual_status={response.status}",
    )
    headers = dict(response.headers)
    headers[CONTROLLED_HTTP_EXPECTATION_HEADER] = str(
        expectation["expectation_id"]
    )
    route.fulfill(response=response, headers=headers)


def _declare_expected_http_errors(
    console_errors: ConsoleErrorLog,
    *,
    label: str,
    page_url: str,
    source_url: str,
    method: str = "GET",
    count: int = 1,
) -> tuple[str, ...]:
    return console_errors.declare_http_errors(
        label=label,
        page_url=page_url,
        source_url=source_url,
        status=503,
        method=method,
        resource_type="fetch",
        navigation_request=False,
        count=count,
    )


def _declare_expected_no_content_response(
    page,
    *,
    source_url: str,
    method: str,
) -> str:
    console_errors = getattr(page, "_scientific_spaces_console_error_log", None)
    _require(
        isinstance(console_errors, ConsoleErrorLog),
        "204 response expectation requires the structured console ledger",
    )
    assert isinstance(console_errors, ConsoleErrorLog)
    return console_errors.declare_no_content_response(
        page=page,
        source_url=source_url,
        method=method,
    )


def _declare_expected_route_transition(
    page,
    *,
    destination_url: str,
    request_page_url: str | None = None,
    allow_speculative_cancellations: bool = False,
    allow_post_terminal_destination_commit: bool = False,
    allow_complete_precursor_snapshot: bool = True,
    cancelled_route_urls: tuple[str, ...] = (),
    cancelled_read_urls: tuple[str, ...] = (),
) -> str:
    console_errors = getattr(page, "_scientific_spaces_console_error_log", None)
    _require(
        isinstance(console_errors, ConsoleErrorLog),
        "route transition expectation requires the structured console ledger",
    )
    assert isinstance(console_errors, ConsoleErrorLog)
    return console_errors.declare_route_transition(
        page=page,
        destination_url=destination_url,
        request_page_url=request_page_url,
        allow_speculative_cancellations=allow_speculative_cancellations,
        allow_post_terminal_destination_commit=(
            allow_post_terminal_destination_commit
        ),
        allow_complete_precursor_snapshot=(
            allow_complete_precursor_snapshot
        ),
        cancelled_route_urls=cancelled_route_urls,
        cancelled_read_urls=cancelled_read_urls,
    )


def _complete_expected_route_transition(page, expectation_id: str) -> None:
    console_errors = getattr(page, "_scientific_spaces_console_error_log", None)
    _require(
        isinstance(console_errors, ConsoleErrorLog),
        "route transition completion requires the structured console ledger",
    )
    assert isinstance(console_errors, ConsoleErrorLog)
    console_errors.complete_route_transition(
        page=page,
        expectation_id=expectation_id,
    )


def _bind_expected_post_terminal_destination_request(
    page,
    *,
    expectation_id: str,
    evidence: dict[str, object],
) -> None:
    console_errors = getattr(page, "_scientific_spaces_console_error_log", None)
    _require(
        isinstance(console_errors, ConsoleErrorLog),
        "post-terminal destination binding requires the structured console ledger",
    )
    assert isinstance(console_errors, ConsoleErrorLog)
    console_errors.bind_post_terminal_destination_request(
        expectation_id=expectation_id,
        evidence=evidence,
    )


def _wait_for_page_requests_to_settle(
    page,
    console_errors: ConsoleErrorLog,
    *,
    timeout_ms: int = 10_000,
    quiet_ms: int = 750,
) -> None:
    """Require a stable quiet window before an intentional page transition."""
    page_id = _page_identity(page)
    deadline = time.monotonic() + timeout_ms / 1_000
    quiet_since: float | None = None
    while True:
        pending = [
            {
                "source_url": evidence.get("source_url"),
                "method": evidence.get("method"),
                "resource_type": evidence.get("resource_type"),
                "response_status": evidence.get("response_status"),
            }
            for evidence in console_errors.request_evidence.values()
            if evidence.get("page_id") == page_id
            and _is_product_browser_request(evidence)
            and evidence.get("finished") is not True
            and evidence.get("failure") is None
        ]
        now = time.monotonic()
        if pending:
            quiet_since = None
        elif quiet_since is None:
            quiet_since = now
        elif now - quiet_since >= quiet_ms / 1_000:
            return
        if now >= deadline:
            raise E2EFailure(
                "page requests did not settle before an intentional transition: "
                f"page={page.url} pending={pending}"
            )
        page.wait_for_timeout(50)


def _select_exact_route_request_terminal_candidate(
    candidates: list[dict[str, object]],
    *,
    allow_response_backed_route_abort: bool,
    route_key: tuple[object, ...],
    current_page_url: str,
    current_navigation_generation: int,
) -> dict[str, object] | None:
    successful_candidates = [
        evidence for evidence in candidates if evidence.get("finished") is True
    ]
    aborted_candidates = [
        evidence for evidence in candidates if evidence.get("failure") is not None
    ]
    pending_candidates = [
        evidence
        for evidence in candidates
        if evidence.get("finished") is not True
        and evidence.get("failure") is None
    ]
    for evidence in successful_candidates:
        status = evidence.get("response_status")
        _require(
            evidence.get("failure") is None
            and isinstance(status, int)
            and 200 <= status < 300
            and evidence.get("response_url") == evidence.get("source_url"),
            "exact route request did not finish successfully: " f"{evidence}",
        )
    response_backed_abort_candidates = []
    for evidence in aborted_candidates:
        status = evidence.get("response_status")
        navigation_generation = evidence.get("navigation_generation")
        response_backed_route_abort_candidate = (
            allow_response_backed_route_abort
            and evidence.get("failure") == "net::ERR_ABORTED"
            and isinstance(status, int)
            and 200 <= status < 300
            and evidence.get("response_url") == evidence.get("source_url")
            and isinstance(navigation_generation, int)
        )
        if (
            response_backed_route_abort_candidate
            and _route_document_key(current_page_url) == route_key
            and current_navigation_generation > navigation_generation
        ):
            response_backed_abort_candidates.append(evidence)
            continue
        if not response_backed_route_abort_candidate:
            raise E2EFailure(
                "exact route request failed before its lifecycle was proven: "
                f"{evidence}"
            )
    if pending_candidates or (
        len(response_backed_abort_candidates) != len(aborted_candidates)
    ):
        return None
    _require(
        len(candidates) == 1,
        "response-backed route request produced an ambiguous retry set: "
        f"candidates={candidates}",
    )
    return (
        response_backed_abort_candidates[0]
        if response_backed_abort_candidates
        else successful_candidates[0]
    )


def _require_unambiguous_response_backed_route_abort(
    selected_candidate: dict[str, object],
    all_exact_candidates: list[dict[str, object]],
    *,
    source_url: str,
    cache_precursor_evidences: tuple[dict[str, object], ...] = (),
) -> None:
    if selected_candidate.get("failure") is None:
        return
    expected_candidates = [selected_candidate]
    expected_candidates.extend(cache_precursor_evidences)
    _require(
        len(all_exact_candidates) == len(expected_candidates)
        and all(
            any(candidate is expected for candidate in all_exact_candidates)
            for expected in expected_candidates
        ),
        "response-backed route abort had a competing exact destination lifecycle: "
        f"source={source_url} candidates={all_exact_candidates}",
    )


def _wait_for_exact_route_request_to_finish(
    page,
    console_errors: ConsoleErrorLog,
    *,
    source_url: str,
    after_sequence: int,
    timeout_ms: int = 3_000,
    discovery_ms: int = 500,
    expect_prefetch: bool = True,
    require_observed_request: bool = False,
    allow_response_backed_route_abort: bool = False,
    cache_precursor_expectation_id: str | None = None,
) -> dict[str, object] | None:
    _require(
        not allow_response_backed_route_abort or require_observed_request,
        "response-backed route abort handling requires an observed route request",
    )
    _require(
        not allow_response_backed_route_abort or not expect_prefetch,
        "response-backed route abort handling cannot target a prefetch request",
    )
    _require(
        cache_precursor_expectation_id is None
        or allow_response_backed_route_abort,
        "route cache precursor requires response-backed abort handling",
    )
    page_id = _page_identity(page)
    route_key = _route_document_key(source_url)
    cache_precursor_evidences: tuple[dict[str, object], ...] = ()
    route_expectation: dict[str, object] | None = None
    if cache_precursor_expectation_id is not None:
        cache_expectations = [
            expectation
            for expectation in console_errors.route_transition_expectations
            if expectation.get("expectation_id")
            == cache_precursor_expectation_id
        ]
        _require(
            len(cache_expectations) == 1
            and cache_expectations[0].get(
                "allow_complete_precursor_snapshot"
            )
            is True
            and cache_expectations[0].get("page_id") == page_id
            and _route_document_key(
                str(cache_expectations[0].get("destination_url") or "")
            )
            == route_key,
            "route cache precursor expectation was missing or mismatched: "
            f"{cache_precursor_expectation_id}",
        )
        cache_precursors = _route_transition_cache_precursors(
            console_errors,
            cache_expectations[0],
        )
        route_expectation = cache_expectations[0]
        _require(
            cache_precursors is not None,
            "route cache precursor expectation was invalid: "
            f"{cache_expectations[0]}",
        )
        cache_precursor_evidences = tuple(
            evidence for _, evidence in cache_precursors
        )
    started_at = time.monotonic()
    deadline = started_at + timeout_ms / 1_000
    discovery_deadline = started_at + discovery_ms / 1_000
    stable_signature: tuple[tuple[object, ...], ...] | None = None
    stable_since: float | None = None
    while True:
        all_exact_candidate_items = [
            (request_id, evidence)
            for request_id, evidence in console_errors.request_evidence.items()
            if evidence.get("page_id") == page_id
            and isinstance(evidence.get("start_sequence"), int)
            and evidence.get("rsc_request") is True
            and evidence.get("method") == "GET"
            and evidence.get("resource_type") in {"fetch", "xhr"}
            and evidence.get("navigation_request") is False
            and evidence.get("main_frame") is True
            and not evidence.get("service_worker_url")
            and _route_document_key(str(evidence.get("source_url") or ""))
            == route_key
            and not _is_framework_prefetch_cancellation(console_errors, evidence)
        ]
        window_candidate_items = [
            (request_id, evidence)
            for request_id, evidence in all_exact_candidate_items
            if int(evidence["start_sequence"]) > after_sequence
        ]
        candidate_items = [
            (request_id, evidence)
            for request_id, evidence in window_candidate_items
            if (
                evidence.get("next_router_prefetch") is True
                or evidence.get("purpose") == "prefetch"
                or str(evidence.get("sec_purpose") or "").split(";", 1)[0]
                == "prefetch"
            )
            is expect_prefetch
        ]
        candidates = [evidence for _, evidence in candidate_items]
        _require(
            len(candidates) <= (2 if allow_response_backed_route_abort else 1),
            "exact route request produced ambiguous matching lifecycles: "
            f"source={source_url} candidates={candidates}",
        )
        if candidate_items:
            selected_candidate = _select_exact_route_request_terminal_candidate(
                candidates,
                allow_response_backed_route_abort=(
                    allow_response_backed_route_abort
                ),
                route_key=route_key,
                current_page_url=page.url,
                current_navigation_generation=(
                    console_errors._page_navigation_generations.get(page_id, 0)
                ),
            )
            if allow_response_backed_route_abort:
                if selected_candidate is not None:
                    ambiguity_items = all_exact_candidate_items
                    needs_post_terminal_recovery = (
                        selected_candidate.get("failure") is not None
                        and (
                            route_expectation is None
                            or _route_document_key(
                                str(selected_candidate.get("page_url") or "")
                            ) not in {
                                _route_document_key(str(route_expectation["request_page_url"])),
                                route_key,
                            }
                            and not _has_pre_start_route_navigation(
                                console_errors, route_expectation, selected_candidate
                            )
                        )
                    )
                    if needs_post_terminal_recovery:
                        _require_unambiguous_response_backed_route_abort(
                            selected_candidate,
                            [evidence for _, evidence in ambiguity_items],
                            source_url=source_url,
                            cache_precursor_evidences=cache_precursor_evidences,
                        )
                    signature_items = (
                        ambiguity_items
                        if needs_post_terminal_recovery
                        else candidate_items
                    )
                    signature = tuple(
                        (
                            request_id,
                            evidence.get("start_sequence"),
                            evidence.get("response_sequence"),
                            evidence.get("terminal_sequence"),
                            evidence.get("finished"),
                            evidence.get("failure"),
                        )
                        for request_id, evidence in signature_items
                    )
                    now = time.monotonic()
                    if signature != stable_signature:
                        stable_signature = signature
                        stable_since = now
                    elif (
                        stable_since is not None
                        and now - stable_since
                        >= POST_TERMINAL_DESTINATION_COMMIT_MAX_SECONDS
                    ):
                        return selected_candidate
                else:
                    stable_signature = None
                    stable_since = None
            elif selected_candidate is not None:
                return selected_candidate
        now = time.monotonic()
        if not candidate_items and now >= discovery_deadline:
            if require_observed_request:
                raise E2EFailure(
                    "required exact route request did not start: "
                    f"source={source_url} expect_prefetch={expect_prefetch}"
                )
            return None
        if now >= deadline:
            raise E2EFailure(
                "exact route request did not reach a terminal state: "
                f"source={source_url} candidates={candidates}"
            )
        page.wait_for_timeout(25)


def _wait_for_declared_http_errors(
    page,
    console_errors: ConsoleErrorLog,
    *,
    expectation_ids: tuple[str, ...],
    timeout_ms: int = 5_000,
) -> None:
    _require(
        len(expectation_ids) == len(set(expectation_ids)),
        f"controlled HTTP declaration IDs are not unique: {expectation_ids}",
    )
    selected = [
        item
        for item in console_errors.expectations
        if item["expectation_id"] in expectation_ids
    ]
    _require(
        {item["expectation_id"] for item in selected} == set(expectation_ids),
        f"controlled HTTP declarations are missing: {expectation_ids}",
    )
    unbound_requests = [
        item["expectation_id"]
        for item in selected
        if item["request_id"] is None
    ]
    _require(
        not unbound_requests,
        "controlled HTTP declarations were not bound to Playwright requests: "
        f"{unbound_requests}",
    )
    deadline = time.monotonic() + timeout_ms / 1_000
    while any(item["network_request_id"] is None for item in selected):
        if time.monotonic() >= deadline:
            break
        page.wait_for_timeout(10)
    unbound_network_requests = [
        item["expectation_id"]
        for item in selected
        if item["network_request_id"] is None
    ]
    _require(
        not unbound_network_requests,
        "controlled HTTP declarations were not bound to CDP requests: "
        f"{unbound_network_requests}",
    )
    expected_responses = Counter(_expected_response_key(item) for item in selected)
    expected_console = Counter(_expected_console_key(item) for item in selected)
    _require(expected_responses, f"no controlled HTTP errors were declared: {expectation_ids}")
    completed_responses: Counter[tuple[object, ...]] = Counter()
    observed_console: Counter[tuple[object, ...]] = Counter()
    while True:
        completed_responses = Counter(
            _expected_response_key(
                {
                    "expectation_id": item["expectation_id"],
                    "request_id": item["request_id"],
                    "network_request_id": item["network_request_id"],
                    "label": item["label"],
                    "page_id": item["page_id"],
                    "page_url": item["page_url"],
                    "source_url": item["source_url"],
                    "status": item["status"],
                    "method": item["method"],
                    "resource_type": item["resource_type"],
                    "navigation_request": item["navigation_request"],
                }
            )
            for item in console_errors.response_evidence
            if item["expectation_id"] in expectation_ids
            and item["finished"] is True
            and item["failure"] is None
        )
        selected_bases = {_console_base_key(item) for item in selected}
        active_same_base_expectations = [
            item
            for item in console_errors.expectations
            if item["request_id"] is not None
            and _console_base_key(item) in selected_bases
        ]
        observed_console, _console_failures = _reconcile_http_console_evidence(
            console_errors,
            active_same_base_expectations,
            include_unrelated=False,
        )
        if not (expected_responses - completed_responses) and not (
            expected_console - observed_console
        ):
            return
        if time.monotonic() >= deadline:
            break
        page.wait_for_timeout(10)
    _require(
        False,
        "controlled HTTP evidence did not settle: "
        f"missing_responses={list((expected_responses - completed_responses).elements())}, "
        f"missing_console={list((expected_console - observed_console).elements())}, "
        "response_evidence="
        f"{[item for item in console_errors.response_evidence if item['expectation_id'] in expectation_ids]}, "
        "console_evidence="
        f"{[item for item in console_errors.evidence if item.get('label') in {selected_item['label'] for selected_item in selected}]}, "
        "cdp_console_evidence="
        f"{[item for item in console_errors.cdp_console_evidence if item.get('label') in {selected_item['label'] for selected_item in selected}]}",
    )


def _request_identity(request) -> str:
    implementation = getattr(request, "_impl_obj", request)
    return str(getattr(implementation, "_guid", id(implementation)))


def _page_identity(page) -> str:
    implementation = getattr(page, "_impl_obj", page)
    return str(getattr(implementation, "_guid", id(implementation)))


def _header_value(headers: object, name: str) -> str:
    if not isinstance(headers, dict):
        return ""
    expected_name = name.casefold()
    for key, value in headers.items():
        if str(key).casefold() == expected_name:
            return str(value)
    return ""


def _is_product_browser_request(evidence: dict[str, object]) -> bool:
    return _is_allowed_http_url(str(evidence.get("source_url") or ""))


def _is_allowed_http_url(url: str) -> bool:
    parsed = urlparse(url)
    try:
        origin = (parsed.scheme, parsed.hostname, parsed.port)
    except ValueError:
        return False
    return (
        parsed.username is None
        and parsed.password is None
        and origin in ALLOWED_HTTP_ORIGINS
    )


def _is_allowed_websocket_url(url: str) -> bool:
    parsed = urlparse(url)
    try:
        origin = (parsed.scheme, parsed.hostname, parsed.port)
    except ValueError:
        return False
    return (
        parsed.username is None
        and parsed.password is None
        and origin in ALLOWED_WEBSOCKET_ORIGINS
    )


def _is_allowed_frontend_url(url: str) -> bool:
    parsed = urlparse(url)
    try:
        return (
            parsed.username is None
            and parsed.password is None
            and (parsed.scheme, parsed.hostname, parsed.port)
            == ("http", "127.0.0.1", 3000)
        )
    except ValueError:
        return False


def _network_url_key(
    url: str,
) -> tuple[str, str, int | None, str, str, str, str]:
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError:
        port = None
    return (
        parsed.scheme,
        parsed.hostname or "",
        port,
        parsed.path or "/",
        parsed.params,
        parsed.query,
        parsed.fragment,
    )


def _route_query_parts(query: str) -> tuple[str, ...]:
    return tuple(
        part
        for part in query.split("&")
        if part and unquote_plus(part.partition("=")[0]) != "_rsc"
    )


def _route_url_key(
    url: str,
) -> tuple[str, str, int | None, str, str, tuple[str, ...], str]:
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError:
        port = None
    return (
        parsed.scheme,
        parsed.hostname or "",
        port,
        parsed.path or "/",
        parsed.params,
        _route_query_parts(parsed.query),
        parsed.fragment,
    )


def _route_document_key(
    url: str,
) -> tuple[str, str, int | None, str, str, tuple[str, ...]]:
    return _route_url_key(url)[:-1]


def _static_chunk_matches_declared_route(
    source_url: str,
    expectation: dict[str, object],
) -> bool:
    source_path = unquote(urlparse(source_url).path)
    if not source_path.startswith("/_next/static/chunks/"):
        return False
    declared_routes = {
        str(expectation.get("request_page_url") or ""),
        str(expectation.get("destination_url") or ""),
        *(
            str(url)
            for url in expectation.get("cancelled_route_urls") or ()
        ),
    }
    return any(
        source_path in _next_route_exclusive_static_chunk_paths(route_url)
        for route_url in declared_routes
    )


def _is_valid_route_cache_precursor(
    evidence: dict[str, object],
    *,
    page_id: str,
    label: str,
    destination_url: str,
    declaration_sequence: int,
) -> bool:
    source_url = str(evidence.get("source_url") or "")
    start_sequence = evidence.get("start_sequence")
    response_sequence = evidence.get("response_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    status = evidence.get("response_status")
    return bool(
        evidence.get("page_id") == page_id
        and evidence.get("label") == label
        and _is_allowed_frontend_url(source_url)
        and _route_document_key(source_url) == _route_document_key(destination_url)
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") in {"fetch", "xhr"}
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("rsc_request") is True
        and isinstance(status, int)
        and 200 <= status < 300
        and evidence.get("response_url") == source_url
        and evidence.get("finished") is True
        and evidence.get("failure") is None
        and isinstance(start_sequence, int)
        and isinstance(response_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < response_sequence < terminal_sequence
        and terminal_sequence < declaration_sequence
    )


def _route_transition_cache_precursors(
    messages: ConsoleErrorLog,
    expectation: dict[str, object],
) -> tuple[tuple[str, dict[str, object]], ...] | None:
    request_ids = expectation.get("cache_precursor_request_ids")
    declaration_sequence = expectation.get("declaration_sequence")
    allow_cache = expectation.get("allow_complete_precursor_snapshot")
    if not (
        isinstance(allow_cache, bool)
        and isinstance(request_ids, tuple)
        and all(isinstance(request_id, str) for request_id in request_ids)
        and len(request_ids) == len(set(request_ids))
        and isinstance(declaration_sequence, int)
    ):
        return None
    if not allow_cache:
        return () if not request_ids else None
    results = []
    for request_id in request_ids:
        evidence = messages.request_evidence.get(request_id)
        if evidence is None or not _is_valid_route_cache_precursor(
            evidence,
            page_id=str(expectation.get("page_id") or ""),
            label=str(expectation.get("label") or ""),
            destination_url=str(expectation.get("destination_url") or ""),
            declaration_sequence=declaration_sequence,
        ):
            return None
        results.append((request_id, evidence))
    if tuple(
        sorted(
            results,
            key=lambda item: int(item[1].get("start_sequence") or -1),
        )
    ) != tuple(results):
        return None
    return tuple(results)


def _has_pre_start_route_navigation(
    messages: ConsoleErrorLog,
    expectation: dict[str, object],
    evidence: dict[str, object],
) -> bool:
    generation = evidence.get("navigation_generation")
    declaration = expectation.get("declaration_sequence")
    start = evidence.get("start_sequence")
    if not all(isinstance(value, int) for value in (generation, declaration, start)):
        return False
    endpoint_keys = {
        _route_document_key(str(expectation.get(key) or ""))
        for key in ("request_page_url", "destination_url")
    }
    return sum(
        event.get("generation") == generation
        and isinstance(event.get("sequence"), int)
        and declaration < event["sequence"] < start
        and _route_document_key(str(event.get("url") or "")) in endpoint_keys
        for event in messages._page_navigation_events.get(
            str(evidence.get("page_id") or ""), ()
        )
    ) == 1


def _route_transition_request_kind(
    messages: ConsoleErrorLog,
    expectation: dict[str, object],
    evidence: dict[str, object],
) -> str | None:
    declaration_sequence = expectation.get("declaration_sequence")
    start_sequence = evidence.get("start_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    allowed_page_keys = {
        _route_document_key(str(expectation.get("request_page_url") or "")),
        _route_document_key(str(expectation.get("destination_url") or "")),
    }
    if not (
        expectation.get("page_id") == evidence.get("page_id")
        and expectation.get("label") == evidence.get("label")
        and _is_allowed_frontend_url(str(evidence.get("page_url") or ""))
        and isinstance(declaration_sequence, int)
        and isinstance(start_sequence, int)
        and isinstance(terminal_sequence, int)
        and declaration_sequence < start_sequence < terminal_sequence
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") in {"fetch", "xhr", "script"}
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
    ):
        return None
    source_url = str(evidence.get("source_url") or "")
    if not _is_allowed_http_url(source_url):
        return None
    evidence_page_key = _route_document_key(
        str(evidence.get("page_url") or "")
    )
    page_id = str(evidence.get("page_id") or "")
    navigation_generation = evidence.get("navigation_generation")
    source_route_key = _route_document_key(source_url)
    destination_route_key = _route_document_key(
        str(expectation.get("destination_url") or "")
    )
    completion_sequence = expectation.get("completion_sequence")
    response_sequence = evidence.get("response_sequence")
    declaration_navigation_generation = expectation.get(
        "declaration_navigation_generation"
    )
    completion_navigation_generation = expectation.get(
        "completion_navigation_generation"
    )
    terminal_navigation_generation = evidence.get("terminal_navigation_generation")
    terminal_monotonic = evidence.get("terminal_monotonic")
    cache_precursors = _route_transition_cache_precursors(messages, expectation)
    if cache_precursors is None:
        return None
    cache_precursor_request_ids = tuple(
        request_id for request_id, _ in cache_precursors
    )
    cache_precursor_evidences = tuple(
        precursor for _, precursor in cache_precursors
    )
    evidence_request_ids = [
        request_id
        for request_id, candidate in messages.request_evidence.items()
        if candidate is evidence
    ]
    explicit_prefetch = (
        evidence.get("next_router_prefetch") is True
        or evidence.get("purpose") == "prefetch"
        or str(evidence.get("sec_purpose") or "").split(";", 1)[0]
        == "prefetch"
    )
    route_abort_with_precursors = False
    if (
        evidence.get("rsc_request") is True
        and not explicit_prefetch
        and source_route_key == destination_route_key
        and isinstance(completion_sequence, int)
        and len(evidence_request_ids) == 1
        and expectation.get("post_terminal_request_id") == evidence_request_ids[0]
    ):
        destination_siblings = [
            (request_id, candidate)
            for request_id, candidate in messages.request_evidence.items()
            if candidate is not evidence
            and candidate.get("page_id") == evidence.get("page_id")
            and candidate.get("label") == evidence.get("label")
            and isinstance(candidate.get("start_sequence"), int)
            and int(candidate["start_sequence"]) < completion_sequence
            and candidate.get("rsc_request") is True
            and candidate.get("method") == "GET"
            and candidate.get("resource_type") in {"fetch", "xhr"}
            and candidate.get("navigation_request") is False
            and candidate.get("main_frame") is True
            and not candidate.get("service_worker_url")
            and _route_document_key(str(candidate.get("source_url") or ""))
            == destination_route_key
            and not _is_framework_prefetch_cancellation(messages, candidate)
        ]
        if destination_siblings:
            if not (
                cache_precursor_request_ids
                and len(destination_siblings)
                == len(cache_precursor_request_ids)
                and {request_id for request_id, _ in destination_siblings}
                == set(cache_precursor_request_ids)
                and all(
                    any(
                        request_id == precursor_request_id
                        and candidate is precursor
                        for precursor_request_id, precursor in cache_precursors
                    )
                    for request_id, candidate in destination_siblings
                )
            ):
                return None
            if not (
                isinstance(evidence.get("response_status"), int)
                and 200 <= int(evidence["response_status"]) < 300
                and evidence.get("response_url") == source_url
                and isinstance(response_sequence, int)
                and start_sequence < response_sequence < terminal_sequence
            ):
                return None
            route_abort_with_precursors = True
        elif cache_precursor_request_ids:
            return None
    pre_start_navigation = _has_pre_start_route_navigation(messages, expectation, evidence)
    post_terminal_navigation_events = [
        event
        for event in messages._page_navigation_events.get(page_id, ())
        if isinstance(event.get("sequence"), int)
        and isinstance(completion_sequence, int)
        and terminal_sequence
        < int(event["sequence"])
        < completion_sequence
    ]
    post_terminal_destination_events = []
    for event in post_terminal_navigation_events:
        event_sequence = event.get("sequence")
        event_monotonic = event.get("monotonic")
        if not (
            expectation.get("allow_post_terminal_destination_commit") is True
            and len(evidence_request_ids) == 1
            and expectation.get("post_terminal_request_id")
            == evidence_request_ids[0]
            and evidence.get("rsc_request") is True
            and evidence.get("resource_type") in {"fetch", "xhr"}
            and not explicit_prefetch
            and evidence.get("response_status") == 200
            and evidence.get("response_url") == source_url
            and isinstance(response_sequence, int)
            and declaration_sequence
            < start_sequence
            < response_sequence
            < terminal_sequence
            and isinstance(navigation_generation, int)
            and declaration_navigation_generation == navigation_generation
            and terminal_navigation_generation == navigation_generation
            and completion_navigation_generation == navigation_generation + 1
            and event.get("generation") == navigation_generation + 1
            and isinstance(event_sequence, int)
            and isinstance(terminal_monotonic, (int, float))
            and isinstance(event_monotonic, (int, float))
            and 0
            <= float(event_monotonic) - float(terminal_monotonic)
            <= POST_TERMINAL_DESTINATION_COMMIT_MAX_SECONDS
            and _route_url_key(str(event.get("url") or ""))
            == _route_url_key(str(expectation.get("destination_url") or ""))
            and source_route_key == destination_route_key
        ):
            continue
        competing_declarations = [
            item
            for item in messages.route_transition_expectations
            if item is not expectation
            and item.get("page_id") == evidence.get("page_id")
            and item.get("label") == evidence.get("label")
            and isinstance(item.get("declaration_sequence"), int)
            and start_sequence
            < int(item["declaration_sequence"])
            < event_sequence
        ]
        competing_destination_requests = [
            candidate
            for candidate in messages.request_evidence.values()
            if candidate is not evidence
            and all(
                candidate is not precursor
                for precursor in cache_precursor_evidences
            )
            and candidate.get("page_id") == evidence.get("page_id")
            and candidate.get("label") == evidence.get("label")
            and isinstance(candidate.get("start_sequence"), int)
            and int(candidate["start_sequence"]) < event_sequence
            and candidate.get("rsc_request") is True
            and candidate.get("method") == "GET"
            and candidate.get("resource_type") in {"fetch", "xhr"}
            and candidate.get("navigation_request") is False
            and candidate.get("main_frame") is True
            and not candidate.get("service_worker_url")
            and _route_document_key(str(candidate.get("source_url") or ""))
            == destination_route_key
            and not _is_framework_prefetch_cancellation(messages, candidate)
        ]
        if not competing_declarations and not competing_destination_requests:
            post_terminal_destination_events.append(event)
    if (
        len(evidence_request_ids) == 1
        and expectation.get("post_terminal_request_id") == evidence_request_ids[0]
        and not (
            len(post_terminal_navigation_events) == 1
            and len(post_terminal_destination_events) == 1
        )
    ):
        return None
    # Playwright can briefly report a stale frame URL around a client route.
    # Accept that observation only with one exact endpoint event: either the
    # same-generation event preceded the request, or the next-generation
    # destination commit immediately followed the aborted destination RSC.
    if evidence_page_key not in allowed_page_keys and (
        int(pre_start_navigation)
        + int(
            len(post_terminal_navigation_events) == 1
            and len(post_terminal_destination_events) == 1
        )
        != 1
    ):
        return None
    parsed_source = urlparse(source_url)
    if parsed_source.port == 8000:
        if evidence.get("resource_type") not in {"fetch", "xhr"}:
            return None
        declared_read_keys = {
            _network_url_key(str(url))
            for url in expectation.get("cancelled_read_urls") or ()
        }
        return (
            "explicit_read"
            if _network_url_key(source_url) in declared_read_keys
            else None
        )
    if parsed_source.port != 3000:
        return None
    if evidence.get("rsc_request") is True:
        if evidence.get("resource_type") not in {"fetch", "xhr"}:
            return None
        source_route_key = _route_document_key(source_url)
        if explicit_prefetch:
            return (
                "speculative"
                if expectation.get("allow_speculative_cancellations") is True
                else None
            )
        declared_cancelled_route_keys = {
            _route_document_key(str(url))
            for url in expectation.get("cancelled_route_urls") or ()
        }
        if source_route_key in declared_cancelled_route_keys:
            return "cancelled_route"
        declared_route_keys = {
            _route_document_key(str(expectation.get("request_page_url") or "")),
            _route_document_key(str(expectation.get("destination_url") or "")),
        }
        if source_route_key not in declared_route_keys:
            return None
        return (
            "route_with_complete_precursor_snapshot"
            if route_abort_with_precursors
            else "route"
        )
    if (
        evidence.get("resource_type") == "script"
        and expectation.get("allow_speculative_cancellations") is True
        and _static_chunk_matches_declared_route(source_url, expectation)
    ):
        return "speculative"
    return None


def _completed_route_transition_for_request(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
    *,
    speculative: bool = False,
    explicit_read: bool = False,
    cancelled_route: bool = False,
) -> dict[str, object] | None:
    start_sequence = evidence.get("start_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    if not (
        isinstance(start_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < terminal_sequence
    ):
        return None
    request_ids = [
        request_id
        for request_id, candidate in messages.request_evidence.items()
        if candidate is evidence
    ]
    if len(request_ids) != 1:
        return None
    request_id = request_ids[0]
    _require(
        sum((speculative, explicit_read, cancelled_route)) <= 1,
        "route request classification selected conflicting request kinds",
    )
    if explicit_read:
        expected_kinds = {"explicit_read"}
    elif cancelled_route:
        expected_kinds = {"cancelled_route"}
    elif speculative:
        expected_kinds = {"speculative"}
    else:
        expected_kinds = {"route", "route_with_complete_precursor_snapshot"}
    candidates = []
    for expectation in messages.route_transition_expectations:
        declaration_sequence = expectation.get("declaration_sequence")
        completion_sequence = expectation.get("completion_sequence")
        if not (
            isinstance(declaration_sequence, int)
            and declaration_sequence < start_sequence
            and isinstance(completion_sequence, int)
            and terminal_sequence < completion_sequence
            and _route_url_key(str(expectation.get("completion_url") or ""))
            == _route_url_key(str(expectation.get("destination_url") or ""))
            and request_id in (expectation.get("bound_request_ids") or ())
            and _route_transition_request_kind(messages, expectation, evidence)
            in expected_kinds
        ):
            continue
        candidates.append(expectation)
    if not candidates:
        return None
    candidates.sort(key=lambda item: int(item["declaration_sequence"]), reverse=True)
    selected = candidates[0]
    later_declarations = [
        item
        for item in messages.route_transition_expectations
        if item.get("page_id") == evidence.get("page_id")
        and isinstance(item.get("declaration_sequence"), int)
        and int(selected["declaration_sequence"])
        < int(item["declaration_sequence"])
        < start_sequence
    ]
    return None if later_declarations else selected


def _has_intentional_page_close_lifecycle(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
) -> bool:
    page_id = evidence.get("page_id")
    start_sequence = evidence.get("start_sequence")
    response_sequence = evidence.get("response_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    close_intent_sequence = messages._page_close_intent_sequences.get(
        str(page_id)
    )
    if not (
        isinstance(page_id, str)
        and bool(page_id)
        and page_id in messages._closed_page_ids
        and isinstance(start_sequence, int)
        and isinstance(close_intent_sequence, int)
        and start_sequence < close_intent_sequence
        and response_sequence is None
    ):
        return False
    failure = evidence.get("failure")
    if failure == "net::ERR_ABORTED":
        return (
            isinstance(terminal_sequence, int)
            and close_intent_sequence < terminal_sequence
        )
    return (
        failure is None
        and evidence.get("finished") is not True
        and terminal_sequence is None
    )


def _is_explicit_next_prefetch_abort(evidence: dict[str, object]) -> bool:
    source_url = str(evidence.get("source_url") or "")
    parsed = urlparse(source_url)
    start_sequence = evidence.get("start_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    start_monotonic = evidence.get("start_monotonic")
    terminal_monotonic = evidence.get("terminal_monotonic")
    explicit_prefetch = (
        evidence.get("rsc_request") is True
        and (
            evidence.get("next_router_prefetch") is True
            or evidence.get("purpose") == "prefetch"
            or str(evidence.get("sec_purpose") or "").split(";", 1)[0]
            == "prefetch"
        )
    )
    return bool(
        explicit_prefetch
        and _is_allowed_frontend_url(source_url)
        and parsed.port == 3000
        and "_rsc" in parse_qs(parsed.query, keep_blank_values=True)
        and bool(evidence.get("label"))
        and bool(evidence.get("page_id"))
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") == "fetch"
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("response_status") is None
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
        and isinstance(start_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < terminal_sequence
        and isinstance(start_monotonic, float)
        and isinstance(terminal_monotonic, float)
        and 0 <= terminal_monotonic - start_monotonic <= 1.0
    )


def _is_framework_prefetch_cancellation(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
) -> bool:
    parsed = urlparse(str(evidence.get("source_url") or ""))
    status = evidence.get("response_status")
    failure = evidence.get("failure")
    explicit_prefetch = (
        evidence.get("rsc_request") is True
        and (
            evidence.get("next_router_prefetch") is True
            or evidence.get("purpose") == "prefetch"
            or str(evidence.get("sec_purpose") or "").split(";", 1)[0]
            == "prefetch"
        )
    )
    base_contract = (
        bool(evidence.get("label"))
        and _is_allowed_http_url(str(evidence.get("source_url") or ""))
        and parsed.port == 3000
        and "_rsc" in parse_qs(parsed.query, keep_blank_values=True)
        and explicit_prefetch
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") == "fetch"
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
    )
    if not base_contract:
        return False
    if status is None:
        return (
            _is_explicit_next_prefetch_abort(evidence)
        ) or (
            failure is None
            and _has_intentional_page_close_lifecycle(messages, evidence)
        )
    start_sequence = evidence.get("start_sequence")
    response_sequence = evidence.get("response_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    start_monotonic = evidence.get("start_monotonic")
    terminal_monotonic = evidence.get("terminal_monotonic")
    return (
        isinstance(status, int)
        and 200 <= status < 300
        and evidence.get("response_url") == evidence.get("source_url")
        and failure == "net::ERR_ABORTED"
        and evidence.get("finished") is not True
        and isinstance(start_sequence, int)
        and isinstance(response_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < response_sequence < terminal_sequence
        and isinstance(start_monotonic, float)
        and isinstance(terminal_monotonic, float)
        and 0 <= terminal_monotonic - start_monotonic <= 1.0
    )


def _framework_prefetch_cancellations(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    return [
        evidence
        for evidence in messages.request_evidence.values()
        if _is_product_browser_request(evidence)
        and _is_framework_prefetch_cancellation(messages, evidence)
    ]


def _is_route_transition_cancellation(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
) -> bool:
    source_url = str(evidence.get("source_url") or "")
    declared_rsc_transition = (
        evidence.get("rsc_request") is True
        and evidence.get("next_router_prefetch") is not True
        and _is_allowed_frontend_url(source_url)
        and _completed_route_transition_for_request(messages, evidence) is not None
    )
    status = evidence.get("response_status")
    start_sequence = evidence.get("start_sequence")
    response_sequence = evidence.get("response_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    response_lifecycle_valid = status is None or (
        isinstance(status, int)
        and 200 <= status < 300
        and evidence.get("response_url") == evidence.get("source_url")
        and isinstance(start_sequence, int)
        and isinstance(response_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < response_sequence < terminal_sequence
    )
    return (
        bool(evidence.get("label"))
        and bool(evidence.get("page_id"))
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") in {"fetch", "xhr"}
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
        and response_lifecycle_valid
        and declared_rsc_transition
    )


def _route_transition_cancellations(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    return [
        evidence
        for evidence in messages.request_evidence.values()
        if _is_product_browser_request(evidence)
        and _is_route_transition_cancellation(messages, evidence)
    ]


def _route_cancellations_with_complete_precursor_snapshot(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    results = []
    for evidence in messages.request_evidence.values():
        if not (
            _is_product_browser_request(evidence)
            and _is_route_transition_cancellation(messages, evidence)
        ):
            continue
        expectation = _completed_route_transition_for_request(messages, evidence)
        if (
            expectation is not None
            and _route_transition_request_kind(messages, expectation, evidence)
            == "route_with_complete_precursor_snapshot"
        ):
            results.append(evidence)
    return results


def _is_declared_cancelled_route_request(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
) -> bool:
    source_url = str(evidence.get("source_url") or "")
    status = evidence.get("response_status")
    start_sequence = evidence.get("start_sequence")
    response_sequence = evidence.get("response_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    response_lifecycle_valid = status is None or (
        isinstance(status, int)
        and 200 <= status < 300
        and evidence.get("response_url") == source_url
        and isinstance(start_sequence, int)
        and isinstance(response_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < response_sequence < terminal_sequence
    )
    return bool(
        bool(evidence.get("label"))
        and bool(evidence.get("page_id"))
        and evidence.get("rsc_request") is True
        and _is_allowed_frontend_url(source_url)
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") in {"fetch", "xhr"}
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
        and response_lifecycle_valid
        and _completed_route_transition_for_request(
            messages,
            evidence,
            cancelled_route=True,
        )
        is not None
    )


def _declared_cancelled_route_requests(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    return [
        evidence
        for evidence in messages.request_evidence.values()
        if _is_product_browser_request(evidence)
        and _is_declared_cancelled_route_request(messages, evidence)
    ]


def _is_declared_route_read_cancellation(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
) -> bool:
    return (
        bool(evidence.get("label"))
        and bool(evidence.get("page_id"))
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") in {"fetch", "xhr"}
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("response_status") is None
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
        and _completed_route_transition_for_request(
            messages,
            evidence,
            explicit_read=True,
        )
        is not None
    )


def _declared_route_read_cancellations(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    return [
        evidence
        for evidence in messages.request_evidence.values()
        if _is_product_browser_request(evidence)
        and _is_declared_route_read_cancellation(messages, evidence)
    ]


def _is_reconcilable_aborted_read(evidence: dict[str, object]) -> bool:
    start_sequence = evidence.get("start_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    return bool(
        isinstance(start_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < terminal_sequence
        and bool(evidence.get("label"))
        and bool(evidence.get("page_id"))
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") in {"fetch", "xhr"}
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("response_status") is None
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
    )


def _is_exact_successful_read_replacement(
    evidence: dict[str, object],
    candidate: dict[str, object],
) -> bool:
    start_sequence = evidence.get("start_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    candidate_start = candidate.get("start_sequence")
    candidate_response = candidate.get("response_sequence")
    candidate_terminal = candidate.get("terminal_sequence")
    candidate_status = candidate.get("response_status")
    return bool(
        isinstance(start_sequence, int)
        and isinstance(terminal_sequence, int)
        and isinstance(candidate_start, int)
        and start_sequence < candidate_start < terminal_sequence
        and candidate.get("page_id") == evidence.get("page_id")
        and candidate.get("page_url") == evidence.get("page_url")
        and candidate.get("frame_url_at_request")
        == evidence.get("frame_url_at_request")
        and candidate.get("navigation_generation")
        == evidence.get("navigation_generation")
        and candidate.get("source_url") == evidence.get("source_url")
        and candidate.get("method") == evidence.get("method")
        and candidate.get("resource_type") == evidence.get("resource_type")
        and candidate.get("navigation_request") is False
        and candidate.get("main_frame") is True
        and not candidate.get("service_worker_url")
        and isinstance(candidate_status, int)
        and 200 <= candidate_status < 400
        and isinstance(candidate_response, int)
        and isinstance(candidate_terminal, int)
        and candidate_start < candidate_response < candidate_terminal
        and candidate.get("response_url") == candidate.get("source_url")
        and candidate.get("finished") is True
        and candidate.get("failure") is None
    )


def _superseded_read_pairs(messages: ConsoleErrorLog) -> dict[str, str]:
    aborted = sorted(
        (
            (request_id, evidence)
            for request_id, evidence in messages.request_evidence.items()
            if _is_reconcilable_aborted_read(evidence)
        ),
        key=lambda item: (
            int(item[1]["start_sequence"]),
            int(item[1]["terminal_sequence"]),
            item[0],
        ),
    )
    successful = sorted(
        messages.request_evidence.items(),
        key=lambda item: (
            int(item[1].get("start_sequence") or -1),
            item[0],
        ),
    )
    used_replacements: set[str] = set()
    pairs: dict[str, str] = {}
    for request_id, evidence in aborted:
        for candidate_id, candidate in successful:
            if (
                candidate_id not in used_replacements
                and candidate_id != request_id
                and _is_exact_successful_read_replacement(evidence, candidate)
            ):
                pairs[request_id] = candidate_id
                used_replacements.add(candidate_id)
                break
    return pairs


def _is_superseded_successful_read(
    messages: ConsoleErrorLog,
    request_id: str,
    evidence: dict[str, object],
) -> bool:
    if not _is_reconcilable_aborted_read(evidence):
        return False
    return request_id in _superseded_read_pairs(messages)


def _superseded_successful_reads(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    return [
        evidence
        for request_id, evidence in messages.request_evidence.items()
        if _is_product_browser_request(evidence)
        and _is_superseded_successful_read(messages, request_id, evidence)
    ]


def _route_pattern_matches_path(pattern: str, path: str) -> bool:
    pattern_segments = [segment for segment in pattern.split("/") if segment]
    path_segments = [segment for segment in path.split("/") if segment]
    return len(pattern_segments) == len(path_segments) and all(
        pattern_segment.startswith("[") and pattern_segment.endswith("]")
        or pattern_segment == path_segment
        for pattern_segment, path_segment in zip(
            pattern_segments,
            path_segments,
            strict=True,
        )
    )


def _trusted_next_build_manifests_available() -> bool:
    if ACTIVE_FRONTEND_MODE != "start":
        return False
    build_id = FRONTEND_ROOT / ".next" / "BUILD_ID"
    try:
        build_identity = build_id.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return bool(build_identity) and all(
        path.is_file()
        for path in (
            FRONTEND_ROOT / ".next" / "app-path-routes-manifest.json",
            FRONTEND_ROOT / ".next" / "app-build-manifest.json",
        )
    )


def _next_route_static_chunk_paths(route_url: str) -> frozenset[str]:
    if not _trusted_next_build_manifests_available():
        return frozenset()
    try:
        app_routes = json.loads(
            (FRONTEND_ROOT / ".next" / "app-path-routes-manifest.json").read_text()
        )
        app_build = json.loads(
            (FRONTEND_ROOT / ".next" / "app-build-manifest.json").read_text()
        )
    except (OSError, json.JSONDecodeError):
        return frozenset()
    route_path = urlparse(route_url).path or "/"
    matching_app_paths = [
        app_path
        for app_path, pattern in app_routes.items()
        if isinstance(pattern, str)
        and _route_pattern_matches_path(pattern, route_path)
    ]
    pages = app_build.get("pages") if isinstance(app_build, dict) else None
    if not isinstance(pages, dict):
        return frozenset()
    return frozenset(
        f"/_next/{asset}"
        for app_path in matching_app_paths
        for asset in pages.get(app_path, ())
        if isinstance(asset, str) and asset.startswith("static/chunks/")
    )


def _next_route_exclusive_static_chunk_paths(route_url: str) -> frozenset[str]:
    if not _trusted_next_build_manifests_available():
        return frozenset()
    try:
        app_routes = json.loads(
            (FRONTEND_ROOT / ".next" / "app-path-routes-manifest.json").read_text()
        )
        app_build = json.loads(
            (FRONTEND_ROOT / ".next" / "app-build-manifest.json").read_text()
        )
    except (OSError, json.JSONDecodeError):
        return frozenset()
    route_path = urlparse(route_url).path or "/"
    matching_app_paths = {
        app_path
        for app_path, pattern in app_routes.items()
        if isinstance(pattern, str)
        and _route_pattern_matches_path(pattern, route_path)
    }
    pages = app_build.get("pages") if isinstance(app_build, dict) else None
    if not matching_app_paths or not isinstance(pages, dict):
        return frozenset()

    def chunks_for(app_paths: set[str]) -> set[str]:
        return {
            f"/_next/{asset}"
            for app_path in app_paths
            for asset in pages.get(app_path, ())
            if isinstance(asset, str) and asset.startswith("static/chunks/")
        }

    target_chunks = chunks_for(matching_app_paths)
    other_chunks = chunks_for(set(pages) - matching_app_paths)
    return frozenset(target_chunks - other_chunks)


def _static_chunk_prefetch_owner(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
) -> dict[str, object] | None:
    source_url = str(evidence.get("source_url") or "")
    parsed = urlparse(source_url)
    start_sequence = evidence.get("start_sequence")
    terminal_sequence = evidence.get("terminal_sequence")
    start_monotonic = evidence.get("start_monotonic")
    terminal_monotonic = evidence.get("terminal_monotonic")
    if not (
        _is_allowed_frontend_url(source_url)
        and parsed.path.startswith("/_next/static/chunks/")
        and bool(evidence.get("label"))
        and bool(evidence.get("page_id"))
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") == "script"
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("response_status") is None
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
        and isinstance(start_sequence, int)
        and isinstance(terminal_sequence, int)
        and start_sequence < terminal_sequence
        and isinstance(start_monotonic, float)
        and isinstance(terminal_monotonic, float)
    ):
        return None
    owners = [
        candidate
        for candidate in messages.request_evidence.values()
        if _is_explicit_next_prefetch_abort(candidate)
        and candidate.get("page_id") == evidence.get("page_id")
        and candidate.get("label") == evidence.get("label")
        and candidate.get("page_url") == evidence.get("page_url")
        and candidate.get("frame_url_at_request")
        == evidence.get("frame_url_at_request")
        and candidate.get("navigation_generation")
        == evidence.get("navigation_generation")
        and parsed.path
        in _next_route_exclusive_static_chunk_paths(
            str(candidate.get("source_url") or "")
        )
        and isinstance(candidate.get("start_sequence"), int)
        and isinstance(candidate.get("terminal_sequence"), int)
        and int(candidate["start_sequence"])
        < start_sequence
        < terminal_sequence
        < int(candidate["terminal_sequence"])
        and isinstance(candidate.get("start_monotonic"), float)
        and isinstance(candidate.get("terminal_monotonic"), float)
        and float(candidate["start_monotonic"])
        <= start_monotonic
        <= terminal_monotonic
        <= float(candidate["terminal_monotonic"])
    ]
    return owners[0] if len(owners) == 1 else None


def _is_next_static_chunk_cancellation(
    messages: ConsoleErrorLog,
    evidence: dict[str, object],
) -> bool:
    parsed = urlparse(str(evidence.get("source_url") or ""))
    return (
        bool(evidence.get("label"))
        and bool(evidence.get("page_id"))
        and _is_allowed_http_url(str(evidence.get("source_url") or ""))
        and parsed.port == 3000
        and parsed.path.startswith("/_next/static/chunks/")
        and evidence.get("method") == "GET"
        and evidence.get("resource_type") == "script"
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and evidence.get("response_status") is None
        and evidence.get("finished") is not True
        and evidence.get("failure") == "net::ERR_ABORTED"
        and (
            _has_intentional_page_close_lifecycle(messages, evidence)
            or _completed_route_transition_for_request(
                messages,
                evidence,
                speculative=True,
            )
            is not None
            or _static_chunk_prefetch_owner(messages, evidence) is not None
        )
    )


def _next_static_chunk_cancellations(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    return [
        evidence
        for evidence in messages.request_evidence.values()
        if _is_product_browser_request(evidence)
        and _is_next_static_chunk_cancellation(messages, evidence)
    ]


def _is_declared_successful_no_content_response(
    messages: ConsoleErrorLog,
    request_id: str,
    evidence: dict[str, object],
) -> bool:
    expectation = messages._no_content_expectation_for_request(request_id)
    return bool(
        expectation is not None
        and expectation["request_id"] == request_id
        and isinstance(expectation.get("declaration_sequence"), int)
        and isinstance(evidence.get("start_sequence"), int)
        and int(expectation["declaration_sequence"])
        < int(evidence["start_sequence"])
        and expectation["label"] == evidence.get("label")
        and expectation["page_id"] == evidence.get("page_id")
        and expectation["page_url"] == evidence.get("page_url")
        and expectation["source_url"] == evidence.get("source_url")
        and expectation["method"] == evidence.get("method")
        and expectation["response_status"] == evidence.get("response_status") == 204
        and expectation["response_url"]
        == evidence.get("response_url")
        == evidence.get("source_url")
        and expectation["finished"] == evidence.get("finished")
        and expectation["failure"] == evidence.get("failure")
        and evidence.get("resource_type") in {"fetch", "xhr"}
        and evidence.get("navigation_request") is False
        and evidence.get("main_frame") is True
        and not evidence.get("service_worker_url")
        and (
            evidence.get("finished") is True and evidence.get("failure") is None
            or evidence.get("finished") is False
            and evidence.get("failure") == "net::ERR_ABORTED"
        )
    )


def _successful_no_content_responses(
    messages: ConsoleErrorLog,
) -> list[dict[str, object]]:
    return [
        evidence
        for request_id, evidence in messages.request_evidence.items()
        if _is_product_browser_request(evidence)
        and _is_declared_successful_no_content_response(
            messages, request_id, evidence
        )
    ]


def _expected_http_console_text(status: int) -> str:
    reasons = {404: "Not Found", 503: "Service Unavailable"}
    _require(status in reasons, f"no exact console text registered for HTTP {status}")
    return (
        "Failed to load resource: the server responded with a status of "
        f"{status} ({reasons[status]})"
    )


def _capture_page_error(page_errors: list[str], label: str, page, error: Exception) -> None:
    stack = getattr(error, "stack", None) or str(error)
    page_errors.append(f"{label} [{page.url}]: {stack}")


def _focus_via_tab(page, locator, *, max_steps: int = 160) -> None:
    page.evaluate(
        """
        () => {
          const active = document.activeElement;
          if (active instanceof HTMLElement) {
            active.blur();
          }
        }
        """
    )
    for _ in range(max_steps):
        page.keyboard.press("Tab")
        if locator.evaluate("element => element === document.activeElement"):
            focus_state = locator.evaluate(
                """
                element => {
                  const style = getComputedStyle(element);
                  return {
                    focusVisible: element.matches(":focus-visible"),
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                  };
                }
                """
            )
            _require(
                focus_state["focusVisible"]
                and focus_state["outlineStyle"] != "none"
                and focus_state["outlineWidth"] != "0px",
                f"keyboard target lacks visible focus: {focus_state}",
            )
            return
    raise E2EFailure(f"keyboard target was not reachable within {max_steps} Tab presses")


def _wait_for_application_shell(page) -> None:
    from playwright.sync_api import expect

    expect(page.get_by_test_id("application-shell")).to_have_attribute(
        "data-hydrated",
        "true",
        timeout=30_000,
    )


def _verify_worker_network_surfaces_blocked(page) -> None:
    result = page.evaluate(
        """
        () => {
          const blocked = {};
          for (const name of ["Worker", "SharedWorker"]) {
            try {
              new globalThis[name]("data:text/javascript,");
              blocked[name] = false;
            } catch (error) {
              blocked[name] = String(error).includes(
                "Worker network surfaces are disabled in Product E2E"
              );
            }
          }
          return {
            marker: globalThis.__scientificSpacesWorkerNetworkBlocked === true,
            ...blocked,
          };
        }
        """
    )
    _require(
        result == {"marker": True, "Worker": True, "SharedWorker": True},
        f"worker network surfaces were not blocked: {result}",
    )


def _verify_ordinary_shell_route_focus(
    browser,
    *,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1440, "height": 640}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    page = context.new_page()
    _mark_expected_context_page(context, page)
    page.on(
        "console",
        lambda message: _capture_console_error(
            console_errors, message, label="shell-ordinary-route", page=page
        ),
    )
    if isinstance(console_errors, ConsoleErrorLog):
        console_errors.observe_http_errors(page, label="shell-ordinary-route")
    page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "shell-ordinary-route", page, error),
    )
    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        _wait_for_animation_frames(page, 5)
        _require(
            page.evaluate("document.activeElement === document.body"),
            "ordinary-route probe moved focus during initial hydration",
        )

        for navigation_id, source_pathname, pathname, heading in (
            ("library", "/", "/library", "Saved Learning Library"),
            ("session", "/", "/session", "Focused Study Session"),
            ("articles", "/", "/articles", "Article List"),
            ("references", "/", "/zotero", "Zotero Library"),
            ("graph", "/", "/graph", "Knowledge Graph"),
            ("tutor", "/", "/tutor", "AI Research Tutor"),
            ("dashboard", "/articles", "/", "Scientific Spaces AI Learning OS"),
        ):
            if isinstance(console_errors, ConsoleErrorLog):
                _wait_for_page_requests_to_settle(page, console_errors)
            page.goto(f"{FRONTEND_URL}{source_pathname}", wait_until="domcontentloaded")
            _wait_for_application_shell(page)
            previous_history_length = int(page.evaluate("history.length"))
            navigation = page.get_by_test_id(f"primary-nav-{navigation_id}")
            navigation.focus()
            ordinary_route_transition = _declare_expected_route_transition(
                page,
                destination_url=f"{FRONTEND_URL}{pathname}",
            )
            navigation.press("Enter")
            page.wait_for_function("path => location.pathname === path", arg=pathname)
            expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible(
                timeout=30_000
            )
            shell_main = page.get_by_test_id("shell-main-content")
            expect(shell_main).to_be_focused(timeout=30_000)
            _require_visible_focus(shell_main, f"desktop {navigation_id} route destination")
            _complete_expected_route_transition(page, ordinary_route_transition)
            _require(
                int(page.evaluate("history.length")) == previous_history_length + 1,
                f"desktop {navigation_id} route did not add exactly one history entry",
            )

        expect(
            page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
        ).to_be_visible(timeout=30_000)
        same_route_scroll = int(
            page.evaluate(
                """
                () => {
                  const maximum = document.documentElement.scrollHeight - innerHeight;
                  scrollTo(0, Math.min(240, maximum));
                  return scrollY;
                }
                """
            )
        )
        _require(same_route_scroll > 0, "same-route rail probe did not establish scroll state")
        same_route_history = int(page.evaluate("history.length"))
        same_route_url = page.url
        page.get_by_test_id("primary-nav-dashboard").press("Enter")
        shell_main = page.get_by_test_id("shell-main-content")
        expect(shell_main).to_be_focused(timeout=30_000)
        _require(
            int(page.evaluate("history.length")) == same_route_history
            and page.url == same_route_url
            and int(page.evaluate("scrollY")) == same_route_scroll,
            "same-route desktop rail activation changed history, URL, or scroll",
        )

        content_history = int(page.evaluate("history.length"))
        content_route_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles",
        )
        page.get_by_role("link", name="View all", exact=True).press("Enter")
        expect(page).to_have_url(re.compile(r"/articles$"), timeout=30_000)
        shell_main = page.get_by_test_id("shell-main-content")
        expect(shell_main).to_be_focused(timeout=30_000)
        _complete_expected_route_transition(page, content_route_transition)
        _require(
            int(page.evaluate("history.length")) == content_history + 1,
            "ordinary content navigation did not add exactly one history entry",
        )
        content_history_after_navigation = int(page.evaluate("history.length"))
        content_back_transition = _declare_expected_route_transition(
            page,
            destination_url=FRONTEND_URL,
        )
        page.go_back()
        expect(page).to_have_url(re.compile(r"/$"), timeout=30_000)
        expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
        _complete_expected_route_transition(page, content_back_transition)
        _require(
            int(page.evaluate("history.length")) == content_history_after_navigation,
            "ordinary browser Back changed history length",
        )
        content_forward_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles",
        )
        page.go_forward()
        expect(page).to_have_url(re.compile(r"/articles$"), timeout=30_000)
        expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
        _complete_expected_route_transition(page, content_forward_transition)
        _require(
            int(page.evaluate("history.length")) == content_history_after_navigation,
            "ordinary browser Forward changed history length",
        )

        dashboard_return_transition = _declare_expected_route_transition(
            page,
            destination_url=FRONTEND_URL,
        )
        page.get_by_test_id("primary-nav-dashboard").click()
        expect(page).to_have_url(re.compile(r"/$"), timeout=30_000)
        expect(
            page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
        ).to_be_visible(timeout=30_000)
        _complete_expected_route_transition(page, dashboard_return_transition)
        expect(page.get_by_test_id("dashboard-command-center")).to_have_attribute(
            "aria-busy", "false", timeout=30_000
        )
        _wait_for_animation_frames(page, 2)
        brand = page.get_by_role("link", name="Scientific Spaces AI Learning OS home", exact=True)
        page.evaluate(
            """
            () => {
              const maximum = document.documentElement.scrollHeight - innerHeight;
              scrollTo(0, Math.min(180, maximum));
            }
            """
        )
        _wait_for_animation_frames(page, 2)
        brand_scroll = int(page.evaluate("scrollY"))
        _require(brand_scroll > 0, "same-route brand probe did not establish scroll state")
        brand_history = int(page.evaluate("history.length"))
        brand_url = page.url
        brand.press("Enter")
        expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
        _require(
            int(page.evaluate("history.length")) == brand_history
            and page.url == brand_url
            and int(page.evaluate("scrollY")) == brand_scroll,
            "same-route brand activation changed history, URL, or scroll",
        )

        modified = page.get_by_test_id("primary-nav-tutor")
        modified.focus()
        current_url = page.url
        def observe_modified_page(opened) -> None:
            opened.on(
                "console",
                lambda message: _capture_console_error(
                    console_errors,
                    message,
                    label="shell-ordinary-modified-navigation",
                    page=opened,
                ),
            )
            opened.on(
                "pageerror",
                lambda error: _capture_page_error(
                    page_errors,
                    "shell-ordinary-modified-navigation",
                    opened,
                    error,
                ),
            )
            if isinstance(console_errors, ConsoleErrorLog):
                console_errors.observe_http_errors(
                    opened, label="shell-ordinary-modified-navigation"
                )

        context.on("page", observe_modified_page)
        try:
            with context.expect_page(timeout=10_000) as opened_page:
                modified.click(modifiers=["Control"])
            new_page = opened_page.value
            _mark_expected_popup(blocked_external, context, new_page)
        finally:
            context.remove_listener("page", observe_modified_page)
        new_page.wait_for_load_state("domcontentloaded")
        _wait_for_application_shell(new_page)
        _require(
            new_page.url.endswith("/tutor"),
            f"modified rail opened wrong URL: {new_page.url}",
        )
        _wait_for_page_requests_to_settle(new_page, console_errors)
        new_page.close()
        page.bring_to_front()
        _require(page.url == current_url, "modified rail activation changed the source page")
        expect(modified).to_be_focused()
    finally:
        context.close()


def _verify_reader_fragment_focus_ownership(
    browser,
    *,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN")
    context.add_init_script(
        f"""
        (() => {{
          const originalFetch = window.fetch.bind(window);
          window.__p3034DelayNextArticle = true;
          window.__p3034DelayNextReferenceList = true;
          window.fetch = (input, init) => {{
            const rawUrl = typeof input === 'string' ? input : input.url;
            const url = new URL(rawUrl, location.href);
            const localApi = ['127.0.0.1', 'localhost'].includes(url.hostname)
              && url.port === '8000';
            if (
              window.__p3034DelayNextArticle
              && localApi
              && url.pathname === '/articles/{CRB_ARTICLE_ID}'
            ) {{
              window.__p3034DelayNextArticle = false;
              return new Promise((resolve, reject) => {{
                setTimeout(() => originalFetch(input, init).then(resolve, reject), 2500);
              }});
            }}
            if (
              window.__p3034DelayNextReferenceList
              && localApi
              && url.pathname === '/v1.2/articles/{CRB_ARTICLE_ID}/references'
            ) {{
              window.__p3034DelayNextReferenceList = false;
              return new Promise((resolve, reject) => {{
                setTimeout(() => originalFetch(input, init).then(resolve, reject), 1200);
              }});
            }}
            return originalFetch(input, init);
          }};
        }})();
        """
    )
    _install_network_guard(context, blocked_external)
    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="reader-fragment-route-owner",
    )

    def isolate_reader_session(route) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-034-fragment-focus-probe",
                    "article_id": CRB_ARTICLE_ID,
                    "started_at": "2026-09-06T00:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        )

    page.route(re.compile(r".*/learning/sessions$"), isolate_reader_session)
    try:
        reference_payload = _api_json(
            context,
            "GET",
            f"/v1.2/articles/{CRB_ARTICLE_ID}/references?page=1&page_size=20",
        )
        reference_items = reference_payload.get("items")
        _require(
            isinstance(reference_items, list) and bool(reference_items),
            "structured-reference focus probe found no reference fixture",
        )
        structured_reference_id = str(reference_items[0]["reference_id"])
        structured_reference_url = (
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}"
            f"#structured-reference-{structured_reference_id}"
        )

        page.goto(structured_reference_url, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        _require(
            page.evaluate("document.activeElement === document.body"),
            "hard-loaded structured-reference hash moved focus during hydration",
        )
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        structured_reference_row = page.locator(
            f"#structured-reference-{structured_reference_id}"
        )
        expect(structured_reference_row).to_be_visible(timeout=30_000)
        _wait_for_animation_frames(page, 5)
        _require(
            page.evaluate("document.activeElement === document.body"),
            "late structured-reference data moved focus on a hard load",
        )

        page.goto(structured_reference_url, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        delayed_reference_search_trigger = page.get_by_test_id(
            "global-search-trigger-mobile"
        )
        delayed_reference_search_trigger.click()
        delayed_reference_dialog = page.get_by_test_id("global-search-dialog")
        delayed_reference_input = delayed_reference_dialog.get_by_label("Search library")
        expect(delayed_reference_input).to_be_focused()
        expect(page.locator(f"#structured-reference-{structured_reference_id}")).to_be_visible(
            timeout=30_000
        )
        _wait_for_animation_frames(page, 5)
        expect(delayed_reference_dialog).to_be_visible()
        expect(delayed_reference_input).to_be_focused()
        delayed_reference_dialog.get_by_role("button", name="Close", exact=True).click()
        expect(delayed_reference_dialog).to_have_count(0)

        page.close()
        page = _new_observed_page(
            context,
            console_errors,
            page_errors,
            label="reader-fragment-route-owner",
        )
        page.route(re.compile(r".*/learning/sessions$"), isolate_reader_session)
        page.goto(
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}#article-outline",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(page)
        _require(
            page.evaluate("document.activeElement === document.body"),
            "cold hashed Reader hydration moved focus before user interaction",
        )
        page.get_by_test_id("global-search-trigger-mobile").click()
        search_dialog = page.get_by_test_id("global-search-dialog")
        search_input = search_dialog.get_by_label("Search library")
        expect(search_input).to_be_focused()
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        _wait_for_animation_frames(page, 5)
        expect(search_dialog).to_be_visible()
        expect(search_input).to_be_focused()

        search_dialog.get_by_role("button", name="Close", exact=True).click()
        expect(search_dialog).to_have_count(0)
        back_to_articles_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles",
        )
        page.get_by_role("link", name="Back to articles", exact=True).click()
        expect(page).to_have_url(re.compile(r"/articles$"), timeout=30_000)
        expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
        _wait_for_page_requests_to_settle(page, console_errors)
        _complete_expected_route_transition(page, back_to_articles_transition)
        persistent_fragment_history_origin = page.get_by_test_id(
            "global-search-trigger-mobile"
        )
        fragment_history_length = int(page.evaluate("history.length"))
        page.evaluate("window.__p3034DelayNextArticle = true")
        page.evaluate(
            """
            () => {
              window.__p3034FragmentRouteFocusEvents = [];
              window.__p3034FragmentRouteFocusObserver = event => {
                if (event.target instanceof Element) {
                  window.__p3034FragmentRouteFocusEvents.push(
                    event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  );
                }
              };
              document.addEventListener(
                'focusin',
                window.__p3034FragmentRouteFocusObserver,
                true
              );
            }
            """
        )
        persistent_fragment_history_origin.evaluate(
            "element => { element.focus(); history.back(); }"
        )
        expect(page).to_have_url(re.compile(r"#article-outline$"), timeout=30_000)
        outline_target = page.locator("#article-outline")
        expect(outline_target).to_be_focused(timeout=30_000)
        _require_visible_focus(outline_target, "cross-route Reader hash history target")
        fragment_route_focus_events = page.evaluate(
            """
            () => {
              document.removeEventListener(
                'focusin',
                window.__p3034FragmentRouteFocusObserver,
                true
              );
              return window.__p3034FragmentRouteFocusEvents;
            }
            """
        )
        _require(
            "shell-main-content" not in fragment_route_focus_events,
            "Shell focused main before the cross-route Reader fragment owner: "
            f"{fragment_route_focus_events}",
        )
        _require(
            int(page.evaluate("history.length")) == fragment_history_length,
            "Reader hash cross-route Back changed history length",
        )

        page.goto(
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession#reading-tools",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        _wait_for_animation_frames(page, 5)
        tools_target = page.locator("#reading-tools")
        _require(
            page.evaluate("document.activeElement === document.body"),
            "hard-loaded guided Reader moved focus during initial hydration",
        )

        guided_base_reader_url = (
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession"
        )
        page.goto(guided_base_reader_url, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        guided_heading = page.get_by_role("heading", name=CRB_TITLE, exact=True)
        expect(guided_heading).to_be_visible(timeout=30_000)
        _wait_for_animation_frames(page, 5)
        _require(
            page.evaluate("document.activeElement === document.body"),
            "hard-loaded hashless guided Reader moved focus during hydration",
        )
        guided_history_length = int(page.evaluate("history.length"))
        page.get_by_role("link", name="Outline", exact=True).click()
        expect(page.locator("#article-outline")).to_be_focused(timeout=30_000)
        page.go_back()
        expect(page).to_have_url(guided_base_reader_url, timeout=30_000)
        expect(guided_heading).to_be_focused(timeout=30_000)
        _require_visible_focus(guided_heading, "hashless guided Reader history target")
        _require(
            int(page.evaluate("history.length")) == guided_history_length + 1,
            "hashless guided Reader Back changed history length",
        )

        base_reader_url = f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}"
        page.goto(base_reader_url, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        _wait_for_animation_frames(page, 5)
        _require(
            page.evaluate("document.activeElement === document.body"),
            "hard-loaded hashless Reader moved focus during initial hydration",
        )
        interrupted_fragment_trigger = page.get_by_test_id("global-search-trigger-mobile")
        page.get_by_role("link", name="Outline", exact=True).evaluate(
            """
            (element) => {
              element.click();
              window.dispatchEvent(new KeyboardEvent('keydown', {key: 'Tab'}));
              document.querySelector('[data-testid="global-search-trigger-mobile"]')?.focus();
            }
            """
        )
        _wait_for_animation_frames(page, 3)
        expect(interrupted_fragment_trigger).to_be_focused()
        expect(page.locator("#article-outline")).not_to_be_focused()
        page.goto(base_reader_url, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        _wait_for_animation_frames(page, 5)
        _require(
            page.evaluate("document.activeElement === document.body"),
            "fragment interruption reset moved focus during initial hydration",
        )
        hashless_history_length = int(page.evaluate("history.length"))
        page.get_by_role("link", name="Outline", exact=True).click()
        outline_target = page.locator("#article-outline")
        expect(outline_target).to_be_focused(timeout=30_000)
        hash_history_search_trigger = page.get_by_test_id("global-search-trigger-mobile")
        hash_history_search_trigger.click()
        hash_history_dialog = page.get_by_test_id("global-search-dialog")
        expect(hash_history_dialog.get_by_label("Search library")).to_be_focused()
        hash_history_dialog.get_by_role("button", name="Close", exact=True).evaluate(
            "element => { element.click(); history.back(); }"
        )
        expect(page).to_have_url(base_reader_url, timeout=30_000)
        article_target = page.locator("article#article-start")
        expect(article_target).to_be_focused(timeout=30_000)
        _require_visible_focus(article_target, "hashless Reader history target")
        expect(hash_history_search_trigger).not_to_be_focused()
        _require(
            int(page.evaluate("history.length")) == hashless_history_length + 1,
            "hashless Reader Back changed history length",
        )
        page.go_forward()
        expect(page).to_have_url(re.compile(r"#article-outline$"), timeout=30_000)
        expect(outline_target).to_be_focused(timeout=30_000)

        heading_history_length = int(page.evaluate("history.length"))
        heading_outline_link = page.get_by_test_id("article-outline").locator(
            'a[href^="#"]'
        ).first
        heading_href = heading_outline_link.get_attribute("href")
        _require(bool(heading_href), "Reader heading history probe found no outline target")
        heading_target_id = unquote((heading_href or "").lstrip("#"))
        heading_outline_link.click()
        heading_target = page.locator(f'[id="{heading_target_id}"]')
        expect(heading_target).to_be_focused(timeout=30_000)
        _require(
            page.evaluate(
                "targetId => decodeURIComponent(location.hash.slice(1)) === targetId",
                heading_target_id,
            ),
            "Reader outline navigation did not persist its exact heading hash",
        )
        page.get_by_role("link", name="Outline", exact=True).click()
        expect(outline_target).to_be_focused(timeout=30_000)
        page.go_back()
        _require(
            page.evaluate(
                "targetId => decodeURIComponent(location.hash.slice(1)) === targetId",
                heading_target_id,
            ),
            "Reader heading Back did not restore the exact hash",
        )
        expect(heading_target).to_be_focused(timeout=30_000)
        _require_visible_focus(heading_target, "Reader heading hash history target")
        page.go_forward()
        expect(page).to_have_url(re.compile(r"#article-outline$"), timeout=30_000)
        expect(outline_target).to_be_focused(timeout=30_000)
        _require(
            int(page.evaluate("history.length")) == heading_history_length + 1,
            "Reader heading hash Back/Forward changed history length",
        )

        page.evaluate(
            """
            ([key, value]) => localStorage.setItem(key, value)
            """,
            [
                "scientific-spaces-study-session-v1",
                json.dumps(
                    {
                        "version": 1,
                        "active_article_id": CRB_ARTICLE_ID,
                        "updated_at": "2026-09-06T00:00:00.000Z",
                        "items": [
                            {
                                "article_id": CRB_ARTICLE_ID,
                                "title": CRB_TITLE,
                                "section_id": "reading-tools",
                                "added_at": "2026-09-06T00:00:00.000Z",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            ],
        )
        page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible(
            timeout=30_000
        )
        page.evaluate(
            """
            () => {
              window.__p3034GuidedReaderFocusEvents = [];
              window.__p3034GuidedReaderFocusObserver = event => {
                if (event.target instanceof Element) {
                  window.__p3034GuidedReaderFocusEvents.push(
                    event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  );
                }
              };
              document.addEventListener(
                'focusin',
                window.__p3034GuidedReaderFocusObserver,
                true
              );
            }
            """
        )
        page.get_by_role("link", name=CRB_TITLE, exact=True).click()
        expect(page).to_have_url(re.compile(r"#reading-tools$"), timeout=30_000)
        expect(tools_target).to_be_focused(timeout=30_000)
        _require_visible_focus(tools_target, "guided Reader hash route target")
        guided_focus_events = page.evaluate(
            """
            () => {
              document.removeEventListener(
                'focusin',
                window.__p3034GuidedReaderFocusObserver,
                true
              );
              return window.__p3034GuidedReaderFocusEvents;
            }
            """
        )
        _require(
            "shell-main-content" not in guided_focus_events,
            f"Shell focused main before the guided Reader target: {guided_focus_events}",
        )
        focused_scroll = int(page.evaluate("scrollY"))
        _require(focused_scroll > 0, "guided Reader target did not establish scroll state")
        page.mouse.wheel(0, -100_000)
        page.wait_for_timeout(250)
        user_scroll = int(page.evaluate("scrollY"))
        _require(user_scroll < focused_scroll, "Reader ignored user scroll away from fragment")
        page.wait_for_timeout(600)
        _require(
            int(page.evaluate("scrollY")) == user_scroll,
            "Reader fragment visibility guard overrode subsequent user scroll",
        )
        expect(tools_target).to_be_focused()

        page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        expect(page.get_by_role("link", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        page.get_by_role("link", name=CRB_TITLE, exact=True).click()
        expect(page).to_have_url(re.compile(r"#reading-tools$"), timeout=30_000)
        modal_trigger = page.get_by_test_id("global-search-trigger-mobile")
        modal_trigger.click()
        modal = page.get_by_test_id("global-search-dialog")
        modal_input = modal.get_by_label("Search library")
        expect(modal_input).to_be_focused()
        modal.get_by_role("button", name="Close", exact=True).click()
        expect(modal).to_have_count(0)
        expect(modal_trigger).to_be_focused()
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        _wait_for_animation_frames(page, 5)
        expect(modal_trigger).to_be_focused()
        expect(page.locator("#reading-tools")).not_to_be_focused()

        saved_section_link = page.get_by_test_id("article-outline").get_by_role(
            "link", name="数值检查", exact=True
        ).first
        saved_section_href = saved_section_link.get_attribute("href")
        _require(bool(saved_section_href), "ordinary Reader probe found no saved section target")
        saved_section_id = unquote((saved_section_href or "").lstrip("#"))
        saved_section_label = saved_section_link.inner_text().strip()
        _require(
            "%" in (saved_section_href or "") and saved_section_label == "数值检查",
            f"ordinary Reader probe did not select an encoded Chinese heading: {saved_section_href}",
        )
        guided_heading_history_length = int(page.evaluate("history.length"))
        saved_section_link.click()
        guided_section_target = page.locator(f'[id="{saved_section_id}"]')
        expect(guided_section_target).to_be_focused(timeout=30_000)
        page.get_by_role("link", name="Reading tools", exact=True).click()
        expect(page.locator("#reading-tools")).to_be_focused(timeout=30_000)
        _start_zotero_focus_trace(page)
        page.go_back()
        page.wait_for_function(
            "sectionId => decodeURIComponent(location.hash.slice(1)) === sectionId",
            arg=saved_section_id,
            timeout=30_000,
        )
        _wait_for_animation_frames(page, 8)
        _assert_zotero_focus_continuity(
            page,
            "guided Reader arbitrary heading history",
            (f"heading:{saved_section_label}",),
            ("testid:shell-main-content",),
        )
        expect(guided_section_target).to_be_focused(timeout=30_000)
        _require_visible_focus(
            guided_section_target,
            "guided Reader arbitrary heading history target",
        )
        _require(
            int(page.evaluate("history.length")) == guided_heading_history_length + 1,
            "guided Reader heading history changed history length",
        )
        page.evaluate(
            """
            ([key, sectionId, sectionTitle]) => {
              const raw = localStorage.getItem(key);
              const snapshot = raw ? JSON.parse(raw) : null;
              if (!snapshot || !Array.isArray(snapshot.items) || !snapshot.items[0]) {
                throw new Error('guided Reader session fixture is unavailable');
              }
              snapshot.items[0] = {
                ...snapshot.items[0],
                section_id: sectionId,
                section_title: sectionTitle,
              };
              localStorage.setItem(key, JSON.stringify(snapshot));
            }
            """,
            [
                "scientific-spaces-study-session-v1",
                saved_section_id,
                saved_section_label,
            ],
        )
        page.get_by_role("link", name="Back to study session", exact=True).first.click()
        expect(page).to_have_url(re.compile(r"/session$"), timeout=30_000)
        expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible(
            timeout=30_000
        )
        session_saved_heading_link = page.get_by_role(
            "link", name=f"Continue current Article: {CRB_TITLE}", exact=True
        )
        expect(session_saved_heading_link).to_be_visible(timeout=30_000)
        session_saved_heading_link.click()
        page.wait_for_function(
            "sectionId => decodeURIComponent(location.hash.slice(1)) === sectionId",
            arg=saved_section_id,
            timeout=30_000,
        )
        expect(guided_heading).to_be_focused(timeout=30_000)
        _require_visible_focus(guided_heading, "guided Reader saved-heading route target")
        session_completion_action = page.get_by_test_id(
            "focused-session-completion"
        ).locator("button:not([disabled])").first
        page.keyboard.press("Tab")
        expect(session_completion_action).to_be_focused()
        session_forward_history_length = int(page.evaluate("history.length"))
        page.go_back()
        expect(page).to_have_url(re.compile(r"/session$"), timeout=30_000)
        expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible(
            timeout=30_000
        )
        session_forward_origin = page.get_by_role(
            "link", name=f"Continue current Article: {CRB_TITLE}", exact=True
        )
        session_forward_origin.focus()
        expect(session_forward_origin).to_be_focused()
        _start_zotero_focus_trace(page)
        page.go_forward()
        page.wait_for_function(
            "sectionId => decodeURIComponent(location.hash.slice(1)) === sectionId",
            arg=saved_section_id,
            timeout=30_000,
        )
        expect(guided_heading).to_be_focused(timeout=30_000)
        _require_visible_focus(guided_heading, "guided Reader saved-heading Forward target")
        _assert_zotero_focus_continuity(
            page,
            "guided Reader saved-heading Forward",
            (f"heading:{CRB_TITLE}",),
            ("testid:shell-main-content",),
        )
        page.keyboard.press("Tab")
        expect(session_completion_action).to_be_focused()
        _require(
            int(page.evaluate("history.length")) == session_forward_history_length,
            "guided Reader saved-heading Back/Forward changed history length",
        )
        guided_unmanaged_history_length = int(page.evaluate("history.length"))
        page.get_by_role("link", name="Reading tools", exact=True).click()
        expect(page.locator("#reading-tools")).to_be_focused(timeout=30_000)
        _start_zotero_focus_trace(page)
        page.go_back()
        page.wait_for_function(
            "sectionId => decodeURIComponent(location.hash.slice(1)) === sectionId",
            arg=saved_section_id,
            timeout=30_000,
        )
        expect(guided_section_target).to_be_focused(timeout=30_000)
        page.wait_for_function(
            """
            sectionId => {
              const target = document.getElementById(sectionId);
              if (!target) return false;
              const top = target.getBoundingClientRect().top;
              return top >= -8 && top <= Math.min(220, window.innerHeight * 0.3);
            }
            """,
            arg=saved_section_id,
            timeout=30_000,
        )
        _assert_zotero_focus_continuity(
            page,
            "guided Reader unmanaged heading history",
            (f"heading:{saved_section_label}",),
            ("testid:shell-main-content",),
        )
        _require_visible_focus(
            guided_section_target,
            "guided Reader unmanaged heading history target",
        )
        _require(
            int(page.evaluate("history.length")) == guided_unmanaged_history_length + 1,
            "guided Reader unmanaged heading Back changed history length",
        )
        page.evaluate(
            """
            ([articleId, title, sectionId, sectionTitle]) => {
              localStorage.setItem(
                'scientific-spaces-reading-history-v1',
                JSON.stringify([{
                  id: articleId,
                  title,
                  url: 'https://spaces.ac.cn/archives/11787',
                  last_read_at: '2026-09-06T00:00:00.000Z',
                }])
              );
              localStorage.setItem(
                'scientific-spaces-reader-progress-v1',
                JSON.stringify({
                  version: 1,
                  items: [{
                    article_id: articleId,
                    section_id: sectionId,
                    section_title: sectionTitle,
                    progress: 90,
                    updated_at: '2026-09-06T00:00:00.000Z',
                  }],
                })
              );
            }
            """,
            [CRB_ARTICLE_ID, CRB_TITLE, saved_section_id, saved_section_label],
        )

        learning_state_list_pattern = re.compile(r".*/learning/state$")

        def provide_incomplete_learning_states(route) -> None:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"items": [], "total": 0}),
            )

        page.route(learning_state_list_pattern, provide_incomplete_learning_states)
        page.goto(FRONTEND_URL, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        continue_crb = page.get_by_role(
            "link", name=f"Continue learning {CRB_TITLE}", exact=True
        )
        expect(continue_crb).to_be_visible(timeout=30_000)
        continue_href = str(continue_crb.get_attribute("href") or "")
        _require(
            continue_href.startswith(f"/articles/{CRB_ARTICLE_ID}#"),
            f"ordinary Reader resume link lost its explicit heading hash: {continue_href}",
        )
        continue_crb.focus()
        continue_history_length = int(page.evaluate("history.length"))
        page.evaluate("window.__p3034DelayNextArticle = true")
        _start_zotero_focus_trace(page)
        continue_reader_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}{continue_href}",
        )
        continue_crb.press("Enter")
        page.wait_for_function(
            """
            ([articleId, sectionId]) => (
              location.pathname === `/articles/${articleId}`
              && decodeURIComponent(location.hash.slice(1)) === sectionId
            )
            """,
            arg=[CRB_ARTICLE_ID, saved_section_id],
            timeout=30_000,
        )
        cross_route_heading_target = page.locator(f'[id="{saved_section_id}"]')
        expect(cross_route_heading_target).to_be_focused(timeout=30_000)
        _require_visible_focus(
            cross_route_heading_target,
            "ordinary cross-route Reader heading hash target",
        )
        _assert_zotero_focus_continuity(
            page,
            "ordinary cross-route Reader heading hash",
            (f"heading:{saved_section_label}",),
            ("testid:shell-main-content",),
        )
        _complete_expected_route_transition(page, continue_reader_transition)
        _require(
            int(page.evaluate("history.length")) == continue_history_length + 1,
            "ordinary Reader heading hash navigation did not add exactly one history entry",
        )
        page.unroute(learning_state_list_pattern, provide_incomplete_learning_states)

        page.goto(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(page)
        attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
        expect(attention_heading).to_be_visible(timeout=30_000)
        recent_section = page.locator("section").filter(
            has=page.get_by_role("heading", name="Recent Reading", exact=True)
        )
        recent_crb = recent_section.get_by_role(
            "link", name=re.compile(rf"^{re.escape(CRB_TITLE)}")
        )
        expect(recent_crb).to_be_visible(timeout=30_000)
        recent_crb.focus()
        expect(recent_crb).to_be_focused()
        ordinary_reader_history_length = int(page.evaluate("history.length"))
        page.evaluate("window.__p3034DelayNextArticle = true")
        _start_zotero_focus_trace(page)
        first_recent_reader_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
        )
        recent_crb.press("Enter")
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(CRB_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        ordinary_reader_main = page.get_by_test_id("shell-main-content")
        expect(ordinary_reader_main).to_be_focused(timeout=2_000)
        expect(page.get_by_text("Loading article", exact=True)).to_be_visible(timeout=5_000)
        page.mouse.wheel(0, 1)
        crb_heading = page.get_by_role("heading", name=CRB_TITLE, exact=True)
        expect(crb_heading).to_be_visible(timeout=30_000)
        saved_route_target = page.locator(f'[id="{saved_section_id}"]')
        _wait_for_animation_frames(page, 5)
        expect(ordinary_reader_main).to_be_focused()
        expect(saved_route_target).not_to_be_focused()
        _assert_zotero_focus_continuity(
            page,
            "interaction-canceled ordinary delayed Article navigation",
            ("testid:shell-main-content",),
        )
        _complete_expected_route_transition(page, first_recent_reader_transition)

        first_recent_back_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        )
        page.go_back()
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(ATTENTION_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        expect(page.locator("article#article-start")).to_be_focused(timeout=30_000)
        _complete_expected_route_transition(page, first_recent_back_transition)
        page.evaluate("window.__p3034DelayNextArticle = true")
        _start_zotero_focus_trace(page)
        restored_recent_reader_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
        )
        recent_crb.press("Enter")
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(CRB_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        expect(ordinary_reader_main).to_be_focused(timeout=2_000)
        expect(crb_heading).to_be_visible(timeout=30_000)
        expect(saved_route_target).to_be_focused(timeout=30_000)
        _require_visible_focus(saved_route_target, "ordinary delayed Reader saved section")
        _assert_zotero_focus_continuity(
            page,
            "ordinary delayed Article-to-Article navigation",
            ("testid:shell-main-content", f"heading:{saved_section_label}"),
        )
        _complete_expected_route_transition(page, restored_recent_reader_transition)
        page.wait_for_timeout(500)
        restored_position = page.evaluate(
            """
            articleId => {
              const raw = localStorage.getItem('scientific-spaces-reader-progress-v1');
              const parsed = raw ? JSON.parse(raw) : null;
              return parsed?.items?.find(item => item.article_id === articleId) ?? null;
            }
            """,
            CRB_ARTICLE_ID,
        )
        _require(
            restored_position
            and restored_position.get("section_id") == saved_section_id
            and restored_position.get("progress", 0) > 0,
            f"ordinary Reader route lost saved progress: {restored_position}",
        )
        _require(
            int(page.evaluate("scrollY")) > 0,
            "ordinary Reader route did not restore its saved section position",
        )
        _require(
            int(page.evaluate("history.length")) == ordinary_reader_history_length + 1,
            "ordinary Article-to-Article navigation did not add exactly one history entry",
        )
        ordinary_reader_back_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        )
        page.go_back()
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(ATTENTION_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        attention_target = page.locator("article#article-start")
        expect(attention_target).to_be_focused(timeout=30_000)
        _require_visible_focus(attention_target, "ordinary Reader Back target")
        _complete_expected_route_transition(page, ordinary_reader_back_transition)
        _require(
            int(page.evaluate("history.length")) == ordinary_reader_history_length + 1,
            "ordinary Article-to-Article Back changed history length",
        )
        ordinary_reader_forward_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
        )
        page.go_forward()
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(CRB_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        crb_target = page.locator("article#article-start")
        expect(crb_target).to_be_focused(timeout=30_000)
        _require_visible_focus(crb_target, "ordinary Reader Forward target")
        _complete_expected_route_transition(page, ordinary_reader_forward_transition)

        graph_query_return = "/graph?q=CRB"
        graph_query_reader = (
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?"
            + urlencode({"from": graph_query_return})
        )
        page.goto(graph_query_reader, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        query_graph_return = page.get_by_role("link", name="Return to graph", exact=True).first
        expect(query_graph_return).to_have_attribute("href", graph_query_return)
        query_graph_return.focus()
        expect(query_graph_return).to_be_focused()
        _start_zotero_focus_trace(page)
        query_graph_return_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}{graph_query_return}",
        )
        query_graph_return.press("Enter")
        page.wait_for_function(
            "expected => location.pathname + location.search === expected",
            arg=graph_query_return,
            timeout=30_000,
        )
        graph_query_main = page.get_by_test_id("shell-main-content")
        expect(graph_query_main).to_be_focused(timeout=5_000)
        _require_visible_focus(graph_query_main, "Graph query-only return main fallback")
        _assert_zotero_focus_continuity(
            page,
            "Graph query-only return",
            ("testid:shell-main-content",),
        )
        _wait_for_page_requests_to_settle(page, console_errors)
        _complete_expected_route_transition(page, query_graph_return_transition)

        page.goto(
            f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        _require(
            isinstance(console_errors, ConsoleErrorLog),
            "Reader failure probe requires structured HTTP evidence",
        )
        failure_article_expectations = _declare_expected_http_errors(
            console_errors,
            label="reader-fragment-route-owner",
            page_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
            source_url=f"{BROWSER_API_URL}/articles/{CRB_ARTICLE_ID}",
            count=2,
        )
        failure_article_requests = {"count": 0}
        failure_article_pattern = re.compile(
            rf".*/articles/{re.escape(CRB_ARTICLE_ID)}$"
        )

        def fulfill_delayed_article_failure(route) -> None:
            failure_article_requests["count"] += 1
            _fulfill_expected_http_error(
                route,
                console_errors=console_errors,
                page=page,
                expectation_ids=failure_article_expectations,
                body='{"detail":"intentional delayed Article failure"}',
            )

        page.route(failure_article_pattern, fulfill_delayed_article_failure, times=2)
        _install_fetch_response_gate(page, f"/articles/{CRB_ARTICLE_ID}")
        failure_recent_section = page.locator("section").filter(
            has=page.get_by_role("heading", name="Recent Reading", exact=True)
        )
        failure_recent_link = failure_recent_section.get_by_role(
            "link", name=re.compile(rf"^{re.escape(CRB_TITLE)}")
        )
        first_failure_reader_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
        )
        failure_recent_link.press("Enter")
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(CRB_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        failure_main = page.get_by_test_id("shell-main-content")
        expect(failure_main).to_be_focused(timeout=2_000)
        expect(page.get_by_text("Loading article", exact=True)).to_be_visible(timeout=5_000)
        page.mouse.wheel(0, 1)
        _release_fetch_response_gate(page)
        expect(page.get_by_text("Article unavailable", exact=True)).to_be_visible(
            timeout=30_000
        )
        _complete_expected_route_transition(page, first_failure_reader_transition)
        expect(failure_main).to_be_focused()
        expect(page.get_by_role("button", name="Retry article", exact=True)).not_to_be_focused()
        _wait_for_declared_http_errors(
            page,
            console_errors,
            expectation_ids=failure_article_expectations[:1],
        )
        failure_reader_back_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}",
        )
        page.go_back()
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(ATTENTION_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        expect(page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        _complete_expected_route_transition(page, failure_reader_back_transition)

        second_failure_reader_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
        )
        failure_recent_link.press("Enter")
        expect(page).to_have_url(
            re.compile(rf"/articles/{re.escape(CRB_ARTICLE_ID)}$"),
            timeout=30_000,
        )
        _wait_for_fetch_response_gate_pending(page)
        newer_shell_focus = page.get_by_test_id("global-search-trigger-mobile")
        newer_shell_focus.click()
        failure_search_dialog = page.get_by_test_id("global-search-dialog")
        expect(failure_search_dialog.get_by_label("Search library")).to_be_focused()
        failure_search_dialog.get_by_role("button", name="Close", exact=True).click()
        expect(failure_search_dialog).to_have_count(0)
        expect(newer_shell_focus).to_be_focused()
        _release_fetch_response_gate(page)
        expect(page.get_by_text("Article unavailable", exact=True)).to_be_visible(
            timeout=30_000
        )
        _complete_expected_route_transition(page, second_failure_reader_transition)
        expect(newer_shell_focus).to_be_focused()
        expect(page.get_by_role("button", name="Retry article", exact=True)).not_to_be_focused()
        _wait_for_declared_http_errors(
            page,
            console_errors,
            expectation_ids=failure_article_expectations,
        )
        _require(
            failure_article_requests["count"] == 2,
            "Article failure fixture did not intercept exactly two requests",
        )
        _restore_fetch_response_gate(page)
        page.unroute(failure_article_pattern, fulfill_delayed_article_failure)
    finally:
        context.close()


def _verify_shell_reader_focus_ownership(
    browser,
    *,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    context.add_init_script(
        """
        window.IntersectionObserver = class {
          constructor() {}
          observe() {}
          unobserve() {}
          disconnect() {}
          takeRecords() { return []; }
        };
        """
    )
    page = context.new_page()
    _mark_expected_context_page(context, page)
    page.on(
        "console",
        lambda message: _capture_console_error(
            console_errors, message, label="shell-reader-owner", page=page
        ),
    )
    if isinstance(console_errors, ConsoleErrorLog):
        console_errors.observe_http_errors(page, label="shell-reader-owner")
    page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "shell-reader-owner", page, error),
    )
    delayed_requests: list[str] = []
    delayed_session_pattern = re.compile(r".*/session(?:\?.*)?$")

    def delay_session(route) -> None:
        if "_rsc=" in route.request.url:
            delayed_requests.append(route.request.url)
            time.sleep(2.5)
        route.continue_()

    page.route(delayed_session_pattern, delay_session)
    page.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-030-reader-owner-probe",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-09-05T01:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    try:
        page.goto(
            f"{FRONTEND_URL}/graph?node_id=concept%3Aattention&q=Attention",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
            timeout=30_000
        )
        graph_article_link = page.get_by_role("link", name="Open article", exact=True).first
        expect(graph_article_link).to_be_visible(timeout=30_000)
        graph_article_href = str(graph_article_link.get_attribute("href") or "")
        _require(
            graph_article_href.startswith(f"/articles/{ATTENTION_ARTICLE_ID}")
            and "from=" in graph_article_href,
            f"Graph Reader ownership probe found an invalid Article href: {graph_article_href}",
        )
        graph_article_link.evaluate(
            "element => element.setAttribute('data-p3030-reader-race-link', 'true')"
        )
        reader_route_anchor = console_errors._event_sequence
        reader_route_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}{graph_article_href}",
        )

        page.get_by_test_id("global-search-trigger-desktop").click()
        dialog = page.get_by_test_id("global-search-dialog")
        expect(dialog.get_by_label("Search library")).to_be_focused()
        page.evaluate(
            """
            () => {
              window.__p3030ReaderOwnerActions = [];
              window.__p3030ReaderOwnerFocusEvents = [];
              window.__p3030ReaderOwnerFocusObserver = event => {
                if (event.target instanceof Element) {
                  window.__p3030ReaderOwnerFocusEvents.push(
                    event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  );
                }
              };
              document.addEventListener('focusin', window.__p3030ReaderOwnerFocusObserver, true);
              setTimeout(() => {
                const articleLink = document.querySelector('[data-p3030-reader-race-link="true"]');
                window.__p3030ReaderOwnerActions.push(
                  articleLink ? 'reader' : 'missing-reader'
                );
                articleLink?.click();
              }, 150);
            }
            """
        )
        dialog.get_by_test_id("global-search-result-workspace").filter(
            has_text=re.compile(r"^Session")
        ).click()
        expect(page).to_have_url(re.compile(rf"/articles/{ATTENTION_ARTICLE_ID}\?"), timeout=30_000)
        reader_heading = page.locator("article#article-start > h1")
        expect(reader_heading).to_have_text(ATTENTION_TITLE, timeout=30_000)
        try:
            expect(reader_heading).to_be_focused(timeout=30_000)
        except AssertionError as exc:
            focus_diagnostics = page.evaluate(
                """
                () => ({
                  active: document.activeElement instanceof Element
                    ? document.activeElement.getAttribute('data-testid')
                      || document.activeElement.id
                      || document.activeElement.tagName
                    : null,
                  actions: window.__p3030ReaderOwnerActions,
                  focusEvents: window.__p3030ReaderOwnerFocusEvents,
                })
                """
            )
            raise AssertionError(
                f"Reader destination did not claim focus: {focus_diagnostics}"
            ) from exc
        _wait_for_animation_frames(page, 5)
        focus_evidence = page.evaluate(
            """
            () => {
              document.removeEventListener(
                'focusin',
                window.__p3030ReaderOwnerFocusObserver,
                true
              );
              return {
                actions: window.__p3030ReaderOwnerActions,
                focusEvents: window.__p3030ReaderOwnerFocusEvents,
              };
            }
            """
        )
        expect(reader_heading).to_be_focused()
        _require_visible_focus(reader_heading, "Shell-armed Reader heading")
        _require(
            focus_evidence["actions"] == ["reader"],
            f"Reader ownership action did not execute: {focus_evidence['actions']}",
        )
        _require(
            "shell-main-content" not in focus_evidence["focusEvents"],
            f"Shell stole Reader destination focus: {focus_evidence['focusEvents']}",
        )
        _require(
            len(delayed_requests) == 1 and "/session?" in delayed_requests[0],
            f"Reader ownership probe did not delay the Shell route: {delayed_requests}",
        )
        _wait_for_exact_route_request_to_finish(
            page,
            console_errors,
            source_url=f"{FRONTEND_URL}{graph_article_href}",
            after_sequence=reader_route_anchor,
            expect_prefetch=False,
            require_observed_request=True,
            allow_response_backed_route_abort=True,
            cache_precursor_expectation_id=reader_route_transition,
        )
        _complete_expected_route_transition(page, reader_route_transition)

        page.goto(FRONTEND_URL, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        delayed_requests.clear()
        dashboard_articles = page.get_by_role("link", name="View all", exact=True)
        dashboard_articles.evaluate(
            "element => element.setAttribute('data-p3034-ordinary-race-link', 'true')"
        )
        ordinary_supersession_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/articles",
        )
        page.get_by_test_id("global-search-trigger-desktop").click()
        dialog = page.get_by_test_id("global-search-dialog")
        expect(dialog.get_by_label("Search library")).to_be_focused()
        page.evaluate(
            """
            () => {
              setTimeout(() => {
                document.querySelector('[data-p3034-ordinary-race-link="true"]')?.click();
              }, 150);
            }
            """
        )
        dialog.get_by_test_id("global-search-result-workspace").filter(
            has_text=re.compile(r"^Session")
        ).click()
        expect(page).to_have_url(re.compile(r"/articles$"), timeout=30_000)
        shell_main = page.get_by_test_id("shell-main-content")
        expect(shell_main).to_be_focused(timeout=30_000)
        _require_visible_focus(shell_main, "superseding ordinary route destination")
        _wait_for_animation_frames(page, 5)
        expect(page).to_have_url(re.compile(r"/articles$"))
        expect(shell_main).to_be_focused()
        _require(
            len(delayed_requests) == 1 and "/session?" in delayed_requests[0],
            f"ordinary supersession probe did not delay the Shell route: {delayed_requests}",
        )
        _wait_for_page_requests_to_settle(page, console_errors)
        _complete_expected_route_transition(
            page,
            ordinary_supersession_transition,
        )
    finally:
        page.unroute(delayed_session_pattern, delay_session)
        context.close()


def _verify_overlapping_shell_route_supersession(
    browser,
    *,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    context.add_init_script(
        """
        window.IntersectionObserver = class {
          constructor() {}
          observe() {}
          unobserve() {}
          disconnect() {}
          takeRecords() { return []; }
        };
        """
    )
    page = context.new_page()
    _mark_expected_context_page(context, page)
    page.on(
        "console",
        lambda message: _capture_console_error(
            console_errors, message, label="shell-overlap", page=page
        ),
    )
    if isinstance(console_errors, ConsoleErrorLog):
        console_errors.observe_http_errors(page, label="shell-overlap")
    page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "shell-overlap", page, error),
    )
    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        page.evaluate("history.pushState(history.state, '', '/')")
        page.evaluate(
            """
            () => {
              if (typeof window.__p3036ShellSupersessionOriginalFetch === 'function') {
                throw new Error('P3-036 Shell supersession gate is already installed');
              }
              const originalFetch = window.fetch.bind(window);
              window.__p3036ShellSupersessionOriginalFetch = originalFetch;
              window.__p3036ShellSupersessionGate = {
                startedCount: 0,
                pendingCount: 0,
                networkCompletedCount: 0,
                networkFailure: null,
                requestUrl: null,
                requestMethod: null,
                requestNextRouterPrefetch: null,
                requestPurpose: null,
                requestSecPurpose: null,
                responseReady: false,
                responseStatus: null,
                responseUrl: null,
                responseRedirected: null,
                responseContentType: null,
                responseMediaType: null,
                responseBodyLength: 0,
                releasedCount: 0,
                deliveryResolvedCount: 0,
                downstreamBodyBytes: 0,
                downstreamBodySettled: false,
                downstreamBodyCancelled: false,
                downstreamCancelReason: null,
                release: null,
              };
              window.fetch = (...args) => {
                const input = args[0];
                const init = args[1] ?? {};
                const target = String(input instanceof Request ? input.url : input);
                const parsed = new URL(target, location.href);
                if (
                  parsed.origin !== location.origin
                  || parsed.pathname !== '/session'
                  || !parsed.searchParams.has('_rsc')
                ) {
                  return originalFetch(...args);
                }
                const requestMethod = String(
                  init.method ?? (input instanceof Request ? input.method : 'GET')
                ).toUpperCase();
                const requestHeaders = new Headers(
                  init.headers !== undefined
                    ? init.headers
                    : input instanceof Request
                      ? input.headers
                      : undefined
                );
                const nextRouterPrefetch = requestHeaders.get('next-router-prefetch') || '';
                const purpose = (requestHeaders.get('purpose') || '').toLowerCase();
                const secPurpose = (requestHeaders.get('sec-purpose') || '').toLowerCase();
                const explicitPrefetch = nextRouterPrefetch === '1'
                  || purpose === 'prefetch'
                  || secPurpose.split(';', 1)[0] === 'prefetch';
                if (
                  requestMethod !== 'GET'
                  || explicitPrefetch
                ) {
                  return originalFetch(...args);
                }
                const effectiveRequest = input instanceof Request
                  ? new Request(input, init)
                  : new Request(parsed.href, init);
                const gate = window.__p3036ShellSupersessionGate;
                gate.startedCount += 1;
                gate.requestUrl = effectiveRequest.url;
                gate.requestMethod = requestMethod;
                gate.requestNextRouterPrefetch = nextRouterPrefetch;
                gate.requestPurpose = purpose;
                gate.requestSecPurpose = secPurpose;
                const detachedSignal = new AbortController().signal;
                const detachedFetch = originalFetch(
                  new Request(effectiveRequest, { signal: detachedSignal })
                );
                gate.pendingCount += 1;
                return new Promise((resolve, reject) => {
                  detachedFetch.then(
                    async response => {
                      try {
                        const responseUrl = new URL(response.url);
                        const contentType = response.headers.get('content-type') || '';
                        const mediaType = contentType.split(';', 1)[0].trim().toLowerCase();
                        const responseBody = await response.clone().arrayBuffer();
                        if (
                          response.status !== 200
                          || response.redirected
                          || response.url !== effectiveRequest.url
                          || responseUrl.origin !== location.origin
                          || responseUrl.pathname !== '/session'
                          || !responseUrl.searchParams.has('_rsc')
                          || mediaType !== 'text/x-component'
                          || responseBody.byteLength === 0
                        ) {
                          throw new Error(
                            `invalid held Session response: status=${response.status} `
                            + `url=${response.url} contentType=${contentType} `
                            + `bodyLength=${responseBody.byteLength}`
                          );
                        }
                        gate.networkCompletedCount += 1;
                        gate.responseStatus = response.status;
                        gate.responseUrl = response.url;
                        gate.responseRedirected = response.redirected;
                        gate.responseContentType = contentType;
                        gate.responseMediaType = mediaType;
                        gate.responseBodyLength = responseBody.byteLength;
                        gate.responseReady = true;
                        gate.release = () => {
                          gate.release = null;
                          gate.pendingCount -= 1;
                          gate.releasedCount += 1;
                          const body = new Uint8Array(responseBody);
                          let emitted = false;
                          const trackedBody = new ReadableStream({
                            pull(controller) {
                              if (!emitted) {
                                emitted = true;
                                gate.downstreamBodyBytes = body.byteLength;
                                controller.enqueue(body);
                                return;
                              }
                              controller.close();
                              gate.downstreamBodySettled = true;
                            },
                            cancel(reason) {
                              gate.downstreamBodyCancelled = true;
                              gate.downstreamCancelReason = String(reason ?? 'cancelled');
                              gate.downstreamBodySettled = true;
                            },
                          });
                          const deliveredResponse = new Response(trackedBody, {
                            status: response.status,
                            statusText: response.statusText,
                            headers: response.headers,
                          });
                          Object.defineProperties(deliveredResponse, {
                            url: { configurable: true, value: response.url },
                            redirected: { configurable: true, value: response.redirected },
                            type: { configurable: true, value: response.type },
                          });
                          gate.deliveryResolvedCount += 1;
                          resolve(deliveredResponse);
                        };
                      } catch (error) {
                        gate.pendingCount -= 1;
                        gate.networkFailure = String(error);
                        reject(error);
                      }
                    },
                    error => {
                      gate.pendingCount -= 1;
                      gate.networkFailure = String(error);
                      reject(error);
                    },
                  );
                });
              };
            }
            """
        )
        page.get_by_test_id("global-search-trigger-desktop").click()
        dialog = page.get_by_test_id("global-search-dialog")
        expect(dialog.get_by_label("Search library")).to_be_focused()
        page.evaluate(
            """
            () => {
              window.__p3030OverlapFocusBehindModal = [];
              window.__p3030OverlapFocusObserver = event => {
                const activeDialog = document.querySelector('[data-testid="global-search-dialog"]');
                if (activeDialog && event.target instanceof Node && !activeDialog.contains(event.target)) {
                  window.__p3030OverlapFocusBehindModal.push(
                    event.target instanceof Element
                      ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                      : 'non-element'
                  );
                }
              };
              document.addEventListener('focusin', window.__p3030OverlapFocusObserver, true);
            }
            """
        )
        dialog.get_by_test_id("global-search-result-workspace").filter(
            has_text=re.compile(r"^Session")
        ).click()
        page.wait_for_function(
            """
            () => {
              const gate = window.__p3036ShellSupersessionGate;
              return gate?.pendingCount === 1 && gate.responseReady === true
                && typeof gate.release === 'function';
            }
            """,
            timeout=30_000,
        )
        expect(page).to_have_url(
            re.compile(rf"^{re.escape(FRONTEND_URL)}/?$"),
        )
        page.get_by_test_id("global-search-trigger-desktop").click()
        reopened_dialog = page.get_by_test_id("global-search-dialog")
        expect(reopened_dialog.get_by_label("Search library")).to_be_focused()
        library_route_anchor = console_errors._event_sequence
        library_transition = _declare_expected_route_transition(
            page,
            destination_url=f"{FRONTEND_URL}/library",
        )
        reopened_dialog.get_by_test_id("global-search-result-workspace").filter(
            has_text=re.compile(r"^Saved")
        ).click()
        expect(page).to_have_url(re.compile(r"/library$"), timeout=30_000)
        library_main = page.get_by_test_id("shell-main-content")
        expect(library_main).to_be_focused(timeout=30_000)
        _wait_for_exact_route_request_to_finish(
            page,
            console_errors,
            source_url=f"{FRONTEND_URL}/library",
            after_sequence=library_route_anchor,
            expect_prefetch=False,
            require_observed_request=True,
            allow_response_backed_route_abort=True,
            cache_precursor_expectation_id=library_transition,
        )
        _complete_expected_route_transition(page, library_transition)
        root_transition = _declare_expected_route_transition(
            page,
            destination_url=FRONTEND_URL,
        )
        page.go_back()
        expect(page).to_have_url(
            re.compile(rf"^{re.escape(FRONTEND_URL)}/?$"),
            timeout=30_000,
        )
        expect(page.get_by_test_id("global-search-dialog")).to_have_count(0)
        main = page.get_by_test_id("shell-main-content")
        expect(main).to_be_focused(timeout=30_000)
        _wait_for_animation_frames(page, 5)
        expect(main).to_be_focused()
        _require_visible_focus(main, "overlapping superseded Shell route")
        post_release_navigation_anchor = console_errors._event_sequence
        release_state = page.evaluate(
            """
            () => {
              const gate = window.__p3036ShellSupersessionGate;
              if (typeof gate?.release !== 'function') return null;
              if (window.__p3036PostReleaseEvidence) {
                throw new Error('P3-036 post-release evidence is already installed');
              }
              const describeFocus = target => ({
                targetTestId: target instanceof Element
                  ? target.getAttribute('data-testid') || ''
                  : '',
                targetId: target instanceof Element ? target.id || '' : '',
                targetTag: target instanceof Element ? target.tagName : 'NON_ELEMENT',
                connected: target instanceof Node ? target.isConnected : false,
                url: location.href,
              });
              const postRelease = {
                initialUrl: location.href,
                initialFocus: describeFocus(document.activeElement),
                focusTransitions: [],
                focusLossTransitions: [],
                bodyFocusSnapshots: [],
                protectedFocusNodeRemoved: false,
                historyTransitions: [],
                originalPushState: history.pushState,
                originalReplaceState: history.replaceState,
                focusHandler: null,
                blurHandler: null,
                focusoutHandler: null,
                popstateHandler: null,
                hashchangeHandler: null,
                mutationObserver: null,
                protectedFocusNode: document.activeElement,
              };
              const recordHistory = kind => {
                postRelease.historyTransitions.push({ kind, url: location.href });
              };
              postRelease.focusHandler = event => {
                postRelease.focusTransitions.push(describeFocus(event.target));
              };
              const recordFocusLoss = (kind, event) => {
                postRelease.focusLossTransitions.push({
                  kind,
                  from: describeFocus(event.target),
                  active: describeFocus(document.activeElement),
                });
              };
              postRelease.blurHandler = event => recordFocusLoss('blur', event);
              postRelease.focusoutHandler = event => recordFocusLoss('focusout', event);
              postRelease.popstateHandler = () => recordHistory('popstate');
              postRelease.hashchangeHandler = () => recordHistory('hashchange');
              postRelease.mutationObserver = new MutationObserver(records => {
                for (const record of records) {
                  for (const removedNode of record.removedNodes) {
                    if (
                      removedNode === postRelease.protectedFocusNode
                      || (
                        removedNode instanceof Element
                        && removedNode.contains(postRelease.protectedFocusNode)
                      )
                    ) {
                      postRelease.protectedFocusNodeRemoved = true;
                    }
                  }
                }
                if (document.activeElement === document.body) {
                  postRelease.bodyFocusSnapshots.push({
                    kind: 'mutation',
                    url: location.href,
                  });
                }
              });
              history.pushState = function (...args) {
                const result = Reflect.apply(postRelease.originalPushState, this, args);
                recordHistory('pushState');
                return result;
              };
              history.replaceState = function (...args) {
                const result = Reflect.apply(postRelease.originalReplaceState, this, args);
                recordHistory('replaceState');
                return result;
              };
              document.addEventListener('focusin', postRelease.focusHandler, true);
              document.addEventListener('blur', postRelease.blurHandler, true);
              document.addEventListener('focusout', postRelease.focusoutHandler, true);
              addEventListener('popstate', postRelease.popstateHandler);
              addEventListener('hashchange', postRelease.hashchangeHandler);
              postRelease.mutationObserver.observe(document, {
                childList: true,
                subtree: true,
              });
              window.__p3036PostReleaseEvidence = postRelease;
              gate.release();
              return {
                startedCount: gate.startedCount,
                pendingCount: gate.pendingCount,
                networkCompletedCount: gate.networkCompletedCount,
                networkFailure: gate.networkFailure,
                requestUrl: gate.requestUrl,
                requestMethod: gate.requestMethod,
                requestNextRouterPrefetch: gate.requestNextRouterPrefetch,
                requestPurpose: gate.requestPurpose,
                requestSecPurpose: gate.requestSecPurpose,
                responseReady: gate.responseReady,
                responseStatus: gate.responseStatus,
                responseUrl: gate.responseUrl,
                responseRedirected: gate.responseRedirected,
                responseContentType: gate.responseContentType,
                responseMediaType: gate.responseMediaType,
                responseBodyLength: gate.responseBodyLength,
                releasedCount: gate.releasedCount,
                deliveryResolvedCount: gate.deliveryResolvedCount,
              };
            }
            """
        )
        _require(release_state is not None, "superseded Session response had no release gate")
        page.wait_for_function(
            """
            () => window.__p3036ShellSupersessionGate?.downstreamBodySettled === true
            """,
            timeout=30_000,
        )
        _wait_for_page_requests_to_settle(page, console_errors)
        _wait_for_animation_frames(page, 5)
        expect(page).to_have_url(re.compile(rf"^{re.escape(FRONTEND_URL)}/?$"))
        expect(main).to_be_focused()
        _require_visible_focus(
            main,
            "overlapping superseded Shell route after stale response settlement",
        )
        overlap_evidence = page.evaluate(
            """
            () => {
              document.removeEventListener('focusin', window.__p3030OverlapFocusObserver, true);
              const gate = window.__p3036ShellSupersessionGate;
              const postRelease = window.__p3036PostReleaseEvidence;
              document.removeEventListener('focusin', postRelease.focusHandler, true);
              document.removeEventListener('blur', postRelease.blurHandler, true);
              document.removeEventListener('focusout', postRelease.focusoutHandler, true);
              removeEventListener('popstate', postRelease.popstateHandler);
              removeEventListener('hashchange', postRelease.hashchangeHandler);
              postRelease.mutationObserver.disconnect();
              history.pushState = postRelease.originalPushState;
              history.replaceState = postRelease.originalReplaceState;
              return {
                focusBehindModal: window.__p3030OverlapFocusBehindModal,
                postRelease: {
                  initialUrl: postRelease.initialUrl,
                  initialFocus: postRelease.initialFocus,
                  focusTransitions: postRelease.focusTransitions,
                  focusLossTransitions: postRelease.focusLossTransitions,
                  bodyFocusSnapshots: postRelease.bodyFocusSnapshots,
                  protectedFocusNodeRemoved: postRelease.protectedFocusNodeRemoved,
                  historyTransitions: postRelease.historyTransitions,
                },
                gate: {
                  startedCount: gate.startedCount,
                  pendingCount: gate.pendingCount,
                  networkCompletedCount: gate.networkCompletedCount,
                  networkFailure: gate.networkFailure,
                  requestUrl: gate.requestUrl,
                  requestMethod: gate.requestMethod,
                  requestNextRouterPrefetch: gate.requestNextRouterPrefetch,
                  requestPurpose: gate.requestPurpose,
                  requestSecPurpose: gate.requestSecPurpose,
                  responseReady: gate.responseReady,
                  responseStatus: gate.responseStatus,
                  responseUrl: gate.responseUrl,
                  responseRedirected: gate.responseRedirected,
                  responseContentType: gate.responseContentType,
                  responseMediaType: gate.responseMediaType,
                  responseBodyLength: gate.responseBodyLength,
                  releasedCount: gate.releasedCount,
                  deliveryResolvedCount: gate.deliveryResolvedCount,
                  downstreamBodyBytes: gate.downstreamBodyBytes,
                  downstreamBodySettled: gate.downstreamBodySettled,
                  downstreamBodyCancelled: gate.downstreamBodyCancelled,
                  downstreamCancelReason: gate.downstreamCancelReason,
                },
              };
            }
            """
        )
        gate_evidence = overlap_evidence["gate"]
        _require(
            gate_evidence["startedCount"] == 1
            and gate_evidence["pendingCount"] == 0
            and gate_evidence["networkCompletedCount"] == 1
            and gate_evidence["networkFailure"] is None
            and gate_evidence["requestMethod"] == "GET"
            and gate_evidence["requestNextRouterPrefetch"] == ""
            and gate_evidence["requestPurpose"] != "prefetch"
            and str(gate_evidence["requestSecPurpose"]).split(";", 1)[0]
            != "prefetch"
            and gate_evidence["responseReady"] is True
            and gate_evidence["responseStatus"] == 200
            and gate_evidence["responseRedirected"] is False
            and gate_evidence["responseUrl"] == gate_evidence["requestUrl"]
            and _route_document_key(str(gate_evidence["requestUrl"]))
            == _route_document_key(f"{FRONTEND_URL}/session")
            and gate_evidence["responseMediaType"] == "text/x-component"
            and int(gate_evidence["responseBodyLength"]) > 0
            and gate_evidence["releasedCount"] == 1
            and gate_evidence["deliveryResolvedCount"] == 1
            and gate_evidence["downstreamBodySettled"] is True
            and (
                gate_evidence["downstreamBodyCancelled"] is True
                or int(gate_evidence["downstreamBodyBytes"])
                == int(gate_evidence["responseBodyLength"])
            ),
            f"overlapping Shell supersession gate diverged: {gate_evidence}",
        )
        _require(
            overlap_evidence["focusBehindModal"] == [],
            "overlapping Shell route focused behind a reopened modal: "
            f"{overlap_evidence['focusBehindModal']}",
        )
        root_url_key = _route_url_key(FRONTEND_URL)
        post_release_evidence = overlap_evidence["postRelease"]
        _require(
            _route_url_key(str(post_release_evidence["initialUrl"])) == root_url_key
            and post_release_evidence["initialFocus"]["targetTestId"]
            == "shell-main-content"
            and post_release_evidence["initialFocus"]["connected"] is True
            and post_release_evidence["focusLossTransitions"] == []
            and post_release_evidence["bodyFocusSnapshots"] == []
            and post_release_evidence["protectedFocusNodeRemoved"] is False
            and all(
                transition["targetTestId"] == "shell-main-content"
                and transition["connected"] is True
                and _route_url_key(str(transition["url"])) == root_url_key
                for transition in post_release_evidence["focusTransitions"]
            )
            and all(
                _route_url_key(str(transition["url"])) == root_url_key
                for transition in post_release_evidence["historyTransitions"]
            ),
            "stale Session response caused a transient post-release focus or history takeover: "
            f"{post_release_evidence}",
        )
        post_release_navigation_events = [
            event
            for event in console_errors._page_navigation_events.get(
                _page_identity(page),
                (),
            )
            if isinstance(event.get("sequence"), int)
            and int(event["sequence"]) > post_release_navigation_anchor
        ]
        _require(
            all(
                _route_url_key(str(event.get("url") or "")) == root_url_key
                for event in post_release_navigation_events
            ),
            "stale Session response caused a transient post-release navigation: "
            f"{post_release_navigation_events}",
        )
        _complete_expected_route_transition(page, root_transition)
        page.evaluate(
            """
            () => {
              window.fetch = window.__p3036ShellSupersessionOriginalFetch;
              delete window.__p3036ShellSupersessionOriginalFetch;
              delete window.__p3036ShellSupersessionGate;
              delete window.__p3036PostReleaseEvidence;
            }
            """
        )
    finally:
        context.close()


def _wait_for_animation_frames(page, count: int) -> None:
    page.evaluate(
        """
        frameCount => new Promise(resolve => {
          let remaining = Math.max(1, frameCount);
          const next = () => {
            remaining -= 1;
            if (remaining === 0) {
              resolve();
              return;
            }
            requestAnimationFrame(next);
          };
          requestAnimationFrame(next);
        })
        """,
        count,
    )


def _document_width(page) -> int:
    return int(
        page.evaluate(
            "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)"
        )
    )


def _wait_for_test_id_near_viewport_top(page, test_id: str, *, max_top: int = 200) -> None:
    page.wait_for_function(
        """
        ({ testId, maxTop }) => {
          const node = document.querySelector(`[data-testid="${testId}"]`);
          if (!(node instanceof HTMLElement)) return false;
          const box = node.getBoundingClientRect();
          return box.top < maxTop && box.bottom > 0;
        }
        """,
        arg={"testId": test_id, "maxTop": max_top},
        timeout=30_000,
    )


def _require_visible_focus(locator, label: str) -> None:
    from playwright.sync_api import expect

    expect(locator).to_be_in_viewport(timeout=5_000)
    focus_state = locator.evaluate(
        """
        node => {
          const style = getComputedStyle(node);
          const box = node.getBoundingClientRect();
          return {
            active: node === document.activeElement,
            boxShadow: style.boxShadow,
            bottom: box.bottom,
            left: box.left,
            outlineStyle: style.outlineStyle,
            outlineWidth: style.outlineWidth,
            right: box.right,
            top: box.top,
            viewportHeight: window.innerHeight,
            viewportWidth: window.innerWidth,
          };
        }
        """
    )
    _require(
        focus_state["active"]
        and (
            (
                focus_state["outlineStyle"] != "none"
                and focus_state["outlineWidth"] != "0px"
            )
            or focus_state["boxShadow"] != "none"
        ),
        f"{label} lacks a visible focus indicator: {focus_state}",
    )
    _require(
        focus_state["bottom"] > 0
        and focus_state["right"] > 0
        and focus_state["top"] < focus_state["viewportHeight"]
        and focus_state["left"] < focus_state["viewportWidth"],
        f"{label} is focused outside the viewport: {focus_state}",
    )


def _require_focus_in_viewport(locator, label: str) -> None:
    focus_state = locator.evaluate(
        """
        node => {
          const box = node.getBoundingClientRect();
          return {
            active: node === document.activeElement,
            top: box.top,
            right: box.right,
            bottom: box.bottom,
            left: box.left,
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
          };
        }
        """
    )
    _require(
        focus_state["active"]
        and focus_state["top"] >= 0
        and focus_state["left"] >= 0
        and focus_state["top"] < focus_state["viewportHeight"]
        and focus_state["left"] < focus_state["viewportWidth"],
        f"{label} starts outside the viewport: {focus_state}",
    )


def _install_fetch_response_gate(
    page,
    endpoint: str,
    *,
    method: str | None = None,
) -> None:
    page.evaluate(
        """
        ({ endpoint, method }) => {
          if (typeof window.__p3027OriginalFetch === "function") {
            throw new Error("P3-027 fetch response gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3027OriginalFetch = originalFetch;
          window.__p3027FetchGate = {
            endpoint,
            pendingCount: 0,
            completedCount: 0,
            release: null,
          };
          window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (target.endsWith(endpoint) && (!method || requestMethod === method)) {
              const gate = window.__p3027FetchGate;
              gate.pendingCount += 1;
              await new Promise((resolve) => {
                gate.release = resolve;
              });
              gate.release = null;
              gate.completedCount += 1;
            }
            return response;
          };
        }
        """,
        {"endpoint": endpoint, "method": method},
    )


def _wait_for_fetch_response_gate_pending(page) -> None:
    page.wait_for_function(
        """
        () => {
          const gate = window.__p3027FetchGate;
          return gate && gate.pendingCount > gate.completedCount
            && typeof gate.release === "function";
        }
        """,
        timeout=30_000,
    )


def _release_fetch_response_gate(page) -> None:
    _wait_for_fetch_response_gate_pending(page)
    expected_count = page.evaluate(
        """
        () => {
          const gate = window.__p3027FetchGate;
          const release = gate.release;
          gate.release = null;
          release();
          return gate.pendingCount;
        }
        """
    )
    page.wait_for_function(
        """expected => window.__p3027FetchGate?.completedCount >= expected""",
        arg=expected_count,
        timeout=30_000,
    )


def _restore_fetch_response_gate(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3027OriginalFetch === "function") {
            window.fetch = window.__p3027OriginalFetch;
            delete window.__p3027OriginalFetch;
            delete window.__p3027FetchGate;
          }
        }
        """
    )


def _install_tutor_article_search_delays(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3036TutorOriginalFetch === "function") {
            throw new Error("P3-036 Tutor Article delay is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3036TutorOriginalFetch = originalFetch;
          window.__p3036TutorArticleDelays = {};
          window.fetch = async (...args) => {
            const target = new URL(
              String(args[0] instanceof Request ? args[0].url : args[0]),
              window.location.href,
            );
            if (target.pathname === "/v1.1/articles") {
              const query = target.searchParams.get("q") ?? "";
              const delay = Number(window.__p3036TutorArticleDelays?.[query] ?? 0);
              if (delay > 0) {
                await new Promise((resolve) => window.setTimeout(resolve, delay));
              }
            }
            return originalFetch(...args);
          };
        }
        """
    )


def _set_tutor_article_search_delays(page, delays: dict[str, int]) -> None:
    page.evaluate(
        "delays => { window.__p3036TutorArticleDelays = {...delays}; }",
        delays,
    )


def _restore_tutor_article_search_delays(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3036TutorOriginalFetch === "function") {
            window.fetch = window.__p3036TutorOriginalFetch;
            delete window.__p3036TutorOriginalFetch;
            delete window.__p3036TutorArticleDelays;
          }
        }
        """
    )


def _expected_console_key(item: dict[str, object]) -> tuple[object, ...]:
    return (
        item["expectation_id"],
        item["network_request_id"],
        item["label"],
        item["page_id"],
        item["source_url"],
        item["status"],
    )


def _console_base_key(item: dict[str, object]) -> tuple[object, ...]:
    return (
        item["label"],
        item["page_id"],
        item["source_url"],
        item["status"],
    )


def _http_console_status(text: str) -> int | None:
    for status in (404, 503):
        if text == _expected_http_console_text(status):
            return status
    return None


def _reconcile_http_console_evidence(
    messages: ConsoleErrorLog,
    expectations: list[dict[str, object]],
    *,
    include_unrelated: bool,
) -> tuple[Counter[tuple[object, ...]], list[object]]:
    failures: list[object] = []
    expected_full = Counter(_expected_console_key(item) for item in expectations)
    expected_base = Counter(_console_base_key(item) for item in expectations)
    target_bases = set(expected_base)
    playwright_base: Counter[tuple[object, ...]] = Counter()

    for text, evidence in zip(messages, messages.evidence, strict=True):
        status = _http_console_status(text)
        if status is None:
            if include_unrelated:
                failures.append({"kind": "unexpected_console", "evidence": evidence})
            continue
        base = (
            evidence["label"],
            evidence["page_id"],
            evidence["url"],
            status,
        )
        if base not in target_bases:
            if include_unrelated:
                failures.append({"kind": "unexpected_console", "evidence": evidence})
            continue
        provenance_valid = (
            evidence["text"] == text
            and evidence["same_page"] is True
            and evidence["listener_page_id"] == evidence["page_id"]
            and not evidence["worker_url"]
        )
        if not provenance_valid:
            failures.append({"kind": "invalid_console_provenance", "evidence": evidence})
            continue
        playwright_base[base] += 1

    missing_playwright = expected_base - playwright_base
    surplus_playwright = playwright_base - expected_base
    if missing_playwright or surplus_playwright:
        failures.append(
            {
                "kind": "playwright_console_cardinality",
                "missing": list(missing_playwright.elements()),
                "surplus": list(surplus_playwright.elements()),
            }
        )

    cdp_by_base: dict[
        tuple[object, ...], Counter[tuple[object, ...]]
    ] = {base: Counter() for base in target_bases}
    for evidence in messages.cdp_console_evidence:
        text_value = str(evidence["text"])
        status = _http_console_status(text_value)
        if status is None:
            if include_unrelated:
                failures.append({"kind": "unexpected_cdp_console", "evidence": evidence})
            continue
        base = (
            evidence["label"],
            evidence["page_id"],
            evidence["url"],
            status,
        )
        if base not in target_bases:
            if include_unrelated:
                failures.append({"kind": "unexpected_cdp_console", "evidence": evidence})
            continue
        candidate = {
            "expectation_id": evidence.get("expectation_id"),
            "network_request_id": evidence.get("network_request_id"),
            "label": evidence["label"],
            "page_id": evidence["page_id"],
            "source_url": evidence["url"],
            "status": status,
        }
        full_key = _expected_console_key(candidate)
        provenance_valid = (
            evidence["same_page"] is True
            and evidence["listener_page_id"] == evidence["page_id"]
            and not evidence["worker_url"]
        )
        if not provenance_valid or full_key not in expected_full:
            failures.append({"kind": "invalid_cdp_console", "evidence": evidence})
        cdp_by_base[base][full_key] += 1

    actual_full: Counter[tuple[object, ...]] = Counter()
    for base in expected_base:
        expected_for_base = Counter(
            {
                key: count
                for key, count in expected_full.items()
                if key[2:] == base
            }
        )
        actual_for_base = cdp_by_base[base]
        if not (expected_for_base - actual_for_base) and not (
            actual_for_base - expected_for_base
        ):
            actual_full.update(actual_for_base)
            continue
        failures.append(
            {
                "kind": "cdp_console_cardinality",
                "base": base,
                "missing": list((expected_for_base - actual_for_base).elements()),
                "surplus": list((actual_for_base - expected_for_base).elements()),
            }
        )
        actual_full.update(actual_for_base)

    return actual_full, failures


def _expected_response_key(item: dict[str, object]) -> tuple[object, ...]:
    return (
        item["request_id"],
        *_expected_console_key(item),
        item["page_url"],
        item["method"],
        item["resource_type"],
        item["navigation_request"],
    )


def _unexpected_console_errors(messages: list[str]) -> list[object]:
    if not isinstance(messages, ConsoleErrorLog):
        return list(messages)

    failures: list[object] = list(messages.binding_failures)
    if len(messages) != len(messages.evidence):
        return [
            {
                "kind": "console_evidence_alignment",
                "messages": len(messages),
                "evidence": len(messages.evidence),
            }
        ]

    expectation_ids = [item["expectation_id"] for item in messages.expectations]
    request_ids = [item["request_id"] for item in messages.expectations]
    network_request_ids = [
        item["network_request_id"] for item in messages.expectations
    ]
    page_ids = [item["page_id"] for item in messages.expectations]
    if (
        len(expectation_ids) != len(set(expectation_ids))
        or any(not isinstance(item, str) or not item for item in expectation_ids)
        or any(not isinstance(item, str) or not item for item in request_ids)
        or len(request_ids) != len(set(request_ids))
        or any(not isinstance(item, str) or not item for item in network_request_ids)
        or len(network_request_ids) != len(set(network_request_ids))
        or any(not isinstance(item, str) or not item for item in page_ids)
    ):
        failures.append(
            {
                "kind": "invalid_http_error_declarations",
                "expectation_ids": expectation_ids,
                "request_ids": request_ids,
                "network_request_ids": network_request_ids,
                "page_ids": page_ids,
            }
        )

    no_content_ids = [
        item["expectation_id"] for item in messages.no_content_expectations
    ]
    no_content_request_ids = [
        item["request_id"] for item in messages.no_content_expectations
    ]
    if (
        len(no_content_ids) != len(set(no_content_ids))
        or any(not isinstance(item, str) or not item for item in no_content_ids)
        or any(
            not isinstance(item, str) or not item
            for item in no_content_request_ids
        )
        or len(no_content_request_ids) != len(set(no_content_request_ids))
    ):
        failures.append(
            {
                "kind": "invalid_no_content_declarations",
                "expectation_ids": no_content_ids,
                "request_ids": no_content_request_ids,
            }
        )
    for expectation in messages.no_content_expectations:
        request_id = expectation.get("request_id")
        actual = (
            messages.request_evidence.get(request_id)
            if isinstance(request_id, str)
            else None
        )
        if actual is None or not _is_declared_successful_no_content_response(
            messages, request_id, actual
        ):
            failures.append(
                {
                    "kind": "invalid_no_content_response_lifecycle",
                    "expectation": expectation,
                    "request": actual,
                }
            )

    route_expectation_ids = [
        item["expectation_id"] for item in messages.route_transition_expectations
    ]
    route_bound_request_ids: list[str] = []
    for expectation in messages.route_transition_expectations:
        cancelled_route_urls = tuple(expectation.get("cancelled_route_urls") or ())
        cancelled_read_urls = tuple(expectation.get("cancelled_read_urls") or ())
        cancelled_route_keys = tuple(
            _route_document_key(str(url)) for url in cancelled_route_urls
        )
        cancelled_read_keys = tuple(
            _network_url_key(str(url)) for url in cancelled_read_urls
        )
        endpoint_route_keys = {
            _route_document_key(
                str(expectation.get("request_page_url") or "")
            ),
            _route_document_key(str(expectation.get("destination_url") or "")),
        }
        bound_request_ids = tuple(expectation.get("bound_request_ids") or ())
        post_terminal_request_id = expectation.get("post_terminal_request_id")
        cache_precursor_request_ids = expectation.get(
            "cache_precursor_request_ids"
        )
        cache_precursors = _route_transition_cache_precursors(
            messages,
            expectation,
        )
        endpoint_route_binding_counts = {
            route_key: sum(
                1
                for request_id in bound_request_ids
                if request_id in messages.request_evidence
                and _route_transition_request_kind(
                    messages,
                    expectation,
                    messages.request_evidence[request_id],
                )
                in {"route", "route_with_complete_precursor_snapshot"}
                and _route_document_key(
                    str(
                        messages.request_evidence[request_id].get(
                            "source_url"
                        )
                        or ""
                    )
                )
                == route_key
            )
            for route_key in endpoint_route_keys
        }
        cancelled_route_binding_counts = {
            route_key: sum(
                1
                for request_id in bound_request_ids
                if request_id in messages.request_evidence
                and _route_transition_request_kind(
                    messages,
                    expectation,
                    messages.request_evidence[request_id],
                )
                == "cancelled_route"
                and _route_document_key(
                    str(
                        messages.request_evidence[request_id].get(
                            "source_url"
                        )
                        or ""
                    )
                )
                == route_key
            )
            for route_key in cancelled_route_keys
        }
        cancelled_read_binding_counts = {
            read_key: sum(
                1
                for request_id in bound_request_ids
                if request_id in messages.request_evidence
                and _route_transition_request_kind(
                    messages,
                    expectation,
                    messages.request_evidence[request_id],
                )
                == "explicit_read"
                and _network_url_key(
                    str(
                        messages.request_evidence[request_id].get(
                            "source_url"
                        )
                        or ""
                    )
                )
                == read_key
            )
            for read_key in cancelled_read_keys
        }
        route_bound_request_ids.extend(str(item) for item in bound_request_ids)
        precursor_snapshot_binding_count = sum(
            1
            for request_id in bound_request_ids
            if request_id in messages.request_evidence
            and _route_transition_request_kind(
                messages,
                expectation,
                messages.request_evidence[request_id],
            )
            == "route_with_complete_precursor_snapshot"
        )
        completion_sequence = expectation.get("completion_sequence")
        declaration_navigation_generation = expectation.get(
            "declaration_navigation_generation"
        )
        completion_navigation_generation = expectation.get(
            "completion_navigation_generation"
        )
        route_identity_changed = (
            _route_url_key(str(expectation.get("request_page_url") or ""))
            != _route_url_key(str(expectation.get("destination_url") or ""))
        )
        observed_navigation = (
            isinstance(declaration_navigation_generation, int)
            and isinstance(completion_navigation_generation, int)
            and completion_navigation_generation
            > declaration_navigation_generation
        )
        observed_required_supersession = bool(cancelled_route_urls) and all(
            count == 1
            for count in cancelled_route_binding_counts.values()
        )
        observed_explicit_supersession = observed_required_supersession
        valid_route_expectation = (
            isinstance(expectation.get("expectation_id"), str)
            and bool(expectation["expectation_id"])
            and isinstance(expectation.get("page_id"), str)
            and bool(expectation["page_id"])
            and isinstance(expectation.get("label"), str)
            and bool(expectation["label"])
            and _is_allowed_frontend_url(
                str(expectation.get("request_page_url") or "")
            )
            and _is_allowed_frontend_url(
                str(expectation.get("destination_url") or "")
            )
            and isinstance(expectation.get("declaration_sequence"), int)
            and isinstance(declaration_navigation_generation, int)
            and isinstance(completion_sequence, int)
            and isinstance(completion_navigation_generation, int)
            and int(expectation["declaration_sequence"])
            < int(completion_sequence)
            and _route_url_key(str(expectation.get("completion_url") or ""))
            == _route_url_key(str(expectation.get("destination_url") or ""))
            and (
                route_identity_changed
                or observed_navigation
                or observed_explicit_supersession
            )
            and isinstance(
                expectation.get("allow_post_terminal_destination_commit"), bool
            )
            and (
                post_terminal_request_id is None
                or (
                    expectation.get("allow_post_terminal_destination_commit") is True
                    and isinstance(post_terminal_request_id, str)
                    and post_terminal_request_id in bound_request_ids
                )
            )
            and (
                cache_precursors is not None
                and isinstance(
                    expectation.get("allow_complete_precursor_snapshot"),
                    bool,
                )
                and isinstance(cache_precursor_request_ids, tuple)
                and precursor_snapshot_binding_count in {0, 1}
                and (
                    precursor_snapshot_binding_count == 0
                    or (
                        expectation.get(
                            "allow_complete_precursor_snapshot"
                        )
                        is True
                        and bool(cache_precursors)
                    )
                )
            )
            and len(cancelled_route_keys) == len(set(cancelled_route_keys))
            and all(count <= 1 for count in endpoint_route_binding_counts.values())
            and all(
                _is_allowed_frontend_url(str(url))
                for url in cancelled_route_urls
            )
            and not set(cancelled_route_keys) & endpoint_route_keys
            and all(count == 1 for count in cancelled_route_binding_counts.values())
            and len(cancelled_read_keys) == len(set(cancelled_read_keys))
            and all(
                _is_allowed_http_url(str(url)) and urlparse(str(url)).port == 8000
                for url in cancelled_read_urls
            )
            and all(count == 1 for count in cancelled_read_binding_counts.values())
            and len(bound_request_ids) == len(set(bound_request_ids))
            and all(
                isinstance(request_id, str)
                and request_id in messages.request_evidence
                and isinstance(
                    messages.request_evidence[request_id].get("terminal_sequence"),
                    int,
                )
                and int(
                    messages.request_evidence[request_id]["terminal_sequence"]
                )
                < int(completion_sequence)
                and _route_transition_request_kind(
                    messages,
                    expectation,
                    messages.request_evidence[request_id],
                )
                is not None
                for request_id in bound_request_ids
            )
        )
        if not valid_route_expectation:
            failures.append(
                {
                    "kind": "invalid_route_transition_expectation",
                    "expectation": expectation,
                }
            )
    if len(route_expectation_ids) != len(set(route_expectation_ids)):
        failures.append(
            {
                "kind": "duplicate_route_transition_expectation",
                "expectation_ids": route_expectation_ids,
            }
        )
    if len(route_bound_request_ids) != len(set(route_bound_request_ids)):
        failures.append(
            {
                "kind": "duplicate_route_transition_request_binding",
                "request_ids": route_bound_request_ids,
            }
        )
    for request_id, evidence in messages.request_evidence.items():
        if not _is_product_browser_request(evidence):
            continue
        if (
            evidence.get("response_status") == 204
            and evidence.get("method") in {"POST", "PUT", "PATCH", "DELETE"}
            and request_id not in messages._expected_no_content_request_ids
        ):
            failures.append(
                {
                    "kind": "undeclared_mutation_no_content_response",
                    "request_id": request_id,
                    "evidence": evidence,
                }
            )
            continue
        if (
            _is_framework_prefetch_cancellation(messages, evidence)
            or _is_route_transition_cancellation(messages, evidence)
            or _is_declared_cancelled_route_request(messages, evidence)
            or _is_declared_route_read_cancellation(messages, evidence)
            or _is_superseded_successful_read(messages, request_id, evidence)
            or _is_next_static_chunk_cancellation(messages, evidence)
            or _is_declared_successful_no_content_response(
                messages, request_id, evidence
            )
        ):
            continue
        if evidence["failure"] is not None:
            start_sequence = evidence.get("start_sequence")
            terminal_sequence = evidence.get("terminal_sequence")
            nearby_navigation_events = [
                event
                for event in messages._page_navigation_events.get(
                    str(evidence.get("page_id") or ""),
                    (),
                )
                if isinstance(start_sequence, int)
                and isinstance(terminal_sequence, int)
                and isinstance(event.get("sequence"), int)
                and start_sequence - 5
                <= int(event["sequence"])
                <= terminal_sequence + 5
            ]
            failures.append(
                {
                    "kind": (
                        "failed_product_request_after_http_response"
                        if evidence.get("response_status") is not None
                        else "failed_product_request_without_http_response"
                    ),
                    "request_id": request_id,
                    "evidence": evidence,
                    "nearby_navigation_events": nearby_navigation_events,
                }
            )
        elif evidence["finished"] is not True:
            failures.append(
                {
                    "kind": "unsettled_product_request",
                    "request_id": request_id,
                    "evidence": evidence,
                }
            )

    expected_console = Counter(_expected_console_key(item) for item in messages.expectations)
    expected_response = Counter(_expected_response_key(item) for item in messages.expectations)
    actual_console, console_failures = _reconcile_http_console_evidence(
        messages,
        messages.expectations,
        include_unrelated=True,
    )
    failures.extend(console_failures)

    expected_console_delta = expected_console - actual_console
    actual_console_delta = actual_console - expected_console
    if expected_console_delta or actual_console_delta:
        failures.append(
            {
                "kind": "console_cardinality",
                "missing": list(expected_console_delta.elements()),
                "surplus": list(actual_console_delta.elements()),
            }
        )

    actual_response: Counter[tuple[object, ...]] = Counter()
    for evidence in messages.response_evidence:
        if evidence["expectation_id"] is None:
            failures.append({"kind": "unregistered_http_error_response", "evidence": evidence})
            continue
        candidate = {
            "expectation_id": evidence["expectation_id"],
            "request_id": evidence["request_id"],
            "network_request_id": evidence["network_request_id"],
            "label": evidence["label"],
            "page_id": evidence["page_id"],
            "page_url": evidence["page_url"],
            "source_url": evidence["source_url"],
            "status": evidence["status"],
            "method": evidence["method"],
            "resource_type": evidence["resource_type"],
            "navigation_request": evidence["navigation_request"],
        }
        expectation = messages._expectation(evidence["expectation_id"])
        bridge_valid = (
            expectation is not None
            and evidence["bridge_expectation_id"] == evidence["expectation_id"]
        )
        provenance_valid = (
            evidence["same_page"] is True
            and evidence["main_frame"] is True
            and evidence["listener_page_id"] == evidence["page_id"]
            and (
                evidence["navigation_request"] is True
                or evidence["frame_url_at_request"] == evidence["page_url"]
            )
            and not evidence["service_worker_url"]
            and evidence["from_service_worker"] is False
            and evidence["finished"] is True
            and evidence["failure"] is None
            and bridge_valid
        )
        if not provenance_valid:
            failures.append({"kind": "invalid_response_lifecycle", "evidence": evidence})
            continue
        actual_response[_expected_response_key(candidate)] += 1

    expected_response_delta = expected_response - actual_response
    actual_response_delta = actual_response - expected_response
    if expected_response_delta or actual_response_delta:
        failures.append(
            {
                "kind": "response_cardinality",
                "missing": list(expected_response_delta.elements()),
                "surplus": list(actual_response_delta.elements()),
            }
        )
    return failures


def _verify_http_error_evidence_contract() -> None:
    expectation = {
        "expectation_id": "contract-http-1",
        "request_id": "contract-request-1",
        "network_request_id": "contract-network-request-1",
        "label": "contract-probe",
        "page_id": "contract-page-1",
        "page_url": f"{FRONTEND_URL}/contract-probe",
        "source_url": f"{BROWSER_API_URL}/contract-probe",
        "status": 503,
        "method": "GET",
        "resource_type": "fetch",
        "navigation_request": False,
        "response_header_required": True,
    }
    console = {
        "expectation_id": expectation["expectation_id"],
        "network_request_id": expectation["network_request_id"],
        "label": expectation["label"],
        "listener_page_id": expectation["page_id"],
        "listener_page_url": expectation["page_url"],
        "page_id": expectation["page_id"],
        "page_url": expectation["page_url"],
        "same_page": True,
        "worker_url": "",
        "text": _expected_http_console_text(503),
        "url": expectation["source_url"],
    }
    response = {
        **expectation,
        "listener_page_id": expectation["page_id"],
        "listener_page_url": expectation["page_url"],
        "frame_url_at_request": expectation["page_url"],
        "same_page": True,
        "main_frame": True,
        "service_worker_url": "",
        "from_service_worker": False,
        "bridge_expectation_id": expectation["expectation_id"],
        "finished": True,
        "failure": None,
    }

    def build_log(
        *,
        console_override: dict[str, object] | None = None,
        response_override: dict[str, object] | None = None,
        expectation_override: dict[str, object] | None = None,
        include_console: bool = True,
        include_response: bool = True,
        extra_message: str | None = None,
        duplicate_response: bool = False,
    ) -> ConsoleErrorLog:
        log = ConsoleErrorLog()
        effective_expectation = {**expectation, **(expectation_override or {})}
        log.expectations.append(effective_expectation)
        if include_console:
            console_item = {**console, **(console_override or {})}
            list.append(log, str(console_item["text"]))
            log.evidence.append(console_item)
            log.cdp_console_evidence.append(dict(console_item))
        if extra_message is not None:
            list.append(log, extra_message)
            log.evidence.append(
                {
                    **console,
                    "text": extra_message,
                    "url": f"{BROWSER_API_URL}/foreign",
                }
            )
        if include_response:
            response_item = {
                **response,
                **effective_expectation,
                **(response_override or {}),
            }
            log.response_evidence.append(response_item)
            if duplicate_response:
                log.response_evidence.append(dict(response_item))
        return log

    _require(
        not _unexpected_console_errors(build_log()),
        "valid controlled HTTP error evidence did not reconcile",
    )
    negative_cases = (
        build_log(console_override={"label": "wrong-label"}),
        build_log(console_override={"page_id": "wrong-page"}),
        build_log(console_override={"url": f"{BROWSER_API_URL}/wrong"}),
        build_log(console_override={"same_page": False}),
        build_log(console_override={"worker_url": "worker.js"}),
        build_log(response_override={"expectation_id": "wrong-expectation"}),
        build_log(response_override={"request_id": "wrong-request"}),
        build_log(response_override={"network_request_id": "wrong-network-request"}),
        build_log(response_override={"label": "wrong-label"}),
        build_log(response_override={"page_url": f"{FRONTEND_URL}/wrong"}),
        build_log(response_override={"source_url": f"{BROWSER_API_URL}/wrong"}),
        build_log(response_override={"status": 404}),
        build_log(response_override={"method": "POST"}),
        build_log(response_override={"resource_type": "xhr"}),
        build_log(response_override={"navigation_request": True}),
        build_log(response_override={"same_page": False}),
        build_log(response_override={"main_frame": False}),
        build_log(response_override={"listener_page_id": "wrong-page"}),
        build_log(response_override={"frame_url_at_request": f"{FRONTEND_URL}/wrong"}),
        build_log(response_override={"service_worker_url": "service-worker.js"}),
        build_log(response_override={"from_service_worker": True}),
        build_log(response_override={"bridge_expectation_id": "wrong-expectation"}),
        build_log(response_override={"finished": False}),
        build_log(response_override={"failure": "net::ERR_FAILED"}),
        build_log(expectation_override={"request_id": None}),
        build_log(expectation_override={"network_request_id": None}),
        build_log(expectation_override={"expectation_id": ""}),
        build_log(response_override={"expectation_id": None}),
        build_log(duplicate_response=True),
        build_log(include_console=False),
        build_log(include_response=False),
        build_log(extra_message=_expected_http_console_text(503)),
    )
    _require(
        all(_unexpected_console_errors(case) for case in negative_cases),
        "controlled HTTP error evidence accepted a negative contract case",
    )

    duplicate_log = ConsoleErrorLog()
    for index in range(2):
        duplicate_expectation = {
            **expectation,
            "expectation_id": f"contract-http-{index + 1}",
            "request_id": f"contract-request-{index + 1}",
            "network_request_id": f"contract-network-request-{index + 1}",
        }
        duplicate_log.expectations.append(duplicate_expectation)
        list.append(duplicate_log, str(console["text"]))
        duplicate_log.evidence.append(
            {
                **console,
                "expectation_id": duplicate_expectation["expectation_id"],
                "network_request_id": duplicate_expectation["network_request_id"],
            }
        )
        duplicate_log.cdp_console_evidence.append(
            {
                **console,
                "expectation_id": duplicate_expectation["expectation_id"],
                "network_request_id": duplicate_expectation["network_request_id"],
            }
        )
        duplicate_log.response_evidence.append(
            {
                **response,
                **duplicate_expectation,
                "bridge_expectation_id": duplicate_expectation["expectation_id"],
            }
        )
    _require(
        not _unexpected_console_errors(duplicate_log),
        "two predeclared same-URL HTTP errors did not reconcile independently",
    )
    misbound_duplicate_log = ConsoleErrorLog()
    misbound_duplicate_log.expectations.extend(
        dict(item) for item in duplicate_log.expectations
    )
    misbound_duplicate_log.response_evidence.extend(
        dict(item) for item in duplicate_log.response_evidence
    )
    for _ in range(2):
        list.append(misbound_duplicate_log, str(console["text"]))
        misbound_duplicate_log.evidence.append(dict(duplicate_log.evidence[0]))
        misbound_duplicate_log.cdp_console_evidence.append(
            dict(duplicate_log.cdp_console_evidence[0])
        )
    _require(
        bool(_unexpected_console_errors(misbound_duplicate_log)),
        "duplicate console evidence from one request satisfied another request",
    )

    class ContractFrame:
        def __init__(self, page) -> None:
            self.page = page
            self.url = page.url

    class ContractPage:
        url = str(expectation["page_url"])

        def __init__(self, page_id: str) -> None:
            self._impl_obj = type("PageIdentity", (), {"_guid": page_id})()
            self.main_frame = ContractFrame(self)

    class ContractRequest:
        service_worker = None
        headers: dict[str, str] = {}
        url = str(expectation["source_url"])
        method = str(expectation["method"])
        resource_type = str(expectation["resource_type"])

        def __init__(self, page: ContractPage, request_id: str) -> None:
            self.frame = page.main_frame
            self._impl_obj = type("RequestIdentity", (), {"_guid": request_id})()

        def is_navigation_request(self) -> bool:
            return bool(expectation["navigation_request"])

    class ContractResponse:
        def __init__(self, *, url: str, status: int) -> None:
            self.url = url
            self.status = status
            self.headers = {"content-type": "application/json"}

    class ContractRoute:
        def __init__(self, request, response: ContractResponse) -> None:
            self.request = request
            self.response = response
            self.fetch_options: dict[str, object] | None = None
            self.fulfill_options: dict[str, object] | None = None

        def fetch(self, **options):
            self.fetch_options = options
            return self.response

        def fulfill(self, **options) -> None:
            self.fulfill_options = options

    def build_forward_contract(response_url: str) -> tuple[ConsoleErrorLog, ContractRoute]:
        log = ConsoleErrorLog()
        page = ContractPage("forward-contract-page")
        page_id = _page_identity(page)
        log._observed_pages[page_id] = str(expectation["label"])
        expectation_ids = log.declare_http_errors(
            label=str(expectation["label"]),
            page_url=str(expectation["page_url"]),
            source_url=str(expectation["source_url"]),
            status=int(expectation["status"]),
            method=str(expectation["method"]),
            resource_type=str(expectation["resource_type"]),
            navigation_request=bool(expectation["navigation_request"]),
        )
        route = ContractRoute(
            ContractRequest(page, "forward-contract-request"),
            ContractResponse(
                url=response_url,
                status=int(expectation["status"]),
            ),
        )
        _forward_expected_http_error(
            route,
            console_errors=log,
            page=page,
            expectation_ids=expectation_ids,
        )
        return log, route

    forwarded_log, forwarded_route = build_forward_contract(
        str(expectation["source_url"])
    )
    _require(
        forwarded_route.fetch_options == {"max_redirects": 0}
        and forwarded_route.fulfill_options is not None
        and _header_value(
            forwarded_route.fulfill_options["headers"],
            CONTROLLED_HTTP_EXPECTATION_HEADER,
        )
        == forwarded_log.expectations[0]["expectation_id"],
        "forwarded controlled HTTP error did not disable redirects or bridge identity",
    )
    redirected_route_rejected = False
    try:
        build_forward_contract("https://external.invalid/final")
    except E2EFailure:
        redirected_route_rejected = True
    _require(
        redirected_route_rejected,
        "forwarded controlled HTTP error accepted a redirected response URL",
    )

    def capture_contract_cdp_request(
        log: ConsoleErrorLog,
        page: ContractPage,
        network_request_id: str,
        *,
        session_id: str = "contract-session",
    ) -> None:
        log._capture_cdp_request(
            {
                "requestId": network_request_id,
                "documentURL": expectation["page_url"],
                "request": {
                    "url": expectation["source_url"],
                    "method": expectation["method"],
                },
                "type": "Fetch",
            },
            label=str(expectation["label"]),
            page=page,
            session_id=session_id,
        )

    def capture_contract_cdp_response(
        log: ConsoleErrorLog,
        network_request_id: str,
        status: int,
        *,
        bridge_id: str = "",
        session_id: str = "contract-session",
    ) -> None:
        log._capture_cdp_response(
            {
                "requestId": network_request_id,
                "response": {
                    "status": status,
                    "headers": (
                        {CONTROLLED_HTTP_EXPECTATION_HEADER: bridge_id}
                        if bridge_id
                        else {}
                    ),
                },
            },
            session_id=session_id,
        )

    delayed_binding_log = ConsoleErrorLog()
    delayed_binding_page = ContractPage("delayed-page")
    delayed_ids = delayed_binding_log.declare_http_errors(
        label=str(expectation["label"]),
        page_url=str(expectation["page_url"]),
        source_url=str(expectation["source_url"]),
        status=int(expectation["status"]),
        method=str(expectation["method"]),
        resource_type=str(expectation["resource_type"]),
        navigation_request=bool(expectation["navigation_request"]),
    )
    delayed_item = delayed_binding_log.bind_http_error_request(
        delayed_ids,
        request=ContractRequest(delayed_binding_page, "delayed-request"),
        page=delayed_binding_page,
    )
    _require(
        delayed_item["network_request_id"] is None,
        "route-first contract unexpectedly required an early CDP request",
    )
    capture_contract_cdp_request(
        delayed_binding_log,
        delayed_binding_page,
        "delayed-network-request",
    )
    capture_contract_cdp_response(
        delayed_binding_log,
        "delayed-network-request",
        int(expectation["status"]),
        bridge_id=str(delayed_item["expectation_id"]),
    )
    _require(
        delayed_item["network_request_id"]
        == "contract-session:delayed-network-request",
        "route-first contract did not bind the later CDP response",
    )

    prior_success_log = ConsoleErrorLog()
    prior_success_page = ContractPage("prior-success-page")
    prior_success_ids = prior_success_log.declare_http_errors(
        label=str(expectation["label"]),
        page_url=str(expectation["page_url"]),
        source_url=str(expectation["source_url"]),
        status=int(expectation["status"]),
        method=str(expectation["method"]),
        resource_type=str(expectation["resource_type"]),
        navigation_request=bool(expectation["navigation_request"]),
    )
    capture_contract_cdp_request(
        prior_success_log,
        prior_success_page,
        "prior-success-network-request",
    )
    capture_contract_cdp_response(
        prior_success_log,
        "prior-success-network-request",
        200,
    )
    prior_success_item = prior_success_log.bind_http_error_request(
        prior_success_ids,
        request=ContractRequest(prior_success_page, "controlled-request"),
        page=prior_success_page,
    )
    capture_contract_cdp_request(
        prior_success_log,
        prior_success_page,
        "controlled-network-request",
    )
    capture_contract_cdp_response(
        prior_success_log,
        "controlled-network-request",
        int(expectation["status"]),
        bridge_id=str(prior_success_item["expectation_id"]),
    )
    _require(
        prior_success_item["network_request_id"]
        == "contract-session:controlled-network-request",
        "a prior successful request captured the controlled failure binding",
    )

    reverse_completion_log = ConsoleErrorLog()
    reverse_completion_page = ContractPage("reverse-page")
    reverse_ids = reverse_completion_log.declare_http_errors(
        label=str(expectation["label"]),
        page_url=str(expectation["page_url"]),
        source_url=str(expectation["source_url"]),
        status=int(expectation["status"]),
        method=str(expectation["method"]),
        resource_type=str(expectation["resource_type"]),
        navigation_request=bool(expectation["navigation_request"]),
        count=2,
    )
    reverse_items = [
        reverse_completion_log.bind_http_error_request(
            reverse_ids,
            request=ContractRequest(
                reverse_completion_page, f"reverse-request-{index}"
            ),
            page=reverse_completion_page,
        )
        for index in (1, 2)
    ]
    for network_id in ("reverse-network-1", "reverse-network-2"):
        capture_contract_cdp_request(
            reverse_completion_log,
            reverse_completion_page,
            network_id,
        )
    capture_contract_cdp_response(
        reverse_completion_log,
        "reverse-network-2",
        int(expectation["status"]),
        bridge_id=reverse_ids[1],
    )
    capture_contract_cdp_response(
        reverse_completion_log,
        "reverse-network-1",
        int(expectation["status"]),
        bridge_id=reverse_ids[0],
    )
    _require(
        reverse_items[0]["network_request_id"]
        == "contract-session:reverse-network-1"
        and reverse_items[1]["network_request_id"]
        == "contract-session:reverse-network-2",
        "response-header bridge crossed reverse-completing identical requests",
    )

    late_console_log = build_log(include_console=False)

    class DelayedConsolePage:
        delivered = False

        def wait_for_timeout(self, _timeout_ms: int) -> None:
            if self.delivered:
                return
            self.delivered = True
            list.append(late_console_log, str(console["text"]))
            late_console_log.evidence.append(dict(console))
            late_console_log.cdp_console_evidence.append(dict(console))

    _wait_for_declared_http_errors(
        DelayedConsolePage(),
        late_console_log,
        expectation_ids=(str(expectation["expectation_id"]),),
        timeout_ms=100,
    )

    not_found_expectation = {
        **expectation,
        "expectation_id": "contract-404",
        "request_id": "contract-404-request",
        "network_request_id": "contract-session:contract-404-network",
        "label": "contract-not-found",
        "page_id": "contract-404-page",
        "page_url": f"{FRONTEND_URL}/contract-not-found",
        "source_url": f"{BROWSER_API_URL}/contract-not-found",
        "status": 404,
        "response_header_required": True,
    }
    not_found_console = {
        **console,
        "expectation_id": not_found_expectation["expectation_id"],
        "network_request_id": not_found_expectation["network_request_id"],
        "label": not_found_expectation["label"],
        "listener_page_id": not_found_expectation["page_id"],
        "listener_page_url": not_found_expectation["page_url"],
        "page_id": not_found_expectation["page_id"],
        "page_url": not_found_expectation["page_url"],
        "text": _expected_http_console_text(404),
        "url": not_found_expectation["source_url"],
    }
    not_found_response = {
        **response,
        **not_found_expectation,
        "listener_page_id": not_found_expectation["page_id"],
        "listener_page_url": not_found_expectation["page_url"],
        "frame_url_at_request": not_found_expectation["page_url"],
        "bridge_expectation_id": not_found_expectation["expectation_id"],
    }
    not_found_log = ConsoleErrorLog()
    not_found_log.expectations.append(not_found_expectation)
    list.append(not_found_log, str(not_found_console["text"]))
    not_found_log.evidence.append(not_found_console)
    not_found_log.cdp_console_evidence.append(dict(not_found_console))
    not_found_log.response_evidence.append(not_found_response)
    _require(
        not _unexpected_console_errors(not_found_log),
        "valid response-bridged predeclared 404 evidence did not reconcile",
    )
    headerless_404_log = ConsoleErrorLog()
    headerless_404_log.expectations.append(dict(not_found_expectation))
    list.append(headerless_404_log, str(not_found_console["text"]))
    headerless_404_log.evidence.append(dict(not_found_console))
    headerless_404_log.cdp_console_evidence.append(dict(not_found_console))
    headerless_404_log.response_evidence.append(
        {**not_found_response, "bridge_expectation_id": None}
    )
    _require(
        bool(_unexpected_console_errors(headerless_404_log)),
        "headerless 404 evidence bypassed the response identity bridge",
    )
    surplus_404_log = ConsoleErrorLog()
    surplus_404_log.expectations.append(dict(not_found_expectation))
    list.append(surplus_404_log, str(not_found_console["text"]))
    surplus_404_log.evidence.append(dict(not_found_console))
    surplus_404_log.cdp_console_evidence.append(dict(not_found_console))
    surplus_404_log.response_evidence.extend(
        [
            dict(not_found_response),
            {
                **not_found_response,
                "expectation_id": None,
                "request_id": "contract-unregistered-500",
                "network_request_id": None,
                "status": 500,
            },
        ]
    )
    _require(
        bool(_unexpected_console_errors(surplus_404_log)),
        "predeclared 404 ledger accepted a surplus HTTP failure",
    )

    def lifecycle_log(
        *,
        method: str = "GET",
        failure: str | None = "net::ERR_ABORTED",
        finished: bool = False,
        closed: bool = True,
        response_status: int | None = None,
        source_url: str = f"{BROWSER_API_URL}/learning/state",
        resource_type: str = "fetch",
        main_frame: bool = True,
        service_worker_url: str = "",
        start_sequence: int = 1,
        navigation_generation: int = 1,
        terminal_page_url: str | None = None,
        terminal_navigation_generation: int | None = None,
        rsc_request: bool = False,
        next_router_prefetch: bool = False,
        declare_no_content: bool = False,
    ) -> ConsoleErrorLog:
        log = ConsoleErrorLog()
        page_id = "contract-lifecycle-page"
        request_id = "contract-lifecycle-request"
        page_url = f"{FRONTEND_URL}/articles"
        response_url = source_url if response_status is not None else None
        evidence = {
            "label": "contract-lifecycle",
            "page_id": page_id,
            "page_url": page_url,
            "frame_url_at_request": page_url,
            "source_url": source_url,
            "method": method,
            "resource_type": resource_type,
            "navigation_request": False,
            "main_frame": main_frame,
            "service_worker_url": service_worker_url,
            "rsc_request": rsc_request,
            "next_router_prefetch": next_router_prefetch,
            "purpose": "",
            "sec_purpose": "",
            "route_intent_sequence": (
                start_sequence
                if rsc_request and not next_router_prefetch
                else None
            ),
            "start_sequence": start_sequence,
            "start_monotonic": 1.0,
            "response_sequence": 2 if response_status is not None else None,
            "response_monotonic": 1.1 if response_status is not None else None,
            "terminal_sequence": 4 if failure is not None or finished else None,
            "terminal_monotonic": 1.2 if failure is not None or finished else None,
            "navigation_generation": navigation_generation,
            "terminal_page_url": terminal_page_url,
            "terminal_navigation_generation": terminal_navigation_generation,
            "response_status": response_status,
            "response_url": response_url,
            "finished": finished,
            "failure": failure,
        }
        log.request_evidence[request_id] = evidence
        if closed:
            log._closed_page_ids.add(page_id)
            log._page_close_intent_sequences[page_id] = 3
        if declare_no_content:
            expectation_id = "contract-no-content-1"
            log.no_content_expectations.append(
                {
                    "expectation_id": expectation_id,
                    "label": evidence["label"],
                    "page_id": page_id,
                    "page_url": page_url,
                    "source_url": source_url,
                    "method": method,
                    "declaration_sequence": 0,
                    "request_id": request_id,
                    "response_status": response_status,
                    "response_url": response_url,
                    "finished": finished,
                    "failure": failure,
                }
            )
            log._expected_no_content_request_ids[request_id] = expectation_id
        return log

    def add_completed_route_expectation(
        log: ConsoleErrorLog,
        *,
        destination_url: str,
        allow_speculative_cancellations: bool = False,
    ) -> None:
        evidence = log.request_evidence["contract-lifecycle-request"]
        log.route_transition_expectations.append(
            {
                "expectation_id": "contract-route-1",
                "label": evidence["label"],
                "page_id": evidence["page_id"],
                "request_page_url": evidence["page_url"],
                "destination_url": destination_url,
                "allow_speculative_cancellations": allow_speculative_cancellations,
                "allow_post_terminal_destination_commit": False,
                "allow_complete_precursor_snapshot": False,
                "cancelled_route_urls": (),
                "cancelled_read_urls": (),
                "declaration_sequence": 0,
                "declaration_navigation_generation": 0,
                "completion_sequence": 5,
                "completion_url": destination_url,
                "completion_navigation_generation": (
                    1 if destination_url == evidence["page_url"] else 0
                ),
                "bound_request_ids": ("contract-lifecycle-request",),
                "post_terminal_request_id": None,
                "cache_precursor_request_ids": (),
            }
        )

    class ContractPage:
        def __init__(self, url: str) -> None:
            self.url = url

        def wait_for_timeout(self, milliseconds: int) -> None:
            time.sleep(milliseconds / 1_000)

    production_page = ContractPage(f"{FRONTEND_URL}/articles")
    production_log = ConsoleErrorLog()
    production_page_id = _page_identity(production_page)
    production_log._observed_pages[production_page_id] = "contract-production"
    production_expectation_id = production_log.declare_route_transition(
        page=production_page,
        destination_url=f"{FRONTEND_URL}/session",
    )
    production_log.request_evidence["production-route-request"] = {
        "label": "contract-production",
        "page_id": production_page_id,
        "page_url": f"{FRONTEND_URL}/articles",
        "frame_url_at_request": f"{FRONTEND_URL}/articles",
        "source_url": f"{FRONTEND_URL}/session?_rsc=production",
        "method": "GET",
        "resource_type": "fetch",
        "navigation_request": False,
        "main_frame": True,
        "service_worker_url": "",
        "rsc_request": True,
        "next_router_prefetch": False,
        "purpose": "",
        "sec_purpose": "",
        "route_intent_sequence": 2,
        "start_sequence": 2,
        "start_monotonic": 1.0,
        "response_sequence": 3,
        "response_monotonic": 1.05,
        "terminal_sequence": 4,
        "terminal_monotonic": 1.1,
        "navigation_generation": 0,
        "terminal_page_url": f"{FRONTEND_URL}/session",
        "terminal_navigation_generation": 1,
        "response_status": 200,
        "response_url": f"{FRONTEND_URL}/session?_rsc=production",
        "finished": False,
        "failure": "net::ERR_ABORTED",
    }
    production_log._event_sequence = 4
    production_page.url = f"{FRONTEND_URL}/session"
    production_log.complete_route_transition(
        page=production_page,
        expectation_id=production_expectation_id,
    )
    production_expectation = production_log.route_transition_expectations[0]
    _require(
        production_expectation["bound_request_ids"]
        == ("production-route-request",)
        and production_expectation["completion_sequence"] == 5,
        "production route lifecycle did not freeze its exact request at completion",
    )
    production_log.request_evidence["late-route-request"] = {
        **production_log.request_evidence["production-route-request"],
        "start_sequence": 6,
        "terminal_sequence": 7,
    }
    _require(
        production_expectation["bound_request_ids"]
        == ("production-route-request",),
        "production route lifecycle admitted a request after completion",
    )

    cache_page = ContractPage(f"{FRONTEND_URL}/articles")
    cache_log = ConsoleErrorLog()
    cache_page_id = _page_identity(cache_page)
    cache_log._observed_pages[cache_page_id] = "contract-cache"
    cache_precursor_evidence = {
        **production_log.request_evidence["production-route-request"],
        "label": "contract-cache",
        "page_id": cache_page_id,
        "source_url": f"{FRONTEND_URL}/session?_rsc=cache-precursor",
        "response_url": f"{FRONTEND_URL}/session?_rsc=cache-precursor",
        "start_sequence": 1,
        "response_sequence": 2,
        "terminal_sequence": 3,
        "finished": True,
        "failure": None,
    }
    cache_log.request_evidence["contract-cache-precursor"] = (
        cache_precursor_evidence
    )
    cache_log.request_evidence["contract-cache-precursor-2"] = {
        **cache_precursor_evidence,
        "source_url": f"{FRONTEND_URL}/session?_rsc=cache-precursor-2",
        "response_url": f"{FRONTEND_URL}/session?_rsc=cache-precursor-2",
        "start_sequence": 4,
        "response_sequence": 5,
        "terminal_sequence": 6,
    }
    cache_log._event_sequence = 6
    cache_expectation_id = cache_log.declare_route_transition(
        page=cache_page,
        destination_url=f"{FRONTEND_URL}/session",
        allow_complete_precursor_snapshot=True,
        allow_post_terminal_destination_commit=True,
    )
    _require(
        cache_log.route_transition_expectations[0][
            "cache_precursor_request_ids"
        ]
        == ("contract-cache-precursor", "contract-cache-precursor-2")
        and cache_log.route_transition_expectations[0]["declaration_sequence"]
        == 7,
        "route cache precursor was not bound before the new transition",
    )
    cache_current_request = {
        **production_log.request_evidence["production-route-request"],
        "label": "contract-cache",
        "page_id": cache_page_id,
        "start_sequence": 8,
        "response_sequence": 9,
        "terminal_sequence": 10,
        "page_url": f"{FRONTEND_URL}/library",
        "frame_url_at_request": f"{FRONTEND_URL}/library",
        "terminal_page_url": f"{FRONTEND_URL}/library",
        "terminal_navigation_generation": 0,
    }
    cache_log.request_evidence["contract-current-route"] = cache_current_request
    cache_log.bind_post_terminal_destination_request(
        expectation_id=cache_expectation_id,
        evidence=cache_current_request,
    )
    cache_page.url = f"{FRONTEND_URL}/session"
    cache_log._event_sequence = 11
    cache_log._page_navigation_generations[cache_page_id] = 1
    cache_log._page_navigation_events[cache_page_id] = [{
        "sequence": 11,
        "generation": 1,
        "url": cache_page.url,
        "monotonic": 1.2,
    }]
    cache_log.complete_route_transition(
        page=cache_page,
        expectation_id=cache_expectation_id,
    )
    _require(
        cache_log.route_transition_expectations[0]["bound_request_ids"]
        == ("contract-current-route",)
        and not _unexpected_console_errors(cache_log)
        and _route_cancellations_with_complete_precursor_snapshot(cache_log)
        == [cache_current_request],
        "production route snapshot did not preserve and audit both precursors",
    )
    for invalid_status in (None, 301, 500):
        cache_current_request["response_status"] = invalid_status
        _require(
            not _route_cancellations_with_complete_precursor_snapshot(cache_log)
            and bool(_unexpected_console_errors(cache_log)),
            f"prior successful responses hid current HTTP status {invalid_status}",
        )
    cache_current_request["response_status"] = 200

    revisit_page = ContractPage(f"{FRONTEND_URL}/articles")
    revisit_log = ConsoleErrorLog()
    revisit_page_id = _page_identity(revisit_page)
    revisit_log._observed_pages[revisit_page_id] = "contract-revisit"
    for visit in range(3):
        revisit_expectation_id = revisit_log.declare_route_transition(
            page=revisit_page,
            destination_url=f"{FRONTEND_URL}/session",
        )
        anchor = revisit_log._event_sequence
        revisit_request = {
            **production_log.request_evidence["production-route-request"],
            "label": "contract-revisit",
            "page_id": revisit_page_id,
            "page_url": f"{FRONTEND_URL}/library" if visit == 2 else revisit_page.url,
            "navigation_generation": visit,
            "terminal_navigation_generation": visit + 1,
            "start_sequence": anchor + 2,
            "response_sequence": anchor + 3,
            "terminal_sequence": anchor + 4,
        }
        if visit == 2:
            revisit_log._page_navigation_events[revisit_page_id] = [{
                "sequence": anchor + 1,
                "generation": visit,
                "url": revisit_page.url,
                "monotonic": 1.0,
            }]
        revisit_log.request_evidence[f"revisit-{visit}"] = revisit_request
        revisit_log._event_sequence = anchor + 4
        revisit_page.url = f"{FRONTEND_URL}/session"
        revisit_log._page_navigation_generations[revisit_page_id] = visit + 1
        _require(
            _wait_for_exact_route_request_to_finish(
                revisit_page,
                revisit_log,
                source_url=revisit_page.url,
                after_sequence=anchor,
                expect_prefetch=False,
                require_observed_request=True,
                allow_response_backed_route_abort=True,
                cache_precursor_expectation_id=revisit_expectation_id,
            ) is revisit_request,
            "a prior completed navigation contaminated the current route waiter",
        )
        revisit_log.complete_route_transition(
            page=revisit_page,
            expectation_id=revisit_expectation_id,
        )
        _require(
            not _unexpected_console_errors(revisit_log),
            "separate ordinary route cancellations did not retain exact ownership",
        )
    revisit_log._page_navigation_events[revisit_page_id][0]["url"] = (
        f"{FRONTEND_URL}/unrelated"
    )
    _require(
        bool(_unexpected_console_errors(revisit_log)),
        "an unrelated pre-start event proved stale route ownership",
    )

    pending_page = ContractPage(f"{FRONTEND_URL}/articles")
    pending_log = ConsoleErrorLog()
    pending_page_id = _page_identity(pending_page)
    pending_log._observed_pages[pending_page_id] = "contract-pending"
    pending_expectation_id = pending_log.declare_route_transition(
        page=pending_page,
        destination_url=f"{FRONTEND_URL}/session",
    )
    pending_log.request_evidence["pending-route-request"] = {
        **production_log.request_evidence["production-route-request"],
        "label": "contract-pending",
        "page_id": pending_page_id,
        "page_url": f"{FRONTEND_URL}/articles",
        "frame_url_at_request": f"{FRONTEND_URL}/articles",
        "source_url": f"{FRONTEND_URL}/session?_rsc=pending",
        "start_sequence": 2,
        "response_sequence": 3,
        "terminal_sequence": None,
        "terminal_monotonic": None,
        "terminal_page_url": None,
        "terminal_navigation_generation": None,
        "response_status": 200,
        "response_url": f"{FRONTEND_URL}/session?_rsc=pending",
        "finished": False,
        "failure": None,
    }
    pending_page.url = f"{FRONTEND_URL}/session"
    try:
        pending_log.complete_route_transition(
            page=pending_page,
            expectation_id=pending_expectation_id,
        )
    except E2EFailure:
        pass
    else:
        raise E2EFailure(
            "production route lifecycle completed with a pending exact RSC request"
        )

    fragment_page = ContractPage(f"{FRONTEND_URL}/articles")
    fragment_log = ConsoleErrorLog()
    fragment_log._observed_pages[_page_identity(fragment_page)] = "contract-fragment"
    fragment_expectation_id = fragment_log.declare_route_transition(
        page=fragment_page,
        destination_url=f"{FRONTEND_URL}/articles#expected",
    )
    fragment_page.url = f"{FRONTEND_URL}/articles#wrong"
    try:
        fragment_log.complete_route_transition(
            page=fragment_page,
            expectation_id=fragment_expectation_id,
        )
    except E2EFailure:
        pass
    else:
        raise E2EFailure(
            "production route lifecycle accepted the wrong completion fragment"
        )

    framework_prefetch_url = f"{FRONTEND_URL}/articles?_rsc=contract"
    _require(
        not _unexpected_console_errors(
            lifecycle_log(
                source_url=framework_prefetch_url,
                rsc_request=True,
                next_router_prefetch=True,
            )
        ),
        "closed-page Next.js prefetch cancellation was not classified as teardown",
    )
    _require(
        not _unexpected_console_errors(
            lifecycle_log(
                source_url=framework_prefetch_url,
                failure=None,
                rsc_request=True,
                next_router_prefetch=True,
            )
        ),
        "closed-page unsettled Next.js prefetch was not classified as teardown",
    )
    _require(
        not _unexpected_console_errors(
            lifecycle_log(
                closed=False,
                source_url=framework_prefetch_url,
                rsc_request=True,
                next_router_prefetch=True,
            )
        ),
        "explicit Next.js prefetch cancellation was not classified",
    )
    _require(
        not _unexpected_console_errors(
            lifecycle_log(
                closed=False,
                source_url=framework_prefetch_url,
                response_status=200,
                rsc_request=True,
                next_router_prefetch=True,
            )
        ),
        "response-backed explicit Next.js prefetch cancellation was not classified",
    )
    contract_frontend_mode = ACTIVE_FRONTEND_MODE
    globals()["ACTIVE_FRONTEND_MODE"] = "dev"
    try:
        _require(
            not _trusted_next_build_manifests_available()
            and not _next_route_static_chunk_paths(framework_prefetch_url)
            and not _next_route_exclusive_static_chunk_paths(
                framework_prefetch_url
            ),
            "development mode trusted stale production build manifests",
        )
    finally:
        globals()["ACTIVE_FRONTEND_MODE"] = contract_frontend_mode
    production_build_manifest_available = _trusted_next_build_manifests_available()
    if production_build_manifest_available:
        dependent_prefetch_chunk = lifecycle_log(
            closed=False,
            source_url=framework_prefetch_url,
            rsc_request=True,
            next_router_prefetch=True,
        )
        article_prefetch_chunks = _next_route_exclusive_static_chunk_paths(
            framework_prefetch_url
        )
        tutor_only_chunks = _next_route_exclusive_static_chunk_paths(
            f"{FRONTEND_URL}/tutor?_rsc=contract"
        )
        _require(
            article_prefetch_chunks and tutor_only_chunks,
            "Next.js build manifest did not expose route-bound contract chunks",
        )
        dependent_prefetch_chunk.request_evidence["dependent-static-chunk"] = {
            **dependent_prefetch_chunk.request_evidence[
                "contract-lifecycle-request"
            ],
            "source_url": f"{FRONTEND_URL}{sorted(article_prefetch_chunks)[0]}",
            "resource_type": "script",
            "rsc_request": False,
            "next_router_prefetch": False,
            "start_sequence": 2,
            "start_monotonic": 1.05,
            "terminal_sequence": 3,
            "terminal_monotonic": 1.15,
        }
        _require(
            not _unexpected_console_errors(dependent_prefetch_chunk),
            "explicit Next.js prefetch did not own its exact static dependency",
        )
        shared_prefetch_chunks = _next_route_static_chunk_paths(
            framework_prefetch_url
        ) - article_prefetch_chunks
        _require(
            shared_prefetch_chunks,
            "Next.js build manifest did not expose a shared contract chunk",
        )
        shared_prefetch_chunk = lifecycle_log(
            closed=False,
            source_url=framework_prefetch_url,
            rsc_request=True,
            next_router_prefetch=True,
        )
        shared_prefetch_chunk.request_evidence["shared-static-chunk"] = {
            **shared_prefetch_chunk.request_evidence[
                "contract-lifecycle-request"
            ],
            "source_url": f"{FRONTEND_URL}{sorted(shared_prefetch_chunks)[0]}",
            "resource_type": "script",
            "rsc_request": False,
            "next_router_prefetch": False,
            "start_sequence": 2,
            "start_monotonic": 1.05,
            "terminal_sequence": 3,
            "terminal_monotonic": 1.15,
        }
        _require(
            bool(_unexpected_console_errors(shared_prefetch_chunk)),
            "shared Next.js chunk was falsely attributed to one route prefetch",
        )
    unrelated_prefetch_chunk = lifecycle_log(
        closed=False,
        source_url=framework_prefetch_url,
        rsc_request=True,
        next_router_prefetch=True,
    )
    unrelated_prefetch_chunk.request_evidence["unrelated-static-chunk"] = {
        **unrelated_prefetch_chunk.request_evidence["contract-lifecycle-request"],
        "source_url": (
            f"{FRONTEND_URL}/_next/static/chunks/"
            "p3-036-unrelated-contract.js"
        ),
        "resource_type": "script",
        "rsc_request": False,
        "next_router_prefetch": False,
        "start_sequence": 2,
        "start_monotonic": 1.05,
        "terminal_sequence": 3,
        "terminal_monotonic": 1.15,
    }
    undeclared_backend_route_cancellation = lifecycle_log(
        closed=False,
        terminal_page_url=f"{FRONTEND_URL}/session",
        terminal_navigation_generation=2,
    )
    following_navigation = lifecycle_log(closed=False)
    following_navigation._page_navigation_events["contract-lifecycle-page"] = [
        {
            "sequence": 5,
            "generation": 2,
            "url": f"{FRONTEND_URL}/session",
            "monotonic": 1.3,
        }
    ]
    same_url_rsc_navigation = lifecycle_log(
        closed=False,
        source_url=framework_prefetch_url,
        response_status=200,
        rsc_request=True,
        terminal_navigation_generation=1,
    )
    same_url_rsc_navigation._page_navigation_events[
        "contract-lifecycle-page"
    ] = [
        {
            "sequence": 5,
            "generation": 2,
            "url": f"{FRONTEND_URL}/articles",
            "monotonic": 1.3,
        }
    ]
    preterminal_route_supersession = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/session?_rsc=contract",
        response_status=200,
        rsc_request=True,
        terminal_page_url=f"{FRONTEND_URL}/articles",
        terminal_navigation_generation=2,
    )
    preterminal_route_supersession._page_navigation_events[
        "contract-lifecycle-page"
    ] = [
        {
            "sequence": 3,
            "generation": 2,
            "url": f"{FRONTEND_URL}/articles",
            "monotonic": 1.15,
        }
    ]
    declared_query_transition = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?q=changed&_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        declared_query_transition,
        destination_url=f"{FRONTEND_URL}/articles?q=changed",
    )
    _require(
        not _unexpected_console_errors(declared_query_transition),
        "declared same-path RSC transition was not classified",
    )
    declared_source_route_transition = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        declared_source_route_transition,
        destination_url=f"{FRONTEND_URL}/session",
    )
    _require(
        not _unexpected_console_errors(declared_source_route_transition),
        "declared source-route RSC cancellation was not classified",
    )
    event_bound_stale_page_route = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/session?_rsc=contract",
        response_status=200,
        rsc_request=True,
        start_sequence=2,
        navigation_generation=1,
    )
    add_completed_route_expectation(
        event_bound_stale_page_route,
        destination_url=f"{FRONTEND_URL}/session",
    )
    event_bound_expectation = event_bound_stale_page_route.route_transition_expectations[0]
    event_bound_expectation["request_page_url"] = f"{FRONTEND_URL}/articles"
    event_bound_evidence = event_bound_stale_page_route.request_evidence[
        "contract-lifecycle-request"
    ]
    event_bound_evidence["page_url"] = f"{FRONTEND_URL}/library"
    event_bound_evidence["frame_url_at_request"] = f"{FRONTEND_URL}/library"
    event_bound_evidence["response_sequence"] = 3
    event_bound_stale_page_route._page_navigation_events[
        "contract-lifecycle-page"
    ] = [
        {
            "sequence": 1,
            "generation": 1,
            "url": f"{FRONTEND_URL}/articles",
            "monotonic": 0.9,
        }
    ]
    _require(
        _route_transition_request_kind(
            event_bound_stale_page_route,
            event_bound_expectation,
            event_bound_evidence,
        )
        == "route"
        and not _unexpected_console_errors(event_bound_stale_page_route),
        "an exact sequence-bounded navigation event did not recover a stale page URL",
    )

    def post_terminal_stale_page_route(
        *,
        event_generation: int = 2,
        event_sequence: int = 5,
        event_monotonic: float = 1.3,
        event_url: str = f"{FRONTEND_URL}/session",
        source_url: str = f"{FRONTEND_URL}/session?_rsc=contract",
        duplicate_event: bool = False,
        completion_sequence: int | None = None,
        terminal_sequence: int = 4,
        bind_request: bool = True,
        complete_transition: bool = True,
    ) -> tuple[ConsoleErrorLog, dict[str, object], dict[str, object]]:
        log = lifecycle_log(
            closed=False,
            source_url=source_url,
            response_status=200,
            rsc_request=True,
            start_sequence=2,
            navigation_generation=1,
        )
        add_completed_route_expectation(
            log,
            destination_url=f"{FRONTEND_URL}/session",
        )
        expectation = log.route_transition_expectations[0]
        expectation["request_page_url"] = f"{FRONTEND_URL}/articles"
        expectation["allow_post_terminal_destination_commit"] = True
        expectation["declaration_navigation_generation"] = 1
        planned_completion_sequence = (
            completion_sequence
            if completion_sequence is not None
            else 7 if duplicate_event else 6
        )
        expectation["completion_sequence"] = None
        expectation["completion_url"] = None
        expectation["completion_navigation_generation"] = None
        expectation["bound_request_ids"] = None
        evidence = log.request_evidence["contract-lifecycle-request"]
        evidence["page_url"] = f"{FRONTEND_URL}/library"
        evidence["frame_url_at_request"] = f"{FRONTEND_URL}/library"
        evidence["response_sequence"] = 3
        evidence["terminal_sequence"] = terminal_sequence
        evidence["terminal_page_url"] = f"{FRONTEND_URL}/library"
        evidence["terminal_navigation_generation"] = 1
        events = [
            {
                "sequence": event_sequence,
                "generation": event_generation,
                "url": event_url,
                "monotonic": event_monotonic,
            }
        ]
        if duplicate_event:
            events.append(
                {
                    "sequence": 6,
                    "generation": 3,
                    "url": f"{FRONTEND_URL}/session",
                    "monotonic": 1.4,
                }
            )
        log._page_navigation_events["contract-lifecycle-page"] = events
        if bind_request:
            log.bind_post_terminal_destination_request(
                expectation_id=str(expectation["expectation_id"]),
                evidence=evidence,
            )
        if complete_transition:
            expectation["completion_sequence"] = planned_completion_sequence
            expectation["completion_url"] = f"{FRONTEND_URL}/session"
            expectation["completion_navigation_generation"] = 2
            expectation["bound_request_ids"] = (
                ("contract-lifecycle-request",) if bind_request else ()
            )
        log._event_sequence = planned_completion_sequence
        return log, expectation, evidence

    def altered_post_terminal_route(
        *,
        expectation_updates: dict[str, object] | None = None,
        evidence_updates: dict[str, object] | None = None,
        **options,
    ) -> tuple[ConsoleErrorLog, dict[str, object], dict[str, object]]:
        log, expectation, evidence = post_terminal_stale_page_route(**options)
        expectation.update(expectation_updates or {})
        evidence.update(evidence_updates or {})
        return log, expectation, evidence

    post_terminal_route, post_terminal_expectation, post_terminal_evidence = (
        post_terminal_stale_page_route()
    )
    _require(
        _route_transition_request_kind(
            post_terminal_route,
            post_terminal_expectation,
            post_terminal_evidence,
        )
        == "route"
        and not _unexpected_console_errors(post_terminal_route),
        "an exact next-generation destination commit did not recover a stale page URL",
    )

    prefetch_history_route = post_terminal_stale_page_route()
    prefetch_history_route[0].request_evidence["earlier-prefetch-abort"] = {
        **prefetch_history_route[2],
        "source_url": f"{FRONTEND_URL}/session?_rsc=earlier-prefetch",
        "response_url": f"{FRONTEND_URL}/session?_rsc=earlier-prefetch",
        "next_router_prefetch": True,
        "start_sequence": -3,
        "response_sequence": -2,
        "terminal_sequence": -1,
        "start_monotonic": 0.1,
        "terminal_monotonic": 0.2,
    }
    _require(
        not _unexpected_console_errors(prefetch_history_route[0])
        and len(_framework_prefetch_cancellations(prefetch_history_route[0])) == 1,
        "independently valid prefetch cancellation contaminated later route evidence",
    )
    prefetch_history_route[0].request_evidence["earlier-prefetch-abort"][
        "response_status"
    ] = 500
    _require(
        bool(_unexpected_console_errors(prefetch_history_route[0])),
        "an earlier failed prefetch was hidden by a later route transition",
    )

    route_with_precursors = post_terminal_stale_page_route(
        event_sequence=9,
        event_monotonic=1.4,
        completion_sequence=10,
        terminal_sequence=8,
    )
    route_with_precursors[1]["declaration_sequence"] = 4
    route_with_precursors[1]["allow_complete_precursor_snapshot"] = True
    route_with_precursors[1]["cache_precursor_request_ids"] = (
        "contract-route-older-cache-precursor",
        "contract-route-cache-precursor",
    )
    route_with_precursors[2].update(
        {
            "start_sequence": 5,
            "response_sequence": 6,
            "terminal_sequence": 8,
            "terminal_monotonic": 1.3,
        }
    )
    route_with_precursors[0].request_evidence[
        "contract-route-cache-precursor"
    ] = {
        **route_with_precursors[2],
        "source_url": f"{FRONTEND_URL}/session?_rsc=cache-precursor",
        "navigation_generation": 0,
        "start_sequence": 1,
        "start_monotonic": 0.8,
        "response_sequence": 2,
        "response_monotonic": 0.85,
        "terminal_sequence": 3,
        "terminal_monotonic": 0.9,
        "terminal_navigation_generation": 0,
        "response_status": 200,
        "response_url": f"{FRONTEND_URL}/session?_rsc=cache-precursor",
        "finished": True,
        "failure": None,
    }
    route_with_precursors[0].request_evidence[
        "contract-route-older-cache-precursor"
    ] = {
        **route_with_precursors[0].request_evidence[
            "contract-route-cache-precursor"
        ],
        "source_url": f"{FRONTEND_URL}/session?_rsc=older-cache-precursor",
        "start_sequence": -2,
        "response_sequence": -1,
        "terminal_sequence": 0,
        "response_url": f"{FRONTEND_URL}/session?_rsc=older-cache-precursor",
    }
    _require(
        _route_transition_request_kind(
            route_with_precursors[0],
            route_with_precursors[1],
            route_with_precursors[2],
        )
        == "route_with_complete_precursor_snapshot"
        and not _unexpected_console_errors(route_with_precursors[0])
        and len(_route_cancellations_with_complete_precursor_snapshot(route_with_precursors[0])) == 1,
        "an explicitly predeclared precursor snapshot route lifecycle did not reconcile",
    )

    terminal_candidate_route_key = _route_document_key(f"{FRONTEND_URL}/session")
    terminal_success = {
        **post_terminal_evidence,
        "finished": True,
        "failure": None,
    }
    terminal_abort = {**post_terminal_evidence}
    terminal_prefetch_success = {
        **terminal_success,
        "next_router_prefetch": True,
    }
    terminal_pending = {
        **post_terminal_evidence,
        "response_sequence": None,
        "response_status": None,
        "response_url": None,
        "terminal_sequence": None,
        "terminal_monotonic": None,
        "finished": False,
        "failure": None,
    }
    _require(
        _select_exact_route_request_terminal_candidate(
            [terminal_success],
            allow_response_backed_route_abort=True,
            route_key=terminal_candidate_route_key,
            current_page_url=f"{FRONTEND_URL}/session",
            current_navigation_generation=2,
        )
        is terminal_success,
        "a single successful exact route lifecycle was not selected",
    )
    _require(
        _select_exact_route_request_terminal_candidate(
            [terminal_abort],
            allow_response_backed_route_abort=True,
            route_key=terminal_candidate_route_key,
            current_page_url=f"{FRONTEND_URL}/session",
            current_navigation_generation=2,
        )
        is terminal_abort,
        "a single exact response-backed route abort was not selected",
    )
    _require(
        _select_exact_route_request_terminal_candidate(
            [terminal_success, terminal_pending],
            allow_response_backed_route_abort=True,
            route_key=terminal_candidate_route_key,
            current_page_url=f"{FRONTEND_URL}/session",
            current_navigation_generation=2,
        )
        is None,
        "a pending exact route lifecycle was resolved prematurely",
    )
    _require_unambiguous_response_backed_route_abort(
        terminal_success,
        [terminal_prefetch_success, terminal_success],
        source_url=f"{FRONTEND_URL}/session",
    )
    second_terminal_precursor = {
        **terminal_prefetch_success,
        "source_url": f"{FRONTEND_URL}/session?_rsc=second-precursor",
        "response_url": f"{FRONTEND_URL}/session?_rsc=second-precursor",
    }
    _require_unambiguous_response_backed_route_abort(
        terminal_abort,
        [terminal_prefetch_success, second_terminal_precursor, terminal_abort],
        source_url=f"{FRONTEND_URL}/session",
        cache_precursor_evidences=(
            terminal_prefetch_success,
            second_terminal_precursor,
        ),
    )

    def require_terminal_candidate_set_rejected(
        candidates: list[dict[str, object]],
        *,
        label: str,
    ) -> None:
        try:
            _select_exact_route_request_terminal_candidate(
                candidates,
                allow_response_backed_route_abort=True,
                route_key=terminal_candidate_route_key,
                current_page_url=f"{FRONTEND_URL}/session",
                current_navigation_generation=2,
            )
        except E2EFailure:
            return
        raise E2EFailure(f"exact route terminal selection accepted {label}")

    require_terminal_candidate_set_rejected(
        [terminal_success, terminal_abort],
        label="success followed by abort",
    )
    require_terminal_candidate_set_rejected(
        [terminal_abort, terminal_success],
        label="abort followed by success",
    )
    require_terminal_candidate_set_rejected(
        [terminal_prefetch_success, terminal_abort],
        label="successful prefetch followed by abort",
    )
    try:
        _require_unambiguous_response_backed_route_abort(
            terminal_abort,
            [terminal_prefetch_success, terminal_abort],
            source_url=f"{FRONTEND_URL}/session",
        )
    except E2EFailure:
        pass
    else:
        raise E2EFailure(
            "a successful prefetch laundered a response-backed route abort"
        )

    def require_post_terminal_binding_rejected(
        log: ConsoleErrorLog,
        *,
        expectation_id: str,
        evidence: dict[str, object],
        label: str,
    ) -> None:
        try:
            log.bind_post_terminal_destination_request(
                expectation_id=expectation_id,
                evidence=evidence,
            )
        except E2EFailure:
            return
        raise E2EFailure(f"post-terminal request binding accepted {label}")

    duplicate_binding_route = post_terminal_stale_page_route(
        complete_transition=False
    )
    require_post_terminal_binding_rejected(
        duplicate_binding_route[0],
        expectation_id=str(duplicate_binding_route[1]["expectation_id"]),
        evidence=duplicate_binding_route[2],
        label="a duplicate binding",
    )
    foreign_binding_route = post_terminal_stale_page_route(
        bind_request=False,
        complete_transition=False,
    )
    require_post_terminal_binding_rejected(
        foreign_binding_route[0],
        expectation_id=str(foreign_binding_route[1]["expectation_id"]),
        evidence={**foreign_binding_route[2]},
        label="foreign evidence",
    )
    completed_binding_route = post_terminal_stale_page_route(bind_request=False)
    require_post_terminal_binding_rejected(
        completed_binding_route[0],
        expectation_id=str(completed_binding_route[1]["expectation_id"]),
        evidence=completed_binding_route[2],
        label="a completed expectation",
    )
    cross_expectation_binding_route = post_terminal_stale_page_route(
        complete_transition=False
    )
    cross_expectation_binding_route[0].route_transition_expectations.append(
        {
            **cross_expectation_binding_route[1],
            "expectation_id": "contract-route-cross-binding",
            "declaration_sequence": 1,
            "completion_sequence": None,
            "completion_url": None,
            "completion_navigation_generation": None,
            "bound_request_ids": None,
            "post_terminal_request_id": None,
        }
    )
    require_post_terminal_binding_rejected(
        cross_expectation_binding_route[0],
        expectation_id="contract-route-cross-binding",
        evidence=cross_expectation_binding_route[2],
        label="one request across two expectations",
    )

    unrelated_other_page_activity = post_terminal_stale_page_route(
        event_sequence=8,
        completion_sequence=9,
    )
    unrelated_other_page_activity[0].request_evidence["other-page-request"] = {
        **unrelated_other_page_activity[2],
        "label": "other-page",
        "page_id": "other-page-id",
        "page_url": f"{FRONTEND_URL}/articles",
        "frame_url_at_request": f"{FRONTEND_URL}/articles",
        "source_url": f"{FRONTEND_URL}/articles?_rsc=other",
        "start_sequence": 5,
        "response_sequence": 6,
        "terminal_sequence": 7,
        "response_status": 200,
        "response_url": f"{FRONTEND_URL}/articles?_rsc=other",
        "finished": True,
        "failure": None,
    }
    _require(
        _route_transition_request_kind(
            unrelated_other_page_activity[0],
            unrelated_other_page_activity[1],
            unrelated_other_page_activity[2],
        )
        == "route",
        "unrelated other-page activity invalidated an exact destination commit",
    )

    competing_declaration_route = post_terminal_stale_page_route(
        event_sequence=6,
        completion_sequence=7,
        terminal_sequence=5,
    )
    competing_declaration_route[0].route_transition_expectations.append(
        {
            **competing_declaration_route[1],
            "expectation_id": "contract-route-2",
            "declaration_sequence": 4,
            "completion_sequence": None,
            "completion_url": None,
            "completion_navigation_generation": None,
            "bound_request_ids": None,
            "post_terminal_request_id": None,
        }
    )
    competing_request_route = post_terminal_stale_page_route(
        event_sequence=8,
        completion_sequence=9,
        terminal_sequence=7,
    )
    competing_request_route[0].request_evidence["competing-destination-request"] = {
        **competing_request_route[2],
        "start_sequence": 4,
        "response_sequence": 5,
        "terminal_sequence": 6,
        "terminal_monotonic": 1.15,
        "response_status": 200,
        "response_url": f"{FRONTEND_URL}/session?_rsc=retry",
        "source_url": f"{FRONTEND_URL}/session?_rsc=retry",
        "finished": True,
        "failure": None,
    }
    competing_prefetch_route = post_terminal_stale_page_route(
        event_sequence=9,
        event_monotonic=1.4,
        completion_sequence=10,
        terminal_sequence=8,
    )
    competing_prefetch_route[2].update(
        {
            "start_sequence": 5,
            "response_sequence": 6,
            "terminal_sequence": 8,
            "terminal_monotonic": 1.3,
        }
    )
    competing_prefetch_route[0].request_evidence[
        "competing-destination-prefetch"
    ] = {
        **competing_prefetch_route[2],
        "source_url": f"{FRONTEND_URL}/session?_rsc=prefetch",
        "next_router_prefetch": True,
        "start_sequence": 2,
        "start_monotonic": 1.0,
        "response_sequence": 3,
        "response_monotonic": 1.05,
        "terminal_sequence": 4,
        "terminal_monotonic": 1.1,
        "response_status": 200,
        "response_url": f"{FRONTEND_URL}/session?_rsc=prefetch",
        "finished": True,
        "failure": None,
    }
    predeclaration_prefetch_route = post_terminal_stale_page_route(
        event_sequence=9,
        event_monotonic=1.4,
        completion_sequence=10,
        terminal_sequence=8,
    )
    predeclaration_prefetch_route[1]["declaration_sequence"] = 4
    predeclaration_prefetch_route[2].update(
        {
            "start_sequence": 5,
            "response_sequence": 6,
            "terminal_sequence": 8,
            "terminal_monotonic": 1.3,
        }
    )
    predeclaration_prefetch_route[0].request_evidence[
        "predeclaration-destination-prefetch"
    ] = {
        **predeclaration_prefetch_route[2],
        "source_url": f"{FRONTEND_URL}/session?_rsc=predeclared-prefetch",
        "next_router_prefetch": True,
        "navigation_generation": 0,
        "start_sequence": 1,
        "start_monotonic": 0.8,
        "response_sequence": 2,
        "response_monotonic": 0.85,
        "terminal_sequence": 3,
        "terminal_monotonic": 0.9,
        "terminal_navigation_generation": 0,
        "response_status": 200,
        "response_url": f"{FRONTEND_URL}/session?_rsc=predeclared-prefetch",
        "finished": True,
        "failure": None,
    }

    invalid_post_terminal_routes = (
        (
            "allowed-source-but-delayed-navigation",
            altered_post_terminal_route(
                event_monotonic=1.6,
                evidence_updates={"page_url": f"{FRONTEND_URL}/articles"},
            ),
        ),
        (
            "allowed-source-but-duplicate-navigation",
            altered_post_terminal_route(
                duplicate_event=True,
                evidence_updates={"page_url": f"{FRONTEND_URL}/articles"},
            ),
        ),
        ("wrong-generation", post_terminal_stale_page_route(event_generation=1)),
        ("generation-plus-two", post_terminal_stale_page_route(event_generation=3)),
        ("before-terminal", post_terminal_stale_page_route(event_sequence=3)),
        ("at-terminal", post_terminal_stale_page_route(event_sequence=4)),
        (
            "delayed-cached-navigation",
            post_terminal_stale_page_route(
                event_monotonic=1.6,
            ),
        ),
        ("at-completion", post_terminal_stale_page_route(event_sequence=6)),
        (
            "wrong-destination",
            post_terminal_stale_page_route(event_url=f"{FRONTEND_URL}/articles"),
        ),
        (
            "wrong-fragment",
            post_terminal_stale_page_route(
                event_url=f"{FRONTEND_URL}/session#unrelated"
            ),
        ),
        (
            "non-destination-request",
            altered_post_terminal_route(
                evidence_updates={
                    "source_url": f"{FRONTEND_URL}/articles?_rsc=contract",
                    "response_url": f"{FRONTEND_URL}/articles?_rsc=contract",
                }
            ),
        ),
        ("duplicate-destination-events", post_terminal_stale_page_route(duplicate_event=True)),
        (
            "missing-response",
            altered_post_terminal_route(
                evidence_updates={
                    "response_sequence": None,
                    "response_status": None,
                    "response_url": None,
                }
            ),
        ),
        (
            "non-200-response",
            altered_post_terminal_route(
                evidence_updates={"response_status": 201}
            ),
        ),
        (
            "mismatched-response-url",
            altered_post_terminal_route(
                evidence_updates={"response_url": f"{FRONTEND_URL}/wrong"}
            ),
        ),
        (
            "invalid-response-sequence",
            altered_post_terminal_route(
                evidence_updates={"response_sequence": 2}
            ),
        ),
        (
            "declaration-generation-mismatch",
            altered_post_terminal_route(
                expectation_updates={"declaration_navigation_generation": 0}
            ),
        ),
        (
            "terminal-generation-mismatch",
            altered_post_terminal_route(
                evidence_updates={"terminal_navigation_generation": 2}
            ),
        ),
        (
            "completion-generation-mismatch",
            altered_post_terminal_route(
                expectation_updates={"completion_navigation_generation": 3}
            ),
        ),
        (
            "not-explicitly-enabled",
            altered_post_terminal_route(
                expectation_updates={
                    "allow_post_terminal_destination_commit": False
                }
            ),
        ),
        (
            "prefetch-request",
            altered_post_terminal_route(
                evidence_updates={"next_router_prefetch": True}
            ),
        ),
        ("competing-route-declaration", competing_declaration_route),
        ("competing-destination-request", competing_request_route),
        ("competing-destination-prefetch", competing_prefetch_route),
        (
            "predeclaration-destination-prefetch",
            predeclaration_prefetch_route,
        ),
    )
    for case_label, (
        invalid_post_terminal_route,
        invalid_post_terminal_expectation,
        invalid_post_terminal_evidence,
    ) in invalid_post_terminal_routes:
        _require(
            _route_transition_request_kind(
                invalid_post_terminal_route,
                invalid_post_terminal_expectation,
                invalid_post_terminal_evidence,
            )
            is None
            and bool(_unexpected_console_errors(invalid_post_terminal_route)),
            "invalid post-terminal navigation evidence bound a stale route request: "
            f"{case_label}",
        )

    unrelated_same_generation_route = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/session?_rsc=contract",
        response_status=200,
        rsc_request=True,
        start_sequence=2,
        navigation_generation=1,
    )
    add_completed_route_expectation(
        unrelated_same_generation_route,
        destination_url=f"{FRONTEND_URL}/session",
    )
    unrelated_expectation = unrelated_same_generation_route.route_transition_expectations[0]
    unrelated_expectation["request_page_url"] = f"{FRONTEND_URL}/articles"
    unrelated_evidence = unrelated_same_generation_route.request_evidence[
        "contract-lifecycle-request"
    ]
    unrelated_evidence["page_url"] = f"{FRONTEND_URL}/library"
    unrelated_evidence["frame_url_at_request"] = f"{FRONTEND_URL}/library"
    unrelated_same_generation_route._page_navigation_events[
        "contract-lifecycle-page"
    ] = [
        {
            "sequence": 1,
            "generation": 1,
            "url": f"{FRONTEND_URL}/library",
            "monotonic": 0.9,
        }
    ]
    _require(
        _route_transition_request_kind(
            unrelated_same_generation_route,
            unrelated_expectation,
            unrelated_evidence,
        )
        is None
        and bool(_unexpected_console_errors(unrelated_same_generation_route)),
        "same-generation evidence from an unrelated page bound a route request",
    )
    for case_label, event_generation, event_sequence in (
        ("wrong-generation", 2, 1),
        ("before-declaration", 1, -1),
        ("at-declaration", 1, 0),
        ("at-request-start", 1, 2),
        ("after-request-start", 1, 3),
    ):
        invalid_event_route = lifecycle_log(
            closed=False,
            source_url=f"{FRONTEND_URL}/session?_rsc=contract",
            response_status=200,
            rsc_request=True,
            start_sequence=2,
            navigation_generation=1,
        )
        add_completed_route_expectation(
            invalid_event_route,
            destination_url=f"{FRONTEND_URL}/session",
        )
        invalid_event_expectation = invalid_event_route.route_transition_expectations[0]
        invalid_event_expectation["request_page_url"] = f"{FRONTEND_URL}/articles"
        invalid_event_evidence = invalid_event_route.request_evidence[
            "contract-lifecycle-request"
        ]
        invalid_event_evidence["page_url"] = f"{FRONTEND_URL}/library"
        invalid_event_evidence["frame_url_at_request"] = f"{FRONTEND_URL}/library"
        invalid_event_evidence["response_sequence"] = 3
        invalid_event_route._page_navigation_events[
            "contract-lifecycle-page"
        ] = [
            {
                "sequence": event_sequence,
                "generation": event_generation,
                "url": f"{FRONTEND_URL}/articles",
                "monotonic": 0.9,
            }
        ]
        _require(
            _route_transition_request_kind(
                invalid_event_route,
                invalid_event_expectation,
                invalid_event_evidence,
            )
            is None
            and bool(_unexpected_console_errors(invalid_event_route)),
            "invalid navigation-event fallback bypassed generation or sequence bounds: "
            f"{case_label}",
        )
    duplicate_endpoint_route = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        duplicate_endpoint_route,
        destination_url=f"{FRONTEND_URL}/session",
    )
    duplicate_endpoint_expectation = (
        duplicate_endpoint_route.route_transition_expectations[0]
    )
    duplicate_endpoint_route.request_evidence["duplicate-route-request"] = {
        **duplicate_endpoint_route.request_evidence[
            "contract-lifecycle-request"
        ],
    }
    duplicate_endpoint_expectation["bound_request_ids"] = (
        "contract-lifecycle-request",
        "duplicate-route-request",
    )
    _require(
        bool(_unexpected_console_errors(duplicate_endpoint_route)),
        "one route transition accepted duplicate endpoint request bindings",
    )
    declared_superseded_route = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/session?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        declared_superseded_route,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    declared_superseded_route.route_transition_expectations[0][
        "cancelled_route_urls"
    ] = (f"{FRONTEND_URL}/session",)
    _require(
        not _unexpected_console_errors(declared_superseded_route),
        "explicitly declared superseded RSC route was not classified",
    )
    duplicate_declared_supersession = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/session?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        duplicate_declared_supersession,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    duplicate_expectation = (
        duplicate_declared_supersession.route_transition_expectations[0]
    )
    duplicate_expectation["cancelled_route_urls"] = (
        f"{FRONTEND_URL}/session",
    )
    duplicate_declared_supersession.request_evidence[
        "duplicate-cancelled-route-request"
    ] = {
        **duplicate_declared_supersession.request_evidence[
            "contract-lifecycle-request"
        ],
    }
    duplicate_expectation["bound_request_ids"] = (
        "contract-lifecycle-request",
        "duplicate-cancelled-route-request",
    )
    _require(
        bool(_unexpected_console_errors(duplicate_declared_supersession)),
        "one cancelled-route declaration accepted duplicate request bindings",
    )
    canonical_route_collision = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/session?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        canonical_route_collision,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    canonical_route_collision.route_transition_expectations[0][
        "cancelled_route_urls"
    ] = (
        f"{FRONTEND_URL}/session",
        f"{FRONTEND_URL}/session?_rsc=duplicate",
    )
    _require(
        bool(_unexpected_console_errors(canonical_route_collision)),
        "canonical duplicate cancelled-route identities were accepted",
    )
    canonical_read_url = (
        f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention"
    )
    canonical_read_collision = lifecycle_log(
        closed=False,
        source_url=canonical_read_url,
    )
    add_completed_route_expectation(
        canonical_read_collision,
        destination_url=(
            f"{FRONTEND_URL}/graph?node_id=article%3Aattention-basics"
        ),
    )
    canonical_read_collision.route_transition_expectations[0][
        "cancelled_read_urls"
    ] = (
        canonical_read_url,
        canonical_read_url.replace("localhost", "LOCALHOST"),
    )
    _require(
        bool(_unexpected_console_errors(canonical_read_collision)),
        "canonical duplicate cancelled-read identities were accepted",
    )
    cancelled_endpoint_no_op = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        cancelled_endpoint_no_op,
        destination_url=f"{FRONTEND_URL}/articles",
    )
    cancelled_endpoint_expectation = (
        cancelled_endpoint_no_op.route_transition_expectations[0]
    )
    cancelled_endpoint_expectation["cancelled_route_urls"] = (
        f"{FRONTEND_URL}/articles",
    )
    cancelled_endpoint_expectation["completion_navigation_generation"] = 0
    _require(
        bool(_unexpected_console_errors(cancelled_endpoint_no_op)),
        "no-op transition accepted an endpoint as its cancelled route",
    )
    long_response_prefetch = lifecycle_log(
        closed=False,
        source_url=framework_prefetch_url,
        response_status=200,
        rsc_request=True,
        next_router_prefetch=True,
    )
    long_response_prefetch.request_evidence["contract-lifecycle-request"][
        "terminal_monotonic"
    ] = 101.0
    _require(
        bool(_unexpected_console_errors(long_response_prefetch)),
        "long-lived response-backed prefetch cancellation bypassed its time bound",
    )
    declared_destination_frame_transition = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        declared_destination_frame_transition,
        destination_url=f"{FRONTEND_URL}/session",
    )
    declared_destination_frame_evidence = (
        declared_destination_frame_transition.request_evidence[
            "contract-lifecycle-request"
        ]
    )
    declared_destination_frame_evidence["page_url"] = f"{FRONTEND_URL}/session"
    declared_destination_frame_evidence["frame_url_at_request"] = (
        f"{FRONTEND_URL}/session"
    )
    _require(
        not _unexpected_console_errors(declared_destination_frame_transition),
        "declared RSC transition rejected destination-owned frame evidence",
    )
    if production_build_manifest_available:
        canonicalization_chunks = _next_route_exclusive_static_chunk_paths(
            f"{FRONTEND_URL}/articles?q=canonical"
        )
        _require(
            canonicalization_chunks,
            "Next.js build manifest did not expose canonicalization chunks",
        )
        declared_canonicalization_chunk = lifecycle_log(
            closed=False,
            source_url=f"{FRONTEND_URL}{sorted(canonicalization_chunks)[0]}",
            resource_type="script",
        )
        add_completed_route_expectation(
            declared_canonicalization_chunk,
            destination_url=f"{FRONTEND_URL}/articles?q=canonical",
            allow_speculative_cancellations=True,
        )
        _require(
            not _unexpected_console_errors(declared_canonicalization_chunk),
            "declared canonicalization did not classify its static-chunk cancellation",
        )
    declared_route_read = lifecycle_log(
        closed=False,
        source_url=f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention",
    )
    add_completed_route_expectation(
        declared_route_read,
        destination_url=f"{FRONTEND_URL}/graph?node_id=article%3Aattention-basics",
    )
    declared_route_read.route_transition_expectations[0][
        "cancelled_read_urls"
    ] = (f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention",)
    _require(
        not _unexpected_console_errors(declared_route_read),
        "declared route-owned read cancellation was not classified",
    )
    superseded_read = lifecycle_log(closed=False)
    superseded_read.request_evidence["contract-replacement-request"] = {
        **superseded_read.request_evidence["contract-lifecycle-request"],
        "route_intent_sequence": None,
        "start_sequence": 2,
        "start_monotonic": 1.05,
        "response_sequence": 3,
        "response_monotonic": 1.1,
        "terminal_sequence": 5,
        "terminal_monotonic": 1.3,
        "response_status": 200,
        "response_url": f"{BROWSER_API_URL}/learning/state",
        "finished": True,
        "failure": None,
    }
    _require(
        not _unexpected_console_errors(superseded_read),
        "aborted read with an exact successful replacement was not reconciled",
    )
    _require(
        not _unexpected_console_errors(
            lifecycle_log(
                source_url=f"{FRONTEND_URL}/_next/static/chunks/app/session/page.js",
                resource_type="script",
            )
        ),
        "Next.js static chunk cancellation was not classified",
    )
    _require(
        not _unexpected_console_errors(
            lifecycle_log(
                method="DELETE",
                response_status=204,
                declare_no_content=True,
            )
        ),
        "declared 204 mutation abort was not accepted as terminal evidence",
    )
    _require(
        not _unexpected_console_errors(
            lifecycle_log(
                method="DELETE",
                failure=None,
                finished=True,
                response_status=204,
                declare_no_content=True,
            )
        ),
        "declared completed 204 mutation was not accepted as terminal evidence",
    )

    mismatched_no_content = lifecycle_log(
        method="DELETE",
        response_status=204,
        declare_no_content=True,
    )
    mismatched_no_content.no_content_expectations[0]["source_url"] = (
        f"{BROWSER_API_URL}/wrong"
    )
    mismatched_response = lifecycle_log(response_status=200)
    mismatched_response.request_evidence[
        "contract-lifecycle-request"
    ]["response_url"] = f"{BROWSER_API_URL}/wrong"
    unbound_no_content = lifecycle_log(
        method="DELETE",
        response_status=204,
        declare_no_content=True,
    )
    unbound_no_content.no_content_expectations[0]["request_id"] = None
    unbound_no_content._expected_no_content_request_ids.clear()
    ambiguous_no_content = lifecycle_log(method="DELETE", response_status=204)
    ambiguous_actual = ambiguous_no_content.request_evidence[
        "contract-lifecycle-request"
    ]
    for index in (1, 2):
        ambiguous_no_content.no_content_expectations.append(
            {
                "expectation_id": f"ambiguous-no-content-{index}",
                "label": ambiguous_actual["label"],
                "page_id": ambiguous_actual["page_id"],
                "page_url": ambiguous_actual["page_url"],
                "source_url": ambiguous_actual["source_url"],
                "method": ambiguous_actual["method"],
                "request_id": None,
                "response_status": None,
                "response_url": None,
                "finished": False,
                "failure": None,
            }
        )
    ambiguous_no_content._bind_no_content_response(
        request_id="contract-lifecycle-request",
        actual=ambiguous_actual,
        response_url=str(ambiguous_actual["source_url"]),
    )
    query_only_prefetch = lifecycle_log(source_url=framework_prefetch_url)
    response_after_close_intent = lifecycle_log(response_status=200)
    response_after_close_intent.request_evidence[
        "contract-lifecycle-request"
    ]["response_sequence"] = 4
    terminal_before_close_intent = lifecycle_log(response_status=200)
    terminal_before_close_intent.request_evidence[
        "contract-lifecycle-request"
    ]["terminal_sequence"] = 2
    closed_without_close_intent = lifecycle_log(response_status=200)
    closed_without_close_intent._page_close_intent_sequences.clear()
    closed_after_response_headers = lifecycle_log(response_status=200)
    closed_with_unfinished_response = lifecycle_log(
        response_status=200,
        failure=None,
    )
    static_chunk_without_close_intent = lifecycle_log(
        source_url=f"{FRONTEND_URL}/_next/static/chunks/app/session/page.js",
        resource_type="script",
    )
    static_chunk_without_close_intent._page_close_intent_sequences.clear()
    following_same_url = lifecycle_log(closed=False)
    following_same_url._page_navigation_events["contract-lifecycle-page"] = [
        {
            "sequence": 5,
            "generation": 2,
            "url": f"{FRONTEND_URL}/articles",
        }
    ]
    following_navigation_after_new_work = lifecycle_log(closed=False)
    following_navigation_after_new_work._page_navigation_events[
        "contract-lifecycle-page"
    ] = [
        {
            "sequence": 6,
            "generation": 2,
            "url": f"{FRONTEND_URL}/session",
        }
    ]
    following_navigation_after_new_work.request_evidence["new-request"] = {
        **following_navigation_after_new_work.request_evidence[
            "contract-lifecycle-request"
        ],
        "start_sequence": 5,
        "response_sequence": None,
        "terminal_sequence": None,
        "response_status": None,
        "response_url": None,
        "finished": True,
        "failure": None,
    }
    query_only_terminal_transition = lifecycle_log(
        closed=False,
        terminal_page_url=f"{FRONTEND_URL}/articles?q=changed",
        terminal_navigation_generation=2,
    )
    retrospective_replacement = lifecycle_log(closed=False)
    retrospective_replacement.request_evidence["late-replacement"] = {
        **retrospective_replacement.request_evidence[
            "contract-lifecycle-request"
        ],
        "route_intent_sequence": None,
        "start_sequence": 5,
        "start_monotonic": 1.3,
        "response_sequence": 6,
        "response_monotonic": 1.4,
        "terminal_sequence": 7,
        "terminal_monotonic": 1.5,
        "response_status": 200,
        "response_url": f"{BROWSER_API_URL}/learning/state",
        "finished": True,
        "failure": None,
    }
    cross_route_replacement = lifecycle_log(closed=False)
    cross_route_replacement.request_evidence["cross-route-replacement"] = {
        **cross_route_replacement.request_evidence[
            "contract-lifecycle-request"
        ],
        "page_url": f"{FRONTEND_URL}/session",
        "frame_url_at_request": f"{FRONTEND_URL}/session",
        "navigation_generation": 2,
        "route_intent_sequence": None,
        "start_sequence": 2,
        "start_monotonic": 1.05,
        "response_sequence": 3,
        "response_monotonic": 1.1,
        "terminal_sequence": 5,
        "terminal_monotonic": 1.3,
        "response_status": 200,
        "response_url": f"{BROWSER_API_URL}/learning/state",
        "finished": True,
        "failure": None,
    }
    duplicate_abort_reconciliation = lifecycle_log(closed=False)
    duplicate_abort_reconciliation.request_evidence["second-aborted-request"] = {
        **duplicate_abort_reconciliation.request_evidence[
            "contract-lifecycle-request"
        ],
        "start_sequence": 2,
        "start_monotonic": 1.05,
        "response_sequence": None,
        "response_monotonic": None,
        "terminal_sequence": 5,
        "terminal_monotonic": 1.3,
    }
    duplicate_abort_reconciliation.request_evidence["single-replacement"] = {
        **duplicate_abort_reconciliation.request_evidence[
            "contract-lifecycle-request"
        ],
        "route_intent_sequence": None,
        "start_sequence": 3,
        "start_monotonic": 1.1,
        "response_sequence": 6,
        "response_monotonic": 1.4,
        "terminal_sequence": 7,
        "terminal_monotonic": 1.5,
        "response_status": 200,
        "response_url": f"{BROWSER_API_URL}/learning/state",
        "finished": True,
        "failure": None,
    }
    incomplete_route_expectation = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?q=changed&_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        incomplete_route_expectation,
        destination_url=f"{FRONTEND_URL}/articles?q=changed",
    )
    incomplete_route_expectation.route_transition_expectations[0][
        "completion_sequence"
    ] = None
    incomplete_route_expectation.route_transition_expectations[0][
        "completion_url"
    ] = None
    mismatched_route_expectation = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?q=changed&_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        mismatched_route_expectation,
        destination_url=f"{FRONTEND_URL}/articles?q=other",
    )
    late_route_termination = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?q=changed&_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        late_route_termination,
        destination_url=f"{FRONTEND_URL}/articles?q=changed",
    )
    late_route_termination.request_evidence["contract-lifecycle-request"][
        "terminal_sequence"
    ] = 6
    wrong_fragment_completion = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        wrong_fragment_completion,
        destination_url=f"{FRONTEND_URL}/articles#expected",
    )
    wrong_fragment_completion.route_transition_expectations[0][
        "completion_url"
    ] = f"{FRONTEND_URL}/articles#wrong"
    unrelated_route_expectation = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/tutor?_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        unrelated_route_expectation,
        destination_url=f"{FRONTEND_URL}/session",
    )
    mismatched_declared_read = lifecycle_log(
        closed=False,
        source_url=f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention",
    )
    add_completed_route_expectation(
        mismatched_declared_read,
        destination_url=f"{FRONTEND_URL}/graph?node_id=article%3Aattention-basics",
    )
    mismatched_declared_read.route_transition_expectations[0][
        "cancelled_read_urls"
    ] = (f"{BROWSER_API_URL}/graph/nodes/concept%3Acrb",)
    mismatched_backend_rsc_read = lifecycle_log(
        closed=False,
        source_url=(
            f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention?_rsc=actual"
        ),
    )
    add_completed_route_expectation(
        mismatched_backend_rsc_read,
        destination_url=f"{FRONTEND_URL}/graph?node_id=article%3Aattention-basics",
    )
    mismatched_backend_rsc_read.route_transition_expectations[0][
        "cancelled_read_urls"
    ] = (
        f"{BROWSER_API_URL}/graph/nodes/concept%3Aattention?_rsc=declared",
    )
    unrelated_static_chunk = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/_next/static/chunks/app/tutor/page.js",
        resource_type="script",
    )
    add_completed_route_expectation(
        unrelated_static_chunk,
        destination_url=f"{FRONTEND_URL}/articles?q=changed",
        allow_speculative_cancellations=True,
    )
    unbound_duplicate_route_request = lifecycle_log(
        closed=False,
        source_url=f"{FRONTEND_URL}/articles?q=changed&_rsc=contract",
        response_status=200,
        rsc_request=True,
    )
    add_completed_route_expectation(
        unbound_duplicate_route_request,
        destination_url=f"{FRONTEND_URL}/articles?q=changed",
    )
    unbound_duplicate_route_request.request_evidence["second-route-request"] = {
        **unbound_duplicate_route_request.request_evidence[
            "contract-lifecycle-request"
        ],
        "start_sequence": 2,
        "response_sequence": 3,
        "terminal_sequence": 4,
    }
    retrospective_no_content = lifecycle_log(
        method="DELETE",
        response_status=204,
        declare_no_content=True,
    )
    retrospective_no_content.no_content_expectations[0][
        "declaration_sequence"
    ] = 2
    lifecycle_negative_cases = (
        lifecycle_log(),
        lifecycle_log(failure=None),
        query_only_prefetch,
        lifecycle_log(source_url=framework_prefetch_url, closed=False),
        lifecycle_log(source_url=framework_prefetch_url, main_frame=False),
        lifecycle_log(
            source_url=framework_prefetch_url,
            service_worker_url="service-worker.js",
        ),
        lifecycle_log(failure="net::ERR_CONNECTION_REFUSED"),
        lifecycle_log(
            closed=False,
            terminal_page_url=f"{FRONTEND_URL}/articles",
            terminal_navigation_generation=1,
        ),
        lifecycle_log(response_status=503),
        mismatched_response,
        closed_after_response_headers,
        closed_with_unfinished_response,
        response_after_close_intent,
        terminal_before_close_intent,
        closed_without_close_intent,
        static_chunk_without_close_intent,
        following_navigation,
        following_same_url,
        following_navigation_after_new_work,
        unrelated_prefetch_chunk,
        undeclared_backend_route_cancellation,
        same_url_rsc_navigation,
        preterminal_route_supersession,
        query_only_terminal_transition,
        retrospective_replacement,
        cross_route_replacement,
        duplicate_abort_reconciliation,
        incomplete_route_expectation,
        mismatched_route_expectation,
        late_route_termination,
        wrong_fragment_completion,
        unrelated_route_expectation,
        mismatched_declared_read,
        mismatched_backend_rsc_read,
        unrelated_static_chunk,
        unbound_duplicate_route_request,
        lifecycle_log(method="DELETE", response_status=204),
        lifecycle_log(
            method="DELETE",
            failure=None,
            finished=True,
            response_status=204,
        ),
        lifecycle_log(method="DELETE", response_status=200),
        lifecycle_log(
            method="DELETE",
            failure="net::ERR_CONNECTION_REFUSED",
            response_status=204,
            declare_no_content=True,
        ),
        mismatched_no_content,
        unbound_no_content,
        ambiguous_no_content,
        retrospective_no_content,
    )
    _require(
        all(_unexpected_console_errors(case) for case in lifecycle_negative_cases),
        "request lifecycle policy accepted a mutation, live-page, transport, or HTTP failure",
    )

    _require(
        all(
            _is_allowed_http_url(url)
            for url in (
                FRONTEND_URL,
                BROWSER_API_URL,
                API_URL,
            )
        ),
        "local HTTP network allowlist rejected a product origin",
    )
    _require(
        all(
            not _is_allowed_http_url(url)
            for url in (
                "https://spaces.ac.cn/",
                "http://127.0.0.1:9000/",
                "http://localhost/articles",
                "http://localhost:3000/articles",
                "https://127.0.0.1:3000/articles",
                "http://[::1]:3000/articles",
                "http://user@127.0.0.1:3000/articles",
            )
        ),
        "HTTP network allowlist accepted a non-product origin",
    )
    _require(
        _is_allowed_websocket_url("ws://127.0.0.1:3000/socket")
        and not _is_allowed_websocket_url("wss://spaces.ac.cn/socket")
        and not _is_allowed_websocket_url("ws://127.0.0.1:9000/socket")
        and not _is_allowed_websocket_url("ws://localhost:3000/socket")
        and not _is_allowed_websocket_url("wss://127.0.0.1:3000/socket")
        and not _is_allowed_websocket_url("ws://user@127.0.0.1:3000/socket"),
        "WebSocket network allowlist did not enforce product origins",
    )
    _require(
        _network_url_key(f"{BROWSER_API_URL}/learning/state")
        != _network_url_key(f"{BROWSER_API_URL}/learning/state;unexpected")
        and _network_url_key(f"{BROWSER_API_URL}/learning/state?a=1&a=2")
        != _network_url_key(f"{BROWSER_API_URL}/learning/state?a=2&a=1")
        and _route_url_key(f"{FRONTEND_URL}/articles?_rsc=one&a=1&a=2")
        != _route_url_key(f"{FRONTEND_URL}/articles;unexpected?_rsc=two&a=1&a=2")
        and _route_url_key(f"{FRONTEND_URL}/articles?_rsc=one&a=1&a=2")
        != _route_url_key(f"{FRONTEND_URL}/articles?a=2&_rsc=two&a=1"),
        "network or route URL keys collapsed params or query ordering",
    )


def _reset_mutable_runtime(runtime: dict[str, Path | dict[str, str]]) -> None:
    Path(runtime["learning"]).unlink(missing_ok=True)
    Path(runtime["tutor"]).unlink(missing_ok=True)


def _require_box_inside(
    container: dict[str, float] | None,
    child: dict[str, float] | None,
    label: str,
    *,
    minimum_width: float,
    minimum_height: float,
) -> None:
    _require(container is not None and child is not None, f"{label} has no rendered geometry")
    assert container is not None and child is not None
    _require(
        child["width"] >= minimum_width
        and child["height"] >= minimum_height
        and child["x"] >= container["x"]
        and child["y"] >= container["y"]
        and child["x"] + child["width"] <= container["x"] + container["width"]
        and child["y"] + child["height"] <= container["y"] + container["height"],
        f"{label} is clipped or outside its canvas: container={container}, child={child}",
    )


def _require_viewport_intersection(
    box: dict[str, float] | None,
    viewport_width: int,
    viewport_height: int,
    label: str,
) -> None:
    _require(
        box is not None
        and box["x"] >= 0
        and box["x"] + box["width"] <= viewport_width
        and box["y"] < viewport_height
        and box["y"] + box["height"] > 0,
        f"{label} is clipped or outside the viewport: {box}",
    )


def _require_viewport_containment(
    box: dict[str, float] | None,
    viewport_width: int,
    viewport_height: int,
    label: str,
) -> None:
    _require(
        box is not None
        and box["x"] >= 0
        and box["x"] + box["width"] <= viewport_width
        and box["y"] >= 0
        and box["y"] + box["height"] <= viewport_height,
        f"{label} is clipped or outside the viewport: {box}",
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise E2EFailure(message)


def _require_port_free(port: int) -> None:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise E2EFailure(f"required local port {port} is already in use")


def _wait_for_url(
    url: str,
    process: subprocess.Popen[str],
    log_path: Path,
    *,
    timeout: int = 30,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise E2EFailure(
                f"server exited with {process.returncode}: {_bounded_log_summary(log_path)}"
            )
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError):
            pass
        time.sleep(0.25)
    raise E2EFailure(f"server did not become ready at {url}: {_bounded_log_summary(log_path)}")


def _stop_process(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            process.wait(timeout=5)


def _bounded_log_summary(path: Path, *, max_lines: int = 30) -> list[str]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [f"{type(exc).__name__}: {exc}"]
    return lines[-max_lines:]


if __name__ == "__main__":
    raise SystemExit(main())
