"""
Contact Loader, Blacklist Filter & Number Normalization Engine
=============================================================
Supports loading leads from both plain text (.txt) and CSV files (.csv),
normalizing regional/international phone numbers, filtering previously
contacted entries, enforcing blacklist exclusions, and generating 1-click
cleaned contact exports.
"""

import os
import csv
import glob
from typing import List, Dict, Any, Set, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def normalize_phone(raw_phone: str) -> Optional[str]:
    """
    Cleans and standardizes raw phone inputs into numerical digits.
    Handles Bangladesh localized inputs (01XXXXXXXXX -> 8801XXXXXXXXX)
    and international E.164 numbers.
    """
    digits = "".join(ch for ch in str(raw_phone) if ch.isdigit())
    if not digits:
        return None

    # Bangladesh formatting
    if digits.startswith("880"):
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "88" + digits
    if len(digits) == 10 and digits.startswith("1"):
        return "880" + digits

    # General international numbers (at least 10 digits)
    return digits if len(digits) >= 10 else None


def load_sent_history(history_file: str) -> Set[str]:
    """Returns a set of normalized phone numbers already contacted."""
    if not os.path.exists(history_file):
        return set()
    with open(history_file, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip() and not line.startswith("#"))


def record_sent_number(history_file: str, phone: str) -> None:
    """Appends a successfully contacted number to the history ledger."""
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(phone + "\n")


def load_blacklist(blacklist_file: Optional[str] = None) -> Set[str]:
    """
    Loads and normalizes all blacklisted phone numbers from blacklist.local.txt or blacklist.txt.
    """
    blacklisted: Set[str] = set()
    candidates = []

    if blacklist_file and os.path.exists(blacklist_file):
        candidates.append(blacklist_file)
    else:
        candidates.append(os.path.join(BASE_DIR, "blacklist.local.txt"))
        candidates.append(os.path.join(BASE_DIR, "blacklist.txt"))

    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    cleaned = line.strip()
                    if cleaned and not cleaned.startswith("#"):
                        norm = normalize_phone(cleaned)
                        if norm:
                            blacklisted.add(norm)
            break

    return blacklisted


def get_unregistered_history(reports_dir: str) -> Set[str]:
    """
    Extracts phone numbers confirmed NOT to be on WhatsApp from past reports.
    """
    unregistered: Set[str] = set()
    if not os.path.exists(reports_dir):
        return unregistered

    csv_reports = glob.glob(os.path.join(reports_dir, "report_*.csv"))
    for report_file in csv_reports:
        try:
            with open(report_file, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = row.get("Status", "").upper()
                    if "NOT_ON_WHATSAPP" in status or "UNREGISTERED" in status:
                        p = normalize_phone(row.get("Phone", ""))
                        if p:
                            unregistered.add(p)
        except Exception:
            pass

    return unregistered


def load_contacts(filepath: str) -> List[Dict[str, Any]]:
    """
    Loads contacts from either a .txt or .csv file.
    Returns a list of dicts with at minimum {"phone": "...", "name": "..."}.
    """
    if not os.path.exists(filepath):
        return []

    ext = os.path.splitext(filepath)[1].lower()
    results: List[Dict[str, Any]] = []
    seen_phones: Set[str] = set()

    if ext == ".csv":
        with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            phone_keys = ["phone", "mobile", "number", "contact", "whatsapp", "cell", "tel"]
            name_keys = ["name", "full_name", "first_name", "client", "customer"]

            for row in reader:
                row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}

                raw_phone = ""
                for pk in phone_keys:
                    if pk in row_lower and row_lower[pk]:
                        raw_phone = row_lower[pk]
                        break

                if not raw_phone:
                    raw_phone = list(row.values())[0] if row else ""

                norm_phone = normalize_phone(raw_phone)
                if norm_phone and norm_phone not in seen_phones:
                    seen_phones.add(norm_phone)
                    contact_data = dict(row_lower)
                    contact_data["phone"] = norm_phone

                    c_name = ""
                    for nk in name_keys:
                        if nk in row_lower and row_lower[nk]:
                            c_name = row_lower[nk]
                            break
                    contact_data["name"] = c_name

                    results.append(contact_data)

    else:
        # Plain text file format (one number per line)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                cleaned = line.strip()
                if cleaned and not cleaned.startswith("#"):
                    if "," in cleaned:
                        parts = [p.strip() for p in cleaned.split(",", 1)]
                        norm_phone = normalize_phone(parts[0])
                        c_name = parts[1] if len(parts) > 1 else ""
                    else:
                        norm_phone = normalize_phone(cleaned)
                        c_name = ""

                    if norm_phone and norm_phone not in seen_phones:
                        seen_phones.add(norm_phone)
                        results.append({
                            "phone": norm_phone,
                            "name": c_name
                        })

    return results


def export_cleaned_contacts(
    input_file: str,
    output_file: str,
    history_file: str,
    blacklist_file: Optional[str] = None,
    reports_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reads an input contacts file and creates an ultra-clean export file
    with all duplicates, invalid formats, previously contacted numbers,
    blacklisted contacts, and non-WhatsApp numbers stripped out.
    """
    all_contacts = load_contacts(input_file)
    sent_history = load_sent_history(history_file)
    blacklist = load_blacklist(blacklist_file)
    unregistered = get_unregistered_history(reports_dir) if reports_dir else set()

    clean_contacts: List[Dict[str, Any]] = []
    removed_history = 0
    removed_blacklist = 0
    removed_unregistered = 0

    for c in all_contacts:
        ph = c["phone"]
        if ph in blacklist:
            removed_blacklist += 1
            continue
        if ph in sent_history:
            removed_history += 1
            continue
        if ph in unregistered:
            removed_unregistered += 1
            continue
        clean_contacts.append(c)

    # Determine export format based on output file extension
    ext = os.path.splitext(output_file)[1].lower()
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    if ext == ".csv":
        fieldnames = ["Phone", "Name"]
        # Include any extra keys present in clean_contacts
        extra_keys = set()
        for c in clean_contacts:
            for k in c.keys():
                if k not in ["phone", "name"]:
                    extra_keys.add(k.capitalize())
        fieldnames.extend(sorted(list(extra_keys)))

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in clean_contacts:
                row = {"Phone": "+" + c["phone"], "Name": c.get("name", "")}
                for k in extra_keys:
                    row[k] = c.get(k.lower(), "")
                writer.writerow(row)
    else:
        # Default plain text
        with open(output_file, "w", encoding="utf-8") as f:
            for c in clean_contacts:
                if c.get("name"):
                    f.write(f"+{c['phone']}, {c['name']}\n")
                else:
                    f.write(f"+{c['phone']}\n")

    return {
        "total_parsed": len(all_contacts),
        "clean_count": len(clean_contacts),
        "removed_history": removed_history,
        "removed_blacklist": removed_blacklist,
        "removed_unregistered": removed_unregistered,
        "output_path": output_file
    }
