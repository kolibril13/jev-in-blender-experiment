"""Ranking Blender operators with Jev. Two strategies:

hierarchical (2 requests)
    1. one Choice over every bpy.ops module -> P(module)
    2. for the top modules (until their probability mass reaches
       `module_mass`, at most `top_modules`), one Choice per <=250-operator
       chunk, all in one request -> P(op | chunk)
    score(op) = P(module) * P(op | chunk)

flat (1 request)
    one Choice per <=250-operator chunk over the whole catalog, all in one
    request. score(op) = P(op | chunk). Fewer round trips, more tokens.

Pure Python apart from the catalog; safe to call from a worker thread as long
as the catalog was built on the main thread first.
"""

from time import perf_counter

from . import jev_api
from . import catalog as cat

CHUNK = 250  # a Choice takes at most 255 options; leave room for the none option
NONE = "none_of_these"

MODULE_INSTRUCTIONS = {
    "question": (
        "The user describes something they want to do in Blender (`request`). "
        "Which operator category most likely contains the operator that performs it?"
    ),
    "focus": (
        "Judge by what the user wants to accomplish, not by words that happen to match a "
        "category name. `blender_context` says what mode the user is in and what is selected; "
        "prefer categories whose tools work in that mode when the request could fit several."
    ),
}

OPERATOR_INSTRUCTIONS = {
    "question": (
        "The user describes something they want to do in Blender (`request`). "
        "Which of these operators performs exactly that?"
    ),
    "focus": (
        "Each option is an operator name followed by its label and description. Choose the "
        "operator whose description matches the user's goal. Choose none_of_these if no listed "
        "operator does what the user describes."
    ),
}


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _tokens(usage):
    return usage.get("input_tokens") or 0


def rank_modules(api_key, state, catalog, model):
    answers, usage = jev_api.system_one(
        api_key,
        state,
        {"module": jev_api.choice(MODULE_INSTRUCTIONS, cat.module_criteria(catalog))},
        model=model,
    )
    probs = answers["module"]["probabilities"]
    return sorted(probs.items(), key=lambda kv: -kv[1]), usage


def rank_operators(api_key, state, catalog, modules, model):
    """One request: a Choice per chunk of each module. Returns {idname: P(op|chunk)}."""
    questions = {}
    for mod_name in modules:
        for i, chunk in enumerate(_chunks(catalog[mod_name], CHUNK)):
            criteria = cat.operator_criteria(chunk)
            criteria[NONE] = "No operator in this list does what the user describes"
            questions[f"{mod_name}::{i}"] = jev_api.choice(OPERATOR_INSTRUCTIONS, criteria)
    answers, usage = jev_api.system_one(api_key, state, questions, model=model)
    per_op = {}
    for answer in answers.values():
        for idname, p in answer["probabilities"].items():
            if idname != NONE:
                per_op[idname] = p
    return per_op, usage


def _select_modules(ranked, top_modules, module_mass):
    """Top modules until their cumulative probability reaches module_mass."""
    chosen, mass = [], 0.0
    for mod_name, p in ranked[:top_modules]:
        chosen.append(mod_name)
        mass += p
        if mass >= module_mass:
            break
    return chosen


def _score(catalog, modules, module_p, per_op):
    scored = []
    for mod_name in modules:
        for idname, label, desc in catalog[mod_name]:
            p = per_op.get(idname, 0.0)
            scored.append(
                {
                    "idname": idname,
                    "label": label,
                    "description": desc,
                    "module": mod_name,
                    "p_module": module_p.get(mod_name, 1.0),
                    "p_op": p,
                    "score": module_p.get(mod_name, 1.0) * p,
                }
            )
    scored.sort(key=lambda r: -r["score"])
    return scored


def search_hierarchical(api_key, state, catalog, top_modules, module_mass, model):
    t0 = perf_counter()
    ranked_modules, usage1 = rank_modules(api_key, state, catalog, model)
    chosen = _select_modules(ranked_modules, top_modules, module_mass)
    per_op, usage2 = rank_operators(api_key, state, catalog, chosen, model)
    scored = _score(catalog, chosen, dict(ranked_modules), per_op)
    meta = {
        "strategy": "hierarchical",
        "modules": [(m, p) for m, p in ranked_modules if m in chosen],
        "input_tokens": _tokens(usage1) + _tokens(usage2),
        "seconds": perf_counter() - t0,
    }
    return scored, meta


def search_flat(api_key, state, catalog, model):
    t0 = perf_counter()
    modules = list(catalog)
    per_op, usage = rank_operators(api_key, state, catalog, modules, model)
    scored = _score(catalog, modules, {}, per_op)
    meta = {
        "strategy": "flat",
        "modules": [],
        "input_tokens": _tokens(usage),
        "seconds": perf_counter() - t0,
    }
    return scored, meta


def search(
    api_key,
    request_text,
    blender_context,
    top_modules=3,
    top_results=8,
    model="jev-latest",
    strategy="hierarchical",
    module_mass=0.9,
):
    """Returns (results, meta). results: list of dicts sorted by score desc."""
    catalog = cat.get_catalog()
    state = {"request": request_text, "blender_context": blender_context}
    if strategy == "flat":
        scored, meta = search_flat(api_key, state, catalog, model)
    else:
        scored, meta = search_hierarchical(api_key, state, catalog, top_modules, module_mass, model)
    return scored[:top_results], meta
