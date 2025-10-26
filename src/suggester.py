from .utils import tokenize, jaccard, normalize_text

def suggest_replacement(anchor_text: str, page_title: str, catalog_rows: list[dict]) -> tuple[str, float]:
    """Catalogの (url, title, queries) から最も近いものを返す（URL, fit_score）"""
    a = set(tokenize(anchor_text + " " + page_title))
    best = ("", 0.0)
    for row in catalog_rows:
        title = normalize_text(row.get("title",""))
        queries = normalize_text(row.get("queries_top10_pipe","").replace("|"," "))
        b = set(tokenize(title + " " + queries))
        score = jaccard(a, b)
        if score > best[1]:
            best = (row.get("url",""), score)
    return best
