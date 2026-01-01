"""
企業Webサイトのスクレイピング機能
- URLからHTMLコンテンツを取得
- JavaScript実行が必要な場合はSelenium使用
- テキスト抽出・クリーニング機能
"""
import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class WebScraper:
    """企業Webサイトのスクレイピングを行うクラス"""
    
    def __init__(self, use_selenium=False):
        """
        Args:
            use_selenium: Seleniumを使用するかどうか（デフォルトはrequests）
        """
        self.use_selenium = use_selenium
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.127 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def extract_domain(self, url: str) -> str:
        """
        URLからドメインを抽出
        
        Args:
            url: 完全なURL (https://www.example.co.jp/about)
        
        Returns:
            ドメイン (example.co.jp)
        """
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    
    def scrape_website(self, url: str, max_chars: int = 15000) -> dict:
        """
        企業WebサイトからHTMLコンテンツを取得
        
        Args:
            url: スクレイピング対象のURL
            max_chars: 取得する最大文字数（トークン削減のため）
        
        Returns:
            {
                'success': bool,
                'url': str,
                'domain': str,
                'html': str,  # 取得したHTMLコンテンツ
                'text': str,  # テキスト抽出結果
                'error': str  # エラー時のメッセージ
            }
        """
        try:
            if self.use_selenium:
                return self._scrape_with_selenium(url, max_chars)
            else:
                return self._scrape_with_requests(url, max_chars)
        except Exception as e:
            return {
                'success': False,
                'url': url,
                'domain': self.extract_domain(url),
                'html': '',
                'text': '',
                'error': f'スクレイピング失敗: {str(e)}'
            }
    
    def _scrape_with_requests(self, url: str, max_chars: int) -> dict:
        """requestsライブラリを使用したスクレイピング"""
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        
        html = response.text[:max_chars * 3]  # HTML→テキスト変換で約1/3になる想定
        text = self._extract_text(html)
        text = text[:max_chars]
        
        return {
            'success': True,
            'url': url,
            'domain': self.extract_domain(url),
            'html': html,
            'text': text,
            'error': None
        }
    
    def _scrape_with_selenium(self, url: str, max_chars: int) -> dict:
        """Seleniumを使用したスクレイピング（JavaScript実行対応）"""
        from app import get_stealth_driver
        
        driver = None
        try:
            driver = get_stealth_driver()
            driver.get(url)
            
            # ページ読み込み待機（最大10秒）
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # JavaScript実行完了を待つ
            
            html = driver.page_source[:max_chars * 3]
            text = self._extract_text(html)
            text = text[:max_chars]
            
            return {
                'success': True,
                'url': url,
                'domain': self.extract_domain(url),
                'html': html,
                'text': text,
                'error': None
            }
        finally:
            if driver:
                driver.quit()
    
    def _extract_text(self, html: str) -> str:
        """
        HTMLからテキストを抽出・クリーニング
        
        Args:
            html: HTMLコンテンツ
        
        Returns:
            クリーニングされたテキスト
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 不要なタグを削除（スクリプト、スタイル、ヘッダー、フッター、ナビ）
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        
        # テキスト抽出
        text = soup.get_text(separator='\n', strip=True)
        
        # クリーニング
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            # 空行や短すぎる行をスキップ
            if len(line) < 10:
                continue
            # 繰り返される空白を削除
            line = re.sub(r'\s+', ' ', line)
            lines.append(line)
        
        return '\n'.join(lines)
