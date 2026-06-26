# Graham Portfolio Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a parallel JSON portfolio engine that builds a simple Graham-style equal-weight 20-stock portfolio from the existing LiXinger CSV inputs.

**Architecture:** Reuse the existing CSV ingestion, column canonicalization, metric derivation, and financial subtype classifier. Add one focused portfolio module for hard filters, MOS ranking, JSON serialization, and a separate CLI module so the existing workbook screen remains unchanged.

**Tech Stack:** Python 3.12, pandas, unittest, argparse, JSON standard library.

---

### Task 1: Portfolio Engine Core

**Files:**
- Create: `graham_screen/portfolio.py`
- Test: `tests/test_portfolio_engine.py`

- [ ] **Step 1: Write failing core tests**

Create `tests/test_portfolio_engine.py` with tests for non-financial pass/reject, bank pass, finance reject, MOS sorting, watchlist bounds, and equal weights.

```python
import unittest

import pandas as pd

from graham_screen.portfolio import build_portfolio_output, compute_mos, portfolio_industry_type


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
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run python -m unittest tests.test_portfolio_engine -v
```

Expected: fail because `graham_screen.portfolio` does not exist.

- [ ] **Step 3: Implement `graham_screen/portfolio.py`**

Create the module with these responsibilities:

- `portfolio_industry_type(financial_subtype_value)`.
- `compute_mos(pe, pb)`.
- `build_portfolio_output(frame)`.
- Internal rule evaluators for non-financial and bank rows.

The function returns only JSON-serializable Python dictionaries and lists.

- [ ] **Step 4: Run the core tests**

Run:

```bash
uv run python -m unittest tests.test_portfolio_engine -v
```

Expected: all tests pass.

### Task 2: CSV Runner And CLI

**Files:**
- Modify: `graham_screen/portfolio.py`
- Create: `graham_screen/portfolio_cli.py`
- Create: `scripts/graham_portfolio.py`
- Modify: `pyproject.toml`
- Test: `tests/test_portfolio_engine.py`

- [ ] **Step 1: Add failing runner and CLI tests**

Extend `tests/test_portfolio_engine.py`:

```python
from pathlib import Path
import json
import subprocess
import sys
import tempfile

from graham_screen.portfolio import run_portfolio_engine


ROOT = Path(__file__).resolve().parents[1]


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
```

- [ ] **Step 2: Run the failing CLI tests**

Run:

```bash
uv run python -m unittest tests.test_portfolio_engine.PortfolioCliTest -v
```

Expected: fail because `run_portfolio_engine` and CLI files do not exist.

- [ ] **Step 3: Implement CSV runner**

Add `run_portfolio_engine(csv1_path, csv2_path)` in `graham_screen/portfolio.py`. It reads both CSVs, canonicalizes, merges by `交易所 + 代码`, derives metrics, applies `financial_subtype`, and calls `build_portfolio_output`.

- [ ] **Step 4: Implement CLI and script wrapper**

Create `graham_screen/portfolio_cli.py` with argparse for `csv1`, `csv2`, and `--output`.

Create `scripts/graham_portfolio.py` as a thin import wrapper.

Add a console script entry in `pyproject.toml`:

```toml
graham-portfolio = "graham_screen.portfolio_cli:main"
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
uv run python -m unittest tests.test_portfolio_engine.PortfolioCliTest -v
```

Expected: all CLI tests pass.

### Task 3: Documentation And Regression

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the new command**

Add a short section showing:

```bash
uv run graham-portfolio CSV1.csv CSV2.csv --output portfolio.json
```

State that this JSON engine is parallel to the Excel workbook report and is not investment advice.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Run sample portfolio command**

Run:

```bash
uv run graham-portfolio 公司筛选_格雷厄姆CSV1_20260622_212016.csv 公司筛选_格雷厄姆CSV2_20260622_212026.csv --output /tmp/graham_portfolio.json
```

Expected: command exits 0 and writes a JSON object with `portfolio`, `watchlist`, and `reject`.

## Plan Self-Review

- Spec coverage: the tasks cover the separate module, hard filters, industry mapping, MOS sorting, JSON output, CLI, and tests.
- Placeholder scan: no task depends on undefined requirements or deferred behavior.
- Type consistency: public functions are consistently named `compute_mos`, `portfolio_industry_type`, `build_portfolio_output`, and `run_portfolio_engine`.
