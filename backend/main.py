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

from app import config
from app.routers import auth, tickets, departments, employees, dashboard
from app.routers import settings as settings_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ncpl")


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

    prefix = "/api"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(tickets.router, prefix=prefix)
    app.include_router(departments.router, prefix=prefix)
    app.include_router(employees.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
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