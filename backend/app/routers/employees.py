from fastapi import APIRouter, HTTPException, Request

from ..auth import require_auth, require_admin
from ..db import connect, one, many
from ..models import EmployeePatch
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
