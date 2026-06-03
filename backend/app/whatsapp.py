import logging
from typing import Optional

import requests as http

from . import config

logger = logging.getLogger(__name__)


def _get_phone_and_key(
    assignee_name: Optional[str], assignee_id: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    from .db import connect, one

    if assignee_id:
        conn = connect()
        user = one(conn, "SELECT phone_number, wa_api_key FROM users WHERE user_id=?", (assignee_id,))
        conn.close()
        if user and user.get("phone_number"):
            return user["phone_number"], user.get("wa_api_key")

    if assignee_name and assignee_name in config.WHATSAPP_PHONE_MAP:
        phone, key = config.WHATSAPP_PHONE_MAP[assignee_name]
        return phone, key

    return None, None


def send_ticket_assigned(ticket: dict) -> bool:
    phone, api_key = _get_phone_and_key(
        ticket.get("assignee_name"), ticket.get("assignee_id")
    )
    if not phone or not api_key:
        logger.debug(
            "WhatsApp skipped for ticket %s — no phone/apikey for assignee %s",
            ticket.get("code"),
            ticket.get("assignee_name"),
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

    try:
        resp = http.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": phone, "text": message, "apikey": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("WhatsApp notification sent to %s for ticket %s", phone, ticket.get("code"))
        return True
    except Exception as exc:
        logger.error("WhatsApp notification failed for ticket %s: %s", ticket.get("code"), exc)
        return False