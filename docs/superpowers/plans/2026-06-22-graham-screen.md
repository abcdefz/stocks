# Graham Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a Python CLI that calculates the provided CSV1/CSV2 files into `格雷厄姆第一版筛选结果.xlsx`.

**Architecture:** Use a focused Python package with separate modules for I/O, column mapping, metrics, classification, scoring, and workbook writing. Keep `scripts/graham_screen.py` as the user-facing entrypoint and cover behavior with `unittest`.

**Tech Stack:** Python 3, pandas, openpyxl, unittest.

---

### Task 1: Test Core Cleaning And Classification

**Files:**
- Create: `tests/test_cleaning_and_classification.py`
- Create later: `graham_screen/io.py`
- Create later: `graham_screen/metrics.py`
- Create later: `graham_screen/classification.py`

- [ ] Write failing tests for LiXinger stock-code cleanup, numeric cleanup, percentage normalization, and financial subtype classification.
- [ ] Run `python3 -m unittest tests.test_cleaning_and_classification -v` and confirm the tests fail because `graham_screen` does not exist yet.
- [ ] Implement the minimal modules needed for these tests.
- [ ] Re-run the tests and confirm they pass.

### Task 2: Test Column Mapping And Derived Metrics

**Files:**
- Create: `tests/test_columns_and_metrics.py`
- Create later: `graham_screen/columns.py`
- Modify later: `graham_screen/metrics.py`

- [ ] Write failing tests that map the current LiXinger long headers to canonical fields.
- [ ] Write failing tests for PE x PB, five-year means/minimums, profit-all-positive flags, CAGR, operating-cash-flow fallback, and free-cash-flow totals.
- [ ] Run `python3 -m unittest tests.test_columns_and_metrics -v` and confirm failure from missing implementation.
- [ ] Implement canonical column selection and metric derivation.
- [ ] Re-run the tests and confirm they pass.

### Task 3: Test Ordinary Scoring And Bank Candidate Rules

**Files:**
- Create: `tests/test_scoring.py`
- Create later: `graham_screen/scoring.py`

- [ ] Write failing tests for A档 strict pass, B档 score threshold, missing-rule denominator handling, bank candidate filters, and bank observation tags.
- [ ] Run `python3 -m unittest tests.test_scoring -v` and confirm failure from missing implementation.
- [ ] Implement ordinary scoring and bank candidate selection.
- [ ] Re-run the tests and confirm they pass.

### Task 4: Test End-To-End CLI

**Files:**
- Create: `tests/test_end_to_end.py`
- Create later: `graham_screen/cli.py`
- Create later: `graham_screen/workbook.py`
- Create later: `scripts/graham_screen.py`

- [ ] Write a failing integration test that runs the two repository CSV files through the public calculation function and asserts the workbook exists with the required sheets.
- [ ] Run `python3 -m unittest tests.test_end_to_end -v` and confirm failure from missing implementation.
- [ ] Implement the CLI calculation flow and workbook writing.
- [ ] Re-run the integration test and confirm it passes.

### Task 5: Project Metadata And User Docs

**Files:**
- Create: `README.md`
- Create: `requirements.txt`
- Create: `.gitignore`

- [ ] Document the command using the current CSV filenames.
- [ ] List runtime dependencies `pandas` and `openpyxl`.
- [ ] Ignore generated workbooks, caches, and Python bytecode.
- [ ] Confirm no project instructions conflict with `AGENTS.md`.

### Task 6: Final Verification

**Files:**
- Generated: `格雷厄姆第一版筛选结果.xlsx`

- [ ] Run `python3 -m unittest discover -s tests -v`.
- [ ] Run `python3 scripts/graham_screen.py 公司筛选_格雷厄姆CSV1_20260622_212016.csv 公司筛选_格雷厄姆CSV2_20260622_212026.csv --output 格雷厄姆第一版筛选结果.xlsx`.
- [ ] Inspect the workbook sheet names, counts, and top rows.
- [ ] Confirm the final response can report A档数量, B档数量, 银行候选池数量, 金融单独观察数量, A档前20名, and 银行候选池前20名.

## Plan Self-Review

- The plan covers every required artifact in `AGENTS.md`: workbook sheets, summary counts, financial separation, ordinary scoring, bank candidate handling, and missing fields.
- There are no `TBD` or deferred implementation sections.
- Function boundaries match the design spec and can be tested independently.
- The acceptance check is concrete: the two repository CSV files must calculate successfully.
