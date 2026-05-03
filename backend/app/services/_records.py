"""Shared CSV paths and row normalization (no I/O logic beyond pandas read)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def read_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file: {path}")
    return pd.read_csv(path)


def series_to_dict(series: pd.Series) -> dict[str, object]:
    """Convert a pandas Series to JSON-friendly plain Python values."""
    out: dict[str, object] = {}
    for key, val in series.items():
        k = str(key)
        if pd.isna(val):
            out[k] = None
        elif isinstance(val, (bool,)):
            out[k] = val
        elif hasattr(val, "item") and type(val).__module__.startswith("numpy"):
            out[k] = val.item()
        else:
            out[k] = val
    return out


def frame_to_dict_list(df: pd.DataFrame) -> list[dict[str, object]]:
    return [series_to_dict(df.iloc[i]) for i in range(len(df))]
