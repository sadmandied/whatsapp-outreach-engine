"""
Campaign Analytics & Report Generator
=====================================
Generates high-fidelity, professional HTML analytics dashboards and CSV exports
for WhatsApp outreach sessions. Uses a modern, developer-tool design system
(Linear / GitHub dark mode) with interactive live filtering and search.
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any


def generate_campaign_reports(
    records: List[Dict[str, Any]],
    output_dir: str,
    campaign_name: str = "WhatsApp Outreach Campaign"
) -> Dict[str, str]:
    """
    Generates both an enterprise HTML dashboard and CSV data reports.
    Returns dict with paths: {"html": path, "csv": path}
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    date_display = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    csv_filename = f"report_{timestamp_str}.csv"
    html_filename = f"report_{timestamp_str}.html"

    csv_path = os.path.join(output_dir, csv_filename)
    html_path = os.path.join(output_dir, html_filename)

    total = len(records)
    delivered = sum(1 for r in records if r.get("status") == "SENT")
    invalid = sum(1 for r in records if r.get("status") == "NOT_ON_WHATSAPP")
    failed = sum(1 for r in records if r.get("status") == "FAILED")
    success_rate = (delivered / total * 100) if total > 0 else 0

    # 1. Export Clean CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Phone", "Name", "Status", "Notes", "Message_Preview"])
        for r in records:
            writer.writerow([
                r.get("timestamp", ""),
                r.get("phone", ""),
                r.get("name", ""),
                r.get("status", ""),
                r.get("notes", ""),
                r.get("message_preview", "")
            ])

    # 2. Build Table Rows
    rows_html = ""
    for idx, r in enumerate(records, 1):
        status = r.get("status", "")
        if status == "SENT":
            badge_class = "badge-success"
            badge_text = "DELIVERED"
            row_data_status = "delivered"
        elif status == "NOT_ON_WHATSAPP":
            badge_class = "badge-warning"
            badge_text = "UNREGISTERED"
            row_data_status = "unregistered"
        else:
            badge_class = "badge-danger"
            badge_text = "FAILED"
            row_data_status = "failed"

        msg_snip = r.get("message_preview", "")
        if len(msg_snip) > 100:
            msg_snip = msg_snip[:100] + "..."

        name_display = r.get("name") if r.get("name") else '<span class="text-dim">—</span>'

        rows_html += f"""
        <tr data-status="{row_data_status}" data-search="{r.get('phone', '')} {r.get('name', '')} {msg_snip}">
          <td class="col-idx">{idx:02d}</td>
          <td class="col-phone"><code>+{r.get('phone', '')}</code></td>
          <td class="col-name">{name_display}</td>
          <td class="col-status"><span class="status-pill {badge_class}">● {badge_text}</span></td>
          <td class="col-time"><span class="mono-time">{r.get('timestamp', '')}</span></td>
          <td class="col-msg"><span class="msg-snippet" title="{r.get('message_preview', '')}">{msg_snip}</span></td>
        </tr>
        """

    records_json = json.dumps(records)

    # 3. Modern, Restrained Enterprise Dashboard HTML & CSS
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{campaign_name} - Session Telemetry</title>
  <style>
    :root {{
      --bg: #0D1117;
      --surface: #161B22;
      --surface-subtle: #21262D;
      --border: #30363D;
      --border-muted: #21262D;
      --text-primary: #E6EDF3;
      --text-secondary: #8B949E;
      --text-dim: #484F58;
      --accent-green: #238636;
      --status-success: #3FB950;
      --status-warning: #D29922;
      --status-danger: #F85149;
      --status-info: #58A6FF;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg);
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: 13px;
      line-height: 1.5;
      padding: 32px 24px;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 1240px;
      margin: 0 auto;
    }}

    /* Header Bar */
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 28px;
      gap: 20px;
    }}

    .header-left {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .header-breadcrumb {{
      font-size: 12px;
      color: var(--text-secondary);
      font-family: var(--font-mono);
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .header-title-row {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    h1 {{
      font-size: 20px;
      font-weight: 600;
      color: var(--text-primary);
      letter-spacing: -0.01em;
    }}

    .status-badge-complete {{
      font-size: 11px;
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--status-success);
      background: rgba(63, 185, 80, 0.1);
      border: 1px solid rgba(63, 185, 80, 0.3);
      padding: 2px 8px;
      border-radius: 4px;
    }}

    .meta-subtitle {{
      color: var(--text-secondary);
      font-size: 12px;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 500;
      padding: 6px 12px;
      border-radius: 6px;
      text-decoration: none;
      cursor: pointer;
      border: 1px solid var(--border);
      background: var(--surface-subtle);
      color: var(--text-primary);
      transition: background 0.15s, border-color 0.15s;
    }}

    .btn:hover {{
      background: #30363D;
      border-color: #484F58;
    }}

    .btn-primary {{
      background: var(--accent-green);
      border-color: rgba(240, 246, 252, 0.1);
      color: #fff;
    }}

    .btn-primary:hover {{
      background: #2EA043;
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin-bottom: 24px;
    }}

    @media (max-width: 900px) {{
      .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}

    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .kpi-title {{
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }}

    .kpi-num {{
      font-size: 26px;
      font-weight: 600;
      font-family: var(--font-mono);
      color: var(--text-primary);
      line-height: 1.1;
    }}

    .kpi-num.green {{ color: var(--status-success); }}
    .kpi-num.amber {{ color: var(--status-warning); }}
    .kpi-num.red {{ color: var(--status-danger); }}

    .kpi-subtext {{
      font-size: 11px;
      color: var(--text-dim);
      margin-top: 6px;
    }}

    /* Main Table Container */
    .table-container {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
    }}

    /* Toolbar above table */
    .table-toolbar {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      background: var(--surface);
    }}

    .filter-tabs {{
      display: flex;
      gap: 4px;
    }}

    .tab-btn {{
      font-size: 12px;
      font-weight: 500;
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid transparent;
      background: transparent;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s;
    }}

    .tab-btn:hover {{
      color: var(--text-primary);
      background: var(--surface-subtle);
    }}

    .tab-btn.active {{
      background: var(--surface-subtle);
      border-color: var(--border);
      color: var(--text-primary);
    }}

    .tab-counter {{
      font-size: 10px;
      font-family: var(--font-mono);
      background: rgba(255, 255, 255, 0.08);
      padding: 1px 5px;
      border-radius: 10px;
      margin-left: 4px;
    }}

    .search-box {{
      position: relative;
    }}

    .search-input {{
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text-primary);
      font-size: 12px;
      padding: 6px 12px;
      border-radius: 6px;
      width: 240px;
      outline: none;
      font-family: var(--font-sans);
    }}

    .search-input:focus {{
      border-color: var(--status-info);
    }}

    /* Data Table */
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}

    thead th {{
      background: #11161D;
      padding: 10px 16px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-secondary);
      border-bottom: 1px solid var(--border);
    }}

    tbody td {{
      padding: 11px 16px;
      border-bottom: 1px solid var(--border-muted);
      vertical-align: middle;
      font-size: 13px;
    }}

    tbody tr:last-child td {{
      border-bottom: none;
    }}

    tbody tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .col-idx {{
      color: var(--text-dim);
      font-family: var(--font-mono);
      font-size: 11px;
      width: 45px;
    }}

    .col-phone code {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text-primary);
      background: var(--surface-subtle);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid var(--border);
    }}

    .col-name {{
      font-weight: 500;
      color: var(--text-primary);
    }}

    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      font-family: var(--font-mono);
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 4px;
      letter-spacing: 0.02em;
    }}

    .badge-success {{
      color: var(--status-success);
      background: rgba(63, 185, 80, 0.08);
      border: 1px solid rgba(63, 185, 80, 0.25);
    }}

    .badge-warning {{
      color: var(--status-warning);
      background: rgba(210, 153, 34, 0.08);
      border: 1px solid rgba(210, 153, 34, 0.25);
    }}

    .badge-danger {{
      color: var(--status-danger);
      background: rgba(248, 81, 73, 0.08);
      border: 1px solid rgba(248, 81, 73, 0.25);
    }}

    .mono-time {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-secondary);
    }}

    .msg-snippet {{
      color: var(--text-secondary);
      font-family: var(--font-sans);
      font-size: 12px;
      display: block;
      max-width: 440px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .text-dim {{
      color: var(--text-dim);
    }}

    /* Footer */
    .footer {{
      margin-top: 32px;
      padding-top: 20px;
      border-top: 1px solid var(--border-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--font-mono);
    }}

    @media print {{
      body {{ background: #fff; color: #000; padding: 0; }}
      .header-actions, .table-toolbar {{ display: none; }}
      .kpi-card, .table-container {{ border: 1px solid #ddd; background: #fff; }}
      tbody td, thead th {{ color: #000; border-bottom: 1px solid #eee; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="header-left">
        <div class="header-breadcrumb">outreach / telemetry / session</div>
        <div class="header-title-row">
          <h1>{campaign_name}</h1>
          <span class="status-badge-complete">COMPLETED</span>
        </div>
        <div class="meta-subtitle">Dispatched on {date_display} • Deterministic DOM Engine (Playwright)</div>
      </div>
      <div class="header-actions">
        <button class="btn" onclick="window.print()">Print Report</button>
        <a class="btn btn-primary" href="{csv_filename}" download>Download CSV</a>
      </div>
    </header>

    <!-- Key Performance Indicators -->
    <section class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Target Queue</div>
        <div class="kpi-num">{total}</div>
        <div class="kpi-subtext">Total contacts parsed</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Delivered</div>
        <div class="kpi-num green">{delivered}</div>
        <div class="kpi-subtext">Acknowledged on WhatsApp</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Unregistered</div>
        <div class="kpi-num amber">{invalid}</div>
        <div class="kpi-subtext">Not on WhatsApp network</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Failed / Timeout</div>
        <div class="kpi-num red">{failed}</div>
        <div class="kpi-subtext">Network or DOM errors</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Delivery Rate</div>
        <div class="kpi-num green">{success_rate:.1f}%</div>
        <div class="kpi-subtext">Overall queue efficiency</div>
      </div>
    </section>

    <!-- Detailed Record Table -->
    <section class="table-container">
      <div class="table-toolbar">
        <div class="filter-tabs">
          <button class="tab-btn active" onclick="filterStatus('all')">All Records <span class="tab-counter">{total}</span></button>
          <button class="tab-btn" onclick="filterStatus('delivered')">Delivered <span class="tab-counter">{delivered}</span></button>
          <button class="tab-btn" onclick="filterStatus('unregistered')">Unregistered <span class="tab-counter">{invalid}</span></button>
          <button class="tab-btn" onclick="filterStatus('failed')">Failed <span class="tab-counter">{failed}</span></button>
        </div>
        <div class="search-box">
          <input type="text" id="searchInput" class="search-input" placeholder="Search phone, name, copy..." oninput="handleSearch()">
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th class="col-idx">#</th>
            <th>Recipient</th>
            <th>Name</th>
            <th>Status</th>
            <th>Timestamp</th>
            <th>Rendered Copy Preview</th>
          </tr>
        </thead>
        <tbody id="tableBody">
          {rows_html if rows_html else '<tr><td colspan="6" style="text-align:center; padding: 32px; color: var(--text-dim)">No records logged for this session.</td></tr>'}
        </tbody>
      </table>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div>WhatsApp Outreach Engine • Local persistent storage</div>
      <div>Session hash: {timestamp_str}</div>
    </footer>
  </div>

  <script>
    let currentFilter = 'all';

    function filterStatus(status) {{
      currentFilter = status;
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      event.target.closest('.tab-btn').classList.add('active');
      applyFilters();
    }}

    function handleSearch() {{
      applyFilters();
    }}

    function applyFilters() {{
      const query = document.getElementById('searchInput').value.toLowerCase().trim();
      const rows = document.querySelectorAll('#tableBody tr');

      rows.forEach(row => {{
        const rowStatus = row.getAttribute('data-status');
        const rowSearch = (row.getAttribute('data-search') || '').toLowerCase();

        const matchesStatus = (currentFilter === 'all') || (rowStatus === currentFilter);
        const matchesQuery = !query || rowSearch.includes(query);

        if (matchesStatus && matchesQuery) {{
          row.style.display = '';
        }} else {{
          row.style.display = 'none';
        }}
      }});
    }}
  </script>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {"html": html_path, "csv": csv_path}
