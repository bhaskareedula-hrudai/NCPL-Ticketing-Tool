import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Request, HTTPException, Response
from . import config
from .db import connect, one, now


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
    conn = connect()
    session = one(conn, "SELECT * FROM user_sessions WHERE session_token=?", (token,))
    if not session:
        conn.close()
        return None
    exp = datetime.fromisoformat(session["expires_at"])
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        conn.close()
        return None
    user = one(conn, "SELECT * FROM users WHERE user_id=?", (session["user_id"],))
    conn.close()
    return user


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
    conn = connect()
    existing = one(conn, "SELECT * FROM users WHERE email=?", (email,))
    token = secrets.token_urlsafe(32)
    ts = now()

    if existing:
        uid = existing["user_id"]
        role = "admin" if email in config.ADMIN_EMAILS else existing["role"]
        conn.execute(
            "UPDATE users SET name=?, picture=?, role=?, last_login_at=? WHERE user_id=?",
            (name, picture, role, ts, uid),
        )
    else:
        uid = f"user_{_uuid.uuid4().hex[:12]}"
        role = "admin" if email in config.ADMIN_EMAILS else "employee"
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
            (uid, email, name, picture, role, None, ts, ts),
        )

    expires = (datetime.now(timezone.utc) + timedelta(days=config.SESSION_TTL_DAYS)).isoformat()
    conn.execute("INSERT INTO user_sessions VALUES (?,?,?,?)", (token, uid, expires, ts))
    conn.commit()
    user = one(conn, "SELECT * FROM users WHERE user_id=?", (uid,))
    conn.close()
    set_session_cookie(response, token)
    return user
