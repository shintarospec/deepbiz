#!/usr/bin/env python3
"""
Phase 1B: 埋め込みマップからCIDを取得
Place IDから埋め込みGoogleマップをロードし、「拡大地図を表示」リンクからCIDを抽出
"""
import sys
import os
import time
import re

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Biz, get_stealth_driver

def get_cid_from_place_id(place_id, api_key, driver):
    """
    Place IDから通常のGoogleマップページ経由でCIDを取得
    
    Args:
        place_id: GoogleマップのPlace ID
        api_key: 使用しない（互換性のため残す）
        driver: Seleniumドライバー
    
    Returns:
        str: CID or None
    """
    if not place_id:
        return None
    
    try:
        # 通常のGoogleマップURL（APIキー不要）
        maps_url = f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}"
        
        # タイムアウトを30秒に設定
        driver.set_page_load_timeout(30)
        driver.get(maps_url)
        time.sleep(5)  # ページロード待機
        
        # 現在のURLからCIDを抽出
        current_url = driver.current_url
        
        # パターン1: /maps/place/.../data=...!8m2!3d緯度!4d経度!16s...cid:数字
        match = re.search(r'!1s0x[0-9a-f]+:0x([0-9a-f]+)', current_url)
        if match:
            # 16進数を10進数に変換
            hex_cid = match.group(1)
            cid = str(int(hex_cid, 16))
            return cid
        
        # パターン2: URLに直接 cid= が含まれている
        match = re.search(r'cid=(\d+)', current_url)
        if match:
            return match.group(1)
        
        # パターン3: ページソースから検索
        page_source = driver.page_source
        match = re.search(r'\"ludocid\":\"(\d+)\"', page_source)
        if match:
            return match.group(1)
        
        print(f"    CIDが見つかりませんでした (URL: {current_url[:100]}...)")
        return None
        
    except Exception as e:
        print(f"    CID取得エラー: {type(e).__name__}: {str(e)[:100]}")
        # ブラウザを再起動してリトライ
        try:
            driver.quit()
        except:
            pass
        return None


def enrich_cid(limit=None):
    """Place IDを持つクリニックにCIDを追加"""
    
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("エラー: GOOGLE_MAPS_API_KEYが設定されていません")
        return
    
    with app.app_context():
        # Place IDがあるがCIDがないクリニックを取得
        query = Biz.query.filter(
            Biz.place_id.isnot(None),
            Biz.cid.is_(None)
        )
        
        if limit:
            query = query.limit(limit)
        
        salons = query.all()
        total = len(salons)
        
        print(f"=== Phase 1B: CID取得開始（Googleマップページ方式） ===")
        print(f"対象クリニック: {total}件")
        print(f"方式: Google Maps URL解析（API課金なし）")
        
        driver = None
        success = 0
        failed = 0
        
        try:
            driver = get_stealth_driver()
            driver_restarts = 0
            
            for i, salon in enumerate(salons, 1):
                print(f"\n[{i}/{total}] {salon.name}")
                print(f"  Place ID: {salon.place_id}")
                
                try:
                    # 30件ごとにブラウザを再起動（メモリリーク対策）
                    if i > 1 and i % 30 == 0:
                        print("  → ブラウザ再起動中...")
                        driver.quit()
                        time.sleep(3)
                        driver = get_stealth_driver()
                        driver_restarts += 1
                    
                    cid = get_cid_from_place_id(salon.place_id, api_key, driver)
                    
                    if cid:
                        salon.cid = cid
                        db.session.commit()
                        
                        print(f"  ✓ CID: {cid}")
                        print(f"  → マップリンク: https://maps.google.com/?cid={cid}")
                        success += 1
                    else:
                        print(f"  ✗ CID取得失敗")
                        failed += 1
                    
                    # 進捗表示
                    if i % 10 == 0:
                        print(f"\n--- 進捗: {i}/{total} 完了（成功: {success}, 失敗: {failed}）---")
                    
                    time.sleep(2)  # レート制限対策
                    
                except Exception as e:
                    print(f"  エラー: {type(e).__name__}: {str(e)[:100]}")
                    failed += 1
                    db.session.rollback()
                    
                    # エラー時にブラウザ再起動を試みる
                    try:
                        driver.quit()
                        time.sleep(3)
                        driver = get_stealth_driver()
                        print("  → エラー後ブラウザ再起動完了")
                    except:
                        pass
                    
                    time.sleep(2)
                    continue
        
        finally:
            if driver:
                driver.quit()
        
        print(f"\n=== Phase 1B: CID取得完了 ===")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")
        print(f"成功率: {success/total*100:.1f}%")
        
        # 統計情報
        with_cid = Biz.query.filter(Biz.cid.isnot(None)).count()
        with_place_id = Biz.query.filter(Biz.place_id.isnot(None)).count()
        
        print(f"\n現在の状況:")
        print(f"  CID有り: {with_cid}件")
        print(f"  Place ID有り: {with_place_id}件")
        print(f"  CID取得率: {with_cid/with_place_id*100:.1f}%")
        print(f"  総クリニック数: {Biz.query.count()}件")


if __name__ == '__main__':
    # 引数で処理件数を指定可能（テスト用）
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    if limit:
        print(f"テストモード: {limit}件のみ処理")
    
    enrich_cid(limit=limit)
