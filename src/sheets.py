# すでに同等がある場合は読み飛ばし。シグネチャだけ合わせてください。
import os, json, gspread
from datetime import datetime, timezone
from google.oauth2.service_account import Credentials

def _client():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    return gspread.authorize(Credentials.from_service_account_info(info, scopes=scopes))

def open_sheet():
    return _client().open_by_key(os.environ["GOOGLE_SHEET_ID"])

def read_catalog(sh=None):
    sh = sh or open_sheet()
    ws = sh.worksheet("カタログ")
    rows = ws.get_all_values()[1:]  # skip header
    return rows

def append_candidates(sh, rows):
    if not rows: return
    ws = sh.worksheet("候補URL")
    ws.append_rows(rows, value_input_option="RAW")

def append_results(sh, rows):
    if not rows: return
    ws = sh.worksheet("検査結果")
    ws.append_rows(rows, value_input_option="RAW")

def write_exclusion_log(sh, rows):
    if not rows: return
    ws = sh.worksheet("除外ログ")
    ws.append_rows(rows, value_input_option="RAW")

def utcnow():
    return datetime.now(timezone.utc).isoformat()
