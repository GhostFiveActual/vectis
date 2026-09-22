# GHOST FIVE // VECTIS
# Opens local VECTIS application URLs across desktop Python environments and WSL.

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import webbrowser


def _is_wsl() -> bool:
    """Return whether VECTIS is running inside Windows Subsystem for Linux."""
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    return "microsoft" in platform.release().lower()


def open_local_url(url: str) -> bool:
    """Open a local application URL without leaking browser-launch failures."""
    if _is_wsl():
        command = shutil.which("cmd.exe")
        if command:
            try:
                subprocess.Popen(
                    [command, "/c", "start", "", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except OSError:
                pass

    try:
        return bool(webbrowser.open(url))
    except OSError:
        return False
