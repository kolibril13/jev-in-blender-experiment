# Jev in Blender — operator search

# Installation Demo video

https://github.com/user-attachments/assets/8ce5a91a-7560-40e9-8405-093acc9ca457


A Blender extension (4.2+) that adds a **Jev** tab to the 3D Viewport sidebar (`N`).
Type what you want to do in plain language, press Enter, and
[TypeSafe's Jev](https://docs.typesafe.ai) ranks every registered `bpy.ops` operator
against it. Click a result to run it, or copy its `bpy.ops` call.

## How it works

Blender exposes ~2,500 operators; a TypeSafe `Choice` question holds at most 255
options, so the search is hierarchical (two requests per search):

1. **Rank modules** — one `Choice` over all `bpy.ops` modules (`mesh`, `object`,
   `transform`, …) with hand-written descriptions → `P(module)`.
2. **Rank operators** — for the top-3 modules, one `Choice` per ≤250-operator chunk,
   all in a single request (they run in parallel), each with a `none_of_these`
   option → `P(op | chunk)`.

Code combines `P(module) · P(op | chunk)` and shows the top hits. Modules are only
expanded until their combined probability reaches 0.9 (preference), so a clear
request usually expands one module. A **flat** strategy (preference) skips step 1
and ranks every operator in one request — fewer round trips, ~4× the tokens.

One HTTPS connection is kept open between requests (and warmed up when the panel
first draws) so searches don't pay a TLS handshake each time. The request state
includes a summary of the current Blender context (mode, active object type,
selection count, editor) so "delete" can mean `mesh.delete` in Edit Mode and
`object.delete` in Object Mode.

A hierarchical search costs roughly 5–15k input tokens (≈ $0.0005 at jev‑1.13 pricing).

## Install (development)

```sh
ln -s "$PWD/jev_operator_search" \
  "$HOME/Library/Application Support/Blender/5.2/extensions/user_default/jev_operator_search"
```

Then in Blender: *Edit › Preferences › Get Extensions › ⌄ › Refresh Local*, enable
**Jev Operator Search**, and paste your API key
(<https://console.typesafe.ai/>) into its preferences. The `TYPESAFE_API_KEY`
environment variable is used as a fallback.

To build a distributable zip: `blender --command extension build --source-dir jev_operator_search`.

## Test headless

```sh
export TYPESAFE_API_KEY=...
blender -b --factory-startup --python scripts/test_search.py -- "bevel the selected edges" "add a cube"
```

## Layout

- `jev_operator_search/jev_api.py` — tiny `urllib` client for `POST /v1/systemone`
- `jev_operator_search/catalog.py` — scans `bpy.ops`, module descriptions
- `jev_operator_search/search.py` — the two-stage ranking
- `jev_operator_search/__init__.py` — panel, operators, preferences, worker thread
