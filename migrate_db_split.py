import os
import shutil
from sqlalchemy import create_engine, inspect, text

# データベースファイルが置かれているフォルダ
INSTANCE_FOLDER = 'instance'
# 公開サイト用DBのファイル名
PUBLIC_DB_NAME = 'salon_data.db'
# スクレイピング用DBのファイル名
SCRAPING_DB_NAME = 'scraping_data.db'

PUBLIC_DB_PATH = os.path.join(INSTANCE_FOLDER, PUBLIC_DB_NAME)
SCRAPING_DB_PATH = os.path.join(INSTANCE_FOLDER, SCRAPING_DB_NAME)

# それぞれのDBに残すべきテーブルを定義
PUBLIC_TABLES = [
    'salon', 'category', 'job', 'coupon', 'advertisement', 'salon_categories',
    'alembic_version' # マイグレーション履歴テーブル
]
SCRAPING_TABLES = [
    'area', 'scraping_task', 'category',
    'alembic_version' # マイグレーション履歴テーブル
]

def migrate_databases():
    """既存のDBを2つに分割する"""
    print("--- データベースの分割処理を開始します ---")

    # 1. 既存のDBをコピーして、スクレイピング用DBを作成
    if os.path.exists(PUBLIC_DB_PATH):
        print(f"'{PUBLIC_DB_PATH}' を '{SCRAPING_DB_PATH}' にコピーしています...")
        shutil.copyfile(PUBLIC_DB_PATH, SCRAPING_DB_PATH)
        print("コピーが完了しました。")
    else:
        print(f"エラー: 元となるデータベース '{PUBLIC_DB_PATH}' が見つかりません。")
        return

    # 2. 公開用DB (salon_data.db) から不要なテーブルを削除
    print("\n--- 公開用DB (salon_data.db) のクリーンアップを開始 ---")
    public_engine = create_engine(f'sqlite:///{PUBLIC_DB_PATH}')
    with public_engine.connect() as connection:
        inspector = inspect(public_engine)
        all_tables = inspector.get_table_names()
        for table_name in all_tables:
            if table_name not in PUBLIC_TABLES:
                print(f"不要なテーブル '{table_name}' を削除します...")
                trans = connection.begin()
                try:
                    # ▼▼▼ text() を使ってSQLを実行するように修正 ▼▼▼
                    connection.execute(text(f'DROP TABLE {table_name}'))
                    trans.commit()
                except Exception as e:
                    print(f"削除中にエラーが発生: {e}")
                    trans.rollback()
    print("公開用DBのクリーンアップが完了しました。")

    # 3. スクレイピング用DB (scraping_data.db) から不要なテーブルを削除
    print("\n--- スクレイピング用DB (scraping_data.db) のクリーンアップを開始 ---")
    scraping_engine = create_engine(f'sqlite:///{SCRAPING_DB_PATH}')
    with scraping_engine.connect() as connection:
        inspector = inspect(scraping_engine)
        all_tables = inspector.get_table_names()
        for table_name in all_tables:
            if table_name not in SCRAPING_TABLES:
                print(f"不要なテーブル '{table_name}' を削除します...")
                trans = connection.begin()
                try:
                    # ▼▼▼ text() を使ってSQLを実行するように修正 ▼▼▼
                    connection.execute(text(f'DROP TABLE {table_name}'))
                    trans.commit()
                except Exception as e:
                    print(f"削除中にエラーが発生: {e}")
                    trans.rollback()
    print("スクレイピング用DBのクリーンアップが完了しました。")

    print("\n--- データベースの分割が完了しました！ ---")

if __name__ == '__main__':
    if not os.path.exists(INSTANCE_FOLDER):
        os.makedirs(INSTANCE_FOLDER)
    migrate_databases()

