from app import app, db
from models import Category

# 登録したい初期カテゴリのリスト
INITIAL_CATEGORIES = [
    '美容院',
    'ネイルサロン',
    'まつげエクステサロン',
    'リラクサロン',
    'エステサロン',
    '美容クリニック'
]

def seed_data():
    with app.app_context():
        print("--- カテゴリの初期データ投入を開始します ---")
        
        # 既存のカテゴリ名を一度に取得
        existing_names = {c.name for c in db.session.query(Category).all()}
        
        added_count = 0
        for name in INITIAL_CATEGORIES:
            if name not in existing_names:
                category = Category(name=name)
                db.session.add(category)
                added_count += 1
        
        if added_count > 0:
            db.session.commit()
            print(f"{added_count}件の新規カテゴリを登録しました。")
        else:
            print("全ての初期カテゴリは既に登録済みです。")

        print("--- カテゴリの初期データ投入が完了しました！ ---")

if __name__ == '__main__':
    seed_data()

