from app import launcher


def test_application_url_uses_local_defaults() -> None:
    assert launcher.application_url() == "http://127.0.0.1:8765/app/"


def test_application_url_accepts_custom_address() -> None:
    assert launcher.application_url("0.0.0.0", 9000) == "http://0.0.0.0:9000/app/"


def test_schedule_browser_open_starts_daemon_timer(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeTimer:
        def __init__(self, delay, callback, args):
            captured["delay"] = delay
            captured["callback"] = callback
            captured["args"] = args
            self.daemon = False

        def start(self) -> None:
            captured["started"] = True

    monkeypatch.setattr(launcher.threading, "Timer", FakeTimer)

    timer = launcher.schedule_browser_open("http://localhost/app/", 0.5)

    assert captured == {
        "delay": 0.5,
        "callback": launcher.open_application,
        "args": ("http://localhost/app/",),
        "started": True,
    }
    assert timer.daemon is True
