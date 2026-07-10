#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test bounded Tutor graph context.")
    parser.add_argument("--graph-file", type=Path, required=True)
    parser.add_argument("--node-id", default="concept:attention")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from app.graph.service import GraphService
    from app.graph.store import GraphStore
    from app.tutor.models import TutorRequest
    from app.tutor.service import TutorService
    from app.zotero.store import ZoteroLinkStore

    graph_service = GraphService(store=GraphStore(args.graph_file.resolve()))
    service = TutorService(
        graph_service=graph_service,
        zotero_store=ZoteroLinkStore(args.output.parent / ".empty-tutor-smoke-zotero.json"),
    )
    request = TutorRequest(
        question="attention",
        mode="research",
        node_id=args.node_id,
        include_graph_context=True,
        include_zotero_context=False,
    )
    context, sources = service._graph_context(request)
    root = next((node for node in context["nodes"] if node["node_id"] == args.node_id), None)
    root_metadata = root.get("metadata") if root else {}
    serialized = json.dumps({"context": context, "sources": [source.to_dict() for source in sources]}, ensure_ascii=False)
    summary = graph_service.get_summary()
    result = {
        "status": "PASS",
        "context_node_count": len(context["nodes"]),
        "context_edge_count": len(context["edges"]),
        "graph_source_count": len(sources),
        "full_graph_injected": len(context["nodes"]) >= int(summary["node_count"]),
        "article_provenance_preserved": any(
            node.get("source_url") or (node.get("metadata") or {}).get("sources")
            for node in context["nodes"]
        ),
        "local_path_exposed": bool(
            re.search(
                r"(?:file://|(?:^|[\"'\s:=])/(?:home|users|root|tmp|var|etc|opt|mnt|srv|data)/"
                r"|(?:^|[\"'\s:=])[A-Za-z]:[\\/])",
                serialized,
                re.I,
            )
        ),
        "root_source_count": int((root_metadata or {}).get("source_count") or 0),
        "root_stored_source_count": len((root_metadata or {}).get("sources") or []),
        "root_provenance_truncated": bool((root_metadata or {}).get("truncated")),
    }
    if (
        not context["nodes"]
        or not context["edges"]
        or result["full_graph_injected"]
        or not result["article_provenance_preserved"]
        or result["local_path_exposed"]
    ):
        result["status"] = "BLOCKED"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
