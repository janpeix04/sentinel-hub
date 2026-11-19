import os
from pathlib import Path

import pytest

from sentinel_hub import SHConfig, SHSession
from sentinel_hub.config import (
    SH_CLIENT_ID_ENV_VAR,
    SH_CLIENT_SECRET_ENV_VAR,
    SH_PROFILE_ENV_VAR,
)
from tests.testing_utils import get_input_folder

INPUT_FOLDER = get_input_folder(__file__)

def _load_real_credentials() -> tuple[str, str]:
    """Reads credentials from env vars, falling back to the user's config.toml."""
    env_client_id = os.environ.get(SH_CLIENT_ID_ENV_VAR, "")
    env_client_secret = os.environ.get(SH_CLIENT_SECRET_ENV_VAR, "")
    # SHConfig.load() would create a default config.toml if it does not exist
    if not os.path.exists(SHConfig.get_config_location()):
        return env_client_id, env_client_secret
    try:
        config = SHConfig()  # precedence: env > config.toml
    except KeyError:
        return env_client_id, env_client_secret
    return config.sh_client_id, config.sh_client_secret


REAL_CLIENT_ID, REAL_CLIENT_SECRET = _load_real_credentials()


def _is_live(request: pytest.FixtureRequest) -> bool:
    return request.node.get_closest_marker("sh_integration") is not None


@pytest.fixture(autouse=True)
def isolated_config(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(SH_PROFILE_ENV_VAR, raising=False)
    if _is_live(request):
        monkeypatch.setenv(SH_CLIENT_ID_ENV_VAR, REAL_CLIENT_ID)
        monkeypatch.setenv(SH_CLIENT_SECRET_ENV_VAR, REAL_CLIENT_SECRET)
    else:
        monkeypatch.delenv(SH_CLIENT_ID_ENV_VAR, raising=False)
        monkeypatch.delenv(SH_CLIENT_SECRET_ENV_VAR, raising=False)
    config_path = tmp_path / "sentinelhub" / "config.toml"
    monkeypatch.setattr(
        SHConfig, "get_config_location", staticmethod(lambda: str(config_path))
    )


@pytest.fixture(name="input_folder", scope="session")
def input_folder_fixture() -> str:
    return INPUT_FOLDER


@pytest.fixture(name="session", scope="session")
def session_fixture() -> SHSession:
    return SHSession(
        SHConfig(
            use_defaults=True,
            sh_client_id=REAL_CLIENT_ID,
            sh_client_secret=REAL_CLIENT_SECRET,
        )
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if REAL_CLIENT_ID and REAL_CLIENT_SECRET:
        return
    skip = pytest.mark.skip(
        reason="Needs SH_CLIENT_ID and SH_CLIENT_SECRET (env or config.toml) for the live service"
    )
    for item in items:
        if "sh_integration" in item.keywords:
            item.add_marker(skip)
