# 企業Webサイト解析API - AI AutoForm連携機能

## 🎯 概要

DeepBiz側で企業WebサイトをAI解析し、AI AutoFormにAPIで提供する機能です。

- **目的**: 営業対象企業の情報を自動取得・解析してメッセージをパーソナライズ
- **処理方式**: DeepBiz APIで一元管理（複数ユーザーでコスト効率化）
- **AI**: Gemini 2.0 Flash（0.023円/社、2回目以降はキャッシュで0円）
- **キャッシュ**: 90日間有効（期限後は自動再解析）

## 📁 実装ファイル一覧

```
deepbiz/
├── models.py                           # CompanyAnalysisモデル追加
├── app.py                              # APIブループリント登録
├── requirements.txt                    # google-generativeai追加
├── api/
│   ├── __init__.py                     # API module
│   └── company_analysis.py             # 企業分析APIエンドポイント
├── services/
│   ├── __init__.py                     # Services module  
│   ├── web_scraper.py                  # Webスクレイピング機能
│   └── gemini_analyzer.py              # Gemini AI解析機能
├── scripts/
│   └── cleanup_company_cache.py        # キャッシュクリーンアップ
├── migrations/
│   └── versions/
│       └── cf3f9d6d0d0a_*.py            # CompanyAnalysisテーブル
├── test_company_analysis.py            # 統合テストスクリプト
└── docs/
    └── COMPANY_ANALYSIS_API.md         # API仕様書
```

## 🗄️ データベース設計

### CompanyAnalysisテーブル

| カラム名 | 型 | 説明 | インデックス |
|---------|---|-----|------------|
| id | INTEGER | 主キー | PRIMARY |
| company_domain | VARCHAR(255) | ドメイン（example.co.jp） | UNIQUE, INDEX |
| company_url | VARCHAR(500) | 完全URL | - |
| business_description | TEXT | 事業内容の要約（100-200文字） | - |
| industry | VARCHAR(100) | 業界分類 | - |
| strengths | JSON | 強み（配列） | - |
| target_customers | TEXT | ターゲット顧客層 | - |
| key_topics | JSON | キーワード（配列） | - |
| company_size | VARCHAR(50) | 企業規模 | - |
| pain_points | JSON | 潜在的な課題（配列） | - |
| analyzed_at | DATETIME | 解析日時 | INDEX |
| expires_at | DATETIME | 期限日時（90日後） | INDEX |
| cache_hit_count | INTEGER | 利用回数 | - |
| last_accessed_at | DATETIME | 最終アクセス日時 | - |

## 🔌 APIエンドポイント

### 1. 企業分析取得（GET）

**キャッシュから取得、なければ新規解析**

```http
GET /api/v1/companies/{company_domain}/analysis
Authorization: Bearer {deepbiz_api_key}
```

**レスポンス例:**
```json
{
  "success": true,
  "company_domain": "cyberagent.co.jp",
  "analysis": {
    "businessDescription": "インターネット広告事業、メディア事業、ゲーム事業を展開...",
    "industry": "IT・ソフトウェア",
    "strengths": ["AI技術", "メディア運営ノウハウ", "多角的事業展開"],
    "targetCustomers": "企業のマーケティング担当者、ゲームユーザー",
    "keyTopics": ["AI", "広告", "メディア", "ゲーム"],
    "companySize": "大企業",
    "painPoints": ["競合激化", "人材確保"]
  },
  "cached": true,
  "analyzed_at": "2026-01-01T10:00:00Z",
  "expires_at": "2026-04-01T10:00:00Z",
  "cache_hit_count": 15
}
```

### 2. 新規企業解析（POST）

**強制的に再解析（キャッシュ更新）**

```http
POST /api/v1/companies/analyze
Authorization: Bearer {deepbiz_api_key}
Content-Type: application/json

{
  "company_url": "https://www.cyberagent.co.jp"
}
```

**レスポンス例:**
```json
{
  "success": true,
  "company_domain": "cyberagent.co.jp",
  "analysis": { ... },
  "cached": false,
  "analyzed_at": "2026-01-01T10:00:00Z",
  "expires_at": "2026-04-01T10:00:00Z",
  "tokens_used": {
    "input": 5310,
    "output": 600,
    "total": 5910
  },
  "cost": 0.000145
}
```

### エラーレスポンス

| ステータス | 説明 | 理由 |
|-----------|------|------|
| 401 | Unauthorized | Authorizationヘッダーなし |
| 403 | Forbidden | 無効なAPIキー |
| 404 | Not Found | ドメインが見つからない |
| 500 | Internal Server Error | スクレイピング/AI解析失敗 |

## 🚀 セットアップ手順

### 1. 環境変数設定

```bash
# .envファイルまたはシステム環境変数
export GEMINI_API_KEY="your-gemini-api-key"
export DEEPBIZ_API_KEY="your-deepbiz-api-key"
```

### 2. 依存関係インストール

```bash
cd /workspaces/deepbiz
source venv/bin/activate
pip install -r requirements.txt
```

### 3. データベースマイグレーション

```bash
export FLASK_APP=app.py
flask db migrate -m "Add CompanyAnalysis model"
flask db upgrade
```

### 4. テスト実行

```bash
python test_company_analysis.py
```

### 5. サーバー起動

```bash
# 開発環境
python app.py

# 本番環境
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🧪 動作確認

### cURLでのテスト

```bash
# 新規企業解析
curl -X POST http://localhost:5000/api/v1/companies/analyze \
  -H "Authorization: Bearer ${DEEPBIZ_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://www.cyberagent.co.jp"}'

# キャッシュから取得
curl -X GET http://localhost:5000/api/v1/companies/cyberagent.co.jp/analysis \
  -H "Authorization: Bearer ${DEEPBIZ_API_KEY}"
```

### Pythonクライアント例

```python
import requests
import os

class DeepBizClient:
    def __init__(self):
        self.api_url = os.getenv('DEEPBIZ_API_URL', 'http://localhost:5000')
        self.api_key = os.getenv('DEEPBIZ_API_KEY')
    
    def get_company_analysis(self, company_url):
        domain = company_url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
        
        response = requests.get(
            f"{self.api_url}/api/v1/companies/{domain}/analysis",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['analysis']
        else:
            raise Exception(f"API Error: {response.status_code}")

# 使用例
client = DeepBizClient()
analysis = client.get_company_analysis('https://www.cyberagent.co.jp')
print(analysis['businessDescription'])
```

## 🔧 メンテナンス

### キャッシュ統計確認

```bash
python scripts/cleanup_company_cache.py --stats
```

**出力例:**
```
===== キャッシュ統計情報 =====
総キャッシュ数: 150
有効なキャッシュ: 148
期限切れキャッシュ: 2

利用頻度TOP10:
1. cyberagent.co.jp - 25回 (最終: 2026-01-01 10:00:00)
2. mercari.com - 18回 (最終: 2026-01-01 09:30:00)
...
```

### 期限切れキャッシュ削除

```bash
python scripts/cleanup_company_cache.py --cleanup
```

### cronで定期実行（推奨）

```bash
# 毎日午前3時にクリーンアップ
0 3 * * * cd /var/www/salon_app && source venv/bin/activate && python scripts/cleanup_company_cache.py --cleanup
```

## 💰 コスト試算

### Gemini 2.5 Flash-Lite料金（2026年1月時点）

| 項目 | 料金 | 備考 |
|------|------|------|
| Input | $0.0001 / 1K tokens | プロンプト + HTML |
| Output | $0.0004 / 1K tokens | JSON出力 |

### 1社あたりのコスト

```
【入力】
- プロンプト: 300トークン
- HTML: 5,010トークン
- 合計: 5,310トークン × $0.0001 = $0.000531

【出力】
- JSON: 600トークン × $0.0004 = $0.000240

【合計】
$0.000771 ≈ 0.12円/社（初回のみ）
```

### 運用コスト（月100社×10ユーザー）

```
【DeepBiz側】
初回: 100社 × 0.12円 = 12円
2回目以降: 0円（キャッシュ）

【AI AutoForm側】
全ユーザー: 0円（DeepBiz API呼び出しのみ）

→ 実効コスト: ほぼ0円
```

## 🔐 セキュリティ

### APIキー管理

- **DEEPBIZ_API_KEY**: AI AutoForm側で設定（Authorization header）
- **GEMINI_API_KEY**: DeepBiz側のみ（外部に漏洩しない）

### ベストプラクティス

1. APIキーは環境変数で管理（コードにハードコードしない）
2. HTTPSを使用（本番環境）
3. レート制限を設定（DDoS対策）
4. ログ監視（異常なアクセスパターン検出）

## 📊 モニタリング

### ログ確認

```bash
# アプリケーションログ
tail -f /var/www/salon_app/logs/app.log

# Gunicornログ
tail -f /var/www/salon_app/logs/gunicorn.log
```

### データベース確認

```bash
sqlite3 /var/www/salon_app/instance/salon_data.db

# キャッシュ件数
SELECT COUNT(*) FROM company_analysis;

# 利用頻度TOP10
SELECT company_domain, cache_hit_count, last_accessed_at 
FROM company_analysis 
ORDER BY cache_hit_count DESC 
LIMIT 10;

# 期限切れ件数
SELECT COUNT(*) FROM company_analysis 
WHERE expires_at < datetime('now');
```

## 🐛 トラブルシューティング

### よくあるエラー

#### 1. `GEMINI_API_KEY not set`

```bash
# 解決方法
export GEMINI_API_KEY="your-api-key"
```

#### 2. `Selenium WebDriver not found`

```bash
# Chrome/ChromeDriverインストール確認
google-chrome --version
which chromedriver
```

#### 3. `Database locked`

```bash
# SQLiteの同時接続制限
# → PostgreSQLへの移行を検討
```

#### 4. `JSON parse error`

- Gemini出力がJSON形式でない場合
- → プロンプト改善またはリトライロジック追加

## 🔄 アップデート履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-01-01 | 1.0.0 | 初回リリース - 企業分析API実装 |

## 📚 関連ドキュメント

- [DeepBiz プロジェクト仕様](../SPECIFICATION.md)
- [AI AutoForm連携設計](../ai-auto-form/DEEPBIZ_INTEGRATION.md)
- [API詳細仕様](COMPANY_ANALYSIS_API.md)

## 🤝 サポート

問題が発生した場合：

1. [GitHub Issues](https://github.com/shintarospec/deepbiz/issues)で報告
2. ログファイルを添付
3. 再現手順を記載

---

**実装完了日**: 2026-01-01  
**次のステップ**: AI AutoForm側の実装 → 連携テスト → 本番デプロイ
