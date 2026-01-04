#!/usr/bin/env python3
"""
港区×IT関連カテゴリのテストタスク生成
複数キーワードでの検索効果を比較
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import ScrapingTask, Area, Category

def generate_minato_it_tasks():
    """港区の詳細エリア×IT関連カテゴリでタスク生成"""
    
    with app.app_context():
        print("=" * 60)
        print("港区×IT関連カテゴリ テストタスク生成")
        print("=" * 60)
        
        # IT関連カテゴリを取得
        it_categories = Category.query.filter(
            (Category.name.like('%IT%')) | 
            (Category.name.like('%ソフトウェア%')) |
            (Category.name.like('%システム%')) |
            (Category.name.like('%Web%')) |
            (Category.name.like('%SaaS%')) |
            (Category.name.like('%アプリ%')) |
            (Category.name.like('%クラウド%'))
        ).all()
        
        if not it_categories:
            print("\n⚠ IT関連カテゴリが見つかりません")
            print("先に seed_it_categories.py を実行してください")
            return
        
        print(f"\n対象カテゴリ: {len(it_categories)}種類")
        for cat in it_categories:
            print(f"  - {cat.name} (ID: {cat.id})")
        
        # 港区のエリアを取得
        minato_areas = Area.query.filter(
            Area.prefecture == "東京都",
            Area.city.like('港区%')
        ).all()
        
        if not minato_areas:
            print("\n⚠ 港区エリアデータが見つかりません")
            print("エリアマスタを確認してください")
            # 港区のみでタスク生成（エリアデータなしの場合）
            for category in it_categories:
                keyword = f"東京都港区 {category.name}"
                
                existing = ScrapingTask.query.filter_by(
                    task_type='GMAP',
                    search_keyword=keyword
                ).first()
                
                if not existing:
                    task = ScrapingTask(
                        task_type='GMAP',
                        search_keyword=keyword,
                        status='未実行',
                        category_id=category.id
                    )
                    db.session.add(task)
                    print(f"  ✓ {keyword}")
            
            db.session.commit()
            total = ScrapingTask.query.filter_by(task_type='GMAP', status='未実行').count()
            print(f"\n生成完了: {total}タスク")
            return
        
        print(f"\n港区エリア数: {len(minato_areas)}件")
        
        # エリア×カテゴリでタスク生成
        print("\nタスク生成中...")
        created_count = 0
        skipped_count = 0
        
        for area in minato_areas:
            for category in it_categories:
                keyword = f"{area.prefecture}{area.city} {category.name}"
                
                # 重複チェック
                existing = ScrapingTask.query.filter_by(
                    task_type='GMAP',
                    search_keyword=keyword
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                task = ScrapingTask(
                    task_type='GMAP',
                    search_keyword=keyword,
                    status='未実行',
                    category_id=category.id
                )
                db.session.add(task)
                created_count += 1
                
                if created_count % 10 == 0:
                    print(f"  進捗: {created_count}タスク生成済み")
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print(f"完了: 新規 {created_count}タスク | スキップ {skipped_count}タスク")
        print("=" * 60)
        
        # 統計表示
        print("\n【タスク統計】")
        total_tasks = ScrapingTask.query.filter_by(task_type='GMAP').count()
        未実行 = ScrapingTask.query.filter_by(task_type='GMAP', status='未実行').count()
        
        print(f"総GMAP タスク: {total_tasks}件")
        print(f"未実行: {未実行}件")
        
        # カテゴリ別タスク数
        print("\n【カテゴリ別タスク数】")
        for category in it_categories:
            count = ScrapingTask.query.filter_by(
                task_type='GMAP',
                category_id=category.id,
                status='未実行'
            ).count()
            print(f"  {category.name}: {count}タスク")
        
        print("\n次のステップ:")
        print("  python run_gmap_scraper.py  # タスク実行開始")

if __name__ == '__main__':
    generate_minato_it_tasks()
