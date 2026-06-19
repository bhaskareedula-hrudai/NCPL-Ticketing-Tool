"""NCPL Ticketing Tool — FastAPI application entry point."""
import os
import sys
import logging
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from app import config
from app.routers import auth, tickets, departments, employees, dashboard, widget
from app.routers import settings as settings_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ncpl")

class _WidgetCORSMiddleware(BaseHTTPMiddleware):
    _WIDGET_HEADERS = {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, POST, PATCH , OPTIONS",
        "Access-Control-Allow-Headers": "X-Widget-Key, Content-Type",
        "Access-Control-Max-Age":       "3600",
    }

    async def dispatch(self, request: StarletteRequest, call_next):
        if not request.url.path.startswith("/api/widget"):
            return await call_next(request)
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=self._WIDGET_HEADERS)
        response = await call_next(request)
        for k, v in self._WIDGET_HEADERS.items():
            response.headers[k] = v
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="NCPL Ticketing API", version="2.0")

    if config.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=".*",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(_WidgetCORSMiddleware)   

    prefix = "/api"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(tickets.router, prefix=prefix)
    app.include_router(departments.router, prefix=prefix)
    app.include_router(employees.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(widget.router, prefix=prefix)
    app.include_router(settings_router.router, prefix=prefix)

    @app.get("/api")
    def health():
        return {"service": "NCPL Ticketing", "status": "ok", "storage": "supabase"}

    @app.get("/api/health")
    def health_check():
        try:
            from app.db import _sb
            _sb().table("departments").select("id").limit(1).execute()
            return {"service": "NCPL Ticketing", "db": "ok", "storage": "supabase"}
        except Exception as exc:
            return {"service": "NCPL Ticketing", "db": "error", "error": str(exc)}

    if not os.environ.get("VERCEL"):
        try:
            from app import wa_web
            wa_web.start()
            logger.info("WhatsApp Web worker started")
        except Exception as exc:
            logger.warning("WhatsApp Web worker could not start: %s", exc)

    return app


app = create_app()