# DeepBiz - AI開発アシスタント用指示書

このファイルはGitHub Copilotなどのコーディングアシスタントが参照するプロジェクト固有のルールと知識です。

---

## 📌 プロジェクト概要

**プロジェクト名:** DeepBiz（旧: Salondb）  
**目的:** Googleマップのビジネス情報を網羅的にDB化し、詳細な連絡先情報を提供する検索プラットフォーム  
**現在フェーズ:** Phase 2 - AI企業分析機能実装完了、データ収集準備中  
**関連システム:** TheSide（営業支援プラットフォーム）との連携

### Phase 2実装完了機能
- ✅ Gemini 2.5 Flash-Lite による企業分析（0.12円/社）
- ✅ 90日間キャッシュ機能
- ✅ 管理画面テストページ（`/admin/test_company_analysis`）
- ✅ RESTful API（`/api/v1/companies/{domain}/analysis`）
- ✅ CompanyAnalysisモデル実装
- ✅ **VPS本番デプロイ完了**（2026年1月4日）
- ✅ WebScraperクラス実装（requests + Seleniumフォールバック）

---

## 🏗️ アーキテクチャ

### 技術スタック
- **Language:** Python 3.12
- **Framework:** Flask 3.1.2
- **Database:** SQLite（2DB構成）
  - `salon_data.db`: メインデータ（Salon, ReviewSummary, Job, Coupon）
  - `scraping_data.db`: スクレイピングタスク管理
- **ORM:** SQLAlchemy 2.0.43
- **Webスクレイピング:** Selenium (undetected-chromedriver) + BeautifulSoup4
- **Web Server:** Nginx + Gunicorn（3ワーカー）

### インフラ
- **VPS:** さくらインターネット 133.167.116.58
- **OS:** Ubuntu 24.04 LTS
- **アプリケーションパス:** `/var/www/salon_app`
- **Python環境:** venv (`/var/www/salon_app/venv`)
- **Git管理:** ✅ 有効（2026年1月4日～）origin/main と同期
- **SSH認証:** ✅ 鍵認証（2026年1月4日～）
  - ローカル鍵: `~/.ssh/id_ed25519_deepbiz`
  - VPS公開鍵: `/home/ubuntu/.ssh/authorized_keys`
  - SSH config: `~/.ssh/config` (エイリアス: `deepbiz-vps`)

---

## 📦 データモデル

### 主要モデル: Salon
```python
class Salon(db.Model):
    id: int                    # 主キー
    name: str                  # Google Maps由来の名前
    name_hpb: str             # Hot Pepper Beauty由来の名前
    address: str              # 住所
    place_id: str             # Google Maps Place ID（ユニーク）
    cid: str                  # Google Maps CID（ユニーク）
    website_url: str          # 公式サイトURL
    inquiry_url: str          # 問い合わせURL
    email: str                # メールアドレス
    phone: str                # 電話番号
    hotpepper_url: str        # Hot Pepper URL（ユニーク）
    categories: List[Category] # カテゴリ（多対多）
    review_summaries: List[ReviewSummary] # 口コミ集計
```

### Phase 2モデル: CompanyAnalysis
```python
class CompanyAnalysis(db.Model):
    id: int
    domain: str               # 企業ドメイン（ユニーク）
    business_description: str # 事業内容
    industry: str            # 業界
    strengths: str           # 強み（JSON配列）
    target_customers: str    # ターゲット顧客
    key_topics: str          # キーワード（JSON配列）
    company_size: str        # 企業規模
    pain_points: str         # 潜在的課題（JSON配列）
    created_at: datetime     # 作成日時（90日キャッシュ）
```

### データ取得の優先順位
1. **Place ID** → Google Maps検索で取得（最も信頼性が高い）
2. **CID** → Place IDから変換（マップリンク生成に必要）
3. **Website/Email/Phone** → 公式サイトスクレイピング
4. **Review** → Google Maps API（課金注意）
5. **企業分析** → Gemini 2.5 Flash-Lite（0.12円/社、90日キャッシュ）

---

## 🔧 開発ルール

### コーディング規約

#### ファイル命名
- **スクリプト:** `動詞_目的語.py`
  - 例: `enrich_cid_from_embed_v2.py`, `run_hpb_scraper.py`
- **管理スクリプト:** `scripts/` ディレクトリに配置

#### 関数命名
- **データ取得:** `get_*()` - 例: `get_cid_from_place_id()`
- **データ更新:** `enrich_*()` - 例: `enrich_cid()`
- **実行:** `run_*()` - 例: `run_scraper()`

#### データベース操作
```python
# ✅ Good: app_contextを使用
with app.app_context():
    salons = Salon.query.filter(...).all()
    db.session.commit()

# ❌ Bad: app_contextなし
salons = Salon.query.all()  # エラー！
```

### 重要な制約

#### 1. API課金回避
```python
# ❌ 避ける: Google Maps API（Place Details）
result = gmaps.place(place_id=place_id)

# ✅ 推奨: スクレイピング経由
url = f"https://www.google.com/maps/search/?api=1&query_place_id={place_id}"
driver.get(url)
```

#### 2. AI APIコスト管理
```python
# ✅ 必須: キャッシュ確認（90日間有効）
existing = CompanyAnalysis.query.filter_by(domain=domain).first()
if existing and (datetime.now() - existing.created_at).days < 90:
    return existing  # キャッシュヒット、0円

# ✅ Gemini 2.5 Flash-Lite使用（0.12円/社）
from services.gemini_analyzer import GeminiAnalyzer
analyzer = GeminiAnalyzer()
result = analyzer.analyze_company(url)  # 初回のみ課金
```

#### 3. Bot検出回避
```python
# ✅ 必須: undetected-chromedriverを使用
from app import get_stealth_driver
driver = get_stealth_driver()

# ✅ 必須: 適度な待機時間
time.sleep(2)  # レート制限対策
```

#### 3. ブラウザ安定性
```python
# ✅ 定期的な再起動（メモリリーク対策）
if i % 15 == 0:  # 15件ごと
    driver = restart_driver(driver)

# ✅ エラーハンドリング
try:
    driver.get(url)
except WebDriverException:
    driver = restart_driver(driver)
```

---

## 🚀 開発ワークフロー

### スクリプト開発の標準手順

1. **ローカルで開発**
   ```bash
   # /workspaces/deepbiz で作業
   vim scripts/new_script.py
   ```

2. **テスト機能を実装**
   ```python
   if __name__ == '__main__':
       parser = argparse.ArgumentParser()
       parser.add_argument('--test', action='store_true')
       args = parser.parse_args()
       
       limit = 10 if args.test else None
   ```

3. **VPSに同期（Git経由）**
   ```bash
   # ローカルでコミット・プッシュ
   git add scripts/new_script.py
   git commit -m "feat: Add new script"
   git push
   
   # VPSで同期（1コマンド）
   ssh ubuntu@133.167.116.58 'cd /var/www/salon_app && git pull'
   ```

4. **VPSでテスト実行**
   ```bash
   ssh ubuntu@133.167.116.58 \
     "cd /var/www/salon_app && venv/bin/python scripts/new_script.py --test"
   ```

5. **本番実行**
   ```bash
   # バックグラウンド実行
   nohup venv/bin/python scripts/new_script.py > output.log 2>&1 &
   ```

6. **Webアプリ再起動（コード変更時）**
   ```bash
   ssh ubuntu@133.167.116.58 \
     'cd /var/www/salon_app && pkill -f gunicorn && \
      venv/bin/gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app --daemon'
   ```

### デバッグパターン

#### ログ確認
```bash
# リアルタイム監視
tail -f /var/www/salon_app/output.log

# 最新50行
tail -50 /var/www/salon_app/output.log

# プロセス確認
ps aux | grep new_script.py
```

#### データベース確認
```python
# 進捗確認
with app.app_context():
    total = Salon.query.count()
    with_place_id = Salon.query.filter(Salon.place_id.isnot(None)).count()
    with_cid = Salon.query.filter(Salon.cid.isnot(None)).count()
    print(f"Place ID率: {with_place_id/total*100:.1f}%")
    print(f"CID率: {with_cid/total*100:.1f}%")
```

---

## 🎯 現在進行中のタスク

### Phase 1: データ拡充
- [x] Place ID取得（1,722件）
- [ ] CID取得（進行中: 976件残り）
- [ ] Website/Email/Phone取得（未着手）

### データ取得状況（2025年12月23日時点）
```
総クリニック数: 1,905件
Place ID有り: 1,722件 (90.4%)
CID有り: 約800件 (46.5%) ← 進行中
```

---

## 📝 よくあるパターン

### Place ID → CID変換
```python
def get_cid_from_place_id(place_id, driver):
    """
    Place IDからCIDを取得（改善版パターン）
    複数の抽出パターンを試行
    """
    url = f"https://www.google.com/maps/search/?api=1&query_place_id={place_id}"
    driver.get(url)
    time.sleep(5)  # JavaScriptロード待機
    
    # パターン1: URL内の16進数
    match = re.search(r'!1s0x[0-9a-f]+:0x([0-9a-f]+)', driver.current_url)
    if match:
        return str(int(match.group(1), 16))
    
    # パターン2: ページソースのludocid
    match = re.search(r'\"ludocid\":\"(\d+)\"', driver.page_source)
    if match:
        return match.group(1)
```

### リトライ処理
```python
MAX_RETRIES = 3
for attempt in range(1, MAX_RETRIES + 1):
    try:
        result = risky_operation()
        if result:
            return result
    except Exception as e:
        if attempt < MAX_RETRIES:
            time.sleep(2)
            continue
        return None
```

### 進捗表示
```python
for i, item in enumerate(items, 1):
    print(f"\n[{i}/{total}] {item.name}")
    
    # 10件ごとに進捗サマリー
    if i % 10 == 0:
        print(f"\n{'='*60}")
        print(f"進捗: {i}/{total} | 成功: {success} | 失敗: {failed}")
        print(f"成功率: {success/i*100:.1f}%")
        print(f"{'='*60}")
```

---

## ⚠️ 注意事項

### やってはいけないこと
1. **Google Maps APIの乱用** → 課金が発生
2. **高速すぎるリクエスト** → IP制限
3. **app_contextなしのDB操作** → エラー
4. **ブラウザの長時間起動** → メモリリーク

### やるべきこと
1. **テスト機能の実装** → 本番実行前に必ず確認
2. **エラーハンドリング** → 途中で止まらないように
3. **ログ出力** → 進捗と問題を追跡可能に
4. **定期的な再起動** → ブラウザとプロセスの安定性

---

## 🧪 テスト機能

### GUIテスト（推奨）
管理画面から企業分析機能を視覚的にテストできます。

**アクセス:**
```
http://localhost:5000/admin/test_company_analysis
```

**機能:**
- リアルタイムAI分析結果表示
- コスト情報可視化（トークン数・料金）
- サンプルテキスト入力/URL自動スクレイピング対応
- エラーハンドリング・ローディング表示

### CLIテスト
```bash
# 統合テスト実行
python test_company_analysis.py

# スクリプト単体テスト
python scripts/cleanup_company_cache.py --dry-run
```

---

## 🔗 参考ドキュメント

- **仕様書:** `SPECIFICATION.md`
- **企業分析API:** `docs/COMPANY_ANALYSIS_API.md`
- **企業分析統合:** `docs/COMPANY_ANALYSIS_INTEGRATION.md`
- **システム戦略:** `docs/DeepBiz_System_AI_Strategy.md`
- **プロジェクト計画:** `docs/PROJECT_PLAN.md`
- **データ収集戦略:** `docs/DATA_COLLECTION_STRATEGY.md`
- **デプロイガイド:** `DEPLOYMENT_GUIDE.md`
- **リファクタリング計画:** `REFACTORING_PLAN.md`

---

## 💡 コード生成時のヒント

新しいスクリプトを作成する際は：
1. 既存の `scripts/enrich_cid_from_embed_v2.py` をベースにする
2. `--test` フラグで10件のみ処理する機能を実装
3. エラーハンドリングとリトライロジックを含める
4. 進捗表示（10件ごと）とサマリーを実装
5. ブラウザを使う場合は15件ごとに再起動

このパターンに従えば、安定した本番実行が可能です。
