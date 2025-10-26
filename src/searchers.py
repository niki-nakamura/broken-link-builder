import os, re, json, time, random, requests
from .sheets import read_catalog

UA = os.getenv("BLB_UA", "BLB/1.0 (contact: you@example.com)")
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "12"))
CC_INDEX = os.getenv("CC_INDEX", "CC-MAIN-2024-33-index")

def _norm_terms(qpipe: str) -> list[str]:
    # "A|B|C" 形式から、英数・日本語を含むトークン候補を抽出
    terms = []
    for t in (qpipe or "").split("|"):
        t = t.strip()
        if not t: continue
        # URL に載りやすいトークンのみ（空白・記号を削る）
        t = re.sub(r"[^\w\-/\u3040-\u30ff\u4e00-\u9fff]+", "", t.lower())
        if len(t) >= 2:
            terms.append(t)
    return list(dict.fromkeys(terms))[:5]  # 過剰膨張を抑制

def _cc_query(term: str, limit=10) -> list[str]:
    u = f"https://index.commoncrawl.org/{CC_INDEX}"
    p = {"url": f"*{term}*", "output": "json", "limit": str(limit)}
    r = requests.get(u, params=p, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    urls = []
    for line in r.text.splitlines():
        try:
            j = json.loads(line)
            u = j.get("url") or j.get("urlkey")
            if u and u.startswith("http"):
                urls.append(u)
        except Exception:
            pass
    return urls

def _cdx_query(term: str, limit=10) -> list[str]:
    u = "https://web.archive.org/cdx/search/cdx"
    p = {"url": f"*{term}*", "output": "json", "filter": "statuscode:200", "limit": str(limit)}
    r = requests.get(u, params=p, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    js = r.json()
    # 先頭はヘッダー行、以降は [urlkey, timestamp, original, mimetype, statuscode, digest, length]
    urls = []
    for row in js[1:]:
        if len(row) >= 3 and row[2].startswith("http"):
            urls.append(row[2])
    return urls

def discover_candidates(max_queries=50, topk=10) -> list[str]:
    # 「カタログ」から上位 max_queries 件のクエリ行を読み、各行から URL を少量ずつ取得
    cat = read_catalog()
    urls: list[str] = []
    for i, row in enumerate(cat[:max_queries]):
        qpipe = row[0] if row else ""
        terms = _norm_terms(qpipe)
        pool = set()
        for t in terms:
            # CC と CDX から少しずつ
            try:
                pool.update(_cc_query(t, limit=5))
            except Exception:
                pass
            time.sleep(0.2 + random.random()*0.3)
            try:
                pool.update(_cdx_query(t, limit=5))
            except Exception:
                pass
            time.sleep(0.2 + random.random()*0.3)
            if len(pool) >= topk * 2:
                break
        # そのクエリでの候補を最大 topk 件に絞る
        urls.extend(list(pool)[:topk])
        if len(urls) >= max_queries * topk:
            break
    # 全体を去重
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out
