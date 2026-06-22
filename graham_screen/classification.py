from __future__ import annotations

import pandas as pd


FINANCIAL_SUBTYPES = {"银行", "保险", "证券", "其他金融"}


def financial_subtype(row: dict | pd.Series) -> str:
    text = " ".join(
        str(row.get(column, ""))
        for column in ("行业", "一级行业", "二级行业", "三级行业")
        if not pd.isna(row.get(column, ""))
    )
    if "银行" in text:
        return "银行"
    if "保险" in text:
        return "保险"
    if "证券" in text or "券商" in text:
        return "证券"
    if "非银金融" in text or "金融" in text:
        return "其他金融"
    return "非金融"


def is_financial_subtype(subtype: str) -> bool:
    return subtype in FINANCIAL_SUBTYPES
