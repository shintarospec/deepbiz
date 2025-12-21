import csv
import re
from app import app, db
from models import Category, ScrapingTask, Area

CSV_FILE = 'utf_ken_all.csv'

def expand_town_name(town_string):
    """
    「芝（１〜３丁目）」のような文字列を「芝１丁目」「芝２丁目」「芝３丁目」のリストに展開する
    """
    match = re.search(r'(.+?)（(.+?)）', town_string)
    if not match:
        return [town_string]

    base_name = match.group(1)
    parts_str = match.group(2)
    
    # 「、」で区切られたリスト形式（例：４、５丁目）
    if '、' in parts_str:
        suffix = re.search(r'([^\d、]+)$', parts_str)
        suffix = suffix.group(1) if suffix else ''
        numbers = [p.replace(suffix, '') for p in parts_str.split('、')]
        return [f"{base_name}{num}{suffix}" for num in numbers]

    # 「〜」で区切られた範囲形式（例：１〜３丁目）
    if '〜' in parts_str:
        suffix = re.search(r'([^\d〜]+)$', parts_str)
        suffix = suffix.group(1) if suffix else ''
        range_str = parts_str.replace(suffix, '')
        
        try:
            start_str, end_str = range_str.split('〜')
            # 全角数字を半角数字に変換
            start_num = int(start_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            end_num = int(end_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            
            expanded_names = []
            for i in range(start_num, end_num + 1):
                # 半角数字を全角に戻して結合
                num_zenkaku = str(i).translate(str.maketrans('0123456789', '０１２３４５６７８９'))
                expanded_names.append(f"{base_name}{num_zenkaku}{suffix}")
            return expanded_names
        except (ValueError, IndexError):
             return [town_string] # 変換に失敗した場合は元の日付を返す

    return [town_string]

def seed_areas():
    with app.app_context():
        db.session.query(Area).delete()
        db.session.commit()
        print("既存のエリアデータを削除しました。")

        unique_areas = set()
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                prefecture = row[6]
                city = row[7]
                town = row[8]
                
                # 「以下に掲載がない場合」はスキップ
                if town == '以下に掲載がない場合':
                    continue

                # 地名を展開
                expanded_towns = expand_town_name(town)
                for expanded_town in expanded_towns:
                    # 市区町村名と結合して、より細かいエリア名を作成
                    full_area_name = city + expanded_town
                    unique_areas.add((prefecture, full_area_name))
        
        print(f"{len(unique_areas)} 件のユニークなエリアが見つかりました。DBに登録します...")
        
        for prefecture, full_area_name in sorted(list(unique_areas)):
            # cityカラムに完全なエリア名を保存
            area = Area(prefecture=prefecture, city=full_area_name)
            db.session.add(area)
            
        db.session.commit()
        print("エリアDBの作成が完了しました。")

if __name__ == '__main__':
    seed_areas()
