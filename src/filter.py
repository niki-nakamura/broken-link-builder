import os, re
from urllib.parse import urlparse
from .config import HTTPS_ONLY, FREE_INCLUDE_COM_IN_JA

ATTACH_EXT = re.compile(r"\.(?:pdf|zip|docx?|xlsx?|pptx?|svg|gif|jpe?g|png|webp)(?:$|\?)", re.I)
INDEX_UTILITY_RE = re.compile(r"""(?:
    /index\.(?:html?|php|aspx?)$|
    /default\.html?$|
    /wp-content/uploads/|
    /(login|signin|logout|register|mypage|cart|checkout|wp-admin|wp-login|admin)/
    |/(feed|atom|rss)/
    |/sitemap(?:\.xml)?/?$
    |[?&](?:s|q|search)=
)""", re.X | re.I)
IP_LIKE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
NUMERIC_SLD = re.compile(r"^\d+(?:-\d+)+$")  # e.g. 0-0-0-0.jp
JA_CHAR = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")

def is_numeric_sld(host: str) -> bool:
    parts = host.split(".")
    if len(parts) < 2: return False
    sld = parts[-2]
    # jp 2LD の簡易考慮
    if parts[-1] == "jp" and sld in {"co","or","ne","ac","ed","go","lg"} and len(parts) >= 3:
        sld = parts[-3]
    alnum = "".join(ch for ch in sld if ch.isalnum() or ch == "-")
    if not alnum: return False
    digits = sum(ch.isdigit() for ch in alnum)
    ratio = digits / len(alnum)
    return digits >= 3 and (ratio >= 0.6 or NUMERIC_SLD.match(sld) is not None)

def looks_ja_hint(u: str) -> bool:
    try:
        p = urlparse(u)
        if (p.hostname or "").endswith(".jp"): return True
        tail = (p.hostname or "") + (p.path or "")
        return bool(JA_CHAR.search(tail))
    except Exception:
        return False

def early_url_keep(u: str, excluded_roots: set[str], excluded_hosts: set[str], excluded_urls: set[str]) -> bool:
    """True を返した URL のみ後段へ進める（＝破棄しない）。超早期フィルタの理由はログ非記録。"""
    if not u: return False
    if HTTPS_ONLY and u.lower().startswith("http://"):
        return False
    try:
        p = urlparse(u)
    except Exception:
        return False
    host = (p.hostname or "").lower().lstrip("www.")
    path_q = (p.path or "") + (("?" + p.query) if p.query else "")

    # TLD 制御
    if host.endswith(".org"):
        return False
    if host.endswith(".com") and not (FREE_INCLUDE_COM_IN_JA and looks_ja_hint(u)):
        return False

    # 対象外（root/host/url）
    root = ".".join(host.split(".")[-2:])
    if root in excluded_roots or host in excluded_hosts or (p.scheme + "://" + host + p.path) in excluded_urls:
        return False

    # IP / 数字SLD
    if IP_LIKE.match(host) or is_numeric_sld(host):
        return False

    # 添付系 / インデックス/ユーティリティ
    if ATTACH_EXT.search(path_q): return False
    if INDEX_UTILITY_RE.search(path_q): return False

    return True
