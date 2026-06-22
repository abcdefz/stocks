from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


CSV_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "gb18030", "gbk")


def clean_stock_code(value: object) -> str:
    """Normalize LiXinger stock-code exports without losing leading zeroes."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.startswith("="):
        text = text[1:].strip()
    while len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text


def read_csv_with_fallback(path: str | Path, encodings: Iterable[str] = CSV_ENCODINGS) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(csv_path, encoding=encoding, dtype=str)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise UnicodeDecodeError(
        "csv",
        b"",
        0,
        1,
        f"unable to decode {csv_path} with encodings: {', '.join(encodings)}",
    ) from last_error
