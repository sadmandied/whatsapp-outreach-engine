"""
WhatsApp Safe Outreach Automation Engine
========================================
A lightweight, open-source automated outreach engine for WhatsApp Web,
engineered with Playwright for deterministic DOM execution, persistent session
caching, and algorithmic human pacing to prevent account flagging and bans.

Author: Open Source Community
License: MIT
"""

import os
import sys
import time
import random
import urllib.parse
from typing import List, Set, Optional

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
except ImportError:
    print("[!] Playwright is not installed.")
    print("    Please run: pip install -r requirements.txt")
    sys.exit(1)

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Smart Path Resolution (Prefers untracked local files if present)
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.local.txt")
if not os.path.exists(CONTACTS_FILE):
    CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.txt")

MESSAGE_FILE = os.path.join(BASE_DIR, "message.local.txt")
if not os.path.exists(MESSAGE_FILE):
    MESSAGE_FILE = os.path.join(BASE_DIR, "message.txt")

SENT_HISTORY_FILE = os.path.join(BASE_DIR, "sent_history.txt")
PROFILE_DIR = os.path.join(BASE_DIR, "wa_profile")

# Safe Anti-Ban Operational Defaults
DEFAULT_BATCH_SIZE = 20
MIN_DELAY_SECONDS = 15
MAX_DELAY_SECONDS = 28


def clean_phone_number(raw_phone: str) -> Optional[str]:
    """
    Normalizes raw input phone strings into international numerical digits.
    Supports Bangladeshi local formats (01XXXXXXXXX -> 8801XXXXXXXXX)
    as well as standard international E.164 numbers.
    """
    digits = "".join(ch for ch in raw_phone if ch.isdigit())
    if not digits:
        return None

    # Bangladesh formatting (11 digits starting with 01)
    if digits.startswith("880"):
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "88" + digits
    if len(digits) == 10 and digits.startswith("1"):
        return "880" + digits

    # General international number (assumes country code already present)
    return digits if len(digits) >= 10 else None


def load_sent_history() -> Set[str]:
    """Loads previously contacted phone numbers to prevent duplicate outreach."""
    if not os.path.exists(SENT_HISTORY_FILE):
        return set()
    with open(SENT_HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip() and not line.startswith("#"))


def record_sent_contact(phone_number: str) -> None:
    """Appends a successfully contacted number to the persistent history file."""
    with open(SENT_HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(phone_number + "\n")


def human_countdown(seconds: int, label: str = "Anti-ban pause") -> None:
    """Displays a live descending countdown timer in the console."""
    for s in range(seconds, 0, -1):
        print(f"\r  --> {label}: {s}s remaining...  ", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 65 + "\r", end="", flush=True)


def load_contacts(filepath: str) -> List[str]:
    """Reads and normalizes phone numbers from the specified contacts file."""
    if not os.path.exists(filepath):
        return []
    valid_contacts: List[str] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip()
            if cleaned and not cleaned.startswith("#"):
                normalized = clean_phone_number(cleaned)
                if normalized and normalized not in valid_contacts:
                    valid_contacts.append(normalized)
    return valid_contacts


def send_single_message(page: Page, phone: str, encoded_msg: str) -> bool:
    """
    Navigates to WhatsApp Web for a target phone number, waits dynamically
    for conversation DOM initialization, and triggers message dispatch.
    """
    url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
    page.goto(url)
    print("  --> Waiting for conversation and send button...")

    start_time = time.time()
    while time.time() - start_time < 35:
        # Check for invalid phone number dialog
        try:
            invalid_popup = page.locator('div[role="dialog"] button:has-text("OK")')
            if invalid_popup.is_visible():
                print(f"  [!] Target +{phone} is not registered on WhatsApp. Skipping.")
                invalid_popup.click()
                return False
        except Exception:
            pass

        # Check for Send Button (by aria-label, data-icon, or button wrapper)
        try:
            send_btn = page.locator(
                'button[aria-label="Send"], span[data-icon="send"], button:has(span[data-icon="send"])'
            ).first
            if send_btn.is_visible():
                time.sleep(1)  # Brief pause to let link preview settle
                send_btn.click()
                print(f"  [✓] Message sent successfully to +{phone}!")
                return True
        except Exception:
            pass

        # Fallback: Send via Enter key if chat input box is active
        try:
            msg_box = page.locator('div[contenteditable="true"][data-tab="10"]').first
            if msg_box.is_visible():
                time.sleep(1)
                msg_box.press("Enter")
                print(f"  [✓] Message sent via Enter key to +{phone}!")
                return True
        except Exception:
            pass

        time.sleep(1)

    print(f"  [!] Warning: Timed out waiting for send completion for +{phone}.")
    return False


def main() -> None:
    print("=" * 68)
    print("       WhatsApp Safe Outreach Automation Engine (Playwright)       ")
    print("=" * 68)

    # 1. Load promotional message
    if not os.path.exists(MESSAGE_FILE):
        print(f"[!] Message file not found: {MESSAGE_FILE}")
        return
    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        message_text = f.read().strip()

    if not message_text:
        print("[!] Message file is empty! Please write your outreach copy in message.txt")
        return

    # 2. Load contacts
    all_contacts = load_contacts(CONTACTS_FILE)
    if not all_contacts:
        print(f"[!] No valid contacts found in: {CONTACTS_FILE}")
        return

    # Filter out contacts already processed
    sent_history = load_sent_history()
    pending_contacts = [c for c in all_contacts if c not in sent_history]

    print(f"[*] Contacts loaded from:            {os.path.basename(CONTACTS_FILE)}")
    print(f"[*] Total valid numbers found:       {len(all_contacts)}")
    print(f"[*] Already contacted previously:    {len(sent_history)}")
    print(f"[*] Pending outreach queue:          {len(pending_contacts)}")
    print("-" * 68)
    print("Preview of Outreach Copy:")
    print("--------------------------------------------------------------------")
    print(message_text)
    print("--------------------------------------------------------------------")

    if not pending_contacts:
        print("[✓] All contacts in your queue have already been contacted!")
        print("    Add new numbers to contacts.txt to initiate another campaign.")
        return

    # 3. Interactive Batch Controls
    print("\nSelect execution mode:")
    print("  [1] Test Run (Send to FIRST contact only & keep browser open)")
    print(f"  [2] Safe Batch Mode (Send up to {DEFAULT_BATCH_SIZE} contacts with human delays)")
    print("  [A] Process ALL pending contacts")
    user_choice = input("Enter choice (1 / 2 / A) [default: 2]: ").strip().lower()

    if user_choice == "1":
        queue = pending_contacts[:1]
        print("[*] Test mode selected: 1 contact.")
    elif user_choice == "a":
        queue = pending_contacts
        print(f"[!] Full queue selected: {len(queue)} contacts.")
    else:
        queue = pending_contacts[:DEFAULT_BATCH_SIZE]
        print(f"[*] Safe batch selected: {len(queue)} contacts.")

    encoded_message = urllib.parse.quote(message_text)
    total_in_queue = len(queue)
    successful_count = 0

    print("\n[*] Initializing Playwright browser instance...")
    os.makedirs(PROFILE_DIR, exist_ok=True)

    with sync_playwright() as p:
        # Launch persistent context using local Chrome installation
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=False,
            no_viewport=True,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        print("[*] Loading WhatsApp Web...")
        page.goto("https://web.whatsapp.com")

        # Session authentication verification
        try:
            page.wait_for_selector(
                'div[contenteditable="true"][data-tab="3"], div[aria-label="Search"], header',
                timeout=9000,
            )
            print("[✓] WhatsApp Web authenticated session loaded successfully!")
        except Exception:
            print("\n" + "!" * 68)
            print("  FIRST-TIME INITIALIZATION REQUIRED:")
            print("  Please scan the QR code displayed in the Chrome window using your")
            print("  WhatsApp mobile app (Settings -> Linked Devices -> Link a Device).")
            print("  (Session credentials are saved locally in wa_profile for future runs)")
            print("!" * 68 + "\n")
            page.wait_for_selector(
                'div[contenteditable="true"][data-tab="3"], div[aria-label="Search"], header',
                timeout=120000,
            )
            print("[✓] Authentication verified! Launching outreach queue...")

        time.sleep(2)

        # 4. Dispatch Loop
        for idx, phone in enumerate(queue, 1):
            print(f"\n[{idx}/{total_in_queue}] Dispatching outreach to +{phone}...")

            sent = send_single_message(page, phone, encoded_message)

            if sent:
                record_sent_contact(phone)
                successful_count += 1
                time.sleep(3)  # Brief wait for WebSocket transport ACK

            # Random human pacing between consecutive dispatches
            if idx < total_in_queue:
                delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                human_countdown(delay, label="Anti-ban pacing pause")

        print("\n" + "=" * 68)
        print(f"[✓] CAMPAIGN FINISHED: Successfully contacted {successful_count} client(s)!")
        print(f"[✓] Processed entries permanently tracked in '{os.path.basename(SENT_HISTORY_FILE)}'.")
        print("=" * 68)

        print("\n" + "-" * 68)
        print("  Browser window remains active so you can inspect outgoing chats.")
        print("  Press ENTER in this console when you wish to close the session.")
        print("-" * 68)
        input("Press ENTER to close browser...")
        context.close()


if __name__ == "__main__":
    main()
