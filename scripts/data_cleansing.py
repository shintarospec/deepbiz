#!/usr/bin/env python3
"""
データクレンジング: ビジネスデータの正規化・標準化
Phase 1C, 1B完了後に実行
"""
import sys
import os
import re

sys.path.append('/var/www/salon_app')
os.chdir('/var/www/salon_app')

from app import app, db, Salon

def normalize_phone_number(phone_str):
    """
    電話番号を標準形式に正規化
    
    Args:
        phone_str: 元の電話番号文字列（複数番号、ハイフンあり/なし混在）
    
    Returns:
        str: 正規化された電話番号（03-1234-5678形式）または None
    """
    if not phone_str:
        return None
    
    # 複数番号がある場合は最初の1つを使用
    phones = phone_str.split(',')
    phone = phones[0].strip()
    
    # 数字のみ抽出
    digits = re.sub(r'\D', '', phone)
    
    # 桁数チェック（10桁または11桁）
    if len(digits) not in [10, 11]:
        return None
    
    # フォーマット変換
    if len(digits) == 10:
        # 03-1234-5678 or 06-1234-5678
        if digits[:2] in ['03', '04', '06']:
            return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        # 0120-123-456
        elif digits[:4] == '0120':
            return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
        else:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    else:  # 11桁
        # 090-1234-5678
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

def remove_zipcode_from_address(address):
    """
    住所から郵便番号を削除
    
    Args:
        address: 元の住所文字列
    
    Returns:
        str: 郵便番号なしの住所
    """
    if not address:
        return None
    
    # 〒123-4567 または 1234567 を削除
    address = re.sub(r'^〒?\d{3}-?\d{4}\s*', '', address)
    return address.strip()

def extract_former_name(name):
    """
    名前から旧名称を抽出
    
    Args:
        name: クリニック名（括弧付き情報含む）
    
    Returns:
        tuple: (現在名, 旧名 or None)
    """
    if not name:
        return name, None
    
    # 「（旧：XXX）」または「(旧:XXX)」パターン
    match = re.search(r'[（(]旧[：:]\s*(.+?)[）)]', name)
    if match:
        former = match.group(1).strip()
        current = re.sub(r'[（(]旧[：:].+?[）)]', '', name).strip()
        return current, former
    
    return name, None

def cleanse_all_data(dry_run=True):
    """
    全データをクレンジング
    
    Args:
        dry_run: Trueの場合は変更せずレポートのみ
    """
    
    with app.app_context():
        salons = Salon.query.all()
        total = len(salons)
        
        stats = {
            'phone_normalized': 0,
            'phone_invalid': 0,
            'address_cleaned': 0,
            'former_name_extracted': 0,
            'closed_flagged': 0,
        }
        
        print(f"=== データクレンジング{'（DRY RUN）' if dry_run else ''} ===")
        print(f"対象: {total}件")
        print()
        
        for i, salon in enumerate(salons, 1):
            changed = False
            
            # 1. 電話番号の正規化
            if salon.phone:
                normalized = normalize_phone_number(salon.phone)
                if normalized and normalized != salon.phone:
                    print(f"[{i}] {salon.name}")
                    print(f"  電話: {salon.phone} → {normalized}")
                    if not dry_run:
                        salon.phone = normalized
                    stats['phone_normalized'] += 1
                    changed = True
                elif not normalized:
                    stats['phone_invalid'] += 1
            
            # 2. 住所から郵便番号削除
            if salon.address and re.match(r'^〒?\d{3}-?\d{4}', salon.address):
                cleaned = remove_zipcode_from_address(salon.address)
                if cleaned != salon.address:
                    if changed:
                        print(f"  住所: {salon.address[:40]}... → {cleaned[:40]}...")
                    if not dry_run:
                        salon.address = cleaned
                    stats['address_cleaned'] += 1
                    changed = True
            
            # 3. 旧名称の抽出
            if salon.name:
                current, former = extract_former_name(salon.name)
                if former:
                    if not changed:
                        print(f"[{i}] {salon.name}")
                    print(f"  名前: {salon.name} → {current}")
                    print(f"  旧名: {former}")
                    if not dry_run:
                        salon.name = current
                        # former_name フィールドは後で追加
                    stats['former_name_extracted'] += 1
                    changed = True
            
            # 4. 閉院フラグ
            if salon.name and ('閉院' in salon.name or '閉鎖' in salon.name):
                if not changed:
                    print(f"[{i}] {salon.name}")
                print(f"  閉院フラグ: ON")
                # is_closed フィールドは後で追加
                stats['closed_flagged'] += 1
                changed = True
            
            if changed and i % 100 == 0:
                print(f"\n--- 進捗: {i}/{total} ---\n")
        
        if not dry_run:
            db.session.commit()
            print("\n✓ データベース更新完了")
        
        print(f"\n=== クレンジング結果 ===")
        print(f"電話番号正規化: {stats['phone_normalized']}件")
        print(f"電話番号不正: {stats['phone_invalid']}件")
        print(f"住所クリーニング: {stats['address_cleaned']}件")
        print(f"旧名称抽出: {stats['former_name_extracted']}件")
        print(f"閉院フラグ: {stats['closed_flagged']}件")

if __name__ == '__main__':
    # デフォルトはDRY RUN（変更なし）
    dry_run = '--execute' not in sys.argv
    
    if dry_run:
        print("DRY RUNモード: データは変更されません")
        print("実行するには --execute オプションを付けてください")
        print()
    
    cleanse_all_data(dry_run=dry_run)
