from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request

from ..auth import require_auth
from ..db import connect, many
from .. import config

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
def get_stats(request: Request):
    user = require_auth(request)
    conn = connect()
    is_admin = user["role"] == "admin"
    uid = user["user_id"]
    user_name = user.get("name") or ""

    def _count(extra: str = "", extra_params: tuple = ()) -> int:
        if is_admin:
            visibility = ""
            vis_params = ()
        else:
            visibility = "(created_by=? OR assignee_id=? OR (assignee_name=? AND assignee_id IS NULL))"
            vis_params = (uid, uid, user_name)

        if visibility and extra:
            sql = f"SELECT COUNT(*) FROM tickets WHERE {visibility} AND ({extra})"
        elif visibility:
            sql = f"SELECT COUNT(*) FROM tickets WHERE {visibility}"
        elif extra:
            sql = f"SELECT COUNT(*) FROM tickets WHERE {extra}"
        else:
            sql = "SELECT COUNT(*) FROM tickets"

        return conn.execute(sql, vis_params + extra_params).fetchone()[0]

    total = _count()
    active = _count("status IN ('Open','In Progress','Pending')")
    unassigned = _count("assignee_id IS NULL AND assignee_name IS NULL AND status NOT IN ('Resolved','Closed')")
    resolved = _count("status='Resolved'")
    closed = _count("status='Closed'")
    high_priority = _count("priority IN ('High','Urgent') AND status NOT IN ('Resolved','Closed')")
    escalated = _count("is_escalated=1")
    assigned_to_me = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE (assignee_id=? OR (assignee_name=? AND assignee_id IS NULL)) AND status NOT IN ('Resolved','Closed')",
        (uid, user_name),
    ).fetchone()[0]

    by_status = [
        {"status": s, "count": _count("status=?", (s,))}
        for s in config.TICKET_STATUSES
    ]
    by_priority = [
        {"priority": p, "count": _count("priority=?", (p,))}
        for p in config.TICKET_PRIORITIES
    ]
    departments = many(conn, "SELECT name FROM departments ORDER BY name")
    by_department = [
        {"department": d["name"], "count": _count("department=?", (d["name"],))}
        for d in departments
    ]

    now_dt = datetime.now(timezone.utc)
    trend_7d = []
    for days_ago in range(6, -1, -1):
        day_start = (now_dt - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = _count("created_at >= ? AND created_at < ?", (day_start.isoformat(), day_end.isoformat()))
        trend_7d.append({"date": day_start.strftime("%b %d"), "count": count})

    conn.close()
    return {
        "total": total,
        "active": active,
        "unassigned": unassigned,
        "resolved": resolved,
        "closed": closed,
        "high_priority": high_priority,
        "escalated": escalated,
        "assigned_to_me": assigned_to_me,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_department": by_department,
        "trend_7d": trend_7d,
    }
