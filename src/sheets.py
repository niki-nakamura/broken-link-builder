import os, json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _open_sheet():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not sa_json or not sheet_id:
        return None, None
    info = json.loads(sa_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    return gc, sh

def read_catalog_from_sheet():
    """
    Googleスプレッドシート『カタログ』を読み、以下のdictリストを返す:
      {"queries_top10_pipe": <文字列>, "replacement_url": <B列url or replacement_url>}
    """
    gc, sh = _open_sheet()
    if not sh:
        return []
    try:
        ws = sh.worksheet("カタログ")
    except gspread.WorksheetNotFound:
        # 念のため先頭シートを使うフォールバック
        ws = sh.sheet1
    records = ws.get_all_records()  # 1行目をヘッダーとして辞書化
    out = []
    for r in records:
      q = str(r.get("queries_top10_pipe") or "").strip()
      # B列の url を優先（なければ replacement_url を使う）
      repl = str(r.get("url") or r.get("replacement_url") or "").strip()
      if q:
          out.append({"queries_top10_pipe": q, "replacement_url": repl})
    return out

def write_table(worksheet_title: str, header: list, rows: list[list], clear: bool = True):
    """
    同じスプレッドシート内に、ヘッダー＋行配列を書き込む。
    存在しなければ新規作成、既存なら clear=True で全消去後に上書き。
    """
    gc, sh = _open_sheet()
    if not sh:
        return False
    try:
        ws = sh.worksheet(worksheet_title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_title,
                              rows=max(len(rows)+10, 1000),
                              cols=max(len(header)+5, 20))
    if clear:
        ws.clear()
    if header:
        ws.update("A1", [header])
        if rows:
            ws.update("A2", rows)
    else:
        if rows:
            ws.update("A1", rows)
    return True
