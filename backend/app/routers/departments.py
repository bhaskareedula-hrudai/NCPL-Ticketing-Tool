from fastapi import APIRouter, HTTPException, Request

from ..auth import require_auth, require_admin
from ..db import get_one, get_many, db_insert, db_update, db_delete, new_id, now
from ..models import DepartmentIn

router = APIRouter(tags=["departments"])


@router.get("/departments")
def list_departments(request: Request):
    require_auth(request)
    return get_many("departments", order_col="name", desc=False)


@router.post("/departments")
def create_department(body: DepartmentIn, request: Request):
    require_admin(request)
    if get_one("departments", name=body.name):
        raise HTTPException(400, "Department already exists")
    dept = {
        "id": new_id("dept"),
        "name": body.name,
        "description": body.description or "",
        "created_at": now(),
    }
    db_insert("departments", dept)
    return dept


@router.patch("/departments/{dept_id}")
def update_department(dept_id: str, body: DepartmentIn, request: Request):
    require_admin(request)
    result = db_update("departments", {"name": body.name, "description": body.description or ""}, id=dept_id)
    if not result:
        raise HTTPException(404, "Not found")
    return result


@router.delete("/departments/{dept_id}")
def delete_department(dept_id: str, request: Request):
    require_admin(request)
    db_delete("departments", id=dept_id)
    return {"ok": True}