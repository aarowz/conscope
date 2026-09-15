#!/usr/bin/env python3
"""
ConScope pipeline launcher — runs all components in one terminal.

Usage:
  python scripts/run_all.py              # All five: storage, processor, alerts, producer, dashboard
  python scripts/run_all.py --no-dashboard   # Four backend only; run Streamlit in a separate terminal

Press Ctrl+C to stop all components.

Cross-platform: Windows and Mac/Linux.
"""

import argparse
import os
import sys
import signal
import threading
import subprocess
import time

# Project root (parent of scripts/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def get_commands(include_dashboard=True):
    """Return list of (name, cmd_list) for each component. Uses current Python (venv)."""
    python = sys.executable
    commands = [
        ("storage", [python, "-m", "consumers.storage_consumer"]),
        ("processor", [python, "-m", "processors.price_processor"]),
        ("alerts", [python, "-m", "consumers.alert_consumer"]),
        ("producer", [python, "-m", "producers.mock_producer"]),
    ]
    if include_dashboard:
        commands.append(
            ("dashboard", [python, "-m", "streamlit", "run", "dashboard/app.py", "--server.headless", "true"])
        )
    return commands


def stream_output(proc, name):
    """Read proc.stdout line by line and print with [name] prefix."""
    try:
        for line in iter(proc.stdout.readline, ""):
            if line:
                print(f"[{name}] {line}", end="")
    except (BrokenPipeError, ValueError):
        pass
    finally:
        if proc.stdout:
            try:
                proc.stdout.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Run ConScope pipeline components. Use --no-dashboard to run backend only and start Streamlit in a separate terminal."
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Start only storage, processor, alerts, producer; run 'streamlit run dashboard/app.py' in another terminal for the dashboard.",
    )
    args = parser.parse_args()
    include_dashboard = not args.no_dashboard

    os.chdir(PROJECT_ROOT)

    commands = get_commands(include_dashboard=include_dashboard)
    processes = []
    threads = []

    def shutdown(signum=None, frame=None):
        print("\nShutting down all components...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        time.sleep(2)
        for p in processes:
            if p.poll() is None:
                p.kill()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    n = len(commands)
    print(f"ConScope pipeline — starting {n} component(s). Press Ctrl+C to stop.\n")
    if include_dashboard:
        print("Dashboard will be at http://localhost:8501\n")
    else:
        print("Dashboard not started. Run in another terminal: streamlit run dashboard/app.py\n")

    for name, cmd in commands:
        try:
            p = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            processes.append(p)
            t = threading.Thread(target=stream_output, args=(p, name), daemon=True)
            t.start()
            threads.append(t)
        except Exception as e:
            print(f"[run_all] Failed to start {name}: {e}", file=sys.stderr)
            shutdown()
            sys.exit(1)

    try:
        while True:
            if any(p.poll() is not None for p in processes):
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()

    for p in processes:
        p.wait(timeout=5)

    print("All components stopped.")


if __name__ == "__main__":
    main()
