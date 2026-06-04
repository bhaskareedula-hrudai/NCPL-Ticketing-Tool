import secrets
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from typing import Optional

import requests as http_requests
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse

from ..auth import extract_token, get_user_by_token, require_admin, set_session_cookie, upsert_user
from ..db import get_one, db_insert, db_delete, new_id, now
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

    email = profile.get("email", "").lower()
    if not email:
        return RedirectResponse(f"{config.FRONTEND_URL}/login?error=auth_failed")

    try:
        existing = get_one("users", email=email)
        if not existing and email not in config.ADMIN_EMAILS:
            return RedirectResponse(f"{config.FRONTEND_URL}/login?error=not_invited")
    except Exception:
        if email not in config.ADMIN_EMAILS:
            return RedirectResponse(f"{config.FRONTEND_URL}/login?error=auth_failed")

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
        db_delete("user_sessions", session_token=token)
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@router.post("/auth/preview-employee")
def preview_as_employee(request: Request, response: Response):
    require_admin(request)
    demo_email = "demo.employee@ncpl.preview"
    ts = now()
    demo = get_one("users", email=demo_email)
    if not demo:
        uid = new_id("user")
        db_insert("users", {
            "user_id": uid, "email": demo_email, "name": "Demo Employee",
            "picture": None, "role": "employee", "department": "HR",
            "created_at": ts, "last_login_at": ts,
            "phone_number": None, "wa_api_key": None,
        })
        demo = get_one("users", user_id=uid)

    preview_token = f"preview_{secrets.token_urlsafe(24)}"
    expires = (datetime.now(timezone.utc) + timedelta(hours=config.PREVIEW_SESSION_HOURS)).isoformat()
    db_insert("user_sessions", {"session_token": preview_token, "user_id": demo["user_id"], "expires_at": expires, "created_at": ts})
    set_session_cookie(response, preview_token, max_age=config.PREVIEW_SESSION_HOURS * 3600)
    return {"user": demo, "preview": True}