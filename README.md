# A-share Graham Screen

This project runs an A-share Graham-style first-pass quantitative screen from two LiXinger CSV exports.

It separates ordinary non-financial companies from financial companies before scoring. Ordinary companies can enter `A档_严格通过` or `B档_观察名单`; banks only enter a candidate pool unless bank-specific metrics are supplied; insurance and securities companies stay in separate observation output.

## Inputs

The normal workflow uses two CSV files:

- CSV1: current valuation and financial-state export.
- CSV2: five-year history export.

The merge key is `交易所 + 代码`. CSV1 is used as the left table, so CSV2-only rows are discarded.

## Run

```bash
uv run graham-screen \
  公司筛选_格雷厄姆CSV1_20260622_212016.csv \
  公司筛选_格雷厄姆CSV2_20260622_212026.csv \
  --output 格雷厄姆第一版筛选结果.xlsx
```

## Test

```bash
uv run python -m unittest discover -s tests -v
```

## Output

The workbook includes:

- `说明`
- `A档_严格通过`
- `B档_观察名单`
- `银行_候选池`
- `金融_单独观察`
- `全部评分`
- `剔除名单`
- `缺失字段`

`银行_深度观察` is only appropriate after supplementing bank-specific metrics such as 不良贷款率、拨备覆盖率、拨贷比、核心一级资本充足率、资本充足率、净息差.

The result is a quantitative first-pass screen, not investment advice.
