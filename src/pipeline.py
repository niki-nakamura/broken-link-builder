import time
from .sheets import open_book, read_catalog, read_excluded, append_candidates, append_results

def run(discover: bool, scan: bool, suggest: bool, time_budget_min: int):
    t0 = time.time()
    print(f"[BLB] start (budget={time_budget_min} min)")

    # 0) 接続テスト
    sh = open_book()
    print(f"[BLB] opened: {sh.title}")

    # 1) カタログ A列テスト読込
    queries = read_catalog(sh)
    print(f"[BLB] loaded queries: {len(queries)} (sample: {queries[:3]})")

    # 2) 対象外シート（任意）
    roots, hosts, urls = read_excluded(sh)
    print(f"[BLB] excluded: roots={len(roots)}, hosts={len(hosts)}, urls={len(urls)}")

    # 3) 動作確認としてダミー1行を書き込む（※後で消してOK）
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    append_candidates(sh, [["https://example.com", "Example", "DUMMY", now]])
    append_results(sh, [["https://example.com/page", "https://example.com/broken", "anchor", "404", "0", "https://example.com/fix", "0.50"]])
    print("[BLB] wrote 1 row to 候補URL & 検査結果 (dummy)")

    print(f"[BLB] done in {time.time()-t0:.1f}s")
