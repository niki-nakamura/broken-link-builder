# Broken Link Builder (Free, CI-friendly)

**完全無料**で動かす「ブロークンリンクビルディング」検出パイプラインです。  
Google Apps Script のタイムアウトを回避し、**GitHub Actions**などの CI 上で定期実行できます。

- 候補ページ取得：DuckDuckGo Lite / Mojeek（HTML・無課金）※規約・robots.txt を遵守し、低頻度での利用を推奨
- 本文フィルタ：`queries_top10_pipe` の語が**合計2回以上**出現するページに限定
- アンカー抽出：アンカーテキストにクエリ語を含むリンクに限定
- 壊れリンク判定：`404/410/451`、`5xx`、タイムアウト、**ソフト404**（本文に「404」「Not Found」「ページが見つかりません」など）
- 出力：`outputs/serp.csv` と `outputs/broken_links.csv`、`outputs/report.md`

> **注意**：検索エンジンの利用規約違反を避けるため、負荷を抑え、`search_engine: mojeek` を推奨。完全準拠を最優先する場合は、Common Crawl 等のオープンデータ供給源に切替えてください。

## 1) 事前準備

- Python 3.10+
- （任意）Google スプレッドシートから「カタログ」取得：サービスアカウント JSON を `GOOGLE_SERVICE_ACCOUNT_JSON` として GitHub Secret に保存し、`GOOGLE_SHEET_ID` も指定します。ローカル CSV 運用も可能です。

```
├── config.yaml
├── catalog.sample.csv            # ローカル運用する場合のサンプル
├── src/
│   ├── main.py                   # エントリポイント
│   ├── pipeline.py               # 実行フロー
│   ├── searchers.py              # DuckDuckGo Lite / Mojeek 検索
│   ├── fetcher.py                # HTTP 取得（レート制御・リトライ）
│   ├── parser.py                 # 本文抽出・アンカー抽出・出現回数カウント
│   ├── checker.py                # 壊れリンク判定（HEAD→GET/ソフト404）
│   ├── sheets.py                 # Google Sheets 読み込み（任意）
│   └── utils.py                  # 正規化、レートリミット、ログ
├── outputs/                      # 結果（CI では artifact 化）
└── .github/workflows/broken-link-builder.yml
```

## 2) セットアップ（ローカル）

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp catalog.sample.csv catalog.csv
# catalog.csv を編集して、queries_top10_pipe / replacement_url を記入
python -m src.main
```

## 3) GitHub Actions で定期実行

1. このリポジトリを GitHub にプッシュ
2. （任意）Google Sheets を使う場合は Secrets を設定  
   - `GOOGLE_SERVICE_ACCOUNT_JSON` : サービスアカウント JSON（文字列）  
   - `GOOGLE_SHEET_ID` : 対象スプレッドシート ID（「カタログ」シートが必要）
3. スケジュールは `.github/workflows/broken-link-builder.yml` の `cron` を調整

実行後、Actions の **Artifacts** に `outputs/` が保存されます。

## 4) 設定

`config.yaml` で主に以下を調整：

- `own_domain`: 自社ドメイン（候補から除外）
- `search_engine`: `mojeek` or `duckduckgo_lite`
- `results_per_query`: 1クエリあたりの SERP 取得数
- `min_occurrences`: 本文中の出現回数しきい値（初期 2）
- `sleep_ms_between_fetches`: 取得間スリープ（負荷軽減）
- `soft404_patterns`: サイトに合わせて拡張可能

## 5) インプット（2通り）

- **Google Sheets**：「カタログ」シートから `queries_top10_pipe` と `replacement_url` を読み込み（推奨）  
- **ローカル CSV**：`catalog.csv` の 2 列構成  
  ```csv
  queries_top10_pipe,replacement_url
  棲み分け 意味|棲み分け|住み分け|棲み分けとは|すみわけ|すみ分け|棲み分け 住み分け|すみわけとは|住み分け 意味|住み分けとは,https://digi-mado.jp/xxxx
  ```

## 6) 出力

- `outputs/serp.csv` : `timestamp,engine,query,rank,title,url`
- `outputs/broken_links.csv` :  
  `timestamp,source_url,source_title,matched_terms,matched_count,anchor_text,broken_link_url,status,soft_404,replacement_url,note`
- `outputs/report.md` : ドメイン別集計と上位件のリスト（アウトリーチ用下書付き）

## 7) ライセンスと免責

MIT License。利用は自己責任でお願いします。対象サイトの規約・robots.txt・法令を遵守し、過剰なリクエストを避けてください。
