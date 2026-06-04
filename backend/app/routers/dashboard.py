from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request

from ..auth import require_auth
from ..db import _sb, get_many
from .. import config

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
def get_stats(request: Request):
    user = require_auth(request)
    is_admin = user["role"] == "admin"
    uid = user["user_id"]
    user_name = user.get("name") or ""

    vis_or = (
        f"created_by.eq.{uid},assignee_id.eq.{uid},and(assignee_name.eq.{user_name},assignee_id.is.null)"
        if not is_admin else None
    )

    def _base():
        q = _sb().table("tickets").select("*", count="exact", head=True)
        if vis_or:
            q = q.or_(vis_or)
        return q

    def _count(**kwargs) -> int:
        q = _base()
        if kwargs.get("status_eq"):
            q = q.eq("status", kwargs["status_eq"])
        if kwargs.get("status_in"):
            q = q.in_("status", kwargs["status_in"])
        if kwargs.get("status_not_in"):
            q = q.not_.in_("status", kwargs["status_not_in"])
        if kwargs.get("priority_in"):
            q = q.in_("priority", kwargs["priority_in"])
        if kwargs.get("priority_eq"):
            q = q.eq("priority", kwargs["priority_eq"])
        if kwargs.get("dept_eq"):
            q = q.eq("department", kwargs["dept_eq"])
        if kwargs.get("is_escalated") is not None:
            q = q.eq("is_escalated", kwargs["is_escalated"])
        if kwargs.get("null_assignee"):
            q = q.filter("assignee_id", "is", "null").filter("assignee_name", "is", "null")
        if kwargs.get("date_gte"):
            q = q.gte("created_at", kwargs["date_gte"])
        if kwargs.get("date_lt"):
            q = q.lt("created_at", kwargs["date_lt"])
        return q.execute().count or 0

    total = _count()
    active = _count(status_in=["Open", "In Progress", "Pending"])
    unassigned = _count(null_assignee=True, status_not_in=["Resolved", "Closed"])
    resolved = _count(status_eq="Resolved")
    closed = _count(status_eq="Closed")
    high_priority = _count(priority_in=["High", "Urgent"], status_not_in=["Resolved", "Closed"])
    escalated = _count(is_escalated=1)

    atm_q = _sb().table("tickets").select("*", count="exact", head=True)
    atm_q = atm_q.or_(f"assignee_id.eq.{uid},and(assignee_name.eq.{user_name},assignee_id.is.null)")
    atm_q = atm_q.not_.in_("status", ["Resolved", "Closed"])
    assigned_to_me = atm_q.execute().count or 0

    by_status = [{"status": s, "count": _count(status_eq=s)} for s in config.TICKET_STATUSES]
    by_priority = [{"priority": p, "count": _count(priority_eq=p)} for p in config.TICKET_PRIORITIES]

    departments = get_many("departments", order_col="name", desc=False)
    by_department = [{"department": d["name"], "count": _count(dept_eq=d["name"])} for d in departments]

    now_dt = datetime.now(timezone.utc)
    trend_7d = []
    for days_ago in range(6, -1, -1):
        day_start = (now_dt - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        cnt = _count(date_gte=day_start.isoformat(), date_lt=day_end.isoformat())
        trend_7d.append({"date": day_start.strftime("%b %d"), "count": cnt})

    return {
        "total": total, "active": active, "unassigned": unassigned,
        "resolved": resolved, "closed": closed, "high_priority": high_priority,
        "escalated": escalated, "assigned_to_me": assigned_to_me,
        "by_status": by_status, "by_priority": by_priority,
        "by_department": by_department, "trend_7d": trend_7d,
    }