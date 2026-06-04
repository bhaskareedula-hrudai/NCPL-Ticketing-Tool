"""
WhatsApp Web automation using Playwright (no external service needed).

Setup (one-time):
    pip install playwright
    python -m playwright install chromium

How it works:
  - On first run, opens a headless browser to WhatsApp Web
  - Settings page shows the QR code — scan it once with your WhatsApp
  - Session is saved locally in wa_session/ so future restarts skip QR
  - Messages are sent by navigating to whatsapp.com/send?phone=...
"""
import asyncio
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


async def _async_worker():
    try:
        from playwright.async_api import async_playwright
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
        async with async_playwright() as pw:
            ctx = await pw.chromium.launch_persistent_context(
                str(_SESSION_DIR),
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})

            if "web.whatsapp.com" not in page.url:
                await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                await asyncio.sleep(3)

            # Wait until logged in, updating QR code while waiting
            while True:
                try:
                    await page.wait_for_selector(
                        '[data-testid="chat-list"], #side', timeout=3000
                    )
                    _status["state"] = "connected"
                    _status["qr"] = None
                    logger.info("WhatsApp Web: connected")
                    break
                except Exception:
                    pass

                try:
                    qr_data = await page.evaluate("""() => {
                        const canvas = document.querySelector('canvas');
                        return canvas ? canvas.toDataURL('image/png') : null;
                    }""")
                    if qr_data:
                        _status["qr"] = qr_data
                        _status["state"] = "qr"
                except Exception:
                    pass

                await asyncio.sleep(2)

            # Message loop
            while True:
                try:
                    phone, message = _msg_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(1)
                    continue

                try:
                    phone_clean = phone.lstrip("+").replace(" ", "").replace("-", "")
                    url = (
                        f"https://web.whatsapp.com/send"
                        f"?phone={phone_clean}"
                        f"&text={urllib.parse.quote(message)}"
                    )
                    await page.goto(url, wait_until="domcontentloaded")
                    send_btn = await page.wait_for_selector(
                        '[data-testid="send"], [aria-label="Send"]',
                        timeout=25000,
                    )
                    if send_btn:
                        await send_btn.click()
                        await asyncio.sleep(3)
                        logger.info("WhatsApp sent to +%s", phone_clean)
                    await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                except Exception as exc:
                    logger.error("WhatsApp send failed to %s: %s", phone, exc)

    except Exception as exc:
        _status["state"] = "error"
        _status["error"] = str(exc)
        logger.error("WhatsApp Web worker crashed: %s", exc, exc_info=True)


def _thread_main():
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_async_worker())
    finally:
        loop.close()


def start():
    global _started
    with _lock:
        if not _started:
            _started = True
            t = threading.Thread(target=_thread_main, daemon=True, name="wa-web")
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