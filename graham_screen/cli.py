from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse

import pandas as pd

from .classification import financial_subtype
from .columns import canonicalize_csv1, canonicalize_csv2
from .io import read_csv_with_fallback
from .metrics import derive_metrics
from .scoring import ORDINARY_RULES, Rule, build_bank_candidate_pool, rules_for_market, score_ordinary_companies
from .workbook import write_workbook


FINANCIAL_LIMITATION_NOTE = (
    "金融股未套用普通企业规则。银行先用 CSV1/CSV2 的通用字段生成候选池；只有补齐不良贷款率、"
    "拨备覆盖率、拨贷比、核心一级资本充足率、资本充足率、净息差后，才进入银行深度观察。"
    "保险和证券因缺少行业专用指标，仅单独观察，不评级。"
)

LIMITATION_NOTES = (
    "本结果是量化初筛，不构成投资建议；低 PE 的周期公司可能是价值陷阱；"
    "银行低 PB 可能反映信用风险、净息差压力、区域风险或资本压力；"
    "缺少行业专用金融指标时不能正式评分。"
)


DISPLAY_COLUMNS = [
    "交易所",
    "代码",
    "公司",
    "一级行业",
    "二级行业",
    "A股市值",
    "PE-TTM",
    "PE-TTM_普通",
    "PB",
    "PB_普通",
    "PE×PB",
    "PE十年分位",
    "PB十年分位",
    "股息率",
    "ROE5均",
    "扣非ROE5均",
    "归母净利润5年全正",
    "扣非归母净利润5年全正",
    "经营现金流/净利润5年",
    "自由现金流5年合计",
    "评分",
    "缺失项",
    "未通过规则",
    "理杏仁URL",
]

BANK_COLUMNS = [
    "交易所",
    "代码",
    "公司",
    "一级行业",
    "二级行业",
    "A股市值",
    "PE-TTM",
    "PB",
    "PE十年分位",
    "PB十年分位",
    "股息率",
    "ROE",
    "扣非ROE",
    "ROE5均",
    "扣非ROE5均",
    "归母净利润5年全正",
    "扣非归母净利润5年全正",
    "扣非归母净利润5年CAGR",
    "观察标签",
    "理杏仁URL",
]


@dataclass
class ScreenResult:
    output_path: Path
    csv1_row_count: int
    csv2_row_count: int
    merged_company_count: int
    csv2_only_discarded_count: int
    non_financial_count: int
    bank_count: int
    insurance_count: int
    securities_count: int
    other_financial_count: int
    a_count: int
    b_count: int
    c_count: int
    bank_candidate_count: int
    financial_observation_count: int
    sheets: dict[str, pd.DataFrame]


def _select_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available = [column for column in columns if column in frame.columns]
    return frame[available].copy()


def _sort_a(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in ["PE×PB", "股息率", "ROE5均"] if column in frame.columns]
    if not columns:
        return frame
    return frame.sort_values(columns, ascending=[True, False, False][: len(columns)])


def _sort_b(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in ["评分", "PE×PB", "股息率"] if column in frame.columns]
    if not columns:
        return frame
    return frame.sort_values(columns, ascending=[False, True, False][: len(columns)])


def _market_for_frame(frame: pd.DataFrame) -> str:
    exchanges = {
        str(exchange).lower()
        for exchange in frame.get("交易所", pd.Series(dtype=str)).dropna().unique()
        if str(exchange).lower() in {"hk", "sh", "sz"}
    }
    if exchanges == {"hk"}:
        return "hk"
    return "cn"


def _missing_fields_sheet(frame: pd.DataFrame, ordinary_rules: tuple[Rule, ...]) -> pd.DataFrame:
    fields = sorted({rule.column for rule in ordinary_rules} | set(BANK_COLUMNS))
    rows = []
    for field in fields:
        exists = field in frame.columns
        missing_count = int(frame[field].isna().sum()) if exists else len(frame)
        rows.append(
            {
                "字段": field,
                "是否存在": "是" if exists else "否",
                "缺失数量": missing_count,
                "说明": "用于普通企业评分或银行候选池" if field in {rule.column for rule in ordinary_rules} else "用于展示或银行候选池",
            }
        )
    return pd.DataFrame(rows)


def _summary_sheet(result_values: dict[str, object], ordinary_rules: tuple[Rule, ...]) -> pd.DataFrame:
    rows = [{"项目": key, "值": value} for key, value in result_values.items()]
    rows.extend(
        [
            {"项目": "普通企业规则摘要", "值": "；".join(rule.name for rule in ordinary_rules)},
            {"项目": "金融限制说明", "值": FINANCIAL_LIMITATION_NOTE},
            {"项目": "使用限制", "值": LIMITATION_NOTES},
        ]
    )
    return pd.DataFrame(rows)


def run_screen(csv1_path: str | Path, csv2_path: str | Path, output_path: str | Path) -> ScreenResult:
    csv1_raw = read_csv_with_fallback(csv1_path)
    csv2_raw = read_csv_with_fallback(csv2_path)

    csv1 = canonicalize_csv1(csv1_raw)
    csv2 = canonicalize_csv2(csv2_raw)

    key_columns = ["交易所", "代码"]
    csv1_keys = set(map(tuple, csv1[key_columns].to_numpy()))
    csv2_keys = set(map(tuple, csv2[key_columns].to_numpy()))
    csv2_only_discarded_count = len(csv2_keys - csv1_keys)

    merged = csv1.merge(csv2, on=key_columns, how="left", validate="one_to_one")
    merged = derive_metrics(merged)
    merged["金融分类"] = merged.apply(financial_subtype, axis=1)
    market = _market_for_frame(merged)
    ordinary_rules = rules_for_market(market)

    non_financial = merged[merged["金融分类"] == "非金融"].copy()
    all_scored = score_ordinary_companies(non_financial, rules=ordinary_rules)
    a_frame = _sort_a(all_scored[all_scored["A档"] == True].copy()).reset_index(drop=True)  # noqa: E712
    b_frame = _sort_b(all_scored[all_scored["B档"] == True].copy()).reset_index(drop=True)  # noqa: E712
    c_frame = _sort_b(all_scored[all_scored["C档"] == True].copy()).reset_index(drop=True)  # noqa: E712
    rejected = all_scored[
        (all_scored["A档"] != True) & (all_scored["B档"] != True) & (all_scored["C档"] != True)  # noqa: E712
    ].copy()

    bank_pool = build_bank_candidate_pool(merged)
    financial_observation = merged[merged["金融分类"].isin(["保险", "证券", "其他金融"])].copy()

    summary_values = {
        "CSV1行数": len(csv1_raw),
        "CSV2行数": len(csv2_raw),
        "合并公司数": len(merged),
        "CSV2独有且丢弃行数": csv2_only_discarded_count,
        "非金融公司数": len(non_financial),
        "银行数": int((merged["金融分类"] == "银行").sum()),
        "保险数": int((merged["金融分类"] == "保险").sum()),
        "证券数": int((merged["金融分类"] == "证券").sum()),
        "其他金融数": int((merged["金融分类"] == "其他金融").sum()),
        "A档数量": len(a_frame),
        "B档数量": len(b_frame),
        "C档数量": len(c_frame),
        "银行候选池数量": len(bank_pool),
        "金融单独观察数量": len(financial_observation),
        "普通企业规则口径": "港股可得字段版" if market == "hk" else "A股完整规则版",
        "缺失字段说明": "详见 缺失字段 sheet；评分时缺失规则进入 缺失项。C档为通过估值硬门槛且评分在70%-85%之间的低优先级观察。",
    }

    sheets = {
        "说明": _summary_sheet(summary_values, ordinary_rules),
        "A档_严格通过": _select_columns(a_frame, DISPLAY_COLUMNS),
        "B档_观察名单": _select_columns(b_frame, DISPLAY_COLUMNS),
        "C档_低优先级观察": _select_columns(c_frame, DISPLAY_COLUMNS),
        "银行_候选池": _select_columns(bank_pool, BANK_COLUMNS),
        "金融_单独观察": _select_columns(financial_observation, DISPLAY_COLUMNS + ["金融分类"]),
        "全部评分": _select_columns(all_scored, DISPLAY_COLUMNS + ["A档", "B档", "C档", "通过规则数", "可判断规则数"]),
        "剔除名单": _select_columns(rejected, DISPLAY_COLUMNS),
        "缺失字段": _missing_fields_sheet(merged, ordinary_rules),
    }

    output = write_workbook(output_path, sheets)

    return ScreenResult(
        output_path=output,
        csv1_row_count=len(csv1_raw),
        csv2_row_count=len(csv2_raw),
        merged_company_count=len(merged),
        csv2_only_discarded_count=csv2_only_discarded_count,
        non_financial_count=len(non_financial),
        bank_count=summary_values["银行数"],
        insurance_count=summary_values["保险数"],
        securities_count=summary_values["证券数"],
        other_financial_count=summary_values["其他金融数"],
        a_count=len(a_frame),
        b_count=len(b_frame),
        c_count=len(c_frame),
        bank_candidate_count=len(bank_pool),
        financial_observation_count=len(financial_observation),
        sheets=sheets,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run A-share Graham-style first-pass screening.")
    parser.add_argument("csv1", help="LiXinger CSV1: current valuation and financial state")
    parser.add_argument("csv2", help="LiXinger CSV2: five-year history")
    parser.add_argument("--output", default="格雷厄姆第一版筛选结果.xlsx", help="Output Excel workbook path")
    args = parser.parse_args(argv)

    result = run_screen(args.csv1, args.csv2, args.output)
    print(f"输出文件: {result.output_path}")
    print(f"A档数量: {result.a_count}")
    print(f"B档数量: {result.b_count}")
    print(f"C档数量: {result.c_count}")
    print(f"银行候选池数量: {result.bank_candidate_count}")
    print(f"金融单独观察数量: {result.financial_observation_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
