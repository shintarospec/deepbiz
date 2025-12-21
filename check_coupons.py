# app.pyから、Flaskアプリのインスタンス(app)とデータベース(db)を読み込む
from app import app, db
# models.pyから、Couponモデルを読み込む
from models import Coupon

def check_coupons_in_db():
    """データベース内のクーポンを確認する"""
    # Flaskのアプリケーションコンテキスト内でデータベース操作を行う
    with app.app_context():
        salon_id_to_check = 167
        coupons = Coupon.query.filter_by(salon_id=salon_id_to_check).all()
        
        if coupons:
            print(f"{len(coupons)}件のクーポンが見つかりました。")
            for c in coupons:
                print(f"- {c.title}")
        else:
            print("このサロンに関連付けられたクーポンは、データベースに見つかりませんでした。")

# このファイルが直接実行された場合に、上記の関数を呼び出す
if __name__ == '__main__':
    check_coupons_in_db()
