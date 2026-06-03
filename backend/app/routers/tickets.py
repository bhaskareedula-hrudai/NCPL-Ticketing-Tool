from ..whatsapp import send_ticket_notification
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response, UploadFile, File
from fastapi.responses import Response as HttpResponse

from ..auth import require_auth, require_admin, extract_token, get_user_by_token
from ..db import connect, one, many, new_id, now, next_ticket_code, ticket_with_counts
from .. import config
from ..models import AssignIn, CommentIn, StatusIn, TicketCreate, TicketUpdate
from .. import whatsapp 
router = APIRouter(tags=["tickets"])


# ── Ticket CRUD ──────────────────────────────────────────────────────────────

@router.post("/tickets")
def create_ticket(body: TicketCreate, request: Request):
    user = require_auth(request)
    conn = connect()
    if not one(conn, "SELECT id FROM departments WHERE name=?", (body.department,)):
        conn.close()
        raise HTTPException(400, "Invalid department")
    conn.close()

    # Validate assignee name against the department's member list
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
    conn = connect()
    conn.execute(
        """INSERT INTO tickets VALUES
        (:id,:code,:title,:description,:status,:priority,:department,
         :created_by,:created_by_name,:created_by_email,
         :assignee_id,:assignee_name,:due_at,:is_escalated,
         :escalated_at,:resolved_at,:closed_at,:created_at,:updated_at)""",
        ticket,
    )
    conn.commit()
    conn.close()
    return ticket_with_counts(ticket)
    if assignee_name:                             
        whatsapp.send_ticket_assigned(result)
    return result

    conn.commit()
    conn.close()

    if assignee_name:
        send_ticket_notification(
            assignee_name=assignee_name,
            ticket_code=ticket["code"],
            ticket_title=ticket["title"],
            created_by=ticket["created_by_name"],
        )

    return ticket_with_counts(ticket)

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

    where, params = _build_visibility(is_admin, uid, user_name, scope)

    if status:
        where.append("status=?")
        params.append(status)
    if department:
        where.append("department=?")
        params.append(department)
    if priority:
        where.append("priority=?")
        params.append(priority)
    if assignee_id:
        where.append("assignee_id=?")
        params.append(assignee_id)
    if q:
        where.append("(title LIKE ? OR description LIKE ? OR code LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like]

    sql = "SELECT * FROM tickets"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC"

    conn = connect()
    rows = many(conn, sql, params)
    conn.close()
    return [ticket_with_counts(r) for r in rows]


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, request: Request):
    require_auth(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    conn.close()
    if not ticket:
        raise HTTPException(404, "Not found")
    return ticket_with_counts(ticket)


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, body: TicketUpdate, request: Request):
    user = require_auth(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        conn.close()
        raise HTTPException(404, "Not found")
    if user["role"] != "admin" and ticket["created_by"] != user["user_id"]:
        conn.close()
        raise HTTPException(403, "Forbidden")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        updates["updated_at"] = now()
        if updates.get("status") == "Resolved":
            updates["resolved_at"] = now()
        elif updates.get("status") == "Closed":
            updates["closed_at"] = now()
        if "assignee_id" in updates:
            emp = one(conn, "SELECT name FROM users WHERE user_id=?", (updates["assignee_id"],)) if updates["assignee_id"] else None
            updates["assignee_name"] = emp["name"] if emp else None

        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE tickets SET {set_clause} WHERE id=?",
            list(updates.values()) + [ticket_id],
        )
        conn.commit()

    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    conn.close()
    return ticket_with_counts(ticket)


# ── Ticket actions ───────────────────────────────────────────────────────────

@router.post("/tickets/{ticket_id}/status")
def change_status(ticket_id: str, body: StatusIn, request: Request):
    user = require_auth(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        conn.close()
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        conn.close()
        raise HTTPException(403, "Forbidden")

    extra_cols = []
    extra_vals = []
    if body.status == "Resolved":
        extra_cols.append("resolved_at=?")
        extra_vals.append(now())
    elif body.status == "Closed":
        extra_cols.append("closed_at=?")
        extra_vals.append(now())

    parts = ["status=?", "updated_at=?"] + extra_cols
    conn.execute(
        f"UPDATE tickets SET {', '.join(parts)} WHERE id=?",
        [body.status, now()] + extra_vals + [ticket_id],
    )
    conn.commit()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    conn.close()
    return ticket_with_counts(ticket)


@router.post("/tickets/{ticket_id}/assign")
def assign_ticket(ticket_id: str, body: AssignIn, request: Request):
    require_admin(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        conn.close()
        raise HTTPException(404, "Not found")

    assignee_name = None
    if body.assignee_id:
        emp = one(conn, "SELECT name FROM users WHERE user_id=?", (body.assignee_id,))
        assignee_name = emp["name"] if emp else None

    conn.execute(
        "UPDATE tickets SET assignee_id=?, assignee_name=?, updated_at=? WHERE id=?",
        (body.assignee_id, assignee_name, now(), ticket_id),
    )
    conn.commit()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    conn.close()
    return ticket_with_counts(ticket)


@router.post("/tickets/{ticket_id}/escalate")
def escalate_ticket(ticket_id: str, request: Request):
    require_admin(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        conn.close()
        raise HTTPException(404, "Not found")
    ts = now()
    conn.execute(
        "UPDATE tickets SET is_escalated=1, escalated_at=?, updated_at=? WHERE id=?",
        (ts, ts, ticket_id),
    )
    conn.commit()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    conn.close()
    return ticket_with_counts(ticket)


# ── Comments ─────────────────────────────────────────────────────────────────

@router.get("/tickets/{ticket_id}/comments")
def list_comments(ticket_id: str, request: Request):
    user = require_auth(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        conn.close()
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        conn.close()
        raise HTTPException(403, "Forbidden")

    if user["role"] == "admin":
        rows = many(conn, "SELECT * FROM comments WHERE ticket_id=? ORDER BY created_at", (ticket_id,))
    else:
        rows = many(conn, "SELECT * FROM comments WHERE ticket_id=? AND is_internal=0 ORDER BY created_at", (ticket_id,))
    conn.close()
    for r in rows:
        r["is_internal"] = bool(r.get("is_internal", 0))
    return rows


@router.post("/tickets/{ticket_id}/comments")
def add_comment(ticket_id: str, body: CommentIn, request: Request):
    user = require_auth(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        conn.close()
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        conn.close()
        raise HTTPException(403, "Forbidden")
    if body.is_internal and user["role"] != "admin":
        conn.close()
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
    conn.execute(
        "INSERT INTO comments VALUES (:id,:ticket_id,:body,:is_internal,:author_id,:author_name,:author_role,:created_at)",
        comment,
    )
    conn.execute("UPDATE tickets SET updated_at=? WHERE id=?", (now(), ticket_id))
    conn.commit()
    conn.close()
    comment["is_internal"] = bool(comment["is_internal"])
    return comment


# ── Attachments ──────────────────────────────────────────────────────────────

@router.post("/tickets/{ticket_id}/attachments")
async def upload_attachment(ticket_id: str, request: Request, file: UploadFile = File(...)):
    user = get_user_by_token(extract_token(request))
    if not user:
        raise HTTPException(401, "Not authenticated")

    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    conn.close()
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
        "uploaded_by": user["user_id"],
        "uploaded_by_name": user["name"] or user["email"],
        "created_at": now(),
        "is_deleted": 0,
    }
    conn = connect()
    conn.execute(
        "INSERT INTO attachments(id,ticket_id,filename,content_type,size,data,uploaded_by,uploaded_by_name,created_at,is_deleted) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            attachment["id"], attachment["ticket_id"], attachment["filename"],
            attachment["content_type"], attachment["size"], data,
            attachment["uploaded_by"], attachment["uploaded_by_name"],
            attachment["created_at"], attachment["is_deleted"],
        ),
    )
    conn.commit()
    conn.close()
    return attachment


@router.get("/tickets/{ticket_id}/attachments")
def list_attachments(ticket_id: str, request: Request):
    user = require_auth(request)
    conn = connect()
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        conn.close()
        raise HTTPException(404, "Not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        conn.close()
        raise HTTPException(403, "Forbidden")
    rows = many(
        conn,
        "SELECT id,ticket_id,filename,content_type,size,uploaded_by,uploaded_by_name,created_at FROM attachments WHERE ticket_id=? AND is_deleted=0",
        (ticket_id,),
    )
    conn.close()
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

    conn = connect()
    att = one(conn, "SELECT * FROM attachments WHERE id=? AND is_deleted=0", (attachment_id,))
    if not att:
        conn.close()
        raise HTTPException(404, "Not found")
    ticket = one(conn, "SELECT * FROM tickets WHERE id=?", (att["ticket_id"],))
    conn.close()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if (
        user["role"] != "admin"
        and ticket["created_by"] != user["user_id"]
        and ticket["assignee_id"] != user["user_id"]
    ):
        raise HTTPException(403, "Forbidden")

    return HttpResponse(
        content=bytes(att["data"]),
        media_type=att["content_type"],
        headers={"Content-Disposition": f'inline; filename="{att["filename"]}"'},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_visibility(is_admin: bool, uid: str, user_name: str, scope: Optional[str]) -> tuple:
    where, params = [], []

    if scope == "mine":
        where.append("created_by=?")
        params.append(uid)
        return where, params

    if not is_admin:
        # Include tickets assigned by name (no user_id) when name matches
        where.append("(created_by=? OR assignee_id=? OR (assignee_name=? AND assignee_id IS NULL))")
        params += [uid, uid, user_name]

    if scope == "unassigned":
        where.append("assignee_id IS NULL AND assignee_name IS NULL")
        where.append("status NOT IN ('Resolved','Closed')")
    elif scope == "assigned_to_me":
        where.append("(assignee_id=? OR (assignee_name=? AND assignee_id IS NULL))")
        params += [uid, user_name]
    elif scope == "escalated":
        where.append("is_escalated=1")
    elif scope == "high_priority":
        where.append("priority IN ('High','Urgent')")
    elif scope == "active":
        where.append("status IN ('Open','In Progress','Pending')")
    elif scope == "resolved":
        where.append("status='Resolved'")
    elif scope == "closed":
        where.append("status='Closed'")
    elif scope == "overdue":
        where.append("due_at IS NOT NULL AND due_at < ? AND status NOT IN ('Resolved','Closed')")
        params.append(now())

    return where, params
