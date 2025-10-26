import re, html, unicodedata
from urllib.parse import urlparse

WS_RE = re.compile(r"\s+", re.U)
NON_WORD = re.compile(r"[^\w\u3040-\u30ff\u4e00-\u9fff-]+")

def normalize_text(s: str) -> str:
    if not s: return ""
    s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    return WS_RE.sub(" ", s).strip()

def tokenize(s: str) -> list[str]:
    s = normalize_text(s).lower()
    s = NON_WORD.sub(" ", s)
    return [t for t in s.split() if t]

def jaccard(a: set, b: set) -> float:
    if not a or not b: return 0.0
    inter = len(a & b)
    if inter == 0: return 0.0
    return inter / len(a | b)

def host_of(u: str) -> str:
    try:
        return (urlparse(u).hostname or "").lower().lstrip("www.")
    except Exception:
        return ""
