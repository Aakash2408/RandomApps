import dataclasses

import pytest

from app import config, db


def test_loopback_runs_without_secrets(settings):
    config.check_deployable(dataclasses.replace(settings, host="127.0.0.1", api_secret=""))


@pytest.mark.parametrize("field", ["api_key", "api_secret", "token_key", "phone_pepper"])
def test_public_host_refuses_missing_secret(settings, field):
    with pytest.raises(RuntimeError):
        config.check_deployable(dataclasses.replace(settings, host="0.0.0.0", **{field: ""}))


def test_public_host_requires_https_app_url(settings):
    with pytest.raises(RuntimeError):
        config.check_deployable(dataclasses.replace(settings, host="0.0.0.0", app_url="http://x.up.railway.app"))
    config.check_deployable(dataclasses.replace(settings, host="0.0.0.0"))  # https + all secrets


def test_db_init_creates_missing_directory(settings, tmp_path, monkeypatch):
    target = tmp_path / "not" / "yet" / "there" / "c.sqlite3"
    monkeypatch.setattr(config, "settings", dataclasses.replace(settings, db_path=str(target)))
    db.init()
    assert target.exists()
