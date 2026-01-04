import sys
import time
import re
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from app import app, db
from models import Biz, Job


def scrape_and_save_jobs(biz_id, url):
    """
    指定されたURLから求人情報をスクレイピングし、DBに保存する。
    （ランダム化されたクラス名に対応する最終版）
    """
    print(f"--- [Biz ID: {biz_id}] のスクレイピング開始: {url} ---")
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        driver.get(url)
        time.sleep(3)
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # --- ▼▼▼ 新しいHTML解析ロジック ▼▼▼ ---
        # 1. まず、本来の検索結果を囲んでいる大きな箱を見つける
        main_results_container = soup.find('div', class_='p-search-cassettes-outer')

        job_links = []
        if main_results_container:
            # 2. その箱の中から、求人詳細ページへのリンクをすべて探す
            job_links = main_results_container.find_all('a', href=re.compile(r'^/job/B.*'))
        # --- ▲▲▲ 新しいHTML解析ロジック ▲▲▲ ---

        if not job_links:
            print("求人リンクが見つかりませんでした。")
            return

        # --- DB保存処理 ---
        Job.query.filter_by(biz_id=biz_id).delete()
        new_jobs = []
        for link_tag in job_links:
            # リンクタグのテキストだけでは不十分な場合があるため、
            # リンクタグが含まれる親要素から、より確実なタイトルを探す
            parent_p = link_tag.find_parent('p')
            title = parent_p.get_text(strip=True) if parent_p else "タイトル不明"

            job_url = link_tag.get('href', "URL不明")
            if job_url.startswith('/'):
                job_url = 'https://relax-job.com' + job_url

            job = Job(title=title, job_url=job_url, biz_id=biz_id)
            new_jobs.append(job)

        salon = Biz.query.get(biz_id)
        if salon:
            salon.rejob_url = url

        db.session.add_all(new_jobs)
        db.session.commit()
        print(f"\n--- {len(new_jobs)}件の求人情報をDBに保存しました ---")

    except Exception as e:
        db.session.rollback()
        print(f"予期せぬエラーが発生しました: {e}")
    finally:
        if driver:
            driver.quit()



def run_scraper(start_id=None, end_id=None):
    """
    DBに登録されているサロンに対してスクレイピングを実行するマスター関数。
    IDやID範囲の指定も可能。
    """
    with app.app_context():
        if start_id and end_id:
            print(f"--- IDが {start_id} から {end_id} のサロンを対象とします ---")
            salons = Biz.query.filter(Biz.id.between(start_id, end_id)).order_by(Biz.id).all()
        elif start_id:
            print(f"--- IDが {start_id} のサロンを対象とします ---")
            salons = Biz.query.filter_by(id=start_id).all()
        else:
            print("--- 全てのサロンを対象とします ---")
            salons = Biz.query.all()

        if not salons:
            print("対象のサロンがDBに登録されていません。")
            return

        print(f"合計 {len(salons)}件のサロンを処理します。")

        for salon in salons:
            address = salon.address
            if ' ' in address:
                address_without_postal = address.split(' ', 1)[1]
            else:
                address_without_postal = address

            match = re.search(r'.*?[都道府県].*?[市区町村]', address_without_postal)
            if match:
                area = match.group(0)
            else:
                area = address_without_postal

            search_query = f"{salon.name} {area}"
            encoded_query = urllib.parse.quote(search_query)
            target_url = f"https://relax-job.com/search?keywords={encoded_query}"

            print(f"\n▼ サロン '{salon.name}' (ID: {salon.id}) の検索を開始します。")
            print(f"   検索URL: {target_url}")

            scrape_and_save_jobs(salon.id, target_url)
            print(f"▲ サロン '{salon.name}' の検索が完了しました。")
            time.sleep(5)

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 0:
        run_scraper()
    elif len(args) == 1:
        try:
            start_id = int(args[0])
            run_scraper(start_id=start_id)
        except ValueError:
            print("エラー: IDは数字で指定してください。")
    elif len(args) == 2:
        try:
            start_id = int(args[0])
            end_id = int(args[1])
            if start_id > end_id:
                print("エラー: 開始IDは終了IDより小さくしてください。")
            else:
                run_scraper(start_id=start_id, end_id=end_id)
        except ValueError:
            print("エラー: IDは数字で指定してください。")
    else:
        print("引数が多すぎます。")
        print("使い方:")
        print("  python3 scraper.py          (全件実行)")
        print("  python3 scraper.py 5        (ID=5のみ実行)")
        print("  python3 scraper.py 5 10     (ID=5から10まで実行)")



