#!/usr/bin/env python3
"""Keep the computer awake while a long render runs, then let it sleep again.

Does not change any system setting: it only holds a "don't sleep" request for as long as the
watched process (or the given command) is running. Works on macOS, Windows and Linux.

  python3 scripts/keepawake.py --pid 12345          # watch a render that is already running
  python3 scripts/keepawake.py -- python3 scripts/ambient.py build ...   # run a command awake

macOS: caffeinate.  Windows: SetThreadExecutionState.  Linux: systemd-inhibit (if present).
Closing a laptop lid still sleeps most laptops (unless an external display is connected),
and a laptop on battery may stop when the battery runs out: keep it open and plugged in.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import time

OS = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")


def alive(pid):
    if OS == "windows":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def windows_hold(on):
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_AWAYMODE_REQUIRED = 0x80000000, 0x00000001, 0x00000040
    flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED if on else 0)
    ctypes.windll.kernel32.SetThreadExecutionState(flags)


def watch_pid(pid):
    print(f"keeping the computer awake while process {pid} runs ({OS})", flush=True)
    if OS == "mac":
        subprocess.run(["caffeinate", "-ims", "-w", str(pid)])
    elif OS == "windows":
        windows_hold(True)
        try:
            while alive(pid):
                time.sleep(30)
        finally:
            windows_hold(False)
    elif shutil.which("systemd-inhibit"):
        subprocess.run(["systemd-inhibit", "--what=sleep:idle", "--why=video render", "sh", "-c",
                        f"while kill -0 {pid} 2>/dev/null; do sleep 30; done"])
    else:
        print("no sleep inhibitor found on this Linux; set the power settings by hand", file=sys.stderr)
        while alive(pid):
            time.sleep(30)
    print("render finished: the computer may sleep again", flush=True)


def run_cmd(cmd):
    print(f"running awake: {' '.join(cmd[:6])} ...", flush=True)
    if OS == "mac":
        return subprocess.run(["caffeinate", "-ims", *cmd]).returncode
    if OS == "windows":
        windows_hold(True)
        try:
            return subprocess.run(cmd).returncode
        finally:
            windows_hold(False)
    if shutil.which("systemd-inhibit"):
        return subprocess.run(["systemd-inhibit", "--what=sleep:idle", "--why=video render", *cmd]).returncode
    return subprocess.run(cmd).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, help="process to watch (e.g. a render already running)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command to run while staying awake")
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if a.pid:
        watch_pid(a.pid)
    elif cmd:
        sys.exit(run_cmd(cmd))
    else:
        ap.error("give --pid PID or -- COMMAND")


if __name__ == "__main__":
    main()
