#!/usr/bin/env python3
"""
Phase 1B: 埋め込みマップからCIDを取得（改善版 v2）
Place IDから埋め込みGoogleマップをロードし、「拡大地図を表示」リンクからCIDを抽出

改善点:
- リトライロジック追加（最大3回）
- ブラウザヘルスチェック機能
- タイムアウト最適化（30秒→15秒）
- WebDriverWait使用（明示的待機）
- ブラウザ再起動間隔短縮（30→15件）
- エラーログ詳細化
"""
import sys
import os
import time
import re

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Biz, get_stealth_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# 設定
MAX_RETRIES = 3  # リトライ回数
PAGE_TIMEOUT = 15  # ページロードタイムアウト（秒）
WAIT_TIMEOUT = 10  # 要素待機タイムアウト（秒）
BROWSER_RESTART_INTERVAL = 15  # ブラウザ再起動間隔（件数）


def is_driver_alive(driver):
    """
    ブラウザが正常に動作しているか確認
    
    Returns:
        bool: 正常ならTrue、異常ならFalse
    """
    try:
        # 簡単なコマンドを実行してみる
        _ = driver.current_url
        return True
    except Exception as e:
        print(f"    ⚠️  ブラウザ異常検知: {type(e).__name__}")
        return False


def restart_driver(driver):
    """
    ブラウザを安全に再起動
    
    Returns:
        WebDriver: 新しいドライバーインスタンス
    """
    try:
        if driver:
            driver.quit()
    except Exception as e:
        print(f"    警告: driver.quit()失敗 - {type(e).__name__}")
    
    time.sleep(2)
    new_driver = get_stealth_driver()
    print(f"    ✓ ブラウザ再起動完了")
    return new_driver


def get_cid_from_place_id(place_id, api_key, driver):
    """
    Place IDから通常のGoogleマップページ経由でCIDを取得（リトライ機能付き）
    
    Args:
        place_id: GoogleマップのPlace ID
        api_key: 使用しない（互換性のため残す）
        driver: Seleniumドライバー
    
    Returns:
        str: CID or None
    """
    if not place_id:
        return None
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 通常のGoogleマップURL（APIキー不要）
            maps_url = f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}"
            
            # タイムアウト設定
            driver.set_page_load_timeout(PAGE_TIMEOUT)
            
            # ページロード
            driver.get(maps_url)
            
            # ページが完全にロードされるまで待機（明示的待機）
            try:
                WebDriverWait(driver, WAIT_TIMEOUT).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except TimeoutException:
                print(f"    警告: ページロード待機タイムアウト（試行 {attempt}/{MAX_RETRIES}）")
            
            # 追加：地図が完全にロードされるまで待機
            time.sleep(5)  # JavaScriptの実行を待つ
            
            # 現在のURLからCIDを抽出（複数回試行）
            for url_check_attempt in range(3):
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
                
                # URLにCIDが含まれていない場合、少し待ってから再チェック
                if url_check_attempt < 2:
                    time.sleep(2)
            
            # URLから取れなかった場合、ページソースから検索
            page_source = driver.page_source
            
            # パターン3: ludocid（最も信頼性が高い）
            match = re.search(r'\"ludocid\":\"(\d+)\"', page_source)
            if match:
                return match.group(1)
            
            # パターン4: data-cid属性
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
            print(f"       URL: {current_url[:100]}...")
            
            if attempt < MAX_RETRIES:
                time.sleep(3)  # リトライ前に待機
                continue
            
            return None
            
        except TimeoutException as e:
            print(f"    ⚠️  タイムアウト (試行 {attempt}/{MAX_RETRIES}): {str(e)[:80]}")
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            return None
            
        except WebDriverException as e:
            print(f"    ❌ WebDriverエラー (試行 {attempt}/{MAX_RETRIES}): {str(e)[:80]}")
            # ブラウザが壊れている可能性が高い
            if attempt < MAX_RETRIES:
                print(f"    → ブラウザ再起動を試みます...")
                # 呼び出し元でdriver再起動が必要
                raise  # 上位でハンドリング
            return None
            
        except Exception as e:
            print(f"    ❌ 予期しないエラー (試行 {attempt}/{MAX_RETRIES}): {type(e).__name__}: {str(e)[:80]}")
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            return None
    
    return None


def enrich_cid(limit=None, skip=0):
    """
    Place IDを持つクリニックにCIDを追加（改善版）
    
    Args:
        limit: 処理件数上限（Noneなら全件）
        skip: スキップする件数（既に処理済みの件数を飛ばす）
    """
    
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
        
        # スキップとリミット適用
        if skip > 0:
            query = query.offset(skip)
        
        if limit:
            query = query.limit(limit)
        
        salons = query.all()
        total = len(salons)
        
        print(f"=== Phase 1B: CID取得開始（改善版 v2） ===")
        print(f"対象クリニック: {total}件（スキップ: {skip}件）")
        print(f"方式: Google Maps URL解析（API課金なし）")
        print(f"改善点:")
        print(f"  - リトライ: 最大{MAX_RETRIES}回")
        print(f"  - ページタイムアウト: {PAGE_TIMEOUT}秒")
        print(f"  - ブラウザ再起動: {BROWSER_RESTART_INTERVAL}件ごと")
        print(f"  - ヘルスチェック: 有効")
        print()
        
        driver = None
        success = 0
        failed = 0
        driver_restarts = 0
        
        try:
            driver = get_stealth_driver()
            
            for i, salon in enumerate(salons, 1):
                actual_index = skip + i  # 実際の処理番号
                print(f"\n[{i}/{total}] ({actual_index}) {salon.name}")
                print(f"  Place ID: {salon.place_id}")
                
                try:
                    # ブラウザヘルスチェック
                    if not is_driver_alive(driver):
                        print(f"  ⚠️  ブラウザ異常を検知、再起動します...")
                        driver = restart_driver(driver)
                        driver_restarts += 1
                    
                    # 定期的なブラウザ再起動（メモリリーク対策）
                    if i > 1 and i % BROWSER_RESTART_INTERVAL == 0:
                        print(f"  🔄 定期ブラウザ再起動中（{BROWSER_RESTART_INTERVAL}件ごと）...")
                        driver = restart_driver(driver)
                        driver_restarts += 1
                    
                    # CID取得
                    cid = None
                    retry_after_browser_restart = False
                    
                    try:
                        cid = get_cid_from_place_id(salon.place_id, api_key, driver)
                    except WebDriverException:
                        # ブラウザ異常時は再起動してリトライ
                        print(f"  🔧 ブラウザ再起動してリトライ...")
                        driver = restart_driver(driver)
                        driver_restarts += 1
                        retry_after_browser_restart = True
                    
                    # ブラウザ再起動後のリトライ
                    if retry_after_browser_restart:
                        try:
                            cid = get_cid_from_place_id(salon.place_id, api_key, driver)
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
                    
                    time.sleep(2)  # レート制限対策
                    
                except KeyboardInterrupt:
                    print("\n\n⚠️  ユーザーによる中断")
                    raise
                    
                except Exception as e:
                    print(f"  ❌ 予期しないエラー: {type(e).__name__}")
                    print(f"     詳細: {str(e)[:200]}")
                    failed += 1
                    db.session.rollback()
                    
                    # エラー時もブラウザ再起動を試みる
                    try:
                        driver = restart_driver(driver)
                        driver_restarts += 1
                    except Exception as restart_error:
                        print(f"  ❌ ブラウザ再起動失敗: {type(restart_error).__name__}")
                        # 新しいドライバーを取得
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
                except:
                    print("\n⚠️  ブラウザ終了時にエラー")
        
        # 最終結果
        print(f"\n{'='*60}")
        print(f"=== Phase 1B: CID取得完了（改善版 v2） ===")
        print(f"{'='*60}")
        print(f"処理件数: {success + failed}件")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")
        if (success + failed) > 0:
            print(f"成功率: {success/(success+failed)*100:.1f}%")
        print(f"ブラウザ再起動回数: {driver_restarts}回")
        
        # 統計情報
        with_cid = Biz.query.filter(Biz.cid.isnot(None)).count()
        with_place_id = Biz.query.filter(Biz.place_id.isnot(None)).count()
        total_salons = Biz.query.count()
        
        print(f"\n現在の全体状況:")
        print(f"  総クリニック数: {total_salons}件")
        print(f"  Place ID有り: {with_place_id}件")
        print(f"  CID有り: {with_cid}件")
        print(f"  CID取得率: {with_cid/with_place_id*100:.1f}% ({with_cid}/{with_place_id})")
        print(f"  残りCID未取得: {with_place_id - with_cid}件")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 1B: CID取得（改善版 v2）')
    parser.add_argument('--limit', type=int, help='処理件数上限（テスト用）')
    parser.add_argument('--skip', type=int, default=0, help='スキップする件数（既処理分）')
    parser.add_argument('--test', action='store_true', help='テストモード（10件のみ処理）')
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 テストモード: 10件のみ処理")
        enrich_cid(limit=10, skip=args.skip)
    else:
        enrich_cid(limit=args.limit, skip=args.skip)
