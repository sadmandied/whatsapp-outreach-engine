"""
WhatsApp Outreach Engine - Enterprise Desktop Client
====================================================
Designed with a clean, minimalist developer-tool aesthetic (Linear/GitHub dark mode).
Eliminates juvenile AI design cliches in favor of crisp typography, subtle neutral palettes,
and precise status telemetry.

New Enterprise Capabilities:
1. Message Template Preset Manager (templates.json) with instant dropdown switching.
2. Blacklist & Do-Not-Contact Protection (blacklist.txt).
3. 1-Click Clean & Export Leads Tool (removes contacted, duplicates, and non-WhatsApp leads).
4. Multi-Account / Multi-SIM Profile Switcher (isolated browser sessions).
5. Hands-Free Background Scheduler (trigger at specific hour or countdown).
6. Account Warm-up Safety Mode for fresh SIM cards / new numbers.
"""

import os
import sys
import threading
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any, List, Set

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog

from core.contact_loader import (
    load_contacts,
    load_sent_history,
    load_blacklist,
    export_cleaned_contacts,
)
from core.spintax import render_message
from core.templates import load_templates, save_template, delete_template
from core.scheduler import CampaignScheduler
from core.engine import (
    OutreachEngine,
    launch_detached_chrome,
    is_cdp_active,
    get_profile_info,
    CDP_PORT,
)

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

# Design Tokens (GitHub / Linear dark design system)
THEME = {
    "bg": "#0D1117",
    "surface": "#161B22",
    "surface_subtle": "#21262D",
    "input_bg": "#0D1117",
    "border": "#30363D",
    "border_muted": "#21262D",
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_dim": "#484F58",
    "btn_primary": "#238636",
    "btn_primary_hover": "#2EA043",
    "btn_secondary": "#21262D",
    "btn_secondary_hover": "#30363D",
    "btn_danger": "#8B1E1E",
    "btn_danger_hover": "#B32626",
    "btn_warning": "#9E6A03",
    "btn_warning_hover": "#B87A04",
    "status_ready": "#3FB950",
    "status_running": "#58A6FF",
    "status_paused": "#D29922",
    "status_stopped": "#8B949E",
}


class ModernOutreachApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Frame - Responsive Min & Default Sizes
        self.title("WhatsApp Outreach Engine")
        self.geometry("1140x780")
        self.minsize(900, 600)
        # Ensure Windows taskbar groups with custom icon
        if sys.platform == "win32":
            try:
                import ctypes
                myappid = "sadman.whatsapp.outreach.engine.1.3"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        # Window & Taskbar Icon
        self.icon_ico_path = os.path.join(BASE_DIR, "assets", "icon.ico")
        self.icon_png_path = os.path.join(BASE_DIR, "assets", "icon.png")
        if os.path.exists(self.icon_ico_path):
            try:
                self.iconbitmap(self.icon_ico_path)
            except Exception:
                pass

        self.configure(fg_color=THEME["bg"])
        ctk.set_appearance_mode("dark")

        # Runtime Engine References
        self.engine: Optional[OutreachEngine] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.is_paused = False

        # Profile State
        self.current_profile_name = "Default"
        self.profile_dir, self.cdp_port = get_profile_info(BASE_DIR, "default")

        # Scheduler
        self.scheduler = CampaignScheduler(on_tick=self._on_scheduler_tick)

        self.contacts_path = DEFAULT_CONTACTS
        self.message_path = DEFAULT_MESSAGE
        self.media_path = ""
        self.blacklist_path = BLACKLIST_FILE

        # Template Library Cache
        self.templates_dict = load_templates()

        # Window closing protocol
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._build_interface()
        self._load_defaults()

    def _build_interface(self):
        # Master grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------------- 1. Top Navigation Bar ----------------
        navbar = ctk.CTkFrame(self, fg_color=THEME["surface"], corner_radius=0, height=54, border_width=0)
        navbar.grid(row=0, column=0, sticky="ew")
        navbar.grid_columnconfigure(1, weight=1)

        # App Brand & Version
        brand_box = ctk.CTkFrame(navbar, fg_color="transparent")
        brand_box.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        if os.path.exists(self.icon_png_path):
            try:
                from PIL import Image
                self.logo_image = ctk.CTkImage(
                    light_image=Image.open(self.icon_png_path),
                    dark_image=Image.open(self.icon_png_path),
                    size=(22, 22)
                )
                icon_lbl = ctk.CTkLabel(brand_box, image=self.logo_image, text="")
                icon_lbl.pack(side="left", padx=(0, 8))
            except Exception:
                pass

        title_lbl = ctk.CTkLabel(
            brand_box,
            text="WhatsApp Outreach",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=THEME["text_primary"]
        )
        title_lbl.pack(side="left", padx=(0, 8))

        ver_pill = ctk.CTkLabel(
            brand_box,
            text="v1.3.0 Pro",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["text_secondary"],
            fg_color=THEME["surface_subtle"],
            corner_radius=4,
            padx=7,
            pady=2
        )
        ver_pill.pack(side="left")

        # Right Action Area in Navbar
        nav_right = ctk.CTkFrame(navbar, fg_color="transparent")
        nav_right.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        # Profile Switcher Dropdown
        ctk.CTkLabel(nav_right, text="Profile:", font=ctk.CTkFont(size=11), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))
        self.profile_menu = ctk.CTkOptionMenu(
            nav_right,
            values=["Default", "Account 2 (Sales)", "Account 3 (VIP)", "+ Add Profile..."],
            width=140,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["surface_subtle"],
            button_color=THEME["border"],
            button_hover_color=THEME["border_muted"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            command=self._on_profile_change
        )
        self.profile_menu.set("Default")
        self.profile_menu.pack(side="left", padx=(0, 10))

        # Focus / Open Chrome Button
        open_chrome_btn = ctk.CTkButton(
            nav_right,
            text="Focus Chrome",
            width=92,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            command=self._focus_chrome
        )
        open_chrome_btn.pack(side="left", padx=(0, 10))

        # Telemetry Status Indicator Pill
        self.status_pill = ctk.CTkLabel(
            nav_right,
            text="● Engine Ready",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["status_ready"],
            fg_color=THEME["surface_subtle"],
            corner_radius=6,
            padx=12,
            pady=4
        )
        self.status_pill.pack(side="left")

        # Divider
        divider = ctk.CTkFrame(self, fg_color=THEME["border"], height=1)
        divider.grid(row=0, column=0, sticky="sew")

        # ---------------- 2. Main Workspace ----------------
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=1, column=0, sticky="nsew", padx=16, pady=14)
        workspace.grid_columnconfigure(0, weight=1, minsize=400)
        workspace.grid_columnconfigure(1, weight=1, minsize=440)
        workspace.grid_rowconfigure(0, weight=1)

        # ====== LEFT COLUMN: Parameters & Configuration ======
        left_column = ctk.CTkScrollableFrame(
            workspace,
            fg_color=THEME["surface"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"]
        )
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ---------------- Section: Contacts Source ----------------
        self._section_title(left_column, "Contacts Source", "Accepts .txt (one per line) or .csv with column headers")
        
        c_row = ctk.CTkFrame(left_column, fg_color="transparent")
        c_row.pack(fill="x", padx=16, pady=(0, 6))

        self.contacts_entry = ctk.CTkEntry(
            c_row,
            fg_color=THEME["input_bg"],
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            height=32
        )
        self.contacts_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.contacts_entry.insert(0, self.contacts_path)

        browse_c_btn = ctk.CTkButton(
            c_row,
            text="Browse",
            width=70,
            height=32,
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            command=self._browse_contacts
        )
        browse_c_btn.pack(side="right")

        # Meta & Clean Tool Row
        meta_tool_row = ctk.CTkFrame(left_column, fg_color="transparent")
        meta_tool_row.pack(fill="x", padx=16, pady=(0, 14))

        self.contacts_meta_lbl = ctk.CTkLabel(
            meta_tool_row,
            text="Reading queue status...",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_secondary"]
        )
        self.contacts_meta_lbl.pack(side="left")

        clean_btn = ctk.CTkButton(
            meta_tool_row,
            text="Clean & Export List",
            font=ctk.CTkFont(size=11),
            width=120,
            height=24,
            fg_color=THEME["surface_subtle"],
            hover_color=THEME["border"],
            text_color=THEME["text_secondary"],
            corner_radius=4,
            command=self._clean_contacts_action
        )
        clean_btn.pack(side="right")

        # ---------------- Section: Template Presets ----------------
        self._section_title(
            left_column,
            "Message Template & Preset Library",
            "Choose a pre-saved pitch or customize. Supports Spintax {A|B} and tags"
        )

        preset_bar = ctk.CTkFrame(left_column, fg_color="transparent")
        preset_bar.pack(fill="x", padx=16, pady=(0, 6))

        preset_names = list(self.templates_dict.keys())
        self.template_menu = ctk.CTkOptionMenu(
            preset_bar,
            values=preset_names if preset_names else ["Default"],
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["surface_subtle"],
            button_color=THEME["border"],
            button_hover_color=THEME["border_muted"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            command=self._on_template_selected
        )
        self.template_menu.pack(side="left", fill="x", expand=True, padx=(0, 6))

        save_tmpl_btn = ctk.CTkButton(
            preset_bar,
            text="Save As",
            width=60,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            command=self._save_template_as
        )
        save_tmpl_btn.pack(side="left", padx=(0, 4))

        del_tmpl_btn = ctk.CTkButton(
            preset_bar,
            text="Delete",
            width=55,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_danger_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_secondary"],
            corner_radius=4,
            command=self._delete_template_action
        )
        del_tmpl_btn.pack(side="left")

        # Quick Tag Insert Buttons
        tag_bar = ctk.CTkFrame(left_column, fg_color="transparent")
        tag_bar.pack(anchor="w", padx=16, pady=(0, 6))
        ctk.CTkLabel(tag_bar, text="Insert parameter:", font=ctk.CTkFont(size=11), text_color=THEME["text_dim"]).pack(side="left", padx=(0, 6))

        for tag_name in ["{name}", "{company}", "{phone}"]:
            t_btn = ctk.CTkButton(
                tag_bar,
                text=f"+ {tag_name}",
                width=62,
                height=22,
                font=ctk.CTkFont(size=11),
                fg_color=THEME["surface_subtle"],
                hover_color=THEME["border"],
                text_color=THEME["text_secondary"],
                corner_radius=3,
                command=lambda t=tag_name: self._insert_tag(t)
            )
            t_btn.pack(side="left", padx=2)

        self.message_box = ctk.CTkTextbox(
            left_column,
            height=170,
            fg_color=THEME["input_bg"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=4
        )
        self.message_box.pack(fill="x", padx=16, pady=(0, 14))

        # ---------------- Section: Attachment ----------------
        self._section_title(left_column, "Media Attachment (Optional)", "Send a promo image flyer/banner with your tailored caption")

        m_row = ctk.CTkFrame(left_column, fg_color="transparent")
        m_row.pack(fill="x", padx=16, pady=(0, 14))

        self.media_entry = ctk.CTkEntry(
            m_row,
            placeholder_text="None (Text-only message)",
            fg_color=THEME["input_bg"],
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            height=32
        )
        self.media_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_m_btn = ctk.CTkButton(
            m_row,
            text="Choose Image",
            width=95,
            height=32,
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            corner_radius=4,
            command=self._browse_media
        )
        browse_m_btn.pack(side="right")

        # ---------------- Section: Pacing & Safety Controls ----------------
        self._section_title(left_column, "Pacing & Safety Controls", "Configures velocity bounds, blacklist protection, and warm-up mode")

        pacing_card = ctk.CTkFrame(left_column, fg_color=THEME["surface_subtle"], corner_radius=6, border_width=1, border_color=THEME["border"])
        pacing_card.pack(fill="x", padx=16, pady=(0, 16))
        pacing_card.grid_columnconfigure(0, weight=1)
        pacing_card.grid_columnconfigure(1, weight=0)

        self._pacing_row(pacing_card, "Batch Size limit:", 0, "20", "batch_entry")
        self._pacing_row(pacing_card, "Minimum Delay (seconds):", 1, "15", "min_delay_entry")
        self._pacing_row(pacing_card, "Maximum Delay (seconds):", 2, "28", "max_delay_entry")
        self._pacing_row(pacing_card, "Rest Between Batches (mins):", 3, "15", "batch_rest_entry")

        # Continuous Autopilot Toggle
        self.autopilot_var = ctk.BooleanVar(value=True)
        autopilot_cb = ctk.CTkCheckBox(
            pacing_card,
            text="Continuous Autopilot (Auto-loop batches with rest pauses)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME["text_primary"],
            variable=self.autopilot_var,
            fg_color=THEME["btn_primary"],
            hover_color=THEME["btn_primary_hover"],
            corner_radius=3
        )
        autopilot_cb.grid(row=4, column=0, columnspan=2, padx=14, pady=(8, 4), sticky="w")

        # Warm-up Mode Toggle
        self.warmup_var = ctk.BooleanVar(value=False)
        warmup_cb = ctk.CTkCheckBox(
            pacing_card,
            text="Account Warm-up Mode (Ramps up delay to 25s-45s for fresh SIMs)",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_secondary"],
            variable=self.warmup_var,
            fg_color=THEME["btn_primary"],
            hover_color=THEME["btn_primary_hover"],
            corner_radius=3
        )
        warmup_cb.grid(row=5, column=0, columnspan=2, padx=14, pady=(4, 10), sticky="w")

        # Blacklist Status Row
        bl_row = ctk.CTkFrame(pacing_card, fg_color="transparent")
        bl_row.grid(row=6, column=0, columnspan=2, padx=14, pady=(0, 10), sticky="ew")
        
        self.bl_status_lbl = ctk.CTkLabel(
            bl_row,
            text="Blacklist: Active (blacklist.txt)",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_dim"]
        )
        self.bl_status_lbl.pack(side="left")

        edit_bl_btn = ctk.CTkButton(
            bl_row,
            text="Edit Blacklist",
            width=85,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color=THEME["surface"],
            hover_color=THEME["border"],
            text_color=THEME["text_secondary"],
            corner_radius=3,
            command=self._open_blacklist_file
        )
        edit_bl_btn.pack(side="right")

        # ====== RIGHT COLUMN: Telemetry, Logs & Controls ======
        right_column = ctk.CTkFrame(
            workspace,
            fg_color=THEME["surface"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"]
        )
        right_column.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_column.grid_columnconfigure(0, weight=1)
        
        # Row weights for dynamic vertical resizing
        right_column.grid_rowconfigure(0, weight=0)  # Toolbar
        right_column.grid_rowconfigure(1, weight=0)  # Schedule banner (dynamic)
        right_column.grid_rowconfigure(2, weight=0)  # KPI row
        right_column.grid_rowconfigure(3, weight=0)  # Progress panel
        right_column.grid_rowconfigure(4, weight=0)  # Log header
        right_column.grid_rowconfigure(5, weight=1)  # Activity stream box (EXPANDS!)
        right_column.grid_rowconfigure(6, weight=0)  # Footer actions

        # Control Action Toolbar
        toolbar = ctk.CTkFrame(right_column, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        toolbar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.start_btn = ctk.CTkButton(
            toolbar,
            text="Start Queue",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=THEME["btn_primary"],
            hover_color=THEME["btn_primary_hover"],
            height=34,
            corner_radius=4,
            command=self._start_campaign
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 3), sticky="ew")

        self.schedule_btn = ctk.CTkButton(
            toolbar,
            text="Schedule",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=34,
            corner_radius=4,
            command=self._schedule_campaign_dialog
        )
        self.schedule_btn.grid(row=0, column=1, padx=3, sticky="ew")

        self.pause_btn = ctk.CTkButton(
            toolbar,
            text="Pause",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=34,
            corner_radius=4,
            state="disabled",
            command=self._toggle_pause
        )
        self.pause_btn.grid(row=0, column=2, padx=3, sticky="ew")

        self.stop_btn = ctk.CTkButton(
            toolbar,
            text="Cancel",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_danger_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=34,
            corner_radius=4,
            state="disabled",
            command=self._stop_campaign
        )
        self.stop_btn.grid(row=0, column=3, padx=3, sticky="ew")

        self.test_btn = ctk.CTkButton(
            toolbar,
            text="Test (1 Lead)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=34,
            corner_radius=4,
            command=self._test_single
        )
        self.test_btn.grid(row=0, column=4, padx=(3, 0), sticky="ew")

        # Schedule Banner (Hidden until scheduled)
        self.schedule_banner = ctk.CTkFrame(right_column, fg_color="#1F242C", corner_radius=6, border_width=1, border_color="#388BFD")
        self.schedule_banner_lbl = ctk.CTkLabel(
            self.schedule_banner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#58A6FF"
        )
        self.schedule_banner_lbl.pack(side="left", padx=12, pady=6)
        
        cancel_sched_btn = ctk.CTkButton(
            self.schedule_banner,
            text="Cancel",
            font=ctk.CTkFont(size=10),
            width=60,
            height=22,
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_danger_hover"],
            text_color=THEME["text_secondary"],
            corner_radius=3,
            command=self._cancel_schedule
        )
        cancel_sched_btn.pack(side="right", padx=(4, 10), pady=6)

        self.skip_rest_btn = ctk.CTkButton(
            self.schedule_banner,
            text="▶ Start Now",
            font=ctk.CTkFont(size=10, weight="bold"),
            width=78,
            height=22,
            fg_color=THEME["btn_primary"],
            hover_color=THEME["btn_primary_hover"],
            text_color=THEME["text_primary"],
            corner_radius=3,
            command=self._skip_rest_and_start
        )
        self.skip_rest_btn.pack(side="right", padx=(0, 4), pady=6)

        # Telemetry KPI Dashboard
        kpi_row = ctk.CTkFrame(right_column, fg_color=THEME["surface_subtle"], corner_radius=6, border_width=1, border_color=THEME["border"])
        kpi_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        kpi_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.kpi_queue = self._build_kpi_cell(kpi_row, "Pending Queue", "0", 0)
        self.kpi_delivered = self._build_kpi_cell(kpi_row, "Delivered", "0", 1, accent="#3FB950")
        self.kpi_skipped = self._build_kpi_cell(kpi_row, "Unregistered", "0", 2, accent="#D29922")
        self.kpi_remaining = self._build_kpi_cell(kpi_row, "Remaining", "0", 3)

        # Progress Telemetry Block
        prog_panel = ctk.CTkFrame(right_column, fg_color="transparent")
        prog_panel.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        prog_panel.grid_columnconfigure(0, weight=1)

        self.status_detail_lbl = ctk.CTkLabel(
            prog_panel,
            text="Idle. Ready to process campaign queue.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["text_secondary"]
        )
        self.status_detail_lbl.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(
            prog_panel,
            height=5,
            fg_color=THEME["surface_subtle"],
            progress_color=THEME["status_running"],
            corner_radius=2
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew")
        self.progress_bar.set(0)

        # Activity Stream Console Header
        log_header = ctk.CTkFrame(right_column, fg_color="transparent")
        log_header.grid(row=4, column=0, sticky="ew", padx=16, pady=(6, 4))
        ctk.CTkLabel(
            log_header,
            text="ACTIVITY STREAM",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=THEME["text_dim"]
        ).pack(side="left")

        # Activity Stream Text Box (Expands with window resize)
        self.log_stream = ctk.CTkTextbox(
            right_column,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#090D13",
            text_color="#C9D1D9",
            border_width=1,
            border_color=THEME["border"],
            corner_radius=4
        )
        self.log_stream.grid(row=5, column=0, sticky="nsew", padx=16, pady=(0, 10))

        # Bottom Action Footer
        footer = ctk.CTkFrame(right_column, fg_color="transparent")
        footer.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 14))

        reports_btn = ctk.CTkButton(
            footer,
            text="Open Reports Folder",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_secondary"],
            corner_radius=4,
            command=self._open_reports
        )
        reports_btn.pack(side="left")

        preview_btn = ctk.CTkButton(
            footer,
            text="Preview Spintax Render",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["btn_secondary"],
            hover_color=THEME["btn_secondary_hover"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_secondary"],
            corner_radius=4,
            command=self._preview_spintax
        )
        preview_btn.pack(side="right")

    def _section_title(self, parent, title: str, subtitle: str):
        lbl = ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=THEME["text_primary"])
        lbl.pack(anchor="w", padx=16, pady=(12, 1))
        sub = ctk.CTkLabel(parent, text=subtitle, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=THEME["text_secondary"], wraplength=420, justify="left")
        sub.pack(anchor="w", padx=16, pady=(0, 6))

    def _pacing_row(self, parent, label_text: str, row: int, default_val: str, attr_name: str):
        lbl = ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=12), text_color=THEME["text_secondary"])
        lbl.grid(row=row, column=0, padx=14, pady=5, sticky="w")
        entry = ctk.CTkEntry(parent, width=65, height=26, fg_color=THEME["input_bg"], border_color=THEME["border"], corner_radius=3)
        entry.grid(row=row, column=1, padx=14, pady=5, sticky="e")
        entry.insert(0, default_val)
        setattr(self, attr_name, entry)

    def _build_kpi_cell(self, parent, label: str, value: str, col: int, accent: str = None):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=col, padx=6, pady=8, sticky="ew")
        val_lbl = ctk.CTkLabel(
            cell,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=accent or THEME["text_primary"]
        )
        val_lbl.pack(anchor="center")
        caption = ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=10), text_color=THEME["text_secondary"])
        caption.pack(anchor="center")
        return val_lbl

    def _load_defaults(self):
        # Load active message text
        if os.path.exists(self.message_path):
            with open(self.message_path, "r", encoding="utf-8") as f:
                self.message_box.insert("1.0", f.read().strip())
        elif self.templates_dict:
            first_key = list(self.templates_dict.keys())[0]
            self.message_box.insert("1.0", self.templates_dict[first_key])

        self._refresh_contacts_count()
        self._refresh_blacklist_status()
        self._append_log("Application initialized. Session and Playwright environment verified.")
        if is_cdp_active(self.cdp_port):
            self._append_log(f"Active Chrome session connected on CDP port {self.cdp_port} ({self.current_profile_name}).")

    def _on_profile_change(self, choice: str):
        if choice == "+ Add Profile...":
            new_name = simpledialog.askstring("Add Profile", "Enter new profile label (e.g. Sales, Account4):")
            if new_name:
                clean_name = "".join(c for c in new_name if c.isalnum() or c in "-_")
                if clean_name:
                    current_values = list(self.profile_menu.cget("values"))
                    current_values.insert(-1, clean_name)
                    self.profile_menu.configure(values=current_values)
                    self.profile_menu.set(clean_name)
                    choice = clean_name
                else:
                    self.profile_menu.set(self.current_profile_name)
                    return
            else:
                self.profile_menu.set(self.current_profile_name)
                return

        self.current_profile_name = choice
        self.profile_dir, self.cdp_port = get_profile_info(BASE_DIR, choice)
        self._append_log(f"Switched profile to '{choice}' (Path: {os.path.basename(self.profile_dir)}, Port: {self.cdp_port}).")

    def _focus_chrome(self):
        self._append_log(f"Ensuring Chrome WhatsApp Web instance is running for '{self.current_profile_name}'...")
        launch_detached_chrome(self.profile_dir, port=self.cdp_port)
        self._append_log("Chrome window active.")

    def _on_window_close(self):
        if self.is_running and self.engine:
            if not messagebox.askyesno(
                "Close Application",
                "A campaign is currently dispatching.\nClosing the application will halt the queue.\n\nNote: Chrome will remain running with your WhatsApp session.\n\nClose anyway?"
            ):
                return
            self.engine.stop()
        if self.scheduler.is_active():
            self.scheduler.cancel()
        self.destroy()
        sys.exit(0)

    # ---------------- Template Presets ----------------
    def _on_template_selected(self, preset_name: str):
        if preset_name in self.templates_dict:
            self.message_box.delete("1.0", "end")
            self.message_box.insert("1.0", self.templates_dict[preset_name])
            self._append_log(f"Loaded template preset: '{preset_name}'.")

    def _save_template_as(self):
        text = self.message_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Notice", "Message copy is empty.")
            return

        name = simpledialog.askstring("Save Preset", "Enter a name for this template preset:")
        if name:
            save_template(name, text)
            self.templates_dict = load_templates()
            self.template_menu.configure(values=list(self.templates_dict.keys()))
            self.template_menu.set(name)
            self._append_log(f"Saved new template preset: '{name}'.")

    def _delete_template_action(self):
        current_name = self.template_menu.get()
        if current_name in self.templates_dict:
            if messagebox.askyesno("Confirm Delete", f"Delete template preset '{current_name}'?"):
                delete_template(current_name)
                self.templates_dict = load_templates()
                keys = list(self.templates_dict.keys())
                self.template_menu.configure(values=keys if keys else ["Default"])
                if keys:
                    self.template_menu.set(keys[0])
                    self._on_template_selected(keys[0])
                self._append_log(f"Deleted template preset: '{current_name}'.")

    # ---------------- Blacklist & Contact Clean Tools ----------------
    def _refresh_blacklist_status(self):
        bl = load_blacklist(self.blacklist_path)
        count = len(bl)
        self.bl_status_lbl.configure(text=f"Blacklist: {count} protected numbers ({os.path.basename(self.blacklist_path)})")

    def _open_blacklist_file(self):
        if not os.path.exists(self.blacklist_path):
            with open(self.blacklist_path, "w", encoding="utf-8") as f:
                f.write("# Blacklist / Do-Not-Contact List\n# Add numbers to permanently exclude from campaigns\n")
        os.startfile(self.blacklist_path)

    def _clean_contacts_action(self):
        c_path = self.contacts_entry.get().strip()
        if not os.path.exists(c_path):
            messagebox.showerror("Error", "Contacts file not found.")
            return

        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        ext = os.path.splitext(c_path)[1].lower() or ".txt"
        out_filename = f"contacts_clean_{ts}{ext}"
        out_path = os.path.join(BASE_DIR, out_filename)

        summary = export_cleaned_contacts(
            input_file=c_path,
            output_file=out_path,
            history_file=SENT_HISTORY,
            blacklist_file=self.blacklist_path,
            reports_dir=REPORTS_DIR
        )

        msg = (
            f"Contacts Cleaned Successfully!\n\n"
            f"• Original Raw Records: {summary['total_parsed']}\n"
            f"• Excluded (Already Contacted): {summary['removed_history']}\n"
            f"• Excluded (Blacklisted): {summary['removed_blacklist']}\n"
            f"• Excluded (Not on WhatsApp): {summary['removed_unregistered']}\n\n"
            f"✓ Pure Clean Queue: {summary['clean_count']} leads\n"
            f"Saved to: {out_filename}\n\n"
            f"Would you like to set this clean file as your active queue now?"
        )

        if messagebox.askyesno("Clean Complete", msg):
            self.contacts_entry.delete(0, "end")
            self.contacts_entry.insert(0, out_path)
            self._refresh_contacts_count()

    def _refresh_contacts_count(self):
        path = self.contacts_entry.get().strip()
        if os.path.exists(path):
            contacts = load_contacts(path)
            history = load_sent_history(SENT_HISTORY)
            blacklist = load_blacklist(self.blacklist_path)
            pending = [c for c in contacts if c["phone"] not in history and c["phone"] not in blacklist]
            total = len(contacts)
            p_len = len(pending)
            bl_count = sum(1 for c in contacts if c["phone"] in blacklist)
            self.contacts_meta_lbl.configure(
                text=f"{p_len} pending ({bl_count} blacklisted, {total - p_len - bl_count} sent of {total} total)"
            )
            self.kpi_queue.configure(text=str(p_len))
        else:
            self.contacts_meta_lbl.configure(text="Specified file not found on disk.")

    def _browse_contacts(self):
        f = filedialog.askopenfilename(
            title="Select Contacts File",
            filetypes=[("Contact Files", "*.txt;*.csv"), ("Text Files (*.txt)", "*.txt"), ("CSV Files (*.csv)", "*.csv")]
        )
        if f:
            self.contacts_entry.delete(0, "end")
            self.contacts_entry.insert(0, f)
            self._refresh_contacts_count()

    def _browse_media(self):
        f = filedialog.askopenfilename(
            title="Select Promo Flyer / Media",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp"), ("All Files", "*.*")]
        )
        if f:
            self.media_entry.delete(0, "end")
            self.media_entry.insert(0, f)

    def _insert_tag(self, tag: str):
        self.message_box.insert("insert", tag)

    def _append_log(self, text: str, level: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{ts}] "
        if level == "error":
            prefix += "ERR: "
        elif level == "warning":
            prefix += "WARN: "
        else:
            prefix += "INFO: "

        self.log_stream.insert("end", prefix + text + "\n")
        self.log_stream.see("end")

    def _set_state(self, is_running: bool):
        self.is_running = is_running
        if is_running:
            self.start_btn.configure(state="disabled")
            self.schedule_btn.configure(state="disabled")
            self.test_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal", text="Pause")
            self.stop_btn.configure(state="normal")
        else:
            self.start_btn.configure(state="normal")
            self.schedule_btn.configure(state="normal")
            self.test_btn.configure(state="normal")
            self.pause_btn.configure(state="disabled", text="Pause")
            self.stop_btn.configure(state="disabled")
            self.status_pill.configure(text="● Engine Ready", text_color=THEME["status_ready"])

    def _toggle_pause(self):
        if not self.engine:
            return
        if self.is_paused:
            self.engine.resume()
            self.is_paused = False
            self.pause_btn.configure(text="Pause")
            self.status_pill.configure(text="● Active Dispatch", text_color=THEME["status_running"])
        else:
            self.engine.pause()
            self.is_paused = True
            self.pause_btn.configure(text="Resume")
            self.status_pill.configure(text="● Paused", text_color=THEME["status_paused"])

    def _stop_campaign(self):
        if self.scheduler.is_active():
            self.scheduler.cancel()
            self.schedule_banner.grid_forget()

        if self.engine:
            self.engine.stop()
            self.status_pill.configure(text="● Stopping...", text_color=THEME["status_stopped"])

            def monitor_stop():
                if self.worker_thread and self.worker_thread.is_alive():
                    self.worker_thread.join(timeout=3.0)
                self.after(0, lambda: self._set_state(False))
                self.after(0, lambda: self.status_detail_lbl.configure(text="Campaign stopped by operator."))
                self.after(0, lambda: self._append_log("Campaign stopped.", "warning"))
                self.after(0, self._refresh_contacts_count)

            threading.Thread(target=monitor_stop, daemon=True).start()
        else:
            self._set_state(False)

    # ---------------- Scheduler Controls ----------------
    def _schedule_campaign_dialog(self):
        time_choice = simpledialog.askstring(
            "Schedule Campaign",
            "Set execution time (Format: HH:MM in 24-hour time, e.g. 14:30)\nOr enter '+X' to delay by X minutes (e.g. +30):"
        )
        if not time_choice:
            return

        time_choice = time_choice.strip()
        try:
            if time_choice.startswith("+"):
                mins = int(time_choice.replace("+", ""))
                self.scheduler.schedule_in_minutes(mins, self._start_campaign)
            else:
                self.scheduler.schedule_at(time_choice, self._start_campaign)

            self.schedule_banner.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
            self.schedule_banner_lbl.configure(text=f"⏰ Scheduled for {self.scheduler.get_target_display()}...")
            self.status_pill.configure(text="● Scheduled", text_color="#58A6FF")
            self._append_log(f"Campaign scheduled for {self.scheduler.get_target_display()}.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _cancel_schedule(self):
        self.scheduler.cancel()
        self.schedule_banner.grid_forget()
        self.status_pill.configure(text="● Engine Ready", text_color=THEME["status_ready"])
        self.status_detail_lbl.configure(text="Schedule / Autopilot paused.")
        self._append_log("Campaign schedule / Autopilot rest cancelled.", "warning")

    def _skip_rest_and_start(self):
        self.scheduler.cancel()
        self.schedule_banner.grid_forget()
        self._append_log("Autopilot rest skipped by operator. Starting next batch immediately...", "info")
        self._start_campaign()

    def _on_scheduler_tick(self, remaining_sec: int, time_repr: str):
        def update():
            self.schedule_banner_lbl.configure(
                text=f"⏰ {self.scheduler.get_target_display()} — Next batch starts in {time_repr}"
            )
        self.after(0, update)

    def _open_reports(self):
        if os.path.exists(REPORTS_DIR):
            os.startfile(REPORTS_DIR)
        else:
            messagebox.showinfo("Reports", "No campaign reports generated yet.")

    def _preview_spintax(self):
        tmpl = self.message_box.get("1.0", "end").strip()
        if not tmpl:
            messagebox.showwarning("Notice", "Message template is empty.")
            return

        mock_contact = {"name": "Tanvir", "company": "Apex Trading", "phone": "8801700000001"}
        render1 = render_message(tmpl, mock_contact)
        render2 = render_message(tmpl, mock_contact)

        win = ctk.CTkToplevel(self)
        win.title("Spintax Resolution Preview")
        win.geometry("640x480")
        win.minsize(500, 360)
        win.configure(fg_color=THEME["bg"])

        ctk.CTkLabel(win, text="Resolved Variation A:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))
        tb1 = ctk.CTkTextbox(win, height=140, fg_color=THEME["surface"], border_width=1, border_color=THEME["border"], font=ctk.CTkFont(family="Consolas", size=11))
        tb1.pack(fill="x", padx=16, pady=(0, 10))
        tb1.insert("1.0", render1)

        ctk.CTkLabel(win, text="Resolved Variation B (Re-rolled):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(6, 4))
        tb2 = ctk.CTkTextbox(win, height=140, fg_color=THEME["surface"], border_width=1, border_color=THEME["border"], font=ctk.CTkFont(family="Consolas", size=11))
        tb2.pack(fill="x", padx=16, pady=(0, 16))
        tb2.insert("1.0", render2)

    def _test_single(self):
        c_path = self.contacts_entry.get().strip()
        template = self.message_box.get("1.0", "end").strip()
        media = self.media_entry.get().strip()

        if not os.path.exists(c_path):
            messagebox.showerror("Error", "Contacts file does not exist.")
            return

        contacts = load_contacts(c_path)
        history = load_sent_history(SENT_HISTORY)
        blacklist = load_blacklist(self.blacklist_path)
        pending = [c for c in contacts if c["phone"] not in history and c["phone"] not in blacklist]

        if not pending:
            messagebox.showinfo("Queue Empty", "All contacts in this file have already been contacted or are blacklisted.")
            return

        target_contact = pending[0]
        if not messagebox.askyesno(
            "Test Mode Confirmation",
            f"Send test outreach to first pending lead:\n\nPhone: +{target_contact['phone']}\nName: {target_contact.get('name', 'N/A')}\nProfile: {self.current_profile_name}\n\nChrome will stay open afterwards. Proceed?"
        ):
            return

        self._run_dispatch_thread([target_contact], template, media, 1, 2, warmup=False)

    def _start_campaign(self):
        if self.scheduler.is_active():
            self.schedule_banner.grid_forget()

        c_path = self.contacts_entry.get().strip()
        template = self.message_box.get("1.0", "end").strip()
        media = self.media_entry.get().strip()

        if not os.path.exists(c_path):
            messagebox.showerror("Error", "Contacts file not found.")
            return

        contacts = load_contacts(c_path)
        history = load_sent_history(SENT_HISTORY)
        blacklist = load_blacklist(self.blacklist_path)
        pending = [c for c in contacts if c["phone"] not in history and c["phone"] not in blacklist]

        if not pending:
            messagebox.showinfo("Queue Complete", "All contacts in this list have already been contacted or are blacklisted.")
            return

        warmup = self.warmup_var.get()
        try:
            limit = int(self.batch_entry.get().strip())
        except ValueError:
            limit = 20

        if warmup:
            limit = min(limit, 10)

        queue = pending[:limit]

        try:
            min_d = int(self.min_delay_entry.get().strip())
            max_d = int(self.max_delay_entry.get().strip())
        except ValueError:
            min_d, max_d = 15, 28

        self._run_dispatch_thread(queue, template, media, min_d, max_d, warmup=warmup)

    def _run_dispatch_thread(self, queue: List[Dict[str, Any]], template: str, media: str, min_d: int, max_d: int, warmup: bool = False):
        self._set_state(True)
        self.status_pill.configure(text="● Active Dispatch", text_color=THEME["status_running"])

        self.kpi_queue.configure(text=str(len(queue)))
        self.kpi_delivered.configure(text="0")
        self.kpi_skipped.configure(text="0")
        self.kpi_remaining.configure(text=str(len(queue)))
        self.progress_bar.set(0)

        def worker():
            def log_handler(msg, lvl):
                self.after(0, lambda: self._append_log(msg, lvl))

            def progress_handler(cur, tot, ph, name, status, countdown_sec):
                def update_ui():
                    pct = cur / tot if tot > 0 else 0
                    self.progress_bar.set(pct)
                    if status == "PAUSING":
                        self.status_detail_lbl.configure(
                            text=f"Anti-ban pacing: {countdown_sec}s pause before next lead... ({cur}/{tot})"
                        )
                    else:
                        self.status_detail_lbl.configure(
                            text=f"Processing [{cur}/{tot}] → +{ph} ({status})"
                        )
                    rem = max(0, tot - cur)
                    self.kpi_remaining.configure(text=str(rem))

                self.after(0, update_ui)

            def completion_handler(summary):
                def finalize_ui():
                    self.kpi_delivered.configure(text=str(summary.get("sent", 0)))
                    self.kpi_skipped.configure(text=str(summary.get("skipped", 0)))
                    self.kpi_remaining.configure(text="0")
                    self.progress_bar.set(1.0)
                    self._set_state(False)
                    self._refresh_contacts_count()

                    # Check pending count
                    c_path = self.contacts_entry.get().strip()
                    contacts = load_contacts(c_path) if os.path.exists(c_path) else []
                    history = load_sent_history(SENT_HISTORY)
                    blacklist = load_blacklist(self.blacklist_path)
                    pending = [c for c in contacts if c["phone"] not in history and c["phone"] not in blacklist]

                    is_cancelled = self.engine and self.engine.cancel_event.is_set()

                    if self.autopilot_var.get() and len(pending) > 0 and not is_cancelled:
                        try:
                            rest_mins = int(self.batch_rest_entry.get().strip())
                        except ValueError:
                            rest_mins = 15

                        rest_seconds = max(10, rest_mins * 60)
                        self.status_detail_lbl.configure(
                            text=f"Batch complete ({summary.get('sent', 0)} sent). Autopilot resting for {rest_mins}m before next batch ({len(pending)} leads remaining)..."
                        )
                        self.status_pill.configure(text="● Autopilot Rest", text_color=THEME["status_paused"])
                        self._append_log(
                            f"Batch complete. Autopilot active: resting for {rest_mins}m to protect account safety. Next batch starts automatically ({len(pending)} pending leads).",
                            "info"
                        )

                        self.schedule_banner.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
                        self.schedule_banner_lbl.configure(
                            text=f"☕ Autopilot Rest: Next batch starts in {rest_mins}m 00s ({len(pending)} leads remaining)"
                        )

                        self.scheduler.schedule_countdown(
                            rest_seconds,
                            callback=lambda: self.after(0, self._start_campaign),
                            label="Autopilot Rest"
                        )
                    else:
                        self.status_detail_lbl.configure(text="Batch completed. Chrome remains open.")
                        self.status_pill.configure(text="● Completed", text_color=THEME["status_ready"])

                        if len(pending) == 0 and not is_cancelled:
                            self._append_log("Entire contact list has been processed! All campaigns complete.", "success")
                            messagebox.showinfo("Campaign Complete", "All contacts in your queue have been processed successfully!")

                        reports = summary.get("reports", {})
                        if "html" in reports and not self.autopilot_var.get():
                            if messagebox.askyesno("Batch Finished", "Session complete. Open the interactive analytics report now?"):
                                webbrowser.open(reports["html"])

                self.after(0, finalize_ui)

            try:
                blacklist_set = load_blacklist(self.blacklist_path)

                self.engine = OutreachEngine(
                    profile_dir=self.profile_dir,
                    history_file=SENT_HISTORY,
                    reports_dir=REPORTS_DIR,
                    port=self.cdp_port,
                    on_log=log_handler,
                    on_progress=progress_handler,
                    on_finished=completion_handler
                )

                self.engine.run_campaign(
                    queue=queue,
                    message_template=template,
                    media_path=media if os.path.exists(media) else None,
                    min_delay=min_d,
                    max_delay=max_d,
                    blacklist=blacklist_set,
                    warmup_mode=warmup,
                    keep_browser_open=True
                )
            except Exception as ex:
                self.after(0, lambda: self._append_log(f"Engine interrupted: {ex}", "error"))
                self.after(0, lambda: self.status_detail_lbl.configure(text=f"Engine stopped due to error: {ex}"))
                self.after(0, lambda: self.status_pill.configure(text="● Error", text_color=THEME["btn_danger"]))
                self.after(0, lambda: self._set_state(False))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()


def launch_gui():
    app = ModernOutreachApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
