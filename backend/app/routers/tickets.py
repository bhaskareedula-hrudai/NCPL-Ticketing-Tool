import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response, UploadFile, File
from fastapi.responses import Response as HttpResponse

from ..auth import require_auth, require_admin, extract_token, get_user_by_token
from ..db import _sb, get_one, db_insert, db_update, db_delete, new_id, now, next_ticket_code, ticket_with_counts
from .. import config, whatsapp
from ..models import AssignIn, CommentIn, StatusIn, TicketCreate, TicketUpdate

logger = logging.getLogger("ncpl")
router = APIRouter(tags=["tickets"])


@router.post("/tickets")
def create_ticket(body: TicketCreate, request: Request):
    user = require_auth(request)
    if not get_one("departments", name=body.department):
        raise HTTPException(400, "Invalid department")

    assignee_name = None
    if body.assignee_name:
        allowed = config.DEPARTMENT_MEMBERS.get(body.department, [])
        if body.assignee_name not in allowed:
            raise HTTPException(400, "Invalid assignee for this department")
        assignee_name = body.assignee_name

    ts = now()
    ticket = {
        "id": new_id("tkt"),
        "code": next_ticket_code(),
        "title": body.title,
        "description": body.description,
        "status": "Open",
        "priority": body.priority,
        "department": body.department,
        "created_by": user["user_id"],
        "created_by_name": user["name"] or user["email"],
        "created_by_email": user["email"],
        "assignee_id": None,
        "assignee_name": assignee_name,
        "due_at": None,
        "is_escalated": 0,
        "escalated_at": None,
        "resolved_at": None,
        "closed_at": None,
        "created_at": ts,
        "updated_at": ts,
    }
    db_insert("tickets", ticket)
    result = ticket_with_counts(ticket)

    if assignee_name:
        try:
            whatsapp.send_ticket_assigned(result)
        except Exception as exc:
            logger.warning("WhatsApp notification failed for ticket %s: %s", result.get("code"), exc)

    return result


@router.get("/tickets")
def list_tickets(
    request: Request,
    status: Optional[str] = None,
    department: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[str] = None,
    scope: Optional[str] = Query(None),
    q: Optional[str] = None,
):
    user = require_auth(request)
    uid = user["user_id"]
    is_admin = user["role"] == "admin"
    user_name = user.get("name") or ""

    query = _sb().table("tickets").select("*")

    if scope == "mine":
        query = query.eq("created_by", uid)
    elif not is_admin:
        query = query.or_(f"created_by.eq.{uid},assignee_id.eq.{uid},and(assignee_name.eq.{user_name},assignee_id.is.null)")

    if scope == "unassigned":
        query = query.filter("assignee_id", "is", "null").filter("assignee_name", "is", "null").not_.in_("status", ["Resolved", "Closed"])
    elif scope == "assigned_to_me":
        query = query.or_(f"assignee_id.eq.{uid},and(assignee_name.eq.{user_name},assignee_id.is.null)")
    elif scope == "escalated":
        query = query.eq("is_escalated", 1)
    elif scope == "high_priority":
        query = query.in_("priority", ["High", "Urgent"])
    elif scope == "active":
        query = query.in_("status", ["Open", "In Progress", "Pending"])
    elif scope == "resolved":
        query = query.eq("status", "Resolved")
    elif scope == "closed":
        query = query.eq("status", "Closed")
    elif scope == "overdue":
        query = query.not_.filter("due_at", "is", "null").lt("due_at", now()).not_.in_("status", ["Resolved", "Closed"])

    if status:
        query = query.eq("status", status)
    if department:
        query = query.eq("department", department)
    if priority:
        query = query.eq("priority", priority)
    if assignee_id:
        query = query.eq("assignee_id", assignee_id)
    if q:
        query = query.or_(f"title.ilike.%{q}%,description.ilike.%{q}%,code.ilike.%{q}%")

    rows = query.order("created_at", desc=True).execute().data or []
    return [ticket_with_counts(r) for r in rows]


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, request: Request):
    require_auth(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    return ticket_with_counts(ticket)


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, body: TicketUpdate, request: Request):
    user = require_auth(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    if user["role"] != "admin" and ticket["created_by"] != user["user_id"]:
        raise HTTPException(403, "Forbidden")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        updates["updated_at"] = now()
        if updates.get("status") == "Resolved":
            updates["resolved_at"] = now()
        elif updates.get("status") == "Closed":
            updates["closed_at"] = now()
        if "assignee_id" in updates:
            emp = get_one("users", user_id=updates["assignee_id"]) if updates["assignee_id"] else None
            updates["assignee_name"] = emp["name"] if emp else None
        db_update("tickets", updates, id=ticket_id)

    return ticket_with_counts(get_one("tickets", id=ticket_id))


@router.post("/tickets/{ticket_id}/status")
def change_status(ticket_id: str, body: StatusIn, request: Request):
    user = require_auth(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        raise HTTPException(403, "Forbidden")

    updates = {"status": body.status, "updated_at": now()}
    if body.status == "Resolved":
        updates["resolved_at"] = now()
    elif body.status == "Closed":
        updates["closed_at"] = now()

    db_update("tickets", updates, id=ticket_id)
    return ticket_with_counts(get_one("tickets", id=ticket_id))


@router.post("/tickets/{ticket_id}/assign")
def assign_ticket(ticket_id: str, body: AssignIn, request: Request):
    require_admin(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")

    assignee_name = None
    if body.assignee_id:
        emp = get_one("users", user_id=body.assignee_id)
        assignee_name = emp["name"] if emp else None

    db_update("tickets", {"assignee_id": body.assignee_id, "assignee_name": assignee_name, "updated_at": now()}, id=ticket_id)
    return ticket_with_counts(get_one("tickets", id=ticket_id))


@router.post("/tickets/{ticket_id}/escalate")
def escalate_ticket(ticket_id: str, request: Request):
    require_admin(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    ts = now()
    db_update("tickets", {"is_escalated": 1, "escalated_at": ts, "updated_at": ts}, id=ticket_id)
    return ticket_with_counts(get_one("tickets", id=ticket_id))


@router.get("/tickets/{ticket_id}/comments")
def list_comments(ticket_id: str, request: Request):
    user = require_auth(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        raise HTTPException(403, "Forbidden")

    q = _sb().table("comments").select("*").eq("ticket_id", ticket_id)
    if user["role"] != "admin":
        q = q.eq("is_internal", 0)
    rows = q.order("created_at").execute().data or []
    for r in rows:
        r["is_internal"] = bool(r.get("is_internal", 0))
    return rows


@router.post("/tickets/{ticket_id}/comments")
def add_comment(ticket_id: str, body: CommentIn, request: Request):
    user = require_auth(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        raise HTTPException(403, "Forbidden")
    if body.is_internal and user["role"] != "admin":
        raise HTTPException(403, "Only admins can post internal notes")

    comment = {
        "id": new_id("cmt"),
        "ticket_id": ticket_id,
        "body": body.body,
        "is_internal": 1 if body.is_internal else 0,
        "author_id": user["user_id"],
        "author_name": user["name"] or user["email"],
        "author_role": user["role"],
        "created_at": now(),
    }
    db_insert("comments", comment)
    db_update("tickets", {"updated_at": now()}, id=ticket_id)
    comment["is_internal"] = bool(comment["is_internal"])
    return comment


@router.post("/tickets/{ticket_id}/attachments")
async def upload_attachment(ticket_id: str, request: Request, file: UploadFile = File(...)):
    user = get_user_by_token(extract_token(request))
    if not user:
        raise HTTPException(401, "Not authenticated")

    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        raise HTTPException(403, "Forbidden")

    data = await file.read()
    if len(data) > config.MAX_ATTACHMENT_BYTES:
        raise HTTPException(400, "File too large (max 15 MB)")

    attachment = {
        "id": new_id("att"),
        "ticket_id": ticket_id,
        "filename": file.filename,
        "content_type": file.content_type or "application/octet-stream",
        "size": len(data),
        "data": list(data),
        "uploaded_by": user["user_id"],
        "uploaded_by_name": user["name"] or user["email"],
        "created_at": now(),
        "is_deleted": 0,
    }
    db_insert("attachments", attachment)
    attachment.pop("data")
    return attachment


@router.get("/tickets/{ticket_id}/attachments")
def list_attachments(ticket_id: str, request: Request):
    user = require_auth(request)
    ticket = get_one("tickets", id=ticket_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        raise HTTPException(403, "Forbidden")
    rows = _sb().table("attachments").select(
        "id,ticket_id,filename,content_type,size,uploaded_by,uploaded_by_name,created_at"
    ).eq("ticket_id", ticket_id).eq("is_deleted", 0).execute().data or []
    return rows


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: str,
    request: Request,
    auth_token: Optional[str] = Query(None, alias="auth"),
):
    token = request.cookies.get("session_token") or auth_token
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Not authenticated")

    att = get_one("attachments", id=attachment_id)
    if not att or att.get("is_deleted"):
        raise HTTPException(404, "Not found")
    ticket = get_one("tickets", id=att["ticket_id"])
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        raise HTTPException(403, "Forbidden")

    raw = att["data"]
    content = bytes(raw) if isinstance(raw, list) else bytes(raw)
    return HttpResponse(
        content=content,
        media_type=att["content_type"],
        headers={"Content-Disposition": f'inline; filename="{att["filename"]}"'},
    )