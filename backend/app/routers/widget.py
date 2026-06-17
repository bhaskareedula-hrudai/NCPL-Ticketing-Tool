import logging
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel

from ..db import _sb, db_insert, new_id, now, next_ticket_code
from .. import config, whatsapp

logger = logging.getLogger("ncpl")
router = APIRouter(tags=["widget"])


def _require_widget_key(x_widget_key: Optional[str]) -> None:
    if not config.WIDGET_API_KEY:
        raise HTTPException(500, "WIDGET_API_KEY is not configured on this server")
    if x_widget_key != config.WIDGET_API_KEY:
        raise HTTPException(401, "Invalid widget API key")


class WidgetTicketIn(BaseModel):
    email: str
    title: str
    description: str
    priority: Literal["Low", "Medium", "High", "Urgent"] = "Medium"
    department: Optional[str] = None
    app: Optional[str] = None


@router.post("/widget/tickets")
def create_widget_ticket(
    body: WidgetTicketIn,
    x_widget_key: Optional[str] = Header(None),
):
    _require_widget_key(x_widget_key)

    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email is required")

    source = (body.app or "Widget").strip()
    ts = now()
    ticket = {
        "id":               new_id("tkt"),
        "code":             next_ticket_code(),
        "title":            body.title.strip(),
        "description":      body.description.strip(),
        "status":           "Open",
        "priority":         body.priority,
        "department":       (body.department or "General").strip(),
        "created_by":       None,
        "created_by_name":  email.split("@")[0],
        "created_by_email": email,
        "assignee_id":      None,
        "assignee_name":    None,
        "source":           source,
        "due_at":           None,
        "is_escalated":     0,
        "escalated_at":     None,
        "resolved_at":      None,
        "closed_at":        None,
        "created_at":       ts,
        "updated_at":       ts,
    }
    db_insert("tickets", ticket)
    logger.info("Widget ticket created: %s from %s (app=%s)", ticket["code"], email, source)

    try:
        whatsapp.send_new_ticket_to_department(ticket)
    except Exception as exc:
        logger.warning("Department WhatsApp notification failed for %s: %s", ticket["code"], exc)

    return {"id": ticket["id"], "code": ticket["code"], "status": "Open"}


@router.get("/widget/tickets")
def list_widget_tickets(
    email: str = Query(..., description="User email to filter tickets"),
    app:   Optional[str] = Query(None, description="App name to filter tickets"),
    x_widget_key: Optional[str] = Header(None),
):
    _require_widget_key(x_widget_key)

    email = email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email is required")

    q = (
        _sb().table("tickets")
        .select("id,code,title,status,priority,department,created_at,source")
        .eq("created_by_email", email)
    )
    if app:
        q = q.eq("source", app.strip())

    rows = q.order("created_at", desc=True).execute().data or []
    return rows


@router.get("/widget/departments")
def list_departments(x_widget_key: Optional[str] = Header(None)):
    _require_widget_key(x_widget_key)
    rows = _sb().table("departments").select("id,name").order("name").execute().data or []
    return [{"id": r["id"], "name": r["name"]} for r in rows]


@router.get("/widget/department-tickets")
def list_department_tickets(
    staff_email: str = Query(..., description="Staff member email to resolve department"),
    app: Optional[str] = Query(None, description="App name to filter tickets"),
    x_widget_key: Optional[str] = Header(None),
):
    _require_widget_key(x_widget_key)

    staff_email = staff_email.strip().lower()
    if not staff_email or "@" not in staff_email:
        raise HTTPException(400, "Valid staff email is required")

    users = (
        _sb().table("users").select("department_id")
        .eq("email", staff_email).execute().data or []
    )
    if not users:
        raise HTTPException(403, "Staff member not found")

    dept_id = users[0].get("department_id")
    if not dept_id:
        raise HTTPException(403, "Staff member has no department assigned")

    depts = _sb().table("departments").select("name").eq("id", dept_id).execute().data or []
    if not depts:
        raise HTTPException(403, "Department not found")

    dept_name = depts[0]["name"]
    q = (
        _sb().table("tickets")
        .select("id,code,title,status,priority,department,created_by_name,created_by_email,created_at,source")
        .eq("department", dept_name)
    )
    if app:
        q = q.eq("source", app.strip())

    rows = q.order("created_at", desc=True).execute().data or []
    return rows