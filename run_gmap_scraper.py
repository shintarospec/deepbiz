import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import app, db, scrape_gmap_and_save
from models import ScrapingTask, Category

def process_gmap_task(task_id=None):
    with app.app_context():
        task = None
        if task_id:
            task = db.session.get(ScrapingTask, task_id)
        else:
            five_days_ago = datetime.utcnow() - timedelta(days=5)
            task = ScrapingTask.query.filter(
                ScrapingTask.task_type == 'GMAP',
                ScrapingTask.status.in_(['未実行', '失敗']),
                (ScrapingTask.last_run_at == None) | (ScrapingTask.last_run_at < five_days_ago)
            ).order_by(ScrapingTask.id.asc()).first()

        if not task:
            return

        category = db.session.get(Category, task.category_id)
        if not category:
            task.status = '失敗'
            db.session.commit()
            return

        scrape_gmap_and_save(task.id, task.search_keyword, category.name, 'skip')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        task_id_to_run = int(sys.argv[1])
        process_gmap_task(task_id_to_run)
    else:
        process_gmap_task()

