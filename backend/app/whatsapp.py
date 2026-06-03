import logging
from typing import Optional

import requests as http

from . import config

logger = logging.getLogger(__name__)


def _get_phone(
    assignee_name: Optional[str], assignee_id: Optional[str]
) -> Optional[str]:
    from .db import connect, one

    if assignee_id:
        conn = connect()
        user = one(conn, "SELECT phone_number FROM users WHERE user_id=?", (assignee_id,))
        conn.close()
        if user and user.get("phone_number"):
            return user["phone_number"]

    if assignee_name and assignee_name in config.WHATSAPP_PHONE_MAP:
        return config.WHATSAPP_PHONE_MAP[assignee_name]

    return None


def _normalise_phone(phone: str) -> str:
    return phone.lstrip("+").replace(" ", "").replace("-", "")


def send_ticket_assigned(ticket: dict) -> bool:
    if not config.GREEN_API_INSTANCE_ID or not config.GREEN_API_TOKEN:
        logger.debug("WhatsApp skipped — GREEN_API_INSTANCE_ID or GREEN_API_TOKEN not configured")
        return False

    phone = _get_phone(ticket.get("assignee_name"), ticket.get("assignee_id"))
    if not phone:
        logger.debug(
            "WhatsApp skipped for ticket %s — no phone for assignee %s",
            ticket.get("code"), ticket.get("assignee_name"),
        )
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
        f"Please visit the link below to view and respond:\n"
        f"{ticket_url}\n\n"
        f"— NCPL Ticketing System"
    )

    chat_id = f"{_normalise_phone(phone)}@c.us"
    url = (
        f"https://api.green-api.com"
        f"/waInstance{config.GREEN_API_INSTANCE_ID}"
        f"/sendMessage/{config.GREEN_API_TOKEN}"
    )

    try:
        resp = http.post(url, json={"chatId": chat_id, "message": message}, timeout=15)
        resp.raise_for_status()
        logger.info("WhatsApp notification sent to %s for ticket %s", phone, ticket.get("code"))
        return True
    except Exception as exc:
        logger.error("WhatsApp notification failed for ticket %s: %s", ticket.get("code"), exc)
        return False