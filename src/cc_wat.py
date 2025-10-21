import io, gzip, json, time
from urllib.parse import urlparse, urljoin
import requests
from .utils import normalize_text

def _fetch_wat_paths(crawl_id: str) -> list[str]:
    base = f"https://data.commoncrawl.org/crawl-data/{crawl_id}/wat.paths.gz"
    r = requests.get(base, timeout=60)
    r.raise_for_status()
    data = gzip.decompress(r.content).decode("utf-8").splitlines()
    return [f"https://data.commoncrawl.org/{p}" for p in data]

def _host_endswith(url: str, tld: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        return host.endswith(tld)
    except Exception:
        return False

def _bad_path(url: str, excludes: list[str]) -> bool:
    u = urlparse(url)
    p = (u.path or "") + (("?" + u.query) if u.query else "")
    return any(sub in p for sub in (excludes or []))

def _iter_outlinks_from_wat(session: requests.Session, wat_url: str, terms: list[str],
                            tld_filter: str | None, max_yield: int, timeout: int,
                            min_anchor_chars: int, min_terms_matched: int,
                            path_excludes: list[str]):
    with session.get(wat_url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        gz = gzip.GzipFile(fileobj=resp.raw)
        yielded = 0
        for line in gz:
            if yielded >= max_yield:
                return
            try:
                rec = json.loads(line)
                env = rec.get("Envelope", {})
                src = env.get("WARC-Header-Metadata", {}).get("WARC-Target-URI")
                if not src:
                    continue
                if tld_filter and not _host_endswith(src, tld_filter):
                    continue
                links = (env.get("Payload-Metadata", {})
                           .get("HTTP-Response-Metadata", {})
                           .get("HTML-Metadata", {})
                           .get("Links", []))
                if not links:
                    continue
                src_host = (urlparse(src).hostname or "")
                for lk in links:
                    raw = lk.get("url") or lk.get("href")
                    text = (lk.get("text") or "").strip()
                    if not raw or not text:
                        continue
                    if len(text) < min_anchor_chars:
                        continue
                    abs_url = urljoin(src, raw)
                    if not abs_url.startswith(("http://","https://")):
                        continue
                    # 内部リンクは除外（外部だけ）
                    if (urlparse(abs_url).hostname or "") == src_host:
                        continue
                    if _bad_path(abs_url, path_excludes):
                        continue
                    tnorm = normalize_text(text)
                    matched = sum(1 for t in terms if t and t in tnorm)
                    if matched < min_terms_matched:
                        continue
                    yielded += 1
                    yield {"source_url": src, "anchor_text": text, "link_url": abs_url}
                    if yielded >= max_yield:
                        return
            except Exception:
                continue

def find_candidates_from_commoncrawl(session, terms: list[str], conf: dict) -> list[dict]:
    cc = conf.get("cc", {}) or {}
    crawl_id = cc.get("crawl_id", "")
    if not crawl_id:
        return []
    paths = _fetch_wat_paths(crawl_id)
    stride = max(1, int(cc.get("wat_stride", 4000)))
    max_files = int(cc.get("max_wat_files", 20))
    tld = cc.get("tld_filter") or None
    per_file = int(cc.get("outlinks_per_file", 200))
    min_anchor_chars = int(cc.get("min_anchor_chars", 6))
    min_terms_matched = int(cc.get("min_terms_matched", 1))
    path_excludes = cc.get("path_exclude_substrings", [])

    results = []
    timeout = conf.get("timeout_seconds", 30)
    sleep_ms = conf.get("sleep_ms_between_fetches", 0)
    picked = paths[::stride][:max_files]

    for wat_url in picked:
        try:
            for item in _iter_outlinks_from_wat(session, wat_url, terms, tld, per_file, timeout,
                                                min_anchor_chars, min_terms_matched, path_excludes):
                results.append(item)
                if len(results) >= conf.get("results_per_query", 30):
                    return results
        except Exception:
            pass
        if sleep_ms:
            time.sleep(sleep_ms/1000.0)
    return results
