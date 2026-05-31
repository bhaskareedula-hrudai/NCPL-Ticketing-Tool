from fastapi import APIRouter, HTTPException, Request

from ..auth import require_auth, require_admin
from ..db import connect, one, many, new_id, now
from ..models import DepartmentIn

router = APIRouter(tags=["departments"])


@router.get("/departments")
def list_departments(request: Request):
    require_auth(request)
    conn = connect()
    rows = many(conn, "SELECT * FROM departments ORDER BY name")
    conn.close()
    return rows


@router.post("/departments")
def create_department(body: DepartmentIn, request: Request):
    require_admin(request)
    conn = connect()
    if one(conn, "SELECT id FROM departments WHERE name=?", (body.name,)):
        conn.close()
        raise HTTPException(400, "Department already exists")
    dept = {
        "id": new_id("dept"),
        "name": body.name,
        "description": body.description or "",
        "created_at": now(),
    }
    conn.execute(
        "INSERT INTO departments (id, name, description, created_at) VALUES (:id,:name,:description,:created_at)",
        dept,
    )
    conn.commit()
    conn.close()
    return dept


@router.patch("/departments/{dept_id}")
def update_department(dept_id: str, body: DepartmentIn, request: Request):
    require_admin(request)
    conn = connect()
    conn.execute(
        "UPDATE departments SET name=?, description=? WHERE id=?",
        (body.name, body.description or "", dept_id),
    )
    conn.commit()
    dept = one(conn, "SELECT * FROM departments WHERE id=?", (dept_id,))
    conn.close()
    if not dept:
        raise HTTPException(404, "Not found")
    return dept


@router.delete("/departments/{dept_id}")
def delete_department(dept_id: str, request: Request):
    require_admin(request)
    conn = connect()
    conn.execute("DELETE FROM departments WHERE id=?", (dept_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
