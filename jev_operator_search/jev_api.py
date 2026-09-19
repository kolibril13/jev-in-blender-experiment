"""Minimal HTTP client for the TypeSafe System One API (no third-party deps).

Request/response shapes follow https://docs.typesafe.ai/api.md

A single HTTPS connection is kept open between calls so a search doesn't pay
for a TLS handshake on every request.
"""

import http.client
import json
import threading
import time

HOST = "api.typesafe.ai"
PATH = "/v1/systemone"
RETRY_STATUSES = {429, 529}

_conn = None
_conn_lock = threading.Lock()


class JevError(Exception):
    pass


def choice(instructions, criteria):
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def noul(instructions, criteria=None):
    q = {"type": "noul", "instructions": instructions}
    if criteria:
        q["criteria"] = criteria
    return q


def _connection(timeout):
    global _conn
    if _conn is None:
        _conn = http.client.HTTPSConnection(HOST, timeout=timeout)
        _conn.connect()
    return _conn


def _drop_connection():
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
    _conn = None


def warm_up(timeout=10.0):
    """Open the TLS connection ahead of the first search. Safe to call repeatedly."""
    with _conn_lock:
        try:
            _connection(timeout)
        except OSError:
            _drop_connection()


def _post(body, headers, timeout):
    """One POST over the shared connection; reconnects once if the socket went stale."""
    with _conn_lock:
        for attempt in (0, 1):
            try:
                conn = _connection(timeout)
                conn.request("POST", PATH, body=body, headers=headers)
                resp = conn.getresponse()
                data = resp.read()
                return resp.status, data
            except (http.client.HTTPException, OSError) as e:
                _drop_connection()
                if attempt == 1:
                    raise JevError(f"Network error: {e}") from e


def system_one(api_key, state, questions, model="jev-latest", timeout=60.0, retries=3):
    """POST one request; returns (answers, usage)."""
    if not api_key:
        raise JevError("No TypeSafe API key. Set it in the add-on preferences or TYPESAFE_API_KEY.")
    body = json.dumps({"state": state, "model": model, "questions": questions}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "User-Agent": "jev-operator-search/0.1 (Blender)",
    }
    delay = 1.0
    for attempt in range(retries + 1):
        status, data = _post(body, headers, timeout)
        if status == 200:
            payload = json.loads(data.decode("utf-8"))
            return payload["answers"], payload.get("usage", {})
        if status in RETRY_STATUSES and attempt < retries:
            time.sleep(delay)
            delay *= 2
            continue
        raise JevError(f"TypeSafe API {status}: {data.decode('utf-8', 'replace')[:500]}")
