from __future__ import annotations

from datetime import date
import math
import re

import numpy as np
import pandas as pd


MISSING_STRINGS = {"", "--", "nan", "NaN", "None", "none", "null", "NULL"}


def clean_number(value: object, percent: bool = False) -> float:
    """Clean LiXinger numeric cells into floats.

    Percent values are stored in percentage-point units. For example, both
    ``16.71`` and decimal-formatted ``0.1671`` become ``16.71`` when
    ``percent=True``.
    """
    if value is None or pd.isna(value):
        return math.nan
    text = str(value).strip()
    if text.startswith("="):
        text = text[1:].strip()
    while len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    if text in MISSING_STRINGS:
        return math.nan
    text = text.replace("%", "").replace(",", "").replace(" ", "")
    if text in MISSING_STRINGS:
        return math.nan
    try:
        number = float(text)
    except ValueError:
        return math.nan
    if percent and number != 0 and abs(number) <= 1:
        return number * 100
    return number


def clean_numeric_series(series: pd.Series, percent: bool = False) -> pd.Series:
    return series.map(lambda value: clean_number(value, percent=percent)).astype(float)


def _history_columns(frame: pd.DataFrame, prefix: str) -> list[str]:
    return [f"{prefix}_{offset}" for offset in range(5) if f"{prefix}_{offset}" in frame.columns]


def _all_positive(row: pd.Series, columns: list[str]) -> object:
    if len(columns) < 5:
        return pd.NA
    values = [row[column] for column in columns]
    if any(pd.isna(value) for value in values):
        return pd.NA
    return all(value > 0 for value in values)


def _safe_cagr(latest: object, oldest: object, years: int = 4) -> float:
    if pd.isna(latest) or pd.isna(oldest) or latest <= 0 or oldest <= 0:
        return math.nan
    return ((latest / oldest) ** (1 / years) - 1) * 100


def _listing_years(value: object, today: date) -> float:
    if pd.isna(value):
        return math.nan
    match = re.search(r"\d{4}-\d{1,2}-\d{1,2}", str(value))
    if not match:
        return math.nan
    listed = date.fromisoformat(match.group(0))
    return round((today - listed).days / 365.25, 2)


def derive_metrics(frame: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    result = frame.copy()
    today = today or date.today()

    if {"PE-TTM", "PB"}.issubset(result.columns):
        result["PE×PB"] = result["PE-TTM"] * result["PB"]

    if "上市日期" in result.columns:
        result["上市年数"] = result["上市日期"].map(lambda value: _listing_years(value, today))

    roe_columns = _history_columns(result, "ROE")
    if roe_columns:
        result["ROE5均"] = result[roe_columns].mean(axis=1, skipna=True)
        result["ROE5最小"] = result[roe_columns].min(axis=1, skipna=True)

    deducted_roe_columns = _history_columns(result, "扣非ROE")
    if deducted_roe_columns:
        result["扣非ROE5均"] = result[deducted_roe_columns].mean(axis=1, skipna=True)
        result["扣非ROE5最小"] = result[deducted_roe_columns].min(axis=1, skipna=True)

    profit_columns = _history_columns(result, "归母净利润")
    if profit_columns:
        result["归母净利润5年全正"] = result.apply(lambda row: _all_positive(row, profit_columns), axis=1)

    deducted_profit_columns = _history_columns(result, "扣非归母净利润")
    if deducted_profit_columns:
        result["扣非归母净利润5年全正"] = result.apply(
            lambda row: _all_positive(row, deducted_profit_columns), axis=1
        )
        if {"扣非归母净利润_0", "扣非归母净利润_4"}.issubset(result.columns):
            result["扣非归母净利润5年CAGR"] = result.apply(
                lambda row: _safe_cagr(row["扣非归母净利润_0"], row["扣非归母净利润_4"]),
                axis=1,
            )

    cashflow_columns = _history_columns(result, "经营现金流净额")
    if len(cashflow_columns) < 5:
        inflow_columns = _history_columns(result, "经营现金流入")
        outflow_columns = _history_columns(result, "经营现金流出")
        if len(inflow_columns) == 5 and len(outflow_columns) == 5:
            for offset in range(5):
                result[f"经营现金流净额_{offset}"] = (
                    result[f"经营现金流入_{offset}"] - result[f"经营现金流出_{offset}"]
                )
            cashflow_columns = _history_columns(result, "经营现金流净额")

    if cashflow_columns:
        result["经营现金流净额5年合计"] = result[cashflow_columns].sum(axis=1, min_count=1)

    if cashflow_columns and profit_columns:
        cashflow_sum = result[cashflow_columns].sum(axis=1, min_count=1)
        profit_sum = result[profit_columns].sum(axis=1, min_count=1).replace(0, np.nan)
        result["经营现金流/净利润5年"] = cashflow_sum / profit_sum

    free_cashflow_columns = _history_columns(result, "自由现金流")
    if free_cashflow_columns:
        result["自由现金流5年合计"] = result[free_cashflow_columns].sum(axis=1, min_count=1)

    if {"销售商品提供劳务收到的现金", "营业收入"}.issubset(result.columns):
        revenue = result["营业收入"].replace(0, np.nan)
        result["收现比"] = result["销售商品提供劳务收到的现金"] / revenue

    return result
