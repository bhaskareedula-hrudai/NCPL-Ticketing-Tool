from pathlib import Path
import os
from dotenv import dotenv_values

_ROOT = Path(__file__).resolve().parent.parent

# Read .env file directly — utf-8-sig handles Windows BOM, takes priority over system env vars
_env = dotenv_values(_ROOT / ".env", encoding="utf-8-sig")

def _get(key: str, default: str = "") -> str:
    if key in _env:
        return _env[key] or default
    return os.environ.get(key, default)


DATABASE_URL = _env.get("DATABASE_URL", os.environ.get("DATABASE_URL", ""))
ADMIN_EMAILS = frozenset(
    e.strip().lower()
    for e in _get("ADMIN_EMAILS").split(",")
    if e.strip()
)
APP_NAME = _get("APP_NAME", "ncpl-ticketing")
GOOGLE_CLIENT_ID = _get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _get("GOOGLE_CLIENT_SECRET")

_vercel_url = (
    os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", "")
    or os.environ.get("VERCEL_URL", "")
)
BASE_URL = (
    _get("BASE_URL")
    or (f"https://{_vercel_url}" if _vercel_url else "http://localhost:8000")
)
FRONTEND_URL = (
    _get("FRONTEND_URL")
    or (f"https://{_vercel_url}" if _vercel_url else "http://localhost:3000")
)
SECURE_COOKIE = bool(
    os.environ.get("VERCEL") or _get("SECURE_COOKIE").lower() == "true"
)
CORS_ORIGINS = [
    o.strip()
    for o in _get("CORS_ORIGINS").split(",")
    if o.strip() and o.strip() != "*"
]

SEED_DEPARTMENTS = ["HR", "Sales", "Training", "Mentoring", "Finance", "Hrudai"]

DEPARTMENT_MEMBERS: dict[str, list[str]] = {
    "Finance":   ["Jayalakshmi"],
    "HR":        ["Bhuvana"],
    "Hrudai":    ["Pullaiah", "Bhaskar", "Kalpana", "Harish", "Vaishnavi", "Bhagya"],
    "Mentoring": ["Pinki", "Dharmavathi", "Mahalakshmi"],
    "Sales":     ["Mani", "Bhanu", "Manikanta", "Bhavani"],
    "Training":  ["Himasri", "Gayatri", "Sowjanya", "Nireesha"],
}

TICKET_STATUSES = ["Open", "In Progress", "Pending", "Resolved", "Closed"]
TICKET_PRIORITIES = ["Low", "Medium", "High", "Urgent"]

SESSION_TTL_DAYS = 7
PREVIEW_SESSION_HOURS = 2
MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024

# ── WhatsApp (Green API — free, no recipient activation needed) ───────────────
# Setup (one-time, admin only):
#   1. Sign up at green-api.com (free tier: 200 messages/month)
#   2. Create an instance, scan QR code with your WhatsApp
#   3. Copy Instance ID and API Token below
#
# WHATSAPP_PHONE_MAP maps assignee names to their phone numbers only.
# Format: Name:+CountryCodeNumber  (comma-separated)
# Example: Jayalakshmi:+919876543210,Bhuvana:+919876543211
GREEN_API_INSTANCE_ID = _get("GREEN_API_INSTANCE_ID", "")
GREEN_API_TOKEN = _get("GREEN_API_TOKEN", "")

_phone_map_raw = _get("WHATSAPP_PHONE_MAP", "")
WHATSAPP_PHONE_MAP_RAW = _phone_map_raw  
WHATSAPP_PHONE_MAP: dict[str, str] = {}
for _entry in _phone_map_raw.split(","):
    _entry = _entry.strip()
    if ":" in _entry:
        _name, _phone = _entry.split(":", 1)
        if _name.strip() and _phone.strip():
            WHATSAPP_PHONE_MAP[_name.strip()] = _phone.strip()