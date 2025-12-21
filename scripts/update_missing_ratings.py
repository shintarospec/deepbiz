#!/usr/bin/env python3
"""
Place IDは取得済みだが評価データがないクリニックの評価を更新
"""
import sys
import os
import time
import requests

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Salon, ReviewSummary

def update_missing_ratings():
    """
    Place IDがあるが評価データがないクリニックの評価を取得
    """
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("エラー: GOOGLE_MAPS_API_KEYが設定されていません")
        return
    
    with app.app_context():
        # Place IDはあるが評価データがないクリニックを取得
        salons_with_place_id = Salon.query.filter(Salon.place_id.isnot(None)).all()
        
        missing_reviews = []
        for salon in salons_with_place_id:
            google_review = ReviewSummary.query.filter_by(
                salon_id=salon.id,
                source_name='Google'
            ).first()
            
            if not google_review:
                missing_reviews.append(salon)
        
        total = len(missing_reviews)
        print(f"=== 評価データ更新開始 ===")
        print(f"対象クリニック: {total}件")
        
        success = 0
        failed = 0
        
        for i, salon in enumerate(missing_reviews, 1):
            try:
                print(f"\n[{i}/{total}] {salon.name}")
                
                # Place Details APIで評価を取得
                url = "https://maps.googleapis.com/maps/api/place/details/json"
                params = {
                    'place_id': salon.place_id,
                    'fields': 'rating,user_ratings_total',
                    'key': api_key,
                    'language': 'ja'
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    result = response.json().get('result', {})
                    rating = result.get('rating')
                    review_count = result.get('user_ratings_total')
                    
                    if rating is not None:
                        # ReviewSummaryを作成
                        google_review = ReviewSummary(
                            salon_id=salon.id,
                            source_name='Google',
                            rating=rating,
                            count=review_count
                        )
                        db.session.add(google_review)
                        db.session.commit()
                        
                        print(f"  → 評価: {rating}★ ({review_count}件) 保存完了")
                        success += 1
                    else:
                        print(f"  → 評価データなし")
                        failed += 1
                else:
                    print(f"  → API Error: {response.status_code}")
                    failed += 1
                
                # API制限対策
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  エラー: {e}")
                failed += 1
                db.session.rollback()
                continue
        
        print(f"\n=== 評価データ更新完了 ===")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")
        
        # 最終統計
        total_with_reviews = db.session.query(Salon).join(ReviewSummary).filter(
            ReviewSummary.source_name == 'Google'
        ).count()
        total_salons = Salon.query.count()
        
        print(f"\n現在の状況:")
        print(f"  総クリニック数: {total_salons}件")
        print(f"  Google評価あり: {total_with_reviews}件 ({total_with_reviews/total_salons*100:.1f}%)")

if __name__ == '__main__':
    update_missing_ratings()
