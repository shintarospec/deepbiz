# DeepBiz - ビジネス情報検索プラットフォーム

さくらVPS上で稼働するビジネス情報検索サービス。Google Maps情報をベースに、AI分析とHot Pepper Beauty情報を統合した詳細なビジネスプロフィールを提供します。

---

## 🎯 プロジェクト現在地

**データ数**: 1,905件（美容クリニック）  
**現在フェーズ**: Phase 2 完了 ✅  
**次のステップ**: Phase 3（HPB肉付け）

### フェーズ進捗

```
Phase 0: CSV Import           ✅ 完了（2025年12月21日）
    ↓  1,905件の基礎データ
    
Phase 1: データ収集           ✅ 完了（2025年12月22-24日）
    ↓  Place ID 90% | CID 85% | Website 94%
    
Phase 2: AI企業分析           ✅ 完了（2026年1月4日）
    ↓  Gemini 2.5 Flash-Lite / 0.12円/社
    
Phase 3: HPB肉付け           🔄 次のステップ
    ↓  クーポン・求人・詳細情報
    
Phase 4: TheSide連携         📋 計画中
```

---

## 📚 ドキュメントガイド

プロジェクトを理解するために、以下の順番で読むことをおすすめします：

| 対象 | ドキュメント | 内容 |
|-----|------------|------|
| 🆕 **初めての人** | [HISTORY.md](HISTORY.md) | 時系列で見るプロジェクト履歴 |
| 💻 **開発者** | [.github/copilot-instructions.md](.github/copilot-instructions.md) | コーディング規約・開発ルール |
| 📖 **企画者** | [SPECIFICATION.md](SPECIFICATION.md) | システム仕様・機能要件 |
| 🔧 **運用者** | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | VPSデプロイ・運用手順 |
| 📊 **Phase詳細** | [docs/](docs/) | 各フェーズの詳細記録 |

### Phase別ドキュメント

- [Phase 0: CSV Import](docs/00_PHASE0_CSV_IMPORT.md) - 初期データ投入
- [Phase 1: データ収集](docs/01_PHASE1_DATA_COLLECTION.md) - Google Maps情報取得
- [Phase 2: AI企業分析](docs/02_PHASE2_AI_ANALYSIS.md) - Gemini解析機能
- [Phase 3: HPB肉付け](docs/03_PHASE3_HPB_ENRICHMENT.md) - Hot Pepper Beauty連携（計画）

---

## 🏗️ システム概要

### 主要機能

| 機能 | 説明 | Phase |
|-----|------|-------|
| **サロン検索** | カテゴリ・エリア別検索、評価順ソート | Phase 0 |
| **詳細情報表示** | Place ID、CID、Website、連絡先 | Phase 1 |
| **AI企業分析** | Gemini解析による強み・課題抽出 | Phase 2 ✅ |
| **HPB統合** | クーポン・求人・口コミ情報 | Phase 3 🔄 |
| **管理画面** | データ管理・スクレイピングタスク制御 | 全Phase |

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

⚠️ **セキュリティ重要**: APIキーは絶対にGitにコミットしないでください！

### セットアップ手順

1. `.env.example`をコピーして`.env`を作成：
```bash
cp .env.example .env
```

2. `.env`ファイルに実際のAPIキーを記載：
```bash
GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>
GEMINI_API_KEY=<your-gemini-api-key>
DEEPBIZ_API_KEY=<your-deepbiz-api-key>
```

3. APIキーの取得先：
   - **Google Maps API**: https://console.cloud.google.com/apis/credentials
   - **Gemini AI API**: https://aistudio.google.com/app/apikey
   - **DeepBiz API**: `openssl rand -hex 32` で生成

**注意**: `.env`ファイルは`.gitignore`に含まれており、Gitにコミットされません。

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