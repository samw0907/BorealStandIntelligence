# boreal-stand-intelligence/tests/test_validate.py
"""Tests for fi_forest_data.validate."""

import copy
from pathlib import Path

import yaml

from fi_forest_data.validate import validate_pipeline_config

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
PIPELINE = CONFIG_DIR / "pipeline.yaml"


def _load():
    return yaml.safe_load(PIPELINE.read_text(encoding="utf-8"))


def test_real_pipeline_config_is_valid():
    cfg = _load()
    problems = validate_pipeline_config(cfg, base_dir=CONFIG_DIR)
    assert problems == [], problems


def test_missing_block_is_reported():
    cfg = _load()
    del cfg["sentinel2"]
    problems = validate_pipeline_config(cfg, base_dir=CONFIG_DIR)
    assert any("sentinel2" in p for p in problems)


def test_out_of_range_cloud_pct_is_reported():
    cfg = _load()
    cfg["sentinel2"]["max_cloud_scene_pct"] = 150
    problems = validate_pipeline_config(cfg, base_dir=CONFIG_DIR)
    assert any("max_cloud_scene_pct" in p for p in problems)


def test_bad_change_metric_is_reported():
    cfg = _load()
    cfg["module_b_harvest_detection"]["change_metric"] = "magic"
    problems = validate_pipeline_config(cfg, base_dir=CONFIG_DIR)
    assert any("change_metric" in p for p in problems)


def test_reversed_threshold_sweep_is_reported():
    cfg = copy.deepcopy(_load())
    cfg["module_b_harvest_detection"]["threshold_sweep"] = {"min": 0.6, "max": 0.1, "step": 0.01}
    problems = validate_pipeline_config(cfg, base_dir=CONFIG_DIR)
    assert any("threshold_sweep" in p for p in problems)


def test_missing_aoi_file_is_reported():
    cfg = _load()
    cfg["aoi"] = "config/does_not_exist.yaml"
    problems = validate_pipeline_config(cfg, base_dir=CONFIG_DIR)
    assert any("aoi" in p and "not found" in p for p in problems)
