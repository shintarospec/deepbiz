#!/usr/bin/env python3
"""
東京23区×美容クリニック専用のスクレイピングタスク生成スクリプト

既存の複雑なタスク生成ロジックをシンプルに置き換えます。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Area, Category, ScrapingTask
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '../instance/biz_data.db')}"
app.config['SQLALCHEMY_BINDS'] = {
    'scraping': f"sqlite:///{os.path.join(os.path.dirname(__file__), '../instance/scraping_data.db')}"
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 東京23区のリスト
TOKYO_23_WARDS = [
    '千代田区', '中央区', '港区', '新宿区', '文京区', '台東区',
    '墨田区', '江東区', '品川区', '目黒区', '大田区', '世田谷区',
    '渋谷区', '中野区', '杉並区', '豊島区', '北区', '荒川区',
    '板橋区', '練馬区', '足立区', '葛飾区', '江戸川区'
]

def generate_simple_tasks():
    """シンプルなタスク生成: 23区 × 美容クリニック"""
    with app.app_context():
        print("=" * 60)
        print("東京23区×美容クリニック スクレイピングタスク生成")
        print("=" * 60)
        
        # 美容クリニックカテゴリを取得
        clinic_category = Category.query.filter_by(name='美容クリニック').first()
        if not clinic_category:
            print("エラー: '美容クリニック'カテゴリが見つかりません")
            print("先に seed_categories.py を実行してください")
            return
        
        print(f"\nカテゴリ: {clinic_category.name} (ID: {clinic_category.id})")
        
        # 既存タスクを削除
        existing = ScrapingTask.query.count()
        if existing > 0:
            response = input(f"\n既存の{existing}件のタスクを削除しますか？ (yes/no): ")
            if response.lower() == 'yes':
                ScrapingTask.query.delete()
                db.session.commit()
                print(f"{existing}件のタスクを削除しました")
        
        # 方式1: 区単位でのタスク生成（シンプル）
        print("\n=== 方式1: 区単位でのGoogle Mapタスク生成 ===")
        new_tasks = []
        
        for ward in TOKYO_23_WARDS:
            keyword = f"東京都{ward} 美容クリニック"
            
            # 既存チェック
            exists = ScrapingTask.query.filter_by(search_keyword=keyword).first()
            if exists:
                print(f"  スキップ（既存）: {keyword}")
                continue
            
            task = ScrapingTask(
                task_type='GMAP',
                search_keyword=keyword,
                category_id=clinic_category.id,
                status='未実行'
            )
            new_tasks.append(task)
            print(f"  追加: {keyword}")
        
        if new_tasks:
            db.session.add_all(new_tasks)
            db.session.commit()
            print(f"\n✓ {len(new_tasks)}件のタスクを追加しました")
        else:
            print("\n既に全てのタスクが登録されています")
        
        # 統計表示
        total = ScrapingTask.query.count()
        by_status = db.session.query(
            ScrapingTask.status,
            db.func.count(ScrapingTask.id)
        ).group_by(ScrapingTask.status).all()
        
        print("\n=== タスク統計 ===")
        print(f"総タスク数: {total}件")
        for status, count in by_status:
            print(f"  {status}: {count}件")
        
        print("\n" + "=" * 60)
        print("タスク生成完了！")
        print("=" * 60)

if __name__ == '__main__':
    generate_simple_tasks()
