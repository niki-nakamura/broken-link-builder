from .pipeline import run

if __name__ == "__main__":
    stats = run()
    print(f"SERP rows: {stats['serp_rows']}, Broken rows: {stats['broken_rows']}")
