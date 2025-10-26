import requests
from .config import REQUEST_TIMEOUT, USER_AGENT

HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"}

def head(url: str):
    try:
        r = requests.head(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return r.status_code, r.headers.get("Content-Type","")
    except Exception:
        return -1, ""

def get_html(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        ct = r.headers.get("Content-Type","")
        return r.status_code, ct, (r.text if "html" in ct.lower() else "")
    except Exception:
        return -1, "", ""
