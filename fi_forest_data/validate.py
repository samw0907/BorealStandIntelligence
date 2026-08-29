# boreal-stand-intelligence/fi_forest_data/validate.py
"""Configuration validation.

Checks config/pipeline.yaml (and the AOI file it points at) for missing or
out-of-range parameters, so a typo fails fast rather than defaulting silently.
Importable, and runnable as `python -m fi_forest_data.validate config/pipeline.yaml`
(which is what CI does). Returns / prints a list of problems; empty means valid.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from fi_forest_data.aoi import AOI

_S2_INDICES = {"ndvi", "evi", "nbr", "ndre", "ndmi", "nbr2"}
_CHANGE_METRICS = {"dnbr", "dndmi", "s1_logratio", "combined"}
_FELLING_TYPES = {"regeneration", "thinning", "salvage"}


def _num(problems: list[str], d: dict, key: str, lo=None, hi=None, ctx: str = "") -> None:
    if key not in d:
        problems.append(f"{ctx}: missing '{key}'")
        return
    v = d[key]
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        problems.append(f"{ctx}.{key}: expected a number, got {v!r}")
        return
    if lo is not None and v < lo:
        problems.append(f"{ctx}.{key}: {v} below minimum {lo}")
    if hi is not None and v > hi:
        problems.append(f"{ctx}.{key}: {v} above maximum {hi}")


def _in(problems: list[str], d: dict, key: str, allowed: set, ctx: str = "") -> None:
    if key not in d:
        problems.append(f"{ctx}: missing '{key}'")
    elif d[key] not in allowed:
        problems.append(f"{ctx}.{key}: {d[key]!r} not in {sorted(allowed)}")


def _window(problems: list[str], w, ctx: str) -> None:
    if not isinstance(w, dict) or "start" not in w or "end" not in w:
        problems.append(f"{ctx}: expected keys 'start' and 'end'")
        return
    if str(w["start"]) >= str(w["end"]):
        problems.append(f"{ctx}: start {w['start']} is not before end {w['end']}")


def validate_pipeline_config(cfg: dict, base_dir: Path | None = None) -> list[str]:
    """Return a list of problem strings for a loaded pipeline config. Empty = valid."""
    problems: list[str] = []
    base_dir = base_dir or Path(".")

    # --- AOI ---
    aoi_ref = cfg.get("aoi")
    if not aoi_ref:
        problems.append("top level: missing 'aoi'")
    else:
        aoi_path = (base_dir / aoi_ref).resolve()
        if not aoi_path.exists():
            problems.append(f"aoi: file not found: {aoi_path}")
        else:
            try:
                AOI.from_yaml(aoi_path)
            except ValueError as exc:
                problems.append(f"aoi: {exc}")

    # --- sentinel2 ---
    s2 = cfg.get("sentinel2")
    if not isinstance(s2, dict):
        problems.append("top level: missing 'sentinel2' block")
    else:
        _in(problems, s2, "source", {"cdse", "gee"}, "sentinel2")
        cw = s2.get("composite_windows", {})
        _window(problems, cw.get("pre"), "sentinel2.composite_windows.pre")
        _window(problems, cw.get("post"), "sentinel2.composite_windows.post")
        _num(problems, s2, "max_cloud_scene_pct", 0, 100, "sentinel2")
        _num(problems, s2, "min_scenes_per_composite", 1, None, "sentinel2")
        idx = s2.get("indices")
        if not isinstance(idx, list) or not idx:
            problems.append("sentinel2.indices: expected a non-empty list")
        elif not set(idx) <= _S2_INDICES:
            problems.append(f"sentinel2.indices: unknown {sorted(set(idx) - _S2_INDICES)}")
        scl = s2.get("scl_exclude")
        if not isinstance(scl, list) or not all(isinstance(x, int) for x in scl):
            problems.append("sentinel2.scl_exclude: expected a list of integers")

    # --- sentinel1 ---
    s1 = cfg.get("sentinel1")
    if not isinstance(s1, dict):
        problems.append("top level: missing 'sentinel1' block")
    else:
        if not isinstance(s1.get("enabled"), bool):
            problems.append("sentinel1.enabled: expected true/false")
        _in(problems, s1, "orbit", {"ascending", "descending"}, "sentinel1")
        pol = s1.get("polarisations")
        if not isinstance(pol, list) or not set(pol) <= {"VV", "VH", "HH", "HV"}:
            problems.append("sentinel1.polarisations: expected a subset of [VV, VH, HH, HV]")

    # --- module B ---
    b = cfg.get("module_b_harvest_detection")
    if not isinstance(b, dict):
        problems.append("top level: missing 'module_b_harvest_detection' block")
    else:
        _in(problems, b, "change_metric", _CHANGE_METRICS, "module_b_harvest_detection")
        sw = b.get("threshold_sweep", {})
        if not isinstance(sw, dict) or {"min", "max", "step"} - sw.keys():
            problems.append("module_b_harvest_detection.threshold_sweep: need min, max, step")
        else:
            if sw["min"] >= sw["max"]:
                problems.append("module_b_harvest_detection.threshold_sweep: min >= max")
            if sw["step"] <= 0:
                problems.append("module_b_harvest_detection.threshold_sweep: step must be > 0")
        _num(problems, b, "min_stand_area_ha", 0, None, "module_b_harvest_detection")
        ft = b.get("felling_types_scored", [])
        if not isinstance(ft, list) or not set(ft) <= _FELLING_TYPES:
            problems.append(
                f"module_b_harvest_detection.felling_types_scored: subset of {sorted(_FELLING_TYPES)}"
            )

    # --- modules A and C: presence only for now, detailed checks when built ---
    for key in ("module_a_stand_estimation", "module_c_beetle"):
        if not isinstance(cfg.get(key), dict):
            problems.append(f"top level: missing '{key}' block")

    return problems


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m fi_forest_data.validate <pipeline.yaml>")
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(f"config not found: {path}")
        return 2
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems = validate_pipeline_config(cfg, base_dir=path.parent)
    if problems:
        print(f"{path}: {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"{path}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
