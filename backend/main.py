"""NCPL Ticketing Tool — FastAPI application entry point."""
import sys
import logging
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app import config  # noqa: E402
from app.db import init_db, connect as db_connect  # noqa: E402
from app.routers import auth, tickets, departments, employees, dashboard  # noqa: E402
from app.routers import settings as settings_router  # noqa: E402

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
        db_url = config.DATABASE_URL
        masked = (db_url[:30] + "…" + db_url[-20:]) if len(db_url) > 55 else db_url
        try:
            conn = db_connect()
            row = conn.execute("SELECT 1 AS ok").fetchone()
            conn.close()
            db_ok = row is not None
        except Exception as exc:
            return {
                "service": "NCPL Ticketing",
                "db": "error",
                "db_url_preview": masked or "(not set)",
                "error": str(exc),
            }
        return {
            "service": "NCPL Ticketing",
            "db": "ok",
            "db_url_preview": masked or "(not set)",
        }

    try:
        init_db()
        logger.info("NCPL Ticketing API ready — DB initialised")
    except Exception as exc:
        logger.error("init_db() failed — DB may be unavailable: %s", exc)

    # Start WhatsApp Web background worker
    try:
        from app import wa_web
        wa_web.start()
        logger.info("WhatsApp Web worker started")
    except Exception as exc:
        logger.warning("WhatsApp Web worker could not start: %s", exc)

    return app


app = create_app()