from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

salon_categories = db.Table('salon_categories',
    db.Column('salon_id', db.Integer, db.ForeignKey('salon.id', ondelete='CASCADE'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id', ondelete='CASCADE'), primary_key=True)
)

class Salon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=True, index=True)
    name_hpb = db.Column(db.String(255), nullable=True, index=True)
    address = db.Column(db.String(255), nullable=True, index=True)
    place_id = db.Column(db.String(100), nullable=True, unique=True)
    cid = db.Column(db.String(100), nullable=True, unique=True)
    website_url = db.Column(db.String(255), nullable=True)
    inquiry_url = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(255), nullable=True)
    hotpepper_url = db.Column(db.String(255), nullable=True, unique=True)
    categories = db.relationship('Category', secondary=salon_categories, lazy='subquery', backref=db.backref('salons', lazy=True))
    review_summaries = db.relationship('ReviewSummary', backref='salon', lazy=True, cascade="all, delete-orphan")

class ReviewSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    source_name = db.Column(db.String(50), nullable=False) # 例: 'Google', 'Hot Pepper'
    rating = db.Column(db.Float, nullable=True)
    count = db.Column(db.Integer, nullable=True)

    # salon_id と source_name の組み合わせがユニークであることを保証
    __table_args__ = (db.UniqueConstraint('salon_id', 'source_name', name='_salon_source_uc'),)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    source = db.Column(db.String(50), nullable=True)          # 求人元 (例: 'リジョブ')
    source_url = db.Column(db.String(500), nullable=True)    # 求人ページのURL
    salary = db.Column(db.String(200), nullable=True)        # 給与
    employment_type = db.Column(db.String(100), nullable=True) # 雇用形態

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class Advertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_name = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    link_url = db.Column(db.String(255))

# --- スクレイピング用DBに属するモデル ---

class Area(db.Model):
    __bind_key__ = 'scraping'
    id = db.Column(db.Integer, primary_key=True)
    prefecture = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)

class ScrapingTask(db.Model):
    __bind_key__ = 'scraping'
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(20), nullable=True)
    target_url = db.Column(db.String(500), nullable=True, unique=True)
    search_keyword = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='未実行')
    # ▼▼▼ ForeignKey制約を削除 ▼▼▼
    category_id = db.Column(db.Integer, nullable=False)
    last_run_at = db.Column(db.DateTime, nullable=True)

class CompanyAnalysis(db.Model):
    """企業Webサイト解析結果を保存するモデル（AI AutoForm連携用）"""
    id = db.Column(db.Integer, primary_key=True)
    company_domain = db.Column(db.String(255), unique=True, nullable=False, index=True)  # example.co.jp
    company_url = db.Column(db.String(500), nullable=True)  # https://example.co.jp
    business_description = db.Column(db.Text, nullable=True)  # 事業内容の要約（100-200文字）
    industry = db.Column(db.String(100), nullable=True)  # IT・ソフトウェア
    strengths = db.Column(db.JSON, nullable=True)  # ["強み1", "強み2", "強み3"]
    target_customers = db.Column(db.Text, nullable=True)  # ターゲット顧客層
    key_topics = db.Column(db.JSON, nullable=True)  # ["AI", "業務効率化", "DX"]
    company_size = db.Column(db.String(50), nullable=True)  # 中堅企業、大企業など
    pain_points = db.Column(db.JSON, nullable=True)  # ["リソース不足", "ITスキル不足"]
    analyzed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)  # 90日後に設定
    cache_hit_count = db.Column(db.Integer, nullable=False, default=0)  # 利用回数追跡
    last_accessed_at = db.Column(db.DateTime, nullable=True)  # 最終アクセス日時
