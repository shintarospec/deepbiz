#!/usr/bin/env python3
"""
CSVからクリニックデータをインポートするスクリプト
CSVをマスターデータとして、東京都のクリニックをSalonテーブルに登録
"""
import sys
import os
import csv

# パスを追加
sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Salon, Category

def import_csv_clinics(csv_path, prefecture_filter='東京'):
    """
    CSVファイルからクリニックをインポート
    
    Args:
        csv_path: CSVファイルのパス
        prefecture_filter: インポート対象の都道府県（デフォルト: 東京）
    """
    with app.app_context():
        # カテゴリ「美容クリニック」を取得
        category = Category.query.filter_by(name='美容クリニック').first()
        if not category:
            print("エラー: カテゴリ「美容クリニック」が見つかりません")
            return
        
        print(f"=== CSV クリニックインポート開始 ===")
        print(f"対象都道府県: {prefecture_filter}")
        print(f"カテゴリID: {category.id}")
        
        imported = 0
        skipped = 0
        errors = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            print(f"CSV総行数: {len(rows)}行")
            
            for i, row in enumerate(rows[1:], 2):  # ヘッダーをスキップ
                try:
                    # カラム数チェック
                    if len(row) < 4:
                        skipped += 1
                        continue
                    
                    # データ抽出
                    clinic_id = row[0] if row[0] else None
                    name = row[1].strip() if len(row) > 1 and row[1] else None
                    address = row[2].strip() if len(row) > 2 and row[2] else None
                    official_url = row[3].strip() if len(row) > 3 and row[3] else None
                    
                    # 必須項目チェック
                    if not name or not address:
                        skipped += 1
                        continue
                    
                    # 都道府県フィルタ
                    if prefecture_filter and prefecture_filter not in address:
                        skipped += 1
                        continue
                    
                    # 重複チェック（名前と住所で）
                    existing = Salon.query.filter_by(
                        name=name,
                        address=address
                    ).first()
                    
                    if existing:
                        # 既存データがある場合は公式URLだけ更新
                        if official_url and not existing.website_url:
                            existing.website_url = official_url
                            db.session.commit()
                        skipped += 1
                        continue
                    
                    # 新規登録
                    new_salon = Salon(
                        name=name,
                        address=address,
                        website_url=official_url
                    )
                    db.session.add(new_salon)
                    db.session.flush()  # IDを取得するためにflush
                    
                    # カテゴリ関連付け（重複チェック）
                    if category not in new_salon.categories:
                        new_salon.categories.append(category)
                    
                    db.session.commit()
                    imported += 1
                    
                    if imported % 100 == 0:
                        print(f"  進捗: {imported}件インポート済み（{i}/{len(rows)}行処理）")
                
                except Exception as e:
                    errors += 1
                    print(f"エラー（{i}行目）: {e}")
                    db.session.rollback()
                    continue
        
        print(f"\n=== インポート完了 ===")
        print(f"登録: {imported}件")
        print(f"スキップ: {skipped}件")
        print(f"エラー: {errors}件")
        print(f"DB総件数: {Salon.query.count()}件")

if __name__ == '__main__':
    csv_file = '/var/www/salon_app/csv/clinic_list.csv'
    
    if not os.path.exists(csv_file):
        print(f"エラー: CSVファイルが見つかりません: {csv_file}")
        sys.exit(1)
    
    import_csv_clinics(csv_file, prefecture_filter='東京')
