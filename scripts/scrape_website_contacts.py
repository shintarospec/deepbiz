#!/usr/bin/env python3
"""
Phase 1C: 公式サイトから問い合わせ情報を取得
- 問い合わせページURL
- メールアドレス
- 電話番号
"""
import sys
import os
import time
import re

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Salon, get_stealth_driver
from selenium.webdriver.common.by import By
from datetime import datetime

def scrape_contact_info(website_url, driver):
    """
    公式サイトから問い合わせ情報を取得
    
    Args:
        website_url: クリニックの公式サイトURL
        driver: Seleniumドライバー
    
    Returns:
        dict: {
            'contact_page_url': str or None,
            'emails': list[str],
            'phones': list[str]
        }
    """
    result = {'contact_page_url': None, 'emails': [], 'phones': []}
    
    try:
        # Step 1: トップページをロード
        driver.get(website_url)
        time.sleep(3)
        
        # Step 2: 問い合わせページリンクを探す
        contact_keywords = [
            'お問い合わせ', '問い合わせ', '問合せ', 'お問合せ',
            'contact', 'Contact', 'CONTACT',
            'ご予約', '予約', '相談', 'カウンセリング'
        ]
        
        contact_link = None
        
        # リンクテキストで検索
        for keyword in contact_keywords:
            try:
                elements = driver.find_elements(By.PARTIAL_LINK_TEXT, keyword)
                if elements:
                    href = elements[0].get_attribute('href')
                    # 外部サイト（予約システム等）を除外
                    if href and (website_url.split('/')[2] in href):
                        contact_link = href
                        break
            except Exception:
                continue
        
        # Step 3: 問い合わせページが見つかったらロード
        if contact_link:
            result['contact_page_url'] = contact_link
            print(f"    問い合わせページ: {contact_link}")
            driver.get(contact_link)
            time.sleep(3)
        
        # Step 4: ページ全体からメール・電話を抽出
        page_source = driver.page_source
        
        # メールアドレス抽出
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, page_source)
        
        # 画像ファイル等のノイズを除外
        emails = [
            email for email in emails 
            if not any(ext in email.lower() for ext in ['.jpg', '.png', '.gif', '.svg', '.css', '.js'])
        ]
        result['emails'] = list(set(emails))[:3]  # 重複除去、最大3件
        
        # 電話番号抽出（日本の固定電話・フリーダイヤル）
        phone_patterns = [
            r'0\d{1,4}[-‐ー]\d{1,4}[-‐ー]\d{4}',  # ハイフン付き
            r'0\d{9,10}',  # ハイフンなし
            r'0120[-‐ー]\d{3}[-‐ー]\d{3,4}',  # フリーダイヤル
        ]
        
        phones = []
        for pattern in phone_patterns:
            found = re.findall(pattern, page_source)
            phones.extend(found)
        
        # 正規化（ハイフンを統一）
        phones = [re.sub(r'[‐ー]', '-', phone) for phone in phones]
        result['phones'] = list(set(phones))[:2]  # 重複除去、最大2件
        
        return result
        
    except Exception as e:
        print(f"    エラー: {e}")
        return result


def enrich_contacts(limit=None):
    """全クリニックの問い合わせ情報を収集"""
    
    with app.app_context():
        # Website URLがあるクリニックを取得
        query = Salon.query.filter(
            Salon.website_url.isnot(None),
            Salon.inquiry_url.is_(None)  # まだ問い合わせページを取得していない
        )
        
        if limit:
            query = query.limit(limit)
        
        salons = query.all()
        total = len(salons)
        
        print(f"=== Phase 1C: 問い合わせ情報取得開始 ===")
        print(f"対象クリニック: {total}件")
        print(f"取得内容: 問い合わせページURL、メールアドレス、電話番号")
        
        driver = None
        success = 0
        failed = 0
        
        try:
            driver = get_stealth_driver()
            
            for i, salon in enumerate(salons, 1):
                print(f"\n[{i}/{total}] {salon.name}")
                print(f"  公式サイト: {salon.website_url}")
                
                try:
                    contact_info = scrape_contact_info(salon.website_url, driver)
                    
                    # DBに保存
                    if contact_info['contact_page_url']:
                        salon.inquiry_url = contact_info['contact_page_url']
                    
                    if contact_info['emails']:
                        salon.email = ', '.join(contact_info['emails'])
                        print(f"    メール: {contact_info['emails']}")
                    
                    if contact_info['phones']:
                        salon.phone = ', '.join(contact_info['phones'])
                        print(f"    電話: {contact_info['phones']}")
                    
                    db.session.commit()
                    success += 1
                    
                    # 進捗表示
                    if i % 10 == 0:
                        print(f"\n--- 進捗: {i}/{total} 完了（成功: {success}, 失敗: {failed}）---")
                    
                    time.sleep(3)  # サーバー負荷対策（重要）
                    
                except Exception as e:
                    print(f"  処理エラー: {e}")
                    failed += 1
                    db.session.rollback()
                    time.sleep(2)
                    continue
        
        finally:
            if driver:
                driver.quit()
        
        print(f"\n=== Phase 1C: 完了 ===")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")
        
        # 統計情報
        with_inquiry = Salon.query.filter(Salon.inquiry_url.isnot(None)).count()
        with_email = Salon.query.filter(Salon.email.isnot(None)).count()
        with_phone = Salon.query.filter(Salon.phone.isnot(None)).count()
        
        print(f"\n現在の状況:")
        print(f"  問い合わせページ有り: {with_inquiry}件")
        print(f"  メール有り: {with_email}件")
        print(f"  電話有り: {with_phone}件")
        print(f"  総クリニック数: {Salon.query.count()}件")


if __name__ == '__main__':
    # 引数で処理件数を指定可能（テスト用）
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    if limit:
        print(f"テストモード: {limit}件のみ処理")
    
    enrich_contacts(limit=limit)
