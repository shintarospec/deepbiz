import os
import csv
import requests
import sys
import time
import re
import threading
import urllib.parse
import traceback
from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from werkzeug.utils import secure_filename
from models import db, Salon, Job, Category, Advertisement, Coupon, ScrapingTask, Area, salon_categories, ReviewSummary, CompanyAnalysis
from flask_migrate import Migrate
from datetime import datetime, timedelta
from sqlalchemy import desc, nullslast, text, or_
from functools import wraps
# Selenium関連
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium_stealth import stealth
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
# Google Maps関連
from googlemaps import Client as GoogleMaps
from models import salon_categories 
from sqlalchemy.orm import joinedload

# --- アプリケーションの初期設定 ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-change-this'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'salon_data.db')}"
app.config['SQLALCHEMY_BINDS'] = {
    'scraping': f"sqlite:///{os.path.join(app.instance_path, 'scraping_data.db')}"
}

if not os.path.exists(app.instance_path):
    os.makedirs(app.instance_path)

db.init_app(app)
migrate = Migrate(app, db)

# API Blueprintの登録
from api.company_analysis import api_bp
app.register_blueprint(api_bp)


# --- ヘルパー関数 ---
def clean_data(value):
    if not value: return None
    unwanted_strings = ["URL見つかず", "N/A"]
    if value in unwanted_strings or (isinstance(value, str) and value.strip().startswith("エラー:")): return None
    return value

def get_stealth_driver(driver=None):
    if driver: return driver
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=ja')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.127 Safari/537.36')
    
    # WebDriver検出を回避するための設定
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = uc.Chrome(
        options=options,
        version_main=140,
        use_subprocess=True
    )
    
    # WebDriver特性を隠す
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        '''
    })
    
    return driver

# ... (Google Map ヘルパー関数群は変更なし) ...
def get_gmap_place_details(place_name, api_key, return_list=False):
    gmaps = GoogleMaps(api_key)
    try:
        results = gmaps.places(place_name, language='ja', region='jp').get('results', [])
        if results: return results if return_list else results[0]
    except Exception as e:
        print(f"[Google検索失敗] {e}", flush=True)
    return [] if return_list else None
def get_cid_from_place_id(place_id, driver):
    if not place_id: return None
    gmap_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    try:
        driver.get(gmap_url)
        time.sleep(5)
        final_url = driver.current_url
        cid_match = re.search(r'cid=([0-9]+)', final_url)
        if cid_match: return cid_match.group(1)
        for part in final_url.split('!'):
            if '0x' in part:
                hex_part = part.split(':')[-1]
                try: return str(int(hex_part, 16))
                except ValueError: continue
    except Exception as e:
        print(f"CID取得中にエラー: {e}", flush=True)
    return None
def get_website_from_gmap(driver):
    try: return driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']").get_attribute("href")
    except Exception:
        try: return driver.find_element(By.CSS_SELECTOR, "a[aria-label^='ウェブサイト']").get_attribute("href")
        except Exception: return None
def get_contact_info_from_website(website_url):
    if not website_url: return None, None
    email = None
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(website_url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)))
            if emails: email = ', '.join(emails)
    except Exception as e:
        print(f"公式サイト({website_url})の解析エラー: {e}", flush=True)
    return None, email
def enrich_salon_with_gmap_data(salon_obj, driver):
    search_name = salon_obj.name_hpb or salon_obj.name
    print(f"--- Google Map情報拡充開始: {search_name} ---", flush=True)
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("警告: GOOGLE_MAPS_API_KEYが設定されていません。", flush=True)
        return salon_obj
    try:
        if not salon_obj.place_id:
            place_details = get_gmap_place_details(search_name, api_key)
            if not place_details:
                print("-> Place情報が見つかりませんでした。", flush=True)
                return salon_obj
            salon_obj.name = place_details.get('name')
            salon_obj.place_id = place_details.get('place_id')
            salon_obj.address = place_details.get('formatted_address')
            salon_obj.review_rating = place_details.get('rating')
            salon_obj.review_count = place_details.get('user_ratings_total')
            print(f"-> Place ID: {salon_obj.place_id} を取得しました。", flush=True)
        if salon_obj.place_id:
            salon_obj.cid = get_cid_from_place_id(salon_obj.place_id, driver)
            if salon_obj.cid:
                print(f"-> CID: {salon_obj.cid} を取得しました。", flush=True)
                salon_obj.website_url = get_website_from_gmap(driver)
                if salon_obj.website_url:
                    print(f"-> 公式サイト: {salon_obj.website_url} を取得しました。", flush=True)
                    _, salon_obj.email = get_contact_info_from_website(salon_obj.website_url)
                    if salon_obj.email: print(f"-> Email: {salon_obj.email} を取得しました。", flush=True)
    except Exception as e:
        print(f"Google Map情報取得中にエラーが発生: {e}", flush=True)
    return salon_obj

def get_gmap_details(place_id, api_key):
    """
    Google Places APIから総合評価、レビュー総数、最新のレビュー1件をまとめて取得する。
    """
    if not place_id or not api_key:
        return None
    
    # 取得するフィールドを明示的に指定
    fields = "name,rating,user_ratings_total,reviews"
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields={fields}&language=ja&key={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        data = response.json()

        if data.get("status") == "OK" and "result" in data:
            result = data["result"]
            
            # 総合評価とレビュー総数を格納
            summary_data = {
                'rating': result.get('rating'),
                'count': result.get('user_ratings_total')
            }
            
            # 最新のレビュー1件を格納
            latest_review = None
            if "reviews" in result and result["reviews"]:
                # APIは通常「最も関連性の高い」順で返すため、最初のレビューを取得
                review = result["reviews"][0]
                latest_review = {
                    'author_name': review.get('author_name'),
                    'rating': review.get('rating'),
                    'text': review.get('text'),
                }

            # 辞書形式で両方のデータを返す
            return {
                'summary': summary_data,
                'latest_review': latest_review
            }
        else:
            print(f"Google Places API Error for place_id {place_id}: {data.get('status')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Google Places data for place_id {place_id}: {e}")
        return None


# --- 認証用のデコレータ ---
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        admin_user = os.environ.get('ADMIN_USERNAME')
        admin_pass = os.environ.get('ADMIN_PASSWORD')
        if not auth or not (auth.username == admin_user and auth.password == admin_pass):
            return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

# --- ルーティング (全てのクエリを Flask-SQLAlchemy推奨の書き方に統一) ---
@app.route('/')
def index():
    return redirect(url_for('salon_search'))

@app.route('/search')
def salon_search():
    """美容クリニック検索（東京23区特化版）"""
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    selected_ward = request.args.get('ward', '')  # 23区選択
    sort_by = request.args.get('sort', 'rating')  # デフォルトを評価順に
    
    # 東京23区のリスト
    tokyo_23_wards = [
        '千代田区', '中央区', '港区', '新宿区', '文京区', '台東区',
        '墨田区', '江東区', '品川区', '目黒区', '大田区', '世田谷区',
        '渋谷区', '中野区', '杉並区', '豊島区', '北区', '荒川区',
        '板橋区', '練馬区', '足立区', '葛飾区', '江戸川区'
    ]
    
    # 美容クリニックカテゴリのみ
    clinic_category = Category.query.filter_by(name='美容クリニック').first()
    
    # クエリ構築（美容クリニックのみ）
    query = Salon.query.options(joinedload(Salon.review_summaries))
    if clinic_category:
        query = query.join(Salon.categories).filter(Category.id == clinic_category.id)
    
    # キーワード検索
    if keyword:
        search_term = f"%{keyword}%"
        query = query.filter(Salon.name.ilike(search_term) | Salon.address.ilike(search_term))
    
    # 区で絞り込み
    if selected_ward:
        query = query.filter(Salon.address.like(f"%{selected_ward}%"))
    
    # ソート
    if sort_by == 'rating':
        # Google評価を優先、次にHPB評価
        query = query.outerjoin(ReviewSummary, 
            (ReviewSummary.salon_id == Salon.id) & (ReviewSummary.source_name == 'Google')
        ).order_by(nullslast(desc(ReviewSummary.rating)), Salon.name)
    else:
        query = query.order_by(Salon.name)
    
    pagination = query.paginate(page=page, per_page=20, error_out=False)
    salons = pagination.items
    
    ads = {ad.slot_name: ad for ad in Advertisement.query.all()}
    
    return render_template('salon_search.html', 
        salons=salons, 
        pagination=pagination, 
        keyword=keyword, 
        ward_options=tokyo_23_wards,
        selected_ward=selected_ward,
        sort_by=sort_by, 
        ads=ads
    )

@app.route('/salon/<int:salon_id>')
def salon_detail(salon_id):
    salon = db.session.get(Salon, salon_id)
    if not salon:
        return "サロンが見つかりません", 404

    jobs = Job.query.filter_by(salon_id=salon_id).all()
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    ads = {ad.slot_name: ad for ad in Advertisement.query.all()}

    # --- 口コミ取得とDB保存処理を刷新 ---
    gmap_data = get_gmap_details(salon.place_id, api_key)
    
    if gmap_data and gmap_data.get('summary'):
        summary = gmap_data['summary']
        
        # Googleの総合評価サマリーをDBに保存/更新
        google_summary = ReviewSummary.query.filter_by(salon_id=salon.id, source_name='Google').first()
        if not google_summary:
            google_summary = ReviewSummary(salon_id=salon.id, source_name='Google')
            db.session.add(google_summary)

        # 正しい「総合評価の平均点」と「レビュー総数」を保存する
        google_summary.rating = summary.get('rating')
        google_summary.count = summary.get('count')
        
        db.session.commit()

    # テンプレートに渡すための、最新のレビュー1件の情報をsalonオブジェクトにセット
    if gmap_data and gmap_data.get('latest_review'):
        salon.latest_google_review = gmap_data['latest_review']
    else:
        # データが取得できなかった場合も、キーが存在するようにNoneをセット
        salon.latest_google_review = None
    
    # テンプレートをレンダリングする前に、DBから最新の状態を再読み込み
    db.session.refresh(salon)

    return render_template('salon_detail.html', salon=salon, jobs=jobs, api_key=api_key, ads=ads)

# --- 管理者用機能 ---

@app.route('/admin')
@auth_required
def admin_index():
    """管理画面トップ（東京23区×美容クリニック特化版）"""
    page = request.args.get('page', 1, type=int)
    f_ward = request.args.get('ward', '')  # 23区選択
    f_search_name = request.args.get('search_name', '')
    f_search_address = request.args.get('search_address', '')
    sort_order = request.args.get('sort_order', 'desc')

    # 基本クエリ（美容クリニックのみ）
    clinic_category = Category.query.filter_by(name='美容クリニック').first()
    query = Salon.query
    if clinic_category:
        query = query.join(Salon.categories).filter(Category.id == clinic_category.id)
    
    # 絞り込み条件
    if f_ward:
        query = query.filter(Salon.address.like(f"%{f_ward}%"))
    if f_search_name:
        search_term = f"%{f_search_name}%"
        query = query.filter(or_(Salon.name.like(search_term), Salon.name_hpb.like(search_term)))
    if f_search_address:
        query = query.filter(Salon.address.like(f"%{f_search_address}%"))

    # 並び替え
    if sort_order == 'asc':
        query = query.order_by(Salon.id.asc())
    else:
        query = query.order_by(Salon.id.desc())

    pagination = query.paginate(page=page, per_page=50, error_out=False)
    salons = pagination.items
    
    # 東京23区リスト
    tokyo_23_wards = [
        '千代田区', '中央区', '港区', '新宿区', '文京区', '台東区',
        '墨田区', '江東区', '品川区', '目黒区', '大田区', '世田谷区',
        '渋谷区', '中野区', '杉並区', '豊島区', '北区', '荒川区',
        '板橋区', '練馬区', '足立区', '葛飾区', '江戸川区'
    ]

    return render_template(
        'admin/index.html', 
        salons=salons, 
        pagination=pagination, 
        wards=tokyo_23_wards,
        filters={
            'ward': f_ward,
            'search_name': f_search_name, 
            'search_address': f_search_address
        },
        sort_order=sort_order
    )


@app.route('/admin/bulk_action', methods=['POST'])
@auth_required
def admin_bulk_action():
    action = request.form.get('action')
    selected_ids = request.form.getlist('selected_ids')

    if not action or not selected_ids:
        flash('操作を選択し、少なくとも1つ以上のサロンを選択してください。', 'warning')
        return redirect(url_for('admin_index'))

    # 選択されたIDを整数に変換
    salon_ids = [int(id) for id in selected_ids]
    
    if action == 'delete':
        # --- 一括削除 ---
        Salon.query.filter(Salon.id.in_(salon_ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'{len(salon_ids)}件のサロンを削除しました。', 'success')

    elif action == 'get_jobs':
        # --- 一括求人取得 ---
        salons = Salon.query.filter(Salon.id.in_(salon_ids)).all()
        for salon in salons:
            search_name = salon.name or salon.name_hpb
            if search_name:
                thread = threading.Thread(target=_scrape_rejob_for_salon, args=(app.app_context(), salon.id, search_name))
                thread.start()
        flash(f'{len(salons)}件のサロンの求人情報取得をバックグラウンドで開始しました。', 'info')

    elif action == 'get_hpb_details':
        # --- HPB追加データ取得 (現時点ではプレースホルダー) ---
        flash('「HPB追加データ取得」は現在開発中です。', 'info')
        # ここに将来的に処理を追加

    else:
        flash('無効な操作です。', 'danger')

    return redirect(url_for('admin_index'))


@app.route('/admin/delete/<int:salon_id>', methods=['POST'])
@auth_required
def delete_salon(salon_id):
    salon_to_delete = db.session.get(Salon, salon_id)
    if salon_to_delete:
        db.session.delete(salon_to_delete)
        db.session.commit()
        flash(f'サロン「{salon_to_delete.name}」を削除しました。', 'success')
    return redirect(url_for('admin_index'))

@app.route('/admin/add', methods=['GET', 'POST'])
@auth_required
def add_salon():
    if request.method == 'POST':
        new_salon = Salon(
            name=request.form.get('name'), name_hpb=request.form.get('name_hpb'),
            address=request.form.get('address'), place_id=request.form.get('place_id'), 
            cid=request.form.get('cid'), website_url=request.form.get('website_url'), 
            inquiry_url=request.form.get('inquiry_url'), email=request.form.get('email'),
            hotpepper_url=request.form.get('hotpepper_url')
        )
        category_ids = request.form.getlist('categories')
        new_salon.categories = [db.session.get(Category, int(id)) for id in category_ids]
        db.session.add(new_salon)
        db.session.commit()
        flash(f'サロン「{new_salon.name}」を新しく追加しました。', 'success')
        return redirect(url_for('admin_index'))
    
    all_categories = Category.query.all()
    return render_template('admin/salon_form.html', categories=all_categories, salon=None)

@app.route('/admin/edit/<int:salon_id>', methods=['GET', 'POST'])
@auth_required
def edit_salon(salon_id):
    salon_to_edit = db.session.get(Salon, salon_id)
    if request.method == 'POST':
        salon_to_edit.name = request.form.get('name')
        salon_to_edit.name_hpb = request.form.get('name_hpb')
        salon_to_edit.address = request.form.get('address')
        salon_to_edit.place_id = request.form.get('place_id')
        salon_to_edit.cid = request.form.get('cid')
        salon_to_edit.website_url = request.form.get('website_url')
        salon_to_edit.inquiry_url = request.form.get('inquiry_url')
        salon_to_edit.email = request.form.get('email')
        salon_to_edit.hotpepper_url = request.form.get('hotpepper_url')
        category_ids = request.form.getlist('categories')
        salon_to_edit.categories = [db.session.get(Category, int(id)) for id in category_ids]
        db.session.commit()
        flash(f'サロン「{salon_to_edit.name}」の情報を更新しました。', 'success')
        return redirect(url_for('admin_index'))
    
    all_categories = Category.query.all()
    return render_template('admin/salon_form.html', salon=salon_to_edit, categories=all_categories)

@app.route('/admin/upload', methods=['GET', 'POST'])
@auth_required
def upload_salon_csv():
    # ... (この機能は後で再実装)
    return render_template('admin/upload_salon.html')

@app.route('/admin/ads', methods=['GET', 'POST'])
@auth_required
def manage_ads():
    if request.method == 'POST':
        slot_name = request.form.get('slot_name')
        ad_to_update = Advertisement.query.filter_by(slot_name=slot_name).first_or_404()
        ad_to_update.title = request.form.get('title')
        ad_to_update.description = request.form.get('description')
        ad_to_update.link_url = request.form.get('link_url')
        db.session.commit()
        flash(f'広告枠「{slot_name}」を更新しました。', 'success')
        return redirect(url_for('manage_ads'))
    all_ads = Advertisement.query.order_by(Advertisement.id).all()
    return render_template('admin/manage_ads.html', ads=all_ads)

@app.route('/admin/categories', methods=['GET', 'POST'])
@auth_required
def manage_categories():
    if request.method == 'POST':
        name = request.form.get('category_name')
        if name:
            new_category = Category(name=name)
            db.session.add(new_category)
            db.session.commit()
            flash(f'カテゴリ「{name}」を追加しました。', 'success')
            os.system(f"sudo /var/www/salon_app/venv/bin/python sync_category_table.py")
    all_categories = Category.query.order_by(Category.name).all()
    return render_template('admin/manage_categories.html', categories=all_categories)


@app.route('/admin/scrape_salons', methods=['GET', 'POST'])
@auth_required
def admin_scrape_salons():
    """HPB美容クリニックスクレイピングタスク追加"""
    if request.method == 'POST':
        target_url = request.form.get('url')

        if not target_url:
            flash('URLを指定してください。', 'danger')
            return redirect(url_for('admin_scrape_salons'))
        
        # 美容クリニックカテゴリを取得
        clinic_category = Category.query.filter_by(name='美容クリニック').first()
        if not clinic_category:
            flash('美容クリニックカテゴリが見つかりません。', 'danger')
            return redirect(url_for('admin_scrape_salons'))
        
        # 既存チェック
        exists = ScrapingTask.query.filter_by(target_url=target_url).first()
        if exists:
            flash(f'そのURLのタスクは既に存在します (タスクID: {exists.id})。', 'warning')
        else:
            # HPBタスクを登録
            new_task = ScrapingTask(
                task_type='HPB',
                target_url=target_url,
                category_id=clinic_category.id,
                status='未実行'
            )
            db.session.add(new_task)
            db.session.commit()
            flash(f'新しいHPBタスク (ID: {new_task.id}) を登録しました。', 'success')
        
        return redirect(url_for('scraping_tasks'))

    return render_template('admin/scrape_salons.html')


@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@auth_required
def delete_category(category_id):
    category_to_delete = db.session.get(Category, category_id)
    if category_to_delete:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash(f'カテゴリ「{category_to_delete.name}」を削除しました。', 'success')
        os.system(f"sudo /var/www/salon_app/venv/bin/python sync_category_table.py")
    return redirect(url_for('manage_categories'))


@app.route('/admin/scrape_jobs/<int:salon_id>')
@auth_required
def scrape_jobs_for_salon(salon_id):
    """
    指定されたサロンの求人情報をリジョブから取得するバックグラウンドタスクを開始する。
    """
    salon = db.session.get(Salon, salon_id)
    if not salon:
        flash(f'サロンID {salon_id} が見つかりません。', 'danger')
        return redirect(url_for('admin_index'))
    
    # サロン名がない場合は処理を中止
    search_name = salon.name or salon.name_hpb
    if not search_name:
        flash(f'サロンID {salon_id} に検索可能な名称が設定されていません。', 'warning')
        return redirect(url_for('admin_index'))

    # バックグラウンドでスクレイピング処理を実行
    thread = threading.Thread(target=_scrape_rejob_for_salon, args=(app.app_context(), salon.id, search_name))
    thread.start()

    flash(f'サロン「{search_name}」の求人情報取得を開始しました。', 'info')
    return redirect(url_for('admin_index'))


# --- スクレイピングとタスク管理 ---
@app.route('/admin/tasks', methods=['GET', 'POST']) # methodsに'POST'を復活
@auth_required
def scraping_tasks():
    # --- 新規タスクの手動登録 (POST) ---
    if request.method == 'POST':
        task_type = request.form.get('task_type')
        category_id = request.form.get('category_id')
        
        if not task_type or not category_id:
            flash('タスクタイプとカテゴリは必須です。', 'danger')
        else:
            new_task = ScrapingTask(
                task_type=task_type,
                category_id=category_id,
                target_url=request.form.get('target_url') if task_type == 'HPB' else None,
                search_keyword=request.form.get('search_keyword') if task_type == 'GMAP' else None,
                status='未実行'
            )
            db.session.add(new_task)
            db.session.commit()
            flash('新しいタスクが追加されました。', 'success')
        return redirect(url_for('scraping_tasks'))

    # --- タスク一覧の表示 (GET) ---
    # (この部分のロジックは前回から変更ありません)
    page = request.args.get('page', 1, type=int)
    f_task_type = request.args.get('task_type', '')
    f_prefecture = request.args.get('prefecture', '')
    f_status = request.args.get('status', '')
    f_category_id = request.args.get('category_id', type=int)
    f_start_date = request.args.get('start_date', '')
    f_end_date = request.args.get('end_date', '')
    f_search_id = request.args.get('search_id', '')
    f_search_keyword = request.args.get('search_keyword', '')
    sort_order = request.args.get('sort_order', 'desc')

    query = ScrapingTask.query
    if f_task_type: query = query.filter(ScrapingTask.task_type == f_task_type)
    if f_prefecture: query = query.filter(ScrapingTask.search_keyword.like(f"%{f_prefecture}%"))
    if f_status: query = query.filter(ScrapingTask.status == f_status)
    if f_category_id: query = query.filter(ScrapingTask.category_id == f_category_id)
    if f_start_date: query = query.filter(ScrapingTask.last_run_at >= datetime.strptime(f_start_date, '%Y-%m-%d'))
    if f_end_date:
        end_date_obj = datetime.strptime(f_end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(ScrapingTask.last_run_at < end_date_obj)
    if f_search_id: query = query.filter(ScrapingTask.id == f_search_id)
    if f_search_keyword: query = query.filter(ScrapingTask.search_keyword.like(f"%{f_search_keyword}%"))

    if sort_order == 'asc':
        query = query.order_by(nullslast(ScrapingTask.last_run_at.asc()))
    else:
        query = query.order_by(nullslast(ScrapingTask.last_run_at.desc()))
    
    pagination = query.paginate(page=page, per_page=100, error_out=False)
    tasks = pagination.items

    categories = Category.query.order_by(Category.name).all()
    prefectures = [p[0] for p in db.session.query(Area.prefecture).distinct().order_by(Area.prefecture).all()]
    task_statuses = ['未実行', '実行中', '完了', '失敗']

    for task in tasks:
        task.category_name = next((c.name for c in categories if c.id == task.category_id), '不明')
    
    return render_template(
        'admin/tasks.html', 
        tasks=tasks, pagination=pagination, categories=categories,
        prefectures=prefectures, task_statuses=task_statuses,
        filters={
            'task_type': f_task_type, 'prefecture': f_prefecture, 'status': f_status,
            'category_id': f_category_id, 'start_date': f_start_date, 'end_date': f_end_date,
            'search_id': f_search_id, 'search_keyword': f_search_keyword
        },
        sort_order=sort_order
    )


@app.route('/admin/run_task/<int:task_id>/<update_mode>')
@auth_required
def run_task(task_id, update_mode):
    task = db.session.get(ScrapingTask, task_id)
    if not task:
        flash(f'タスクID {task_id} が見つかりません。', 'danger')
        return redirect(url_for('scraping_tasks'))

    task.status = '実行中'
    task.last_run_at = datetime.now()
    db.session.commit()

    # ▼▼▼▼▼ ログの出力先を権限のある場所に変更 ▼▼▼▼▼
    log_file = os.path.join(app.instance_path, 'manual_task.log')
    
    if task.task_type == 'HPB':
        command = f"nohup /var/www/salon_app/venv/bin/python /var/www/salon_app/run_hpb_scraper.py {task.id} >> {log_file} 2>&1 &"
        os.system(command)
        flash(f'HPBタスク(ID:{task.id})の実行をバックグラウンドで開始しました。', 'info')
    
    elif task.task_type == 'GMAP':
        command = f"nohup /var/www/salon_app/venv/bin/python /var/www/salon_app/run_gmap_scraper.py {task.id} >> {log_file} 2>&1 &"
        os.system(command)
        flash(f'Google Mapタスク(ID:{task.id})の実行をバックグラウンドで開始しました。', 'info')
        
    else:
        flash(f'未対応のタスクタイプです: {task.task_type}', 'danger')
    # ▲▲▲▲▲ ログの出力先を変更 ▲▲▲▲▲
    
    return redirect(url_for('scraping_tasks'))


def scrape_gmap_and_save(task_id, keyword, category_name, update_mode):
    with app.app_context():
        task = db.session.get(ScrapingTask, task_id)
        if not task: return
        
        task.status = '実行中'
        task.last_run_at = datetime.now()
        db.session.commit()
        
        driver = None # driverを再度使うので復活
        try:
            category_obj = Category.query.filter_by(name=category_name).first()
            if not category_obj:
                task.status = '失敗'; db.session.commit(); return

            api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
            place_details_list = get_gmap_place_details(keyword, api_key, return_list=True)

            if not place_details_list:
                task.status = '完了'; db.session.commit(); return

            driver = get_stealth_driver() # driverを初期化
            new_salon_count = 0
            
            for place_details in place_details_list:
                place_id = place_details.get('place_id')
                if not place_id: continue

                existing_salon = Salon.query.filter_by(place_id=place_id).first()
                
                target_salon = None

                if not existing_salon:
                    # --- 新規サロンの場合 ---
                    print(f"新規サロン発見 (Google Map名): {place_details.get('name')}", flush=True)
                    new_salon = Salon(
                        name=place_details.get('name'),
                        place_id=place_id,
                        address=place_details.get('formatted_address')
                    )
                    db.session.add(new_salon)
                    new_salon.categories.append(category_obj)
                    
                    # ▼▼▼▼▼ データ拡充機能を復活 ▼▼▼▼▼
                    enrich_salon_with_gmap_data(new_salon, driver)
                    
                    db.session.commit() # IDを確定
                    target_salon = new_salon
                    new_salon_count += 1
                else:
                    # --- 既存サロンの場合 ---
                    target_salon = existing_salon
                    # update_modeが'overwrite'の場合、情報を更新
                    if update_mode == 'overwrite':
                        print(f"-> 既存サロンを上書き更新: {target_salon.name}", flush=True)
                        target_salon.name = place_details.get('name')
                        target_salon.address = place_details.get('formatted_address')
                        # ▼▼▼▼▼ データ拡充機能を復活 ▼▼▼▼▼
                        enrich_salon_with_gmap_data(target_salon, driver)

                    if not any(cat.id == category_obj.id for cat in target_salon.categories):
                        target_salon.categories.append(category_obj)
                        print(f"-> カテゴリ追加: {target_salon.name} に「{category_name}」を追加", flush=True)

                # --- 評価サマリーの更新 ---
                rating = place_details.get('rating')
                count = place_details.get('user_ratings_total')

                if rating is not None or count is not None:
                    summary = ReviewSummary.query.filter_by(salon_id=target_salon.id, source_name='Google').first()
                    if not summary:
                        summary = ReviewSummary(salon_id=target_salon.id, source_name='Google')
                        db.session.add(summary)
                    summary.rating = rating
                    summary.count = count
                
                db.session.commit()

            task.status = '完了'
            db.session.commit()

        except Exception as e:
            print(f"タスク実行中にエラー: {e}", flush=True)
            task.status = '失敗'
            db.session.commit()
            db.session.rollback()
        finally:
            if driver: # driverを使うので、終了処理も復活
                driver.quit()


def _scrape_rejob_for_salon(app_context, salon_id, salon_name):
    """
    【最終改善版】
    あなたの以前のロジック（ページネーション基準）とbot対策を組み合わせたバージョン
    """
    app_context.push()
    print(f"--- [求人取得開始] サロン: {salon_name} (ID: {salon_id}) ---", flush=True)
    driver = None
    try:
        # 1. 検索URLを構築してアクセス
        encoded_salon_name = urllib.parse.quote(salon_name)
        search_url = f"https://relax-job.com/search?keywords={encoded_salon_name}"

        driver = get_stealth_driver()
        driver.get(search_url)
        time.sleep(5) # ページ読み込みとJS実行を待機

        soup = BeautifulSoup(driver.page_source, 'lxml')

        # 2. ページネーション要素を取得
        pagination_element = soup.find('div', class_='c-pagenation')

        job_link_tags = []
        if pagination_element:
            # ページネーションより前にある求人リンク（aタグ）を全て取得
            # これにより、関連性の低い求人を除外する
            job_link_tags = pagination_element.find_all_previous('a', href=re.compile(r'^/job/B\d+'))
            job_link_tags.reverse() # 順番を元に戻す
            print(f"-> ページネーションを発見。対象求人を{len(job_link_tags)}件に絞り込みました。")
        else:
            # ページネーションがない場合は、ページ全体の求人カードから探す
            print("-> ページネーションが見つからないため、ページ全体の求人カードから検索します。")
            job_cards = soup.select('div.jobCassette')
            for card in job_cards:
                # 会社名でフィルタリング
                company_tag = card.select_one('p.jobCassette__company')
                if company_tag and salon_name in company_tag.get_text(strip=True):
                    title_tag = card.select_one('h3.jobCassette__title a')
                    if title_tag:
                        job_link_tags.append(title_tag)

        if not job_link_tags:
            print("-> 処理対象の求人リンクが見つかりませんでした。")
            return

        # 3. DB保存処理
        Job.query.filter_by(salon_id=salon_id, source='リジョブ').delete()

        new_jobs = []
        for link_tag in job_link_tags:
            title = link_tag.get_text(strip=True)
            source_url = "https://relax-job.com" + link_tag.get('href')

            # 詳細ページから給与などを取得するロジックは、一旦省略しリンク取得を優先
            new_job = Job(
                salon_id=salon_id,
                title=title,
                source='リジョブ',
                source_url=source_url
            )
            new_jobs.append(new_job)

        if new_jobs:
            db.session.add_all(new_jobs)
            db.session.commit()
            print(f"--- [求人取得完了] {len(new_jobs)}件の求人をDBに保存しました。 ---", flush=True)
        else:
            print("--- [求人取得完了] 保存対象の求人はありませんでした。 ---", flush=True)

    except Exception as e:
        print(f"エラーが発生しました: {e}", flush=True)
        db.session.rollback()
    finally:
        if driver:
            driver.quit()
        db.session.close()


# app.py

# ===============================================================
# ▼▼▼ 以下の3つの関数を、app.pyに貼り付けてください ▼▼▼
# (既存の同名関数は削除してください)
# ===============================================================

def _enrich_salon_with_hpb_details(salon_obj, driver):
    """
    【v2】HPB詳細ページから住所を取得するヘルパー関数
    """
    if not salon_obj.hotpepper_url:
        return salon_obj
    try:
        # print(f"-> 詳細情報取得のためアクセス: {salon_obj.hotpepper_url}")
        driver.get(salon_obj.hotpepper_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        info_table = soup.select_one('table.slnDataTbl')
        if info_table:
            rows = info_table.select('tr')
            for row in rows:
                th = row.select_one('th')
                if th and '住所' in th.get_text():
                    td = row.select_one('td')
                    if td:
                        address_text = ' '.join(td.get_text(strip=True).split())
                        salon_obj.address = address_text
                        print(f"-> 住所取得成功: {address_text}")
                        break
    except Exception as e:
        print(f"[HPB詳細解析エラー] {e}", flush=True)
    return salon_obj

def _enrich_salon_with_hpb_reviews(salon_obj, driver):
    """
    【v2】HPB口コミページから評価を取得し、ReviewSummaryテーブルに保存するヘルパー関数
    """
    if not salon_obj or not salon_obj.hotpepper_url:
        return salon_obj
    review_url = salon_obj.hotpepper_url.split('?')[0] + "reviews/"
    try:
        # print(f"-> 口コミ評価取得のためアクセス: {review_url}")
        driver.get(review_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        summary = ReviewSummary.query.filter_by(salon_id=salon_obj.id, source_name='Hot Pepper').first()
        if not summary:
            summary = ReviewSummary(salon_id=salon_obj.id, source_name='Hot Pepper')
            db.session.add(summary)
        rating_summary_p = soup.find('p', class_='reviewPoint', string=re.compile(r'総合'))
        if rating_summary_p:
            rating_span = rating_summary_p.find_next_sibling('p', class_='reviewPointNum')
            if rating_span:
                try:
                    summary.rating = float(rating_span.get_text(strip=True))
                    print(f"-> HPB総合評価取得成功: {summary.rating}")
                except (ValueError, TypeError): pass
        count_tag = soup.select_one('p.reviewRead a')
        if count_tag:
            match = re.search(r'（(\d+)件）', count_tag.get_text(strip=True))
            if match:
                try:
                    summary.count = int(match.group(1))
                    print(f"-> HPB口コミ件数取得成功: {summary.count}")
                except (ValueError, TypeError): pass
    except Exception as e:
        print(f"[HPB口コミ解析エラー] {e}", flush=True)
    return salon_obj


# app.py の scrape_salon_list 関数を以下に置き換えてください

def scrape_salon_list(start_url, category_name, update_mode):
    """
    【v16-final】
    一件ずつDBにコミットすることで、セッションの不整合に起因する
    全てのIntegrityErrorとAttributeErrorを根本的に解決する最終安定版。
    """
    with app.app_context():
        # ▼▼▼【修正点1】import文を関数の先頭に移動 ▼▼▼
        from models import salon_categories

        category_obj = Category.query.filter_by(name=category_name).first()
        if not category_obj:
            print(f"エラー: DBにカテゴリ「{category_name}」が見つかりません。", flush=True)
            return
            
        driver = None
        try:
            driver = get_stealth_driver()
            current_url = start_url
            total_new, total_updated = 0, 0
            page_count = 1

            while current_url:
                processed_urls_this_page = set()
                print(f"\n--- {page_count}ページ目を処理中: {current_url} ---", flush=True)
                driver.get(current_url)
                time.sleep(5)

                soup = BeautifulSoup(driver.page_source, 'lxml')
                
                salon_cards = soup.select('li.searchListCassette')
                if not salon_cards:
                    salon_cards = [body.find_parent('li') for body in soup.select('div.slnCassetteBody')]
                if not salon_cards:
                    salon_cards = soup.select('div.clinic')
                
                if not salon_cards:
                    print("-> 処理対象のサロン・クリニック情報が見つかりませんでした。")
                    break

                # ▼▼▼【修正点2】ページ単位のリストを削除 ▼▼▼
                # page_new_salons = []
                # page_updated_salons = []

                for card in salon_cards:
                    name_tag = card.select_one('h3.slnName a, h3.slcHead a, p.clinic__name a')
                    if not name_tag:
                        continue
                    
                    raw_href = name_tag.get('href')
                    if not raw_href: continue

                    full_url = ""
                    if raw_href.startswith('http'):
                        full_url = raw_href.split('?')[0]
                    elif raw_href.startswith('/'):
                        full_url = "https://clinic.beauty.hotpepper.jp" + raw_href.split('?')[0]
                    else:
                        continue
                    
                    if full_url in processed_urls_this_page:
                        continue
                    processed_urls_this_page.add(full_url)
                    
                    hpb_name = name_tag.get_text(strip=True)
                    
                    # DBから常に最新の状態を取得
                    existing_salon = Salon.query.filter_by(hotpepper_url=full_url).first()
                    
                    if not existing_salon:
                        # HPBのみのデータとして新規登録
                        new_salon = Salon(name_hpb=hpb_name, hotpepper_url=full_url)
                        db.session.add(new_salon)
                        new_salon.categories.append(category_obj)
                        print(f"-> 新規発見: {hpb_name}", flush=True)
                        # ▼▼▼【修正点3】ここで即時コミット▼▼▼
                        db.session.commit() 
                        total_new += 1
                    else:
                        association_exists = db.session.query(salon_categories).filter(
                            salon_categories.c.salon_id == existing_salon.id,
                            salon_categories.c.category_id == category_obj.id
                        ).first() is not None

                        if not association_exists:
                            existing_salon.categories.append(category_obj)
                            print(f"-> 既存サロンにカテゴリ追加: {hpb_name}", flush=True)
                            # ▼▼▼【修正点3】ここで即時コミット▼▼▼
                            db.session.commit()
                            total_updated += 1
                
                # ▼▼▼【修正点4】ページ単位のコミット処理を削除 ▼▼▼
                # if page_new_salons or page_updated_salons:
                #    db.session.commit()
                #    total_new += len(page_new_salons)
                #    total_updated += len(page_updated_salons)

                next_page_tag = soup.select_one('a.iS.arrowR')
                if next_page_tag and '次へ' in next_page_tag.text:
                    current_url = next_page_tag['href']
                else:
                    current_url = None
            
            print(f"\n--- 完了 --- 新規登録:{total_new}件, カテゴリ追加:{total_updated}件", flush=True)

        except Exception as e:
            print(f"エラーが発生しました: {e}", flush=True)
            traceback.print_exc()
            db.session.rollback()
        finally:
            if driver:
                driver.quit()

# ▼▼▼ 【ステップ1】HPB詳細情報取得ヘルパー関数を新規作成 ▼▼▼
# ▼▼▼ この get_hpb_details 関数を、以下の新しい内容に丸ごと置き換えてください ▼▼▼
def get_hpb_details(salon_url):
    """
    単一のHot Pepper BeautyのURLから、追加情報を取得する。
    【真・最終解決版】全カテゴリで口コミ専用ページを参照するようにし、
    クリニック系とその他（美容院・エステ等）でセレクタを正確に使い分ける。
    """
    driver = None
    try:
        driver = get_stealth_driver()
        
        # --- 1. 最初にトップページを開き、住所を取得 ---
        driver.get(salon_url)
        time.sleep(3) 
        soup_main = BeautifulSoup(driver.page_source, 'lxml')
        
        address = None
        address_th = soup_main.find('th', string=lambda t: t and '住所' in t)
        if address_th and address_th.find_next_sibling('td'):
            address = address_th.find_next_sibling('td').get_text(strip=True)

        # --- 2. 評価と口コミ件数を取得 ---
        rating = None
        review_count = None

        # URLによって処理を分岐
        if "clinic.beauty.hotpepper.jp" in salon_url:
            # --- 【クリニック】口コミ専用ページに移動して情報を取得 ---
            reviews_url = salon_url.rstrip('/') + '/reviews/'
            print(f"[診断] クリニック用URLを検出。口コミページへ移動します: {reviews_url}")
            driver.get(reviews_url)
            time.sleep(3)
            soup_reviews = BeautifulSoup(driver.page_source, 'lxml')

            # 総合評価を取得 (span.clinic-review-rating__total-score)
            rating_tag = soup_reviews.select_one('span.clinic-review-rating__total-score')
            if rating_tag:
                try:
                    rating = float(rating_tag.get_text(strip=True))
                except (ValueError, TypeError):
                    print(f"[診断] クリニック評価の数値変換に失敗")
            
            # 口コミ件数を取得 (span.c-search-result-heading__count)
            review_count_tag = soup_reviews.select_one('span.c-search-result-heading__count')
            if review_count_tag:
                review_count_text = review_count_tag.get_text(strip=True)
                count_match = re.search(r'(\d+)', review_count_text)
                if count_match:
                    try:
                        review_count = int(count_match.group(1))
                    except (ValueError, TypeError):
                         print(f"[診断] クリニック口コミ件数の数値変換に失敗")

        else:
            # --- 【美容院・エステ等】口コミ専用ページに移動して情報を取得 ---
            reviews_url = salon_url.rstrip('/') + '/review/'
            print(f"[診断] 美容院・エステ用URLを検出。口コミページへ移動します: {reviews_url}")
            driver.get(reviews_url)
            time.sleep(3)
            soup_reviews = BeautifulSoup(driver.page_source, 'lxml')

            # 総合評価を取得 (dd.reviewRatingMeanScore)
            rating_tag = soup_reviews.select_one('dd.reviewRatingMeanScore')
            if rating_tag:
                try:
                    rating = float(rating_tag.get_text(strip=True))
                except (ValueError, TypeError):
                     print(f"[診断] 美容院・エステ評価の数値変換に失敗")

            # 口コミ件数を取得 (span.numberOfResult)
            review_count_tag = soup_reviews.select_one('span.numberOfResult')
            if review_count_tag:
                review_count_text = review_count_tag.get_text(strip=True)
                count_match = re.search(r'(\d+)', review_count_text)
                if count_match:
                    try:
                        review_count = int(count_match.group(1))
                    except (ValueError, TypeError):
                        print(f"[診断] 美容院・エステ口コミ件数の数値変換に失敗")

        details = {
            'address': address,
            'rating': rating,
            'review_count': review_count
        }
        print(f"HPB詳細取得試行: {salon_url} -> {details}")
        return details

    except Exception as e:
        print(f"HPB詳細情報の取得中にエラーが発生しました: {salon_url}")
        traceback.print_exc()
        return None
    finally:
        if driver:
            driver.quit()

# app.py の末尾あたりに追加

@app.route('/admin/test_hpb_details', methods=['POST'])
# @login_required # ← もし管理者画面にログイン機能があれば、この行のコメントを外してください
def test_hpb_details():
    """
    【改修】単一のサロンIDを受け取り、そのHPB追加情報をテスト取得して結果をJSONで返す。
    タイムアウトを防ぐため、クライアント側で1件ずつリクエストを送信する方式に変更。
    """
    salon_id = request.json.get('salon_id')
    if not salon_id:
        return jsonify({'error': 'サロンIDが指定されていません。'}), 400

    salon = db.session.get(Salon, int(salon_id))
    
    # result_itemの初期化
    result_item = {
        'salon_id': salon_id,
        'salon_name': f"ID:{salon_id}のサロンが見つかりません",
        'url': None,
        'status': 'Error',
        'details': None
    }

    if salon:
        result_item['salon_name'] = salon.name_hpb or salon.name
        if salon.hotpepper_url:
            result_item['url'] = salon.hotpepper_url
            details = get_hpb_details(salon.hotpepper_url)
            if details:
                result_item['status'] = 'Success'
                result_item['details'] = details
            else:
                result_item['status'] = 'Failed'
        else:
            result_item['status'] = 'No URL'
    
    return jsonify(result_item)


@app.route('/admin/test_company_analysis')
def test_company_analysis():
    """企業分析テスト画面"""
    return render_template('admin/test_company_analysis.html')


@app.route('/admin/test_company_analysis_api', methods=['POST'])
def test_company_analysis_api():
    """
    企業分析APIのテスト実行エンドポイント
    
    Request JSON:
        {
            "url": "https://www.example.co.jp/",
            "sample_text": "企業情報テキスト" (オプション)
        }
    
    Response JSON:
        {
            "success": true,
            "data": {
                "businessDescription": "...",
                "industry": "...",
                "strengths": [...],
                "targetCustomers": "...",
                "keyTopics": [...],
                "companySize": "...",
                "painPoints": [...]
            },
            "tokens_used": {
                "input": 338,
                "output": 268,
                "total": 606
            },
            "cost": 0.000026,
            "error": null
        }
    """
    from services.gemini_analyzer import GeminiAnalyzer
    from services.web_scraper import WebScraper
    from dotenv import load_dotenv
    
    # .envファイルを読み込み
    load_dotenv()
    
    try:
        data = request.json
        url = data.get('url')
        sample_text = data.get('sample_text')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URLが指定されていません'
            }), 400
        
        # サンプルテキストが指定されていない場合はスクレイピング
        if not sample_text:
            scraper = WebScraper()
            company_content = scraper.scrape_company_website(url)
            
            if not company_content or len(company_content.strip()) < 50:
                return jsonify({
                    'success': False,
                    'error': 'ウェブサイトからテキストを取得できませんでした'
                }), 400
        else:
            company_content = sample_text
        
        # Gemini AIで分析
        analyzer = GeminiAnalyzer()
        result = analyzer.analyze_company(url, company_content)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '分析中にエラーが発生しました')
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'サーバーエラー: {str(e)}'
        }), 500
