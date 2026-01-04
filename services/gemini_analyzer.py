"""
Gemini AI連携サービス
- 企業Webサイトの解析
- 構造化データ抽出（JSON形式）
- コンテキストキャッシング対応
"""
import os
import json
import google.generativeai as genai
from typing import Dict, Optional


class GeminiAnalyzer:
    """Gemini AIを使用した企業分析クラス"""
    
    # システムプロンプト（約150トークン）
    SYSTEM_PROMPT = """あなたは企業分析の専門家です。以下の企業Webサイトを詳細に分析し、事業内容、強み、ターゲット顧客、課題などを抽出してください。

分析の際は以下の点に注意してください：
- 事業内容は100-200文字で要約
- 強みは最大3つまで抽出
- ターゲット顧客層を明確に特定
- 潜在的な課題（pain points）を推測
- 業界分類を正確に判定"""
    
    # 出力形式指示（約150トークン）
    OUTPUT_FORMAT = """以下の形式でJSON形式で出力してください：

{
  "businessDescription": "事業内容の要約（100-200文字）",
  "industry": "業界名（IT・ソフトウェア、製造業、小売業など）",
  "strengths": ["強み1", "強み2", "強み3"],
  "targetCustomers": "ターゲット顧客層の説明",
  "keyTopics": ["キーワード1", "キーワード2", "キーワード3"],
  "companySize": "企業規模（大企業、中堅企業、中小企業、スタートアップ）",
  "painPoints": ["潜在的な課題1", "潜在的な課題2"]
}

JSON以外のテキストは出力しないでください。"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Gemini APIキー（未指定時は環境変数GEMINI_API_KEYを使用）
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません")
        
        genai.configure(api_key=self.api_key)
        # 2026年版: Gemini 2.5 Flash (最新版)
        self.model = genai.GenerativeModel('gemini-2.5-flash-latest')
    
    def analyze_company(self, company_url: str, html_content: str) -> Dict:
        """
        企業Webサイトを解析し、構造化データを返す
        
        Args:
            company_url: 企業URL
            html_content: HTMLコンテンツ（15,000文字以内に切り詰め済み）
        
        Returns:
            {
                'success': bool,
                'data': {
                    'businessDescription': str,
                    'industry': str,
                    'strengths': list,
                    'targetCustomers': str,
                    'keyTopics': list,
                    'companySize': str,
                    'painPoints': list
                },
                'tokens_used': {
                    'input': int,
                    'output': int,
                    'total': int
                },
                'cost': float,  # USD
                'error': str
            }
        """
        try:
            # プロンプト構築
            prompt = f"""{self.SYSTEM_PROMPT}

企業URL: {company_url}

Webサイトコンテンツ:
{html_content[:15000]}

{self.OUTPUT_FORMAT}"""
            
            # Gemini API呼び出し
            response = self.model.generate_content(prompt)
            
            # トークン数とコスト計算
            tokens_used = {
                'input': response.usage_metadata.prompt_token_count,
                'output': response.usage_metadata.candidates_token_count,
                'total': response.usage_metadata.total_token_count
            }
            
            # Gemini 2.5 Flash-Lite 料金（2026年1月時点）
            # Input: $0.0001 per 1K tokens
            # Output: $0.0004 per 1K tokens
            cost = (
                tokens_used['input'] * 0.0001 / 1000 +
                tokens_used['output'] * 0.0004 / 1000
            )
            
            # JSON抽出
            response_text = response.text.strip()
            
            # コードブロック除去（```json ... ``` の場合）
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            data = json.loads(response_text)
            
            return {
                'success': True,
                'data': data,
                'tokens_used': tokens_used,
                'cost': cost,
                'error': None
            }
        
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'data': None,
                'tokens_used': None,
                'cost': 0,
                'error': f'JSON解析エラー: {str(e)}\nレスポンス: {response_text[:500]}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'tokens_used': None,
                'cost': 0,
                'error': f'AI解析エラー: {str(e)}'
            }
