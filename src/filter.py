import os, re
JA_RE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')  # ひら・カタ・漢
ATTACH_EXT = re.compile(r'\.(pdf|zip|docx?|xlsx?|pptx?|svg|jpe?g|png|gif|webp)(?:$|\?)', re.I)
UTIL_PATH = re.compile(r'/(index\.[a-z0-9]+|wp-content/uploads/|feed|rss|atom|sitemap(\.xml)?|login|signin|register|cart|wp-admin)(/|$)', re.I)
NUM_SLD = re.compile(r'://\d{1,3}(\.\d{1,3}){3}|://[a-z]*\d+[a-z]*\.')

HTTPS_ONLY = os.getenv("HTTPS_ONLY","1") == "1"
FREE_INCLUDE_COM_IN_JA = os.getenv("FREE_INCLUDE_COM_IN_JA","1") == "1"

def pre_http_filter(url: str) -> tuple[bool, str]:
    if HTTPS_ONLY and not url.startswith("https://"):
        return (False, "http-scheme")
    if url.endswith(".org") or re.search(r'\.org(?=/|$)', url):
        return (False, "tld-org")
    if ATTACH_EXT.search(url):
        return (False, "attachment")
    if UTIL_PATH.search(url):
        return (False, "utility")
    if NUM_SLD.search(url):
        return (False, "numeric-sld")
    # 日本語ヒント：.jp or 日本語含有。 .com は FREE_INCLUDE_COM_IN_JA=1 のとき日本語に限定許可
    is_jp = (".jp/" in url) or bool(JA_RE.search(url))
    if ".com/" in url and not (FREE_INCLUDE_COM_IN_JA and is_jp):
        return (False, "com-nonja")
    if not (".jp/" in url or is_jp):
        return (False, "non-ja")
    return (True, "")

def soft404_text(text: str) -> bool:
    t = text.lower()
    return ("not found" in t or "404" in t or "ページが見つかりません" in t or len(t.strip()) < 60)

# vendor/news/docrepo の簡約版（C ルールの要点）
def vendor_penalty(html: str) -> float:
    score = 0.0
    if re.search(r'価格|料金|資料請求|お問い合わせ|導入事例|無料トライアル|デモ|ログイン|サインイン|購入', html):
        score += 1.0
    if re.search(r'/(pricing|price|products?|solutions?|lp|contact|demo|trial|signup|register)(/|$)', html):
        score += 0.8
    if re.search(r'会社情報|採用|IR|プレスリリース', html):
        score += 0.6
    if '"@type":"Product"' in html or '"@type":"Offer"' in html:
        score += 0.6
    return min(score, 2.0)

def news_penalty(html: str, url: str) -> float:
    s = 0.0
    if re.search(r'/news/.*\d{4}[-/]\d{2}[-/]\d{2}', url):
        s += 1.0
    if 'property="og:type" content="article"' in html and re.search(r'<time[^>]+datetime=', html):
        s += 0.6
    if re.search(r'ニュース|速報|プレスリリース|配信', html):
        s += 0.6
    return min(s, 1.5)

def docrepo_penalty(html: str) -> float:
    links = len(re.findall(r'href="[^"]+\.(pdf|docx?|pptx?|xlsx?|zip|svg|jpe?g|png|webp)"', html, flags=re.I))
    p_count = len(re.findall(r'<p\b', html, flags=re.I))
    s = 0.0
    if links >= 5 and p_count <= 3:
        s += 1.0
    return min(s, 1.0)

def post_http_filter(url: str, html: str, content_type: str, status: int) -> tuple[bool, str, dict]:
    if not (content_type or "").lower().startswith("text/html"):
        return (False, "non-html", {})
    if status in (404, 410):
        return (False, str(status), {})
    penalties = {
        "vendor_penalty": vendor_penalty(html),
        "news_penalty": news_penalty(html, url),
        "docrepo_penalty": docrepo_penalty(html),
    }
    # soft404 は「除外」でなく、検査対象ページの評価には使わない（対象はリンク先）
    return (True, "", penalties)
