
import argparse
import sys
import subprocess
from datetime import datetime
from scripts.nhl_data_validator import NHLDataValidator
from scripts.generate_daily_projections import generate_daily
# from scripts.nhl_recommendation_engine import NHLRecEngine # Logic needs update to accept date?

def main():
    parser = argparse.ArgumentParser(description="NHL OPS CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # 1. INGEST
    p_ingest = subparsers.add_parser("ingest", help="Ingest Data")
    p_ingest.add_argument("--date_from", type=str, help="YYYY-MM-DD")
    p_ingest.add_argument("--date_to", type=str, help="YYYY-MM-DD")
    
    # 2. VALIDATE
    p_valid = subparsers.add_parser("validate", help="Run Integrity Gates")
    p_valid.add_argument("--mode", type=str, default="FULL")
    
    # 3. SCORE (Daily Projections)
    p_score = subparsers.add_parser("score", help="Run Daily Projections (Phases 1-4)")
    p_score.add_argument("--slate", type=str, help="YYYY-MM-DD", default=datetime.now().strftime('%Y-%m-%d'))
    
    # 4. RECOMMEND
    p_rec = subparsers.add_parser("recommend", help="Run Recommendation Engine (Phase 6)")
    # rec engine currently pulls *Live Odds* which imply "Today".
    # Supporting historical slate for Recs requires Historical Odds (Hard).
    # So Recs typically run for "Now".
    
    # 5. MONITOR
    p_mon = subparsers.add_parser("monitor", help="Run Monitoring Report")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        run_ingest(args)
    elif args.command == "validate":
        run_validate(args)
    elif args.command == "score":
        run_score(args)
    elif args.command == "recommend":
        run_recommend(args)
    elif args.command == "monitor":
        run_monitor(args)
    else:
        parser.print_help()

def run_ingest(args):
    print("📥 Running Ingestion...")
    # Call ingest scripts
    # For MVP, running the 'safe' history script.
    # Ideally pass dates. The script accepts optional args? No, hardcoded logic currently.
    # We should update ingest_nhl_history_safe.py to accept args if possible.
    # Assuming it pulls 'recent' by default.
    cmd = ["python3", "scripts/ingest_nhl_history_safe.py"]
    subprocess.check_call(cmd)
    
    # Goalies
    cmd = ["python3", "scripts/ingest_nhl_goalies.py"]
    subprocess.check_call(cmd)
    
    print("✅ Ingestion Complete.")

def run_validate(args):
    val = NHLDataValidator(mode=args.mode)
    if not val.run_all():
        print("❌ Integrity Gates Failed.")
        sys.exit(1)
    else:
        print("✅ Integrity Gates Passed.")

def run_score(args):
    print(f"⚡ Scoring Slate: {args.slate}")
    generate_daily(target_date=args.slate)

def run_recommend(args):
    print("💰 Running Recommendation Engine...")
    cmd = ["python3", "scripts/nhl_recommendation_engine.py"]
    subprocess.check_call(cmd)

def run_monitor(args):
    print("📊 Running Monitoring Report...")
    from scripts.nhl_monitoring import NHLMonitor
    mon = NHLMonitor()
    mon.run()

if __name__ == "__main__":
    main()
