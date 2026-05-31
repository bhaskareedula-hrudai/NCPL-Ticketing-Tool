import secrets
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from typing import Optional

import requests as http_requests
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse

from ..auth import extract_token, get_user_by_token, require_admin, set_session_cookie, upsert_user
from ..db import connect, one, now, new_id
from .. import config
from ..models import DevLoginIn

router = APIRouter(tags=["auth"])


@router.get("/auth/google")
def initiate_google_oauth():
    if not config.GOOGLE_CLIENT_ID:
        return RedirectResponse(f"{config.FRONTEND_URL}/login?dev=true")
    params = urlencode({
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{config.BASE_URL}/api/auth/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": secrets.token_urlsafe(16),
        "access_type": "online",
        "prompt": "select_account",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/auth/callback")
def google_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    if error or not code:
        return RedirectResponse(f"{config.FRONTEND_URL}/login?error=auth_failed")
    try:
        token_res = http_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{config.BASE_URL}/api/auth/callback",
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        token_res.raise_for_status()
        user_info = http_requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_res.json()['access_token']}"},
            timeout=15,
        )
        user_info.raise_for_status()
        profile = user_info.json()
    except Exception as exc:
        import logging
        body = getattr(getattr(exc, "response", None), "text", "")
        logging.getLogger("ncpl").error("OAuth failed: %s | Google says: %s", exc, body)
        return RedirectResponse(f"{config.FRONTEND_URL}/login?error=auth_failed")

    email = profile["email"].lower()
    resp = RedirectResponse(f"{config.FRONTEND_URL}/auth/callback")
    try:
        upsert_user(email, profile.get("name", ""), profile.get("picture"), resp)
    except Exception as exc:
        import logging
        logging.getLogger("ncpl").error("upsert_user failed for %s: %s", email, exc)
        return RedirectResponse(f"{config.FRONTEND_URL}/login?error=auth_failed")
    return resp


@router.post("/auth/dev-login")
def dev_login(payload: DevLoginIn, response: Response):
    if config.GOOGLE_CLIENT_ID:
        raise HTTPException(403, "Dev login disabled in production")
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")
    user = upsert_user(email, email.split("@")[0], None, response)
    return {"user": user}


@router.get("/auth/me")
def get_current_user(request: Request):
    from ..auth import require_auth
    return require_auth(request)


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    token = extract_token(request)
    if token:
        conn = connect()
        conn.execute("DELETE FROM user_sessions WHERE session_token=?", (token,))
        conn.commit()
        conn.close()
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@router.post("/auth/preview-employee")
def preview_as_employee(request: Request, response: Response):
    require_admin(request)
    demo_email = "demo.employee@ncpl.preview"
    conn = connect()
    demo = one(conn, "SELECT * FROM users WHERE email=?", (demo_email,))
    if not demo:
        uid = new_id("user")
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
            (uid, demo_email, "Demo Employee", None, "employee", "HR", now(), now()),
        )
        conn.commit()
        demo = one(conn, "SELECT * FROM users WHERE user_id=?", (uid,))

    preview_token = f"preview_{secrets.token_urlsafe(24)}"
    expires = (datetime.now(timezone.utc) + timedelta(hours=config.PREVIEW_SESSION_HOURS)).isoformat()
    conn.execute("INSERT INTO user_sessions VALUES (?,?,?,?)", (preview_token, demo["user_id"], expires, now()))
    conn.commit()
    conn.close()
    set_session_cookie(response, preview_token, max_age=config.PREVIEW_SESSION_HOURS * 3600)
    return {"user": demo, "preview": True}
