import logging
import queue
import threading
import time
import urllib.parse
from pathlib import Path

logger = logging.getLogger(__name__)

_SESSION_DIR = Path(__file__).parent.parent / "wa_session"
_msg_queue: queue.Queue = queue.Queue()
_status: dict = {"state": "stopped", "qr": None, "error": None}
_started = False
_lock = threading.Lock()


def _worker():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _status["state"] = "error"
        _status["error"] = (
            "playwright not installed. "
            "Run: pip install playwright && python -m playwright install chromium"
        )
        logger.error(_status["error"])
        return

    _SESSION_DIR.mkdir(exist_ok=True)
    _status["state"] = "connecting"

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(_SESSION_DIR),
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})

            if "web.whatsapp.com" not in page.url:
                page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                time.sleep(3)

            # Wait until logged in, updating QR code while waiting
            while True:
                try:
                    page.wait_for_selector(
                        '[data-testid="chat-list"], #side', timeout=3000
                    )
                    _status["state"] = "connected"
                    _status["qr"] = None
                    logger.info("WhatsApp Web: connected")
                    break
                except Exception:
                    pass

                try:
                    qr_data = page.evaluate("""() => {
                        const canvas = document.querySelector('canvas');
                        return canvas ? canvas.toDataURL('image/png') : null;
                    }""")
                    if qr_data:
                        _status["qr"] = qr_data
                        _status["state"] = "qr"
                except Exception:
                    pass

                time.sleep(2)

            # Message loop
            while True:
                try:
                    phone, message = _msg_queue.get(timeout=5)
                except queue.Empty:
                    continue

                try:
                    phone_clean = phone.lstrip("+").replace(" ", "").replace("-", "")
                    url = (
                        f"https://web.whatsapp.com/send"
                        f"?phone={phone_clean}"
                        f"&text={urllib.parse.quote(message)}"
                    )
                    page.goto(url, wait_until="domcontentloaded")
                    send_btn = page.wait_for_selector(
                        '[data-testid="send"], [aria-label="Send"]',
                        timeout=25000,
                    )
                    if send_btn:
                        send_btn.click()
                        time.sleep(3)
                        logger.info("WhatsApp sent to +%s", phone_clean)
                    page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                except Exception as exc:
                    logger.error("WhatsApp send failed to %s: %s", phone, exc)

    except Exception as exc:
        _status["state"] = "error"
        _status["error"] = str(exc)
        logger.error("WhatsApp Web worker crashed: %s", exc)


def start():
    global _started
    with _lock:
        if not _started:
            _started = True
            t = threading.Thread(target=_worker, daemon=True, name="wa-web")
            t.start()


def get_status() -> dict:
    return {
        "state": _status["state"],
        "qr": _status["qr"],
        "error": _status.get("error"),
    }


def send(phone: str, message: str) -> bool:
    if _status["state"] != "connected":
        return False
    _msg_queue.put((phone, message))
    return True


def logout():
    import shutil
    if _SESSION_DIR.exists():
        shutil.rmtree(_SESSION_DIR)
    _status["state"] = "stopped"
    _status["qr"] = None