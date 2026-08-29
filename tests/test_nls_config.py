# boreal-stand-intelligence/tests/test_nls_config.py
"""Tests for fi_forest_data.config and fi_forest_data.nls (no network)."""

import pytest

from fi_forest_data import config as cfgmod
from fi_forest_data.nls import _extract_files


def test_get_secret_reads_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("NLS_API_KEY=abc-123\n")
    cfgmod._LOADED = False
    monkeypatch.delenv("NLS_API_KEY", raising=False)
    assert cfgmod.get_secret("NLS_API_KEY", dotenv_path=env) == "abc-123"


def test_get_secret_missing_raises(tmp_path, monkeypatch):
    cfgmod._LOADED = False
    monkeypatch.delenv("NLS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="not set"):
        cfgmod.get_secret("NLS_API_KEY", dotenv_path=tmp_path / "nope.env")


def test_extract_files_parses_nls_results():
    payload = {
        "results": [
            {"path": "https://x/dl/v1/job/korkeusmalli_2m.tif", "format": "TIFF", "length": "123"},
            {"path": "https://x/dl/v1/job/M5411C1.laz", "format": "LAZ", "length": "456"},
            {"zipPath": "https://x/dl/v1/uncompressed/job"},
        ]
    }
    files = _extract_files(payload)
    assert [f["fileName"] for f in files] == ["korkeusmalli_2m.tif", "M5411C1.laz"]
    assert files[0]["length"] == 123


def test_extract_files_empty_raises():
    with pytest.raises(RuntimeError, match="no downloadable files"):
        _extract_files({"results": [{"zipPath": "https://x/z"}]})
