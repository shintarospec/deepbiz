#!/usr/bin/env python3
"""
Biz → Biz リネームマイグレーションスクリプト

テーブル名、カラム名、外部キーを全て変更します。
実行前に必ずバックアップを取ってください！
"""
import sys
import os
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = '/var/www/salon_app/instance/biz_data.db'  # VPS用
# DB_PATH = os.path.join(os.path.dirname(__file__), '../instance/biz_data.db')  # ローカル用

def backup_database():
    """データベースをバックアップ"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.replace('.db', f'_backup_{timestamp}.db')
    
    print(f"=== データベースバックアップ ===")
    print(f"元: {DB_PATH}")
    print(f"先: {backup_path}")
    
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ バックアップ完了\n")
    
    return backup_path

def migrate_tables(conn):
    """テーブルをリネーム"""
    cursor = conn.cursor()
    
    print("=== テーブルリネーム ===")
    
    # 1. salon → biz
    print("1. salon → biz")
    cursor.execute("ALTER TABLE salon RENAME TO biz;")
    print("  ✓ 完了")
    
    # 2. biz_categories → biz_categories
    print("2. biz_categories → biz_categories")
    cursor.execute("ALTER TABLE biz_categories RENAME TO biz_categories;")
    print("  ✓ 完了")
    
    # 3. biz_categoriesのカラム名変更
    print("3. biz_categoriesのカラム名変更")
    # SQLiteは直接カラムリネームできないので、新テーブル作成→データコピー→削除→リネーム
    cursor.execute("""
        CREATE TABLE biz_categories_new (
            biz_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (biz_id, category_id),
            FOREIGN KEY(biz_id) REFERENCES biz (id) ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES category (id) ON DELETE CASCADE
        );
    """)
    cursor.execute("""
        INSERT INTO biz_categories_new (biz_id, category_id)
        SELECT biz_id, category_id FROM biz_categories;
    """)
    cursor.execute("DROP TABLE biz_categories;")
    cursor.execute("ALTER TABLE biz_categories_new RENAME TO biz_categories;")
    print("  ✓ 完了")
    
    conn.commit()
    print()

def migrate_foreign_keys(conn):
    """外部キーを持つテーブルを更新"""
    cursor = conn.cursor()
    
    print("=== 外部キー更新 ===")
    
    # ReviewSummary
    print("1. review_summary.biz_id → biz_id")
    cursor.execute("""
        CREATE TABLE review_summary_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            biz_id INTEGER NOT NULL,
            source_name VARCHAR(50) NOT NULL,
            rating FLOAT,
            count INTEGER,
            FOREIGN KEY(biz_id) REFERENCES biz (id),
            UNIQUE(biz_id, source_name)
        );
    """)
    cursor.execute("""
        INSERT INTO review_summary_new (id, biz_id, source_name, rating, count)
        SELECT id, biz_id, source_name, rating, count FROM review_summary;
    """)
    cursor.execute("DROP TABLE review_summary;")
    cursor.execute("ALTER TABLE review_summary_new RENAME TO review_summary;")
    print("  ✓ 完了")
    
    # Job
    print("2. job.biz_id → biz_id")
    cursor.execute("""
        CREATE TABLE job_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            biz_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            source VARCHAR(50),
            source_url VARCHAR(500),
            salary VARCHAR(200),
            employment_type VARCHAR(100),
            FOREIGN KEY(biz_id) REFERENCES biz (id)
        );
    """)
    cursor.execute("""
        INSERT INTO job_new (id, biz_id, title, source, source_url, salary, employment_type)
        SELECT id, biz_id, title, source, source_url, salary, employment_type FROM job;
    """)
    cursor.execute("DROP TABLE job;")
    cursor.execute("ALTER TABLE job_new RENAME TO job;")
    print("  ✓ 完了")
    
    # Coupon
    print("3. coupon.biz_id → biz_id")
    cursor.execute("""
        CREATE TABLE coupon_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255) NOT NULL,
            biz_id INTEGER NOT NULL,
            FOREIGN KEY(biz_id) REFERENCES biz (id)
        );
    """)
    cursor.execute("""
        INSERT INTO coupon_new (id, title, biz_id)
        SELECT id, title, biz_id FROM coupon;
    """)
    cursor.execute("DROP TABLE coupon;")
    cursor.execute("ALTER TABLE coupon_new RENAME TO coupon;")
    print("  ✓ 完了")
    
    conn.commit()
    print()

def verify_migration(conn):
    """マイグレーション結果を検証"""
    cursor = conn.cursor()
    
    print("=== マイグレーション検証 ===")
    
    # テーブル一覧
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    
    print("存在するテーブル:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count}件")
    
    # 必須テーブルチェック
    required_tables = ['biz', 'biz_categories', 'review_summary', 'job', 'coupon']
    missing = [t for t in required_tables if t not in tables]
    
    if missing:
        print(f"\n⚠️ 不足テーブル: {missing}")
        return False
    
    # 旧テーブルが残っていないか
    old_tables = ['salon', 'biz_categories']
    remaining = [t for t in old_tables if t in tables]
    
    if remaining:
        print(f"\n⚠️ 削除されるべきテーブルが残存: {remaining}")
        return False
    
    print("\n✓ マイグレーション成功！")
    return True

def main():
    print("=" * 60)
    print("Biz → Biz マイグレーション")
    print("=" * 60)
    print()
    
    if not os.path.exists(DB_PATH):
        print(f"エラー: データベースが見つかりません: {DB_PATH}")
        sys.exit(1)
    
    # 確認
    response = input("⚠️ このマイグレーションはデータベースを直接変更します。\n実行前にバックアップを取ります。続行しますか？ (yes/no): ")
    if response.lower() != 'yes':
        print("キャンセルしました")
        sys.exit(0)
    
    # バックアップ
    backup_path = backup_database()
    
    # マイグレーション実行
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = OFF;")  # 外部キー制約を一時的に無効化
        
        migrate_tables(conn)
        migrate_foreign_keys(conn)
        
        conn.execute("PRAGMA foreign_keys = ON;")  # 外部キー制約を再有効化
        
        # 検証
        if verify_migration(conn):
            conn.close()
            print("\n" + "=" * 60)
            print("マイグレーション完了！")
            print(f"バックアップ: {backup_path}")
            print("=" * 60)
        else:
            conn.close()
            print("\n⚠️ マイグレーション検証失敗")
            print(f"バックアップから復元してください: {backup_path}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        print(f"バックアップから復元してください: {backup_path}")
        sys.exit(1)

if __name__ == '__main__':
    main()
