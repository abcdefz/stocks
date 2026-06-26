from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

from graham_screen.portfolio import (
    build_portfolio_output,
    compute_mos,
    portfolio_industry_type,
    run_portfolio_engine,
)


ROOT = Path(__file__).resolve().parents[1]


class PortfolioEngineTest(unittest.TestCase):
    def test_compute_mos_uses_lower_of_pe_and_pb_sides(self):
        self.assertAlmostEqual(compute_mos(7.5, 0.75), 0.75)
        self.assertAlmostEqual(compute_mos(None, 0.75), 0.75)
        self.assertTrue(pd.isna(compute_mos(None, None)))

    def test_industry_type_maps_non_bank_finance_to_finance(self):
        self.assertEqual(portfolio_industry_type("银行"), "bank")
        self.assertEqual(portfolio_industry_type("保险"), "finance")
        self.assertEqual(portfolio_industry_type("证券"), "finance")
        self.assertEqual(portfolio_industry_type("其他金融"), "finance")
        self.assertEqual(portfolio_industry_type("非金融"), "non_financial")

    def test_build_output_filters_sorts_and_weights(self):
        rows = []
        for index in range(25):
            rows.append(
                {
                    "交易所": "sz",
                    "代码": f"000{index:03d}",
                    "金融分类": "非金融",
                    "PE-TTM": 5 + index * 0.1,
                    "PB": 0.5 + index * 0.01,
                    "ROE5均": 10,
                    "归母净利润5年全正": True,
                    "资产负债率": 40,
                    "流动比率": 1.5,
                    "经营现金流/净利润5年": 1.0,
                }
            )
        frame = pd.DataFrame(rows)

        output = build_portfolio_output(frame)

        self.assertEqual(set(output), {"portfolio", "watchlist", "reject"})
        self.assertEqual(len(output["portfolio"]), 20)
        self.assertEqual(len(output["watchlist"]), 5)
        self.assertEqual(output["portfolio"][0]["代码"], "000000")
        self.assertEqual(output["watchlist"][0]["代码"], "000020")
        self.assertAlmostEqual(output["portfolio"][0]["等权权重"], 0.05)

    def test_bank_passes_without_ordinary_cash_flow_rules(self):
        frame = pd.DataFrame(
            [
                {
                    "交易所": "sh",
                    "代码": "600000",
                    "金融分类": "银行",
                    "PE-TTM": None,
                    "PB": 0.8,
                    "ROE5均": 9,
                    "归母净利润5年全正": True,
                    "股息率": 5,
                    "资产负债率": 95,
                    "流动比率": None,
                    "经营现金流/净利润5年": None,
                }
            ]
        )

        output = build_portfolio_output(frame)

        self.assertEqual(len(output["portfolio"]), 1)
        self.assertEqual(output["portfolio"][0]["行业类型"], "bank")
        self.assertEqual(output["reject"], [])

    def test_finance_and_missing_fields_enter_reject_with_reasons(self):
        frame = pd.DataFrame(
            [
                {"交易所": "sh", "代码": "601318", "金融分类": "保险", "PB": 1.0},
                {
                    "交易所": "sz",
                    "代码": "000001",
                    "金融分类": "非金融",
                    "PE-TTM": 10,
                    "PB": 1.0,
                    "ROE5均": None,
                    "归母净利润5年全正": True,
                    "资产负债率": 40,
                    "流动比率": 1.5,
                    "经营现金流/净利润5年": 1.0,
                },
            ]
        )

        output = build_portfolio_output(frame)

        self.assertEqual(len(output["portfolio"]), 0)
        self.assertEqual(len(output["reject"]), 2)
        reasons = {row["代码"]: row["剔除原因"] for row in output["reject"]}
        self.assertIn("行业专用指标", reasons["601318"])
        self.assertIn("缺失: ROE5均", reasons["000001"])


class PortfolioCliTest(unittest.TestCase):
    def test_run_portfolio_engine_reads_repository_csvs(self):
        csv1 = ROOT / "公司筛选_格雷厄姆CSV1_20260622_212016.csv"
        csv2 = ROOT / "公司筛选_格雷厄姆CSV2_20260622_212026.csv"
        if not csv1.exists() or not csv2.exists():
            self.skipTest("repository CSV sample files are not present")

        output = run_portfolio_engine(csv1, csv2)

        self.assertEqual(set(output), {"portfolio", "watchlist", "reject"})
        for row in output["portfolio"]:
            self.assertIsInstance(row["代码"], str)
            self.assertIn(row["行业类型"], {"non_financial", "bank"})

    def test_cli_writes_json_file(self):
        csv1 = ROOT / "公司筛选_格雷厄姆CSV1_20260622_212016.csv"
        csv2 = ROOT / "公司筛选_格雷厄姆CSV2_20260622_212026.csv"
        script = ROOT / "scripts" / "graham_portfolio.py"
        if not csv1.exists() or not csv2.exists():
            self.skipTest("repository CSV sample files are not present")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "portfolio.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(csv1),
                    str(csv2),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"portfolio", "watchlist", "reject"})

    def test_cli_rejects_portfolio_size_option(self):
        csv1 = ROOT / "公司筛选_格雷厄姆CSV1_20260622_212016.csv"
        csv2 = ROOT / "公司筛选_格雷厄姆CSV2_20260622_212026.csv"
        script = ROOT / "scripts" / "graham_portfolio.py"
        if not csv1.exists() or not csv2.exists():
            self.skipTest("repository CSV sample files are not present")

        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                str(csv1),
                str(csv2),
                "--portfolio-size",
                "10",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unrecognized arguments", completed.stderr)


if __name__ == "__main__":
    unittest.main()
