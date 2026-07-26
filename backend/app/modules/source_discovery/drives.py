"""Read-only discovery of available filesystem roots."""

from __future__ import annotations

import os
import shutil
import string
from pathlib import Path

from .schemas import AvailableDrive, AvailableDrivesReport


def list_available_drives() -> AvailableDrivesReport:
    """Return mounted drive roots and their capacity without modifying them."""

    drives: list[AvailableDrive] = []
    if os.name == "nt":
        candidates = (Path(f"{letter}:\\") for letter in string.ascii_uppercase)
    else:
        candidates = (Path("/"),)

    for root in candidates:
        try:
            if not root.exists() or not root.is_dir():
                continue
            usage = shutil.disk_usage(root)
        except OSError:
            continue

        drives.append(
            AvailableDrive(
                root=str(root),
                label=root.drive or str(root),
                system=os.environ.get("SystemDrive", "").casefold()
                == root.drive.casefold(),
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
            )
        )

    return AvailableDrivesReport(drives=drives)
