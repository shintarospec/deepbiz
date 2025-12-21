#!/usr/bin/env python3
"""
データベースを美容クリニック×東京23区に特化してクリーンアップするスクリプト

実行内容:
1. 23区以外のエリアデータを削除
2. 美容クリニック以外のカテゴリ関連データを削除（オプション）
3. 関連するスクレイピングタスクを削除
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Area, Category, Salon, ScrapingTask, salon_categories
from flask import Flask
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '../instance/salon_data.db')}"
app.config['SQLALCHEMY_BINDS'] = {
    'scraping': f"sqlite:///{os.path.join(os.path.dirname(__file__), '../instance/scraping_data.db')}"
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def cleanup_areas():
    """23区以外のエリアデータを削除"""
    print("\n=== エリアデータのクリーンアップ ===")
    
    # 削除前の件数
    total_before = Area.query.count()
    tokyo_total = Area.query.filter(Area.prefecture == '東京都').count()
    tokyo_23 = Area.query.filter(
        Area.prefecture == '東京都',
        Area.city.like('%区%')
    ).count()
    
    print(f"削除前: 全国 {total_before}件, 東京都 {tokyo_total}件, 23区 {tokyo_23}件")
    
    # 23区以外を削除
    deleted_non_tokyo = Area.query.filter(Area.prefecture != '東京都').delete(synchronize_session=False)
    deleted_non_23 = Area.query.filter(
        Area.prefecture == '東京都',
        ~Area.city.like('%区%')
    ).delete(synchronize_session=False)
    
    db.session.commit()
    
    # 削除後の件数
    total_after = Area.query.count()
    
    print(f"削除: 東京都以外 {deleted_non_tokyo}件, 23区以外 {deleted_non_23}件")
    print(f"削除後: {total_after}件")
    print(f"削減率: {100 - (total_after / total_before * 100):.1f}%\n")

def cleanup_salons_by_category(keep_clinic_only=False):
    """美容クリニック以外のサロンデータを削除（オプション）"""
    if not keep_clinic_only:
        print("美容クリニック以外のサロンデータは保持します")
        return
    
    print("\n=== サロンデータのクリーンアップ ===")
    
    # 美容クリニックカテゴリIDを取得
    clinic_category = Category.query.filter_by(name='美容クリニック').first()
    if not clinic_category:
        print("警告: '美容クリニック'カテゴリが見つかりません")
        return
    
    total_before = Salon.query.count()
    
    # 美容クリニックカテゴリを持つサロンのID一覧を取得
    clinic_salon_ids = db.session.query(salon_categories.c.salon_id).filter(
        salon_categories.c.category_id == clinic_category.id
    ).all()
    clinic_salon_ids = [s[0] for s in clinic_salon_ids]
    
    # 美容クリニックカテゴリを持たないサロンを削除
    deleted = Salon.query.filter(~Salon.id.in_(clinic_salon_ids)).delete(synchronize_session=False)
    db.session.commit()
    
    total_after = Salon.query.count()
    
    print(f"削除前: {total_before}件")
    print(f"削除: {deleted}件")
    print(f"削除後: {total_after}件（美容クリニックのみ）\n")

def cleanup_tasks():
    """スクレイピングタスクをクリーンアップ"""
    print("\n=== スクレイピングタスクのクリーンアップ ===")
    
    try:
        total_before = ScrapingTask.query.count()
        
        # 全タスクを削除（新しい23区×美容クリニック用タスクを後で作成）
        deleted = ScrapingTask.query.delete(synchronize_session=False)
        db.session.commit()
        
        print(f"削除前: {total_before}件")
        print(f"削除: {deleted}件")
        print(f"新しいタスクは後で生成します\n")
    except Exception as e:
        print(f"タスククリーンアップ中にエラー: {e}")
        db.session.rollback()

def main():
    """メインの実行関数"""
    with app.app_context():
        print("=" * 60)
        print("データベースクリーンアップ: 東京23区×美容クリニック特化")
        print("=" * 60)
        
        response = input("\n注意: このスクリプトはデータを削除します。続行しますか？ (yes/no): ")
        if response.lower() != 'yes':
            print("キャンセルしました")
            return
        
        # エリアデータのクリーンアップ（23区のみ残す）
        cleanup_areas()
        
        # サロンデータのクリーンアップ（オプション）
        response = input("美容クリニック以外のサロンデータも削除しますか？ (yes/no): ")
        cleanup_salons_by_category(keep_clinic_only=(response.lower() == 'yes'))
        
        # スクレイピングタスクのクリーンアップ
        cleanup_tasks()
        
        print("=" * 60)
        print("クリーンアップ完了！")
        print("=" * 60)

if __name__ == '__main__':
    main()
