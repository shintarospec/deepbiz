#!/usr/bin/env python3
"""HPBサイトの構造を調査"""
import sys
sys.path.append('/var/www/salon_app')
from app import get_stealth_driver
from bs4 import BeautifulSoup
import time

driver = get_stealth_driver()

try:
    # 東京トップページ
    print("=== 東京トップページ ===")
    driver.get("https://clinic.beauty.hotpepper.jp/tokyo/")
    time.sleep(8)
    
    soup = BeautifulSoup(driver.page_source, "lxml")
    title = soup.find("title")
    print(f"Title: {title.get_text() if title else 'None'}")
    
    # 様々なリンク要素を確認
    all_links = soup.find_all("a", href=True)
    tokyo_links = [a for a in all_links if "/tokyo/" in a.get("href", "")]
    print(f"Total links with /tokyo/: {len(tokyo_links)}")
    
    # サンプル表示
    print("\n=== /tokyo/を含むリンク（最初の20件） ===")
    for i, link in enumerate(tokyo_links[:20], 1):
        href = link.get("href")
        text = link.get_text(strip=True)[:40]
        print(f"{i}. {href} -> {text}")
    
    # 渋谷区ページ
    print("\n\n=== 渋谷区ページ ===")
    driver.get("https://clinic.beauty.hotpepper.jp/tokyo/shibuya/")
    time.sleep(8)
    
    soup = BeautifulSoup(driver.page_source, "lxml")
    title = soup.find("title")
    print(f"Title: {title.get_text() if title else 'None'}")
    
    # クリニックリストを探す
    clinic_items = soup.find_all("li", class_=lambda x: x and "cassette" in x.lower())
    print(f"Clinic items (li with 'cassette'): {len(clinic_items)}")
    
    # 詳細エリアリンクを探す
    all_links = soup.find_all("a", href=True)
    shibuya_area_links = [a for a in all_links if "/tokyo/shibuya/" in a.get("href", "") and a.get("href").count("/") > 3]
    print(f"Area links (/tokyo/shibuya/xxx/): {len(shibuya_area_links)}")
    
    if shibuya_area_links:
        print("\n=== 渋谷区のエリアリンク（最初の10件） ===")
        for i, link in enumerate(shibuya_area_links[:10], 1):
            print(f"{i}. {link.get('href')} -> {link.get_text(strip=True)[:30]}")

finally:
    driver.quit()
