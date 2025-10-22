import csv, os, yaml, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from collections import defaultdict, Counter
from datetime import datetime

from .fetcher import make_session, get_text
from .parser import extract_visible_text, extract_anchors, count_terms, any_term_in, is_candidate_url
from .checker import check_link
from .searchers import search_duckduckgo_lite, search_mojeek, search_auto
from .utils import split_terms, rate_limit
from .sheets import read_catalog_from_sheet, write_table
from .cc_wat import find_candidates_from_commoncrawl

# ----------- runtime controls -----------
VERBOSE      = int(os.environ.get("VERBOSE", "0"))
ROWS_LIMIT   = int(os.environ.get("ROWS_LIMIT", "0"))  # 0=all
ROWS_START   = int(os.environ.get("ROWS_START", "1"))  # 1-indexed
FLUSH_EVERY  = int(os.environ.get("FLUSH_EVERY", "5"))
RESET_STATE  = int(os.environ.get("RESET_STATE", "0"))
STATE_PATH   = "outputs/state.json"

def log(msg): 
    if VERBOSE: 
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    conf.setdefault("timeout_seconds", 30)
    conf.setdefault("results_per_query", 20)
    conf.setdefault("min_occurrences", 2)
    conf.setdefault("sleep_ms_between_fetches", 1500)
    conf.setdefault("user_agent", "BrokenLinkCI/0.1")
    conf.setdefault("domain_blocklist", [])
    conf.setdefault("own_domain", "digi-mado.jp")
    conf.setdefault("search_engine", "duckduckgo_lite")
    conf.setdefault("max_workers", 4)
    conf.setdefault("source_mode", "auto")
    conf.setdefault("cc", {})
    '
    # ---- ENV overrides (so we can tweak from Actions inputs) ----
    env_map = {
        "SOURCE_MODE": ("source_mode", str),
        "SEARCH_ENGINE": ("search_engine", str),
        "RESULTS_PER_QUERY": ("results_per_query", int),
        "MIN_OCCURRENCES": ("min_occurrences", int),
    }
    for k,(ck,cast) in env_map.items():
        v=os.environ.get(k)
        if v: conf[ck]=cast(v)

    cc = conf.setdefault("cc", {})
    cc_map = {
        "CC_CRAWL_ID": ("crawl_id", str),
        "CC_MAX_WAT_FILES": ("max_wat_files", int),
        "CC_WAT_STRIDE": ("wat_stride", int),
        "CC_TLD_FILTER": ("tld_filter", str),
        "CC_OUTLINKS_PER_FILE": ("outlinks_per_file", int),
        "CC_MIN_ANCHOR_CHARS": ("min_anchor_chars", int),
        "CC_MIN_TERMS_MATCHED": ("min_terms_matched", int),
    }
    for k,(ck,cast) in cc_map.items():
        v=os.environ.get(k)
        if v is not None:
            if ck=="tld_filter" and v.lower() in ("", "none", "null"):
                cc[ck] = ""
            else:
                cc[ck]=cast(v)
    return conf
'

def _read_catalog():
    rows = read_catalog_from_sheet()
    if rows: return rows
    path = "catalog.csv"
    if not os.path.exists(path): return []
    out=[]
    with open(path, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            q = (r.get("queries_top10_pipe") or "").strip()
            repl = (r.get("url") or r.get("replacement_url") or "").strip()
            if q: out.append({"queries_top10_pipe": q, "replacement_url": repl})
    return out

def _append_csv(path, rows, header):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(header)
        for r in rows: w.writerow(r)

def run(conf_path="config.yaml"):
    conf = load_config(conf_path)
    session = make_session(conf["timeout_seconds"], conf.get("user_agent"))
    catalog_rows = _read_catalog()
    total = len(catalog_rows)
    ts_now = datetime.utcnow().isoformat()

    # resume
    start_from = ROWS_START
    if not RESET_STATE and ROWS_START <= 1 and os.path.exists(STATE_PATH):
        try:
            state = json.load(open(STATE_PATH, "r", encoding="utf-8"))
            start_from = max(1, int(state.get("last_idx", 0)) + 1)
        except Exception:
            start_from = 1

    log(f"Start: rows={total}, from={start_from}, limit={ROWS_LIMIT or 'all'}, mode={conf.get('source_mode')}, engine={conf.get('search_engine')}")

    serp_rows = []
    broken_rows = []
    cc_debug_rows = []
    report_counter = Counter()
    per_source_broken = defaultdict(list)

    def flush_outputs():
        # CSV
        if serp_rows:
            _append_csv("outputs/serp.csv", serp_rows, ["timestamp","engine","query","rank","title","url"])
        if broken_rows:
            _append_csv("outputs/broken_links.csv", broken_rows,
                        ["timestamp","source_url","source_title","matched_terms","matched_count","anchor_text",
                         "broken_link_url","status","soft_404","replacement_url","note"])
        # Sheet
        if os.environ.get("GOOGLE_SHEET_ID"):
            if serp_rows:
                write_table("結果_SERP", ["timestamp","engine","query","rank","title","url"], serp_rows, clear=True)
            if broken_rows:
                write_table("結果_BrokenLinks",
                            ["timestamp","source_url","source_title","matched_terms","matched_count","anchor_text",
                             "broken_link_url","status","soft_404","replacement_url","note"],
                            broken_rows, clear=True)
            if cc_debug_rows:
                write_table("結果_CC候補",
                            ["source_url","source_host","anchor_text","link_url","link_host"],
                            cc_debug_rows[:1000], clear=True)

    def save_state(idx):
        os.makedirs("outputs", exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({"last_idx": idx, "utc": datetime.utcnow().isoformat()}, f)

    try:
        for idx, row in enumerate(catalog_rows, start=1):
            if idx < start_from: 
                continue
            if ROWS_LIMIT and (idx - start_from + 1) > ROWS_LIMIT:
                break

            terms = split_terms(row["queries_top10_pipe"])
            if not terms: 
                save_state(idx); 
                continue

            log(f"Row {idx}/{total}: q='{terms[0]}'")

            # --- Common Crawl route ---
            cc_done = False
            if conf.get("source_mode") in ("commoncrawl","auto"):
                cc_items = find_candidates_from_commoncrawl(session, terms, conf)
                log(f"  CC candidates: {len(cc_items)}")

                # keep CC candidates for visibility
                for it in cc_items[:300]:
                    src_h = urlparse(it["source_url"]).hostname or ""
                    dst_h = urlparse(it["link_url"]).hostname or ""
                    cc_debug_rows.append([it["source_url"], src_h, it["anchor_text"], it["link_url"], dst_h])

                # body relevance gate
                filtered_items = []
                for it in cc_items:
                    status, final_src, html = get_text(session, it["source_url"], conf["timeout_seconds"])
                    if status >= 400 or not html:
                        continue
                    text = extract_visible_text(html)
                    total_hits, matched_terms = count_terms(text, terms)
                    if total_hits < conf["min_occurrences"]:
                        continue
                    filtered_items.append((it, final_src, matched_terms, total_hits))
                log(f"  CC filtered_on_body: {len(filtered_items)}")

                if filtered_items:
                    with ThreadPoolExecutor(max_workers=conf.get("max_workers", 3)) as ex:
                        futs = { ex.submit(check_link, session, it["link_url"], conf["timeout_seconds"], conf.get("soft404_patterns", [])):
                                 (it, final_src, matched_terms, total_hits)
                                 for (it, final_src, matched_terms, total_hits) in filtered_items }
                        for fut in as_completed(futs):
                            it, final_src, matched_terms, total_hits = futs[fut]
                            try:
                                st = fut.result()
                            except Exception as e:
                                st = {"code": -1, "final_url": it["link_url"], "is_broken": True, "soft_404": False, "note": str(e)}
                            if st["is_broken"]:
                                broken_rows.append([
                                    ts_now, final_src, "",
                                    "|".join(matched_terms), total_hits,
                                    it["anchor_text"], st["final_url"], st["code"],
                                    "YES" if st["soft_404"] else "",
                                    row.get("replacement_url",""), st.get("note","")
                                ])
                                host = (urlparse(final_src).hostname or "")
                                report_counter[host] += 1
                                per_source_broken[final_src].append({
                                    "anchor_text": it["anchor_text"], "broken_url": st["final_url"],
                                    "status": st["code"], "soft404": st["soft_404"]
                                })
                    cc_done = True

            if cc_done and conf.get("source_mode")=="auto":
                save_state(idx)
                if (idx - start_from + 1) % FLUSH_EVERY == 0:
                    log("  flushing outputs...")
                    flush_outputs()
                continue

            # --- SERP route ---
            if conf.get("source_mode")!="commoncrawl":
                if conf.get("search_engine") == "duckduckgo_lite":
                    candidates = search_duckduckgo_lite(session, terms[0], conf["results_per_query"], conf)
                elif conf.get("search_engine") == "mojeek":
                    candidates = search_mojeek(session, terms[0], conf["results_per_query"], conf)
                else:
                    candidates = search_auto(session, terms[0], conf["results_per_query"], conf)

                for i, r in enumerate(candidates, start=1):
                    serp_rows.append([ts_now, conf.get("search_engine","duckduckgo_lite"), terms[0], i, r.get("title",""), r["url"]])

                for r in candidates:
                    if not is_candidate_url(r["url"], conf["own_domain"], conf.get("domain_blocklist", [])):
                        continue
                    with rate_limit(conf.get("sleep_ms_between_fetches", 0)):
                        status, final_url, html = get_text(session, r["url"], conf["timeout_seconds"])
                    if status >= 400 or not html: continue

                    text = extract_visible_text(html)
                    total_hits, matched_terms = count_terms(text, terms)
                    if total_hits < conf["min_occurrences"]: continue

                    anchors = [a for a in extract_anchors(html, final_url) if any_term_in(a["text"], terms)]
                    if not anchors: continue

                    with ThreadPoolExecutor(max_workers=conf.get("max_workers", 3)) as ex:
                        futs = { ex.submit(check_link, session, a["href"], conf["timeout_seconds"], conf.get("soft404_patterns", [])): a for a in anchors }
                        for fut in as_completed(futs):
                            a = futs[fut]
                            try:
                                st = fut.result()
                            except Exception as e:
                                st = {"code": -1, "final_url": a["href"], "is_broken": True, "soft_404": False, "note": str(e)}
                            if st["is_broken"]:
                                broken_rows.append([
                                    ts_now, final_url, r.get("title",""),
                                    "|".join(matched_terms), total_hits,
                                    a["text"], st["final_url"], st["code"],
                                    "YES" if st["soft_404"] else "",
                                    row.get("replacement_url",""), st.get("note","")
                                ])
                                host = (urlparse(final_url).hostname or "")
                                report_counter[host] += 1
                                per_source_broken[final_url].append({
                                    "anchor_text": a["text"], "broken_url": st["final_url"],
                                    "status": st["code"], "soft404": st["soft_404"]
                                })

            save_state(idx)
            if (idx - start_from + 1) % FLUSH_EVERY == 0:
                log("  flushing outputs...")
                flush_outputs()

    except KeyboardInterrupt:
        log("Interrupted by user. Flushing & saving state...")

    # final flush
    flush_outputs()
    return {"serp_rows": len(serp_rows), "broken_rows": len(broken_rows)}
