from bs4 import BeautifulSoup
import re

def find_anchors_for_query(html: str, query_terms: list[str]) -> list[tuple[str,str]]:
    """
    return: list of (href, anchor_text)
    """
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a"):
        txt = (a.get_text(" ", strip=True) or "")
        href = a.get("href") or ""
        if not href or not txt: continue
        if any(q in txt for q in query_terms):
            out.append((href, txt))
    return out

def text_only(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(" ", strip=True)
