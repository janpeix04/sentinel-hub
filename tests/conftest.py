from pathlib import Path

import pytest

from sentinel_hub import SHConfig
from sentinel_hub.config import (
    SH_CLIENT_ID_ENV_VAR,
    SH_CLIENT_SECRET_ENV_VAR,
    SH_PROFILE_ENV_VAR,
)
from tests.testing_utils import get_input_folder

INPUT_FOLDER = get_input_folder(__file__)


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SH_PROFILE_ENV_VAR, raising=False)
    monkeypatch.delenv(SH_CLIENT_ID_ENV_VAR, raising=False)
    monkeypatch.delenv(SH_CLIENT_SECRET_ENV_VAR, raising=False)
    config_path = tmp_path / "sentinelhub" / "config.toml"
    monkeypatch.setattr(
        SHConfig, "get_config_location", staticmethod(lambda: str(config_path))
    )


@pytest.fixture(name="input_folder", scope="session")
def input_folder_fixture() -> str:
    return INPUT_FOLDER
