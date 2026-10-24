"""
WhatsApp Outreach Engine - Command Line Interface (CLI)
=======================================================
Interactive terminal runner supporting Spintax rendering, CSV personalization,
blacklist exclusion, multi-profile switching, warm-up pacing, and 1-click
clean contacts export.
"""

import os
import sys
import argparse
from datetime import datetime

from core.contact_loader import (
    load_contacts,
    load_sent_history,
    load_processed_numbers,
    load_blacklist,
    export_cleaned_contacts,
)
from core.spintax import render_message
from core.engine import OutreachEngine, get_profile_info, CDP_PORT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONTACTS = os.path.join(BASE_DIR, "contacts.local.txt")
if not os.path.exists(DEFAULT_CONTACTS):
    DEFAULT_CONTACTS = os.path.join(BASE_DIR, "contacts.txt")

DEFAULT_MESSAGE = os.path.join(BASE_DIR, "message.local.txt")
if not os.path.exists(DEFAULT_MESSAGE):
    DEFAULT_MESSAGE = os.path.join(BASE_DIR, "message.txt")

SENT_HISTORY = os.path.join(BASE_DIR, "sent_history.txt")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.local.txt")
if not os.path.exists(BLACKLIST_FILE):
    BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.txt")

REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def main() -> None:
    parser = argparse.ArgumentParser(description="WhatsApp Safe Outreach Automation Engine")
    parser.add_argument("--gui", action="store_true", help="Launch the Desktop GUI application")
    parser.add_argument("--contacts", type=str, default=DEFAULT_CONTACTS, help="Path to contacts file (.txt or .csv)")
    parser.add_argument("--message", type=str, default=DEFAULT_MESSAGE, help="Path to outreach copy file")
    parser.add_argument("--media", type=str, default="", help="Path to optional image attachment")
    parser.add_argument("--batch", type=int, default=20, help="Batch limit (default: 20)")
    parser.add_argument("--profile", type=str, default="default", help="Profile name for multi-account switching")
    parser.add_argument("--warmup", action="store_true", help="Enable account warm-up pacing (25s-45s delays)")
    parser.add_argument("--clean", action="store_true", help="Clean contacts file by removing contacted/invalid/blacklisted leads")
    parser.add_argument("--blacklist", type=str, default=BLACKLIST_FILE, help="Path to blacklist file")
    args = parser.parse_args()

    if args.gui:
        try:
            import app_gui
            app_gui.launch_gui()
            return
        except ImportError as e:
            print(f"[!] Could not launch GUI: {e}")
            print("    Running CLI mode instead...")

    # Clean Contacts Action
    if args.clean:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        ext = os.path.splitext(args.contacts)[1].lower() or ".txt"
        out_name = f"contacts_clean_{ts}{ext}"
        out_path = os.path.join(BASE_DIR, out_name)

        print("[*] Cleaning contacts file...")
        summary = export_cleaned_contacts(
            input_file=args.contacts,
            output_file=out_path,
            history_file=SENT_HISTORY,
            blacklist_file=args.blacklist,
            reports_dir=REPORTS_DIR
        )
        print(f"[✓] Clean list created: {out_name}")
        print(f"    • Total raw leads:        {summary['total_parsed']}")
        print(f"    • Removed (Contacted):    {summary['removed_history']}")
        print(f"    • Removed (Blacklisted):  {summary['removed_blacklist']}")
        print(f"    • Removed (Not on WA):    {summary['removed_unregistered']}")
        print(f"    ✓ Pure leads remaining:   {summary['clean_count']}")
        return

    print("=" * 68)
    print("       WhatsApp Safe Outreach Automation Engine (CLI Mode)       ")
    print("=" * 68)

    # 1. Load message
    if not os.path.exists(args.message):
        print(f"[!] Message file not found: {args.message}")
        return
    with open(args.message, "r", encoding="utf-8") as f:
        message_template = f.read().strip()

    if not message_template:
        print("[!] Message file is empty! Please write your outreach copy in message.txt")
        return

    # 2. Load contacts & blacklist
    all_contacts = load_contacts(args.contacts)
    if not all_contacts:
        print(f"[!] No valid contacts found in: {args.contacts}")
        return

    sent_history = load_processed_numbers(SENT_HISTORY, REPORTS_DIR)
    blacklist = load_blacklist(args.blacklist)

    pending_contacts = [c for c in all_contacts if c["phone"] not in sent_history and c["phone"] not in blacklist]
    blacklisted_count = sum(1 for c in all_contacts if c["phone"] in blacklist)

    profile_dir, cdp_port = get_profile_info(BASE_DIR, args.profile)

    print(f"[*] Contacts loaded from:            {os.path.basename(args.contacts)}")
    print(f"[*] Profile:                         {args.profile} (Port {cdp_port})")
    print(f"[*] Total valid numbers found:       {len(all_contacts)}")
    print(f"[*] Excluded (Blacklisted):          {blacklisted_count}")
    print(f"[*] Already processed previously:    {len(sent_history)}")
    print(f"[*] Pending outreach queue:          {len(pending_contacts)}")
    if args.warmup:
        print(f"[*] Warm-up mode:                    ACTIVE (25s - 45s relaxed delays)")
    print("-" * 68)
    print("Sample Rendered Message Preview (with Spintax variation):")
    print("--------------------------------------------------------------------")
    sample_contact = pending_contacts[0] if pending_contacts else {"name": "Customer", "phone": "Sample"}
    print(render_message(message_template, sample_contact))
    print("--------------------------------------------------------------------")

    if not pending_contacts:
        print("[✓] All contacts in your queue have already been contacted or are blacklisted!")
        return

    # 3. Interactive Batch Controls
    print("\nSelect execution mode:")
    print("  [1] Test Run (Send to FIRST contact only & keep browser open)")
    batch_limit = min(args.batch, 10) if args.warmup else args.batch
    print(f"  [2] Safe Batch Mode (Send up to {batch_limit} contacts with human delays)")
    print("  [A] Process ALL pending contacts")
    user_choice = input("Enter choice (1 / 2 / A) [default: 2]: ").strip().lower()

    if user_choice == "1":
        queue = pending_contacts[:1]
        print("[*] Test mode selected: 1 contact.")
    elif user_choice == "a":
        queue = pending_contacts
        print(f"[!] Full queue selected: {len(queue)} contacts.")
    else:
        queue = pending_contacts[:batch_limit]
        print(f"[*] Safe batch selected: {len(queue)} contacts.")

    # 4. Run Campaign
    engine = OutreachEngine(
        profile_dir=profile_dir,
        history_file=SENT_HISTORY,
        reports_dir=REPORTS_DIR,
        port=cdp_port
    )

    media_to_send = args.media if args.media and os.path.exists(args.media) else None

    summary = engine.run_campaign(
        queue=queue,
        message_template=message_template,
        media_path=media_to_send,
        min_delay=15,
        max_delay=28,
        blacklist=blacklist,
        warmup_mode=args.warmup,
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
