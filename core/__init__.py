"""
WhatsApp Outreach Automation Core Package
"""

from core.spintax import parse_spintax, interpolate_variables, render_message
from core.contact_loader import (
    load_contacts,
    normalize_phone,
    load_sent_history,
    record_sent_number,
    record_excluded_number,
    load_processed_numbers,
    load_blacklist,
    export_cleaned_contacts,
)
from core.reports import generate_campaign_reports
from core.engine import OutreachEngine, get_profile_info, launch_detached_chrome, is_cdp_active
from core.templates import load_templates, save_template, delete_template
from core.scheduler import CampaignScheduler

__all__ = [
    "parse_spintax",
    "interpolate_variables",
    "render_message",
    "load_contacts",
    "normalize_phone",
    "load_sent_history",
    "record_sent_number",
    "load_blacklist",
    "export_cleaned_contacts",
    "generate_campaign_reports",
    "OutreachEngine",
    "get_profile_info",
    "launch_detached_chrome",
    "is_cdp_active",
    "load_templates",
    "save_template",
    "delete_template",
    "CampaignScheduler",
]
