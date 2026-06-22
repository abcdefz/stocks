# Graham Screen Design

## Goal

Build a reusable Python command line tool that reads the two LiXinger CSV exports in this repository, applies the A-share Graham-style first-pass screening rules from `AGENTS.md`, and writes `格雷厄姆第一版筛选结果.xlsx`.

## Inputs

- CSV1 is the current valuation and financial-state export.
- CSV2 is the five-year history export.
- The merge key is `交易所 + 代码`.
- CSV1 is authoritative. Rows present only in CSV2 are discarded.
- Stock codes remain strings after removing LiXinger formula wrappers such as `="002801"`.

## Architecture

The implementation is a small Python package plus a CLI:

- `graham_screen/io.py` reads CSV files with the required encoding fallback and normalizes stock identifiers.
- `graham_screen/columns.py` maps LiXinger long column names to canonical field names.
- `graham_screen/metrics.py` cleans numeric values and derives five-year metrics.
- `graham_screen/classification.py` separates non-financial companies, banks, insurance, securities, and other financial companies.
- `graham_screen/scoring.py` applies ordinary-company A/B scoring and bank candidate rules.
- `graham_screen/workbook.py` writes the required Excel workbook.
- `graham_screen/cli.py` exposes the calculation command.
- `scripts/graham_screen.py` is a thin executable wrapper.

## Data Flow

1. Read CSV1 and CSV2 using the encoding fallback `utf-8-sig`, `utf-8`, `gb18030`, `gbk`.
2. Normalize key columns and equivalent names.
3. Convert numeric fields, preserving percentage-point units.
4. Merge CSV1 left with CSV2 by `交易所 + 代码`.
5. Derive PE x PB, listing age, ROE five-year metrics, profit stability, cash-flow metrics, free-cash-flow totals, cash collection ratio, and dividend five-year fields where available.
6. Classify financial companies before ordinary scoring.
7. Score only non-financial companies into `A档_严格通过` and `B档_观察名单`.
8. Build `银行_候选池` from CSV1/CSV2 fields only.
9. Keep insurance, securities, and other financial companies in `金融_单独观察` unless bank-specific supplements are supplied.
10. Write the required workbook sheets and summary notes.

## Error Handling

- Missing optional fields become missing-rule notes rather than hard failures.
- Missing required input files or missing merge keys raise clear CLI errors.
- If enhanced PE/PB fields exist, they become the main valuation fields and the ordinary fields remain as references.
- If enhanced fields are absent, the output notes that ordinary PE-TTM and PB were used.

## Testing

Use standard-library `unittest` so the project does not require a test runner dependency. Tests cover numeric cleaning, code preservation, column mapping, financial classification, ordinary scoring, bank candidate tagging, and an end-to-end run against the two CSV files in the repository.

## Plan Self-Review

- No placeholder requirements remain.
- The design keeps financial companies out of ordinary-company scoring.
- The design uses the current CSV exports as the concrete acceptance sample.
- The design produces a reusable project, not a one-off notebook.
