"""Test app that misbehaves on purpose so you can practise diagnosing it.

MODE=leak   (default) allocate ~10 MB per second until the kernel OOM-kills it (exit 137)
MODE=crash  exit with code 1 after a few seconds (app-level crash, not OOM)
MODE=ok     behave normally (healthy baseline for comparison)
"""
import os
import sys
import time

MODE = os.environ.get("MODE", "leak")
CHUNK_MB = int(os.environ.get("CHUNK_MB", "10"))
INTERVAL = float(os.environ.get("INTERVAL", "1"))

print(f"starting in MODE={MODE}", flush=True)


def rss_mb():
    # Resident memory of this process, read from /proc (Linux containers)
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) // 1024
    return -1


if MODE == "leak":
    hoard = []
    while True:
        # bytearray(b"x") * n writes real bytes, so the pages are actually committed
        hoard.append(bytearray(b"x") * (CHUNK_MB * 1024 * 1024))
        print(f"allocated {len(hoard) * CHUNK_MB} MB, rss={rss_mb()} MB", flush=True)
        time.sleep(INTERVAL)

elif MODE == "crash":
    for i in range(5, 0, -1):
        print(f"about to crash in {i}s", flush=True)
        time.sleep(1)
    print("fatal: simulated application error", file=sys.stderr, flush=True)
    sys.exit(1)

else:
    while True:
        print(f"healthy, rss={rss_mb()} MB", flush=True)
        time.sleep(5)