from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from .utils import normalize_text

TAG_STRIP = re.compile(r"\s+")

def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return TAG_STRIP.sub(" ", text).strip()

def extract_anchors(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out=[]
    for a in soup.find_all("a"):
        href=a.get("href")
        if not href or href.startswith(("mailto:","tel:","javascript:","#")): continue
        abs_url=urljoin(base_url, href)
        t = TAG_STRIP.sub(" ", a.get_text(" ", strip=True)).strip()
        if not t: continue
        out.append({"href": abs_url, "text": t})
    return out

def count_terms(text: str, terms: list[str]) -> tuple[int, list[str]]:
    t = normalize_text(text)
    total=0; matched=[]
    for term in terms:
        if not term: continue
        c = t.count(term)
        if c>0: matched.append(f"{term}:{c}")
        total += c
    return total, matched

def any_term_in(text: str, terms: list[str]) -> bool:
    t = normalize_text(text)
    return any(term and term in t for term in terms)

def is_candidate_url(url: str, own_domain: str, domain_blocklist: list[str]) -> bool:
    try:
        u = urlparse(url)
        if u.scheme not in ("http","https"): return False
        host = u.hostname or ""
        # 外部のみ対象（自社は除外）
        if own_domain and own_domain in host: return False
        # 検索サイト・SNS・ブロック対象は除外
        if any(b in host for b in (domain_blocklist or [])): return False
        if "mojeek.com" in host or "duckduckgo.com" in host: return False
        return True
    except Exception:
        return False
