from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

from ..auth import require_admin
from ..db import _sb, get_one, db_insert, db_delete

router = APIRouter(tags=["settings"])


class WhatsAppSettings(BaseModel):
    instance_id: Optional[str] = None
    token: Optional[str] = None
    phone_map: Optional[str] = None


def _get_setting(key: str) -> Optional[str]:
    row = get_one("app_settings", key=key)
    return row["value"] if row else None


def _set_setting(key: str, value: str):
    db_delete("app_settings", key=key)
    db_insert("app_settings", {"key": key, "value": value})


@router.get("/settings/whatsapp")
def get_whatsapp_settings(request: Request):
    require_admin(request)
    result = {
        "instance_id": _get_setting("wa_instance_id") or "",
        "token": _get_setting("wa_token") or "",
        "phone_map": _get_setting("wa_phone_map") or "",
    }
    token = result["token"]
    result["token_masked"] = (token[:6] + "…" + token[-4:]) if len(token) > 10 else ("*" * len(token) if token else "")
    return result


@router.patch("/settings/whatsapp")
def save_whatsapp_settings(body: WhatsAppSettings, request: Request):
    require_admin(request)
    if body.instance_id is not None:
        _set_setting("wa_instance_id", body.instance_id.strip())
    if body.token is not None:
        _set_setting("wa_token", body.token.strip())
    if body.phone_map is not None:
        _set_setting("wa_phone_map", body.phone_map.strip())
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
    return {"ok": False, "message": "Failed — check Green API credentials or WhatsApp Web QR code"}