import difflib

def fit_score(anchor_text: str, catalog_title: str) -> float:
    # 文字列類似度（0..1）
    return difflib.SequenceMatcher(None, anchor_text, catalog_title).ratio()
