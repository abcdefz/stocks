from __future__ import annotations

import argparse
import json
from pathlib import Path

from .portfolio import run_portfolio_engine


def _json_text(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Graham Portfolio Engine v1 and emit JSON.")
    parser.add_argument("csv1", help="LiXinger CSV1: current valuation and financial state")
    parser.add_argument("csv2", help="LiXinger CSV2: five-year history")
    parser.add_argument("--output", help="Output JSON path. Defaults to stdout.")
    args = parser.parse_args(argv)

    result = run_portfolio_engine(args.csv1, args.csv2)
    text = _json_text(result)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
