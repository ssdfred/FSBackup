"""Read-only discovery of available filesystem roots."""

from __future__ import annotations

import os
import string
from pathlib import Path

from .schemas import AvailableDrive, AvailableDrivesReport


def list_available_drives() -> AvailableDrivesReport:
    """Return mounted Windows drive roots without modifying them."""

    drives: list[AvailableDrive] = []
    if os.name == "nt":
        candidates = (Path(f"{letter}:\\") for letter in string.ascii_uppercase)
    else:
        candidates = (Path("/"),)

    for root in candidates:
        try:
            if not root.exists() or not root.is_dir():
                continue
        except OSError:
            continue

        drives.append(
            AvailableDrive(
                root=str(root),
                label=root.drive or str(root),
                system=os.environ.get("SystemDrive", "").casefold()
                == root.drive.casefold(),
            )
        )

    return AvailableDrivesReport(drives=drives)
