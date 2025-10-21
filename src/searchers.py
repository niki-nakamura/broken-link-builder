from bs4 import BeautifulSoup
from urllib.parse import urlencode
from .utils import rate_limit
from .parser import is_candidate_url

def _uniq_by_url(items):
    seen=set(); out=[]
    for it in items:
        k = it["url"].split("#")[0].split("?")[0]
        if k in seen: continue
        seen.add(k); out.append(it)
    return out

def _ddg_lite(session, query, limit, conf):
    url = "https://lite.duckduckgo.com/lite/?" + urlencode({"q": query, "kl": "jp-jp"})
    with rate_limit(conf.get("sleep_ms_between_fetches", 0)):
        r = session.get(url, allow_redirects=True, timeout=conf["timeout_seconds"])
    if r.status_code >= 400: return []
    soup = BeautifulSoup(r.text, "html.parser")
    results=[]
    for a in soup.find_all("a", href=True):
        href=a["href"]; title=a.get_text(" ", strip=True)
        if "duckduckgo.com" in href: continue
        if not is_candidate_url(href, conf["own_domain"], conf.get("domain_blocklist", [])): continue
        results.append({"title": title, "url": href})
        if len(results)>=limit: break
    return _uniq_by_url(results)

def _ddg_html(session, query, limit, conf):
    url = "https://html.duckduckgo.com/html/?" + urlencode({"q": query, "kl": "jp-jp"})
    with rate_limit(conf.get("sleep_ms_between_fetches", 0)):
        r = session.get(url, allow_redirects=True, timeout=conf["timeout_seconds"])
    if r.status_code >= 400: return []
    soup = BeautifulSoup(r.text, "html.parser")
    results=[]
    for a in soup.select("a.result__a, a.result__url, a[href]"):
        href=a.get("href"); title=a.get_text(" ", strip=True)
        if not href or not title: continue
        if "duckduckgo.com" in href: continue
        if not is_candidate_url(href, conf["own_domain"], conf.get("domain_blocklist", [])): continue
        results.append({"title": title, "url": href})
        if len(results)>=limit: break
    return _uniq_by_url(results)

def _mojeek(session, query, limit, conf):
    url = "https://www.mojeek.com/search?" + urlencode({"q": query, "snh": "1"})
    with rate_limit(conf.get("sleep_ms_between_fetches", 0)):
        r = session.get(url, allow_redirects=True, timeout=conf["timeout_seconds"])
    if r.status_code >= 400: return []
    soup = BeautifulSoup(r.text, "html.parser")
    results=[]
    patterns = [
        ("a", {"class": lambda v: v and "result-title" in v}),
        ("h2", {}),
        ("div", {"class": lambda v: v and "result" in v}),
    ]
    for tag, kwargs in patterns:
        links=[]
        for node in soup.find_all(tag, **kwargs):
            a = node if node.name=="a" else node.find("a", href=True)
            if not a: continue
            href=a.get("href"); title=a.get_text(" ", strip=True)
            if not href or not title: continue
            if not is_candidate_url(href, conf["own_domain"], conf.get("domain_blocklist", [])): continue
            links.append({"title": title, "url": href})
            if len(links)>=limit: break
        if links:
            results.extend(links)
            break
    if not results:
        for a in soup.find_all("a", href=True):
            href=a["href"]; title=a.get_text(" ", strip=True)
            if not href or not title or len(title)<5: continue
            if not is_candidate_url(href, conf["own_domain"], conf.get("domain_blocklist", [])): continue
            results.append({"title": title, "url": href})
            if len(results)>=limit: break
    return _uniq_by_url(results)

def search_auto(session, query: str, limit: int, conf: dict) -> list[dict]:
    for fn in (_ddg_lite, _ddg_html, _mojeek):
        res = fn(session, query, limit, conf)
        if res: return res
    return []

def search_duckduckgo_lite(session, query: str, limit: int, conf: dict) -> list[dict]:
    return _ddg_lite(session, query, limit, conf)

def search_mojeek(session, query: str, limit: int, conf: dict) -> list[dict]:
    return _mojeek(session, query, limit, conf)
