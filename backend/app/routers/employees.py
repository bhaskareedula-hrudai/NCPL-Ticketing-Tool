from fastapi import APIRouter, HTTPException, Request

from ..auth import require_auth, require_admin
from ..db import get_one, get_many, db_insert, db_update, db_delete, new_id, now
from ..models import EmployeePatch, EmployeeCreate
from .. import config

router = APIRouter(tags=["employees"])


@router.get("/employees")
def list_employees(request: Request):
    require_admin(request)
    return get_many("users", order_col="name", desc=False)


@router.get("/employees/assignable")
def list_assignable(request: Request):
    require_auth(request)
    return get_many("users", order_col="name", desc=False, role="admin")


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
    if get_one("users", email=email):
        raise HTTPException(409, "A user with this email already exists")
    uid = new_id("user")
    role = "admin" if email in config.ADMIN_EMAILS else body.role
    ts = now()
    name = body.name.strip() if body.name and body.name.strip() else email.split("@")[0]
    phone = body.phone_number.strip() if body.phone_number and body.phone_number.strip() else None
    wa_key = body.wa_api_key.strip() if body.wa_api_key and body.wa_api_key.strip() else None
    db_insert("users", {
        "user_id": uid, "email": email, "name": name, "picture": None,
        "role": role, "department": body.department, "created_at": ts, "last_login_at": ts,
        "phone_number": phone, "wa_api_key": wa_key,
    })
    return get_one("users", user_id=uid)


@router.delete("/employees/{user_id}")
def delete_employee(user_id: str, request: Request):
    me = require_admin(request)
    if me["user_id"] == user_id:
        raise HTTPException(400, "You cannot delete your own account")
    if not get_one("users", user_id=user_id):
        raise HTTPException(404, "Employee not found")
    db_delete("users", user_id=user_id)
    return {"ok": True}


@router.patch("/employees/{user_id}")
def update_employee(user_id: str, body: EmployeePatch, request: Request):
    require_admin(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        result = db_update("users", updates, user_id=user_id)
        if not result:
            raise HTTPException(404, "Not found")
        return result
    user = get_one("users", user_id=user_id)
    if not user:
        raise HTTPException(404, "Not found")
    return user