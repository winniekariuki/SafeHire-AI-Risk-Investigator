"""Misconduct reports from misconduct_reports.csv — deterministic, no LLM calls."""

from __future__ import annotations

import pandas as pd

from app.services._records import frame_to_dict_list, read_csv


def load_misconduct_reports() -> pd.DataFrame:
    return read_csv("misconduct_reports")


def get_misconduct_reports(worker_id: str) -> list[dict[str, object]]:
    wid = worker_id.strip()
    df = load_misconduct_reports()
    filtered = df[df["worker_id"] == wid]
    return frame_to_dict_list(filtered)


get_reports = get_misconduct_reports
