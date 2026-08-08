#!/usr/bin/env python3
"""Stale-fact gate for the docs. Exit 1 on any finding.

Checks:
1. docs/API.md freshness — regenerating from OpenAPI must produce a byte-
   identical file (endpoints/schemas added or removed → docs drift → fail).
2. Blocklist — known-stale tokens must not appear in the current docs
   (old design system, old LLM provider, old test counts, removed infra).

Run: cd backend && .venv/bin/python ../docs/scripts/docs_check.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # docs/
sys.path.insert(0, str(Path(__file__).parent))

import generate_api_md  # noqa: E402

fails: list[str] = []

# 1. API.md must match what the generator produces.
generated = generate_api_md.main()
committed = (ROOT / "API.md").read_text()
if generated != committed:
    fails.append("docs/API.md is stale — run docs/scripts/generate_api_md.py")

# 2. Blocklist across the living docs (OPTIONS_PAGE_REWORK.md is a historical
#    design record; scripts/ is tooling — both excluded).
STALE = [
    r"Amber Health Check", r"ollama", r":0731", r"147 passed", r"177 passed",
    r"137 passed", r"167 passed", r"134 passed", r"docker compose",
    r"analysis/\[symbol\]", r"github/workflows",
]
docs = [p for p in ROOT.glob("*.md") if p.name != "OPTIONS_PAGE_REWORK.md"]
for p in sorted(docs):
    text = p.read_text()
    for pat in STALE:
        if re.search(pat, text, re.IGNORECASE):
            fails.append(f"{p.name}: stale token {pat!r}")

if fails:
    print("DOCS CHECK FAILED:")
    for f in fails:
        print(f"  - {f}")
    sys.exit(1)
print(f"docs check OK ({len(docs)} files)")
