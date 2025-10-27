import os, json, time, random, requests, re
from typing import List
from .sheets import read_catalog

UA = os.getenv("BLB_UA", "BLB/1.0 (+contact: you@example.com)")
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "12"))
CC_INDEX = os.getenv("CC_INDEX", "CC-MAIN-2024-33-index")

def _json_lines(text: str):
    for line in text.splitlines():
        line=line.strip()
        if not line: continue
        try:
            yield json.loads(line)
        except Exception:
            continue

def _cc_query(pattern: str, limit: int) -> List[str]:
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

def _cdx_query(pattern: str, limit: int) -> List[str]:
    # Wayback CDX はレート・フィルタ厳しめ。UA を明示し、失敗時は空配列
    try:
        u = "https://web.archive.org/cdx/search/cdx"
        p = {"url": pattern, "output": "json", "filter":"statuscode:200", "limit": str(limit)}
        r = requests.get(u, params=p, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        rows = r.json()[1:]  # 先頭はヘッダ
        out = []
        for c in rows:
            # c[2]=original URL
            if len(c) > 2 and str(c[2]).startswith("https://"):
                out.append(c[2])
        return out
    except Exception:
        return []

def _terms(qpipe: str) -> list[str]:
    ts = []
    for t in (qpipe or "").split("|"):
        t = t.strip()
        if not t: continue
        ts.append(t)
    return ts

def _pattern_for(t: str) -> str:
    # 日本語を含むタイトルはパスに現れるケースが少ないため広めに
    # *.jp/* をベースに、トークンを含む URL を拾う
    safe = re.sub(r'\s+', '-', t)
    return f"*.jp/*{safe}*"

def discover_candidates(sh, max_queries=200, topk=10, per_query_limit=20) -> list[tuple[str,str,str]]:
    """
    return: list of (page_url, title_placeholder, source_query)
    title_placeholder は空でOK（後段で取得）
    """
    rows = read_catalog(sh)
    out = []
    for r in rows[:max_queries]:
        qpipe, self_url = r[0], r[1]
        for t in _terms(qpipe):
            pat = _pattern_for(t)
            cc = _cc_query(pat, min(per_query_limit, 10))
            cdx = _cdx_query(pat, min(per_query_limit, 10))
            urls = list(dict.fromkeys(cc + cdx))  # de-dup keep order
            # 早期 HTTP 前フィルタは pipeline 側で実施
            for u in urls[:topk]:
                out.append((u, "", t))
        # polite
        time.sleep(0.7 + random.random()*0.3)
    return out
