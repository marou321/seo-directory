# admin_app.py
import os
import threading
from datetime import datetime
import requests
import customtkinter as ctk

# ============================================================================
# HARDCODED CONFIGURATION CONSTANTS (Update or override via Environment Vars)
# ============================================================================
NODE_API_URL = os.getenv("NODE_API_URL", "http://localhost:3000/api/admin/stats")
NODE_API_KEY = os.getenv("NODE_API_KEY", "seo-secret-api-key-2026")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "ghp_replace_with_your_github_pat_token")
GITHUB_REPO = os.getenv("GITHUB_REPO", "marou321/seo-directory")
GITHUB_WORKFLOW_FILE = os.getenv("GITHUB_WORKFLOW_FILE", "automate.yml")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")


class MetricCard(ctk.CTkFrame):
    """Reusable dark-themed metric card widget for displaying KPI telemetry."""

    def __init__(self, master, title: str, initial_value: str, subtitle: str, accent_color: str = "#6366f1"):
        super().__init__(
            master,
            fg_color="#111827",
            corner_radius=14,
            border_width=1,
            border_color="#1f2937",
        )

        self.grid_columnconfigure(0, weight=1)

        self.accent_bar = ctk.CTkFrame(
            self,
            height=4,
            fg_color=accent_color,
            corner_radius=2,
        )
        self.accent_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))

        self.title_label = ctk.CTkLabel(
            self,
            text=title.upper(),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#9ca3af",
            anchor="w",
        )
        self.title_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(2, 4))

        self.value_label = ctk.CTkLabel(
            self,
            text=initial_value,
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color="#f9fafb",
            anchor="w",
        )
        self.value_label.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 4))

        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#6b7280",
            anchor="w",
        )
        self.subtitle_label.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 16))

    def update_metric(self, value: str, subtitle: str | None = None) -> None:
        self.value_label.configure(text=value)
        if subtitle is not None:
            self.subtitle_label.configure(text=subtitle)


class SEOAdminControlPanel(ctk.CTk):
    """Standalone Desktop Admin Control Panel for the Programmatic SEO Directory."""

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("TechPay SEO Directory — Desktop Admin Control Panel")
        self.geometry("860x560")
        self.minsize(780, 520)
        self.configure(fg_color="#030712")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_kpi_grid()
        self._build_control_panel()
        self._build_footer()

        # Fetch live stats automatically on startup
        self.after(250, self.refresh_stats_async)

    def _build_header(self) -> None:
        header_frame = ctk.CTkFrame(
            self,
            fg_color="#0f172a",
            corner_radius=16,
            border_width=1,
            border_color="#1e293b",
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 14))
        header_frame.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w", padx=20, pady=16)

        badge_label = ctk.CTkLabel(
            title_box,
            text="PROGRAMMATIC SEO TELEMETRY & AUTOMATION",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#818cf8",
            anchor="w",
        )
        badge_label.pack(anchor="w")

        app_title = ctk.CTkLabel(
            title_box,
            text="TechPay Admin Control Center",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#f8fafc",
            anchor="w",
        )
        app_title.pack(anchor="w", pady=(2, 0))

        self.refresh_btn = ctk.CTkButton(
            header_frame,
            text="⟳  Refresh Live Stats",
            command=self.refresh_stats_async,
            width=175,
            height=40,
            corner_radius=10,
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#475569",
            text_color="#f1f5f9",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.refresh_btn.grid(row=0, column=1, sticky="e", padx=20, pady=16)

    def _build_kpi_grid(self) -> None:
        kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        kpi_container.grid(row=1, column=0, sticky="ew", padx=24, pady=6)
        kpi_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="kpi")

        self.pages_card = MetricCard(
            kpi_container,
            title="Total Generated Pages",
            initial_value="--",
            subtitle="Indexed in SQLite data.db",
            accent_color="#6366f1",
        )
        self.pages_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.views_card = MetricCard(
            kpi_container,
            title="Total Page Views",
            initial_value="--",
            subtitle="Today: -- views",
            accent_color="#0ea5e9",
        )
        self.views_card.grid(row=0, column=1, sticky="nsew", padx=8)

        self.earnings_card = MetricCard(
            kpi_container,
            title="Estimated Earnings",
            initial_value="$0.00",
            subtitle="Formula: (Views / 1000) * $5.00 RPM",
            accent_color="#10b981",
        )
        self.earnings_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

    def _build_control_panel(self) -> None:
        action_frame = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=16,
            border_width=1,
            border_color="#1f2937",
        )
        action_frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(14, 14))
        action_frame.grid_columnconfigure(0, weight=1)

        section_title = ctk.CTkLabel(
            action_frame,
            text="GitHub Actions Remote Pipeline Trigger",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#f9fafb",
            anchor="w",
        )
        section_title.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 4))

        section_desc = ctk.CTkLabel(
            action_frame,
            text=(
                f"Dispatches workflow '{GITHUB_WORKFLOW_FILE}' on repository '{GITHUB_REPO}' "
                f"(branch: '{GITHUB_BRANCH}') via the GitHub REST API to scrape, enrich with OpenAI, "
                "and commit the updated data.db."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#9ca3af",
            anchor="w",
            justify="left",
            wraplength=760,
        )
        section_desc.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 18))

        self.run_pipeline_btn = ctk.CTkButton(
            action_frame,
            text="⚡  RUN AUTOMATED AI PIPELINE (GITHUB WORKFLOW DISPATCH)",
            command=self.trigger_pipeline_async,
            height=54,
            corner_radius=12,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        )
        self.run_pipeline_btn.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 16))

        status_box = ctk.CTkFrame(
            action_frame,
            fg_color="#030712",
            corner_radius=10,
            border_width=1,
            border_color="#1f2937",
        )
        status_box.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 20))
        status_box.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_box,
            text="System Ready — Waiting for command.",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#94a3b8",
            anchor="w",
            justify="left",
            wraplength=740,
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=14, pady=12)

    def _build_footer(self) -> None:
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", padx=26, pady=(0, 16))
        footer_frame.grid_columnconfigure(0, weight=1)

        self.endpoint_label = ctk.CTkLabel(
            footer_frame,
            text=f"API Target: {NODE_API_URL}   |   GitHub Repo: {GITHUB_REPO}",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#64748b",
            anchor="w",
        )
        self.endpoint_label.grid(row=0, column=0, sticky="w")

        self.last_sync_label = ctk.CTkLabel(
            footer_frame,
            text="Last Sync: Never",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#64748b",
            anchor="e",
        )
        self.last_sync_label.grid(row=0, column=1, sticky="e")

    def _set_status(self, message: str, color: str = "#94a3b8") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_label.configure(text=f"[{timestamp}] {message}", text_color=color)

    # ========================================================================
    # NODE.JS API TELEMETRY FETCH
    # ========================================================================
    def refresh_stats_async(self) -> None:
        self.refresh_btn.configure(state="disabled", text="Syncing...")
        self._set_status(f"Fetching stats from {NODE_API_URL} ...", "#38bdf8")
        worker = threading.Thread(target=self._fetch_stats_worker, daemon=True)
        worker.start()

    def _fetch_stats_worker(self) -> None:
        headers = {
            "API_KEY": NODE_API_KEY,
            "Accept": "application/json",
        }
        try:
            response = requests.get(NODE_API_URL, headers=headers, timeout=10)
            if response.status_code == 200:
                payload = response.json()
                self.after(0, self._on_stats_success, payload)
            else:
                try:
                    err_msg = response.json().get("error", response.text)
                except Exception:
                    err_msg = response.text
                self.after(0, self._on_stats_error, f"HTTP {response.status_code}: {err_msg}")
        except requests.RequestException as exc:
            self.after(0, self._on_stats_error, f"Connection failed: {exc}")

    def _on_stats_success(self, payload: dict) -> None:
        total_pages = int(payload.get("total_pages", 0))
        total_views = int(payload.get("total_views", 0))
        today_views = int(payload.get("today_views", 0))
        rpm = float(payload.get("rpm", 5.0))
        estimated_earnings = float(payload.get("estimated_earnings", (total_views / 1000.0) * rpm))

        self.pages_card.update_metric(
            value=f"{total_pages:,}",
            subtitle="Indexed in SQLite data.db",
        )
        self.views_card.update_metric(
            value=f"{total_views:,}",
            subtitle=f"Today: {today_views:,} views",
        )
        self.earnings_card.update_metric(
            value=f"${estimated_earnings:,.2f}",
            subtitle=f"Formula: (Views / 1000) * ${rpm:.2f} RPM",
        )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_sync_label.configure(text=f"Last Sync: {now_str}")
        self._set_status("Stats refreshed successfully from Node.js SQLite API.", "#34d399")
        self.refresh_btn.configure(state="normal", text="⟳  Refresh Live Stats")

    def _on_stats_error(self, error_message: str) -> None:
        self._set_status(f"Stats Error — {error_message}", "#f87171")
        self.refresh_btn.configure(state="normal", text="⟳  Refresh Live Stats")

    # ========================================================================
    # GITHUB REST API WORKFLOW DISPATCH TRIGGER
    # ========================================================================
    def trigger_pipeline_async(self) -> None:
        self.run_pipeline_btn.configure(
            state="disabled",
            text="⏳  DISPATCHING WORKFLOW TO GITHUB ACTIONS...",
        )
        self._set_status(
            f"Sending workflow_dispatch POST request to {GITHUB_REPO} ({GITHUB_WORKFLOW_FILE})...",
            "#fbbf24",
        )
        worker = threading.Thread(target=self._trigger_pipeline_worker, daemon=True)
        worker.start()

    def _trigger_pipeline_worker(self) -> None:
        dispatch_url = (
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW_FILE}/dispatches"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        body = {"ref": GITHUB_BRANCH}

        try:
            response = requests.post(dispatch_url, headers=headers, json=body, timeout=15)
            # GitHub REST API returns HTTP 204 No Content when workflow_dispatch succeeds
            if response.status_code == 204:
                self.after(
                    0,
                    self._on_pipeline_result,
                    True,
                    "Pipeline Started Successfully! GitHub Action 'automate.yml' is now running.",
                )
            else:
                try:
                    err_detail = response.json().get("message", response.text)
                except Exception:
                    err_detail = response.text
                self.after(
                    0,
                    self._on_pipeline_result,
                    False,
                    f"GitHub API Error (HTTP {response.status_code}): {err_detail}",
                )
        except requests.RequestException as exc:
            self.after(
                0,
                self._on_pipeline_result,
                False,
                f"Network Error while contacting GitHub API: {exc}",
            )

    def _on_pipeline_result(self, success: bool, message: str) -> None:
        if success:
            self._set_status(message, "#34d399")
        else:
            self._set_status(message, "#f87171")

        self.run_pipeline_btn.configure(
            state="normal",
            text="⚡  RUN AUTOMATED AI PIPELINE (GITHUB WORKFLOW DISPATCH)",
        )


if __name__ == "__main__":
    app = SEOAdminControlPanel()
    app.mainloop()
