import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from charset_normalizer import from_bytes

def make_session(timeout: int = 30, ua: str = None) -> requests.Session:
    s = requests.Session()
    headers = {
        "User-Agent": ua or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    s.headers.update(headers)
    retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[429,500,502,503,504], allowed_methods=["GET","HEAD"])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter); s.mount("https://", adapter)
    s.request_timeout = timeout
    return s

def get_text(session: requests.Session, url: str, timeout: int) -> tuple[int, str, str]:
    resp = session.get(url, allow_redirects=True, timeout=timeout)
    status=resp.status_code; final_url=str(resp.url)
    if status>=400: return status, final_url, ""
    best = from_bytes(resp.content).best()
    return status, final_url, (str(best) if best else resp.text)

def head_or_get_status(session: requests.Session, url: str, timeout: int) -> tuple[int, str, str]:
    try:
        r = session.head(url, allow_redirects=True, timeout=timeout)
        if r.status_code in (405,403,501): raise requests.RequestException("fallback GET")
        return r.status_code, str(r.url), ""
    except Exception:
        try:
            r = session.get(url, allow_redirects=True, timeout=timeout)
            return r.status_code, str(r.url), (r.text if r.status_code<400 else "")
        except Exception:
            return -1, url, ""
