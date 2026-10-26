"""Command-line entry point.

Examples
    python run_pipeline.py --sample                     # offline demo, no internet needed
    python run_pipeline.py                              # real API, incremental
    python run_pipeline.py --start 2026-09-01 --end 2026-09-30   # backfill a range
"""
import argparse
import logging
import sys
from datetime import date

from pipeline.run import run


def main() -> int:
    parser = argparse.ArgumentParser(description="Azerbaijan weather ELT pipeline")
    parser.add_argument("--sample", action="store_true",
                        help="use generated sample data instead of calling the API")
    parser.add_argument("--start", type=date.fromisoformat,
                        help="backfill start date YYYY-MM-DD (overrides the watermark)")
    parser.add_argument("--end", type=date.fromisoformat,
                        help="end date YYYY-MM-DD (default: today minus archive lag)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-5s  %(message)s",
                        datefmt="%H:%M:%S")
    try:
        summary = run(sample=args.sample, start=args.start, end=args.end)
    except Exception:
        return 1
    print(f"\nRun {summary['run_id']} finished: {summary['rows_bronze']} raw rows, "
          f"{summary['rows_silver']} silver rows, {summary['rows_gold']} gold rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
