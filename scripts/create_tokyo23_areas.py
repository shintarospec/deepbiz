#!/usr/bin/env python3
"""
東京23区のみのエリアデータを作成するスクリプト
既存の Area テーブルから23区のデータのみを抽出します。
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Area
from flask import Flask

# Flaskアプリの初期化
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '../instance/biz_data.db')}"
app.config['SQLALCHEMY_BINDS'] = {
    'scraping': f"sqlite:///{os.path.join(os.path.dirname(__file__), '../instance/scraping_data.db')}"
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 東京23区のリスト
TOKYO_23_WARDS = [
    '千代田区', '中央区', '港区', '新宿区', '文京区', '台東区',
    '墨田区', '江東区', '品川区', '目黒区', '大田区', '世田谷区',
    '渋谷区', '中野区', '杉並区', '豊島区', '北区', '荒川区',
    '板橋区', '練馬区', '足立区', '葛飾区', '江戸川区'
]

def main():
    with app.app_context():
        print("=== 東京23区エリアデータ抽出開始 ===\n")
        
        # 23区のエリアデータ統計を表示
        for ward in TOKYO_23_WARDS:
            count = Area.query.filter(
                Area.prefecture == '東京都',
                Area.city.like(f'{ward}%')
            ).count()
            print(f"{ward}: {count}エリア")
        
        # 全体の統計
        total_23 = Area.query.filter(
            Area.prefecture == '東京都',
            Area.city.like('%区%')
        ).count()
        
        total_all = Area.query.filter(Area.prefecture == '東京都').count()
        
        print(f"\n合計:")
        print(f"  23区エリア数: {total_23}")
        print(f"  東京都全体: {total_all}")
        print(f"  削減率: {100 - (total_23 / total_all * 100):.1f}%")
        
        print("\n=== 完了 ===")

if __name__ == '__main__':
    main()
