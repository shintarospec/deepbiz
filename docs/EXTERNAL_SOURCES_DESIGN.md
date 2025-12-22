# 外部サイト連携・スクレイピング管理設計

## 📋 概要

基礎データ（GMAP・公式サイト）を元に、外部サイト情報を体系的に肉付けする仕組み。
Indeed、ホットペッパー、食べログなど、複数の外部サイトを統一的に管理。

---

## 🏗️ データ構造設計

### 1. ExternalSource（外部サイト定義マスタ）

```python
# models.py

class ExternalSource(db.Model):
    """外部サイト定義マスタ"""
    __tablename__ = 'external_source'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 基本情報
    name = db.Column(db.String(100), nullable=False, unique=True)
    # 例: 'Indeed', 'Hot Pepper Beauty', 'Tabelog', 'リジョブ'
    
    slug = db.Column(db.String(50), nullable=False, unique=True)
    # 例: 'indeed', 'hotpepper', 'tabelog'
    
    url_pattern = db.Column(db.String(500), nullable=True)
    # 例: 'https://jp.indeed.com/cmp/{company_id}'
    
    icon_url = db.Column(db.String(500), nullable=True)
    # サイトアイコンURL
    
    # 分類
    category = db.Column(db.String(50), nullable=False)
    # 'job', 'review', 'booking', 'media', 'sns'
    
    # スクレイピング設定
    search_url_template = db.Column(db.String(500), nullable=True)
    # 例: 'https://jp.indeed.com/jobs?q={business_name}+{location}'
    
    scraping_enabled = db.Column(db.Boolean, default=True)
    scraping_interval_days = db.Column(db.Integer, default=30)
    # 再スクレイピング間隔（日数）
    
    # 取得データフィールド定義（JSON）
    extractable_fields = db.Column(db.JSON, nullable=True)
    # 例: {"求人数": "integer", "平均評価": "float", "掲載ページURL": "string"}
    
    # メタ情報
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0)  # 優先度（高い順に処理）
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーション
    external_links = db.relationship('ExternalLink', backref='source', 
                                    lazy=True, cascade="all, delete-orphan")


class ExternalLink(db.Model):
    """Business × ExternalSource の連携情報"""
    __tablename__ = 'external_link'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 関連付け
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    source_id = db.Column(db.Integer, db.ForeignKey('external_source.id'), nullable=False)
    
    # URL情報
    url = db.Column(db.String(500), nullable=False)
    # 例: 'https://jp.indeed.com/cmp/○○クリニック'
    
    # 取得データ（JSON）
    scraped_data = db.Column(db.JSON, nullable=True)
    # 例: {"求人数": 5, "平均評価": 4.2, "レビュー数": 18}
    
    # ステータス
    status = db.Column(db.String(20), default='active')
    # 'active', 'inactive', 'error', 'pending'
    
    # スクレイピング履歴
    last_scraped_at = db.Column(db.DateTime, nullable=True)
    last_scrape_status = db.Column(db.String(50), nullable=True)
    # 'success', 'failed', 'not_found', 'blocked'
    
    error_message = db.Column(db.Text, nullable=True)
    scrape_count = db.Column(db.Integer, default=0)
    
    # メタ情報
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ユニーク制約
    __table_args__ = (
        db.UniqueConstraint('business_id', 'source_id', name='_business_source_link_uc'),
        db.Index('idx_external_link_source', 'source_id', 'status'),
    )


# Business モデルに追加
class Business(db.Model):
    # ... 既存フィールド
    
    # 外部サイトリンク
    external_links = db.relationship('ExternalLink', backref='business', 
                                    lazy=True, cascade="all, delete-orphan")


# ScrapingTask 拡張
class ScrapingTask(db.Model):
    __bind_key__ = 'scraping'
    id = db.Column(db.Integer, primary_key=True)
    
    # 拡張: 外部サイトスクレイピング対応
    task_type = db.Column(db.String(30), nullable=True)
    # 'gmap_discovery', 'hpb_scraping', 'external_source_discovery', 'external_source_scraping'
    
    target_url = db.Column(db.String(500), nullable=True)
    search_keyword = db.Column(db.String(200), nullable=True)
    
    # 新規追加
    external_source_id = db.Column(db.Integer, nullable=True)
    # ExternalSource.id（外部連携時のみ使用）
    
    business_id = db.Column(db.Integer, nullable=True)
    # 特定ビジネスへのスクレイピング（business_id指定時）
    
    status = db.Column(db.String(50), nullable=False, default='未実行')
    category_id = db.Column(db.Integer, nullable=False)
    last_run_at = db.Column(db.DateTime, nullable=True)
    
    # 結果
    result_summary = db.Column(db.JSON, nullable=True)
    # 例: {"found": 15, "new": 8, "updated": 7}
```

---

## 🎯 外部サイト定義例

### 初期登録データ

```python
# scripts/init_external_sources.py

EXTERNAL_SOURCES = [
    {
        'name': 'Indeed',
        'slug': 'indeed',
        'url_pattern': 'https://jp.indeed.com/cmp/{company_slug}',
        'category': 'job',
        'search_url_template': 'https://jp.indeed.com/jobs?q={business_name}+{location}&l={city}',
        'extractable_fields': {
            '求人掲載数': 'integer',
            '企業評価': 'float',
            '口コミ数': 'integer',
            '給与情報': 'string',
        },
        'icon_url': 'https://www.indeed.com/favicon.ico',
        'priority': 10,
    },
    {
        'name': 'リジョブ',
        'slug': 'rejob',
        'url_pattern': 'https://relax-job.com/detail/{job_id}',
        'category': 'job',
        'search_url_template': 'https://relax-job.com/search?keyword={business_name}',
        'extractable_fields': {
            '求人掲載数': 'integer',
            '職種': 'string',
            '勤務地': 'string',
        },
        'priority': 9,
    },
    {
        'name': 'ホットペッパービューティー',
        'slug': 'hotpepper',
        'url_pattern': 'https://clinic.beauty.hotpepper.jp/slnH{salon_id}/',
        'category': 'booking',
        'search_url_template': None,  # 既存HPBスクレイピング利用
        'extractable_fields': {
            '口コミ件数': 'integer',
            '平均評価': 'float',
            'クーポン数': 'integer',
            '施術メニュー': 'list',
        },
        'priority': 8,
    },
    {
        'name': '食べログ',
        'slug': 'tabelog',
        'url_pattern': 'https://tabelog.com/tokyo/{restaurant_id}/',
        'category': 'review',
        'search_url_template': 'https://tabelog.com/keywords/{business_name}/tokyo/',
        'extractable_fields': {
            '評価': 'float',
            '口コミ数': 'integer',
            'ジャンル': 'string',
            '予算': 'string',
        },
        'priority': 7,
    },
    {
        'name': 'Twitter/X',
        'slug': 'twitter',
        'url_pattern': 'https://twitter.com/{screen_name}',
        'category': 'sns',
        'search_url_template': 'https://twitter.com/search?q={business_name}',
        'extractable_fields': {
            'フォロワー数': 'integer',
            'ツイート数': 'integer',
            '最終更新日': 'date',
        },
        'priority': 5,
    },
    {
        'name': 'Instagram',
        'slug': 'instagram',
        'url_pattern': 'https://www.instagram.com/{username}/',
        'category': 'sns',
        'search_url_template': None,  # 検索API制限あり
        'extractable_fields': {
            'フォロワー数': 'integer',
            '投稿数': 'integer',
        },
        'priority': 5,
    },
]


def init_external_sources():
    """外部サイト定義を初期化"""
    with app.app_context():
        for source_data in EXTERNAL_SOURCES:
            existing = ExternalSource.query.filter_by(slug=source_data['slug']).first()
            
            if not existing:
                source = ExternalSource(**source_data)
                db.session.add(source)
                print(f"✓ {source_data['name']} を追加")
            else:
                print(f"- {source_data['name']} は既に存在")
        
        db.session.commit()
        print(f"\n外部サイト登録完了: {ExternalSource.query.count()}件")


if __name__ == '__main__':
    init_external_sources()
```

---

## 🔍 Indeed スクレイピング実装例

### 1. 検索・発見フェーズ

```python
# scripts/scrape_indeed.py

import sys
sys.path.append('/var/www/salon_app')

from app import app, db, Business, ExternalSource, ExternalLink, get_stealth_driver
from bs4 import BeautifulSoup
import time
import re

def discover_indeed_pages(business_id=None, limit=None):
    """
    Indeedに掲載されている企業を検索・発見
    
    Args:
        business_id: 特定ビジネスのみ処理（Noneなら全件）
        limit: 処理件数制限
    """
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    
    with app.app_context():
        # Indeed ソース取得
        indeed_source = ExternalSource.query.filter_by(slug='indeed').first()
        if not indeed_source:
            print("エラー: Indeedソースが未登録")
            return
        
        # 対象ビジネス取得
        query = Business.query.filter_by(business_type='beauty_clinic')
        
        if business_id:
            query = query.filter_by(id=business_id)
        
        # 既にIndeedリンクがあるものは除外
        query = query.filter(
            ~Business.external_links.any(ExternalLink.source_id == indeed_source.id)
        )
        
        if limit:
            query = query.limit(limit)
        
        businesses = query.all()
        total = len(businesses)
        
        print(f"=== Indeed検索開始 ===")
        print(f"対象: {total}件")
        
        driver = get_stealth_driver()
        found = 0
        not_found = 0
        
        try:
            for i, business in enumerate(businesses, 1):
                print(f"\n[{i}/{total}] {business.name}")
                
                # Indeed検索
                search_url = f"https://jp.indeed.com/jobs?q={business.name}&l=東京都"
                driver.get(search_url)
                time.sleep(3)
                
                # 企業ページリンクを探す
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # 企業名一致チェック
                company_links = soup.find_all('a', href=re.compile(r'/cmp/'))
                
                indeed_url = None
                for link in company_links:
                    company_name = link.get_text(strip=True)
                    
                    # 名前の類似度チェック（簡易）
                    if business.name in company_name or company_name in business.name:
                        indeed_url = 'https://jp.indeed.com' + link['href']
                        break
                
                if indeed_url:
                    # ExternalLink作成
                    external_link = ExternalLink(
                        business_id=business.id,
                        source_id=indeed_source.id,
                        url=indeed_url,
                        status='pending',
                        last_scrape_status='found'
                    )
                    db.session.add(external_link)
                    db.session.commit()
                    
                    print(f"  ✓ 発見: {indeed_url}")
                    found += 1
                else:
                    print(f"  - 見つかりませんでした")
                    not_found += 1
                
                time.sleep(2)  # レート制限対策
                
        finally:
            driver.quit()
        
        print(f"\n=== 完了 ===")
        print(f"発見: {found}件")
        print(f"未発見: {not_found}件")


def scrape_indeed_details():
    """
    発見済みIndeedページから詳細情報を取得
    """
    with app.app_context():
        indeed_source = ExternalSource.query.filter_by(slug='indeed').first()
        
        # status='pending' のリンクを取得
        links = ExternalLink.query.filter_by(
            source_id=indeed_source.id,
            status='pending'
        ).all()
        
        total = len(links)
        print(f"=== Indeed詳細取得開始 ===")
        print(f"対象: {total}件")
        
        driver = get_stealth_driver()
        success = 0
        failed = 0
        
        try:
            for i, link in enumerate(links, 1):
                business = link.business
                print(f"\n[{i}/{total}] {business.name}")
                print(f"  URL: {link.url}")
                
                try:
                    driver.get(link.url)
                    time.sleep(3)
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # データ抽出
                    scraped_data = {}
                    
                    # 求人掲載数
                    jobs_section = soup.find('div', class_='cmp-Jobs-tab')
                    if jobs_section:
                        jobs_count_text = jobs_section.find('span', class_='cmp-navigation-label')
                        if jobs_count_text:
                            match = re.search(r'(\d+)', jobs_count_text.get_text())
                            if match:
                                scraped_data['求人掲載数'] = int(match.group(1))
                    
                    # 企業評価
                    rating_elem = soup.find('span', class_='cmp-Rating-text')
                    if rating_elem:
                        try:
                            scraped_data['企業評価'] = float(rating_elem.get_text())
                        except ValueError:
                            pass
                    
                    # 口コミ数
                    reviews_elem = soup.find('div', class_='cmp-ReviewsCount')
                    if reviews_elem:
                        match = re.search(r'(\d+)', reviews_elem.get_text())
                        if match:
                            scraped_data['口コミ数'] = int(match.group(1))
                    
                    # データ保存
                    link.scraped_data = scraped_data
                    link.status = 'active'
                    link.last_scraped_at = datetime.utcnow()
                    link.last_scrape_status = 'success'
                    link.scrape_count += 1
                    
                    db.session.commit()
                    
                    print(f"  ✓ 取得成功: {scraped_data}")
                    success += 1
                    
                except Exception as e:
                    print(f"  ✗ エラー: {e}")
                    link.last_scrape_status = 'failed'
                    link.error_message = str(e)
                    db.session.commit()
                    failed += 1
                
                time.sleep(3)
                
        finally:
            driver.quit()
        
        print(f"\n=== 完了 ===")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'discover':
        # 発見フェーズ
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        discover_indeed_pages(limit=limit)
    else:
        # 詳細取得フェーズ
        scrape_indeed_details()
```

---

## 🎨 管理画面UI設計

### 1. 外部サイト管理ページ

```python
# app.py - 管理画面ルート追加

@app.route('/admin/external-sources')
@requires_auth
def admin_external_sources():
    """外部サイト管理画面"""
    sources = ExternalSource.query.order_by(ExternalSource.priority.desc()).all()
    
    # 各ソースの統計情報
    source_stats = []
    for source in sources:
        links_count = ExternalLink.query.filter_by(source_id=source.id).count()
        active_count = ExternalLink.query.filter_by(
            source_id=source.id, 
            status='active'
        ).count()
        
        source_stats.append({
            'source': source,
            'total_links': links_count,
            'active_links': active_count,
            'pending_scrape': ExternalLink.query.filter_by(
                source_id=source.id,
                status='pending'
            ).count(),
        })
    
    return render_template('admin/external_sources.html', source_stats=source_stats)


@app.route('/admin/external-sources/add', methods=['GET', 'POST'])
@requires_auth
def admin_add_external_source():
    """外部サイト追加"""
    if request.method == 'POST':
        source = ExternalSource(
            name=request.form['name'],
            slug=request.form['slug'],
            category=request.form['category'],
            url_pattern=request.form.get('url_pattern'),
            search_url_template=request.form.get('search_url_template'),
            scraping_enabled=request.form.get('scraping_enabled') == 'on',
            priority=int(request.form.get('priority', 0)),
        )
        db.session.add(source)
        db.session.commit()
        
        flash(f'{source.name} を追加しました', 'success')
        return redirect(url_for('admin_external_sources'))
    
    return render_template('admin/external_source_form.html')


@app.route('/admin/external-sources/<int:source_id>/discover', methods=['POST'])
@requires_auth
def admin_discover_external_links(source_id):
    """外部サイトリンク発見タスク作成"""
    source = ExternalSource.query.get_or_404(source_id)
    
    # ScrapingTask作成
    task = ScrapingTask(
        task_type='external_source_discovery',
        external_source_id=source_id,
        search_keyword=source.name,
        status='未実行',
        category_id=1,  # 適切なカテゴリID
    )
    db.session.add(task)
    db.session.commit()
    
    flash(f'{source.name} の発見タスクを作成しました', 'success')
    return redirect(url_for('admin_external_sources'))


@app.route('/admin/businesses/<int:business_id>/external-links')
@requires_auth
def admin_business_external_links(business_id):
    """特定ビジネスの外部サイトリンク管理"""
    business = Business.query.get_or_404(business_id)
    
    # 全外部サイト取得
    all_sources = ExternalSource.query.filter_by(is_active=True).all()
    
    # このビジネスの既存リンク
    existing_links = {link.source_id: link for link in business.external_links}
    
    links_data = []
    for source in all_sources:
        link = existing_links.get(source.id)
        links_data.append({
            'source': source,
            'link': link,
            'has_link': link is not None,
        })
    
    return render_template('admin/business_external_links.html',
                         business=business,
                         links_data=links_data)
```

### 2. テンプレート例

```html
<!-- templates/admin/external_sources.html -->
{% extends "layout.html" %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">外部サイト管理</h1>
    <a href="{{ url_for('admin_add_external_source') }}" 
       class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
      + 外部サイト追加
    </a>
  </div>
  
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {% for stat in source_stats %}
    <div class="bg-white border rounded-lg p-6 shadow-sm">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-xl font-semibold">{{ stat.source.name }}</h3>
        {% if stat.source.is_active %}
        <span class="bg-green-100 text-green-800 px-2 py-1 rounded text-sm">
          有効
        </span>
        {% else %}
        <span class="bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm">
          無効
        </span>
        {% endif %}
      </div>
      
      <div class="space-y-2 mb-4">
        <div class="flex justify-between text-sm">
          <span class="text-gray-600">カテゴリ:</span>
          <span class="font-medium">{{ stat.source.category }}</span>
        </div>
        <div class="flex justify-between text-sm">
          <span class="text-gray-600">登録リンク:</span>
          <span class="font-medium">{{ stat.total_links }}件</span>
        </div>
        <div class="flex justify-between text-sm">
          <span class="text-gray-600">有効:</span>
          <span class="font-medium text-green-600">{{ stat.active_links }}件</span>
        </div>
        <div class="flex justify-between text-sm">
          <span class="text-gray-600">スクレイピング待ち:</span>
          <span class="font-medium text-orange-600">{{ stat.pending_scrape }}件</span>
        </div>
      </div>
      
      <div class="flex space-x-2">
        <form action="{{ url_for('admin_discover_external_links', source_id=stat.source.id) }}" 
              method="POST" class="flex-1">
          <button type="submit" 
                  class="w-full bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700">
            🔍 発見開始
          </button>
        </form>
        
        {% if stat.pending_scrape > 0 %}
        <button class="bg-orange-600 text-white px-3 py-2 rounded text-sm hover:bg-orange-700">
          📥 取得開始
        </button>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

### 3. ビジネス詳細ページに外部サイト表示

```html
<!-- templates/clinic/detail.html -->

<!-- 基本情報の後に追加 -->
<div class="bg-white rounded-lg shadow p-6 mb-6">
  <h2 class="text-2xl font-bold mb-4">外部サイト情報</h2>
  
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    {% for link in business.external_links %}
    {% if link.status == 'active' %}
    <a href="{{ link.url }}" target="_blank" 
       class="border rounded-lg p-4 hover:shadow-md transition">
      <div class="text-center">
        <div class="text-3xl mb-2">
          {% if link.source.slug == 'indeed' %}💼
          {% elif link.source.slug == 'hotpepper' %}💆
          {% elif link.source.slug == 'tabelog' %}🍽️
          {% else %}🔗
          {% endif %}
        </div>
        <div class="font-medium">{{ link.source.name }}</div>
        
        {% if link.scraped_data %}
        <div class="text-sm text-gray-600 mt-2">
          {% if link.scraped_data.get('求人掲載数') %}
          <div>求人: {{ link.scraped_data['求人掲載数'] }}件</div>
          {% endif %}
          {% if link.scraped_data.get('企業評価') %}
          <div>評価: {{ link.scraped_data['企業評価'] }}★</div>
          {% endif %}
        </div>
        {% endif %}
      </div>
    </a>
    {% endif %}
    {% endfor %}
  </div>
</div>
```

---

## 🚀 実装フロー

### Phase 1: 基盤構築
1. [ ] モデル追加（ExternalSource, ExternalLink）
2. [ ] マイグレーション実行
3. [ ] 初期外部サイト登録（Indeed, HPB等）

### Phase 2: スクレイピング実装
4. [ ] Indeedスクレイピングスクリプト作成
5. [ ] 発見フェーズテスト（10件）
6. [ ] 詳細取得フェーズテスト（10件）

### Phase 3: 管理画面構築
7. [ ] 外部サイト管理ページ実装
8. [ ] タスク実行ボタン追加
9. [ ] 進捗表示機能

### Phase 4: フロント表示
10. [ ] ビジネス詳細ページに外部リンク表示
11. [ ] 検索フィルタ追加（Indeed掲載企業のみ等）

---

## 📊 実装後の業務フロー

```
1. 管理画面で「Indeed」の「発見開始」ボタンクリック
   ↓
2. ScrapingTask作成 → バックグラウンド実行
   ↓
3. 1,722件のクリニックをIndeed検索
   ↓
4. 企業ページ発見 → ExternalLink作成（status='pending'）
   ↓
5. 管理画面で「取得開始」ボタンクリック
   ↓
6. pending状態のリンクをスクレイピング
   ↓
7. 求人数・評価等を scraped_data に保存（status='active'）
   ↓
8. フロントエンド表示: ビジネス詳細に「Indeedで求人情報を見る」リンク
```

---

この設計で**どんな外部サイトでも統一的に管理**できます！

実装を開始しますか？それとも特定の外部サイト（Indeed等）の詳細設計を先に詰めますか?