#!/usr/bin/env python3
"""
Phase 1Cのログからエラーが発生したクリニックを抽出
"""
import sys
import os
import re

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Biz

def extract_failed_from_log(log_file='website_scrape.log'):
    """ログファイルからエラーが発生したクリニック名を抽出"""
    
    failed_clinics = []
    current_clinic = None
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            # クリニック名の行を検出
            match = re.match(r'\[(\d+)/\d+\] (.+)', line)
            if match:
                current_clinic = match.group(2).strip()
            
            # エラー行を検出
            if 'エラー:' in line and current_clinic:
                error_type = line.split('エラー:')[1].strip()[:100]
                failed_clinics.append({
                    'name': current_clinic,
                    'error': error_type
                })
                current_clinic = None
    
    return failed_clinics

def get_failed_clinics_from_db():
    """DBから「URLあるが連絡先情報なし」のクリニックを取得"""
    
    with app.app_context():
        # website_urlはあるが、phone/email/inquiry_urlが全て空
        failed = Biz.query.filter(
            Biz.website_url.isnot(None),
            Biz.website_url != '',
            Biz.phone.is_(None),
            Biz.email.is_(None),
            Biz.inquiry_url.is_(None)
        ).all()
        
        return failed

def export_failed_to_csv(output_file='failed_clinics.csv'):
    """エラーが発生したクリニックをCSV出力"""
    
    import csv
    
    # ログから抽出
    log_failed = extract_failed_from_log()
    
    # DBから抽出
    db_failed = get_failed_clinics_from_db()
    
    print(f"=== エラー発生クリニック抽出結果 ===")
    print(f"ログから: {len(log_failed)}件")
    print(f"DBから: {len(db_failed)}件")
    
    # CSV出力（DB版）
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'クリニック名', '公式サイト', '住所', 'GoogleマップURL'])
        
        for salon in db_failed:
            gmap_url = f"https://www.google.com/maps/search/?api=1&query={salon.name} {salon.address}" if salon.address else ''
            writer.writerow([
                salon.id,
                salon.name,
                salon.website_url,
                salon.address,
                gmap_url
            ])
    
    print(f"\n✓ CSV出力完了: {output_file}")
    print(f"  → 手動チェック対象: {len(db_failed)}件")
    
    # ログファイルからのエラー種別を集計
    if log_failed:
        error_types = {}
        for item in log_failed:
            error_key = item['error'].split('\n')[0][:50]  # 最初の50文字
            error_types[error_key] = error_types.get(error_key, 0) + 1
        
        print("\n主なエラー種別:")
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {count}件: {error}")

if __name__ == '__main__':
    export_failed_to_csv()
