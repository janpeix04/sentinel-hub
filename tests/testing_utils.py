import os
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest


def get_input_folder(current_file: str) -> str:
    return os.path.join(os.path.dirname(os.path.realpath(current_file)), "TestInputs")


def get_output_folder(current_file: str) -> str:
    return os.path.join(os.path.dirname(os.path.realpath(current_file)), "TestOutputs")


def assert_statistics_match(
    data: np.ndarray,
    exp_shape: tuple[int, ...] | None = None,
    exp_dtype: None | type | np.dtype = None,
    exp_min: float | None = None,
    exp_max: float | None = None,
    exp_mean: float | None = None,
    exp_median: float | None = None,
    exp_std: float | None = None,
    rel_delta: float | None = None,
    abs_delta: float | None = None,
) -> None:
    stats_suite: dict[str, tuple[Callable[[np.ndarray], Any], Any]] = {
        "shape": (lambda array: array.shape, exp_shape),
        "dtype": (lambda array: array.dtype, exp_dtype),
        "min": (np.nanmin, exp_min),
        "max": (np.nanmax, exp_max),
        "mean": (np.nanmean, exp_mean),
        "median": (np.nanmedian, exp_median),
        "std": (np.nanstd, exp_std),
    }

    is_precise = {"shape", "dtype"}

    data_stats: dict[str, Any] = {}
    exp_stats: dict[str, Any] = {}
    for name, (func, expected) in stats_suite.items():
        if expected is not None:
            data_stats[name] = func(data)
            exp_stats[name] = (
                expected
                if name in is_precise
                else pytest.approx(expected, rel=rel_delta, abs=abs_delta)
            )

    assert data_stats == exp_stats, (
        f"Statistics differ from expected values. Actual: {data_stats}"
    )
