#!/usr/bin/env python3
"""
東京23区の美容クリニック 町名レベルURLを取得するスクリプト
https://clinic.beauty.hotpepper.jp/tokyo/shibuya/jingumae/ のような
詳細エリアURLを収集します。
"""
import time
import re
from selenium import webdriver
from selenium_stealth import stealth
from bs4 import BeautifulSoup

OUTPUT_FILE = "tokyo23_clinic_urls.txt"
BASE_URL = "https://clinic.beauty.hotpepper.jp"

# 東京23区のURL識別パターン
TOKYO_23_WARDS = [
    'chiyoda', 'chuo', 'minato', 'shinjuku', 'bunkyo', 'taito',
    'sumida', 'koto', 'shinagawa', 'meguro', 'ota', 'setagaya',
    'shibuya', 'nakano', 'suginami', 'toshima', 'kita', 'arakawa',
    'itabashi', 'nerima', 'adachi', 'katsushika', 'edogawa'
]

def get_tokyo_23_clinic_urls():
    """
    東京23区の美容クリニックの町名レベルURLを収集
    バックアップの旧スクリプトと同じ方式を使用
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
    
    driver = None
    all_area_urls = set()
    
    try:
        print("=" * 70)
        print("東京23区の美容クリニック 詳細エリアURL収集を開始")
        print("=" * 70)
        
        driver = webdriver.Chrome(options=options)
        stealth(driver,
                languages=["ja-JP", "ja"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)
        
        # 東京都トップページから区のリンクを取得
        tokyo_top_url = f"{BASE_URL}/tokyo/"
        print(f"\n1. 東京都トップページにアクセス: {tokyo_top_url}")
        driver.get(tokyo_top_url)
        time.sleep(5)  # 待機時間を増やす
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        
        # ナビゲーションリストから区のリンクを取得
        nav_links = soup.select('nav.navigation-list ul.c-link-list li a')
        
        print(f"   ナビゲーションリンク検出: {len(nav_links)}件")
        
        ward_urls = []
        for link in nav_links:
            if link.has_attr('href'):
                href = link['href']
                # 東京23区のURLパターン: /tokyo/ward/
                if any(f'/tokyo/{ward}/' in href for ward in TOKYO_23_WARDS):
                    full_url = BASE_URL + href if href.startswith('/') else href
                    # クエリパラメータを除去
                    full_url = full_url.split('?')[0]
                    ward_urls.append(full_url)
        
        print(f"   → {len(ward_urls)}件の23区URLを発見")
        
        if not ward_urls:
            # ナビゲーションリンクが取れない場合、直接23区URLを生成
            print("   ナビゲーションリンクが見つからないため、直接URLを生成します")
            ward_urls = [f"{BASE_URL}/tokyo/{ward}/" for ward in TOKYO_23_WARDS]
        
        # 各区のページから町名レベルのURLを取得
        for i, ward_url in enumerate(ward_urls, 1):
            ward_name = ward_url.split('/')[-2]
            print(f"\n2-{i}. {ward_name} の詳細エリアを取得中...")
            print(f"   URL: {ward_url}")
            
            driver.get(ward_url)
            time.sleep(4)
            
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            # エリア絞り込みリンクを取得
            # 複数のセレクタを試行
            area_links = soup.select('ul.refine-field-modal__items li a')
            if not area_links:
                area_links = soup.select('div.refine-field li a')
            if not area_links:
                # navリストからも試行
                area_links = soup.select('nav ul.c-link-list li a')
            
            print(f"      検出されたリンク: {len(area_links)}件")
            
            found_count = 0
            for link in area_links:
                if link.has_attr('href'):
                    href = link['href']
                    
                    # 区レベルURL（/tokyo/shibuya/）は除外
                    # 町名レベル（/tokyo/shibuya/jingumae/）のみ収集
                    if href.count('/') > 3:  # /tokyo/ward/area/ の形式
                        full_url = BASE_URL + href if href.startswith('/') else href
                        # クエリパラメータを除去
                        full_url = full_url.split('?')[0]
                        
                        # 23区内のURLか確認
                        if f'/tokyo/{ward_name}/' in full_url:
                            all_area_urls.add(full_url)
                            found_count += 1
            
            # 町名URLが見つからない場合は区URLも含める
            if found_count == 0:
                print(f"      詳細エリアが見つからないため、区URLを追加: {ward_url}")
                all_area_urls.add(ward_url)
                found_count = 1
            else:
                print(f"   → {found_count}件の詳細エリアURLを発見")
            
            # レート制限回避
            time.sleep(2)
        
        # 結果を保存
        print("\n" + "=" * 70)
        print(f"収集完了: 合計 {len(all_area_urls)}件のユニークなエリアURLを取得")
        print("=" * 70)
        
        sorted_urls = sorted(list(all_area_urls))
        
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            for url in sorted_urls:
                f.write(url + "\n")
        
        print(f"\n'{OUTPUT_FILE}' に保存しました")
        
        # サンプル表示
        print("\n【取得したURLのサンプル（最初の10件）】")
        for i, url in enumerate(sorted_urls[:10], 1):
            print(f"  {i}. {url}")
        
        return sorted_urls
    
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        if driver:
            driver.quit()
            print("\nブラウザを終了しました")

if __name__ == '__main__':
    get_tokyo_23_clinic_urls()
