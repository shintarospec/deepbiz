#!/usr/bin/env python3
"""
IT関連カテゴリのマスターデータを投入するスクリプト
様々なキーワードでGoogle Maps検索の効果を比較
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Category

IT_CATEGORIES = [
    "IT企業",
    "ソフトウェア開発",
    "システム開発",
    "Webサービス",
    "ITコンサルティング",
    "SaaS企業",
    "アプリ開発",
    "クラウドサービス",
]

def seed_it_categories():
    """IT関連カテゴリを投入"""
    with app.app_context():
        print("=" * 60)
        print("IT関連カテゴリマスター投入")
        print("=" * 60)
        
        added_count = 0
        existing_count = 0
        
        for category_name in IT_CATEGORIES:
            existing = Category.query.filter_by(name=category_name).first()
            
            if existing:
                print(f"  スキップ（既存）: {category_name}")
                existing_count += 1
            else:
                new_category = Category(name=category_name)
                db.session.add(new_category)
                print(f"  ✓ 追加: {category_name}")
                added_count += 1
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print(f"完了: 追加 {added_count}件 | 既存 {existing_count}件")
        print("=" * 60)
        
        # 確認
        all_categories = Category.query.all()
        print(f"\n全カテゴリ数: {len(all_categories)}件")
        print("\n【IT関連カテゴリ一覧】")
        for cat in Category.query.filter(Category.name.like('%IT%') | 
                                         Category.name.like('%ソフトウェア%') |
                                         Category.name.like('%システム%') |
                                         Category.name.like('%Web%') |
                                         Category.name.like('%SaaS%') |
                                         Category.name.like('%アプリ%') |
                                         Category.name.like('%クラウド%')).all():
            print(f"  ID: {cat.id} | {cat.name}")

if __name__ == '__main__':
    seed_it_categories()
