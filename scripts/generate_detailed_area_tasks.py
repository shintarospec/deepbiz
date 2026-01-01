#!/usr/bin/env python3
"""
詳細エリアベースのタスク生成スクリプト
東京23区の3,423件の詳細エリア（町名レベル）から
Google Map検索タスクを生成します。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import ScrapingTask, Area, Category

def generate_detailed_area_tasks():
    """詳細エリアごとのGoogle Mapタスクを生成"""
    
    with app.app_context():
        print("=" * 60)
        print("詳細エリアベースのタスク生成を開始")
        print("=" * 60)
        
        # 美容クリニックのカテゴリーIDを取得
        clinic_category = Category.query.filter_by(name='美容クリニック').first()
        if not clinic_category:
            print("\n⚠ 美容クリニックカテゴリーが見つかりません")
            return
        
        category_id = clinic_category.id
        print(f"\n美容クリニックカテゴリーID: {category_id}")
        
        # 既存のGMAPタスクを削除
        existing_count = ScrapingTask.query.filter_by(task_type='GMAP').count()
        print(f"\n既存のGMAPタスク: {existing_count}件")
        
        if existing_count > 0:
            confirm = input("既存のGMAPタスクを削除しますか？ (yes/no): ")
            if confirm.lower() != 'yes':
                print("キャンセルしました")
                return
            
            ScrapingTask.query.filter_by(task_type='GMAP').delete()
            db.session.commit()
            print(f"✓ 既存タスク{existing_count}件を削除")
        
        # 東京23区の詳細エリアを取得
        tokyo_wards = [
            "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区",
            "墨田区", "江東区", "品川区", "目黒区", "大田区", "世田谷区",
            "渋谷区", "中野区", "杉並区", "豊島区", "北区", "荒川区",
            "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区"
        ]
        
        # 全ての東京都エリアを取得
        all_areas = Area.query.filter(Area.prefecture == "東京都").all()
        
        if not all_areas:
            print("\n⚠ エリアデータが見つかりません")
            return
        
        # 23区のエリアのみをフィルタリング
        filtered_areas = []
        for area in all_areas:
            if any(area.city.startswith(ward) for ward in tokyo_wards):
                filtered_areas.append(area)
        
        print(f"\n対象エリア数: {len(filtered_areas)}件")
        
        # 区ごとの内訳を表示
        print("\n【区ごとのタスク数】")
        ward_counts = {}
        for area in filtered_areas:
            for ward in tokyo_wards:
                if area.city.startswith(ward):
                    ward_counts[ward] = ward_counts.get(ward, 0) + 1
                    break
        
        for ward in sorted(ward_counts.keys(), key=lambda x: ward_counts[x], reverse=True):
            print(f"  {ward}: {ward_counts[ward]}件")
        
        # タスク生成
        print("\nタスク生成中...")
        created_count = 0
        
        for area in filtered_areas:
            keyword = f"{area.prefecture}{area.city} 美容クリニック"
            
            # 重複チェック
            exists = ScrapingTask.query.filter_by(
                task_type='GMAP',
                search_keyword=keyword
            ).first()
            
            if not exists:
                task = ScrapingTask(
                    task_type='GMAP',
                    search_keyword=keyword,
                    status='未実行',
                    category_id=category_id
                )
                db.session.add(task)
                created_count += 1
                
                if created_count % 100 == 0:
                    print(f"  {created_count}件生成...")
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print(f"✓ タスク生成完了: {created_count}件")
        print("=" * 60)
        
        # サンプル表示
        print("\n【タスクサンプル（最初の10件）】")
        samples = ScrapingTask.query.filter_by(task_type='GMAP').limit(10).all()
        for i, task in enumerate(samples, 1):
            print(f"  {i}. {task.search_keyword}")

if __name__ == '__main__':
    generate_detailed_area_tasks()
