"""
Playwright WhatsApp Automation Engine Core
==========================================
Deterministic browser execution engine with persistent session caching,
DOM-level locators, Spintax rendering, optional media attachments,
thread-safe pause/resume/cancel controls, and callback hooks for CLI & GUI.

Architected to run inside a detached, persistent Chrome instance via CDP
(Chrome DevTools Protocol), ensuring Chrome continues running even if the
GUI or Python process is closed.
"""

import os
import sys
import time
import random
import socket
import shutil
import subprocess
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Set, Tuple
from threading import Event

from playwright.sync_api import sync_playwright, Page, BrowserContext

from core.spintax import render_message
from core.contact_loader import record_sent_number
from core.reports import generate_campaign_reports

CDP_PORT = 9222


def find_chrome_executable() -> str:
    """Locates the Google Chrome binary on the local system."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    which = shutil.which("chrome")
    if which:
        return which
    return "chrome.exe"


def is_cdp_active(port: int = CDP_PORT) -> bool:
    """Checks whether Chrome DevTools Protocol port is answering connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False


def launch_detached_chrome(profile_dir: str, port: int = CDP_PORT) -> bool:
    """
    Spawns Chrome as an independent, detached Windows process tree with remote
    debugging enabled. Because it is detached, Chrome will NEVER terminate when
    Python exits or when the GUI window is closed.
    """
    if is_cdp_active(port):
        return True

    chrome_exe = find_chrome_executable()
    os.makedirs(profile_dir, exist_ok=True)
    abs_profile = os.path.abspath(profile_dir)

    cmd = [
        chrome_exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={abs_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
        "https://web.whatsapp.com"
    ]

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        subprocess.Popen(
            cmd,
            creationflags=creation_flags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"[!] Error launching detached Chrome: {e}")
        return False

    # Poll port readiness up to 12 seconds
    start_time = time.time()
    while time.time() - start_time < 12:
        if is_cdp_active(port):
            return True
        time.sleep(0.5)

def get_profile_info(base_dir: str, profile_name: str = "default") -> Tuple[str, int]:
    """
    Returns (profile_dir, cdp_port) for a given profile name.
    Default profile uses wa_profile/ on port 9222.
    Secondary profiles use wa_profile_<name>/ on dedicated ports (9223+).
    """
    safe = "".join(c for c in profile_name.lower().strip() if c.isalnum() or c in "-_")
    if not safe or safe in ["default", "main", "primary"]:
        return os.path.join(base_dir, "wa_profile"), CDP_PORT
    
    port_offset = (sum(ord(c) for c in safe) % 25) + 1
    return os.path.join(base_dir, f"wa_profile_{safe}"), CDP_PORT + port_offset


class OutreachEngine:
    """Thread-safe WhatsApp outreach automation orchestrator."""

    def __init__(
        self,
        profile_dir: str,
        history_file: str,
        reports_dir: str,
        port: int = CDP_PORT,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, int, str, str, str, int], None]] = None,
        on_finished: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.profile_dir = profile_dir
        self.history_file = history_file
        self.reports_dir = reports_dir
        self.port = port
        self.on_log = on_log or (lambda msg, lvl="info": print(f"[{lvl.upper()}] {msg}"))
        self.on_progress = on_progress
        self.on_finished = on_finished

        self.pause_event = Event()
        self.pause_event.set()  # Unpaused by default
        self.cancel_event = Event()

    def log(self, message: str, level: str = "info") -> None:
        self.on_log(message, level)

    def pause(self) -> None:
        self.pause_event.clear()
        self.log("Campaign execution paused by user.", "warning")

    def resume(self) -> None:
        self.pause_event.set()
        self.log("Campaign execution resumed.", "info")

    def stop(self) -> None:
        self.cancel_event.set()
        self.pause_event.set()  # Break out of any pause sleep
        self.log("Campaign execution stopped by user.", "warning")

    def _wait_while_paused(self) -> bool:
        """Returns True if cancelled, False otherwise."""
        while not self.pause_event.is_set():
            if self.cancel_event.is_set():
                return True
            time.sleep(0.5)
        return self.cancel_event.is_set()

    def _sleep_with_cancel_check(self, seconds: int, current_idx: int, total: int, phone: str, name: str) -> bool:
        """Sleeps while checking for pause/cancel flags and reporting live countdown."""
        for s in range(seconds, 0, -1):
            if self.cancel_event.is_set():
                return True
            if self._wait_while_paused():
                return True

            if self.on_progress:
                self.on_progress(current_idx, total, phone, name, "PAUSING", s)
            time.sleep(1)
        return False

    def send_contact(
        self,
        page: Page,
        contact: Dict[str, Any],
        raw_template: str,
        media_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches message to an individual contact with dynamic Spintax rendering
        and optional image attachment upload.
        """
        phone = contact.get("phone", "")
        name = contact.get("name", "")

        # Render unique message for this specific contact
        personalized_text = render_message(raw_template, contact)
        encoded_msg = urllib.parse.quote(personalized_text)

        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "phone": phone,
            "name": name,
            "status": "FAILED",
            "notes": "",
            "message_preview": personalized_text
        }

        # 1. Open the conversation
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            pass

        start_time = time.time()
        dispatched = False

        while time.time() - start_time < 35:
            if self.cancel_event.is_set():
                result["status"] = "CANCELLED"
                result["notes"] = "Cancelled by operator"
                return result

            if self._wait_while_paused():
                result["status"] = "CANCELLED"
                return result

            # A. Check for 'Phone number shared via url is invalid' popup
            invalid_popup = page.query_selector('div[data-animate-modal-body="true"], div[data-tab="3"], div[role="dialog"]')
            if invalid_popup:
                modal_text = (invalid_popup.inner_text() or "").lower()
                if any(k in modal_text for k in ["invalid", "isn't on whatsapp", "not on whatsapp", "not registered"]):
                    self.log(f"Phone +{phone} is not registered on WhatsApp. Skipping.", "warning")
                    result["status"] = "NOT_ON_WHATSAPP"
                    result["notes"] = "Unregistered phone number"

                    # Dismiss modal
                    try:
                        ok_btn = page.query_selector('button:has-text("OK"), div[role="button"]:has-text("OK"), button[aria-label="OK"]')
                        if ok_btn:
                            ok_btn.click()
                    except Exception:
                        pass
                    return result

            # B. If Media Attachment is specified, attach flyer
            if media_path and os.path.exists(media_path):
                try:
                    # Look for attach icon
                    attach_btn = page.query_selector('span[data-icon="plus"], span[data-icon="attach-menu-plus"], button[aria-label="Attach"]')
                    file_input = page.query_selector('input[type="file"]')

                    if file_input:
                        file_input.set_input_files(media_path)
                        self.log(f"Media flyer attached for +{phone}. Awaiting preview...", "info")
                        time.sleep(2)

                        # Click media send button
                        media_send_btn = page.wait_for_selector(
                            'span[data-icon="send"], span[data-icon="wds-ic-send-filled"], div[aria-label="Send"]',
                            timeout=10000
                        )
                        if media_send_btn:
                            media_send_btn.click()
                            dispatched = True
                            self.log(f"Media + Caption dispatched to +{phone}!", "success")
                            break
                    elif attach_btn:
                        attach_btn.click()
                        time.sleep(1)
                        continue
                except Exception as ex:
                    self.log(f"Media attach attempt failed, falling back to text: {ex}", "warning")

            # C. Locate standard text Send button
            send_btn = page.query_selector(
                'button[aria-label="Send"], span[data-icon="send"], span[data-icon="wds-ic-send-filled"]'
            )

            if send_btn and send_btn.is_visible():
                try:
                    send_btn.click()
                    dispatched = True
                    self.log(f"Message dispatched successfully to +{phone}!", "success")
                    break
                except Exception:
                    pass

            # D. Fallback: Press Enter inside active composer
            chat_input = page.query_selector('footer div[contenteditable="true"]')
            if chat_input and chat_input.is_visible():
                try:
                    text_content = chat_input.inner_text().strip()
                    if text_content:
                        chat_input.press("Enter")
                        dispatched = True
                        self.log(f"Message dispatched via Enter key to +{phone}!", "success")
                        break
                except Exception:
                    pass

            time.sleep(1)

        if dispatched:
            result["status"] = "SENT"
            result["notes"] = "Delivered successfully"
            record_sent_number(self.history_file, phone)
            time.sleep(3.5)  # Transport confirmation
        else:
            result["status"] = "FAILED"
            result["notes"] = "Timed out waiting for Send confirmation"
            self.log(f"Delivery timed out for +{phone}.", "error")

        return result

    def run_campaign(
        self,
        queue: List[Dict[str, Any]],
        message_template: str,
        media_path: Optional[str] = None,
        min_delay: int = 15,
        max_delay: int = 28,
        blacklist: Optional[Set[str]] = None,
        warmup_mode: bool = False,
        keep_browser_open: bool = True
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end outreach campaign.
        Runs inside persistent detached Chrome so that Chrome stays active even if
        the program or GUI window is closed by the user.
        """
        self.cancel_event.clear()
        self.pause_event.set()

        # Enforce blacklist exclusions
        if blacklist:
            orig_len = len(queue)
            queue = [c for c in queue if c.get("phone") not in blacklist]
            excluded_bl = orig_len - len(queue)
            if excluded_bl > 0:
                self.log(f"Excluded {excluded_bl} lead(s) matching your blacklist.", "warning")

        # Enforce warm-up pacing
        if warmup_mode:
            min_delay = max(min_delay, 25)
            max_delay = max(max_delay, 45)
            self.log("Account Warm-Up Mode Active: Enforcing relaxed delay pacing (25s - 45s).", "info")

        total = len(queue)
        records: List[Dict[str, Any]] = []
        sent_count = 0
        skipped_count = 0

        self.log(f"Starting outreach campaign for {total} contact(s)...", "info")
        os.makedirs(self.profile_dir, exist_ok=True)

        # 1. Ensure Chrome is running detached on profile port
        target_port = getattr(self, "port", CDP_PORT)
        self.log(f"Initializing persistent Chrome session (detached process on port {target_port})...", "info")
        chrome_ready = launch_detached_chrome(self.profile_dir, port=target_port)

        with sync_playwright() as p:
            context: BrowserContext
            page: Page

            if chrome_ready and is_cdp_active(target_port):
                self.log(f"Connecting to persistent Chrome via CDP port {target_port}...", "info")
                browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{target_port}")
                context = browser.contexts[0] if browser.contexts else browser.new_context()

                # Find existing WhatsApp page or open new page
                page = None
                for pg in context.pages:
                    if "web.whatsapp.com" in pg.url:
                        page = pg
                        break
                if not page:
                    page = context.pages[0] if context.pages else context.new_page()
                    self.log("Navigating to WhatsApp Web...", "info")
                    page.goto("https://web.whatsapp.com")
                else:
                    try:
                        page.bring_to_front()
                    except Exception:
                        pass
            else:
                self.log("CDP port unavailable, falling back to direct persistent context...", "warning")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    channel="chrome",
                    headless=False,
                    no_viewport=True,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://web.whatsapp.com")

            # Session authentication check
            try:
                page.wait_for_selector(
                    'div[contenteditable="true"][data-tab="3"], div[aria-label="Search"], header',
                    timeout=9000,
                )
                self.log("Authenticated WhatsApp session verified!", "success")
            except Exception:
                self.log("First-time setup: Please scan the QR code in the Chrome window.", "warning")
                page.wait_for_selector(
                    'div[contenteditable="true"][data-tab="3"], div[aria-label="Search"], header',
                    timeout=120000,
                )
                self.log("QR Code scanned! Session authenticated.", "success")

            time.sleep(1.5)

            # 2. Process Contacts
            for idx, contact in enumerate(queue, 1):
                if self.cancel_event.is_set():
                    self.log("Campaign cancelled before processing remaining contacts.", "warning")
                    break

                if self._wait_while_paused():
                    break

                phone = contact.get("phone", "")
                name = contact.get("name", "")

                if self.on_progress:
                    self.on_progress(idx, total, phone, name, "SENDING", 0)

                self.log(f"[{idx}/{total}] Dispatching to +{phone}...", "info")
                record = self.send_contact(page, contact, message_template, media_path=media_path)
                records.append(record)

                if record["status"] == "SENT":
                    sent_count += 1
                elif record["status"] == "NOT_ON_WHATSAPP":
                    skipped_count += 1

                if self.on_progress:
                    self.on_progress(idx, total, phone, name, record["status"], 0)

                # Randomized human delay between dispatches
                if idx < total and not self.cancel_event.is_set():
                    delay = random.randint(min_delay, max_delay)
                    self.log(f"Anti-ban pacing: sleeping {delay}s before next contact...", "info")
                    cancelled = self._sleep_with_cancel_check(delay, idx, total, phone, name)
                    if cancelled:
                        break

            # 3. Generate Reports
            report_paths = generate_campaign_reports(records, self.reports_dir)
            self.log(f"Campaign reports generated in: {self.reports_dir}", "success")

            summary = {
                "total": total,
                "sent": sent_count,
                "skipped": skipped_count,
                "failed": total - sent_count - skipped_count,
                "reports": report_paths,
                "records": records
            }

            if self.on_finished:
                self.on_finished(summary)

            self.log("Outreach finished. Chrome remains running with WhatsApp Web open.", "info")
            return summary
