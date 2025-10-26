import os
# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
# Sheet names (固定)
SHEET_NAME_CATALOG    = "カタログ"
SHEET_NAME_CANDIDATES = "候補URL"
SHEET_NAME_RESULTS    = "検査結果"
SHEET_NAME_EXCLUDED   = "除外ログ"
# Discovery / Filter params
HTTPS_ONLY = os.getenv("HTTPS_ONLY", "1") == "1"
FREE_INCLUDE_COM_IN_JA = os.getenv("FREE_INCLUDE_COM_IN_JA", "1") == "1"
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "12"))
TOPK_PER_QUERY = int(os.getenv("TOPK_PER_QUERY", "10"))
MAX_QUERIES = int(os.getenv("MAX_QUERIES", "50"))
PER_DOMAIN_MAX_PER_QUERY = int(os.getenv("PER_DOMAIN_MAX_PER_QUERY", "2"))
