# DeepBiz - 美容サロン検索・求人情報統合システム

さくらVPS上で稼働している美容サロン・クリニック検索サービスのバックエンドシステムです。

## システム概要

このシステムは以下の機能を提供しています：

### 主要機能
1. **サロン検索機能**
   - Google MapとHot Pepper Beautyから美容サロン・クリニック情報を収集
   - カテゴリ別検索（美容院、エステ、ネイル、まつエク、リラクゼーション、クリニック）
   - エリア（都道府県）別絞り込み
   - 評価順/名前順ソート

2. **データスクレイピング**
   - Google Maps API連携で店舗情報取得
   - Hot Pepper Beautyから詳細情報・口コミ取得
   - リジョブから求人情報取得
   - バックグラウンドタスク管理システム

3. **管理画面**
   - サロン情報のCRUD操作
   - 一括操作（削除、求人取得、詳細情報取得）
   - スクレイピングタスク管理
   - カテゴリ・広告管理

4. **企業分析API**（Phase 2）
   - Gemini AIによる企業Webサイト自動解析
   - 事業内容・業界・強み・課題の構造化抽出
   - 90日間キャッシュで高速応答・コスト削減
   - 管理画面テストページ（`/admin/test_company_analysis`）
   - RESTful API（`/api/v1/companies`）

## 技術スタック

### バックエンド
- **Framework**: Flask 3.1.2
- **Database**: SQLite（2DB構成）
  - `salon_data.db`: メインデータ（サロン、求人、口コミ等）
  - `scraping_data.db`: スクレイピングタスク管理
- **ORM**: SQLAlchemy 2.0.43 + Flask-Migrate 4.1.0
- **WSGI Server**: Gunicorn 23.0.0（3ワーカー、Unixソケット）

### Webスクレイピング
- **Selenium**: undetected-chromedriver + selenium-stealth（Bot検出回避）
- **Parser**: BeautifulSoup4 + lxml
- **API**: Google Maps API（googlemaps 4.10.0）

### フロントエンド
- **Template Engine**: Jinja2
- **Static Files**: /static ディレクトリ
- **Templates**: /templates ディレクトリ

### インフラ
- **Webサーバー**: Nginx（リバースプロキシ）
- **OS**: Ubuntu 24.04 LTS
- **ホスティング**: さくらVPS (133.167.116.58)

## データベース構造

### メインDB（salon_data.db）
```
Salon: サロン情報
├─ ReviewSummary: 口コミ評価サマリー（Google/Hot Pepper別）
├─ Job: 求人情報
└─ Category: カテゴリ（多対多）

Category: カテゴリマスタ
Advertisement: 広告枠
Coupon: クーポン（未使用）
CompanyAnalysis: 企業分析結果（Gemini AI）
```

### スクレイピングDB（scraping_data.db）
```
Area: エリアマスタ（都道府県・市区町村）
ScrapingTask: タスクキュー（GMAP/HPBタイプ）
```

## ディレクトリ構成

```
/var/www/salon_app/
├── app.py                      # メインアプリケーション
├── models.py                   # データモデル定義
├── requirements.txt            # Python依存パッケージ
├── templates/                  # Jinja2テンプレート
│   ├── salon_search.html
│   ├── salon_detail.html
│   └── admin/                  # 管理画面
├── static/                     # CSS/JS/画像
├── instance/                   # DBファイル格納
│   ├── salon_data.db
│   └── scraping_data.db
├── venv/                       # Python仮想環境
├── migrations/                 # DB migration
└── *.py                        # スクレイパー・シードスクリプト
```

## 主要スクリプト

### スクレイピング
- `run_gmap_scraper.py`: Google Mapスクレイパー実行
- `run_hpb_scraper.py`: Hot Pepper Beautyスクレイパー実行
- `run_hpb_details_updater.py`: HPB詳細情報更新

### 企業分析（Phase 2）
- `test_company_analysis.py`: 企業分析機能の統合テスト
- `scripts/cleanup_company_cache.py`: 期限切れキャッシュ削除

### マスタデータ
- `seed_*.py`: マスタデータ投入スクリプト
- `migrate_db_split.py`: DB分割移行スクリプト

## 環境変数

```bash
GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>
GEMINI_API_KEY=<your-gemini-api-key>
DEEPBIZ_API_KEY=<your-deepbiz-api-key>  # 企業分析API認証用
```

または`.env`ファイルに記載：
```
GOOGLE_MAPS_API_KEY=xxx
GEMINI_API_KEY=xxx
DEEPBIZ_API_KEY=xxx
```

## 開発環境セットアップ

```bash
# 仮想環境作成・有効化
python3 -m venv venv
source venv/bin/activate

# 依存パッケージインストール
pip install -r requirements.txt

# DB初期化
flask db upgrade

# 開発サーバー起動
flask run
```

## 本番環境

### Gunicorn起動コマンド
```bash
/var/www/salon_app/venv/bin/gunicorn --workers 3 \
  --bind unix:salon_app.sock \
  -m 007 \
  app:app
```

### Nginx設定
- リバースプロキシでGunicornのUnixソケットに転送
- ポート80/443でリッスン

## 現在の状況

- **稼働状況**: 本番環境で稼働中（2024年11月26日より継続）
- **データ**: サロン・クリニック情報が登録済み
- **スクレイピング**: バックグラウンドタスクで継続的にデータ収集

## 今後の開発予定

（追加開発要件を確認後、ここに記載）