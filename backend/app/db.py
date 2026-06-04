import uuid
from datetime import datetime, timezone
from typing import Optional

from . import config

_client = None


def _sb():
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def get_one(table: str, **filters) -> Optional[dict]:
    q = _sb().table(table).select("*")
    for k, v in filters.items():
        q = q.eq(k, v)
    resp = q.limit(1).execute()
    return resp.data[0] if resp.data else None


def get_many(table: str, order_col: str = "created_at", desc: bool = True, **filters) -> list:
    q = _sb().table(table).select("*")
    for k, v in filters.items():
        q = q.eq(k, v)
    if order_col:
        q = q.order(order_col, desc=desc)
    return q.execute().data or []


def db_insert(table: str, data: dict) -> dict:
    resp = _sb().table(table).insert(data).execute()
    return resp.data[0] if resp.data else data


def db_upsert(table: str, data: dict, on_conflict: str = None) -> dict:
    kwargs = {"on_conflict": on_conflict} if on_conflict else {}
    resp = _sb().table(table).upsert(data, **kwargs).execute()
    return resp.data[0] if resp.data else data


def db_update(table: str, data: dict, **filters) -> Optional[dict]:
    q = _sb().table(table).update(data)
    for k, v in filters.items():
        q = q.eq(k, v)
    resp = q.execute()
    return resp.data[0] if resp.data else None


def db_delete(table: str, **filters):
    q = _sb().table(table).delete()
    for k, v in filters.items():
        q = q.eq(k, v)
    q.execute()


def db_count(table: str, filters: dict = None, or_filter: str = None, in_filter: dict = None, not_in: dict = None, null_cols: list = None) -> int:
    q = _sb().table(table).select("*", count="exact", head=True)
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    if or_filter:
        q = q.or_(or_filter)
    if in_filter:
        for k, v in in_filter.items():
            q = q.in_(k, v)
    if not_in:
        for k, v in not_in.items():
            q = q.not_.in_(k, v)
    if null_cols:
        for col in null_cols:
            q = q.filter(col, "is", "null")
    return q.execute().count or 0


def next_ticket_code() -> str:
    resp = _sb().rpc("increment_ticket_counter").execute()
    n = resp.data
    return f"NCP-{n:04d}"


def ticket_with_counts(t: dict) -> dict:
    att = _sb().table("attachments").select("*", count="exact", head=True).eq("ticket_id", t["id"]).eq("is_deleted", 0).execute()
    cmt = _sb().table("comments").select("*", count="exact", head=True).eq("ticket_id", t["id"]).execute()
    t["attachments_count"] = att.count or 0
    t["comments_count"] = cmt.count or 0
    t["is_escalated"] = bool(t.get("is_escalated", 0))
    return t