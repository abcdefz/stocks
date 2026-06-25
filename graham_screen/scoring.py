from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class Rule:
    name: str
    column: str
    predicate: Callable[[object], bool]


def _between_gt_le(lower: float, upper: float) -> Callable[[object], bool]:
    return lambda value: value > lower and value <= upper


def _le(upper: float) -> Callable[[object], bool]:
    return lambda value: value <= upper


def _ge(lower: float) -> Callable[[object], bool]:
    return lambda value: value >= lower


def _gt(lower: float) -> Callable[[object], bool]:
    return lambda value: value > lower


def _is_true(value: object) -> bool:
    return bool(value)


ORDINARY_RULES: tuple[Rule, ...] = (
    Rule("PE-TTM > 0 且 <= 15", "PE-TTM", _between_gt_le(0, 15)),
    Rule("PB > 0 且 <= 1.5", "PB", _between_gt_le(0, 1.5)),
    Rule("PE×PB <= 22.5", "PE×PB", _le(22.5)),
    Rule("PE十年分位 <= 20%", "PE十年分位", _le(20)),
    Rule("PB十年分位 <= 20%", "PB十年分位", _le(20)),
    Rule("当前股息率 >= 3%", "股息率", _ge(3)),
    Rule("ROE5均 >= 8%", "ROE5均", _ge(8)),
    Rule("扣非ROE5均 >= 6%", "扣非ROE5均", _ge(6)),
    Rule("归母净利润最近5年全部为正", "归母净利润5年全正", _is_true),
    Rule("扣非归母净利润最近5年全部为正", "扣非归母净利润5年全正", _is_true),
    Rule("资产负债率 <= 60%", "资产负债率", _le(60)),
    Rule("有息负债率 <= 30%", "有息负债率", _le(30)),
    Rule("流动比率 >= 1.2", "流动比率", _ge(1.2)),
    Rule("速动比率 >= 0.8", "速动比率", _ge(0.8)),
    Rule("经营现金流/净利润5年 >= 0.8", "经营现金流/净利润5年", _ge(0.8)),
    Rule("自由现金流5年合计 > 0", "自由现金流5年合计", _gt(0)),
)


HK_AVAILABLE_RULE_COLUMNS = {
    "PE-TTM",
    "PB",
    "PE×PB",
    "PE十年分位",
    "PB十年分位",
    "股息率",
    "ROE5均",
    "归母净利润5年全正",
    "资产负债率",
    "流动比率",
    "经营现金流/净利润5年",
}

HK_ORDINARY_RULES: tuple[Rule, ...] = tuple(
    rule for rule in ORDINARY_RULES if rule.column in HK_AVAILABLE_RULE_COLUMNS
)


VALUATION_RULE_NAMES = {
    "PE-TTM > 0 且 <= 15",
    "PB > 0 且 <= 1.5",
    "PE×PB <= 22.5",
    "PE十年分位 <= 20%",
    "PB十年分位 <= 20%",
}


def _missing(value: object) -> bool:
    return pd.isna(value)


def rules_for_market(market: object) -> tuple[Rule, ...]:
    if str(market).lower() == "hk":
        return HK_ORDINARY_RULES
    return ORDINARY_RULES


def _score_row(row: pd.Series, rules: tuple[Rule, ...]) -> dict[str, object]:
    passed: list[str] = []
    failed: list[str] = []
    missing: list[str] = []

    for rule in rules:
        if rule.column not in row.index or _missing(row[rule.column]):
            missing.append(rule.column)
            continue
        if rule.predicate(row[rule.column]):
            passed.append(rule.name)
        else:
            failed.append(rule.name)

    judgeable = len(passed) + len(failed)
    score = len(passed) / judgeable if judgeable else pd.NA
    valuation_gate = not any(name in failed for name in VALUATION_RULE_NAMES) and not any(
        rule.column in missing for rule in rules if rule.name in VALUATION_RULE_NAMES
    )
    is_a = len(missing) == 0 and len(failed) == 0
    is_b = (not is_a) and valuation_gate and score is not pd.NA and score >= 0.85

    return {
        "通过规则数": len(passed),
        "可判断规则数": judgeable,
        "评分": score,
        "A档": is_a,
        "B档": is_b,
        "缺失项": "；".join(missing),
        "未通过规则": "；".join(failed),
        "通过规则": "；".join(passed),
    }


def score_ordinary_companies(
    frame: pd.DataFrame,
    rules: tuple[Rule, ...] = ORDINARY_RULES,
) -> pd.DataFrame:
    if frame.empty:
        result = frame.copy()
        for column in ("通过规则数", "可判断规则数", "评分", "A档", "B档", "缺失项", "未通过规则", "通过规则"):
            result[column] = []
        return result

    result = frame.copy()
    scores = pd.DataFrame([_score_row(row, rules) for _, row in result.iterrows()], index=result.index)
    for column in scores.columns:
        result[column] = scores[column]
    return result


def _condition(frame: pd.DataFrame, column: str, predicate: Callable[[pd.Series], pd.Series]) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return predicate(frame[column]).fillna(False)


def _bank_tag(row: pd.Series) -> str:
    if row.get("PB") <= 0.8 and row.get("股息率") >= 4:
        return "低PB高股息观察"
    if row.get("PB") <= 0.8 and row.get("ROE5均") < 8:
        return "低PB但盈利弱"
    if row.get("ROE5均") >= 8 and bool(row.get("归母净利润5年全正")):
        return "盈利稳定观察"
    return "缺银行专用指标，不评级"


def build_bank_candidate_pool(frame: pd.DataFrame) -> pd.DataFrame:
    if "金融分类" not in frame.columns:
        return pd.DataFrame()

    banks = frame[frame["金融分类"] == "银行"].copy()
    if banks.empty:
        banks["观察标签"] = []
        return banks

    mask = (
        _condition(banks, "PB", lambda series: (series > 0) & (series <= 1.0))
        & _condition(banks, "PB十年分位", lambda series: series <= 30)
        & _condition(banks, "股息率", lambda series: series >= 4)
        & _condition(banks, "ROE5均", lambda series: series >= 8)
        & _condition(banks, "扣非ROE5均", lambda series: series >= 6)
        & _condition(banks, "归母净利润5年全正", lambda series: series == True)  # noqa: E712
        & _condition(banks, "扣非归母净利润5年全正", lambda series: series == True)  # noqa: E712
    )
    pool = banks[mask].copy()
    if pool.empty:
        pool["观察标签"] = []
        return pool

    pool["观察标签"] = pool.apply(_bank_tag, axis=1)
    sort_columns = ["PB十年分位", "股息率", "ROE5均", "PB", "扣非ROE5均", "A股市值"]
    available = [column for column in sort_columns if column in pool.columns]
    ascending = [True, False, False, True, False, False][: len(available)]
    return pool.sort_values(available, ascending=ascending).reset_index(drop=True)
