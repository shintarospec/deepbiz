# 企業分析API統合テスト

## 環境設定

```bash
# Gemini APIキーを設定
export GEMINI_API_KEY="your-gemini-api-key"

# DeepBiz APIキーを設定（AI AutoFormとの連携用）
export DEEPBIZ_API_KEY="your-deepbiz-api-key"
```

## テスト実行

### 1. ローカルサーバー起動

```bash
cd /workspaces/deepbiz
source venv/bin/activate
python app.py
# または gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 2. データベースマイグレーション

```bash
# マイグレーションファイル作成
flask db migrate -m "Add CompanyAnalysis model"

# マイグレーション適用
flask db upgrade
```

### 3. API動作確認

#### 3-1. 新規企業解析（POSTリクエスト）

```bash
curl -X POST http://localhost:5000/api/v1/companies/analyze \
  -H "Authorization: Bearer your-deepbiz-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "company_url": "https://www.cyberagent.co.jp"
  }'
```

**期待される出力:**
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

#### 3-2. キャッシュから取得（GETリクエスト）

```bash
curl -X GET http://localhost:5000/api/v1/companies/cyberagent.co.jp/analysis \
  -H "Authorization: Bearer your-deepbiz-api-key"
```

**期待される出力:**
```json
{
  "success": true,
  "company_domain": "cyberagent.co.jp",
  "analysis": {
    "businessDescription": "...",
    "industry": "IT・ソフトウェア",
    "strengths": [...],
    "targetCustomers": "...",
    "keyTopics": [...],
    "companySize": "大企業",
    "painPoints": [...]
  },
  "cached": true,
  "analyzed_at": "2026-01-01T10:00:00Z",
  "expires_at": "2026-04-01T10:00:00Z",
  "cache_hit_count": 1
}
```

#### 3-3. エラーケース確認

```bash
# APIキーなし
curl -X GET http://localhost:5000/api/v1/companies/example.co.jp/analysis

# 期待: 401 Unauthorized

# 無効なAPIキー
curl -X GET http://localhost:5000/api/v1/companies/example.co.jp/analysis \
  -H "Authorization: Bearer invalid-key"

# 期待: 403 Forbidden

# 存在しないドメイン
curl -X GET http://localhost:5000/api/v1/companies/nonexistent123456.co.jp/analysis \
  -H "Authorization: Bearer your-deepbiz-api-key"

# 期待: 500 Internal Server Error（スクレイピング失敗）
```

### 4. キャッシュ管理テスト

```bash
# 統計情報表示
python scripts/cleanup_company_cache.py --stats

# 期限切れキャッシュ削除
python scripts/cleanup_company_cache.py --cleanup
```

## AI AutoForm側の実装例

```python
# backend/services/deepbiz_client.py
import os
import requests
from typing import Dict


class DeepBizClient:
    def __init__(self):
        self.api_url = os.getenv('DEEPBIZ_API_URL', 'http://localhost:5000')
        self.api_key = os.getenv('DEEPBIZ_API_KEY')
    
    def get_company_analysis(self, company_url: str) -> Dict:
        """
        DeepBizから企業分析結果を取得
        
        Args:
            company_url: 企業URL（https://example.co.jp）
        
        Returns:
            企業分析情報（JSON）
        """
        domain = self._extract_domain(company_url)
        
        response = requests.get(
            f"{self.api_url}/api/v1/companies/{domain}/analysis",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['analysis']
        elif response.status_code == 404:
            # キャッシュなし → 新規解析リクエスト
            return self.analyze_company(company_url)
        else:
            raise Exception(f"企業分析取得失敗: {response.status_code}")
    
    def analyze_company(self, company_url: str) -> Dict:
        """
        新規企業解析を実行
        """
        response = requests.post(
            f"{self.api_url}/api/v1/companies/analyze",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={"company_url": company_url},
            timeout=60  # AI解析は時間がかかる可能性あり
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['analysis']
        else:
            raise Exception(f"企業解析失敗: {response.status_code}")
    
    def _extract_domain(self, url: str) -> str:
        """URLからドメイン抽出"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace('www.', '')


# 使用例
if __name__ == '__main__':
    client = DeepBizClient()
    
    # 企業分析取得
    analysis = client.get_company_analysis('https://www.cyberagent.co.jp')
    
    print(f"事業内容: {analysis['businessDescription']}")
    print(f"業界: {analysis['industry']}")
    print(f"強み: {', '.join(analysis['strengths'])}")
    print(f"ターゲット: {analysis['targetCustomers']}")
```

## トラブルシューティング

### 1. Gemini APIエラー

```bash
# APIキーが設定されているか確認
echo $GEMINI_API_KEY

# APIキーの権限確認
curl -X POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=$GEMINI_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

### 2. データベースエラー

```bash
# データベース確認
sqlite3 instance/salon_data.db ".tables"

# CompanyAnalysisテーブルが存在するか確認
sqlite3 instance/salon_data.db "SELECT sql FROM sqlite_master WHERE name='company_analysis';"
```

### 3. Seleniumエラー（JavaScript実行が必要な場合）

```bash
# Chromeがインストールされているか確認
google-chrome --version

# ChromeDriverの確認
which chromedriver
```

## パフォーマンステスト

```bash
# 100社連続解析テスト
for i in {1..100}; do
  curl -X GET http://localhost:5000/api/v1/companies/example${i}.co.jp/analysis \
    -H "Authorization: Bearer your-deepbiz-api-key" \
    -w "\n%{time_total}s\n" \
    -o /dev/null -s
done
```

## コスト試算

### 初回解析コスト（Gemini 2.0 Flash）
- 入力: 5,310トークン × $0.00001875 = $0.0001
- 出力: 600トークン × $0.000075 = $0.000045
- **合計: $0.0001446 ≈ 0.012円/社**

### 運用コスト（月100社×10ユーザー）
- 初回: 100社 × 0.012円 = **1.2円**
- 2回目以降: **0円**（キャッシュ）

### 年間コスト試算
- 新規企業追加: 月100社 × 12ヶ月 × 0.012円 = **14.4円**
- キャッシュ利用: **0円**

**→ 実質的なAIコスト: ほぼ0円**
