from __future__ import annotations

import os
import threading
import webbrowser

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def application_url(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    return f"http://{host}:{port}/app/"


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
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    run()
