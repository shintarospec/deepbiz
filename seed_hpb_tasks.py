import os
from app import app, db
from models import Category, ScrapingTask

# ファイル名と、対応するDB上のカテゴリ名をマッピング
FILE_CATEGORY_MAP = {
    'all_hair_salon_area_urls.txt': '美容院',
    'all_nail_salon_area_urls.txt': 'ネイルサロン',
    'all_eyelash_salon_area_urls.txt': 'まつげエクステサロン',
    'all_relax_salon_area_urls.txt': 'リラクサロン',
    'all_esthe_salon_area_urls.txt': 'エステサロン',
    'all_clinic_area_urls.txt': '美容クリニック',
}

def seed_hpb_tasks():
    with app.app_context():
        total_added = 0
        for filename, category_name in FILE_CATEGORY_MAP.items():
            print(f"--- 処理中: {filename} ---")
            
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                print(f"エラー: カテゴリ '{category_name}' がDBに存在しません。スキップします。")
                continue

            if not os.path.exists(filename):
                print(f"警告: ファイル '{filename}' が見つかりません。スキップします。")
                continue

            with open(filename, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            count_in_file = 0
            for url in urls:
                exists = ScrapingTask.query.filter_by(target_url=url).first()
                if not exists:
                    # task_type='HPB' を指定
                    task = ScrapingTask(
                        task_type='HPB',
                        target_url=url,
                        category_id=category.id,
                        status='未実行'
                    )
                    db.session.add(task)
                    count_in_file += 1
            
            # ▼▼▼ 改善点 ▼▼▼
            # ループの外で、ファイルごとに1回だけコミットする
            if count_in_file > 0:
                db.session.commit()
                print(f"{count_in_file} 件の新規タスクを登録しました。")
                total_added += count_in_file
            else:
                print("新規登録対象のタスクはありませんでした（登録済み）。")
    
    print(f"\n--- 完了 ---")
    print(f"合計 {total_added} 件のタスクをデータベースに登録しました。")

if __name__ == '__main__':
    seed_hpb_tasks()
