from app.main import app
from app.version import __version__


def test_public_version_is_1_0_0() -> None:
    assert __version__ == "1.0.0"


def test_fastapi_uses_public_version() -> None:
    assert app.version == __version__
