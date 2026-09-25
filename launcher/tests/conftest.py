import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO = Path(__file__).resolve().parents[2]
SHIPPED_CONFIG = REPO / "image/system_files/usr/share/hearth/apps.toml"


@pytest.fixture
def shipped_config():
    return SHIPPED_CONFIG
