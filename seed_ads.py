# app.pyから、Flaskアプリのインスタンス(app)とデータベース(db)を読み込む
from app import app, db
# models.pyから、Advertisementモデルを読み込む
from models import Advertisement

def seed_initial_ads():
    """広告テーブルに初期データを投入する"""
    # Flaskのアプリケーションコンテキスト内でデータベース操作を行う
    with app.app_context():
        # 既存のデータがないか確認
        top_ad = Advertisement.query.filter_by(slot_name='top').first()
        bottom_ad = Advertisement.query.filter_by(slot_name='bottom').first()

        # もし上部広告用のデータがなければ作成
        if not top_ad:
            db.session.add(Advertisement(
                slot_name='top',
                title='ここに上部広告のタイトル',
                description='ここに説明文が入ります。',
                link_url='#'
            ))
            print("上部広告枠の初期データを作成しました。")
        
        # もし下部広告用のデータがなければ作成
        if not bottom_ad:
            db.session.add(Advertisement(
                slot_name='bottom',
                title='ここに下部広告のタイトル',
                description='ここに説明文が入ります。',
                link_url='#'
            ))
            print("下部広告枠の初期データを作成しました。")
            
        # データベースに変更を保存
        db.session.commit()
        print("処理を完了しました。")

# このファイルが直接実行された場合に、上記の関数を呼び出す
if __name__ == '__main__':
    seed_initial_ads()
