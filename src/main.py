import argparse
from .pipeline import run

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--discover", action="store_true")
    p.add_argument("--scan", action="store_true")
    p.add_argument("--suggest", action="store_true")
    p.add_argument("--time-budget-min", type=int, default=180)
    args = p.parse_args()

    # フラグ未指定ならフル実行
    d = args.discover or (not args.scan and not args.suggest)
    s = args.scan     or (not args.discover and not args.suggest)
    g = args.suggest  or (not args.discover and not args.scan)

    run(d, s, g, args.time_budget_min)

if __name__ == "__main__":
    main()
