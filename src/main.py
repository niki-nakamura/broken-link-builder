import argparse
from .pipeline import run

def main():
    p = argparse.ArgumentParser(description="Broken Link Builder (BLB)")
    p.add_argument("--discover", action="store_true", help="Discovery phase (CDX/CC → TopK)")
    p.add_argument("--scan", action="store_true", help="Broken link scan (404/soft404)")
    p.add_argument("--suggest", action="store_true", help="Suggest replacement URL")
    p.add_argument("--time-budget-min", type=int, default=30)
    args = p.parse_args()
    run(args.discover, args.scan, args.suggest, args.time_budget_min)

if __name__ == "__main__":
    main()
