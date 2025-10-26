from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .utils import normalize_text

def parse_html(url: str, html: str):
    soup = BeautifulSoup(html, "html.parser")
    title = normalize_text(soup.title.get_text()) if soup.title else ""
    heads = []
    for tag in ["h1","h2","h3"]:
        for el in soup.find_all(tag):
            txt = normalize_text(el.get_text(" "))
            if txt: heads.append(txt)
    # 外部リンク抽出
    page_host = (urlparse(url).hostname or "").lower().lstrip("www.")
    links = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href: continue
        absu = urljoin(url, href)
        host = (urlparse(absu).hostname or "").lower().lstrip("www.")
        if not host or host == page_host:  # 内部は除外（BLB用途）
            continue
        anchor = normalize_text(a.get_text(" "))
        links.append((absu, anchor))
    # 本文（軽く）
    body_txt = []
    for p in soup.find_all(["p","li"]):
        t = normalize_text(p.get_text(" "))
        if t: body_txt.append(t)
    body = " ".join(body_txt[:2000])  # 簡易
    return {"title": title, "heads": heads, "links": links, "body": body}
