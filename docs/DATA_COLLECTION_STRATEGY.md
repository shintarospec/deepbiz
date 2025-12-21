# データ収集戦略 - 東京23区美容クリニック

## 概要
東京23区の美容クリニックデータを網羅的に収集し、GMAP・HPB・公式サイトから情報を統合する。

---

## フェーズ1: 既存CSVデータのGMAP補完 【優先度：最高】

### Phase 1A: 高速API補完（Place ID + 評価のみ） 🚀

#### 目的
トリビューCSVの1,905件に対してコアデータを最速で取得

#### 取得する情報
- **Place ID**（Googleマップの一意識別子）
- **Rating**（評価・星数）
- **Review Count**（口コミ数）

#### 実行方法
```bash
# VPS上で実行
cd /var/www/salon_app
source venv/bin/activate
screen -dmS gmap_enrich bash -c "python scripts/enrich_gmap.py > gmap_enrich.log 2>&1"

# 進捗確認
screen -r gmap_enrich  # Ctrl+A → D で離脱
tail -f gmap_enrich.log
```

#### コスト・時間
- **API費用**: 約$61（Text Search API: $32/1000リクエスト × 1,905件）
- **所要時間**: 2〜3時間（約6件/分、Selenium不使用）
- **API無料枠**: $200/月（十分に余裕あり）

#### スクリプト
- **ファイル**: `scripts/enrich_gmap.py`
- **状態**: CID・Website取得をスキップした高速版に修正済み
- **更新日**: 2025-12-22

---

### Phase 1B: CID・Website取得（Selenium Scraping） 🐢

#### 目的
Place IDが判明したクリニックに対してCIDと公式サイトURLを追加取得

#### 背景
- **CID取得**: SeleniumでGoogleマップページをロードし、URLからCIDパラメータを抽出
- **課題**: ChromeDriver接続が頻繁にタイムアウト（120秒/件）
- **判断**: Phase 1Aの高速処理を優先し、CID/Websiteは別途処理

#### 取得する情報
- **CID**（Googleマップ直リンク用ID）
- **Website URL**（公式サイトURL - CSVに無い場合のみ）

#### 取得方法の選択肢

**Option A: Selenium Scraping（無料、低速）**
```python
# scripts/enrich_cid.py - 新規作成予定
# Place IDからCID・Websiteをスクレイピング
# - timeout対策（最大60秒）
# - retry機能（3回まで）
# - checkpoint保存（100件ごと）
```
- **コスト**: $0（API不使用）
- **所要時間**: 8〜10時間（推定、timeout対策次第）
- **対象**: 1,214件（Phase 1A完了後の残り）

**Option B: Place Details API（有料、高速）**
```python
# Place Details APIでWebsite URLを直接取得
# CIDはURL構造から推測可能な場合あり
```
- **コスト**: 約$21（Place Details API: $17/1000 × 1,214件、websiteフィールド追加で$0.003増）
- **所要時間**: 20分程度
- **精度**: 公式サイトURLは100%、CIDは取得不可

**推奨**: まずPhase 1Aを完了させ、結果を見て判断（CSVに既に91.8%のURLあり）

---

### Phase 1C: 公式サイト解析（Contact Page Scraping） 📧

#### 目的
公式サイトURLから問い合わせページ・メールアドレスを抽出

#### 対象データ
- **Phase 1B完了後**: Website URL保有クリニック（約1,749件 + Phase 1B追加分）
- **現状**: CSVから1,749件（91.8%）が既にURLを保有

#### 取得する情報
1. **問い合わせページURL**
   - パターン: `/contact`, `/inquiry`, `/form`, `/toiawase`
   - 例: `https://example-clinic.jp/contact/`

2. **メールアドレス**
   - 正規表現で抽出: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
   - 例: `info@example-clinic.jp`

3. **電話番号**（オプション）
   - パターン: `03-1234-5678`, `0120-XXX-XXX`

#### スクレイピングフロー

```python
# scripts/scrape_website_contacts.py - 新規作成予定

def scrape_contact_info(website_url):
    """
    公式サイトから問い合わせ情報を取得
    
    Args:
        website_url: クリニックの公式サイトURL
    
    Returns:
        dict: {
            'contact_page_url': str or None,
            'emails': list[str],
            'phones': list[str]
        }
    """
    driver = get_stealth_driver()
    result = {'contact_page_url': None, 'emails': [], 'phones': []}
    
    try:
        # Step 1: トップページをロード
        driver.get(website_url)
        time.sleep(2)
        
        # Step 2: 問い合わせページリンクを探す
        contact_keywords = ['お問い合わせ', '問い合わせ', 'contact', 'お問合せ', 'inquiry']
        contact_link = None
        
        for keyword in contact_keywords:
            elements = driver.find_elements(By.PARTIAL_LINK_TEXT, keyword)
            if elements:
                contact_link = elements[0].get_attribute('href')
                break
        
        # Step 3: 問い合わせページが見つかったらロード
        if contact_link:
            result['contact_page_url'] = contact_link
            driver.get(contact_link)
            time.sleep(2)
        
        # Step 4: ページ全体からメール・電話を抽出
        page_source = driver.page_source
        
        # メールアドレス抽出
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, page_source)
        result['emails'] = list(set(emails))  # 重複除去
        
        # 電話番号抽出（日本の固定電話・フリーダイヤル）
        phone_pattern = r'0\d{1,4}-\d{1,4}-\d{4}'
        phones = re.findall(phone_pattern, page_source)
        result['phones'] = list(set(phones))
        
        return result
        
    except Exception as e:
        print(f"エラー: {website_url} - {e}")
        return result
    
    finally:
        driver.quit()


def enrich_contacts():
    """全クリニックの問い合わせ情報を収集"""
    with app.app_context():
        # Website URLがあるクリニックを取得
        salons = Salon.query.filter(Salon.website_url.isnot(None)).all()
        total = len(salons)
        
        print(f"対象クリニック: {total}件")
        
        for i, salon in enumerate(salons, 1):
            print(f"\n[{i}/{total}] {salon.name}")
            
            contact_info = scrape_contact_info(salon.website_url)
            
            # DBに保存（新規カラム追加が必要）
            # salon.contact_page_url = contact_info['contact_page_url']
            # salon.contact_emails = ','.join(contact_info['emails'])
            # salon.contact_phones = ','.join(contact_info['phones'])
            
            print(f"  問い合わせページ: {contact_info['contact_page_url']}")
            print(f"  メール: {contact_info['emails']}")
            print(f"  電話: {contact_info['phones']}")
            
            db.session.commit()
            
            time.sleep(3)  # サーバー負荷対策
```

#### DB拡張（必要な場合）

```python
# models.py - Salon モデルに追加
class Salon(db.Model):
    # ... 既存フィールド
    
    # Phase 1C で追加
    contact_page_url = db.Column(db.String(500))  # 問い合わせページURL
    contact_emails = db.Column(db.String(500))    # メールアドレス（カンマ区切り）
    contact_phones = db.Column(db.String(200))    # 電話番号（カンマ区切り）
```

#### 実行方法
```bash
cd /var/www/salon_app
source venv/bin/activate
screen -dmS website_scrape bash -c "python scripts/scrape_website_contacts.py > website_scrape.log 2>&1"
```

#### コスト・時間
- **API費用**: $0（スクレイピングのみ）
- **所要時間**: 8〜12時間（約3件/分、各サイト3秒待機）
- **対象**: 1,749件（現在Website URL保有数）

#### 注意事項
- **robots.txt遵守**: 各サイトのクローリングポリシーを確認
- **レート制限**: 同一ドメインへの連続アクセスを避ける（3秒待機）
- **エラーハンドリング**: サイトダウン・403エラーに対応
- **個人情報保護**: 取得したメールアドレスの取り扱いに注意

---

### 対象データ
- **件数**: 1,905件（東京都のクリニック）
- **ソース**: `csv/deepbiz_list - トリビュー.csv`
- **現状**: Phase 1A実行中（691件完了、1,214件残）

---

## フェーズ2: GMAP新規クリニック発見 【優先度：高】

### 目的
CSVに含まれない新規クリニックをGoogleマップ検索で発見

### 検索戦略
**町名レベル × キーワード検索**を実施（検索結果20件上限問題への対策）

#### エリアデータ
- **総数**: 3,423エリア（東京都の町名単位）
- **ソース**: `scraping_data.db` の `Area` テーブル
- **例**: 世田谷区三軒茶屋、渋谷区道玄坂、港区赤坂

#### 検索キーワード候補
1. **美容クリニック** （基本）
2. **美容外科** （専門性高）
3. **美容皮膚科** （皮膚科系）
4. **美容整形** （整形外科系）
5. **クリニック** （広範囲、要フィルタリング）

**推奨**: まず「美容クリニック」1キーワードで実施（3,423タスク）

### 実装内容

#### 2-1. タスク生成スクリプト作成
```python
# scripts/generate_gmap_discovery_tasks.py
from app import app, db
from models import Area, ScrapingTask

KEYWORDS = ["美容クリニック"]

with app.app_context():
    areas = Area.query.filter(Area.prefecture == "東京都").all()
    
    for area in areas:
        for keyword in KEYWORDS:
            search_query = f"{area.city} {keyword}"
            
            # 既存タスクチェック
            existing = ScrapingTask.query.filter_by(
                task_type='gmap_discovery',
                search_keyword=search_query
            ).first()
            
            if not existing:
                task = ScrapingTask(
                    task_type='gmap_discovery',
                    search_keyword=search_query,
                    target_url=None,  # HPB用カラム
                    status='未実行',
                    category_id=1
                )
                db.session.add(task)
    
    db.session.commit()
    print(f"生成タスク数: {len(areas) * len(KEYWORDS)}")
```

#### 2-2. GMAP検索タスク実行機能追加
`app.py` に以下を追加：

```python
@app.route('/admin/tasks/<int:task_id>/execute_gmap', methods=['POST'])
def execute_gmap_task(task_id):
    task = ScrapingTask.query.get_or_404(task_id)
    
    if task.task_type != 'gmap_discovery':
        return jsonify({'error': '対象外タスク'}), 400
    
    # Google Maps Text Search API実行
    results = get_gmap_place_details(task.search_keyword)
    
    new_count = 0
    for place in results.get('results', []):
        place_id = place.get('place_id')
        
        # 既存チェック（Place IDで重複排除）
        existing = Salon.query.filter_by(place_id=place_id).first()
        if existing:
            continue
        
        # 新規クリニック追加
        salon = Salon(
            name=place.get('name'),
            address=place.get('formatted_address'),
            place_id=place_id
        )
        db.session.add(salon)
        new_count += 1
        
        # CID・Website・Rating取得
        enrich_salon_with_gmap_data(salon)
    
    task.status = '完了'
    task.last_run_at = datetime.now()
    db.session.commit()
    
    return jsonify({'new_clinics': new_count})
```

#### 2-3. 管理画面の拡張
- タスクタイプフィルタ追加（HPB / GMAP Discovery）
- バッチ実行機能（複数タスクを一括実行）
- 進捗表示（実行中タスク数、完了率）

### コスト試算
- **3,423タスク × $0.032 = $109.5**
- 新規クリニック発見数：推定200〜500件

---

## フェーズ3: ホットペッパービューティ（HPB）補完 【優先度：中】

### 目的
HPBに掲載されているクリニックの追加情報を取得

### HPBの特徴
- **掲載数**: GMAP より少ない（広告掲載クリニックのみ）
- **情報の質**: 高い（クーポン、詳細メニュー、予約リンク）
- **重複**: 多くはGMAPで既に発見済み

### スクレイピング対象

#### URL構造
```
https://clinic.beauty.hotpepper.jp/prefecture13/area01/  # 千代田区
https://clinic.beauty.hotpepper.jp/prefecture13/area02/  # 中央区
https://clinic.beauty.hotpepper.jp/prefecture13/area03/  # 港区
...
https://clinic.beauty.hotpepper.jp/prefecture13/area23/  # 江戸川区
```

**合計**: 23区 = 23タスク

#### 取得する情報
- クリニック名
- HPB URL
- 住所
- 評価・口コミ数（HPB独自）
- クーポン情報
- 施術メニュー

### 実装内容

#### 3-1. HPBタスク生成
```python
# scripts/generate_hpb_tasks.py
TOKYO23_AREAS = {
    'area01': '千代田区',
    'area02': '中央区',
    'area03': '港区',
    # ... area23まで
}

for area_code, ward_name in TOKYO23_AREAS.items():
    url = f"https://clinic.beauty.hotpepper.jp/prefecture13/{area_code}/"
    
    task = ScrapingTask(
        task_type='hpb_scraping',
        target_url=url,
        search_keyword=ward_name,
        status='未実行',
        category_id=1
    )
    db.session.add(task)
```

#### 3-2. HPBスクレイピング実行
```python
@app.route('/admin/tasks/<int:task_id>/execute_hpb', methods=['POST'])
def execute_hpb_task(task_id):
    task = ScrapingTask.query.get_or_404(task_id)
    
    driver = get_stealth_driver()
    driver.get(task.target_url)
    
    # クリニックリスト取得
    clinic_links = driver.find_elements(By.CSS_SELECTOR, '.clinic-item a')
    
    for link in clinic_links:
        clinic_url = link.get_attribute('href')
        
        # 既存チェック（HPB URLで）
        existing = Salon.query.filter_by(hotpepper_url=clinic_url).first()
        if existing:
            # 評価・クーポン更新
            update_hpb_data(existing, clinic_url)
        else:
            # 新規追加
            scrape_hpb_clinic(clinic_url)
    
    task.status = '完了'
    task.last_run_at = datetime.now()
    db.session.commit()
```

### データ統合戦略
1. **住所マッチング**: HPBで取得した住所がGMAPデータと一致する場合、同一クリニックとして統合
2. **評価の併記**: Google評価とHPB評価を両方表示
3. **クーポン追加**: HPB独自のクーポン情報を `Coupon` テーブルに保存

---

## フェーズ4: 公式サイト詳細解析 【優先度：低】

### 目的
各クリニックの公式サイトから詳細情報を抽出

### 取得する情報
- **問い合わせページURL** (`inquiry_url`)
- **メールアドレス** (`email`)
- **電話番号**
- **診療時間**
- **施術メニュー詳細**

### 実装方針
```python
# scripts/analyze_websites.py
salons = Salon.query.filter(Salon.website_url.isnot(None)).all()

for salon in salons:
    try:
        driver.get(salon.website_url)
        
        # 問い合わせページ検出
        contact_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "お問い合わせ")
        if contact_links:
            salon.inquiry_url = contact_links[0].get_attribute('href')
        
        # メールアドレス抽出
        page_source = driver.page_source
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_source)
        if emails:
            salon.email = emails[0]
        
        db.session.commit()
    except Exception as e:
        print(f"Error: {salon.name} - {e}")
```

---

## タスク実行順序（推奨）

### ステップ1: 既存データの価値最大化
1. ✅ CSVインポート（1,905件）完了
2. ⏳ **GMAP補完実行（残り1,895件）** ← 今すぐ実行
3. ⏳ データ確認・検証

### ステップ2: 新規クリニック発見
4. ⏳ GMAPタスク生成（3,423タスク）
5. ⏳ GMAPタスク実行機能実装
6. ⏳ バッチ実行（段階的：100→500→全件）

### ステップ3: 補完データ収集
7. ⏳ HPBタスク生成（23タスク）
8. ⏳ HPBスクレイピング実行
9. ⏳ データ統合・重複排除

### ステップ4: 詳細情報抽出
10. ⏳ 公式サイト解析スクリプト実装
11. ⏳ 問い合わせページ・メール抽出

---

## API費用総見積もり

| フェーズ | 件数 | 単価 | 合計 |
|---------|------|------|------|
| フェーズ1（既存補完） | 1,895 | $0.032 | $60.64 |
| フェーズ2（新規発見） | 3,423 | $0.032 | $109.54 |
| **合計** | **5,318** | - | **$170.18** |

**Google Maps API 無料枠**: $200/月  
**残額**: $29.82（追加検索に使用可能）

---

## データベース最終目標

### 目標クリニック数
- CSVベース: 1,905件
- GMAP新規発見: +200〜500件
- HPB新規発見: +50〜100件
- **合計見込み**: 2,200〜2,500件

### データ充実度
- ✅ Place ID: 100%
- ✅ CID: 100%
- ✅ Website URL: 90%+
- ✅ Google Rating: 90%+
- ⏳ HPB Rating: 30〜50%
- ⏳ クーポン: 20〜30%
- ⏳ 問い合わせURL: 50〜70%
- ⏳ メールアドレス: 30〜50%

---

## 次のアクション

**今すぐ実行可能：**
```bash
# フェーズ1: 既存1,895件のGMAP補完
ssh ubuntu@133.167.116.58
cd /var/www/salon_app
source venv/bin/activate
python scripts/enrich_gmap.py
```

**実装が必要：**
- フェーズ2: GMAPタスク生成・実行スクリプト
- フェーズ3: HPBタスク生成・実行スクリプト
- フェーズ4: ウェブサイト解析スクリプト

---

**最終更新日**: 2025-12-21  
**ステータス**: フェーズ1実行待ち
