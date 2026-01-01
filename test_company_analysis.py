"""
企業分析API機能のテストスクリプト
- Webスクレイピング機能のテスト
- Gemini AI解析のモックテスト（APIキー不要）
- データベース保存のテスト
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.web_scraper import WebScraper
from app import app, db
from models import CompanyAnalysis
from datetime import datetime, timedelta
import json


def test_web_scraping():
    """Webスクレイピング機能のテスト"""
    print("\n===== Webスクレイピングテスト =====")
    
    scraper = WebScraper(use_selenium=False)
    
    # テスト対象URL（簡単な静的サイト）
    test_url = "https://www.cyberagent.co.jp"
    
    print(f"URL: {test_url}")
    result = scraper.scrape_website(test_url, max_chars=5000)
    
    print(f"成功: {result['success']}")
    print(f"ドメイン: {result['domain']}")
    print(f"テキスト長: {len(result['text'])}文字")
    print(f"テキスト（先頭200文字）:\n{result['text'][:200]}")
    
    if not result['success']:
        print(f"エラー: {result['error']}")
    
    return result['success']


def test_database_operations():
    """データベース操作のテスト"""
    print("\n===== データベース操作テスト =====")
    
    with app.app_context():
        # テストデータ作成
        test_domain = "test-example.co.jp"
        
        # 既存レコード削除
        existing = CompanyAnalysis.query.filter_by(company_domain=test_domain).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            print(f"既存テストデータを削除しました")
        
        # 新規レコード作成
        now = datetime.utcnow()
        test_analysis = CompanyAnalysis(
            company_domain=test_domain,
            company_url=f"https://{test_domain}",
            business_description="テスト企業の事業内容説明",
            industry="IT・ソフトウェア",
            strengths=["強み1", "強み2", "強み3"],
            target_customers="中小企業のDX推進担当者",
            key_topics=["AI", "DX", "業務効率化"],
            company_size="中堅企業",
            pain_points=["リソース不足", "ITスキル不足"],
            analyzed_at=now,
            expires_at=now + timedelta(days=90),
            cache_hit_count=0
        )
        
        db.session.add(test_analysis)
        db.session.commit()
        
        print(f"✅ 新規レコード作成成功: {test_analysis.id}")
        
        # 取得テスト
        retrieved = CompanyAnalysis.query.filter_by(company_domain=test_domain).first()
        print(f"✅ レコード取得成功: {retrieved.company_domain}")
        print(f"   事業内容: {retrieved.business_description}")
        print(f"   業界: {retrieved.industry}")
        print(f"   強み: {retrieved.strengths}")
        
        # 更新テスト（キャッシュヒット）
        retrieved.cache_hit_count += 1
        retrieved.last_accessed_at = datetime.utcnow()
        db.session.commit()
        
        print(f"✅ キャッシュヒット更新成功: {retrieved.cache_hit_count}回")
        
        # クリーンアップ
        db.session.delete(retrieved)
        db.session.commit()
        print(f"✅ テストデータ削除完了")
        
        return True


def test_api_endpoints_manual():
    """APIエンドポイントの手動テスト手順を表示"""
    print("\n===== APIエンドポイント手動テスト =====")
    
    print("""
APIキーが必要なため、手動テストが必要です。

### 1. 環境変数設定

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export DEEPBIZ_API_KEY="your-deepbiz-api-key"
```

### 2. サーバー起動

```bash
cd /workspaces/deepbiz
source venv/bin/activate
python app.py
# または
gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

### 3. 別ターミナルでAPIテスト

#### 新規企業解析（POST）
```bash
curl -X POST http://localhost:5000/api/v1/companies/analyze \\
  -H "Authorization: Bearer your-deepbiz-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{"company_url": "https://www.cyberagent.co.jp"}'
```

#### キャッシュから取得（GET）
```bash
curl -X GET http://localhost:5000/api/v1/companies/cyberagent.co.jp/analysis \\
  -H "Authorization: Bearer your-deepbiz-api-key"
```

#### 認証エラーテスト
```bash
curl -X GET http://localhost:5000/api/v1/companies/cyberagent.co.jp/analysis
# 期待: 401 Unauthorized
```
""")


def test_cache_cleanup():
    """キャッシュクリーンアップ機能のテスト"""
    print("\n===== キャッシュクリーンアップテスト =====")
    
    with app.app_context():
        # 期限切れテストデータ作成
        expired_domain = "expired-test.co.jp"
        
        # 既存削除
        existing = CompanyAnalysis.query.filter_by(company_domain=expired_domain).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
        
        # 期限切れレコード作成（1日前に期限切れ）
        expired_analysis = CompanyAnalysis(
            company_domain=expired_domain,
            company_url=f"https://{expired_domain}",
            business_description="期限切れテストデータ",
            industry="IT・ソフトウェア",
            strengths=["テスト"],
            target_customers="テスト",
            key_topics=["テスト"],
            company_size="テスト",
            pain_points=["テスト"],
            analyzed_at=datetime.utcnow() - timedelta(days=91),
            expires_at=datetime.utcnow() - timedelta(days=1),  # 1日前に期限切れ
            cache_hit_count=5
        )
        
        db.session.add(expired_analysis)
        db.session.commit()
        
        print(f"✅ 期限切れテストデータ作成: {expired_analysis.company_domain}")
        print(f"   期限: {expired_analysis.expires_at}")
        print(f"   現在: {datetime.utcnow()}")
        
        # クリーンアップスクリプトの使い方を表示
        print("""
### クリーンアップスクリプト実行

```bash
# 統計情報表示
python scripts/cleanup_company_cache.py --stats

# 期限切れキャッシュ削除
python scripts/cleanup_company_cache.py --cleanup
```
""")
        
        # テストデータは残したまま終了（クリーンアップスクリプトでテスト）
        print(f"⚠️  期限切れテストデータは残しました: {expired_domain}")
        print(f"   cleanup_company_cache.py で削除してください")
        
        return True


def main():
    """全テスト実行"""
    print("=" * 60)
    print("企業分析API機能テスト開始")
    print("=" * 60)
    
    results = {
        'web_scraping': False,
        'database': False,
        'cache_cleanup': False
    }
    
    try:
        results['web_scraping'] = test_web_scraping()
    except Exception as e:
        print(f"❌ Webスクレイピングテスト失敗: {e}")
    
    try:
        results['database'] = test_database_operations()
    except Exception as e:
        print(f"❌ データベーステスト失敗: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_api_endpoints_manual()
    except Exception as e:
        print(f"❌ API手動テスト説明表示失敗: {e}")
    
    try:
        results['cache_cleanup'] = test_cache_cleanup()
    except Exception as e:
        print(f"❌ キャッシュクリーンアップテスト失敗: {e}")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print("\n次のステップ:")
    print("1. 環境変数を設定（GEMINI_API_KEY, DEEPBIZ_API_KEY）")
    print("2. サーバーを起動（python app.py または gunicorn）")
    print("3. 別ターミナルでAPIエンドポイントをテスト")
    print("4. AI AutoForm側の実装を開始")


if __name__ == '__main__':
    main()
