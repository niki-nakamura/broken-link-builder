# Implementation Plan — BLB v2

本ドキュメントは `specs/001-update-blb-v2-spec/spec.md` に基づく実装計画を定義します。

## 1. Milestones

-   **M1: 設定と超早期フィルタ (Config & Pre-HTTP Filtering)**
    -   `config.yaml` にしきい値、重み、除外パターンを追加。
    -   `src/filter.py` に spec 通りの超早期フィルタ（HTTPS_ONLY, TLD, パターン, 日本語ヒューリスティクス）を実装。
    -   上記フィルタの単体テストを作成。
-   **M2: コンテンツベースフィルタ (Post-HTTP Filtering)**
    -   `src/filter.py` にベンダー/ニュース/資料置き場を判定するヒューリスティックベースのフィルタを実装。
    -   判定ロジックの単体テストを作成。
-   **M3: 多面スコアリング (Multi-faceted Scoring)**
    -   `src/scorer.py` に SERP ライクな多面スコア計算ロジックを実装 (BM25, URL, 鮮度など)。
    -   `filter.py` からのペナルティをスコアに反映させる。
    -   スコアリングロジックの単体テストを作成。
-   **M4: パイプライン統合 (Pipeline Integration)**
    -   `src/pipeline.py` を修正し、新しいフィルタリングとスコアリングのステップを組み込む。
    -   `TopK/クエリ` および `1ドメイン上限` のロジックを適用。
    -   `src/sheets.py` に「除外ログ」への書き込み処理を追加。
-   **M5: E2Eテストとチューニング (E2E Testing & Tuning)**
    -   200クエリ・Top10の目標（3時間以内）を達成するための性能テストとパラメータ調整を実施。
    -   最終的な受け入れ基準をクリアすることを確認。

## 2. Architecture

既存のパイプライン構造を維持し、フィルタリングとスコアリングのロジックを強化します。処理フローは以下の通りです。

1.  **Discover (`searchers.py`)**: Catalog シートからクエリを読み込み、CDX/CC API を使って候補 URL を取得。
2.  **Pre-HTTP Filter (`filter.py`)**: 取得した URL 群に「超早期フィルタ」を適用し、不要な HTTP リクエストを削減。
3.  **Fetch (`fetcher.py`)**: フィルタリング後の URL のコンテンツを取得。
4.  **Post-HTTP Filter (`filter.py`)**: コンテンツタイプが `text/html` のものに限定し、ベンダー/ニュース/資料置き場フィルタを適用。「除外ログ」に記録。
5.  **Parse (`parser.py`)**: ページからスコアリングに必要な要素（タイトル、見出し、本文など）を抽出。
6.  **Score (`scorer.py`)**: 多面スコアを計算し、最終的なランキングを決定。
7.  **Output (`sheets.py`)**: `TopK` の結果を「候補URL」シートに書き込む。

## 3. Modules (`src/*.py`)

既存のファイル構成を変更せず、以下のファイル内のロジックを修正・追加します。

-   `src/config.py`:
    -   フィルタリングルール（除外 TLD, パス）、スコアリングの重み、ペナルティ値、各種しきい値を定数として追加。
-   `src/filter.py`:
    -   `pre_http_filter()`: spec に基づく超早期フィルタ群を実装。
    -   `post_http_filter()`: `is_vendor()`, `is_news()`, `is_docrepo()` などの判定関数と、それらを呼び出すメインのフィルタ関数を実装。各判定は `tasks.md` のヒューリスティクスに従う。
-   `src/scorer.py`:
    -   `calculate_serp_like_score()`: `tasks.md` の定義に基づき、BM25, URL トークン、鮮度、カタログ近接度などのサブスコアを計算し、重み付け加算する関数を実装。`rank_bm25` 等のライブラリ利用を検討。
-   `src/pipeline.py`:
    -   メインの実行フローに `pre_http_filter` と `post_http_filter` の呼び出しを追加。
    -   `scorer.py` の新しいスコアリング関数を呼び出し、結果をソートして TopK を選出するロジックに修正。
-   `src/sheets.py`:
    -   `write_exclusion_log()`: 除外された URL の情報を「除外ログ」シートに追記する関数を新規追加。既存の I/O 関数のインターフェースは変更しない。
-   `src/main.py`:
    -   必要に応じて、新しい設定やデバッグオプションの CLI 引数を追加。

## 4. Sheets I/O

-   **入力**: 「カタログ」シートの構成は変更なし。
-   **出力**:
    -   「候補URL」「検査結果」のスキーマは変更なし。
    -   Post-HTTP フィルタで除外された URL は、新しく「除外ログ」シートに記録される。

## 5. ENV

-   `GOOGLE_SHEET_ID`: (必須) 読み書き対象の Google スプレッドシート ID。
-   `GOOGLE_SERVICE_ACCOUNT_JSON`: (必須) Google Service Account の認証情報 (JSON)。
-   `FREE_INCLUDE_COM_IN_JA`: (任意) `.com` ドメインを日本語サイトとして許可する場合に `1` を設定。

## 6. テスト計画 (Test Plan)

-   **Unit Tests (`pytest`)**:
    -   `tests/test_filter.py`: 超早期フィルタとコンテンツベースフィルタの各ルールに対して、陽性・陰性の両パターンを含むテストケースを追加。
    -   `tests/test_scorer.py`: 既知の入力（HTML コンテンツ）に対して、期待されるスコア（またはスコア範囲）が返却されることを確認するテストを追加。
-   **Integration Tests**:
    -   小規模なダミーの Catalog データを用意し、`main.py` を実行して「候補URL」と「除外ログ」に期待通りの結果が出力されるかを確認する E2E テストを実施。

## 7. リスク対策 (Risk Mitigation)

-   **レート制限 (Rate Limiting)**:
    -   `fetcher.py` および `searchers.py` で外部 API を呼び出す際に、適切な待機時間（e.g., `time.sleep(1)`）を挿入し、サーバーへの負荷を軽減・IP BAN を回避する。
-   **誤除外 (False Positives/Negatives)**:
    -   フィルタリングやスコアリングのしきい値・キーワード・重みはすべて `config.yaml` で管理し、コードの変更なしに調整可能にする。
    -   Post-HTTP フィルタによる除外はすべて理由と共に「除外ログ」に記録し、後の分析とチューニングを容易にする。
-   **長時間化 (Long Processing Time)**:
    -   処理時間の大半を占める HTTP リクエストを最小化するため、「超早期フィルタ」の精度を重視する。
    -   BM25 などの計算コストが高い処理は、`rank_bm25` や `numpy` などの効率的なライブラリを使用して実装する。
    -   可能な処理はバッチ化（例: シートへの一括書き込み）し、I/O オーバーヘッドを削減する。