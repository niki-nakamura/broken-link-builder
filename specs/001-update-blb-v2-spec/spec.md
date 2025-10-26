# Broken Link Builder (BLB) — Spec v2

**Feature Branch**: `001-update-blb-v2-spec`  
**Created**: 2025-10-26  
**Status**: Draft  
**Input**: User description: "BLB v2 の仕様をアップデート。末尾に「差分要約 (Changed/Added/Removed)」「Open Questions」「Assumptions」も追記： - Source of Truth：スプレッドシートID 164u9J8-4uEmkVQd9tFjjrM3B37ja0aHEPSAVyIebauQ - I/O 仕様： - 「カタログ」A:G = queries_top10_pipe, url, title, clicks_total, first_seen_utc, last_seen_utc, new_flag - 「候補URL」= url, title, source_query, retrieved_at_utc - 「検査結果」= page_url, broken_link_url, anchor_text, status, soft_404, replacement_url, fit_score - 「除外ログ」= url, title, source_query, reason, ts（※超早期フィルタは記録しない） - Discovery：Wayback/CDX API と Common Crawl Index APIのみ（Google 検索は禁止） - 超早期フィルタ（HTTP 前・除外ログ非記録）： 1) HTTPS_ONLY（http:// は全破棄） 2) .org 恒久除外、.com は FREE_INCLUDE_COM_IN_JA=1 かつ日本語ヒント時のみ許可 3) IP風/数値SLD、添付拡張子（pdf/zip/docx/xlsx/pptx/svg/gif/jpg/png/webp）、インデックス/ユーティリティ系（/index.*, /wp-content/uploads/, /(login|signin|register|cart|wp-admin)/, /(feed|rss|atom)/, /sitemap(.xml)?, ?[s|q|search]=） 4) 日本語ヒューリスティクス（.jp or ひら/カタ/漢の含有等） - HTTP 後：Content-Type:text/html 限定、404/410/soft404 判定、ベンダー/ニュース/資料置き場の除外、SERPライク多面スコアで TopK/クエリ採用 - 受け入れ基準（抜粋）：http://混入 0%、.org混入 0%、ユーティリティ/インデックス系 0%、代替提案付き率 ≥85%、200 クエリ×Top10 を 3h 未満"

**Owner**: Niki / Creativebank Inc.（digi-mado.jp）  
**Goal**: Wayback/CDX + Common Crawl だけで “SERP ライク” に候補URLを発見し、404/soft404 の差し替え提案→被リンク獲得を最大化する。

## I/O Specifications

- **Source of Truth**: Google スプレッドシート（ID: `164u9J8-4uEmkVQd9tFjjrM3B37ja0aHEPSAVyIebauQ`）
- **Input/Output Sheets**:
    - **カタログ (Catalog)**: `queries_top10_pipe, url, title, clicks_total, first_seen_utc, last_seen_utc, new_flag`
    - **候補URL (Candidates)**: `url, title, source_query, retrieved_at_utc`
    - **検査結果 (Results)**: `page_url, broken_link_url, anchor_text, status, soft_404, replacement_url, fit_score`
    - **除外ログ (Exclusion Log)**: `url, title, source_query, reason, ts` (Note: Early filters are not logged)

## Discovery

- **Data Sources**: Exclusively use **Wayback/CDX API** and **Common Crawl Index API**. Google Search is prohibited.
- **Query Source**: Queries are sourced from the `queries_top10_pipe` column in the Catalog sheet, processed in descending order of frequency.

## Pre-HTTP Filtering (超早期フィルタ)
*(These filters are applied before any HTTP requests and are not logged in the Exclusion Log.)*

1.  **HTTPS_ONLY**: All `http://` URLs are discarded.
2.  **Domain Filtering**:
    -   `.org` TLDs are permanently excluded.
    -   `.com` TLDs are included only if `FREE_INCLUDE_COM_IN_JA=1` is set and Japanese language hints are present.
3.  **Pattern-based Exclusions**:
    -   **IP-like/Numeric SLD**: Hosts that resemble IP addresses or have numeric-heavy Second-Level Domains are discarded.
    -   **File Extensions**: URLs with extensions for attachments (e.g., `pdf`, `zip`, `docx`, `xlsx`, `pptx`, `svg`, `gif`, `jpg`, `png`, `webp`) are discarded.
    -   **Utility/Index Pages**: URLs matching common utility patterns (e.g., `/index.*`, `/wp-content/uploads/`, `/login`, `/signin`, `/register`, `/cart`, `/wp-admin`, `/feed`, `/rss`, `/atom`, `/sitemap.xml`, `?s=`, `?q=`, `?search=`) are discarded.
4.  **Japanese Language Heuristics**: URLs must either have a `.jp` TLD or contain Japanese characters (Hiragana, Katakana, Kanji).

## Post-HTTP Processing

1.  **Content-Type Check**: Only pages with `Content-Type: text/html` are processed.
2.  **Status Check**: Identify and handle pages with 404, 410, or soft 404 statuses.
3.  **Content-based Exclusion**: Exclude content identified as vendor sites, news aggregators, or document repositories.
4.  **SERP-like Scoring**: Employ a multi-faceted scoring model to select the Top-K candidates per query.

## Acceptance Criteria (抜粋)

-   **AC-001**: 0% of candidate URLs use the `http://` protocol.
-   **AC-002**: 0% of candidate URLs have a `.org` TLD.
-   **AC-003**: 0% of candidate URLs are utility or index-like pages.
-   **AC-004**: At least 85% of identified broken links have a replacement suggestion.
-   **AC-005**: The system can process 200 queries (Top 10 results each) in under 3 hours.

## Summary of Changes

-   **Changed**:
    -   `is_soft404` in "検査結果" is now `soft_404`.
    -   `suggested_url` in "検査結果" is now `replacement_url`.
-   **Added**:
    -   "除外ログ" (Exclusion Log) sheet specification.
    -   Japanese language heuristics to the pre-HTTP filter.
    -   Explicit prohibition of Google Search for discovery.
    -   New acceptance criteria for processing time and suggestion rate.
-   **Removed**:
    -   Vague descriptions in favor of explicit I/O specs and filtering rules.

## Open Questions

-   [NEEDS CLARIFICATION: What are the specific patterns for identifying "vendor sites, news aggregators, or document repositories"?]
-   [NEEDS CLARIFICATION: What is the detailed methodology for the "SERP-like multi-faceted scoring model"?]

## Assumptions

-   The Google Sheet (`164u9J8-4uEmkVQd9tFjjrM3B37ja0aHEPSAVyIebauQ`) is and will remain the single source of truth for input and output.
-   The environment variables (`GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_ID`, `GEMINI_API_KEY`) will be securely provided to the execution environment.
-   This specification update is part of the `001-blb-v2` feature, and this document supersedes the previous version for planning and implementation.