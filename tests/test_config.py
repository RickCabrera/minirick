"""Tests de estado local persistido en `state.json`."""

from __future__ import annotations

from pathlib import Path

import pytest

from minirick import config


@pytest.fixture
def state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige get_config_dir a un directorio temporal."""
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path)
    return tmp_path


def test_load_state_returns_empty_dict_when_missing(state_dir: Path) -> None:
    assert not (state_dir / "state.json").exists()
    assert config.load_state() == {}


def test_save_and_load_state_roundtrip(state_dir: Path) -> None:
    payload = {
        "last_auto_launched_task_id": "abc-123",
        "counter": 7,
        "nested": {"k": "v"},
    }
    config.save_state(payload)
    assert (state_dir / "state.json").exists()
    assert config.load_state() == payload
