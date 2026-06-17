import logging
from typing import Optional

from . import config

logger = logging.getLogger(__name__)


def _get_phone_map() -> dict[str, str]:
    from .db import get_one
    try:
        row = get_one("app_settings", key="wa_phone_map")
        raw = (row["value"] if row else "") or config.WHATSAPP_PHONE_MAP_RAW
    except Exception:
        raw = config.WHATSAPP_PHONE_MAP_RAW
    result = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            name, phone = entry.split(":", 1)
            if name.strip() and phone.strip():
                result[name.strip()] = phone.strip()
    return result


def _get_phone(assignee_name: Optional[str], assignee_id: Optional[str]) -> Optional[str]:
    from .db import get_one
    if assignee_id:
        user = get_one("users", user_id=assignee_id)
        if user and user.get("phone_number"):
            return user["phone_number"]
    if assignee_name:
        phone_map = _get_phone_map()
        if assignee_name in phone_map:
            return phone_map[assignee_name]
    return None


def _do_send(phone: str, message: str) -> bool:
    from . import wa_web
    if wa_web.get_status()["state"] == "connected":
        return wa_web.send(phone, message)

    from .db import get_one
    try:
        inst = get_one("app_settings", key="wa_instance_id")
        tok = get_one("app_settings", key="wa_token")
        instance_id = (inst["value"] if inst else "") or config.GREEN_API_INSTANCE_ID
        token = (tok["value"] if tok else "") or config.GREEN_API_TOKEN
    except Exception:
        instance_id = config.GREEN_API_INSTANCE_ID
        token = config.GREEN_API_TOKEN

    if instance_id and token:
        import requests as http
        phone_clean = phone.lstrip("+").replace(" ", "").replace("-", "")
        url = f"https://api.green-api.com/waInstance{instance_id.strip()}/sendMessage/{token.strip()}"
        try:
            resp = http.post(url, json={"chatId": f"{phone_clean}@c.us", "message": message}, timeout=15)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Green API send failed: %s", exc)

    logger.debug("WhatsApp not available — no active session and no Green API credentials")
    return False


def send_ticket_assigned(ticket: dict) -> bool:
    phone = _get_phone(ticket.get("assignee_name"), ticket.get("assignee_id"))
    if not phone:
        return False

    assignee = ticket.get("assignee_name") or "there"
    ticket_url = f"{config.FRONTEND_URL}/tickets/{ticket['id']}"
    message = (
        f"Hello {assignee}!\n\n"
        f"A new support ticket has been raised for you on NCPL Ticketing.\n\n"
        f"Ticket : {ticket.get('code', '')}\n"
        f"Title  : {ticket.get('title', '')}\n"
        f"Priority: {ticket.get('priority', '')}\n"
        f"Raised by: {ticket.get('created_by_name', '')}\n"
        f"Dept   : {ticket.get('department', '')}\n\n"
        f"View it here: {ticket_url}\n\n"
        f"— NCPL Ticketing System"
    )
    result = _do_send(phone, message)
    if result:
        logger.info("WhatsApp sent to %s for ticket %s", phone, ticket.get("code"))
    return result

def send_new_ticket_to_admin(ticket: dict) -> bool:
    phone = config.WIDGET_ADMIN_PHONE
    if not phone:
        from .db import _sb as _get_sb
        try:
            admins = _get_sb().table("users").select("phone_number").eq("role", "admin").execute().data or []
            for a in admins:
                if a.get("phone_number"):
                    phone = a["phone_number"]
                    break
        except Exception:
            pass
    if not phone:
        phone_map = _get_phone_map()
        if phone_map:
            phone = next(iter(phone_map.values()))
    if not phone:
        logger.warning("No admin phone configured for widget notifications")
        return False

    ticket_url = f"{config.FRONTEND_URL}/tickets/{ticket['id']}"
    source = ticket.get("source") or "Widget"
    message = (
        f"🎫 New support ticket from {source}\n\n"
        f"Ticket  : {ticket.get('code', '')}\n"
        f"Title   : {ticket.get('title', '')}\n"
        f"Priority: {ticket.get('priority', '')}\n"
        f"From    : {ticket.get('created_by_email', '')}\n\n"
        f"View: {ticket_url}\n\n"
        f"— NCPL Ticketing System"
    )
    result = _do_send(phone, message)
    if result:
        logger.info("Admin WhatsApp sent to %s for widget ticket %s", phone, ticket.get("code"))
    return result


def send_new_ticket_to_department(ticket: dict) -> bool:
    dept_name = (ticket.get("department") or "").strip()
    if not dept_name:
        return send_new_ticket_to_admin(ticket)

    try:
        dept_rows = _sb().table("departments").select("id").eq("name", dept_name).execute().data or []
        if not dept_rows:
            logger.warning("Department '%s' not found; falling back to admin notify", dept_name)
            return send_new_ticket_to_admin(ticket)

        dept_id = dept_rows[0]["id"]
        members = (
            _sb().table("users")
            .select("phone_number")
            .eq("department_id", dept_id)
            .not_.is_("phone_number", "null")
            .execute().data or []
        )

        ticket_url = f"{config.FRONTEND_URL}/tickets/{ticket['id']}"
        source = ticket.get("source") or "Widget"
        message = (
            f"🎫 New support ticket for {dept_name} ({source})\n\n"
            f"Ticket  : {ticket.get('code', '')}\n"
            f"Title   : {ticket.get('title', '')}\n"
            f"Priority: {ticket.get('priority', '')}\n"
            f"From    : {ticket.get('created_by_email', '')}\n\n"
            f"View: {ticket_url}\n\n"
            f"— NCPL Ticketing System"
        )

        notified = False
        for m in members:
            phone = (m.get("phone_number") or "").strip()
            if phone and _do_send(phone, message):
                logger.info("WhatsApp sent to dept member %s for ticket %s", phone, ticket.get("code"))
                notified = True

        if not notified:
            logger.warning("No dept members notified for '%s'; falling back to admin", dept_name)
            return send_new_ticket_to_admin(ticket)
        return True

    except Exception as exc:
        logger.warning("Department notification failed for %s: %s", ticket.get("code"), exc)
        return send_new_ticket_to_admin(ticket)

def send_test_message() -> bool:
    phone_map = _get_phone_map()
    if not phone_map:
        logger.error("WhatsApp test failed — no phone numbers configured")
        return False
    phone = next(iter(phone_map.values()))
    return _do_send(phone, "✅ NCPL Ticketing — WhatsApp notifications are working correctly!")