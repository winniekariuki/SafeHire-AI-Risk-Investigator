"""Worker profile rows from workers.csv — deterministic, no LLM calls."""

from __future__ import annotations

import pandas as pd

from app.services._records import frame_to_dict_list, read_csv, series_to_dict


def load_workers() -> pd.DataFrame:
    return read_csv("workers")


def list_workers() -> list[dict[str, object]]:
    return frame_to_dict_list(load_workers())


def get_worker(worker_id: str) -> dict[str, object]:
    wid = worker_id.strip()
    workers = load_workers()
    worker = workers[workers["worker_id"] == wid]

    if worker.empty:
        raise ValueError("Worker not found")

    return series_to_dict(worker.iloc[0])
