import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Request, HTTPException, Response
from . import config
from .db import _sb, get_one, db_insert, db_update, now


def extract_token(request: Request) -> Optional[str]:
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    return token or None


def get_user_by_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    session = get_one("user_sessions", session_token=token)
    if not session:
        return None
    exp = datetime.fromisoformat(session["expires_at"])
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        return None
    return get_one("users", user_id=session["user_id"])


def require_auth(request: Request) -> dict:
    user = get_user_by_token(extract_token(request))
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


def require_admin(request: Request) -> dict:
    user = require_auth(request)
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def set_session_cookie(response: Response, token: str, max_age: int = config.SESSION_TTL_DAYS * 86400):
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=config.SECURE_COOKIE,
        samesite="none" if config.SECURE_COOKIE else "lax",
        path="/",
        max_age=max_age,
    )


def upsert_user(email: str, name: str, picture: Optional[str], response: Response) -> dict:
    import uuid as _uuid
    existing = get_one("users", email=email)
    token = secrets.token_urlsafe(32)
    ts = now()

    if existing:
        uid = existing["user_id"]
        role = "admin" if email in config.ADMIN_EMAILS else existing["role"]
        db_update("users", {"name": name, "picture": picture, "role": role, "last_login_at": ts}, user_id=uid)
    else:
        uid = f"user_{_uuid.uuid4().hex[:12]}"
        role = "admin" if email in config.ADMIN_EMAILS else "employee"
        db_insert("users", {
            "user_id": uid, "email": email, "name": name, "picture": picture,
            "role": role, "department": None, "created_at": ts, "last_login_at": ts,
            "phone_number": None, "wa_api_key": None,
        })

    expires = (datetime.now(timezone.utc) + timedelta(days=config.SESSION_TTL_DAYS)).isoformat()
    db_insert("user_sessions", {"session_token": token, "user_id": uid, "expires_at": expires, "created_at": ts})
    user = get_one("users", user_id=uid)
    set_session_cookie(response, token)
    return user