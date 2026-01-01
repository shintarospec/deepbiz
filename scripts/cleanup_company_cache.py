"""
企業分析キャッシュのクリーンアップスクリプト
- 期限切れのキャッシュを削除
- 定期実行（cron）での使用を想定
"""
import os
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import CompanyAnalysis


def cleanup_expired_cache():
    """期限切れのキャッシュを削除"""
    with app.app_context():
        now = datetime.utcnow()
        
        # 期限切れのレコードを取得
        expired_records = CompanyAnalysis.query.filter(
            CompanyAnalysis.expires_at < now
        ).all()
        
        if not expired_records:
            print(f"[{now}] 期限切れのキャッシュはありません")
            return
        
        # 削除処理
        deleted_count = 0
        for record in expired_records:
            print(f"削除: {record.company_domain} (解析日: {record.analyzed_at}, 期限: {record.expires_at})")
            db.session.delete(record)
            deleted_count += 1
        
        db.session.commit()
        print(f"[{now}] {deleted_count}件の期限切れキャッシュを削除しました")


def show_cache_stats():
    """キャッシュの統計情報を表示"""
    with app.app_context():
        total_count = CompanyAnalysis.query.count()
        now = datetime.utcnow()
        
        active_count = CompanyAnalysis.query.filter(
            CompanyAnalysis.expires_at >= now
        ).count()
        
        expired_count = CompanyAnalysis.query.filter(
            CompanyAnalysis.expires_at < now
        ).count()
        
        # 利用頻度の高い企業TOP10
        top_accessed = CompanyAnalysis.query.order_by(
            CompanyAnalysis.cache_hit_count.desc()
        ).limit(10).all()
        
        print(f"\n===== キャッシュ統計情報 =====")
        print(f"総キャッシュ数: {total_count}")
        print(f"有効なキャッシュ: {active_count}")
        print(f"期限切れキャッシュ: {expired_count}")
        
        if top_accessed:
            print(f"\n利用頻度TOP10:")
            for i, record in enumerate(top_accessed, 1):
                print(f"{i}. {record.company_domain} - {record.cache_hit_count}回 (最終: {record.last_accessed_at})")
        
        print(f"=============================\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='企業分析キャッシュのクリーンアップ')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    parser.add_argument('--cleanup', action='store_true', help='期限切れキャッシュを削除')
    
    args = parser.parse_args()
    
    if args.stats:
        show_cache_stats()
    
    if args.cleanup:
        cleanup_expired_cache()
    
    if not args.stats and not args.cleanup:
        # デフォルトは統計表示 + クリーンアップ
        show_cache_stats()
        cleanup_expired_cache()
