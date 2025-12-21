from app import app, db
from models import Category
from sqlalchemy import text

def sync_data():
    with app.app_context():
        print("--- Categoryテーブルを 'instance/scraping_data.db' に同期します ---")

        try:
            # 1. 公開サイト用DBから全てのカテゴリを取得
            # db.session.get_bind(None) を使って、明示的にデフォルトDBに接続
            main_db_session = db.session
            all_categories = main_db_session.query(Category).all()
            
            if not all_categories:
                print("同期するカテゴリデータがありません。")
                return

            # 2. スクレイピング用DBのエンジンを取得
            scraping_engine = db.get_engine(bind_key='scraping')
            
            with scraping_engine.connect() as connection:
                # 3. スクレイピング用DBの既存カテゴリテーブルをクリア
                print("スクレイピング用DBの既存categoryテーブルをクリアしています...")
                connection.execute(text("DROP TABLE IF EXISTS category"))
                
                # 4. Categoryモデルのテーブル定義を使って、空のテーブルを再作成
                Category.__table__.create(bind=connection)
                print("スクレイピング用DBに新しいcategoryテーブルを作成しました。")

                # 5. 取得したカテゴリデータをスクレイピング用DBに一括で書き込み
                for cat_data in all_categories:
                    stmt = Category.__table__.insert().values(id=cat_data.id, name=cat_data.name)
                    connection.execute(stmt)
                
                connection.commit()

            print(f"{len(all_categories)}件のカテゴリデータを同期しました。")
            print("--- 同期が完了しました！ ---")

        except Exception as e:
            db.session.rollback()
            print(f"データベースエラーが発生しました: {e}")

if __name__ == '__main__':
    sync_data()

