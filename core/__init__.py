"""
WhatsApp Outreach Automation Core Package
"""

from core.spintax import parse_spintax, interpolate_variables, render_message
from core.contact_loader import load_contacts, normalize_phone, load_sent_history, record_sent_number
from core.reports import generate_campaign_reports
from core.engine import OutreachEngine

__all__ = [
    "parse_spintax",
    "interpolate_variables",
    "render_message",
    "load_contacts",
    "normalize_phone",
    "load_sent_history",
    "record_sent_number",
    "generate_campaign_reports",
    "OutreachEngine",
]
