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
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None


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
        "assignee_id":      body.assignee_id,
        "assignee_name":    body.assignee_name,
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
        if body.assignee_email:
            whatsapp.send_ticket_to_assignee(ticket, body.assignee_email)
        else:
            whatsapp.send_new_ticket_to_department(ticket)
    except Exception as exc:
        logger.warning("WhatsApp notification failed for %s: %s", ticket["code"], exc)

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
        .select("id,code,title,status,priority,department,created_at,source,assignee_name")
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
        _sb().table("users").select("department")
        .eq("email", staff_email).execute().data or []
    )
    if not users:
        raise HTTPException(403, "Staff member not found")

    dept_name = (users[0].get("department") or "").strip()
    if not dept_name:
        raise HTTPException(403, "Staff member has no department assigned")

    q = (
        _sb().table("tickets")
        .select("id,code,title,status,priority,department,created_by_name,created_by_email,created_at,source,assignee_name")
        .eq("department", dept_name)
    )
    if app:
        q = q.eq("source", app.strip())

    rows = q.order("created_at", desc=True).execute().data or []
    return rows


@router.get("/widget/department-members")
def list_department_members(
    department: str = Query(..., description="Department name"),
    x_widget_key: Optional[str] = Header(None),
):
    _require_widget_key(x_widget_key)

    dept_name = department.strip()
    if not dept_name:
        return []

    try:
        members = (
            _sb().table("users")
            .select("user_id,name,email")
            .eq("department", dept_name)
            .execute().data or []
        )
        return [
            {"id": m["user_id"], "name": m.get("name") or m.get("email", ""), "email": m.get("email", "")}
            for m in members
        ]
    except Exception as e:
        logger.error("department-members error dept=%s: %s", department, e)
        return []