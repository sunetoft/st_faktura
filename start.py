#!/usr/bin/env python
"""
Interactive launcher for ST_Faktura utilities.

Allows user to select and run one of the core scripts, then returns to menu
upon completion. Designed for use inside the project's virtual environment.

Menu Items:
  1. CreateTask.py
  2. CreateInvoice.py
  3. CreateCustomer.py
  4. Tool_SearchOldInvoices.py
  5. Tool_MyCompanyDetails.py
  q. Quit

Features:
  - Detects if running under virtual environment; warns otherwise
  - Clears screen (where possible) between runs for clarity
  - Catches KeyboardInterrupt to return to menu instead of exiting abruptly
  - Pass-through of additional arguments if user enters them after the choice, e.g. "2 --preview"

Usage:
  python start.py
"""
from __future__ import annotations

import os
import sys
import subprocess
import shlex
from typing import Dict, Tuple

SCRIPTS: Dict[str, Tuple[str, str]] = {
    '1': ('CreateTask.py', 'Create a new task'),
    '2': ('CreateInvoice.py', 'Create and send an invoice'),
    '3': ('CreateCustomer.py', 'Create a new customer'),
    '4': ('Tool_SearchOldInvoices.py', 'Search existing invoice PDFs'),
    '5': ('Tool_MyCompanyDetails.py', 'Edit company details'),
}


def _is_venv_active() -> bool:
    return (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
        os.environ.get('VIRTUAL_ENV') is not None
    )


def _clear_screen() -> None:
    try:
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        pass


def _print_header():
    print("\nST_FAKTURA LAUNCHER")
    print("=" * 60)
    if not _is_venv_active():
        print("⚠️  Warning: It looks like you're NOT using the project virtual environment.")
        print("    Activate it for consistent dependencies: .venv\\Scripts\\Activate.ps1 (Windows PowerShell)")
    print()
    for key, (fname, desc) in SCRIPTS.items():
        print(f" {key}. {fname:<25} - {desc}")
    print(" q. Quit")
    print("=" * 60)


def _resolve_python() -> str:
    # Always use current interpreter to avoid cross-env issues
    return sys.executable


def main():
    while True:
        _print_header()
        try:
            raw = input("Select an option (e.g., 2 or '2 --preview') or 'q' to quit: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting launcher.")
            break

        if not raw:
            continue
        if raw.lower() in ('q', 'quit', 'exit'):  # exit options
            print("Goodbye.")
            break

        parts = shlex.split(raw)
        choice = parts[0]
        extra_args = parts[1:]

        if choice not in SCRIPTS:
            print(f"Unknown option: {choice}")
            continue

        script_name, _ = SCRIPTS[choice]
        script_path = os.path.join(os.getcwd(), script_name)
        if not os.path.exists(script_path):
            print(f"❌ Script not found: {script_name}")
            continue

        py = _resolve_python()
        cmd = [py, script_path] + extra_args
        print(f"\n--- Running: {' '.join(shlex.quote(c) for c in cmd)} ---\n")
        try:
            subprocess.run(cmd, check=False)
        except KeyboardInterrupt:
            print("\n(Returned to launcher)\n")
        except Exception as e:
            print(f"❌ Error executing {script_name}: {e}")
        input("\nPress Enter to return to menu...")
        _clear_screen()


if __name__ == "__main__":
    main()
