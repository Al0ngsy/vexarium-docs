#!/usr/bin/env python3
"""Regenerate docs/API.md from the FastAPI OpenAPI schema.

Facts come from code (endpoint tables, params, schemas); judgment (rate
limits, gating, cache keys, gotchas) lives in api_notes.md and is appended
verbatim. Run from anywhere:

    cd backend && .venv/bin/python ../docs/scripts/generate_api_md.py

docs_check.py fails when the committed API.md is stale (i.e. this file would
change it).
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
DOCS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402

TAG_ORDER = ["health", "auth", "analysis", "assets", "options", "strategies",
             "portfolio", "trades", "billing", "stream"]


def schema_name(ref: str | None) -> str:
    return ref.split("/")[-1] if ref else "—"


def example_for(schema: dict, schemas: dict, seen: set | None = None) -> object:
    """Build a tiny JSON example from a JSON-schema dict, resolving $refs."""
    seen = seen or set()
    ref = schema.get("$ref")
    if ref:
        name = ref.split("/")[-1]
        if name in seen:
            return "…"
        seen = seen | {name}
        return example_for(schemas.get(name, {}), schemas, seen)
    t = schema.get("type")
    if t == "object":
        return {k: example_for(v, schemas, seen) for k, v in schema.get("properties", {}).items()}
    if t == "array":
        return [example_for(schema.get("items", {}), schemas, seen)]
    if t == "number" or t == "integer":
        return 0
    if t == "boolean":
        return False
    return "string"


def main() -> str:
    spec = app.openapi()
    schemas = spec.get("components", {}).get("schemas", {})
    paths = spec.get("paths", {})

    out = ["# VEXARIUM — API Reference", "",
           "> **Auto-generated from the FastAPI OpenAPI schema** "
           f"(`app.openapi()`, {len(paths)} paths). Do not hand-edit the tables — "
           "regenerate with `docs/scripts/generate_api_md.py`. Editorial notes "
           "(gating, caching, gotchas) live in `docs/scripts/api_notes.md`.", ""]

    # --- Endpoint tables, grouped by tag (stable order) ---
    by_tag: dict[str, list[tuple[str, str, dict]]] = {}
    for path, ops in paths.items():
        for method, op in ops.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            for tag in op.get("tags", ["misc"]):
                by_tag.setdefault(tag, []).append((method.upper(), path, op))

    for tag in TAG_ORDER:
        ops = by_tag.pop(tag, [])
        if not ops:
            continue
        out += [f"## {tag.title()}", "", "| Method | Path | Params / body → Response | Notes |",
                "|--------|------|---------------------------|-------|"]
        for method, path, op in sorted(ops, key=lambda x: x[1]):
            params = []
            for p in op.get("parameters", []):
                params.append(f"`?{p['name']}`" if p.get("in") == "query" else f"`{p['name']}`")
            rb = op.get("requestBody", {})
            body_ref = schema_name(rb.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref"))
            resp = op.get("responses", {}).get("200", {})
            resp_ref = schema_name(resp.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref"))
            call = " + ".join(params + ([f"`{body_ref}`"] if body_ref != "—" else []))
            call = f"`{call}` → `{resp_ref}`" if call else f"→ `{resp_ref}`"
            summary = (op.get("summary") or op.get("description") or "").strip().split("\n")[0]
            out.append(f"| {method} | `{path}` | {call} | {summary} |")
        out.append("")

    # --- Schemas (JSON skeletons) ---
    out += ["## Schemas", "", "Compact JSON skeletons from the OpenAPI components "
            "(values are placeholder examples, not real data):", ""]
    for name in sorted(schemas):
        ex = example_for(schemas[name], schemas)
        out += [f"### `{name}`", "", "```json", __import__("json").dumps(ex, indent=2), "```", ""]

    # --- Editorial notes (hand-maintained, appended verbatim) ---
    notes = (Path(__file__).parent / "api_notes.md").read_text()
    out += [notes]

    return "\n".join(out) + "\n"


if __name__ == "__main__":
    (DOCS / "API.md").write_text(main())
    print(f"docs/API.md regenerated ({len(main())} chars)")
