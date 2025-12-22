# DeepBiz プロジェクト計画

## 📋 プロジェクト概要

**コンセプト**: 地域×業種特化型のビジネス情報プラットフォーム  
**初期ターゲット**: 東京23区の美容クリニック（1,905件）  
**拡張戦略**: 実績検証後、飲食店・宿泊施設など多業種展開

---

## 🎯 Phase 0: 美容クリニックでの実証（現在）

### 目的
- データ収集・表示フローの確立
- SEO効果の検証
- 運用コスト・工数の把握
- ユーザー反応の測定

### 実施内容
1. **データ収集完了**（2025年12月22日時点）
   - CSV import: 1,905件
   - GMAP補完 Phase 1A: 1,722件（90.4%）Place ID取得完了
   - Google評価: 約1,600件取得済み

2. **追加スクレイピングテスト**（次ステップ）
   - Phase 1B: CID・Website URL取得
   - Phase 1C: 公式サイト問い合わせ情報抽出
   - Phase 2: GMAP新規クリニック発見（3,423エリア検索）
   - Phase 3: HPB追加情報取得

3. **コンテンツ拡充評価**
   - 取得データの精度検証
   - 表示内容の充実度確認
   - SEO効果測定（3ヶ月）
   - ユーザー滞在時間・回遊率分析

4. **判断基準**
   - ✅ データ取得成功率 > 80%
   - ✅ 月間PV > 1,000（初月）
   - ✅ 平均滞在時間 > 2分
   - ✅ 運用工数 < 週5時間

---

## 🚀 Phase 1: 多業種展開準備

### 実施条件
Phase 0で以下を達成後に開始：
- 美容クリニックで月間10,000PV達成
- データ収集スクリプトの安定稼働（3ヶ月以上）
- 収益化の目処が立つ（広告収入 or 掲載課金）

### データモデル統合

#### 1-1. 共通ベーステーブル設計

```python
# models.py - Business基底モデル

class Business(db.Model):
    """全業種共通のベーステーブル"""
    __tablename__ = 'business'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 業種分類
    business_type = db.Column(db.String(50), nullable=False, index=True)
    # 'beauty_clinic', 'restaurant', 'hotel', 'gym', 'hair_salon'
    
    # 基本情報（全業種共通）
    name = db.Column(db.String(255), nullable=True, index=True)
    address = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Google Maps情報
    place_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    cid = db.Column(db.String(100), nullable=True, unique=True)
    
    # Web情報
    website_url = db.Column(db.String(500), nullable=True)
    contact_page_url = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    
    # ポータルサイト情報
    portal_urls = db.Column(db.JSON, nullable=True)
    # 例: {"hotpepper": "https://...", "tabelog": "https://...", "ikyu": "https://..."}
    
    # レビュー情報（Relationship）
    review_summaries = db.relationship('ReviewSummary', backref='business', 
                                       lazy=True, cascade="all, delete-orphan")
    
    # 業種別拡張情報（柔軟なJSON）
    extra_data = db.Column(db.JSON, nullable=True)
    # 例: 
    # 美容クリニック: {"施術メニュー": [...], "診療時間": {...}}
    # 飲食店: {"ジャンル": "イタリアン", "予算": "3000-5000円"}
    # ホテル: {"客室数": 50, "チェックイン": "15:00"}
    
    # メタデータ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scraped_at = db.Column(db.DateTime, nullable=True)
    
    # インデックス
    __table_args__ = (
        db.Index('idx_business_type_address', 'business_type', 'address'),
    )


class ReviewSummary(db.Model):
    """レビュー情報（業種共通）"""
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    source_name = db.Column(db.String(50), nullable=False)
    # 'Google', 'Tabelog', 'Ikyu', 'Hot Pepper', 'Retty'
    rating = db.Column(db.Float, nullable=True)
    count = db.Column(db.Integer, nullable=True)
    
    __table_args__ = (
        db.UniqueConstraint('business_id', 'source_name', name='_business_source_uc'),
    )
```

#### 1-2. Salonモデルの移行戦略

**Option A: ビュー作成（推奨 - 既存コード互換性維持）**
```python
# 既存Salonテーブルは残し、Businessにデータコピー
# Salonは互換性レイヤーとして機能

class Salon(db.Model):
    """美容クリニック（互換性維持）"""
    # 既存構造を維持
    # app.pyの変更を最小化
```

**Option B: 完全移行**
```python
# Salonテーブルを削除し、Businessに統合
# business_type = 'beauty_clinic' でフィルタ
```

---

### 1-3. URL構造設計（サブディレクトリ方式）

```
deepbiz.jp/                  → トップページ（業種選択）
deepbiz.jp/clinic/           → 美容クリニック一覧
deepbiz.jp/clinic/search     → 美容クリニック検索
deepbiz.jp/clinic/123        → 美容クリニック詳細
deepbiz.jp/restaurant/       → 飲食店一覧
deepbiz.jp/restaurant/456    → 飲食店詳細
deepbiz.jp/hotel/            → 宿泊施設一覧
```

#### Flask Blueprint構成
```python
# app.py

from blueprints.clinic import clinic_bp
from blueprints.restaurant import restaurant_bp
from blueprints.hotel import hotel_bp

app.register_blueprint(clinic_bp)
app.register_blueprint(restaurant_bp)
app.register_blueprint(hotel_bp)
```

```python
# blueprints/clinic.py

from flask import Blueprint, render_template, request
from models import Business, ReviewSummary

clinic_bp = Blueprint('clinic', __name__, 
                     url_prefix='/clinic',
                     template_folder='../templates/clinic')

@clinic_bp.route('/')
def index():
    """美容クリニック一覧"""
    clinics = Business.query.filter_by(
        business_type='beauty_clinic'
    ).order_by(Business.name).all()
    
    return render_template('index.html', 
                         businesses=clinics,
                         business_type='美容クリニック',
                         business_slug='clinic')

@clinic_bp.route('/search')
def search():
    """美容クリニック検索"""
    keyword = request.args.get('q', '')
    area = request.args.get('area', '')
    
    query = Business.query.filter_by(business_type='beauty_clinic')
    
    if keyword:
        query = query.filter(Business.name.contains(keyword))
    if area:
        query = query.filter(Business.address.contains(area))
    
    clinics = query.all()
    
    return render_template('search.html',
                         businesses=clinics,
                         keyword=keyword,
                         area=area)

@clinic_bp.route('/<int:id>')
def detail(id):
    """美容クリニック詳細"""
    clinic = Business.query.filter_by(
        id=id,
        business_type='beauty_clinic'
    ).first_or_404()
    
    reviews = ReviewSummary.query.filter_by(business_id=id).all()
    
    return render_template('detail.html',
                         business=clinic,
                         reviews=reviews)
```

---

### 1-4. テンプレート構造

```
templates/
  ├── base.html              # 最上位レイアウト
  ├── components/            # 共通コンポーネント
  │   ├── header.html
  │   ├── footer.html
  │   └── review_card.html
  ├── clinic/                # 美容クリニック
  │   ├── index.html         # 一覧
  │   ├── search.html        # 検索結果
  │   └── detail.html        # 詳細
  ├── restaurant/            # 飲食店
  │   ├── index.html
  │   ├── search.html
  │   └── detail.html
  └── hotel/                 # 宿泊施設
      ├── index.html
      ├── search.html
      └── detail.html
```

#### base.html - 業種切替ナビゲーション
```html
<nav class="bg-white shadow-md">
  <div class="max-w-7xl mx-auto px-4">
    <div class="flex space-x-8 py-4">
      <a href="/" class="text-2xl font-bold text-blue-600">DeepBiz</a>
      
      <div class="flex space-x-6 ml-auto items-center">
        <a href="/clinic" 
           class="{% if business_slug == 'clinic' %}text-blue-600 font-semibold{% else %}text-gray-600 hover:text-blue-600{% endif %}">
          🏥 美容クリニック
        </a>
        <a href="/restaurant" 
           class="{% if business_slug == 'restaurant' %}text-blue-600 font-semibold{% else %}text-gray-600 hover:text-blue-600{% endif %}">
          🍽️ 飲食店
        </a>
        <a href="/hotel" 
           class="{% if business_slug == 'hotel' %}text-blue-600 font-semibold{% else %}text-gray-600 hover:text-blue-600{% endif %}">
          🏨 宿泊施設
        </a>
      </div>
    </div>
  </div>
</nav>

{% block content %}{% endblock %}
```

---

### 1-5. 汎用スクレイピングスクリプト

```python
# scripts/enrich_gmap_universal.py

"""
汎用GMAP情報取得スクリプト
任意の業種モデルに対応
"""

import sys
sys.path.append('/var/www/salon_app')

from app import app, db, Business, ReviewSummary, get_gmap_place_details

def enrich_with_gmap(business_type, limit=None):
    """
    指定業種にGoogleマップ情報を補完
    
    Args:
        business_type: 'beauty_clinic', 'restaurant', 'hotel'
        limit: 処理件数制限
    """
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    
    with app.app_context():
        query = Business.query.filter_by(
            business_type=business_type,
            place_id=None
        )
        
        if limit:
            query = query.limit(limit)
        
        items = query.all()
        total = len(items)
        
        BUSINESS_NAMES = {
            'beauty_clinic': '美容クリニック',
            'restaurant': '飲食店',
            'hotel': '宿泊施設',
        }
        
        print(f"=== {BUSINESS_NAMES[business_type]} GMAP補完開始 ===")
        print(f"対象件数: {total}")
        
        success = 0
        failed = 0
        
        for i, item in enumerate(items, 1):
            try:
                search_query = f"{item.name} {item.address}"
                print(f"\n[{i}/{total}] {item.name}")
                
                place_details = get_gmap_place_details(search_query, api_key)
                
                if not place_details:
                    print(f"  → Place情報が見つかりませんでした")
                    failed += 1
                    continue
                
                # 基本情報更新
                item.place_id = place_details.get('place_id')
                rating = place_details.get('rating')
                review_count = place_details.get('user_ratings_total')
                
                print(f"  → Place ID: {item.place_id}")
                
                # レビュー情報保存
                if rating is not None:
                    google_review = ReviewSummary.query.filter_by(
                        business_id=item.id,
                        source_name='Google'
                    ).first()
                    
                    if google_review:
                        google_review.rating = rating
                        google_review.count = review_count
                    else:
                        google_review = ReviewSummary(
                            business_id=item.id,
                            source_name='Google',
                            rating=rating,
                            count=review_count
                        )
                        db.session.add(google_review)
                    
                    print(f"  → 評価: {rating}★ ({review_count}件)")
                
                item.last_scraped_at = datetime.utcnow()
                db.session.commit()
                success += 1
                
                time.sleep(1)
                
            except Exception as e:
                print(f"  エラー: {e}")
                failed += 1
                db.session.rollback()
                continue
        
        print(f"\n=== 完了 ===")
        print(f"成功: {success}件")
        print(f"失敗: {failed}件")


if __name__ == '__main__':
    # 実行例:
    # python scripts/enrich_gmap_universal.py beauty_clinic
    # python scripts/enrich_gmap_universal.py restaurant 100
    
    if len(sys.argv) < 2:
        print("使用方法: python enrich_gmap_universal.py <business_type> [limit]")
        print("業種: beauty_clinic, restaurant, hotel")
        sys.exit(1)
    
    business_type = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    enrich_with_gmap(business_type, limit)
```

---

### 1-6. 業種設定ファイル

```python
# config/business_config.py

"""
業種別の設定情報
検索キーワード、スクレイピング元、レビューソースなど
"""

BUSINESS_TYPES = {
    'beauty_clinic': {
        'name_ja': '美容クリニック',
        'name_en': 'Beauty Clinic',
        'icon': '🏥',
        'color': 'blue',
        
        # GMAP検索キーワード
        'search_keywords': [
            '美容クリニック',
            '美容外科',
            '美容皮膚科',
            '美容整形',
        ],
        
        # スクレイピング対象サイト
        'scraping_sources': [
            {
                'name': 'ホットペッパービューティー',
                'slug': 'hotpepper',
                'base_url': 'https://clinic.beauty.hotpepper.jp/',
            },
            {
                'name': 'トリビュー',
                'slug': 'tribeau',
                'base_url': 'https://tribeau.jp/',
            },
        ],
        
        # レビューソース
        'review_sources': ['Google', 'Hot Pepper', 'Tribeau'],
        
        # extra_data フィールド定義
        'extra_fields': {
            '施術メニュー': 'list',
            '診療時間': 'dict',
            '予約URL': 'string',
        },
    },
    
    'restaurant': {
        'name_ja': '飲食店',
        'name_en': 'Restaurant',
        'icon': '🍽️',
        'color': 'orange',
        
        'search_keywords': [
            'レストラン',
            '居酒屋',
            'カフェ',
            'バー',
        ],
        
        'scraping_sources': [
            {
                'name': '食べログ',
                'slug': 'tabelog',
                'base_url': 'https://tabelog.com/',
            },
            {
                'name': 'ぐるなび',
                'slug': 'gurunavi',
                'base_url': 'https://www.gnavi.co.jp/',
            },
        ],
        
        'review_sources': ['Google', 'Tabelog', 'Retty'],
        
        'extra_fields': {
            'ジャンル': 'string',
            '予算': 'string',
            '席数': 'integer',
            '予約可否': 'boolean',
        },
    },
    
    'hotel': {
        'name_ja': '宿泊施設',
        'name_en': 'Hotel',
        'icon': '🏨',
        'color': 'purple',
        
        'search_keywords': [
            'ホテル',
            '旅館',
            '民宿',
            'ゲストハウス',
        ],
        
        'scraping_sources': [
            {
                'name': '一休.com',
                'slug': 'ikyu',
                'base_url': 'https://www.ikyu.com/',
            },
            {
                'name': 'じゃらん',
                'slug': 'jalan',
                'base_url': 'https://www.jalan.net/',
            },
        ],
        
        'review_sources': ['Google', 'Ikyu', 'Jalan', 'Rakuten'],
        
        'extra_fields': {
            '客室数': 'integer',
            'チェックイン': 'string',
            'チェックアウト': 'string',
            '駐車場': 'boolean',
        },
    },
}


def get_business_config(business_type):
    """業種設定を取得"""
    return BUSINESS_TYPES.get(business_type)


def get_all_business_types():
    """全業種リストを取得"""
    return list(BUSINESS_TYPES.keys())
```

---

## 📊 Phase 2: 業種追加展開

### 優先順位

1. **飲食店（Restaurant）** - 第2業種
   - 理由: データ量が多い（需要大）、食べログ等API利用可能
   - 目標: 東京23区 10,000店舗
   - スクレイピング: 食べログ、ぐるなび、Retty

2. **宿泊施設（Hotel）** - 第3業種
   - 理由: 単価が高い（広告収入期待）、一休.com等データ充実
   - 目標: 東京23区 500施設
   - スクレイピング: 一休.com、じゃらん、楽天トラベル

3. **フィットネスジム（Gym）** - 第4業種
   - 理由: 成長市場、競合少ない
   - 目標: 東京23区 1,000施設

4. **ヘアサロン（Hair Salon）** - 第5業種
   - 理由: ホットペッパービューティーと親和性高い
   - 目標: 東京23区 5,000店舗

---

## 💰 収益化戦略

### フェーズ別収益モデル

#### Phase 0（美容クリニック実証期間）
- **目標**: データ収集・SEO効果検証
- **収益**: なし（投資フェーズ）

#### Phase 1（多業種展開）
- **Google AdSense**: 月間10万PV達成後
- **アフィリエイト**: 予約サイト誘導（一休.com、食べログ等）

#### Phase 2（プレミアム機能）
- **掲載店舗向け有料プラン**:
  - 上位表示: 月額10,000円
  - 詳細情報掲載: 月額5,000円
  - 問い合わせ転送: 月額3,000円

#### Phase 3（広告営業）
- **純広告枠販売**: 業種別トップページバナー
- **メールマーケティング**: 登録ユーザー向け

---

## 🛠️ 技術スタック

### 現在（Phase 0）
- **Backend**: Flask（Python 3.x）
- **Database**: SQLite（salon_data.db, scraping_data.db）
- **Frontend**: Tailwind CSS + Jinja2
- **Scraping**: Selenium + undetected-chromedriver
- **API**: Google Maps Text Search API
- **Hosting**: Sakura VPS（Ubuntu 24.04）

### 将来（Phase 2以降）
- **Database**: PostgreSQL（スケーラビリティ）
- **Cache**: Redis（パフォーマンス）
- **Queue**: Celery（非同期スクレイピング）
- **Frontend**: Next.js（SPA化検討）
- **Hosting**: AWS/GCP（オートスケール）

---

## 📅 タイムライン

### 2025年12月（Phase 0 - 実証期間）
- [x] 美容クリニックCSVインポート（1,905件）
- [x] GMAP Phase 1A完了（Place ID 90.4%取得）
- [ ] GMAP Phase 1B: CID・Website取得
- [ ] GMAP Phase 1C: 問い合わせ情報取得
- [ ] コンテンツ拡充評価

### 2026年1月〜3月（Phase 0 継続）
- [ ] SEO効果測定（3ヶ月）
- [ ] ユーザー行動分析
- [ ] Phase 1移行判断

### 2026年4月〜6月（Phase 1 - 多業種準備）
- [ ] Businessモデル実装
- [ ] Blueprint構造リファクタ
- [ ] 飲食店データ収集開始

### 2026年7月〜（Phase 2 - 業種展開）
- [ ] 飲食店リリース
- [ ] 宿泊施設データ収集
- [ ] 収益化開始

---

## 🎯 成功指標（KPI）

### Phase 0（美容クリニック実証）
- データ取得率: > 80%
- 月間PV: > 10,000
- 平均滞在時間: > 2分
- 直帰率: < 60%
- オーガニック検索流入: > 50%

### Phase 1（多業種展開）
- 業種数: 3業種以上
- 総データ件数: > 15,000件
- 月間PV: > 100,000
- 広告収入: > 月額50,000円

### Phase 2（収益化）
- 有料掲載店舗: > 50店舗
- 月間売上: > 500,000円
- 利益率: > 30%

---

## 🔄 運用フロー

### 日次
- [ ] スクレイピングエラー確認
- [ ] サーバー稼働状況確認

### 週次
- [ ] 新規データ追加（100件程度）
- [ ] データ精度チェック
- [ ] アクセス解析レビュー

### 月次
- [ ] データ全体更新（評価・URL変更等）
- [ ] SEOパフォーマンス分析
- [ ] 収益レポート作成

---

## 📝 注意事項・リスク

### 技術的リスク
- **スクレイピング規制**: robots.txt遵守、レート制限対策必須
- **API料金**: Google Maps API月額$200制限、超過時の対応
- **データ精度**: 誤情報混入のリスク、定期検証必要

### 法的リスク
- **著作権**: スクレイピング元サイトの利用規約確認
- **個人情報**: メールアドレス等の取り扱い注意
- **景表法**: 口コミ・評価の表示に関する規制

### ビジネスリスク
- **競合出現**: 類似サービスの台頭
- **収益化困難**: 想定PV未達成
- **運用工数**: スケール時の人手不足

---

## 🎓 学習・改善ポイント

### Phase 0で検証すべき仮説
1. **データ量 vs SEO効果**: 1,905件で上位表示可能か？
2. **スクレイピング vs API**: コスト・精度・速度のバランス
3. **ユーザーニーズ**: どの情報が最も閲覧されるか？
4. **地域特化 vs 全国展開**: 東京23区のみで十分か？

### Phase 1での改善
1. **データモデル最適化**: JSON vs 正規化テーブル
2. **スクレイピング効率化**: 並列処理、チェックポイント
3. **UI/UX改善**: A/Bテストによる最適化

---

## 🚀 次のアクション

### 即座に実施（Phase 0継続）
1. [ ] GMAP Phase 1B実行（CID取得）
2. [ ] Phase 1C実行（問い合わせ情報取得）
3. [ ] コンテンツ拡充後のSEO効果測定準備

### 3ヶ月後判断（Phase 1移行可否）
- 上記KPI達成状況を評価
- Phase 1実装の詳細設計開始
- 飲食店データソース調査

---

**最終更新**: 2025年12月22日  
**プロジェクトオーナー**: @shintarospec
