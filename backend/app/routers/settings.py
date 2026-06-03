from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

from ..auth import require_admin
from ..db import connect, one

router = APIRouter(tags=["settings"])


class WhatsAppSettings(BaseModel):
    instance_id: Optional[str] = None
    token: Optional[str] = None
    phone_map: Optional[str] = None


def _get_setting(conn, key: str):
    row = one(conn, "SELECT value FROM app_settings WHERE key=?", (key,))
    return row["value"] if row else None


def _set_setting(conn, key: str, value: str):
    conn.execute("DELETE FROM app_settings WHERE key=?", (key,))
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)", (key, value))


@router.get("/settings/whatsapp")
def get_whatsapp_settings(request: Request):
    require_admin(request)
    conn = connect()
    result = {
        "instance_id": _get_setting(conn, "wa_instance_id") or "",
        "token": _get_setting(conn, "wa_token") or "",
        "phone_map": _get_setting(conn, "wa_phone_map") or "",
    }
    conn.close()
    token = result["token"]
    result["token_masked"] = (token[:6] + "…" + token[-4:]) if len(token) > 10 else ("*" * len(token) if token else "")
    return result


@router.patch("/settings/whatsapp")
def save_whatsapp_settings(body: WhatsAppSettings, request: Request):
    require_admin(request)
    conn = connect()
    if body.instance_id is not None:
        _set_setting(conn, "wa_instance_id", body.instance_id.strip())
    if body.token is not None:
        _set_setting(conn, "wa_token", body.token.strip())
    if body.phone_map is not None:
        _set_setting(conn, "wa_phone_map", body.phone_map.strip())
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/settings/whatsapp/status")
def whatsapp_status(request: Request):
    require_admin(request)
    from .. import wa_web
    return wa_web.get_status()


@router.post("/settings/whatsapp/logout")
def whatsapp_logout(request: Request):
    require_admin(request)
    from .. import wa_web
    wa_web.logout()
    return {"ok": True}


@router.post("/settings/whatsapp/test")
def test_whatsapp(request: Request):
    require_admin(request)
    from .. import whatsapp
    sent = whatsapp.send_test_message()
    if sent:
        return {"ok": True, "message": "Test message sent successfully"}
    return {
        "ok": False,
        "message": "Failed — scan the QR code in the WhatsApp Web section, or check Green API credentials",
    }