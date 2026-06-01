import logging
import requests
from . import config

logger = logging.getLogger(__name__)


def send_ticket_notification(
    assignee_name: str,
    ticket_code: str,
    ticket_title: str,
    created_by: str,
) -> bool:
    if not config.WHATSAPP_API_TOKEN or not config.WHATSAPP_PHONE_NUMBER_ID:
        logger.debug("WhatsApp not configured — skipping notification")
        return False

    phone = config.ASSIGNEE_PHONES.get(assignee_name)
    if not phone:
        logger.debug("No phone number mapped for assignee '%s' — skipping", assignee_name)
        return False

    ticket_link = f"{config.FRONTEND_URL}/tickets"

    message = (
        f"Hello {assignee_name},\n\n"
        f"A ticket has been raised for you:\n"
        f"*Ticket:* {ticket_code}\n"
        f"*Title:* {ticket_title}\n"
        f"*Raised by:* {created_by}\n\n"
        f"Please visit the portal to take action:\n{ticket_link}\n\n"
        f"— NCPL Ticketing System"
    )

    url = f"https://graph.facebook.com/v19.0/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.ok:
            logger.info("WhatsApp notification sent to %s for ticket %s", assignee_name, ticket_code)
            return True
        logger.error("WhatsApp API %s: %s", resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.error("WhatsApp send failed: %s", exc)
        return False