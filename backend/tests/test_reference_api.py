from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.rag.full_corpus import compute_corpus_fingerprint
from app.references.deduplication import build_reference_data
from app.references.extraction import extract_article_references
from app.references.matching import match_reference_records
from app.references.reader import clear_reference_reader_cache, public_candidate
from app.references.store import install_reference_store
from app.storage.article_store import StoredArticle
from app.zotero.models import ZoteroItem


def _article(article_id: str, title: str, content: str) -> StoredArticle:
    return StoredArticle(
        id=article_id,
        title=title,
        url=f"https://spaces.ac.cn/archives/{article_id.removeprefix('a')}",
        content=content,
        metadata={
            "date": "2026-07-01",
            "category": "fixture",
            "references": [],
            "images": [],
        },
    )


def _zotero_item(
    item_key: str,
    title: str,
    *,
    doi: str | None = None,
    url: str | None = None,
) -> ZoteroItem:
    return ZoteroItem(
        item_key=item_key,
        bibtex_key=None,
        title=title,
        creators=["Fixture Author"],
        year="2026",
        item_type="journalArticle",
        publication_title="Fixture Journal",
        doi=doi,
        url=url,
        abstract_note=None,
        tags=[],
        collections=[],
        updated_at=None,
    )


def _configured_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, Path, Path]:
    articles = [
        _article(
            "a1",
            "Attention source",
            (
                "# References\n\nDOI: 10.1000/example\n\nhttps://example.org/paper\n\n"
                + ("distant article body " * 300)
                + "PRIVATE-BODY-SENTINEL"
            ),
        ),
        _article(
            "a2",
            "Attention duplicate",
            "# Sources\n\ndoi:10.1000/example\n\narXiv:1706.03762v2",
        ),
        _article("a3", "No references", "# Notes\n\nThis Article has no structured reference."),
    ]
    article_path = tmp_path / "articles.json"
    article_path.write_text(
        json.dumps([item.to_dict() for item in articles], ensure_ascii=False),
        encoding="utf-8",
    )
    corpus_fingerprint = compute_corpus_fingerprint(articles)
    build_data = build_reference_data(
        [extract_article_references(item) for item in articles],
        corpus_fingerprint=corpus_fingerprint,
        build_id="reference-api-fixture-build",
    )
    candidates = match_reference_records(
        build_data.records,
        [
            _zotero_item("DOI1", "DOI fixture", doi="10.1000/example"),
            _zotero_item(
                "ARXIV1",
                "Attention Is All You Need",
                url="https://arxiv.org/abs/1706.03762v2",
            ),
        ],
    )
    store_path = tmp_path / ".local_data" / "scientific_spaces" / "references" / "full-corpus" / "current"
    install_reference_store(
        store_path,
        build_data=build_data,
        zotero_candidates=candidates.candidates,
        article_ids=[item.id for item in articles],
        corpus_fingerprint=corpus_fingerprint,
        configuration_fingerprint="reference-api-fixture-config",
        build_fingerprint="reference-api-fixture-build",
        source_asset_id="article-store:fixture",
        network_request_count=0,
        extra_counts={"silent_drops": 0},
    )
    monkeypatch.setenv("SCIENTIFIC_SPACES_REFERENCE_STORE", str(store_path))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_path))
    monkeypatch.delenv("SCIENTIFIC_SPACES_ARTICLE_STORE", raising=False)
    monkeypatch.delenv("SCIENTIFIC_SPACES_REFERENCE_CONFIGURATION_FINGERPRINT", raising=False)
    clear_reference_reader_cache()
    return TestClient(app), article_path, store_path


def test_reference_summary_is_valid_bounded_and_path_free(tmp_path: Path, monkeypatch) -> None:
    client, _, store_path = _configured_client(tmp_path, monkeypatch)
    manifest_path = store_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["private_debug_path"] = str(tmp_path / "private")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    clear_reference_reader_cache()

    response = client.get("/v1.2/reference-summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "valid"
    assert payload["counts"]["articles"] == 3
    assert payload["counts"]["records"] > 0
    assert payload["network_request_count"] == 0
    assert str(tmp_path) not in json.dumps(payload)
    assert "private_debug_path" not in payload["counts"]
    assert "rebuild_command" not in payload


def test_reference_list_supports_bounds_filters_query_and_pagination(tmp_path: Path, monkeypatch) -> None:
    client, _, _ = _configured_client(tmp_path, monkeypatch)

    doi_page = client.get(
        "/v1.2/references",
        params={"reference_type": "doi", "q": "10.1000", "page": 1, "page_size": 1},
    )
    invalid_size = client.get("/v1.2/references", params={"page_size": 101})
    long_query = client.get("/v1.2/references", params={"q": "x" * 201})

    assert doi_page.status_code == 200
    payload = doi_page.json()
    assert payload["total"] == 1
    assert payload["items"][0]["doi"] == "10.1000/example"
    assert payload["items"][0]["source_count"] == 2
    assert payload["query"] == "10.1000"
    assert "raw_reference" not in payload["items"][0]
    assert "evidence_ids" not in payload["items"][0]
    assert invalid_size.status_code == 422
    assert long_query.status_code == 422


def test_article_reference_page_handles_records_empty_and_unknown_article(tmp_path: Path, monkeypatch) -> None:
    client, _, _ = _configured_client(tmp_path, monkeypatch)

    populated = client.get("/v1.2/articles/a1/references")
    empty = client.get("/v1.2/articles/a3/references")
    unknown = client.get("/v1.2/articles/not-known/references")

    assert populated.status_code == 200
    assert populated.json()["article_id"] == "a1"
    assert populated.json()["total"] > 0
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total_pages"] == 0
    assert unknown.status_code == 404


def test_reference_detail_bounds_evidence_and_does_not_emit_article_body(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, _, _ = _configured_client(tmp_path, monkeypatch)
    doi_record = client.get("/v1.2/references", params={"reference_type": "doi"}).json()["items"][0]

    response = client.get(
        f"/v1.2/references/{doi_record['reference_id']}",
        params={"provenance_limit": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_total"] == 2
    assert len(payload["evidence"]) == 1
    assert payload["provenance_truncated"] is True
    assert "raw_reference" not in payload["evidence"][0]
    assert "raw_reference_hash" not in payload["evidence"][0]
    assert "PRIVATE-BODY-SENTINEL" not in json.dumps(payload)
    assert client.get(
        f"/v1.2/references/{doi_record['reference_id']}",
        params={"provenance_limit": 21},
    ).status_code == 422
    assert client.get(f"/v1.2/references/{'x' * 201}").status_code == 422


def test_zotero_candidates_are_read_only_bounded_and_filterable(tmp_path: Path, monkeypatch) -> None:
    client, _, _ = _configured_client(tmp_path, monkeypatch)
    doi_record = client.get("/v1.2/references", params={"reference_type": "doi"}).json()["items"][0]

    exact = client.get(
        f"/v1.2/references/{doi_record['reference_id']}/zotero-candidates",
        params={"decision": "exact", "limit": 1},
    )
    unmatched = client.get(
        f"/v1.2/references/{doi_record['reference_id']}/zotero-candidates",
        params={"decision": "unmatched"},
    )

    assert exact.status_code == 200
    assert exact.json()["total"] == 1
    assert exact.json()["items"][0]["decision"] == "exact"
    assert exact.json()["items"][0]["zotero_item_key"] == "DOI1"
    assert unmatched.status_code == 200
    assert unmatched.json()["items"] == []
    assert client.get(
        f"/v1.2/references/{doi_record['reference_id']}/zotero-candidates",
        params={"limit": 21},
    ).status_code == 422


def test_candidate_provenance_uses_a_bounded_field_allowlist() -> None:
    candidate = {
        "candidate_id": "candidate",
        "reference_id": "reference",
        "provenance": {
            "evidence_ids": [f"evidence-{index}" for index in range(25)],
            "matcher_version": "matcher/v1",
            "private_debug_path": "/home/private/library",
        },
    }

    payload = public_candidate(candidate)

    assert payload["provenance"] == {
        "evidence_ids": [f"evidence-{index}" for index in range(20)],
        "matcher_version": "matcher/v1",
    }
    assert "private_debug_path" not in json.dumps(payload)


def test_reference_api_returns_bounded_503_for_missing_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_REFERENCE_STORE", str(tmp_path / "missing"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(tmp_path / "missing-articles.json"))
    clear_reference_reader_cache()

    response = TestClient(app).get("/v1.2/reference-summary")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "reference_store_missing",
        "state": "missing",
        "message": "Reference Store is not configured or is unavailable",
    }
    assert str(tmp_path) not in response.text


def test_reference_api_fails_closed_for_stale_store(tmp_path: Path, monkeypatch) -> None:
    client, article_path, _ = _configured_client(tmp_path, monkeypatch)
    articles: list[dict[str, Any]] = json.loads(article_path.read_text(encoding="utf-8"))
    articles[0]["content"] += "\nchanged after reference build"
    article_path.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
    clear_reference_reader_cache()

    response = client.get("/v1.2/reference-summary")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "reference_store_stale"
    assert response.json()["detail"]["state"] == "stale"


def test_reference_api_fails_closed_for_corrupt_store(tmp_path: Path, monkeypatch) -> None:
    client, _, store_path = _configured_client(tmp_path, monkeypatch)
    with (store_path / "records.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")
    clear_reference_reader_cache()

    response = client.get("/v1.2/reference-summary")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "reference_store_corrupt"
    assert response.json()["detail"]["state"] == "corrupt"


def test_reference_openapi_is_additive_and_preserves_legacy_article_contract() -> None:
    schema = app.openapi()

    assert {
        "/v1.2/references",
        "/v1.2/references/{reference_id}",
        "/v1.2/articles/{article_id}/references",
        "/v1.2/references/{reference_id}/zotero-candidates",
        "/v1.2/reference-summary",
    } <= set(schema["paths"])
    legacy_parameters = [item["name"] for item in schema["paths"]["/articles"]["get"]["parameters"]]
    versioned_parameters = [
        item["name"] for item in schema["paths"]["/v1.1/articles"]["get"]["parameters"]
    ]
    assert legacy_parameters == ["q"]
    assert versioned_parameters == ["q", "page", "page_size", "category", "sort"]
