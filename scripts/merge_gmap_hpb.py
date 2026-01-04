#!/usr/bin/env python3
"""
GmapとHPBのデータをマージするユーティリティ

【マージ戦略】
1. 同一クリニックの判定基準:
   - 住所の類似度（Levenshtein距離 or 部分一致）
   - 名前の類似度（fuzzy matching）
   - 電話番号（完全一致）

2. マージ方法:
   - Google Mapsのデータをマスターとする
   - HPBから取得した情報を追加:
     * hotpepper_url
     * name_hpb（HPB上の名前）
   - レビューデータは両方保持（ReviewSummaryに2レコード）

3. 自動マージのタイミング:
   - HPBスクレイピング実行時に自動マッチング
   - 手動マージ用の管理画面機能も用意
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Biz
from difflib import SequenceMatcher
import re

def normalize_address(address):
    """住所を正規化（全角→半角、空白削除など）"""
    if not address:
        return ""
    
    # 全角数字を半角に
    address = address.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    # 全角ハイフンを半角に
    address = address.replace('－', '-').replace('ー', '-')
    # 空白削除
    address = address.replace(' ', '').replace('　', '')
    # 「丁目」「番地」などの表記揺れを統一
    address = re.sub(r'[−‐－―ー]', '-', address)
    
    return address

def normalize_name(name):
    """クリニック名を正規化"""
    if not name:
        return ""
    
    # 空白削除
    name = name.replace(' ', '').replace('　', '')
    # カタカナの表記揺れを統一
    name = name.replace('ヴ', 'ブ').replace('ヰ', 'イ').replace('ヱ', 'エ')
    # 全角英数字を半角に
    name = name.translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ))
    # 小文字に統一
    name = name.lower()
    
    return name

def calculate_similarity(str1, str2):
    """2つの文字列の類似度を計算（0.0〜1.0）"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1, str2).ratio()

def find_matching_salon(hpb_salon, threshold_address=0.85, threshold_name=0.70):
    """
    HPBのサロンデータに対して、既存のGmapサロンから
    マッチする可能性が高いものを探す
    
    Args:
        hpb_salon: HPBから取得したサロン情報（dict or Biz object）
        threshold_address: 住所の類似度閾値
        threshold_name: 名前の類似度閾値
    
    Returns:
        マッチしたSalonオブジェクト、またはNone
    """
    # HPBサロンの情報を正規化
    hpb_address = normalize_address(hpb_salon.get('address', '') if isinstance(hpb_salon, dict) else hpb_salon.address or '')
    hpb_name = normalize_name(hpb_salon.get('name_hpb', '') if isinstance(hpb_salon, dict) else hpb_salon.name_hpb or '')
    
    if not hpb_address and not hpb_name:
        return None
    
    # Google Mapsから取得済みのサロンを検索
    # hotpepper_urlがNullのものを対象（まだマージされていないもの）
    candidates = Biz.query.filter(
        Biz.hotpepper_url.is_(None),
        Biz.address.isnot(None)
    ).all()
    
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        # 住所の類似度
        candidate_address = normalize_address(candidate.address or '')
        address_similarity = calculate_similarity(hpb_address, candidate_address)
        
        # 名前の類似度
        candidate_name = normalize_name(candidate.name or '')
        name_similarity = calculate_similarity(hpb_name, candidate_name)
        
        # 総合スコア（住所を重視: 70%、名前: 30%）
        total_score = address_similarity * 0.7 + name_similarity * 0.3
        
        # 閾値チェック
        if address_similarity >= threshold_address or name_similarity >= threshold_name:
            if total_score > best_score:
                best_score = total_score
                best_match = candidate
    
    return best_match

def merge_salon_data(gmap_salon, hpb_data):
    """
    GmapサロンにHPBデータをマージ
    
    Args:
        gmap_salon: Gmapから取得したSalonオブジェクト
        hpb_data: HPBから取得したデータ（dict）
            - name_hpb: HPB上の名前
            - hotpepper_url: HPBのURL
    
    Returns:
        bool: マージ成功/失敗
    """
    try:
        if not gmap_salon.hotpepper_url:
            gmap_salon.hotpepper_url = hpb_data.get('hotpepper_url')
        
        if not gmap_salon.name_hpb:
            gmap_salon.name_hpb = hpb_data.get('name_hpb')
        
        db.session.commit()
        return True
    
    except Exception as e:
        print(f"マージエラー: {e}")
        db.session.rollback()
        return False

def auto_merge_hpb_with_gmap():
    """
    HPBで取得したサロンを自動的にGmapサロンとマージ
    """
    with app.app_context():
        print("=" * 70)
        print("HPB ⇔ Gmap 自動マージを開始")
        print("=" * 70)
        
        # HPBからのみ取得されたサロン（hotpepper_urlのみ）
        hpb_only_salons = Biz.query.filter(
            Biz.hotpepper_url.isnot(None),
            Biz.place_id.is_(None)  # Google MapのデータがないもeIAA
        ).all()
        
        print(f"\nHPBのみのサロン: {len(hpb_only_salons)}件")
        
        matched_count = 0
        
        for i, hpb_salon in enumerate(hpb_only_salons, 1):
            print(f"\n({i}/{len(hpb_only_salons)}) {hpb_salon.name_hpb} をマッチング中...")
            
            # マッチング
            gmap_match = find_matching_salon(hpb_salon)
            
            if gmap_match:
                print(f"  ✓ マッチ: {gmap_match.name} (住所: {gmap_match.address})")
                
                # マージ
                success = merge_salon_data(gmap_match, {
                    'name_hpb': hpb_salon.name_hpb,
                    'hotpepper_url': hpb_salon.hotpepper_url
                })
                
                if success:
                    matched_count += 1
                    # HPBのみのレコードは削除（マージ済み）
                    db.session.delete(hpb_salon)
                    db.session.commit()
            else:
                print(f"  - マッチなし")
        
        print("\n" + "=" * 70)
        print(f"自動マージ完了: {matched_count}件をマージ")
        print("=" * 70)

if __name__ == '__main__':
    auto_merge_hpb_with_gmap()
