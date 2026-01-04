#!/usr/bin/env python3
"""
CIDがあるがwebsite_urlがないクリニックに公式サイトURLを追加
"""
import sys
import os
import time

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Biz, get_cid_from_place_id, get_stealth_driver, get_website_from_gmap

def add_website_urls(limit=None):
    """
    CIDはあるがwebsite_urlがないクリニックに公式サイトURLを追加
    """
    with app.app_context():
        # CIDがあってwebsite_urlがないクリニックを取得
        query = Biz.query.filter(
            Biz.cid.isnot(None),
            Biz.website_url.is_(None)
        )
        if limit:
            query = query.limit(limit)
        
        salons = query.all()
        total = len(salons)
        
        print(f"=== 公式サイトURL取得開始 ===")
        print(f"対象クリニック: {total}件")
        
        driver = None
        success = 0
        failed = 0
        
        try:
            driver = get_stealth_driver()
            
            for i, salon in enumerate(salons, 1):
                try:
                    print(f"\n[{i}/{total}] {salon.name}")
                    print(f"  Place ID: {salon.place_id}")
                    
                    # Place IDからGoogleマップを開く（CID取得と同じ処理）
                    gmap_url = f"https://www.google.com/maps/place/?q=place_id:{salon.place_id}"
                    driver.get(gmap_url)
                    time.sleep(3)
                    
                    # 公式サイトURLを取得
                    website = get_website_from_gmap(driver)
                    if website:
                        salon.website_url = website
                        print(f"  ✅ 公式サイト: {website}")
                        db.session.commit()
                        success += 1
                    else:
                        print(f"  ⚠️ 公式サイトが見つかりませんでした")
                        failed += 1
                    
                    time.sleep(2)  # レート制限対策
                    
                except Exception as e:
                    print(f"  ❌ エラー: {e}")
                    failed += 1
                    db.session.rollback()
                    time.sleep(2)
                    continue
        
        finally:
            if driver:
                driver.quit()
        
        print(f"\n=== 公式サイトURL取得完了 ===")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")
        
        # 統計情報
        with_website = Biz.query.filter(Biz.website_url.isnot(None)).count()
        print(f"\n現在の状況:")
        print(f"  公式サイトURL有り: {with_website}件")
        print(f"  総クリニック数: {Biz.query.count()}件")

if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    add_website_urls(limit=limit)
