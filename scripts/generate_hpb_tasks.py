#!/usr/bin/env python3
"""
東京23区のHPBタスクを生成するスクリプト
tokyo23_clinic_urls.txt から読み込んでScrapingTaskに登録します。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import ScrapingTask, Category

INPUT_FILE = "tokyo23_clinic_urls.txt"

def generate_hpb_tasks():
    """tokyo23_clinic_urls.txt からHPBタスクを生成"""
    
    with app.app_context():
        print("=" * 70)
        print("HPBタスク生成を開始")
        print("=" * 70)
        
        # 美容クリニックカテゴリーを取得
        clinic_category = Category.query.filter_by(name='美容クリニック').first()
        if not clinic_category:
            print("\n⚠ エラー: '美容クリニック' カテゴリーが見つかりません")
            return
        
        category_id = clinic_category.id
        print(f"\n美容クリニックカテゴリーID: {category_id}")
        
        # URLファイルを読み込み
        if not os.path.exists(INPUT_FILE):
            print(f"\n⚠ エラー: '{INPUT_FILE}' が見つかりません")
            print("先に get_tokyo23_clinic_urls.py を実行してください")
            return
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        print(f"URLファイルから {len(urls)}件のURLを読み込みました")
        
        # 既存のHPBタスク数を確認
        existing_count = ScrapingTask.query.filter_by(task_type='HPB').count()
        print(f"既存のHPBタスク: {existing_count}件")
        
        if existing_count > 0:
            confirm = input("\n既存のHPBタスクを削除して再生成しますか？ (yes/no): ")
            if confirm.lower() == 'yes':
                ScrapingTask.query.filter_by(task_type='HPB').delete()
                db.session.commit()
                print(f"✓ 既存タスク{existing_count}件を削除")
            else:
                print("既存タスクは保持します（重複スキップ）")
        
        # タスク生成
        print("\nタスク生成中...")
        created_count = 0
        skipped_count = 0
        
        for i, url in enumerate(urls, 1):
            # 重複チェック
            exists = ScrapingTask.query.filter_by(
                task_type='HPB',
                target_url=url
            ).first()
            
            if exists:
                skipped_count += 1
                continue
            
            # 新規タスク作成
            task = ScrapingTask(
                task_type='HPB',
                target_url=url,
                category_id=category_id,
                status='未実行'
            )
            db.session.add(task)
            created_count += 1
            
            if created_count % 100 == 0:
                print(f"  {created_count}件生成...")
                db.session.commit()  # 100件ごとにコミット
        
        # 最終コミット
        db.session.commit()
        
        print("\n" + "=" * 70)
        print(f"✓ タスク生成完了")
        print(f"  新規作成: {created_count}件")
        print(f"  スキップ: {skipped_count}件（既存）")
        print("=" * 70)
        
        # サンプル表示
        print("\n【登録されたタスクのサンプル（最初の5件）】")
        samples = ScrapingTask.query.filter_by(task_type='HPB').limit(5).all()
        for i, task in enumerate(samples, 1):
            print(f"  {i}. ID:{task.id} - {task.target_url}")

if __name__ == '__main__':
    generate_hpb_tasks()
