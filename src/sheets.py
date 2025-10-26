import os, json, gspread
from google.oauth2.service_account import Credentials

# 必要なら config から読み込む作りにしても良いです
SHEET_NAME_CATALOG   = "カタログ"
SHEET_NAME_CANDIDATES= "候補URL"
SHEET_NAME_RESULTS   = "検査結果"
SHEET_NAME_EXCLUDE   = "除外ログ"

SCHEMA = {
    SHEET_NAME_CATALOG:    ["queries_top10_pipe","url","title","clicks_total","first_seen_utc","last_seen_utc","new_flag"],
    SHEET_NAME_CANDIDATES: ["url","title","source_query","retrieved_at_utc"],
    SHEET_NAME_RESULTS:    ["page_url","broken_link_url","anchor_text","status","soft_404","replacement_url","fit_score"],
    SHEET_NAME_EXCLUDE:    ["url","title","source_query","reason","ts"],
}

def _client():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    return gspread.authorize(Credentials.from_service_account_info(info, scopes=scopes))

def open_book():
    gc = _client()
    return gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

def _get_or_create(sh, title):
    try:
        ws = sh.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=200, cols=max(10, len(SCHEMA.get(title, []))))
        if title in SCHEMA:
            ws.update('1:1', [SCHEMA[title]])
        return ws
    need = SCHEMA.get(title)
    if need and ws.row_values(1)[:len(need)] != need:
        ws.update('1:1', [need])
    return ws

def read_catalog(sh):
    ws = _get_or_create(sh, SHEET_NAME_CATALOG)
    return ws.get_all_values()

def read_excluded(sh):
    # まだ運用未定の場合は空集合を返して問題なし
    return set(), set(), set()

def append_candidates(sh, rows):
    ws = _get_or_create(sh, SHEET_NAME_CANDIDATES)
    ws.append_rows(rows, value_input_option="RAW")

def append_results(sh, rows):
    ws = _get_or_create(sh, SHEET_NAME_RESULTS)
    ws.append_rows(rows, value_input_option="RAW")
