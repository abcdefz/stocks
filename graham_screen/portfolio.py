from __future__ import annotations

from pathlib import Path
import math
from typing import Callable

import pandas as pd

from .classification import financial_subtype
from .columns import canonicalize_csv1, canonicalize_csv2
from .io import read_csv_with_fallback
from .metrics import derive_metrics


PortfolioOutput = dict[str, list[dict[str, object]]]
PORTFOLIO_SIZE = 20
WATCHLIST_START = 20
WATCHLIST_END = 40


def _is_missing(value: object) -> bool:
    return value is None or pd.isna(value)


def _as_float(value: object) -> float:
    if _is_missing(value):
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _as_bool(value: object) -> bool:
    return bool(value) if not _is_missing(value) else False


def portfolio_industry_type(financial_subtype_value: object) -> str:
    subtype = "" if _is_missing(financial_subtype_value) else str(financial_subtype_value)
    if subtype == "银行":
        return "bank"
    if subtype in {"保险", "证券", "其他金融"}:
        return "finance"
    return "non_financial"


def compute_mos(pe_ttm: object, pb: object) -> float:
    values: list[float] = []
    pe = _as_float(pe_ttm)
    if not math.isnan(pe):
        values.append(1 - (pe / 15) * 0.5)
    pb_value = _as_float(pb)
    if not math.isnan(pb_value):
        values.append(1 - (pb_value / 1.5) * 0.5)
    return min(values) if values else math.nan


def _row_id(row: pd.Series) -> dict[str, object]:
    return {
        "代码": "" if _is_missing(row.get("代码")) else str(row.get("代码")),
        "交易所": "" if _is_missing(row.get("交易所")) else str(row.get("交易所")),
    }


def _missing_columns(row: pd.Series, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column not in row.index or _is_missing(row.get(column))]


def _rule_failed(row: pd.Series, column: str, predicate: Callable[[object], bool]) -> bool:
    return column in row.index and not _is_missing(row.get(column)) and not predicate(row.get(column))


def _format_reasons(missing: list[str], failed: list[str]) -> str:
    reasons: list[str] = []
    if missing:
        reasons.append(f"缺失: {', '.join(missing)}")
    if failed:
        reasons.append(f"未通过: {', '.join(failed)}")
    return "；".join(reasons)


def _evaluate_non_financial(row: pd.Series) -> str:
    required = (
        "PE-TTM",
        "PB",
        "ROE5均",
        "归母净利润5年全正",
        "资产负债率",
        "流动比率",
        "经营现金流/净利润5年",
    )
    missing = _missing_columns(row, required)
    failed: list[str] = []
    checks: tuple[tuple[str, str, Callable[[object], bool]], ...] = (
        ("PE-TTM", "PE-TTM不在(0, 15]区间", lambda value: 0 < _as_float(value) <= 15),
        ("PB", "PB不在(0, 1.5]区间", lambda value: 0 < _as_float(value) <= 1.5),
        ("ROE5均", "ROE5均低于8", lambda value: _as_float(value) >= 8),
        ("归母净利润5年全正", "归母净利润5年未全正", _as_bool),
        ("资产负债率", "资产负债率高于60", lambda value: _as_float(value) <= 60),
        ("流动比率", "流动比率低于1.2", lambda value: _as_float(value) >= 1.2),
        ("经营现金流/净利润5年", "经营现金流/净利润5年低于0.8", lambda value: _as_float(value) >= 0.8),
    )
    for column, reason, predicate in checks:
        if _rule_failed(row, column, predicate):
            failed.append(reason)
    return _format_reasons(missing, failed)


def _evaluate_bank(row: pd.Series) -> str:
    required = ("PB", "ROE5均", "归母净利润5年全正", "股息率")
    missing = _missing_columns(row, required)
    failed: list[str] = []
    checks: tuple[tuple[str, str, Callable[[object], bool]], ...] = (
        ("PB", "PB不在(0, 1.0]区间", lambda value: 0 < _as_float(value) <= 1.0),
        ("ROE5均", "ROE5均低于8", lambda value: _as_float(value) >= 8),
        ("归母净利润5年全正", "归母净利润5年未全正", _as_bool),
        ("股息率", "股息率低于4", lambda value: _as_float(value) >= 4),
    )
    for column, reason, predicate in checks:
        if _rule_failed(row, column, predicate):
            failed.append(reason)
    return _format_reasons(missing, failed)


def _portfolio_row(row: pd.Series, industry_type: str, mos: float) -> dict[str, object]:
    return {
        **_row_id(row),
        "行业类型": industry_type,
        "MOS值": float(round(mos, 6)),
    }


def _reject_row(row: pd.Series, industry_type: str, reason: str) -> dict[str, object]:
    return {
        **_row_id(row),
        "行业类型": industry_type,
        "剔除原因": reason,
    }


def build_portfolio_output(frame: pd.DataFrame) -> PortfolioOutput:
    candidates: list[dict[str, object]] = []
    reject: list[dict[str, object]] = []

    for _, row in frame.iterrows():
        industry_type = portfolio_industry_type(row.get("金融分类", "非金融"))
        if industry_type == "finance":
            reject.append(_reject_row(row, industry_type, "缺少行业专用指标，未进入组合"))
            continue

        reason = _evaluate_bank(row) if industry_type == "bank" else _evaluate_non_financial(row)
        if reason:
            reject.append(_reject_row(row, industry_type, reason))
            continue

        mos = compute_mos(row.get("PE-TTM"), row.get("PB"))
        if math.isnan(mos):
            reject.append(_reject_row(row, industry_type, "缺失: MOS排序字段"))
            continue
        candidates.append(_portfolio_row(row, industry_type, mos))

    candidates.sort(key=lambda item: item["MOS值"], reverse=True)
    portfolio = candidates[:PORTFOLIO_SIZE]
    weight = round(1 / len(portfolio), 8) if portfolio else 0
    portfolio = [{**row, "等权权重": weight} for row in portfolio]
    watchlist = candidates[WATCHLIST_START:WATCHLIST_END]

    return {
        "portfolio": portfolio,
        "watchlist": watchlist,
        "reject": reject,
    }


def run_portfolio_engine(
    csv1_path: str | Path,
    csv2_path: str | Path,
) -> PortfolioOutput:
    csv1 = canonicalize_csv1(read_csv_with_fallback(csv1_path))
    csv2 = canonicalize_csv2(read_csv_with_fallback(csv2_path))
    merged = csv1.merge(csv2, on=["交易所", "代码"], how="left", validate="one_to_one")
    merged = derive_metrics(merged)
    merged["金融分类"] = merged.apply(financial_subtype, axis=1)
    return build_portfolio_output(merged)
