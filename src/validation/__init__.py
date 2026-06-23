"""DRAM Benchmarking Platform — model validation lane."""

from validation.golden import GoldenSpec, load_all_golden_specs, load_golden_spec

__all__ = ["GoldenSpec", "load_golden_spec", "load_all_golden_specs"]
__version__ = "0.1.0"
