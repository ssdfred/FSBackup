from __future__ import annotations

import os
import threading
import traceback
import webbrowser
from pathlib import Path

import uvicorn

from app.main import app

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def application_url(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    return f"http://{host}:{port}/app/"


def log_file_path() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    base_directory = Path(local_app_data) if local_app_data else Path.home()
    return base_directory / "FSBackup" / "fsbackup.log"


def write_startup_error(error: BaseException) -> Path:
    path = log_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "FSBackup n’a pas pu démarrer.\n\n"
        + "".join(traceback.format_exception(error)),
        encoding="utf-8",
    )
    return path


def show_startup_error(log_path: Path) -> None:
    try:
        import tkinter.messagebox

        tkinter.messagebox.showerror(
            "FSBackup",
            "FSBackup n’a pas pu démarrer.\n\n"
            f"Le détail de l’erreur a été enregistré dans :\n{log_path}",
        )
    except Exception:
        return


def open_application(url: str) -> None:
    webbrowser.open(url, new=1, autoraise=True)


def schedule_browser_open(url: str, delay_seconds: float = 1.2) -> threading.Timer:
    timer = threading.Timer(delay_seconds, open_application, args=(url,))
    timer.daemon = True
    timer.start()
    return timer


def run() -> None:
    host = os.getenv("FSBACKUP_HOST", DEFAULT_HOST)
    port = int(os.getenv("FSBACKUP_PORT", str(DEFAULT_PORT)))
    url = application_url(host, port)
    schedule_browser_open(url)
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        access_log=False,
        log_config=None,
    )


def main() -> None:
    try:
        run()
    except BaseException as error:
        log_path = write_startup_error(error)
        show_startup_error(log_path)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
