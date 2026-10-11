"""
Contact Loader & Number Normalization Engine
============================================
Supports loading leads from both plain text (.txt) and CSV files (.csv),
normalizing regional/international phone numbers, and filtering previously
contacted entries.
"""

import os
import csv
from typing import List, Dict, Any, Set, Optional, Tuple


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
            # Find the phone column
            phone_keys = ["phone", "mobile", "number", "contact", "whatsapp", "cell", "tel"]
            name_keys = ["name", "full_name", "first_name", "client", "customer"]

            for row in reader:
                # Normalize keys to lowercase for flexible matching
                row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}

                raw_phone = ""
                for pk in phone_keys:
                    if pk in row_lower and row_lower[pk]:
                        raw_phone = row_lower[pk]
                        break

                if not raw_phone:
                    # Fallback to the first column if no header match
                    raw_phone = list(row.values())[0] if row else ""

                norm_phone = normalize_phone(raw_phone)
                if norm_phone and norm_phone not in seen_phones:
                    seen_phones.add(norm_phone)
                    contact_data = dict(row_lower)
                    contact_data["phone"] = norm_phone

                    # Resolve name
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
                    # Check if line has format: Phone, Name
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
