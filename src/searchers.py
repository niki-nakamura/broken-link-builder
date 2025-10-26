import os, json, requests, random, time
from typing import List
from .sheets import read_catalog

UA = os.getenv("BLB_UA", "BLB/1.0 (contact: you@example.com)")
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "12"))
CC_INDEX = os.getenv("CC_INDEX", "CC-MAIN-2024-33-index")

def _json_lines(text: str):
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        try:
            yield json.loads(line)
        except Exception:
            continue

def _cc_query(pattern: str, limit: int) -> List[str]:
    """Common Crawl Index (CDX互換) から https のURLを返す（最少件）。"""
    u = f"https://index.commoncrawl.org/{CC_INDEX}"
    p = {"url": pattern, "output": "json", "limit": str(limit)}
    r = requests.get(u, params=p, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    urls = []
    for obj in _json_lines(r.text):
        url = obj.get("url") or ""
        if url.startswith("https://"):
            urls.append(url)
    return urls

def discover_candidates(sh, max_queries: int = 50, topk: int = 10) -> List[str]:
    """カタログからクエリを取り出し、CC Indexで候補URLを少量ずつ収集（PoC）。"""
    rows = read_catalog(sh)
    urls: List[str] = []
    # シンプルに日本語ヒントありのものを優先しつつ、上位 max_queries 件だけ使う
    qs = []
    for r in rows[:max_queries]:
        qpipe = (r[0] or "").strip()  # queries_top10_pipe
        if not qpipe: continue
        # 1クエリにつき代表トークン3つ程度をワイルドカード検索
        tokens = [t for t in qpipe.split("|") if t.strip()]
        tokens = tokens[:3]
        for t in tokens:
            # 日本語が含まれていれば jp を優先して *.jp/* を叩く
            patt = "*.jp/*" if any(ord(ch) > 127 for ch in t) else "*/*"
            # 少量に制限（API礼儀）
            urls.extend(_cc_query(patt, limit=min(topk, 3)))
            time.sleep(0.3)  # 優しめに
    # 去重
    seen, dedup = set(), []
    for u in urls:
        if u in seen: continue
        seen.add(u); dedup.append(u)
    return dedup
