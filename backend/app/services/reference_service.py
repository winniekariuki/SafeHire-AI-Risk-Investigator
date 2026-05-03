"""Reference notes from reference_notes.csv — deterministic, no LLM calls."""

from __future__ import annotations

import pandas as pd

from app.services._records import frame_to_dict_list, read_csv


def load_reference_notes() -> pd.DataFrame:
    return read_csv("reference_notes")


def get_reference_notes(worker_id: str) -> list[dict[str, object]]:
    wid = worker_id.strip()
    df = load_reference_notes()
    filtered = df[df["worker_id"] == wid]
    return frame_to_dict_list(filtered)


get_references = get_reference_notes
