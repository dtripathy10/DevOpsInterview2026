"""Graceful shutdown demo: hook SIGTERM / SIGINT, and show that SIGKILL can't be hooked.

Run:      python graceful_shutdown.py
Then from another terminal (Linux/macOS/WSL/Docker):
          kill -TERM <pid>     -> handler runs, clean exit
          kill -KILL <pid>     -> process dies instantly, no handler, no cleanup
"""
import os
import signal
import sys
import time

shutting_down = False


def cleanup():
    """Put your real shutdown work here: close DB connections, flush logs, etc."""
    print("  cleaning up: flushing buffers, closing connections...", flush=True)
    time.sleep(0.5)
    print("  cleanup done", flush=True)


def handle_signal(signum, frame):
    global shutting_down
    name = signal.Signals(signum).name
    if shutting_down:
        print(f"Received {name} again, already shutting down", flush=True)
        return
    shutting_down = True
    print(f"Received {name}: starting graceful shutdown", flush=True)
    # Keep handlers short: just set a flag and let the main loop exit cleanly.


def main():
    # SIGTERM: what `docker stop`, `kill <pid>` and Kubernetes send first.
    # SIGINT:  Ctrl+C.
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # SIGKILL (and SIGSTOP) can never be caught. The OS rejects the attempt.
    sigkill = getattr(signal, "SIGKILL", None)  # SIGKILL doesn't exist on Windows
    if sigkill is None:
        print("SIGKILL does not exist on this platform (Windows).", flush=True)
    else:
        try:
            signal.signal(sigkill, handle_signal)
        except OSError as exc:
            print(f"Cannot hook SIGKILL (expected): {exc}", flush=True)

    print(f"Running with PID {os.getpid()}. Send SIGTERM or press Ctrl+C.", flush=True)

    tick = 0
    while not shutting_down:
        tick += 1
        print(f"working... {tick}", flush=True)
        time.sleep(1)

    cleanup()
    print("Bye.", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()