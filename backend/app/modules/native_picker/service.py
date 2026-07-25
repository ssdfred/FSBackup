from __future__ import annotations

import os
from pathlib import Path

from .schemas import NativePickerReport


class NativePickerService:
    @staticmethod
    def pick_directory(initial_path: str | None = None) -> NativePickerReport:
        return NativePickerService._pick(kind="directory", initial_path=initial_path)

    @staticmethod
    def pick_archive(initial_path: str | None = None) -> NativePickerReport:
        return NativePickerService._pick(kind="archive", initial_path=initial_path)

    @staticmethod
    def _pick(*, kind: str, initial_path: str | None) -> NativePickerReport:
        if os.name != "nt":
            return NativePickerReport(
                selected=False,
                error="Le sélecteur natif est disponible uniquement sous Windows.",
            )

        try:
            import tkinter as tk
            from tkinter import filedialog
        except ImportError as exc:
            return NativePickerReport(
                selected=False,
                error=f"Le sélecteur Windows est indisponible : {exc}",
            )

        root = None
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            initial_directory = NativePickerService._initial_directory(initial_path)

            if kind == "archive":
                selected_path = filedialog.askopenfilename(
                    parent=root,
                    title="Choisir une archive FSBackup",
                    initialdir=initial_directory,
                    filetypes=(
                        ("Archives FSBackup", "*.fsb *.fsbe"),
                        ("Tous les fichiers", "*.*"),
                    ),
                )
            else:
                selected_path = filedialog.askdirectory(
                    parent=root,
                    title="Choisir un dossier",
                    initialdir=initial_directory,
                    mustexist=True,
                )

            if not selected_path:
                return NativePickerReport(selected=False)

            return NativePickerReport(selected=True, path=str(Path(selected_path)))
        except (OSError, RuntimeError, tk.TclError) as exc:
            return NativePickerReport(
                selected=False,
                error=f"Impossible d'ouvrir l'explorateur Windows : {exc}",
            )
        finally:
            if root is not None:
                root.destroy()

    @staticmethod
    def _initial_directory(initial_path: str | None) -> str | None:
        if not initial_path:
            return None

        candidate = Path(initial_path).expanduser()
        if candidate.is_file():
            candidate = candidate.parent
        if candidate.is_dir():
            return str(candidate)
        if candidate.parent.is_dir():
            return str(candidate.parent)
        return None
