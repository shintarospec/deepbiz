import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import app, db, scrape_salon_list
from models import ScrapingTask, Category

def process_hpb_task(task_id=None):
    with app.app_context():
        task = None
        if task_id:
            # タスクIDが指定された場合、そのタスクを直接取得
            task = db.session.get(ScrapingTask, task_id)
        else:
            # ID指定なし（cron用）の場合、未実行の最も古いタスクを取得
            task = ScrapingTask.query.filter(
                ScrapingTask.task_type == 'HPB',
                ScrapingTask.status.in_(['未実行', '失敗'])
            ).order_by(ScrapingTask.id.asc()).first()

        if not task:
            # print("実行対象のHPBタスクが見つかりませんでした。") # cronで動かす際は不要なログ
            return

        print(f"[{datetime.now()}] HPBタスクID: {task.id} を実行します。URL: {task.target_url}")
        
        task.status = '実行中'
        task.last_run_at = datetime.now()
        db.session.commit()
        
        category = db.session.get(Category, task.category_id)
        if not category:
            task.status = '失敗'
            db.session.commit()
            return
            
        try:
            scrape_salon_list(task.target_url, category.name, 'skip')
            task.status = '完了'
        except Exception as e:
            task.status = '失敗'
        
        db.session.commit()
        print(f"[{datetime.now()}] HPBタスクID: {task.id} の処理が完了。ステータス: {task.status}")

if __name__ == '__main__':
    # コマンドラインからIDが渡されたかチェック
    if len(sys.argv) > 1:
        task_id_to_run = int(sys.argv[1])
        process_hpb_task(task_id_to_run)
    else:
        process_hpb_task()
