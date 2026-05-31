"""Vercel serverless entry point — exposes the FastAPI ASGI app.

Vercel's @vercel/python runtime supports ASGI natively; no Lambda adapter needed.
"""
import sys
import json
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_startup_error = None
app = None

try:
    from backend.main import app  # noqa: E402
    print("backend.main imported OK, app =", type(app))
except Exception:
    _startup_error = traceback.format_exc()
    print("STARTUP ERROR:\n", _startup_error)


def _make_error_app(error_text: str):
    """Minimal ASGI app (zero external deps) that returns the startup error as JSON."""
    async def _app(scope, receive, send):
        if scope["type"] == "lifespan":
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
            return
        body = json.dumps({"startup_error": error_text}).encode()
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [[b"content-type", b"application/json"]],
        })
        await send({"type": "http.response.body", "body": body})
    return _app


if app is None:
    app = _make_error_app(_startup_error or "app failed to load (unknown reason)")

# Vercel's Python runtime calls handler as a plain ASGI callable.
handler = app
