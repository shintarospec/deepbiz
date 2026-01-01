#!/usr/bin/env python3
"""HPBページ構造をデバッグするスクリプト"""
from app import get_stealth_driver
from bs4 import BeautifulSoup
import time

driver = get_stealth_driver()
driver.get("https://clinic.beauty.hotpepper.jp/tokyo/shibuya/")
time.sleep(5)

soup = BeautifulSoup(driver.page_source, "lxml")

# 様々なセレクタを試す
print("=== ページ構造チェック ===")
print(f"li.searchListCassette: {len(soup.select('li.searchListCassette'))}件")
print(f"div.slnCassetteBody: {len(soup.select('div.slnCassetteBody'))}件")
print(f"div.clinic: {len(soup.select('div.clinic'))}件")
print(f"h3.slnName: {len(soup.select('h3.slnName'))}件")

# クリニックっぽいリンクを探す
clinic_links = [a for a in soup.find_all("a", href=True) if "slnH" in a.get("href", "")]
print(f"\nクリニックリンク候補: {len(clinic_links)}件")
for i, link in enumerate(clinic_links[:5], 1):
    print(f"{i}. {link.get_text(strip=True)[:50]} -> {link.get('href')}")

# ページHTMLの一部を保存
print("\n=== HTMLサンプル保存 ===")
with open("debug_hpb.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify()[:10000])
print("debug_hpb.html に最初の10000文字を保存しました")

driver.quit()
