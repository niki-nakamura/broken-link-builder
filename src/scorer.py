from .utils import tokenize, jaccard

def serp_like_score(query: str, page_title: str, heads: list[str], body: str, path_hint: str="") -> float:
    qtok = set(tokenize(query))
    ttok = set(tokenize(page_title))
    htok = set()
    for h in heads:
        htok |= set(tokenize(h))
    btok = set(tokenize(body))  # 軽め

    match_core = jaccard(qtok, ttok | htok) * 2.0 + jaccard(qtok, btok) * 1.0
    path_bonus = 0.0
    for kw in ["guide","glossary","dictionary","resources","links","blog","用語集","リンク集","一覧","おすすめ"]:
        if kw in path_hint.lower():
            path_bonus += 0.5
    # 係数は軽め
    return match_core + path_bonus
