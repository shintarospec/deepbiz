#!/usr/bin/env python3
"""
Phase 1C-2: CIDからWebsite URLを取得
CIDがあるがwebsite_urlがないクリニックを対象に、
GoogleマップページからWebsite URLを取得
"""
import sys
import os
import time
import re
import argparse

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Salon, get_stealth_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# 設定
MAX_RETRIES = 3
PAGE_TIMEOUT = 30
WAIT_TIMEOUT = 15
BROWSER_RESTART_INTERVAL = 20


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
    
    time.sleep(2)
    new_driver = get_stealth_driver()
    print(f"    ✓ ブラウザ再起動完了")
    return new_driver


def get_website_url_from_cid(cid, driver):
    """
    CIDからGoogleマップページを開いてWebsite URLを取得
    
    Args:
        cid: Google Maps CID
        driver: Seleniumドライバー
    
    Returns:
        str: Website URL or None
    """
    if not cid:
        return None
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # GoogleマップURL（CID使用）
            maps_url = f"https://maps.google.com/?cid={cid}"
            
            driver.set_page_load_timeout(PAGE_TIMEOUT)
            driver.get(maps_url)
            
            # ページロード待機
            time.sleep(5)
            
            # 「ウェブサイト」ボタンを探す（複数パターン）
            website_url = None
            
            # パターン1: data-item-id="authority" のリンク
            try:
                element = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
                website_url = element.get_attribute('href')
                if website_url:
                    return website_url
            except NoSuchElementException:
                pass
            
            # パターン2: aria-label="ウェブサイト" のリンク
            try:
                element = driver.find_element(By.CSS_SELECTOR, 'a[aria-label*="ウェブサイト"]')
                website_url = element.get_attribute('href')
                if website_url:
                    return website_url
            except NoSuchElementException:
                pass
            
            # パターン3: テキストに「ウェブサイト」を含むリンク
            try:
                elements = driver.find_elements(By.PARTIAL_LINK_TEXT, 'ウェブサイト')
                if elements:
                    website_url = elements[0].get_attribute('href')
                    if website_url:
                        return website_url
            except NoSuchElementException:
                pass
            
            # パターン4: ページソースから直接抽出
            page_source = driver.page_source
            
            # "http" または "https" で始まるURLを探す（Googleマップ関連URLを除外）
            url_pattern = r'https?://(?!maps\.google|maps\.gstatic|www\.google)[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s"<>]*)?'
            urls = re.findall(url_pattern, page_source)
            
            # クリニックの公式サイトらしいURLを選択
            for url in urls:
                # 除外パターン
                if any(exclude in url.lower() for exclude in [
                    'facebook.com', 'twitter.com', 'instagram.com',
                    'youtube.com', 'google.com', 'gstatic.com',
                    'schema.org', 'w3.org'
                ]):
                    continue
                
                # 最初に見つかった適切なURLを返す
                website_url = url
                break
            
            if website_url:
                return website_url
            
            print(f"    ℹ️  Website URLが見つかりませんでした (試行 {attempt}/{MAX_RETRIES})")
            
            if attempt < MAX_RETRIES:
                time.sleep(3)
                continue
            
            return None
            
        except TimeoutException as e:
            print(f"    ⚠️  タイムアウト (試行 {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(3)
                continue
            return None
            
        except WebDriverException as e:
            print(f"    ❌ WebDriverエラー (試行 {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                print(f"    → ブラウザ再起動を試みます...")
                raise
            return None
            
        except Exception as e:
            print(f"    ❌ 予期しないエラー (試行 {attempt}/{MAX_RETRIES}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(3)
                continue
            return None
    
    return None


def enrich_website_url(limit=None):
    """
    CIDを持つがwebsite_urlがないクリニックにWebsite URLを追加
    
    Args:
        limit: 処理件数上限（Noneなら全件）
    """
    
    with app.app_context():
        # CIDがあるがwebsite_urlがないクリニックを取得
        query = Salon.query.filter(
            Salon.cid.isnot(None),
            Salon.website_url.is_(None)
        )
        
        if limit:
            query = query.limit(limit)
        
        salons = query.all()
        total = len(salons)
        
        print(f"=== Phase 1C-2: Website URL取得開始（CID経由） ===")
        print(f"対象クリニック: {total}件")
        print(f"方式: CID → Googleマップページ → Website URL")
        print(f"改善点:")
        print(f"  - リトライ: 最大{MAX_RETRIES}回")
        print(f"  - ページタイムアウト: {PAGE_TIMEOUT}秒")
        print(f"  - ブラウザ再起動: {BROWSER_RESTART_INTERVAL}件ごと")
        print(f"  - 複数の抽出パターン実装")
        print()
        
        driver = None
        success = 0
        failed = 0
        driver_restarts = 0
        
        try:
            driver = get_stealth_driver()
            
            for i, salon in enumerate(salons, 1):
                print(f"\n[{i}/{total}] {salon.name}")
                print(f"  CID: {salon.cid}")
                
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
                    
                    # Website URL取得
                    website_url = None
                    retry_after_browser_restart = False
                    
                    try:
                        website_url = get_website_url_from_cid(salon.cid, driver)
                    except WebDriverException:
                        driver = restart_driver(driver)
                        driver_restarts += 1
                        retry_after_browser_restart = True
                    
                    # ブラウザ再起動後のリトライ
                    if retry_after_browser_restart:
                        try:
                            website_url = get_website_url_from_cid(salon.cid, driver)
                        except Exception as e:
                            print(f"  ❌ 再起動後もエラー: {type(e).__name__}")
                            website_url = None
                    
                    # 結果処理
                    if website_url:
                        salon.website_url = website_url
                        db.session.commit()
                        
                        print(f"  ✅ Website URL: {website_url}")
                        success += 1
                    else:
                        print(f"  ❌ Website URL取得失敗")
                        failed += 1
                    
                    # 進捗表示
                    if i % 10 == 0:
                        success_rate = (success / i * 100) if i > 0 else 0
                        print(f"\n{'='*60}")
                        print(f"進捗: {i}/{total} 完了 | 成功: {success} | 失敗: {failed}")
                        print(f"成功率: {success_rate:.1f}% | ブラウザ再起動: {driver_restarts}回")
                        print(f"{'='*60}")
                    
                    time.sleep(2)
                    
                except KeyboardInterrupt:
                    print("\n\n⚠️  ユーザーによる中断")
                    raise
                    
                except Exception as e:
                    print(f"  ❌ 予期しないエラー: {type(e).__name__}")
                    print(f"     詳細: {str(e)[:200]}")
                    failed += 1
                    db.session.rollback()
                    
                    try:
                        driver = restart_driver(driver)
                        driver_restarts += 1
                    except Exception as restart_error:
                        print(f"  ❌ ブラウザ再起動失敗: {type(restart_error).__name__}")
                        driver = get_stealth_driver()
                    
                    time.sleep(2)
                    continue
        
        except KeyboardInterrupt:
            print("\n\n⚠️  処理を中断しました")
        
        finally:
            if driver:
                try:
                    driver.quit()
                    print("\n✓ ブラウザを正常終了しました")
                except Exception as e:
                    print(f"\n✗ ブラウザ終了エラー: {type(e).__name__}")
            
            # 最終統計
            success_rate = (success / total * 100) if total > 0 else 0
            
            print(f"\n{'='*60}")
            print(f"=== Phase 1C-2: Website URL取得完了 ===")
            print(f"{'='*60}")
            print(f"処理件数: {total}件")
            print(f"成功: {success}件")
            print(f"失敗: {failed}件")
            print(f"成功率: {success_rate:.1f}%")
            print(f"ブラウザ再起動回数: {driver_restarts}回")
            
            # 現在の全体状況
            total_salons = Salon.query.count()
            with_website = Salon.query.filter(Salon.website_url.isnot(None)).count()
            
            print(f"\n現在の全体状況:")
            print(f"  総クリニック数: {total_salons}件")
            print(f"  Website URL有り: {with_website}件")
            print(f"  Website URL取得率: {with_website/total_salons*100:.1f}% ({with_website}/{total_salons})")
            print(f"  残りWebsite URL未取得: {total_salons - with_website}件")
            print(f"{'='*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CIDからWebsite URLを取得')
    parser.add_argument('--test', action='store_true', help='テストモード（10件のみ）')
    args = parser.parse_args()
    
    if args.test:
        print("🧪 テストモード: 10件のみ処理")
        enrich_website_url(limit=10)
    else:
        enrich_website_url()
