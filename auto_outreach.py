"""
WhatsApp Safe Outreach Automation CLI
=====================================
Command-Line Interface for the WhatsApp Safe Outreach Engine.
Powered by Playwright, Spintax variation, and persistent sessions.
"""

import os
import sys
import argparse
from typing import List, Dict, Any

from core.contact_loader import load_contacts, load_sent_history
from core.spintax import render_message
from core.engine import OutreachEngine

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
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

DEFAULT_BATCH_SIZE = 20
MIN_DELAY = 15
MAX_DELAY = 28


def main():
    parser = argparse.ArgumentParser(description="WhatsApp Safe Outreach Automation Engine")
    parser.add_argument("--gui", action="store_true", help="Launch in Modern Desktop GUI mode")
    parser.add_argument("--media", type=str, default="", help="Path to optional image/poster attachment")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size (default: 20)")
    args = parser.parse_args()

    if args.gui:
        try:
            import app_gui
            app_gui.launch_gui()
            return
        except ImportError as e:
            print(f"[!] Could not launch GUI: {e}")
            print("    Running CLI mode instead...")

    print("=" * 68)
    print("       WhatsApp Safe Outreach Automation Engine (CLI Mode)       ")
    print("=" * 68)

    # 1. Load message
    if not os.path.exists(MESSAGE_FILE):
        print(f"[!] Message file not found: {MESSAGE_FILE}")
        return
    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        message_template = f.read().strip()

    if not message_template:
        print("[!] Message file is empty! Please write your outreach copy in message.txt")
        return

    # 2. Load contacts
    all_contacts = load_contacts(CONTACTS_FILE)
    if not all_contacts:
        print(f"[!] No valid contacts found in: {CONTACTS_FILE}")
        return

    sent_history = load_sent_history(SENT_HISTORY_FILE)
    pending_contacts = [c for c in all_contacts if c["phone"] not in sent_history]

    print(f"[*] Contacts loaded from:            {os.path.basename(CONTACTS_FILE)}")
    print(f"[*] Total valid numbers found:       {len(all_contacts)}")
    print(f"[*] Already contacted previously:    {len(sent_history)}")
    print(f"[*] Pending outreach queue:          {len(pending_contacts)}")
    print("-" * 68)
    print("Sample Rendered Message Preview (with Spintax variation):")
    print("--------------------------------------------------------------------")
    sample_contact = pending_contacts[0] if pending_contacts else {"name": "Customer", "phone": "Sample"}
    print(render_message(message_template, sample_contact))
    print("--------------------------------------------------------------------")

    if not pending_contacts:
        print("[✓] All contacts in your queue have already been contacted!")
        print("    Add new numbers to contacts.txt to initiate another campaign.")
        return

    # 3. Interactive Batch Controls
    print("\nSelect execution mode:")
    print("  [1] Test Run (Send to FIRST contact only & keep browser open)")
    print(f"  [2] Safe Batch Mode (Send up to {args.batch} contacts with human delays)")
    print("  [A] Process ALL pending contacts")
    user_choice = input("Enter choice (1 / 2 / A) [default: 2]: ").strip().lower()

    if user_choice == "1":
        queue = pending_contacts[:1]
        print("[*] Test mode selected: 1 contact.")
    elif user_choice == "a":
        queue = pending_contacts
        print(f"[!] Full queue selected: {len(queue)} contacts.")
    else:
        queue = pending_contacts[:args.batch]
        print(f"[*] Safe batch selected: {len(queue)} contacts.")

    # 4. Run Campaign
    engine = OutreachEngine(
        profile_dir=PROFILE_DIR,
        history_file=SENT_HISTORY_FILE,
        reports_dir=REPORTS_DIR,
    )

    media_to_send = args.media if args.media and os.path.exists(args.media) else None

    summary = engine.run_campaign(
        queue=queue,
        message_template=message_template,
        media_path=media_to_send,
        min_delay=MIN_DELAY,
        max_delay=MAX_DELAY,
        keep_browser_open=True
    )

    print("\n" + "=" * 68)
    print(f"[✓] CAMPAIGN FINISHED: Delivered: {summary['sent']} | Skipped: {summary['skipped']} | Failed: {summary['failed']}")
    if "reports" in summary and "html" in summary["reports"]:
        print(f"[✓] HTML Report: {summary['reports']['html']}")
        print(f"[✓] CSV Report:  {summary['reports']['csv']}")
    print("=" * 68)

    print("\n" + "-" * 68)
    print("  Browser window remains active so you can inspect outgoing chats.")
    print("  Press ENTER in this console when you wish to close the session.")
    print("-" * 68)
    input("Press ENTER to close...")


if __name__ == "__main__":
    main()
