"""
Spintax and Dynamic Template Variable Resolver
==============================================
Handles text spinning syntax: {Option 1|Option 2|Option 3}
and personalized template variables: {Name}, {Company}, {Phone}, etc.
"""

import re
import random
from typing import Dict, Any, Optional


def parse_spintax(text: str) -> str:
    """
    Recursively resolves Spintax patterns: {Option A|Option B|Option C}
    Nested patterns like {{Hi|Hello}|Hey} are supported.
    """
    pattern = re.compile(r'\{([^{}]+)\}')
    # Loop to handle nested brackets if any
    iterations = 0
    while pattern.search(text) and iterations < 10:
        text = pattern.sub(lambda m: random.choice(m.group(1).split('|')), text)
        iterations += 1
    return text


def interpolate_variables(template: str, data: Dict[str, Any], default_name: str = "Friend") -> str:
    """
    Replaces {variable_name} tags with values from contact dictionary.
    Case-insensitive matching. Defaults to fallback values if key is missing or blank.
    """
    # Replace known common variables with defaults if missing/blank
    name_val = str(data.get("name") or data.get("first_name") or "").strip()
    if not name_val:
        name_val = default_name

    data_resolved = dict(data)
    data_resolved["name"] = name_val

    for key, val in data_resolved.items():
        if val is not None:
            regex = re.compile(rf'\{{{re.escape(key)}\}}', re.IGNORECASE)
            template = regex.sub(str(val), template)

    # Clean up any unresolved {var} tags with a blank or reasonable default
    template = re.sub(r'\{[a-zA-Z0-9_]+\}', '', template)
    return template


def render_message(template: str, contact_data: Optional[Dict[str, Any]] = None, default_name: str = "Friend") -> str:
    """
    Full pipeline:
    1. Interpolate variables ({name}, {company}, etc.)
    2. Resolve Spintax ({Hello|Hi|Hey})
    3. Normalize whitespace
    """
    data = contact_data or {}
    personalized = interpolate_variables(template, data, default_name=default_name)
    spun = parse_spintax(personalized)
    return spun.strip()
