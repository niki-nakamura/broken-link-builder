import requests, time, random
from urllib.parse import quote
from .config import (REQUEST_TIMEOUT, USER_AGENT, CDX_LIMIT_PER_QUERY, CC_LIMIT_PER_QUERY)
from .filter import early_url_keep

HEADERS = {"User-Agent": USER_AGENT}
FOOTPRINTS = [
    "links","resources","guide","glossary","dictionary","reference","faq","help",
    "blog","article","useful","まとめ","一覧","リンク集","おすすめ","用語集","事例","ケーススタディ"
]

def gen_url_patterns(q: str) -> list[str]:
    toks = [t for t in q.split("|") if t] if "|" in q else q.split()
    toks = [t.strip() for t in toks if t.strip()]
    patterns = set()
    for token in toks[:3]:
        for fp in FOOTPRINTS:
            patterns.add(f"*{token}*{fp}*")
            patterns.add(f"*{fp}*{token}*")
    # フットプリントのみも少量
    for fp in FOOTPRINTS[:6]:
        patterns.add(f"*{fp}*")
    return list(patterns)

def fetch_cdx(pattern: str, limit: int) -> list[str]:
    # Wayback CDX: url= にワイルドカードが使える
    base = "https://web.archive.org/cdx/search/cdx"
    params = f"url={quote(pattern, safe='*')}&output=json&fl=original&filter=statuscode:200&filter=mimetype:text/html&limit={limit}"
    url = f"{base}?{params}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        js = r.json()
        # fl=original の場合、各行が ["http..."] 形式
        urls = [row[0] for row in js if isinstance(row, list) and row]
        return urls
    except Exception:
        return []

def get_cc_indexes() -> list[str]:
    try:
        r = requests.get("https://index.commoncrawl.org/collinfo.json", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        info = r.json()
        # 新しいものから3個だけ叩く
        return [x.get("cdx-api") for x in info[:3] if x.get("cdx-api")]
    except Exception:
        return []

def fetch_cc(pattern: str, limit: int) -> list[str]:
    idx_urls = get_cc_indexes()
    out = []
    for idx in idx_urls:
        try:
            url = f"{idx}?url={quote(pattern, safe='*')}&output=json&limit={limit}"
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            # NDJSON 形式
            lines = [ln for ln in r.text.splitlines() if ln.strip()]
            for ln in lines:
                try:
                    rec = requests.json.loads(ln)  # requests.json は無いので修正
                except Exception:
                    import json
                    rec = json.loads(ln)
                orig = rec.get("url") or rec.get("original") or ""
                if orig:
                    out.append(orig)
        except Exception:
            continue
        time.sleep(0.15 + random.random()*0.2)
    return out

def discover_candidates_for_query(query: str, excluded_roots, excluded_hosts, excluded_urls, per_query_cap=200) -> list[str]:
    patterns = gen_url_patterns(query)
    pool = set()
    for p in patterns:
        for u in fetch_cdx(p, min(CDX_LIMIT_PER_QUERY, per_query_cap//2)):
            if early_url_keep(u, excluded_roots, excluded_hosts, excluded_urls):
                pool.add(u)
        # CC 側
        for u in fetch_cc(p, min(CC_LIMIT_PER_QUERY, per_query_cap//2)):
            if early_url_keep(u, excluded_roots, excluded_hosts, excluded_urls):
                pool.add(u)
        if len(pool) >= per_query_cap:
            break
    return list(pool)
