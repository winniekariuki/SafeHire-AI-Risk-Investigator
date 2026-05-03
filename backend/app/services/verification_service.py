"""Verification flags from verification_notes.csv — deterministic, no LLM calls."""

from __future__ import annotations

import pandas as pd

from app.services._records import read_csv, series_to_dict


def load_verification_notes() -> pd.DataFrame:
    return read_csv("verification_notes")


def get_verification(worker_id: str) -> dict[str, object]:
    wid = worker_id.strip()
    df = load_verification_notes()
    row = df[df["worker_id"] == wid]

    if row.empty:
        raise ValueError("Worker not found")

    return series_to_dict(row.iloc[0])


get_status = get_verification
