#!/usr/bin/env python3
"""
CSVから取得したクリニックにGoogleマップ情報を補完するスクリプト
クリニック名・住所からPlace ID、CID、評価などを取得
"""
import sys
import os
import time

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Salon, ReviewSummary, get_gmap_place_details, get_cid_from_place_id, get_stealth_driver, get_website_from_gmap

def enrich_with_gmap(limit=None):
    """
    CSVから登録されたクリニックにGoogleマップ情報を追加
    
    Args:
        limit: 処理件数の上限（Noneの場合は全件）
    """
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("エラー: GOOGLE_MAPS_API_KEYが設定されていません")
        return
    
    with app.app_context():
        # Place IDがないクリニックを取得
        query = Salon.query.filter(Salon.place_id.is_(None))
        if limit:
            query = query.limit(limit)
        
        salons = query.all()
        total = len(salons)
        
        print(f"=== GMAP情報補完開始 ===")
        print(f"対象クリニック: {total}件")
        print(f"Google Maps API Key: {'設定済み' if api_key else '未設定'}")
        
        driver = None
        success = 0
        failed = 0
        skipped = 0
        
        try:
            driver = get_stealth_driver()
            
            for i, salon in enumerate(salons, 1):
                try:
                    search_query = f"{salon.name} {salon.address}"
                    print(f"\n[{i}/{total}] {salon.name}")
                    print(f"  検索: {search_query}")
                    
                    # Place情報を取得
                    place_details = get_gmap_place_details(search_query, api_key)
                    
                    if not place_details:
                        print(f"  → Place情報が見つかりませんでした")
                        failed += 1
                        time.sleep(1)
                        continue
                    
                    # 基本情報を更新
                    salon.place_id = place_details.get('place_id')
                    gmap_name = place_details.get('name')
                    gmap_address = place_details.get('formatted_address')
                    rating = place_details.get('rating')
                    review_count = place_details.get('user_ratings_total')
                    
                    # 名前が大きく異なる場合は警告
                    if gmap_name and gmap_name != salon.name:
                        print(f"  ⚠ 名前不一致: CSV「{salon.name}」 vs GMAP「{gmap_name}」")
                    
                    # 住所を更新（GMAPの方が詳細な場合）
                    if gmap_address and len(gmap_address) > len(salon.address or ''):
                        salon.address = gmap_address
                    
                    print(f"  → Place ID: {salon.place_id}")
                    
                    # Google評価を保存・更新
                    if rating is not None:
                        google_review = ReviewSummary.query.filter_by(
                            salon_id=salon.id,
                            source_name='Google'
                        ).first()
                        
                        if google_review:
                            google_review.rating = rating
                            google_review.count = review_count
                        else:
                            google_review = ReviewSummary(
                                salon_id=salon.id,
                                source_name='Google',
                                rating=rating,
                                count=review_count
                            )
                            db.session.add(google_review)
                        
                        print(f"  → 評価: {rating}★ ({review_count}件)")
                    
                    # CIDを取得
                    if salon.place_id:
                        salon.cid = get_cid_from_place_id(salon.place_id, driver)
                        if salon.cid:
                            print(f"  → CID: {salon.cid}")
                            
                            # 公式サイトURLを取得
                            if not salon.website_url:  # CSVにURLがない場合のみ
                                website = get_website_from_gmap(driver)
                                if website:
                                    salon.website_url = website
                                    print(f"  → 公式サイト: {website}")
                            
                        time.sleep(2)  # レート制限対策
                    
                    db.session.commit()
                    success += 1
                    
                    # 進捗表示
                    if i % 10 == 0:
                        print(f"\n--- 進捗: {i}/{total} 完了（成功: {success}, 失敗: {failed}）---")
                    
                    time.sleep(1)  # API制限対策
                    
                except Exception as e:
                    print(f"  エラー: {e}")
                    failed += 1
                    db.session.rollback()
                    time.sleep(2)
                    continue
        
        finally:
            if driver:
                driver.quit()
        
        print(f"\n=== GMAP情報補完完了 ===")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")
        print(f"スキップ: {skipped}件")
        
        # 統計情報
        with_place_id = Salon.query.filter(Salon.place_id.isnot(None)).count()
        with_cid = Salon.query.filter(Salon.cid.isnot(None)).count()
        print(f"\n現在の状況:")
        print(f"  Place ID有り: {with_place_id}件")
        print(f"  CID有り: {with_cid}件")
        print(f"  総クリニック数: {Salon.query.count()}件")

if __name__ == '__main__':
    # 引数で処理件数を指定可能（テスト用）
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    if limit:
        print(f"テストモード: 最初の{limit}件のみ処理")
    
    enrich_with_gmap(limit=limit)
