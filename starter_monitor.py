#!/usr/bin/env python3
"""Live dashboard for the podcast voice generator starter.

Shows service URLs, health status, and per-process logs in a curses UI.
 Falls back to a simple clearing console if curses is unavailable.
"""

import json
import os
import shutil
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"

SERVICES: List[Dict] = [
    {"name": "API", "url": "http://127.0.0.1:{port}/api/health", "port_env": "API_PORT", "default": "8000", "log": "api.log"},
    {"name": "Worker", "url": "http://127.0.0.1:{port}/health", "port_env": "WORKER_PORT", "default": "8001", "log": "worker.log"},
    {"name": "Web", "url": "http://127.0.0.1:{port}", "port_env": "WEB_PORT", "default": "5173", "log": "web.log"},
]


def _get_port(service: Dict) -> int:
    raw = os.getenv(service["port_env"], service["default"])
    try:
        return int(raw)
    except (ValueError, TypeError):
        return int(service["default"])


def _check_health(url: str) -> Tuple[str, str]:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return "OK", body[:60]
    except Exception as e:
        return "DOWN", str(e)


def _tail_lines(path: Path, n: int) -> List[str]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-n:]]
    except Exception:
        return []


def _count_errors(lines: List[str]) -> int:
    return sum(1 for line in lines if any(token in line.lower() for token in ["error", "traceback", "exception", "critical", "failed"]))


def _draw_dashboard(stdscr):
    import curses

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)

    stdscr.nodelay(True)
    curses.curs_set(0)

    last_lines: Dict[str, List[str]] = {s["name"]: [] for s in SERVICES}

    while True:
        try:
            key = stdscr.getch()
            if key in (ord("q"), ord("Q"), 27):
                break
        except curses.error:
            pass

        height, width = stdscr.getmaxyx()
        stdscr.clear()

        header_height = 3 + len(SERVICES)
        panel_height = max(3, (height - header_height - 1) // len(SERVICES))

        row = 0
        stdscr.addstr(row, 0, " Podcast Voice Generator - Process Monitor ".center(width, "="), curses.A_BOLD)
        row += 2

        for service in SERVICES:
            port = _get_port(service)
            url = service["url"].format(port=port)
            status, detail = _check_health(url)
            log_path = LOG_DIR / service["log"]
            lines = _tail_lines(log_path, 500)
            errors = _count_errors(lines)
            recent = _tail_lines(log_path, panel_height - 1)
            last_lines[service["name"]] = recent

            status_color = 1 if status == "OK" else 2
            error_color = 3 if errors > 0 else 1

            left = f" {service['name']:6} | {url:<45} | Status: "
            stdscr.addstr(row, 0, left)
            stdscr.addstr(row, len(left), status, curses.color_pair(status_color) | curses.A_BOLD)
            right = f" | Errors: {errors} | {detail[:30]}"
            stdscr.addstr(row, len(left) + len(status), right)
            row += 1

            panel_top = row
            panel_bottom = min(panel_top + panel_height, height - 1)

            for i, line in enumerate(recent):
                y = panel_top + i
                if y >= panel_bottom:
                    break
                truncated = line[: width - 2]
                color = 0
                lower = line.lower()
                if any(token in lower for token in ["error", "traceback", "exception", "critical", "failed"]):
                    color = curses.color_pair(2)
                elif any(token in lower for token in ["warning", "warn"]):
                    color = curses.color_pair(3)
                try:
                    stdscr.addstr(y, 1, truncated, color)
                except curses.error:
                    pass

            row = panel_bottom
            if row < height - 1:
                try:
                    stdscr.hline(row, 0, curses.ACS_HLINE, width)
                except curses.error:
                    pass
                row += 1

        footer = " Press 'q' to quit monitor (services keep running) "
        try:
            stdscr.addstr(height - 1, 0, footer[:width], curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()
        time.sleep(1)


def _fallback_dashboard():
    """Simple console fallback when curses is not usable."""
    while True:
        try:
            os.system("clear" if os.name != "nt" else "cls")
        except Exception:
            pass

        print("=" * 80)
        print(" Podcast Voice Generator - Process Monitor ".center(80))
        print("=" * 80)
        for service in SERVICES:
            port = _get_port(service)
            url = service["url"].format(port=port)
            status, detail = _check_health(url)
            log_path = LOG_DIR / service["log"]
            lines = _tail_lines(log_path, 500)
            errors = _count_errors(lines)
            print(f"\n[{service['name']}] {url} | Status: {status} | Errors: {errors}")
            print(f"  Detail: {detail[:60]}")
            print("-" * 80)
            for line in _tail_lines(log_path, 10):
                print(f"  {line}")
        print("\nPress Ctrl+C to quit monitor (services keep running)")
        time.sleep(2)


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not sys.stdout.isatty():
        print("Not running in a TTY; falling back to console output.")
        try:
            _fallback_dashboard()
        except KeyboardInterrupt:
            pass
        return

    try:
        import curses

        curses.wrapper(_draw_dashboard)
    except Exception as e:
        print(f"Curses dashboard failed ({e}), falling back to console output.")
        try:
            _fallback_dashboard()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
