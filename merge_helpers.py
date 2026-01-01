"""
HPBとGmapのデータマージ用ヘルパー関数
app.pyから読み込んで使用します
"""
import re
from difflib import SequenceMatcher

def normalize_address_for_matching(address):
    """住所を正規化してマッチング精度を向上"""
    if not address:
        return ""
    address = address.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    address = address.replace('－', '-').replace('ー', '-').replace(' ', '').replace('　', '')
    address = re.sub(r'[−‐－―ー]', '-', address)
    return address

def normalize_name_for_matching(name):
    """クリニック名を正規化してマッチング精度を向上"""
    if not name:
        return ""
    name = name.replace(' ', '').replace('　', '')
    name = name.replace('ヴ', 'ブ').replace('ヰ', 'イ').replace('ヱ', 'エ')
    name = name.translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ))
    return name.lower()

def calculate_text_similarity(str1, str2):
    """2つの文字列の類似度を計算（0.0〜1.0）"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1, str2).ratio()

def try_merge_hpb_with_gmap(hpb_salon, db, Salon):
    """
    HPBで新規登録したサロンに対して、
    Gmapの既存データとマッチするものを探してマージ
    
    Args:
        hpb_salon: HPBサロンオブジェクト
        db: データベースセッション
        Salon: Salonモデル
    
    Returns:
        bool: マージが成功したかどうか
    """
    if not hpb_salon.address:
        return False  # 住所がないとマッチングできない
    
    # 正規化
    hpb_address = normalize_address_for_matching(hpb_salon.address)
    hpb_name = normalize_name_for_matching(hpb_salon.name_hpb or '')
    
    # Gmapから取得済みでHPBがまだ紐付いていないサロンを検索
    candidates = Salon.query.filter(
        Salon.hotpepper_url.is_(None),
        Salon.place_id.isnot(None),  # Gmapデータがある
        Salon.address.isnot(None)
    ).limit(100).all()  # パフォーマンス考慮で上限設定
    
    best_match = None
    best_score = 0.0
    threshold = 0.75  # 類似度閾値
    
    for candidate in candidates:
        candidate_address = normalize_address_for_matching(candidate.address or '')
        candidate_name = normalize_name_for_matching(candidate.name or '')
        
        # 住所と名前の類似度を計算
        address_sim = calculate_text_similarity(hpb_address, candidate_address)
        name_sim = calculate_text_similarity(hpb_name, candidate_name)
        
        # 総合スコア（住所70%、名前30%）
        total_score = address_sim * 0.7 + name_sim * 0.3
        
        if total_score > best_score and total_score >= threshold:
            best_score = total_score
            best_match = candidate
    
    # マッチしたらマージ
    if best_match:
        best_match.hotpepper_url = hpb_salon.hotpepper_url
        best_match.name_hpb = hpb_salon.name_hpb
        db.session.delete(hpb_salon)  # HPBのみのレコードを削除
        db.session.commit()
        print(f"  ✓ Gmapデータとマージ: {best_match.name} (類似度: {best_score:.2f})", flush=True)
        return True
    
    return False
