from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def make_local_data_root(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "scientific_spaces"
    article_path = root / "corpus/pilot/article_store/articles.json"
    articles = [
        {
            "id": "a1",
            "title": "Attention 入门",
            "url": "https://spaces.ac.cn/archives/1",
            "content": "# Attention\n\n正文 $qk^T$。",
            "metadata": {
                "date": "2025-01-01",
                "category": "机器学习",
                "references": ["https://example.test/paper"],
                "images": [],
            },
        },
        {
            "id": "a2",
            "title": "CRB",
            "url": "https://spaces.ac.cn/archives/2",
            "content": "# CRB\n\n正文 $$I(\\theta)^{-1}$$。",
            "metadata": {
                "date": "2025-01-02",
                "category": "统计",
                "references": [],
                "images": ["https://example.test/image.png"],
            },
        },
    ]
    write_json(article_path, articles)
    corpus_fingerprint = compute_corpus_fingerprint(load_full_corpus_articles(article_path))

    write_json(
        root / "corpus/pilot/completion_classifications.json",
        {"classifications": {"3": {"reason": "non-importable"}}},
    )
    write_json(root / "corpus/pilot/progress.json", {"completed": ["1", "2"]})
    (root / "corpus/pilot/failed_urls.jsonl").write_text("", encoding="utf-8")
    write_json(root / "corpus/pilot/validation_summary.json", {"status": "PASS"})

    write_json(
        root / "learning.json",
        {
            "states": {"a1": {"article_id": "a1", "status": "reading"}},
            "bookmarks": {"a1": {"article_id": "a1"}},
            "notes": {"n1": {"note_id": "n1", "content": "private-note-body"}},
            "sessions": {"s1": {"session_id": "s1"}},
        },
    )
    write_json(
        root / "zotero_links.json",
        {"a1": {"Z1": {"article_id": "a1", "zotero_item_key": "Z1"}}},
    )
    write_json(root / "tutor_sessions.json", {"t1": {"session_id": "t1", "turns": []}})

    markdown_root = root / "corpus/local_library"
    (markdown_root / "articles").mkdir(parents=True)
    (markdown_root / "articles/1.md").write_text("# Attention\n", encoding="utf-8")
    (markdown_root / "articles/2.md").write_text("# CRB\n", encoding="utf-8")
    write_json(markdown_root / "index/articles_index.json", [{"id": "a1"}, {"id": "a2"}])
    write_json(
        markdown_root / "reports/local_library_summary.json",
        {"article_count": 2, "exported_markdown_count": 2},
    )

    pdf_root = root / "corpus/pdf_library"
    pdf_payload = b"%PDF-1.4\nfixture\n%%EOF\n"
    (pdf_root / "articles").mkdir(parents=True)
    (pdf_root / "articles/a1.pdf").write_bytes(pdf_payload)
    (pdf_root / "articles/a2.pdf").write_bytes(pdf_payload)
    write_json(
        pdf_root / "manifest/pdf_manifest.json",
        {
            "schema_version": 2,
            "corpus_fingerprint": corpus_fingerprint,
            "records": [
                {
                    "article_id": "a1",
                    "output_relative_path": "articles/a1.pdf",
                    "pdf_sha256": sha256_bytes(pdf_payload),
                    "pdf_size_bytes": len(pdf_payload),
                },
                {
                    "article_id": "a2",
                    "output_relative_path": "articles/a2.pdf",
                    "pdf_sha256": sha256_bytes(pdf_payload),
                    "pdf_size_bytes": len(pdf_payload),
                },
            ],
        },
    )

    rag_root = root / "rag/full_corpus/index"
    rag_root.mkdir(parents=True)
    faiss_payload = b"fixture-faiss"
    chunks_payload = b'{"chunk_id":"a1:0"}\n'
    (rag_root / "faiss.index").write_bytes(faiss_payload)
    (rag_root / "chunks.jsonl").write_bytes(chunks_payload)
    write_json(
        rag_root / "manifest.json",
        {
            "schema_version": 2,
            "article_count": 2,
            "unique_url_count": 2,
            "chunk_count": 1,
            "corpus_fingerprint": corpus_fingerprint,
            "index_file": "faiss.index",
            "index_file_size_bytes": len(faiss_payload),
            "index_file_sha256": sha256_bytes(faiss_payload),
            "chunk_metadata_file": "chunks.jsonl",
            "chunk_metadata_size_bytes": len(chunks_payload),
            "chunk_metadata_sha256": sha256_bytes(chunks_payload),
        },
    )

    graph_root = root / "graph/full_corpus"
    graph_payload = json.dumps({"nodes": [{"node_id": "a1"}], "edges": []}).encode()
    graph_root.mkdir(parents=True)
    (graph_root / "graph.json").write_bytes(graph_payload)
    write_json(
        graph_root / "manifest.json",
        {
            "schema_version": 1,
            "article_count": 2,
            "unique_url_count": 2,
            "node_count": 1,
            "edge_count": 0,
            "corpus_fingerprint": corpus_fingerprint,
            "graph_fingerprint": "fixture-graph-fingerprint",
            "graph_file": "graph.json",
            "graph_file_size_bytes": len(graph_payload),
            "graph_file_sha256": sha256_bytes(graph_payload),
        },
    )

    write_json(root / "evaluation/result.json", {"status": "PASS"})
    (root / "cache").mkdir()
    (root / "cache/transient.cache").write_text("discard", encoding="utf-8")
    return root, corpus_fingerprint
