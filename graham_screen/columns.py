from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .io import clean_stock_code
from .metrics import clean_numeric_series


PERCENT_FIELDS = {
    "股息率",
    "PE十年分位",
    "PB十年分位",
    "股息率十年分位",
    "ROE",
    "扣非ROE",
    "ROA",
    "资产负债率",
    "有息负债率",
    "股息率5年平均",
    "股息率5年最小",
}


def _normalize_headers(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.columns = [str(column).strip() for column in result.columns]
    return result


def _find_column(
    columns: list[str],
    must: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> str | None:
    for column in columns:
        if all(token in column for token in must) and not any(token in column for token in exclude):
            return column
    return None


def _numeric(frame: pd.DataFrame, column: str | None, percent: bool = False) -> pd.Series:
    if column is None:
        return pd.Series([np.nan] * len(frame), index=frame.index, dtype="float64")
    return clean_numeric_series(frame[column], percent=percent)


def _text(frame: pd.DataFrame, column: str | None) -> pd.Series:
    if column is None:
        return pd.Series([""] * len(frame), index=frame.index, dtype="object")
    return frame[column].fillna("").astype(str).str.strip()


def _coalesce(left: pd.Series, right: pd.Series) -> pd.Series:
    return left.combine_first(right)


def canonicalize_csv1(raw: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_headers(raw)
    columns = list(frame.columns)
    out = pd.DataFrame(index=frame.index)

    out["交易所"] = _text(frame, _find_column(columns, ("交易所",))).str.lower()
    out["代码"] = _text(frame, _find_column(columns, ("代码",))).map(clean_stock_code)
    company_column = _find_column(columns, ("公司",)) or _find_column(columns, ("名称",))
    out["公司"] = _text(frame, company_column)
    out["一级行业"] = _text(frame, _find_column(columns, ("一级行业",)))
    out["二级行业"] = _text(frame, _find_column(columns, ("二级行业",)))
    out["三级行业"] = _text(frame, _find_column(columns, ("三级行业",)))
    out["上市日期"] = _text(frame, _find_column(columns, ("上市日期",)))
    out["理杏仁URL"] = _text(frame, _find_column(columns, ("理杏仁", "Url")))

    pe_plain = _numeric(frame, _find_column(columns, ("PE-TTM", "最新时间"), ("扣非", "统计")), percent=False)
    pe_deducted = _numeric(frame, _find_column(columns, ("PE-TTM(扣非)", "最新时间"), ("统计",)), percent=False)
    pb_plain = _numeric(frame, _find_column(columns, ("PB", "最新时间"), ("不含商誉", "统计")), percent=False)
    pb_no_goodwill = _numeric(frame, _find_column(columns, ("PB(不含商誉)", "最新时间"), ("统计",)), percent=False)
    pe_pct_plain = _numeric(frame, _find_column(columns, ("PE-TTM统计值(10年)", "分位点"), ("扣非",)), percent=True)
    pe_pct_deducted = _numeric(frame, _find_column(columns, ("PE-TTM(扣非)统计值(10年)", "分位点")), percent=True)
    pb_pct_plain = _numeric(frame, _find_column(columns, ("PB统计值(10年)", "分位点"), ("不含商誉",)), percent=True)
    pb_pct_no_goodwill = _numeric(frame, _find_column(columns, ("PB(不含商誉)统计值(10年)", "分位点")), percent=True)

    out["PE-TTM_普通"] = pe_plain
    out["PE-TTM扣非"] = pe_deducted
    out["PE-TTM"] = _coalesce(pe_deducted, pe_plain)
    out["PB_普通"] = pb_plain
    out["PB不含商誉"] = pb_no_goodwill
    out["PB"] = _coalesce(pb_no_goodwill, pb_plain)
    out["PE十年分位"] = _coalesce(pe_pct_deducted, pe_pct_plain)
    out["PB十年分位"] = _coalesce(pb_pct_no_goodwill, pb_pct_plain)

    mappings = {
        "A股市值": (("A股市值",), (), False),
        "股息率": (("股息率", "最新时间"), ("统计",), True),
        "股息率十年分位": (("股息率统计值(10年)", "分位点"), (), True),
        "ROE": (("净资产收益率(ROE)",), ("归属于", "最新Q4"), True),
        "扣非ROE": (("扣非ROE",), ("最新Q4",), True),
        "ROA": (("总资产收益率(ROA)",), (), True),
        "资产负债率": (("资产负债率",), (), True),
        "有息负债率": (("有息负债率",), (), True),
        "流动比率": (("流动比率",), (), False),
        "速动比率": (("速动比率",), (), False),
        "经营现金流净额": (("经营活动产生的现金流量净额",), (), False),
        "自由现金流": (("自由现金流量",), (), False),
        "净利润": (("净利润",), ("率",), False),
        "商誉": (("商誉",), (), False),
        "销售商品提供劳务收到的现金": (("销售商品", "提供劳务收到的现金"), (), False),
        "营业收入": (("营业收入",), (), False),
    }

    for canonical, (must, exclude, percent) in mappings.items():
        out[canonical] = _numeric(frame, _find_column(columns, must, exclude), percent=percent)

    return out


def _offset_from_column(column: str) -> int | None:
    if "最新Q4" not in column:
        return None
    match = re.search(r"偏移(\d+)年", column)
    if match:
        return int(match.group(1))
    return 0


def _assign_history(
    source: pd.DataFrame,
    target: pd.DataFrame,
    prefix: str,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
    percent: bool = False,
) -> None:
    for column in source.columns:
        offset = _offset_from_column(column)
        if offset is None or offset > 4:
            continue
        if all(token in column for token in include) and not any(token in column for token in exclude):
            target[f"{prefix}_{offset}"] = clean_numeric_series(source[column], percent=percent)


def canonicalize_csv2(raw: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_headers(raw)
    columns = list(frame.columns)
    out = pd.DataFrame(index=frame.index)

    out["交易所"] = _text(frame, _find_column(columns, ("交易所",))).str.lower()
    out["代码"] = _text(frame, _find_column(columns, ("代码",))).map(clean_stock_code)

    _assign_history(frame, out, "ROE", ("净资产收益率(ROE)",), ("扣非", "归属于"), percent=True)
    _assign_history(frame, out, "扣非ROE", ("扣非ROE",), (), percent=True)
    _assign_history(frame, out, "归母净利润", ("股东的净利润",), ("扣除非经常性",), percent=False)
    _assign_history(frame, out, "扣非归母净利润", ("扣除非经常性损益的净利润",), (), percent=False)
    _assign_history(frame, out, "自由现金流", ("自由现金流量",), (), percent=False)
    _assign_history(frame, out, "经营现金流净额", ("经营活动产生的现金流量净额",), (), percent=False)
    _assign_history(frame, out, "经营现金流入", ("经营活动现金流入小计",), (), percent=False)
    _assign_history(frame, out, "经营现金流出", ("经营活动现金流出小计",), (), percent=False)

    out["股息率5年平均"] = _numeric(frame, _find_column(columns, ("股息率统计值(5年)", "平均值")), percent=True)
    out["股息率5年最小"] = _numeric(frame, _find_column(columns, ("股息率统计值(5年)", "最小值")), percent=True)

    return out
