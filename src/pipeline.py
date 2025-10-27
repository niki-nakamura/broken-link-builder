import os, time, urllib.parse
from .sheets import open_sheet, read_catalog, append_candidates, append_results, write_exclusion_log, utcnow
from .searchers import discover_candidates
from .filter import pre_http_filter, post_http_filter, soft404_text
from .fetcher import fetch_many, fetch_head
from .parser import find_anchors_for_query, text_only
from .scorer import fit_score

TOPK = int(os.getenv("TOPK_PER_QUERY","10"))
MAX_QUERIES = int(os.getenv("MAX_QUERIES","200"))
PER_DOMAIN_MAX_PER_QUERY = int(os.getenv("PER_DOMAIN_MAX_PER_QUERY","1"))

def _host(u: str) -> str:
    return urllib.parse.urlparse(u).netloc

def run():
    t0 = time.time()
    sh = open_sheet()
    cat = read_catalog(sh)  # A:G
    now = utcnow()

    # --- Discover (CC/CDX)
    discovered = []
    per_host = {}
    for page_url, title, source_query in discover_candidates(sh, MAX_QUERIES, TOPK):
        ok, reason = pre_http_filter(page_url)
        if not ok:
            continue
        h = _host(page_url)
        if per_host.get((source_query, h), 0) >= PER_DOMAIN_MAX_PER_QUERY:
            continue
        per_host[(source_query, h)] = per_host.get((source_query, h), 0) + 1
        discovered.append((page_url, title, source_query, now))

    append_candidates(sh, discovered)

    # --- Fetch
    fetched = fetch_many([d[0] for d in discovered], limit= len(discovered))

    # --- Post-HTTP filter and 404 scan
    exclusion_rows = []
    result_rows = []

    # catalog lookup: query -> (self_url, self_title)
    q2self = {}
    for r in cat[:MAX_QUERIES]:
        qpipe, self_url, self_title = r[0], r[1], r[2]
        for q in (qpipe or "").split("|"):
            q2self[q] = (self_url, self_title)

    for (url, status, ct, html) in fetched:
        ok, reason, penalties = post_http_filter(url, html, ct, status)
        if not ok:
            exclusion_rows.append([url, "", "", reason, now])
            continue

        # アンカー抽出（このページの source_query は discovered から逆引き）
        qs = [d[2] for d in discovered if d[0] == url]
        if not qs:  # 安全策
            continue
        anchors = find_anchors_for_query(html, qs)

        # 外部リンクのみ対象
        page_host = _host(url)
        targets = []
        for href, atext in anchors:
            if href.startswith("//"): href = "https:" + href
            if href.startswith("/"):  href = f"https://{page_host}{href}"
            if not href.startswith("http"): continue
            if _host(href) == page_host: continue
            targets.append((href, atext))

        # 先に HEAD（安い）で 404/410 を拾う → 不明なら GET して soft404
        for href, atext in targets:
            try:
                _, st, ctype = fetch_head(href)
            except Exception:
                st, ctype = 0, ""
            is_soft = False
            if st in (404, 410):
                pass
            else:
                # GET して soft404 チェック（軽量パス）
                try:
                    from .fetcher import fetch
                    _, st2, ct2, html2 = fetch(href)
                    st = st or st2
                    ctype = ctype or ct2
                    if str(ctype).lower().startswith("text/html"):
                        is_soft = soft404_text(text_only(html2))
                except Exception:
                    continue

            if st in (404, 410) or is_soft:
                # 該当クエリの自社記事を代替に
                # （同一ページに複数クエリが当たる場合は最初のものを採用）
                self_url, self_title = q2self.get(qs[0], ("", ""))
                score = fit_score(atext, self_title or "")
                result_rows.append([
                    url,
                    href,
                    atext,
                    str(st or 0),
                    "1" if is_soft else "0",
                    self_url,
                    f"{score:.2f}"
                ])

    if exclusion_rows:
        write_exclusion_log(sh, exclusion_rows)
    if result_rows:
        append_results(sh, result_rows)
