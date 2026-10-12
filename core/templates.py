"""
Message Template Preset Manager
================================
Stores, loads, and manages reusable outreach copy presets with Spintax syntax.
Allows instant switching between marketing pitches (VIP Offers, Welcome Bonuses,
Follow-ups, Re-engagement) directly in the GUI and CLI.
"""

import os
import json
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_TEMPLATES = {
    "Standard Business Offer": (
        "{Hello|Hi|Greetings} {name}! 👋\n\n"
        "We are {excited|pleased} to share an exclusive update regarding our {premium|specialized} services.\n\n"
        "Special Benefits for New Clients:\n"
        "• Instant Processing & 24/7 Dedicated Support\n"
        "• Transparent Pricing with Zero Hidden Fees\n"
        "• Special Welcome Bonus on your first transaction\n\n"
        "Use Promo Code: {WELCOME2026|BONUS2026|SPECIALVIP}\n\n"
        "Get started or speak with our team:\n"
        "📱 Support: https://t.me/example_support\n"
        "🌐 Channel: https://t.me/example_channel\n\n"
        "{Feel free to reply directly to this message if you have any questions!|Let us know if you need any assistance!}"
    ),
    "VIP Client & High Roller Pitch": (
        "{Dear|Hello} {name}, special VIP invitation 🌟\n\n"
        "We are offering exclusive {perks|privileges} for high-volume accounts this month:\n"
        "• 0% processing fee on your next transaction\n"
        "• Dedicated 24/7 priority support manager\n"
        "• Instant deposit and withdrawal guarantees\n\n"
        "Exclusive VIP Promo: {VIPBONUS|DIAMOND2026|EXCLUSIVEVIP}\n\n"
        "Speak directly with an account manager:\n"
        "📱 VIP Line: https://t.me/example_support\n\n"
        "{Reply 'VIP' to claim your upgrade!|Let us know if you wish to activate this today!}"
    ),
    "Inactive Lead Re-engagement": (
        "{Hello|Assalamu Alaikum} {name}! We noticed you haven't transacted with us recently.\n\n"
        "We'd love to welcome you back with an exclusive {cashback bonus|reload discount}!\n\n"
        "Your special reactivation perk is waiting:\n"
        "📱 Telegram: https://t.me/example_support\n\n"
        "{Reply here if you'd like us to activate it for you!|Have a wonderful day ahead!}"
    ),
    "Quick 1-Line Check-In": (
        "{Hi|Hello} {name}! Just following up to see if you needed any assistance with our services today?\n\n"
        "Our team is active 24/7: https://t.me/example_support\n\n"
        "{Feel free to message anytime!|Have a great day!}"
    )
}


def get_templates_file_path() -> str:
    local_path = os.path.join(BASE_DIR, "templates.local.json")
    if os.path.exists(local_path):
        return local_path
    return os.path.join(BASE_DIR, "templates.json")


def load_templates(filepath: Optional[str] = None) -> Dict[str, str]:
    """Loads all template presets from disk, returning defaults if not found."""
    target = filepath or get_templates_file_path()
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass

    # Save defaults if file doesn't exist
    save_all_templates(DEFAULT_TEMPLATES, target)
    return DEFAULT_TEMPLATES.copy()


def save_all_templates(templates: Dict[str, str], filepath: Optional[str] = None) -> None:
    """Writes all templates to disk in formatted JSON."""
    target = filepath or get_templates_file_path()
    with open(target, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)


def save_template(name: str, content: str, filepath: Optional[str] = None) -> None:
    """Adds or updates a single template preset."""
    templates = load_templates(filepath)
    templates[name] = content.strip()
    save_all_templates(templates, filepath)


def delete_template(name: str, filepath: Optional[str] = None) -> bool:
    """Deletes a template preset by name."""
    templates = load_templates(filepath)
    if name in templates:
        del templates[name]
        save_all_templates(templates, filepath)
        return True
    return False
