import re
import time
import unicodedata
from contextlib import contextmanager

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    try:
        s = unicodedata.normalize("NFKC", s)
    except Exception:
        pass
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_terms(pipe: str) -> list[str]:
    return [normalize_text(x).strip() for x in (pipe or "").split("|") if normalize_text(x).strip()]

@contextmanager
def rate_limit(sleep_ms: int):
    try:
        yield
    finally:
        if sleep_ms and sleep_ms > 0:
            time.sleep(sleep_ms / 1000.0)
