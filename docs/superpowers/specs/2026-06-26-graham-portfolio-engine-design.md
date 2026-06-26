# Graham Portfolio Engine v1 Design

## Goal

Add a parallel Graham-style portfolio engine without replacing the existing Excel screening workflow. The new engine reads the same two LiXinger CSV exports, applies simple hard filters, ranks surviving stocks by margin of safety, and returns executable JSON output for a long-term equal-weight portfolio.

This engine is intentionally not a research or optimization system. It does not run factor regression, machine learning, return prediction, statistical backtests, Sharpe optimization, or risk-model weighting.

## Relationship To Existing Screen

The existing `graham-screen` workflow remains the first-pass report generator. It writes `格雷厄姆第一版筛选结果.xlsx` with A/B/C tiers, bank candidate pools, financial observation sheets, and missing-field notes.

The portfolio engine is a separate output path:

- It reuses CSV loading, column normalization, numeric cleaning, metric derivation, and financial classification.
- It produces JSON instead of Excel.
- It does not change current A/B/C scoring rules.
- It may include banks in the JSON portfolio only under the simplified bank hard filter described here.
- Insurance, securities, and other financial companies remain excluded from the portfolio because they need industry-specific metrics.

## Inputs

The engine accepts the same two CSV files:

- CSV1: current valuation and financial-state export.
- CSV2: five-year historical financial export.

CSV1 is the left table. Rows that exist only in CSV2 are discarded. The merge key is `交易所 + 代码`, and stock codes remain strings.

## Industry Type

Reuse `financial_subtype()` and map the result to the portfolio engine types:

- `银行` -> `bank`
- `保险`, `证券`, `其他金融` -> `finance`
- `非金融` -> `non_financial`

The broader mapping prevents non-bank financial companies from being accidentally screened with ordinary-company rules.

## Hard Filter

Non-financial companies must pass all available required checks:

- `0 < PE-TTM <= 15`
- `0 < PB <= 1.5`
- `ROE5均 >= 8`
- `归母净利润5年全正 == True`
- `资产负债率 <= 60`
- `流动比率 >= 1.2`
- `经营现金流/净利润5年 >= 0.8`

Banks must pass all required checks:

- `0 < PB <= 1.0`
- `ROE5均 >= 8`
- `归母净利润5年全正 == True`
- `股息率 >= 4`

Rows with missing required fields fail the hard filter and include the missing fields in their reject reasons.

Finance rows that are not banks always fail for portfolio construction with a reason that industry-specific metrics are missing.

## Margin Of Safety

For rows that pass hard filters, compute MOS only for ranking:

```text
MOS = min(
  1 - (PE-TTM / 15) * 0.5,
  1 - (PB / 1.5) * 0.5
)
```

For banks, PE is optional for the hard filter. If bank PE is missing but PB exists, use the PB side as MOS. If neither PE nor PB can produce a MOS value, reject the row because it cannot be ranked.

MOS is not used as a pass/fail rule.

## Portfolio Construction

Sort all hard-filter survivors by MOS descending.

The portfolio size is fixed at 20. If fewer than 20 stocks pass, include all passing stocks in `portfolio`.

Rows ranked 21-40 go into `watchlist`.

Portfolio rows use equal weight. Weight is `1 / portfolio_count` when at least one stock is selected.

## JSON Output

The output object has exactly three top-level keys:

```json
{
  "portfolio": [],
  "watchlist": [],
  "reject": []
}
```

Portfolio and watchlist rows include:

- `代码`
- `交易所`
- `行业类型`
- `MOS值`
- `等权权重` for portfolio rows

Reject rows include:

- `代码`
- `交易所`
- `行业类型`
- `剔除原因`

Additional internal columns may be used for testing and sorting, but the public JSON remains concise.

## CLI

Add a separate command-line path rather than overloading the existing Excel screen:

- Module function: `run_portfolio_engine(csv1, csv2)`
- Console script: `graham-portfolio`
- Optional output file argument: `--output`; when omitted, write JSON to stdout.

## Testing

Add focused tests for:

- Non-financial hard-filter pass and reject reasons.
- Bank hard-filter pass without ordinary debt, liquidity, or cash-flow rules.
- Insurance, securities, and other financial companies always entering reject.
- MOS sorting and portfolio/watchlist boundaries.
- Equal weights and stable code strings.
- CLI JSON output.

## Self-Review

The design keeps the existing workbook screen intact, makes the new engine a separate executable path, preserves the project rule that non-bank financial firms are not ordinary-company scored, and explicitly documents the narrower bank rule exception requested by the portfolio engine prompt.
