import re
from .fetcher import head_or_get_status

def is_soft_404(body: str, patterns: list[str]) -> bool:
    if not body:
        return False
    txt = body.lower()
    return any(p.lower() in txt for p in (patterns or []))

def check_link(session, url: str, timeout: int, soft404_patterns: list[str]):
    code, final_url, body = head_or_get_status(session, url, timeout)
    soft = (code == 200) and is_soft_404(body, soft404_patterns)
    is_broken = (code >= 400 and code != 429) or code == -1 or soft
    return {
        "code": code,
        "final_url": final_url,
        "is_broken": is_broken,
        "soft_404": soft,
        "note": "" if code != -1 else "fetch_error"
    }
