# HTMLをファイルに保存することに特化したコード
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = None
try:
    print("Chromeを起動し、HTMLの取得を開始します...")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    stealth(driver, languages=["ja-JP", "ja"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

    driver.get("https://beauty.hotpepper.jp/")
    time.sleep(10)
    html_content = driver.page_source
    
    # --- 取得したHTMLをファイルに書き出す ---
    file_name = "hotpepper_page.html"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ HTMLの取得とファイル保存に成功しました！ ({file_name})")

except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")
finally:
    if driver:
        driver.quit()
        print("--- 処理を終了しました ---")
