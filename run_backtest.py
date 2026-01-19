#!/usr/bin/env python3
"""
Run Backtest

Standalone script to run historical performance analysis.
"""

import sys
from datetime import datetime, timedelta
from backtesting import run_backtest, print_backtest_report

def main():
    """Run backtest and print results."""
    print("\n" + "="*80)
    print("📊 RUNNING BACKTEST")
    print("="*80 + "\n")

    # Default: last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Check command line arguments
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
        start_date = end_date - timedelta(days=days)
        print(f"Analyzing last {days} days\n")
    else:
        print("Analyzing last 30 days (use: python run_backtest.py <days>)\n")

    # Run backtest
    results = run_backtest(start_date=start_date, end_date=end_date)

    if not results:
        print("❌ No data found for backtest")
        sys.exit(1)

    # Print formatted report
    print_backtest_report(results)

    # Save results to file
    import json
    from datetime import datetime

    filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Convert numpy types to native Python for JSON serialization
    def convert_to_json_serializable(obj):
        if isinstance(obj, dict):
            return {k: convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_json_serializable(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy types
            return obj.item()
        elif hasattr(obj, 'tolist'):  # numpy arrays
            return obj.tolist()
        else:
            return obj

    results_serializable = convert_to_json_serializable(results)

    with open(filename, 'w') as f:
        json.dump(results_serializable, f, indent=2)

    print(f"\n💾 Results saved to {filename}")

if __name__ == "__main__":
    main()
