"""
WhatsApp Outreach Engine - Enterprise Desktop Client
====================================================
Designed with a clean, minimalist developer-tool aesthetic (Linear/GitHub dark mode).
Eliminates juvenile AI design cliches in favor of crisp typography, subtle neutral palettes,
and precise status telemetry.

Fully responsive: adapts smoothly to any window dimension or display scaling.
Persistent browser: Chrome runs detached via CDP and remains open even when the GUI is closed.
"""

import os
import sys
import threading
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any, List

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.contact_loader import load_contacts, load_sent_history
from core.spintax import render_message
from core.engine import OutreachEngine, launch_detached_chrome, is_cdp_active, CDP_PORT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONTACTS = os.path.join(BASE_DIR, "contacts.local.txt")
if not os.path.exists(DEFAULT_CONTACTS):
    DEFAULT_CONTACTS = os.path.join(BASE_DIR, "contacts.txt")

DEFAULT_MESSAGE = os.path.join(BASE_DIR, "message.local.txt")
if not os.path.exists(DEFAULT_MESSAGE):
    DEFAULT_MESSAGE = os.path.join(BASE_DIR, "message.txt")

SENT_HISTORY = os.path.join(BASE_DIR, "sent_history.txt")
PROFILE_DIR = os.path.join(BASE_DIR, "wa_profile")
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
        self.geometry("1120x760")
        self.minsize(880, 580)
        self.configure(fg_color=THEME["bg"])

        ctk.set_appearance_mode("dark")

        # Runtime Engine References
        self.engine: Optional[OutreachEngine] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.is_paused = False

        self.contacts_path = DEFAULT_CONTACTS
        self.message_path = DEFAULT_MESSAGE
        self.media_path = ""

        # Window closing protocol
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._build_interface()
        self._load_defaults()

    def _build_interface(self):
        # Master grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------------- 1. Top Navigation Bar ----------------
        navbar = ctk.CTkFrame(self, fg_color=THEME["surface"], corner_radius=0, height=52, border_width=0)
        navbar.grid(row=0, column=0, sticky="ew")
        navbar.grid_columnconfigure(1, weight=1)

        # App Brand & Version
        brand_box = ctk.CTkFrame(navbar, fg_color="transparent")
        brand_box.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        title_lbl = ctk.CTkLabel(
            brand_box,
            text="WhatsApp Outreach",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=THEME["text_primary"]
        )
        title_lbl.pack(side="left", padx=(0, 8))

        ver_pill = ctk.CTkLabel(
            brand_box,
            text="v1.2.0",
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

        # Focus / Open Chrome Button
        open_chrome_btn = ctk.CTkButton(
            nav_right,
            text="Focus Chrome",
            width=96,
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
        workspace.grid_columnconfigure(0, weight=1, minsize=380)
        workspace.grid_columnconfigure(1, weight=1, minsize=420)
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

        # Field: Contacts File
        self._section_title(left_column, "Contacts Source", "Accepts .txt (one number per line) or .csv with headers")
        
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

        self.contacts_meta_lbl = ctk.CTkLabel(
            left_column,
            text="Reading queue status...",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_secondary"]
        )
        self.contacts_meta_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        # Field: Message Copy
        self._section_title(
            left_column,
            "Message Template",
            "Supports Spintax variation {A|B} and dynamic tags: {name}, {company}, {phone}"
        )

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
            height=180,
            fg_color=THEME["input_bg"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=4
        )
        self.message_box.pack(fill="x", padx=16, pady=(0, 14))

        # Field: Attachment (Optional)
        self._section_title(left_column, "Media Attachment (Optional)", "Send an image flyer or banner with your message caption")

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

        # Field: Pacing & Batch Constraints
        self._section_title(left_column, "Pacing Configuration", "Enforces velocity limits to ensure account safety")

        pacing_card = ctk.CTkFrame(left_column, fg_color=THEME["surface_subtle"], corner_radius=6, border_width=1, border_color=THEME["border"])
        pacing_card.pack(fill="x", padx=16, pady=(0, 16))
        pacing_card.grid_columnconfigure(0, weight=1)
        pacing_card.grid_columnconfigure(1, weight=0)

        self._pacing_row(pacing_card, "Batch Size limit:", 0, "20", "batch_entry")
        self._pacing_row(pacing_card, "Minimum Delay (seconds):", 1, "15", "min_delay_entry")
        self._pacing_row(pacing_card, "Maximum Delay (seconds):", 2, "28", "max_delay_entry")

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
        
        # Configure row weights: Row 4 (Log Textbox) expands to absorb all resizing space!
        right_column.grid_rowconfigure(0, weight=0)  # Toolbar
        right_column.grid_rowconfigure(1, weight=0)  # KPI row
        right_column.grid_rowconfigure(2, weight=0)  # Progress panel
        right_column.grid_rowconfigure(3, weight=0)  # Log header
        right_column.grid_rowconfigure(4, weight=1)  # Activity stream box (Expands!)
        right_column.grid_rowconfigure(5, weight=0)  # Footer actions

        # Control Action Toolbar
        toolbar = ctk.CTkFrame(right_column, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        toolbar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.start_btn = ctk.CTkButton(
            toolbar,
            text="Start Queue",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=THEME["btn_primary"],
            hover_color=THEME["btn_primary_hover"],
            height=34,
            corner_radius=4,
            command=self._start_campaign
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

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
        self.pause_btn.grid(row=0, column=1, padx=4, sticky="ew")

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
        self.stop_btn.grid(row=0, column=2, padx=4, sticky="ew")

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
        self.test_btn.grid(row=0, column=3, padx=(4, 0), sticky="ew")

        # Telemetry KPI Dashboard
        kpi_row = ctk.CTkFrame(right_column, fg_color=THEME["surface_subtle"], corner_radius=6, border_width=1, border_color=THEME["border"])
        kpi_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        kpi_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.kpi_queue = self._build_kpi_cell(kpi_row, "Pending Queue", "0", 0)
        self.kpi_delivered = self._build_kpi_cell(kpi_row, "Delivered", "0", 1, accent="#3FB950")
        self.kpi_skipped = self._build_kpi_cell(kpi_row, "Unregistered", "0", 2, accent="#D29922")
        self.kpi_remaining = self._build_kpi_cell(kpi_row, "Remaining", "0", 3)

        # Progress Telemetry Block
        prog_panel = ctk.CTkFrame(right_column, fg_color="transparent")
        prog_panel.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
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
        log_header.grid(row=3, column=0, sticky="ew", padx=16, pady=(6, 4))
        ctk.CTkLabel(
            log_header,
            text="ACTIVITY STREAM",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=THEME["text_dim"]
        ).pack(side="left")

        # Activity Stream Text Box (Expands smoothly with window resize)
        self.log_stream = ctk.CTkTextbox(
            right_column,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#090D13",
            text_color="#C9D1D9",
            border_width=1,
            border_color=THEME["border"],
            corner_radius=4
        )
        self.log_stream.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 10))

        # Bottom Action Footer
        footer = ctk.CTkFrame(right_column, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))

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
        lbl.grid(row=row, column=0, padx=14, pady=6, sticky="w")
        entry = ctk.CTkEntry(parent, width=65, height=26, fg_color=THEME["input_bg"], border_color=THEME["border"], corner_radius=3)
        entry.grid(row=row, column=1, padx=14, pady=6, sticky="e")
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
        if os.path.exists(self.message_path):
            with open(self.message_path, "r", encoding="utf-8") as f:
                self.message_box.insert("1.0", f.read().strip())
        self._refresh_contacts_count()
        self._append_log("Application initialized. Session and Playwright environment verified.")
        if is_cdp_active(CDP_PORT):
            self._append_log(f"Active Chrome session detected on CDP port {CDP_PORT}.")

    def _focus_chrome(self):
        self._append_log("Ensuring persistent Chrome window is running...")
        launch_detached_chrome(PROFILE_DIR, port=CDP_PORT)
        self._append_log("Chrome window active.")

    def _on_window_close(self):
        if self.is_running and self.engine:
            if not messagebox.askyesno(
                "Close Application",
                "A campaign is currently in progress.\nClosing the application will halt the queue.\n\nNote: Chrome will remain open on your desktop with your WhatsApp chats.\n\nClose anyway?"
            ):
                return
            self.engine.stop()
        self.destroy()
        sys.exit(0)

    def _refresh_contacts_count(self):
        path = self.contacts_entry.get().strip()
        if os.path.exists(path):
            contacts = load_contacts(path)
            history = load_sent_history(SENT_HISTORY)
            pending = [c for c in contacts if c["phone"] not in history]
            total = len(contacts)
            p_len = len(pending)
            self.contacts_meta_lbl.configure(
                text=f"{p_len} pending outreach ({total - p_len} previously contacted of {total} total)"
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
            self.test_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal", text="Pause")
            self.stop_btn.configure(state="normal")
        else:
            self.start_btn.configure(state="normal")
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
        if self.engine:
            self.engine.stop()
            self.status_pill.configure(text="● Stopping...", text_color=THEME["status_stopped"])

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
        pending = [c for c in contacts if c["phone"] not in history]

        if not pending:
            messagebox.showinfo("Queue Empty", "All contacts in this file have already been contacted.")
            return

        target_contact = pending[0]
        if not messagebox.askyesno(
            "Test Mode Confirmation",
            f"Send test outreach to first pending lead:\n\nPhone: +{target_contact['phone']}\nName: {target_contact.get('name', 'N/A')}\n\nChrome will stay open afterwards. Proceed?"
        ):
            return

        self._run_dispatch_thread([target_contact], template, media, 1, 2)

    def _start_campaign(self):
        c_path = self.contacts_entry.get().strip()
        template = self.message_box.get("1.0", "end").strip()
        media = self.media_entry.get().strip()

        if not os.path.exists(c_path):
            messagebox.showerror("Error", "Contacts file not found.")
            return

        contacts = load_contacts(c_path)
        history = load_sent_history(SENT_HISTORY)
        pending = [c for c in contacts if c["phone"] not in history]

        if not pending:
            messagebox.showinfo("Queue Complete", "All contacts in this list have already been contacted.")
            return

        try:
            limit = int(self.batch_entry.get().strip())
        except ValueError:
            limit = 20

        queue = pending[:limit]

        try:
            min_d = int(self.min_delay_entry.get().strip())
            max_d = int(self.max_delay_entry.get().strip())
        except ValueError:
            min_d, max_d = 15, 28

        if not messagebox.askyesno(
            "Confirm Outreach Batch",
            f"Launch outreach campaign to {len(queue)} pending contact(s)?\n\nPacing delay: {min_d}s to {max_d}s between dispatches.\nChrome will remain running on your desktop."
        ):
            return

        self._run_dispatch_thread(queue, template, media, min_d, max_d)

    def _run_dispatch_thread(self, queue: List[Dict[str, Any]], template: str, media: str, min_d: int, max_d: int):
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
                    self.status_detail_lbl.configure(text="Batch completed. Chrome remains open.")
                    self.status_pill.configure(text="● Completed", text_color=THEME["status_ready"])
                    self._set_state(False)
                    self._refresh_contacts_count()

                    reports = summary.get("reports", {})
                    if "html" in reports:
                        if messagebox.askyesno("Batch Finished", "Session complete. Open the interactive analytics report now?"):
                            webbrowser.open(reports["html"])

                self.after(0, finalize_ui)

            self.engine = OutreachEngine(
                profile_dir=PROFILE_DIR,
                history_file=SENT_HISTORY,
                reports_dir=REPORTS_DIR,
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
                keep_browser_open=True
            )

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()


def launch_gui():
    app = ModernOutreachApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
