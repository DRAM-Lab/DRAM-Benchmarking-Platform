"""Offline tests for OpenDRAMBench platform helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from dram_benchmark.manifest import build_manifest
from dram_benchmark.paths import (
    PROJECT_ROOT,
    STANDARD_ACCESS_MODEL_IDS,
    list_access_model_ids,
    resolve_model_root,
)
from dram_benchmark.validation import validate_device_metrics_csv, validate_model_provenance


@pytest.fixture
def sample_metrics_csv(tmp_path: Path) -> Path:
    rows = []
    for model_id in STANDARD_ACCESS_MODEL_IDS:
        rows.append(
            {
                "model_id": model_id,
                "architecture": "VCT",
                "corner": "tt",
                "temp_c": 27.0,
                "vdd": 0.9,
                "ion_a": 1e-6,
                "ioff_a": 1e-14,
                "ron_ohm": 1e5,
                "cgg_f": 1e-17,
                "fpitch_m": 6e-8,
                "vsat": 25000.0,
            }
        )
    path = tmp_path / "device_metrics.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_model_root_has_seven_cards() -> None:
    root = resolve_model_root()
    assert root.is_dir()
    assert len(list_access_model_ids()) == 7


def test_validate_model_provenance_passes() -> None:
    result = validate_model_provenance()
    assert result.passed
    assert any(row["check"] == "model_inventory" and row["status"] == "PASS" for row in result.checks)


def test_validate_device_metrics_csv(sample_metrics_csv: Path) -> None:
    result = validate_device_metrics_csv(sample_metrics_csv)
    assert result.passed


def test_manifest_lists_model_cards(tmp_path: Path, sample_metrics_csv: Path) -> None:
    sample_metrics_csv.rename(tmp_path / "device_metrics.csv")
    manifest = build_manifest(tmp_path, suite="device", corner="tt")
    assert manifest["suite"] == "device"
    assert len(manifest["model_cards"]) == 7
    assert manifest["model_bundle_revision"]


def test_list_models_cli() -> None:
    from dram_benchmark.cli import main

    assert main(["list-models"]) == 0
