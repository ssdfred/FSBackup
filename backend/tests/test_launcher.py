from app import launcher


def test_application_url_uses_local_defaults() -> None:
    assert launcher.application_url() == "http://127.0.0.1:8765/app/"


def test_application_url_accepts_custom_address() -> None:
    assert launcher.application_url("0.0.0.0", 9000) == "http://127.0.0.1:9000/app/"


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


def test_instance_is_running_when_connection_succeeds(monkeypatch) -> None:
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        launcher.socket,
        "create_connection",
        lambda address, timeout: FakeConnection(),
    )

    assert launcher.instance_is_running("127.0.0.1", 8765) is True


def test_instance_is_not_running_when_connection_fails(monkeypatch) -> None:
    def fail_connection(address, timeout):
        raise OSError("port fermé")

    monkeypatch.setattr(launcher.socket, "create_connection", fail_connection)

    assert launcher.instance_is_running("127.0.0.1", 8765) is False


def test_run_opens_existing_instance_without_starting_uvicorn(monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(launcher, "instance_is_running", lambda host, port: True)
    monkeypatch.setattr(launcher, "open_application", opened.append)
    monkeypatch.setattr(
        launcher.uvicorn,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("uvicorn appelé")),
    )

    launcher.run()

    assert opened == ["http://127.0.0.1:8765/app/"]
