#!/usr/bin/env python3
"""
Phase 1B-Retry: CID再取得スクリプト（失敗分のみ）
Place IDからCIDを取得（タイムアウト延長版）

改善点:
- タイムアウト延長（15秒→30秒）
- リトライ回数増加（3回→5回）
- 待機時間延長（5秒→8秒）
"""
import sys
import os
import time
import re
import argparse

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Biz, get_stealth_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# 設定（より安定性重視）
MAX_RETRIES = 5  # リトライ回数増加
PAGE_TIMEOUT = 30  # ページロードタイムアウト延長
WAIT_TIMEOUT = 15  # 要素待機タイムアウト延長
BROWSER_RESTART_INTERVAL = 10  # ブラウザ再起動間隔短縮（安定性向上）


def is_driver_alive(driver):
    """ブラウザが正常に動作しているか確認"""
    try:
        _ = driver.current_url
        return True
    except Exception as e:
        print(f"    ⚠️  ブラウザ異常検知: {type(e).__name__}")
        return False


def restart_driver(driver):
    """ブラウザを安全に再起動"""
    try:
        if driver:
            driver.quit()
    except Exception as e:
        print(f"    警告: driver.quit()失敗 - {type(e).__name__}")
    
    time.sleep(3)  # 再起動前の待機時間延長
    new_driver = get_stealth_driver()
    print(f"    ✓ ブラウザ再起動完了")
    return new_driver


def get_cid_from_place_id(place_id, driver):
    """Place IDからCIDを取得（改善版・タイムアウト延長）"""
    if not place_id:
        return None
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 通常のGoogleマップURL
            maps_url = f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}"
            
            # タイムアウト設定
            driver.set_page_load_timeout(PAGE_TIMEOUT)
            
            # ページロード
            driver.get(maps_url)
            
            # ページロード待機
            try:
                WebDriverWait(driver, WAIT_TIMEOUT).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except TimeoutException:
                print(f"    警告: ページロード待機タイムアウト（試行 {attempt}/{MAX_RETRIES}）")
            
            # JavaScriptロード待機（延長）
            time.sleep(8)
            
            # URL確認（複数回試行）
            for url_check_attempt in range(5):
                current_url = driver.current_url
                
                # パターン1: URL内の16進数
                match = re.search(r'!1s0x[0-9a-f]+:0x([0-9a-f]+)', current_url)
                if match:
                    hex_cid = match.group(1)
                    cid = str(int(hex_cid, 16))
                    return cid
                
                # パターン2: cid= パラメータ
                match = re.search(r'cid=(\d+)', current_url)
                if match:
                    return match.group(1)
                
                # URLにまだCIDが含まれていない場合、待機
                if url_check_attempt < 4:
                    time.sleep(3)
            
            # ページソースから検索
            page_source = driver.page_source
            
            # パターン3: ludocid
            match = re.search(r'\"ludocid\":\"(\d+)\"', page_source)
            if match:
                return match.group(1)
            
            # パターン4: data-cid
            match = re.search(r'data-cid=\"(\d+)\"', page_source)
            if match:
                return match.group(1)
            
            # パターン5: cid パラメータ（ページソース内）
            match = re.search(r'[?&]cid=(\d+)', page_source)
            if match:
                return match.group(1)
            
            # パターン6: 0x形式（ページソース内）
            match = re.search(r'0x[0-9a-f]+:0x([0-9a-f]+)', page_source)
            if match:
                hex_cid = match.group(1)
                cid = str(int(hex_cid, 16))
                return cid
            
            print(f"    ℹ️  CIDが見つかりませんでした (試行 {attempt}/{MAX_RETRIES})")
            
            if attempt < MAX_RETRIES:
                time.sleep(5)  # リトライ前の待機時間延長
                continue
            
            return None
            
        except TimeoutException as e:
            print(f"    ⚠️  タイムアウト (試行 {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(5)
                continue
            return None
            
        except WebDriverException as e:
            print(f"    ❌ WebDriverエラー (試行 {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                raise  # 上位で再起動
            return None
            
        except Exception as e:
            print(f"    ❌ 予期しないエラー (試行 {attempt}/{MAX_RETRIES}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(5)
                continue
            return None
    
    return None


def retry_failed_cid(limit=None):
    """CID取得失敗分を再試行"""
    
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
        
        print(f"=== Phase 1B-Retry: CID再取得開始 ===")
        print(f"対象クリニック: {total}件")
        print(f"改善点:")
        print(f"  - タイムアウト延長: {PAGE_TIMEOUT}秒")
        print(f"  - リトライ: 最大{MAX_RETRIES}回")
        print(f"  - 待機時間: 8秒 + URL確認15秒")
        print(f"  - ブラウザ再起動: {BROWSER_RESTART_INTERVAL}件ごと")
        print()
        
        driver = None
        success = 0
        failed = 0
        driver_restarts = 0
        
        try:
            driver = get_stealth_driver()
            
            for i, salon in enumerate(salons, 1):
                print(f"\n[{i}/{total}] {salon.name}")
                print(f"  Place ID: {salon.place_id}")
                
                try:
                    # ブラウザヘルスチェック
                    if not is_driver_alive(driver):
                        print(f"  ⚠️  ブラウザ異常を検知、再起動します...")
                        driver = restart_driver(driver)
                        driver_restarts += 1
                    
                    # 定期的なブラウザ再起動
                    if i > 1 and i % BROWSER_RESTART_INTERVAL == 0:
                        print(f"  🔄 定期ブラウザ再起動中（{BROWSER_RESTART_INTERVAL}件ごと）...")
                        driver = restart_driver(driver)
                        driver_restarts += 1
                    
                    # CID取得
                    cid = None
                    retry_after_browser_restart = False
                    
                    try:
                        cid = get_cid_from_place_id(salon.place_id, driver)
                    except WebDriverException:
                        print(f"  🔧 ブラウザ再起動してリトライ...")
                        driver = restart_driver(driver)
                        driver_restarts += 1
                        retry_after_browser_restart = True
                    
                    if retry_after_browser_restart:
                        try:
                            cid = get_cid_from_place_id(salon.place_id, driver)
                        except Exception as e:
                            print(f"  ❌ 再起動後もエラー: {type(e).__name__}")
                            cid = None
                    
                    # 結果処理
                    if cid:
                        salon.cid = cid
                        db.session.commit()
                        
                        print(f"  ✅ CID: {cid}")
                        print(f"     マップリンク: https://maps.google.com/?cid={cid}")
                        success += 1
                    else:
                        print(f"  ❌ CID取得失敗")
                        failed += 1
                    
                    # 進捗表示
                    if i % 10 == 0:
                        success_rate = (success / i * 100) if i > 0 else 0
                        print(f"\n{'='*60}")
                        print(f"進捗: {i}/{total} 完了 | 成功: {success} | 失敗: {failed}")
                        print(f"成功率: {success_rate:.1f}% | ブラウザ再起動: {driver_restarts}回")
                        print(f"{'='*60}")
                    
                    time.sleep(3)  # レート制限対策
                    
                except KeyboardInterrupt:
                    print("\n\n⚠️  ユーザーによる中断")
                    raise
                    
                except Exception as e:
                    print(f"  ❌ 予期しないエラー: {type(e).__name__}")
                    failed += 1
                    db.session.rollback()
                    
                    try:
                        driver = restart_driver(driver)
                        driver_restarts += 1
                    except Exception:
                        driver = get_stealth_driver()
                    
                    time.sleep(3)
                    continue
        
        except KeyboardInterrupt:
            print("\n\n⚠️  処理を中断しました")
        
        finally:
            if driver:
                try:
                    driver.quit()
                    print("\n✓ ブラウザを正常終了しました")
                except Exception:
                    pass
            
            # 最終結果
            print(f"\n{'='*60}")
            print(f"=== Phase 1B-Retry: CID再取得完了 ===")
            print(f"{'='*60}")
            print(f"処理件数: {total}件")
            print(f"成功: {success}件")
            print(f"失敗: {failed}件")
            print(f"成功率: {(success/total*100) if total > 0 else 0:.1f}%")
            print(f"ブラウザ再起動回数: {driver_restarts}回")
            
            # 全体状況
            with app.app_context():
                total_salons = Biz.query.count()
                with_place_id = Biz.query.filter(Biz.place_id.isnot(None)).count()
                with_cid = Biz.query.filter(Biz.cid.isnot(None)).count()
                remaining = with_place_id - with_cid
                
                print(f"\n現在の全体状況:")
                print(f"  総クリニック数: {total_salons}件")
                print(f"  Place ID有り: {with_place_id}件")
                print(f"  CID有り: {with_cid}件")
                print(f"  CID取得率: {(with_cid/with_place_id*100) if with_place_id > 0 else 0:.1f}% ({with_cid}/{with_place_id})")
                print(f"  残りCID未取得: {remaining}件")
            print(f"{'='*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CID再取得スクリプト（失敗分のみ）')
    parser.add_argument('--test', action='store_true', help='テストモード（10件のみ処理）')
    args = parser.parse_args()
    
    if args.test:
        print("🧪 テストモード: 10件のみ処理")
        retry_failed_cid(limit=10)
    else:
        retry_failed_cid()
