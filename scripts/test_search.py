"""Headless benchmark. Usage:

    export TYPESAFE_API_KEY=...
    blender -b --factory-startup --python scripts/test_search.py -- "bevel the selected edges" "add a cube"

Runs each query with both strategies and prints time, tokens and the top hits.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jev_operator_search import catalog as cat, search as js, jev_api  # noqa: E402

t = time.time()
catalog = cat.get_catalog()
print(f"catalog: {sum(len(v) for v in catalog.values())} ops / {len(catalog)} modules in {time.time()-t:.2f}s")

key = os.environ.get("TYPESAFE_API_KEY")
if not key:
    print("NO KEY -> skipping live test")
    sys.exit(0)

queries = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [
    "add a cube",
    "bevel the selected edges",
    "separate the selected faces into a new object",
]
ctx = {"mode": "EDIT_MESH", "active_object_type": "MESH", "active_object_name": "Cube",
       "selected_object_count": 1, "editor": "VIEW_3D"}

t = time.time(); jev_api.warm_up(); print(f"tls warm-up: {time.time()-t:.2f}s")

for q in queries:
    for strategy in ("hierarchical", "flat"):
        results, meta = js.search(key, q, ctx, strategy=strategy)
        mods = ", ".join(f"{m} {p:.2f}" for m, p in meta["modules"])
        print(f"\n### {q!r} [{strategy}]  {meta['seconds']:.2f}s  {meta['input_tokens']:,} tokens  {mods}")
        for r in results[:5]:
            print(f"   {r['score']:.3f}  {r['idname']:<40} {r['label']}")
