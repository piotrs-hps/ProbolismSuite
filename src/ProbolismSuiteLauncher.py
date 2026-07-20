#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probolism Suite v1.1 by piotrs

Windows launcher for three independent applications:

    modules/search/ProbolismSearch.exe
    modules/browser/ProbolismBrowser.exe
    modules/seestar/ProbolismSeestar.exe

The launcher uses only the Python standard library. It may be run directly
from Python or packaged with PyInstaller.

Suggested build command:

    python -m PyInstaller --noconfirm --clean --onedir --windowed ^
        --name ProbolismLauncher_1_1 ProbolismLauncher_1_1.py
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk


APP_TITLE = "Probolism Suite v1.1"
APP_VERSION = "1.1"

MODULES = {
    "search": {
        "label": "Search for Probolisms",
        "description": "Calculate Probolism candidates using Gaia and VizieR catalogues.",
        "relative_path": Path("modules") / "search" / "ProbolismSearch.exe",
    },
    "browser": {
        "label": "Browse Probolism Candidates",
        "description": "Open candidate CSV files and inspect astronomical sky images.",
        "relative_path": Path("modules") / "browser" / "ProbolismBrowser.exe",
    },
    "seestar": {
        "label": "Observe with Seestar",
        "description": "Send candidate coordinates to Seestar through ASCOM Alpaca.",
        "relative_path": Path("modules") / "seestar" / "ProbolismSeestar.exe",
    },
}

USER_GUIDE_TEXT = """PROBOLISM SUITE v1.1 — USER GUIDE

1. WHAT IS A PROBOLISM?
Within this project, a Probolism is a candidate area of the sky where a local
concentration or apparent grouping of stars and galaxies is detected within a
small angular field. Candidate Probolisms are identified by comparing stellar
data from Gaia with galaxy data from VizieR and evaluating the resulting sky
fields according to the program's search criteria.

2. SUITE PROGRAMS
Probolism Suite starts three independent programs:

• Search for Probolisms
  Calculates candidate Probolisms using Gaia and VizieR data. The user selects
  or creates the folder in which CSV result files are saved.

• Browse Probolism Candidates
  Opens candidate CSV files and displays astronomical sky images. The user
  selects the CSV file and its folder directly inside this program.

• Observe with Seestar
  Opens candidate CSV files and sends GoTo commands to a Seestar telescope
  through ASCOM Alpaca in the local network. The user selects the CSV file and
  its folder directly inside this program.

3. EXPECTED FOLDER STRUCTURE
The launcher expects this structure:

ProbolismLauncher_1_1/
├── ProbolismLauncher_1_1.exe
├── _internal/
└── modules/
    ├── search/
    │   ├── ProbolismSearch.exe
    │   └── _internal/
    ├── browser/
    │   ├── ProbolismBrowser.exe
    │   └── _internal/
    └── seestar/
        ├── ProbolismSeestar.exe
        └── _internal/

Do not move individual EXE files away from their _internal folders.

4. MAIN BUTTONS
Search for Probolisms
Starts the Gaia/VizieR search module.

Browse Probolism Candidates
Starts the candidate browser.

Observe with Seestar
Starts the Seestar module.

If a module is not installed or its EXE file cannot be found, its Open button
is not displayed.

5. USER FOLDER
The launcher stores its logs under:

%LOCALAPPDATA%\\ProbolismsSuite\\logs\\

Use Open Logs Folder to open this location.

6. DIAGNOSTICS
Diagnostics checks:

• Windows and Python architecture
• launcher location
• user data write access
• presence of all three module EXE files

A diagnostic report is saved in the Logs folder.

7. SEESTAR REQUIREMENTS
The computer running the Seestar module must be connected to the same local
network as the Seestar/ASCOM Alpaca device. Windows Firewall must allow the
required local network communication.

8. TROUBLESHOOTING
If a module does not start:

• Run Diagnostics and inspect the report.
• Verify that the full module folder, including _internal, is present.
• Do not copy only the EXE file.
• Check Windows Defender or other antivirus quarantine.
• Confirm that Windows architecture matches the program build.
• Try starting the module EXE directly from its own folder.
• Review launcher.log in the Logs folder.

9. CLOSING THE LAUNCHER
Closing the launcher does not close modules already started. Each module runs
as a separate process.

Authorship
----------
© 2026 piotrs. All rights reserved. This program was developed by the author with the use of AI tools, including ChatGPT, as support in creating and improving the code.
"""


def application_directory() -> Path:
    """Return the directory containing the script or packaged launcher."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def local_app_data_directory() -> Path:
    """Return a writable per-user data directory."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "ProbolismsSuite"
    return Path.home() / "AppData" / "Local" / "ProbolismsSuite"


def open_path_in_system(path: Path) -> None:
    """Open a file or directory using the operating system shell."""
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist:\n{path}")

    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class ProbolismsLauncher:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.app_dir = application_directory()

        self.data_dir = local_app_data_directory()
        self.logs_dir = self.data_dir / "logs"
        self.log_file = self.logs_dir / "launcher.log"

        for directory in (
            self.data_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self.status_var = tk.StringVar(value="Ready.")
        self.module_status_labels: dict[str, ttk.Label] = {}
        self.module_open_buttons: dict[str, ttk.Button] = {}

        self._configure_root()
        self._configure_styles()
        self._build_interface()
        self._refresh_module_statuses()
        self._write_log("Launcher started.")

    def _configure_root(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("920x510")
        self.root.minsize(820, 460)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        try:
            self.root.option_add("*Font", ("Segoe UI", 10))
        except Exception:
            pass

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("ModuleTitle.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("Module.TButton", font=("Segoe UI", 11, "bold"), padding=(14, 12))
        style.configure("Utility.TButton", padding=(10, 7))
        style.configure("Status.TLabel", padding=(8, 5))

    def _build_interface(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")

        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)

        ttk.Label(title_area, text="PROBOLISM SUITE by piotrs", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_area,
            text="Search, inspect and observe Probolism candidates",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        ttk.Button(
            header,
            text="User Guide",
            style="Utility.TButton",
            command=self._show_user_guide,
        ).pack(side="right", anchor="ne")

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(15, 16))

        modules_frame = ttk.LabelFrame(outer, text="Suite Modules", padding=14)
        modules_frame.pack(fill="x")
        modules_frame.columnconfigure(0, weight=1)

        for row, module_key in enumerate(("search", "browser", "seestar")):
            module = MODULES[module_key]
            card = ttk.Frame(modules_frame, padding=(6, 8))
            card.grid(row=row, column=0, sticky="ew")

            text_frame = ttk.Frame(card)
            text_frame.pack(side="left", fill="both", expand=True)

            ttk.Label(
                text_frame,
                text=module["label"],
                style="ModuleTitle.TLabel",
            ).pack(anchor="w")

            ttk.Label(
                text_frame,
                text=module["description"],
                wraplength=560,
                justify="left",
            ).pack(anchor="w", pady=(3, 0))

            status_label = ttk.Label(text_frame, text="Checking...")
            status_label.pack(anchor="w", pady=(5, 0))
            self.module_status_labels[module_key] = status_label

            open_button = ttk.Button(
                card,
                text="Open",
                width=16,
                style="Module.TButton",
                command=lambda key=module_key: self._launch_module(key),
            )
            self.module_open_buttons[module_key] = open_button

        utility_frame = ttk.LabelFrame(outer, text="Tools", padding=14)
        utility_frame.pack(fill="x", pady=(16, 0))

        utility_buttons = (
            ("Open Logs Folder", self._open_logs_folder),
            ("Diagnostics", self._run_diagnostics),
            ("Refresh Status", self._refresh_module_statuses),
        )

        for column, (text, command) in enumerate(utility_buttons):
            ttk.Button(
                utility_frame,
                text=text,
                style="Utility.TButton",
                command=command,
            ).grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 7, 0))
            utility_frame.columnconfigure(column, weight=1)

        bottom = ttk.Frame(outer)
        bottom.pack(side="bottom", fill="x", pady=(18, 0))
        ttk.Separator(bottom, orient="horizontal").pack(fill="x", pady=(0, 8))

        ttk.Label(
            bottom,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).pack(side="left", fill="x", expand=True)

        ttk.Label(bottom, text=f"Version {APP_VERSION}").pack(side="right", padx=(10, 0))

    def _write_log(self, message: str) -> None:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def _module_executable(self, module_key: str) -> Path:
        return self.app_dir / MODULES[module_key]["relative_path"]

    def _refresh_module_statuses(self) -> None:
        installed_count = 0
        for module_key, label in self.module_status_labels.items():
            exe_path = self._module_executable(module_key)
            open_button = self.module_open_buttons[module_key]
            if exe_path.is_file():
                label.configure(text=f"Status: installed — {exe_path.name}")
                if not open_button.winfo_manager():
                    open_button.pack(side="right", padx=(14, 0))
                installed_count += 1
            else:
                label.configure(text=f"Status: not found — {exe_path}")
                if open_button.winfo_manager():
                    open_button.pack_forget()

        self.status_var.set(
            f"Module check complete: {installed_count} of {len(MODULES)} modules found."
        )
        self._write_log(f"Module status refreshed: {installed_count}/{len(MODULES)} found.")

    def _launch_module(self, module_key: str) -> None:
        module = MODULES[module_key]
        exe_path = self._module_executable(module_key)

        if not exe_path.is_file():
            messagebox.showerror(
                "Module Not Found",
                "The requested module could not be found.\n\n"
                f"Expected file:\n{exe_path}\n\n"
                "Run Diagnostics and verify the installation folder.",
                parent=self.root,
            )
            self._write_log(f"Module missing: {exe_path}")
            return

        command = [str(exe_path)]

        try:
            subprocess.Popen(command, cwd=str(exe_path.parent), close_fds=True)
            self.status_var.set(f"Started: {module['label']}.")
            self._write_log(f"Started module: {exe_path}")
        except Exception as exc:
            self._write_log(
                f"Failed to start module {exe_path}: {exc}\n{traceback.format_exc()}"
            )
            messagebox.showerror(
                "Module Start Error",
                "The module could not be started.\n\n"
                f"Program:\n{exe_path}\n\n"
                f"Error:\n{exc}\n\n"
                f"See the log file:\n{self.log_file}",
                parent=self.root,
            )

    def _open_logs_folder(self) -> None:
        self._safe_open_path(self.logs_dir, "logs folder")

    def _safe_open_path(self, path: Path, description: str = "path") -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
            open_path_in_system(path)
            self.status_var.set(f"Opened {description}.")
        except Exception as exc:
            messagebox.showerror(
                "Open Path Error",
                f"Could not open:\n{path}\n\n{exc}",
                parent=self.root,
            )

    def _run_diagnostics(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.logs_dir / f"diagnostics_{timestamp}.txt"

        lines = [
            "PROBOLISM SUITE v1.1 — DIAGNOSTIC REPORT",
            "=" * 54,
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "SYSTEM",
            f"Operating system: {platform.platform()}",
            f"Machine architecture: {platform.machine()}",
            f"Python architecture: {platform.architecture()[0]}",
            f"Python version: {platform.python_version()}",
            f"Frozen/PyInstaller build: {bool(getattr(sys, 'frozen', False))}",
            "",
            "PATHS",
            f"Launcher directory: {self.app_dir}",
            f"Data directory: {self.data_dir}",
            f"Logs directory: {self.logs_dir}",
            "",
            "WRITE TEST",
        ]

        write_test_path = self.data_dir / "write_test.tmp"
        try:
            write_test_path.write_text("ok", encoding="utf-8")
            write_test_path.unlink(missing_ok=True)
            lines.append("User data directory write access: OK")
        except Exception as exc:
            lines.append(f"User data directory write access: FAILED — {exc}")

        lines.extend(["", "MODULES"])
        all_modules_present = True
        for module_key, module in MODULES.items():
            exe_path = self._module_executable(module_key)
            present = exe_path.is_file()
            all_modules_present = all_modules_present and present
            lines.append(f"{module['label']}: {'FOUND' if present else 'MISSING'}")
            lines.append(f"  Expected path: {exe_path}")

        lines.extend(
            [
                "",
                "SUMMARY",
                f"All modules present: {'YES' if all_modules_present else 'NO'}",
                f"Launcher log: {self.log_file}",
            ]
        )

        try:
            report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.status_var.set(f"Diagnostic report created: {report_path.name}")
            self._write_log(f"Diagnostic report created: {report_path}")
            messagebox.showinfo(
                "Diagnostics Complete",
                "The diagnostic report has been created.\n\n"
                f"{report_path}",
                parent=self.root,
            )
            try:
                open_path_in_system(report_path)
            except Exception:
                pass
        except Exception as exc:
            self._write_log(f"Diagnostics failed: {exc}")
            messagebox.showerror(
                "Diagnostics Error",
                f"Could not create the diagnostic report.\n\n{exc}",
                parent=self.root,
            )

    def _show_user_guide(self) -> None:
        guide_window = tk.Toplevel(self.root)
        guide_window.title("Probolism Suite v1.1 — User Guide")
        guide_window.geometry("820x650")
        guide_window.minsize(650, 480)
        guide_window.transient(self.root)

        frame = ttk.Frame(guide_window, padding=12)
        frame.pack(fill="both", expand=True)

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)

        text_widget = tk.Text(
            text_frame,
            wrap="word",
            font=("Segoe UI", 10),
            padx=12,
            pady=12,
        )
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text_widget.insert("1.0", USER_GUIDE_TEXT)
        text_widget.configure(state="disabled")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(10, 0))

        ttk.Button(
            buttons,
            text="Open Program Folder",
            command=lambda: self._safe_open_path(self.app_dir, "program folder"),
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Open Logs Folder",
            command=lambda: self._safe_open_path(self.logs_dir, "logs folder"),
        ).pack(side="left", padx=(8, 0))

        ttk.Button(buttons, text="Close", command=guide_window.destroy).pack(side="right")
        guide_window.grab_set()
        guide_window.focus_set()

    def _on_close(self) -> None:
        self._write_log("Launcher closed.")
        self.root.destroy()


def show_fatal_error(exc: BaseException) -> None:
    """Display and log an initialization error."""
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    try:
        log_dir = local_app_data_directory() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fatal_log = log_dir / "launcher_fatal_error.log"
        fatal_log.write_text(details, encoding="utf-8")
        log_note = f"\n\nDetails were saved to:\n{fatal_log}"
    except Exception:
        log_note = ""

    try:
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror(
            "Probolism Suite Startup Error",
            f"The launcher could not be started.\n\n{exc}{log_note}",
            parent=error_root,
        )
        error_root.destroy()
    except Exception:
        print(details, file=sys.stderr)


def main() -> int:
    try:
        root = tk.Tk()
        ProbolismsLauncher(root)
        root.mainloop()
        return 0
    except Exception as exc:
        show_fatal_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
