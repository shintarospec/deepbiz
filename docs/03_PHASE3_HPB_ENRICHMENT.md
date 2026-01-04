# Phase 3: HPB肉付け - Hot Pepper Beauty情報統合（計画）

**ステータス**: 🔄 計画中  
**実施予定**: Phase 2完了後  
**目的**: Google Maps + AI分析に加え、HPB情報でさらに詳細化

---

## 📋 概要

Phase 1（Google Maps情報）とPhase 2（AI企業分析）で構築した基盤に、Hot Pepper Beauty（HPB）の詳細情報を追加して、より充実したビジネスプロフィールを提供します。

## 🎯 目的

### ユーザー価値
- **クーポン情報**: お得な割引・特典を表示
- **メニュー・料金**: 詳細な施術内容と価格
- **スタッフ情報**: 担当者の紹介・実績
- **営業時間**: 詳細な営業スケジュール
- **口コミ**: HPB独自の口コミ情報

### DeepBiz価値
- **コンテンツ充実**: SEO効果向上
- **差別化**: Google Mapsにない情報提供
- **ユーザー滞在時間**: 詳細情報で回遊率向上

## 🔄 データフロー（Phase 3追加後）

```
Phase 0: CSV Import（1,905件基礎データ）
    ↓
Phase 1: データ収集（Google Maps情報）
    ↓ Place ID, CID, Website, 連絡先
    ↓
Phase 2: AI企業分析（Gemini）✅ 完了
    ↓ 強み・課題・業界分析
    ↓
Phase 3: HPB肉付け ← これから
    ↓ クーポン・求人・詳細情報
    ↓
【完成】充実したビジネスプロフィール
```

## 📊 実装計画

### Step 1: HPB URL取得

#### 目的
各クリニックのHot Pepper Beauty URLを取得

#### 処理内容
1. 店舗名 + 住所でHPB検索
2. 検索結果からクリニックURLを抽出
3. `Salon.hotpepper_url` に保存

#### 技術スタック
- Selenium（undetected-chromedriver）
- BeautifulSoup4
- リトライロジック（3回）

#### スクリプト
- `scripts/enrich_hpb_url.py`

```python
def get_hpb_url(name, address):
    """
    店舗名と住所からHPB URLを検索
    """
    search_query = f"{name} {address} site:beauty.hotpepper.jp"
    driver.get(f"https://www.google.com/search?q={search_query}")
    
    # 検索結果から beauty.hotpepper.jp のリンクを抽出
    soup = BeautifulSoup(driver.page_source, 'lxml')
    for link in soup.find_all('a', href=True):
        if 'beauty.hotpepper.jp' in link['href']:
            return extract_clean_url(link['href'])
    return None
```

#### 期待成果
- HPB URL取得率: 60-80%（美容クリニック特化のため中程度）

---

### Step 2: HPB詳細情報スクレイピング

#### 目的
HPB URLからクーポン・メニュー・口コミ等を取得

#### 取得データ項目

| 項目 | テーブル | 優先度 |
|-----|---------|--------|
| **クーポン情報** | Coupon | 高 |
| **メニュー・料金** | Menu（新規） | 高 |
| **営業時間** | Salon.business_hours | 中 |
| **定休日** | Salon.closed_days | 中 |
| **スタッフ情報** | Staff（新規） | 低 |
| **HPB口コミ** | ReviewSummary | 中 |

#### データモデル拡張

```python
# 新規テーブル: Menu
class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'))
    name = db.Column(db.String(255))           # メニュー名
    description = db.Column(db.Text)           # 説明
    price = db.Column(db.Integer)              # 料金（円）
    duration = db.Column(db.Integer)           # 所要時間（分）
    category = db.Column(db.String(100))       # カテゴリ（施術種類）

# 新規テーブル: Staff（将来実装）
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'))
    name = db.Column(db.String(255))
    position = db.Column(db.String(100))       # 役職
    specialties = db.Column(db.Text)           # 得意分野
    bio = db.Column(db.Text)                   # プロフィール
```

#### 技術スタック
- Selenium（JavaScript実行必須）
- BeautifulSoup4
- リトライロジック
- レート制限対策（2秒待機）

#### スクリプト
- `scripts/scrape_hpb_details.py`

```python
def scrape_hpb_details(hpb_url):
    """
    HPBページから詳細情報を抽出
    """
    driver.get(hpb_url)
    time.sleep(2)  # JavaScript読み込み待機
    
    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    # クーポン情報
    coupons = []
    for coupon_div in soup.find_all('div', class_='couponBox'):
        coupons.append({
            'title': coupon_div.find('h3').text.strip(),
            'description': coupon_div.find('p', class_='description').text.strip(),
            'price': extract_price(coupon_div)
        })
    
    # メニュー情報
    menus = []
    for menu_div in soup.find_all('div', class_='menuItem'):
        menus.append({
            'name': menu_div.find('h4').text.strip(),
            'price': extract_price(menu_div),
            'duration': extract_duration(menu_div)
        })
    
    return {
        'coupons': coupons,
        'menus': menus,
        'business_hours': extract_business_hours(soup),
        'closed_days': extract_closed_days(soup)
    }
```

---

### Step 3: データ統合・表示

#### 統合ロジック

1. **重複排除**
   - Google Maps口コミ vs HPB口コミ
   - 営業時間の不一致確認

2. **優先順位**
   - Place ID/CID: Google Maps（Phase 1）
   - 営業時間: HPB（詳細）
   - 口コミ: 両方表示（ソース明記）
   - クーポン・メニュー: HPB独自

3. **表示設計**
```html
<!-- サロン詳細ページ -->
<div class="salon-profile">
  <!-- Phase 1: Google Maps基本情報 -->
  <h1>{{ salon.name }}</h1>
  <p>{{ salon.address }}</p>
  <p>評価: {{ salon.rating }} (Google Maps)</p>
  
  <!-- Phase 2: AI分析 -->
  <div class="ai-analysis">
    <h3>💡 AI分析による特徴</h3>
    <ul>
      <li>強み: {{ analysis.strengths }}</li>
      <li>業界: {{ analysis.industry }}</li>
    </ul>
  </div>
  
  <!-- Phase 3: HPB情報 ← NEW -->
  <div class="hpb-info">
    <h3>🎫 クーポン情報</h3>
    {% for coupon in salon.coupons %}
      <div class="coupon-card">
        <h4>{{ coupon.title }}</h4>
        <p>{{ coupon.description }}</p>
        <span class="price">¥{{ coupon.price }}</span>
      </div>
    {% endfor %}
    
    <h3>📋 メニュー・料金</h3>
    <table class="menu-table">
      {% for menu in salon.menus %}
        <tr>
          <td>{{ menu.name }}</td>
          <td>¥{{ menu.price }}</td>
          <td>{{ menu.duration }}分</td>
        </tr>
      {% endfor %}
    </table>
  </div>
</div>
```

## 📅 実装スケジュール

### フェーズ1: HPB URL取得（2週間）
- Week 1: スクリプト開発・テスト（100件）
- Week 2: 本番実行（1,905件）

### フェーズ2: 詳細情報スクレイピング（3週間）
- Week 1: データモデル設計・マイグレーション
- Week 2: スクリプト開発・テスト（100件）
- Week 3: 本番実行（HPB URL保有者のみ）

### フェーズ3: データ統合・UI実装（2週間）
- Week 1: バックエンド統合ロジック
- Week 2: フロントエンド表示実装

**合計**: 7週間（約2ヶ月）

## 🚧 技術的課題

### 1. Bot検出回避
- **課題**: HPBは厳格なBot対策
- **対策**:
  - undetected-chromedriver使用
  - ランダム待機時間（1-3秒）
  - User-Agentローテーション
  - セッション管理

### 2. データ不一致
- **課題**: Google MapsとHPBで営業時間・電話番号が異なる場合
- **対策**:
  - 両方表示（情報源明記）
  - 最終更新日時を記録
  - ユーザーレポート機能

### 3. スクレイピング速度
- **課題**: 1,905件 × 複数ページ = 長時間処理
- **対策**:
  - バックグラウンドタスク化
  - 進捗表示（10件ごと）
  - 定期的ブラウザ再起動（15件ごと）

### 4. コスト管理
- **課題**: VPSのリソース消費（Chrome起動）
- **対策**:
  - 夜間バッチ実行
  - メモリ監視・自動再起動
  - 処理優先度設定

## 📊 期待成果

### データ充足率目標

| 項目 | 現在（Phase 2） | 目標（Phase 3） |
|-----|--------------|---------------|
| Place ID | 90.4% | 90.4% |
| Website | 91.8% | 91.8% |
| HPB URL | 0% | **70%** ← NEW |
| クーポン | 0% | **50%** ← NEW |
| メニュー | 0% | **60%** ← NEW |
| 営業時間（詳細） | 0% | **65%** ← NEW |

### SEO効果予測
- ページコンテンツ量: **+200%**（クーポン・メニュー追加）
- ユーザー滞在時間: **+50%**（詳細情報で回遊）
- 検索順位: **+10-20位**（コンテンツ充実）

### ユーザー価値
- 💰 **コスト比較**: 複数クリニックのメニュー料金を一覧比較
- 🎫 **お得情報**: クーポン情報で来店促進
- ⏰ **営業確認**: 詳細な営業時間で訪問計画

## 🔗 関連ドキュメント

- [Phase 0: CSV Import](00_PHASE0_CSV_IMPORT.md)
- [Phase 1: データ収集](01_PHASE1_DATA_COLLECTION.md)
- [Phase 2: AI企業分析](02_PHASE2_AI_ANALYSIS.md)
- [HPBスクレイピング技術ガイド](HPB_SCRAPING_GUIDE.md)
- [データベーススキーマ](../models.py)

## 📝 次のステップ

Phase 3完了後、以下を検討：

1. **Phase 4: TheSide連携** - 営業支援プラットフォームとの統合
2. **多業種展開** - 飲食店・宿泊施設への拡大
3. **API公開** - 外部サービスへのデータ提供
4. **ユーザーレビュー機能** - DeepBiz独自の口コミシステム

詳細は [プロジェクト計画](PROJECT_PLAN.md) を参照してください。
