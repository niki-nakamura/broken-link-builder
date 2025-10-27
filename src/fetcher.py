import requests, os, time
UA = os.getenv("BLB_UA", "BLB/1.0 (+contact: you@example.com)")
TO = float(os.getenv("REQUEST_TIMEOUT","12"))

def fetch(url: str):
    r = requests.get(url, headers={"User-Agent": UA, "Accept":"text/html"}, timeout=TO, allow_redirects=True)
    ct = r.headers.get("content-type","").split(";")[0]
    return url, r.status_code, ct, r.text

def fetch_head(url: str):
    r = requests.head(url, headers={"User-Agent": UA}, timeout=TO, allow_redirects=True)
    return url, r.status_code, r.headers.get("content-type","")

def fetch_many(urls: list[str], limit: int = 50):
    out = []
    for u in urls[:limit]:
        try:
            out.append(fetch(u))
            time.sleep(0.7)  # polite
        except Exception:
            pass
    return out
