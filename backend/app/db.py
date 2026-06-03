import re
import ssl
import sqlite3
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from . import config

_SQLITE_DB = Path(__file__).parent.parent / "ncpl.db"


# ── Helpers ───────────────────────────────────────────────────────────────────

def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _serialize(val):
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, memoryview):
        return bytes(val)
    return val


def _use_postgres() -> bool:
    url = config.DATABASE_URL or ""
    return url.startswith("postgresql://") or url.startswith("postgres://")


# ── Row / Cursor wrappers ─────────────────────────────────────────────────────

class RowProxy:
    __slots__ = ("_keys", "_values", "_dict")

    def __init__(self, description, raw_values):
        self._keys = [col[0] for col in description]
        self._values = [_serialize(v) for v in raw_values]
        self._dict = dict(zip(self._keys, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._dict[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __bool__(self):
        return True

    def keys(self):
        return self._keys

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def items(self):
        return self._dict.items()


class CursorWrapper:
    def __init__(self, cursor):
        self._cur = cursor

    def fetchone(self) -> Optional[RowProxy]:
        row = self._cur.fetchone()
        return RowProxy(self._cur.description, row) if row is not None else None

    def fetchall(self) -> list:
        return [RowProxy(self._cur.description, r) for r in self._cur.fetchall()]

    def __iter__(self):
        for row in self._cur:
            yield RowProxy(self._cur.description, row)


# ── PostgreSQL connection ─────────────────────────────────────────────────────

def _to_pg(sql: str, params) -> tuple:
    """Convert ? / :name placeholders to pg8000 %s format."""
    if isinstance(params, dict):
        keys = []
        def _repl(m):
            keys.append(m.group(1))
            return "%s"
        converted = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", _repl, sql)
        return converted, [params[k] for k in keys]
    return sql.replace("?", "%s"), list(params) if params else []


class PgConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=()) -> CursorWrapper:
        pg_sql, pg_params = _to_pg(sql, params)
        cur = self._conn.cursor()
        cur.execute(pg_sql, pg_params)
        return CursorWrapper(cur)

    def executescript(self, script: str) -> "PgConnection":
        cur = self._conn.cursor()
        for stmt in script.split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
        return self

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


# ── SQLite connection (local dev) ─────────────────────────────────────────────

class SQLiteConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=()) -> CursorWrapper:
        # Support ?, %s, and :name placeholders — all normalised to ? for sqlite3
        if isinstance(params, dict):
            keys = []
            def _repl(m):
                keys.append(m.group(1))
                return "?"
            sql = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", _repl, sql)
            params = [params[k] for k in keys]
        else:
            sql = sql.replace("%s", "?")
            params = list(params) if params else []
        cur = self._conn.execute(sql, params)
        return CursorWrapper(cur)

    def executescript(self, script: str) -> "SQLiteConnection":
        self._conn.executescript(script)
        return self

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


# ── Public API ────────────────────────────────────────────────────────────────

def connect():
    if _use_postgres():
        import pg8000.dbapi
        url = urlparse(config.DATABASE_URL)
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        conn = pg8000.dbapi.connect(
            host=url.hostname,
            port=url.port or 5432,
            database=url.path.lstrip("/"),
            user=url.username,
            password=url.password,
            ssl_context=ssl_ctx,
            timeout=10,
        )
        return PgConnection(conn)
    else:
        conn = sqlite3.connect(str(_SQLITE_DB), check_same_thread=False)
        return SQLiteConnection(conn)


def one(conn, sql: str, params=()) -> Optional[dict]:
    row = conn.execute(sql, params).fetchone()
    return dict(row._dict) if row else None


def many(conn, sql: str, params=()) -> list:
    return [dict(r._dict) for r in conn.execute(sql, params).fetchall()]


def next_ticket_code() -> str:
    conn = connect()
    if _use_postgres():
        row = conn.execute(
            "UPDATE ticket_counter SET value = value + 1 WHERE id = 1 RETURNING value"
        ).fetchone()
    else:
        conn.execute("UPDATE ticket_counter SET value = value + 1 WHERE id = 1")
        row = conn.execute("SELECT value FROM ticket_counter WHERE id = 1").fetchone()
    conn.commit()
    n = row[0]
    conn.close()
    return f"NCP-{n:04d}"


def ticket_with_counts(t: dict) -> dict:
    conn = connect()
    t["attachments_count"] = conn.execute(
        "SELECT COUNT(*) FROM attachments WHERE ticket_id = ? AND is_deleted = 0",
        (t["id"],),
    ).fetchone()[0]
    t["comments_count"] = conn.execute(
        "SELECT COUNT(*) FROM comments WHERE ticket_id = ?", (t["id"],)
    ).fetchone()[0]
    conn.close()
    t["is_escalated"] = bool(t.get("is_escalated", 0))
    return t


_PG_SCHEMA = """
    CREATE TABLE IF NOT EXISTS public.users (
        user_id       TEXT PRIMARY KEY,
        email         TEXT UNIQUE NOT NULL,
        name          TEXT,
        picture       TEXT,
        role          TEXT NOT NULL DEFAULT 'employee',
        department    TEXT,
        created_at    TIMESTAMPTZ,
        last_login_at TIMESTAMPTZ,
        phone_number  TEXT,
        wa_api_key    TEXT
    );
    CREATE TABLE IF NOT EXISTS public.user_sessions (
        session_token TEXT PRIMARY KEY,
        user_id       TEXT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
        expires_at    TIMESTAMPTZ NOT NULL,
        created_at    TIMESTAMPTZ
    );
    CREATE TABLE IF NOT EXISTS public.departments (
        id          TEXT PRIMARY KEY,
        name        TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at  TIMESTAMPTZ
    );
    CREATE TABLE IF NOT EXISTS public.tickets (
        id               TEXT PRIMARY KEY,
        code             TEXT UNIQUE,
        title            TEXT,
        description      TEXT,
        status           TEXT DEFAULT 'Open',
        priority         TEXT DEFAULT 'Medium',
        department       TEXT,
        created_by       TEXT,
        created_by_name  TEXT,
        created_by_email TEXT,
        assignee_id      TEXT,
        assignee_name    TEXT,
        due_at           TIMESTAMPTZ,
        is_escalated     SMALLINT DEFAULT 0,
        escalated_at     TIMESTAMPTZ,
        resolved_at      TIMESTAMPTZ,
        closed_at        TIMESTAMPTZ,
        created_at       TIMESTAMPTZ,
        updated_at       TIMESTAMPTZ
    );
    CREATE TABLE IF NOT EXISTS public.comments (
        id          TEXT PRIMARY KEY,
        ticket_id   TEXT REFERENCES public.tickets(id) ON DELETE CASCADE,
        body        TEXT,
        is_internal SMALLINT DEFAULT 0,
        author_id   TEXT,
        author_name TEXT,
        author_role TEXT,
        created_at  TIMESTAMPTZ
    );
    CREATE TABLE IF NOT EXISTS public.attachments (
        id               TEXT PRIMARY KEY,
        ticket_id        TEXT REFERENCES public.tickets(id) ON DELETE CASCADE,
        filename         TEXT,
        content_type     TEXT,
        size             INTEGER,
        data             BYTEA,
        uploaded_by      TEXT,
        uploaded_by_name TEXT,
        created_at       TIMESTAMPTZ,
        is_deleted       SMALLINT DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS public.ticket_counter (
        id    INTEGER PRIMARY KEY DEFAULT 1,
        value INTEGER DEFAULT 0
    )
"""

_SQLITE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        user_id       TEXT PRIMARY KEY,
        email         TEXT UNIQUE NOT NULL,
        name          TEXT,
        picture       TEXT,
        role          TEXT NOT NULL DEFAULT 'employee',
        department    TEXT,
        created_at    TEXT,
        last_login_at TEXT,
        phone_number  TEXT,
        wa_api_key    TEXT
    );
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_token TEXT PRIMARY KEY,
        user_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        expires_at    TEXT NOT NULL,
        created_at    TEXT
    );
    CREATE TABLE IF NOT EXISTS departments (
        id          TEXT PRIMARY KEY,
        name        TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at  TEXT
    );
    CREATE TABLE IF NOT EXISTS tickets (
        id               TEXT PRIMARY KEY,
        code             TEXT UNIQUE,
        title            TEXT,
        description      TEXT,
        status           TEXT DEFAULT 'Open',
        priority         TEXT DEFAULT 'Medium',
        department       TEXT,
        created_by       TEXT,
        created_by_name  TEXT,
        created_by_email TEXT,
        assignee_id      TEXT,
        assignee_name    TEXT,
        due_at           TEXT,
        is_escalated     INTEGER DEFAULT 0,
        escalated_at     TEXT,
        resolved_at      TEXT,
        closed_at        TEXT,
        created_at       TEXT,
        updated_at       TEXT
    );
    CREATE TABLE IF NOT EXISTS comments (
        id          TEXT PRIMARY KEY,
        ticket_id   TEXT REFERENCES tickets(id) ON DELETE CASCADE,
        body        TEXT,
        is_internal INTEGER DEFAULT 0,
        author_id   TEXT,
        author_name TEXT,
        author_role TEXT,
        created_at  TEXT
    );
    CREATE TABLE IF NOT EXISTS attachments (
        id               TEXT PRIMARY KEY,
        ticket_id        TEXT REFERENCES tickets(id) ON DELETE CASCADE,
        filename         TEXT,
        content_type     TEXT,
        size             INTEGER,
        data             BLOB,
        uploaded_by      TEXT,
        uploaded_by_name TEXT,
        created_at       TEXT,
        is_deleted       INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS ticket_counter (
        id    INTEGER PRIMARY KEY,
        value INTEGER DEFAULT 0
    )
"""


def init_db() -> None:
    conn = connect()
    if _use_postgres():
        conn.executescript(_PG_SCHEMA)
        conn.execute(
            "INSERT INTO public.ticket_counter (id, value) VALUES (1, 0) ON CONFLICT (id) DO NOTHING"
        )
        for name in config.SEED_DEPARTMENTS:
            conn.execute(
                "INSERT INTO public.departments (id, name, description, created_at)"
                " VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO NOTHING",
                (new_id("dept"), name, f"{name} department", now()),
            )
        # migrations: add new columns if they don't exist yet
        conn.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone_number TEXT")
        conn.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS wa_api_key TEXT")
    else:
        conn.executescript(_SQLITE_SCHEMA)
        conn.execute("INSERT OR IGNORE INTO ticket_counter (id, value) VALUES (1, 0)")
        for name in config.SEED_DEPARTMENTS:
            conn.execute(
                "INSERT OR IGNORE INTO departments (id, name, description, created_at)"
                " VALUES (?, ?, ?, ?)",
                (new_id("dept"), name, f"{name} department", now()),
            )
        # migrations: add new columns for existing SQLite databases
        for _col in ("phone_number TEXT", "wa_api_key TEXT"):
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {_col}")
            except Exception:
                pass  # column already exists
    conn.commit()
    conn.close()