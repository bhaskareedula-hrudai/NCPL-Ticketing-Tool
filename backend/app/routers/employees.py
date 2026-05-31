from fastapi import APIRouter, HTTPException, Request

from ..auth import require_auth, require_admin
from ..db import connect, one, many, new_id, now
from ..models import EmployeePatch, EmployeeCreate
from .. import config

router = APIRouter(tags=["employees"])


@router.get("/employees")
def list_employees(request: Request):
    require_admin(request)
    conn = connect()
    rows = many(conn, "SELECT * FROM users ORDER BY name")
    conn.close()
    return rows


@router.get("/employees/assignable")
def list_assignable(request: Request):
    require_auth(request)
    conn = connect()
    rows = many(conn, "SELECT * FROM users WHERE role='admin' ORDER BY name")
    conn.close()
    return rows


@router.get("/departments/{dept_name}/members")
def get_department_members(dept_name: str, request: Request):
    require_auth(request)
    return config.DEPARTMENT_MEMBERS.get(dept_name, [])

@router.post("/employees")
def add_employee(body: EmployeeCreate, request: Request):
    require_admin(request)
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")
    conn = connect()
    if one(conn, "SELECT user_id FROM users WHERE email=?", (email,)):
        conn.close()
        raise HTTPException(409, "A user with this email already exists")
    uid = new_id("user")
    role = "admin" if email in config.ADMIN_EMAILS else body.role
    ts = now()
    name = body.name.strip() if body.name and body.name.strip() else email.split("@")[0]
    conn.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
        (uid, email, name, None, role, body.department, ts, ts),
    )
    conn.commit()
    user = one(conn, "SELECT * FROM users WHERE user_id=?", (uid,))
    conn.close()
    return user


@router.delete("/employees/{user_id}")
def delete_employee(user_id: str, request: Request):
    me = require_admin(request)
    if me["user_id"] == user_id:
        raise HTTPException(400, "You cannot delete your own account")
    conn = connect()
    user = one(conn, "SELECT * FROM users WHERE user_id=?", (user_id,))
    if not user:
        conn.close()
        raise HTTPException(404, "Employee not found")
    conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
@router.patch("/employees/{user_id}")
def update_employee(user_id: str, body: EmployeePatch, request: Request):
    require_admin(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        conn = connect()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE users SET {set_clause} WHERE user_id=?",
            list(updates.values()) + [user_id],
        )
        conn.commit()
        user = one(conn, "SELECT * FROM users WHERE user_id=?", (user_id,))
        conn.close()
        if not user:
            raise HTTPException(404, "Not found")
        return user
    conn = connect()
    user = one(conn, "SELECT * FROM users WHERE user_id=?", (user_id,))
    conn.close()
    if not user:
        raise HTTPException(404, "Not found")
    return user
