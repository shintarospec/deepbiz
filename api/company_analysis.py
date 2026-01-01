"""
企業分析API Blueprint
- GET /api/v1/companies/<company_domain>/analysis - 企業分析取得
- POST /api/v1/companies/analyze - 新規企業分析実行
"""
from flask import Blueprint, jsonify, request
from models import db, CompanyAnalysis
from services.web_scraper import WebScraper
from services.gemini_analyzer import GeminiAnalyzer
from datetime import datetime, timedelta
from functools import wraps
import os


# Blueprint作成
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


# 認証デコレータ
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('Authorization')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Authorization headerが必要です'
            }), 401
        
        # "Bearer <token>" 形式をサポート
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        # 環境変数からAPIキーを取得
        expected_api_key = os.getenv('DEEPBIZ_API_KEY')
        if not expected_api_key:
            return jsonify({
                'success': False,
                'error': 'サーバー側でDEEPBIZ_API_KEYが設定されていません'
            }), 500
        
        if api_key != expected_api_key:
            return jsonify({
                'success': False,
                'error': '無効なAPIキーです'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


@api_bp.route('/companies/<company_domain>/analysis', methods=['GET'])
@require_api_key
def get_company_analysis(company_domain):
    """
    企業分析結果を取得（キャッシュから取得、なければ新規解析）
    
    GET /api/v1/companies/example.co.jp/analysis
    Headers:
        Authorization: Bearer <api_key>
    
    Response:
        200 OK
        {
            "success": true,
            "company_domain": "example.co.jp",
            "analysis": {
                "businessDescription": "...",
                "industry": "...",
                "strengths": [...],
                "targetCustomers": "...",
                "keyTopics": [...],
                "companySize": "...",
                "painPoints": [...]
            },
            "cached": true,
            "analyzed_at": "2026-01-01T10:00:00Z",
            "expires_at": "2026-04-01T10:00:00Z",
            "cache_hit_count": 15
        }
    """
    try:
        # ドメインからwww.を除去
        company_domain = company_domain.replace('www.', '')
        
        # キャッシュチェック
        cached_analysis = CompanyAnalysis.query.filter_by(company_domain=company_domain).first()
        
        # キャッシュが有効か確認
        if cached_analysis:
            now = datetime.utcnow()
            
            # 期限切れチェック
            if cached_analysis.expires_at and cached_analysis.expires_at < now:
                # 期限切れの場合は削除して再解析
                db.session.delete(cached_analysis)
                db.session.commit()
                cached_analysis = None
            else:
                # キャッシュヒット数を更新
                cached_analysis.cache_hit_count += 1
                cached_analysis.last_accessed_at = now
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'company_domain': company_domain,
                    'analysis': {
                        'businessDescription': cached_analysis.business_description,
                        'industry': cached_analysis.industry,
                        'strengths': cached_analysis.strengths,
                        'targetCustomers': cached_analysis.target_customers,
                        'keyTopics': cached_analysis.key_topics,
                        'companySize': cached_analysis.company_size,
                        'painPoints': cached_analysis.pain_points
                    },
                    'cached': True,
                    'analyzed_at': cached_analysis.analyzed_at.isoformat() + 'Z',
                    'expires_at': cached_analysis.expires_at.isoformat() + 'Z' if cached_analysis.expires_at else None,
                    'cache_hit_count': cached_analysis.cache_hit_count
                }), 200
        
        # キャッシュなし → 新規解析実行
        company_url = f"https://{company_domain}"
        result = analyze_company_url(company_url)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'サーバーエラー: {str(e)}'
        }), 500


@api_bp.route('/companies/analyze', methods=['POST'])
@require_api_key
def analyze_company():
    """
    新規企業分析を実行（強制的にキャッシュを更新）
    
    POST /api/v1/companies/analyze
    Headers:
        Authorization: Bearer <api_key>
    Body:
        {
            "company_url": "https://example.co.jp"
        }
    
    Response:
        200 OK
        {
            "success": true,
            "company_domain": "example.co.jp",
            "analysis": {...},
            "cached": false,
            "analyzed_at": "2026-01-01T10:00:00Z",
            "expires_at": "2026-04-01T10:00:00Z",
            "tokens_used": {"input": 5310, "output": 600, "total": 5910},
            "cost": 0.000145
        }
    """
    try:
        data = request.get_json()
        company_url = data.get('company_url')
        
        if not company_url:
            return jsonify({
                'success': False,
                'error': 'company_urlが必要です'
            }), 400
        
        result = analyze_company_url(company_url, force_update=True)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'サーバーエラー: {str(e)}'
        }), 500


def analyze_company_url(company_url: str, force_update: bool = False) -> dict:
    """
    企業URLを解析してデータベースに保存
    
    Args:
        company_url: 企業URL
        force_update: 強制的にキャッシュを更新するか
    
    Returns:
        解析結果の辞書
    """
    try:
        # 1. Webスクレイピング
        scraper = WebScraper(use_selenium=False)  # まずはrequestsで試行
        scrape_result = scraper.scrape_website(company_url, max_chars=15000)
        
        if not scrape_result['success']:
            # requestsで失敗した場合はSeleniumで再試行
            scraper = WebScraper(use_selenium=True)
            scrape_result = scraper.scrape_website(company_url, max_chars=15000)
            
            if not scrape_result['success']:
                return {
                    'success': False,
                    'error': f"Webスクレイピング失敗: {scrape_result['error']}"
                }
        
        # 2. Gemini AI解析
        analyzer = GeminiAnalyzer()
        analysis_result = analyzer.analyze_company(company_url, scrape_result['text'])
        
        if not analysis_result['success']:
            return {
                'success': False,
                'error': f"AI解析失敗: {analysis_result['error']}"
            }
        
        # 3. データベース保存
        company_domain = scrape_result['domain']
        now = datetime.utcnow()
        expires_at = now + timedelta(days=90)  # 90日間有効
        
        # 既存レコードをチェック
        existing = CompanyAnalysis.query.filter_by(company_domain=company_domain).first()
        
        if existing and not force_update:
            # 既存レコードを返す（通常はここには来ない）
            return {
                'success': True,
                'company_domain': company_domain,
                'analysis': {
                    'businessDescription': existing.business_description,
                    'industry': existing.industry,
                    'strengths': existing.strengths,
                    'targetCustomers': existing.target_customers,
                    'keyTopics': existing.key_topics,
                    'companySize': existing.company_size,
                    'painPoints': existing.pain_points
                },
                'cached': True,
                'analyzed_at': existing.analyzed_at.isoformat() + 'Z',
                'expires_at': existing.expires_at.isoformat() + 'Z',
                'cache_hit_count': existing.cache_hit_count
            }
        
        if existing:
            # 更新
            existing.company_url = company_url
            existing.business_description = analysis_result['data']['businessDescription']
            existing.industry = analysis_result['data']['industry']
            existing.strengths = analysis_result['data']['strengths']
            existing.target_customers = analysis_result['data']['targetCustomers']
            existing.key_topics = analysis_result['data']['keyTopics']
            existing.company_size = analysis_result['data']['companySize']
            existing.pain_points = analysis_result['data']['painPoints']
            existing.analyzed_at = now
            existing.expires_at = expires_at
            existing.cache_hit_count = 0
            existing.last_accessed_at = now
            company_analysis = existing
        else:
            # 新規作成
            company_analysis = CompanyAnalysis(
                company_domain=company_domain,
                company_url=company_url,
                business_description=analysis_result['data']['businessDescription'],
                industry=analysis_result['data']['industry'],
                strengths=analysis_result['data']['strengths'],
                target_customers=analysis_result['data']['targetCustomers'],
                key_topics=analysis_result['data']['keyTopics'],
                company_size=analysis_result['data']['companySize'],
                pain_points=analysis_result['data']['painPoints'],
                analyzed_at=now,
                expires_at=expires_at,
                cache_hit_count=0,
                last_accessed_at=now
            )
            db.session.add(company_analysis)
        
        db.session.commit()
        
        return {
            'success': True,
            'company_domain': company_domain,
            'analysis': analysis_result['data'],
            'cached': False,
            'analyzed_at': now.isoformat() + 'Z',
            'expires_at': expires_at.isoformat() + 'Z',
            'tokens_used': analysis_result['tokens_used'],
            'cost': analysis_result['cost']
        }
    
    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': f'解析処理エラー: {str(e)}\n{traceback.format_exc()}'
        }
