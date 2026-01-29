#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Startup Script

This script starts the ROM Sorter Pro application.
It checks the environment and starts the appropriate UI.
"""

import os
import sys
import logging
import argparse
import platform
import json

from src.version import load_version
import csv

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

def _configure_startup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler('logs/rom_sorter_startup.log', mode='a')],
    )
    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


def _load_version() -> str:
    return str(load_version())

def gui_smoke(backend: str | None = None) -> str:
    """Validate GUI backend selection without launching the GUI."""
    from src.ui.compat import select_backend

    selected = select_backend(backend)
    if selected == "qt":
        try:
            import PySide6  # noqa: F401
        except Exception:
            try:
                import PyQt5  # noqa: F401
            except Exception as exc:
                raise RuntimeError("Qt binding not available") from exc

        from src.ui.mvp import qt_app  # noqa: F401

        if not hasattr(qt_app, "run"):
            raise RuntimeError("Qt app entry not found")
    elif selected == "tk":
        try:
            import tkinter  # noqa: F401
        except Exception as exc:
            raise RuntimeError("Tk backend not available") from exc

        from src.ui.mvp import tk_app  # noqa: F401

        if not hasattr(tk_app, "run"):
            raise RuntimeError("Tk app entry not found")
    else:
        raise RuntimeError(f"Unsupported GUI backend: {selected}")
    return selected

def check_environment():
    """Checks the runtime environment."""
    # Check Python version
    py_version = platform.python_version_tuple()
    if int(py_version[0]) < 3 or (int(py_version[0]) == 3 and int(py_version[1]) < 8):
        print(f"WARNING: Python {platform.python_version()} detected. ROM Sorter Pro requires Python 3.8 or higher.")
        logger.warning(f"Outdated Python version: {platform.python_version()}")

# Detect Operating System
    os_name = platform.system()
    logger.info(f"Operating system: {os_name} {platform.version()}")

# Check Directories
    required_dirs = ["logs", "rom_databases", "temp"]
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)

    return True

def parse_arguments():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="ROM Sorter Pro - Universal ROM Organizer")
    parser.add_argument("--gui", action="store_true", help="Start in GUI mode")
    parser.add_argument("--audit", metavar="PATH", help="Audit conversion readiness for a ROM folder")
    parser.add_argument(
        "--audit-format",
        choices=["json", "csv"],
        default="json",
        help="Export format for conversion audit (default: json)",
    )
    parser.add_argument("--audit-output", help="Output file for conversion audit report")
    parser.add_argument(
        "--audit-enabled-only",
        action="store_true",
        help="Only consider enabled conversion rules during audit",
    )
    parser.add_argument(
        "--backend",
        choices=["qt", "tk"],
        default=None,
        help="GUI backend to use (qt preferred, tk fallback).",
    )
    parser.add_argument("--qt", action="store_true", help="Force Qt GUI backend")
    parser.add_argument("--tk", action="store_true", help="Force Tk GUI backend")
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument("--gui-smoke", action="store_true", help="Validate GUI backend without launching UI")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    return parser.parse_args()

def main() -> int:
    """Main function to start the application."""
    global logger
    logger = _configure_startup_logging()
    logger.info("Starting ROM Sorter Pro...")

# Check Environment
    if not check_environment():
        sys.exit(1)

    # Parse command line arguments
    args = parse_arguments()

    if args.version:
        print(f"ROM Sorter Pro v{load_version()}")
        print("Copyright (c) 2025")
        return 0

    if args.gui_smoke:
        try:
            backend = args.backend
            if args.qt:
                backend = "qt"
            elif args.tk:
                backend = "tk"
            selected = gui_smoke(backend)
            print(f"GUI smoke ok ({selected})")
            return 0
        except Exception as e:
            logger.error("GUI smoke failed: %s", e)
            print(f"GUI smoke failed: {e}")
            return 1

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

# Try to Add the SRC Directory to the Python Path
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Handle conversion audit CLI command (optional)
    if args.audit:
        try:
            from src.app.controller import audit_conversion_candidates

            report = audit_conversion_candidates(
                args.audit,
                include_disabled=not args.audit_enabled_only,
            )

            output_path = args.audit_output
            if not output_path:
                output_path = os.path.join("cache", f"audit_report.{args.audit_format}")

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            if args.audit_format == "csv":
                with open(output_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "input_path",
                            "detected_system",
                            "current_extension",
                            "recommended_extension",
                            "rule_name",
                            "tool_key",
                            "status",
                            "reason",
                        ]
                    )
                    for item in report.items:
                        writer.writerow(
                            [
                                item.input_path,
                                item.detected_system,
                                item.current_extension,
                                item.recommended_extension,
                                item.rule_name,
                                item.tool_key,
                                item.status,
                                item.reason,
                            ]
                        )
            else:
                payload = {
                    "source_path": report.source_path,
                    "totals": report.totals,
                    "cancelled": report.cancelled,
                    "items": [
                        {
                            "input_path": item.input_path,
                            "detected_system": item.detected_system,
                            "current_extension": item.current_extension,
                            "recommended_extension": item.recommended_extension,
                            "rule_name": item.rule_name,
                            "tool_key": item.tool_key,
                            "status": item.status,
                            "reason": item.reason,
                        }
                        for item in report.items
                    ],
                }
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)

            totals = report.totals or {}
            summary = ", ".join(f"{key}: {value}" for key, value in sorted(totals.items()))
            print(f"Conversion audit complete. {summary}")
            print(f"Report saved to: {output_path}")
            return 0

        except Exception as e:
            logger.error(f"Audit failed: {e}")
            print(f"Audit failed: {e}")
            return 1

    # Start the Application in the Desired Mode
    try:
        logger.info("Starting in GUI mode...")

        backend = args.backend
        if args.qt:
            backend = "qt"
        elif args.tk:
            backend = "tk"

        # IMPORTANT: Do not import src.ui package here. It imports many optional modules.
        # Use the compat launcher which lazily loads the chosen backend.
        from src.ui.compat import launch_gui

        exit_code = launch_gui(backend=backend)
        if exit_code != 0:
            logger.error(f"GUI returned error code: {exit_code}")
            return int(exit_code)

    except ImportError as e:
        logger.error(f"Error importing modules: {e}")
        print(f"Error: {e}")
        print("Please run 'python install_dependencies.py' to install all required dependencies.")
        return 1
    except Exception as e:
        logger.error(f"Error starting the application: {e}")
        print(f"Error: {e}")
        return 1

    logger.info("ROM Sorter Pro terminated.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
