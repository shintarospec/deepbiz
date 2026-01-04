# Phase 0: CSV Import - 初期データ投入

**実施日**: 2025年12月21日  
**対象**: 美容クリニック情報CSV  
**結果**: 1,905件登録完了

---

## 📋 概要

トリビュー社から提供されたCSVデータを、DeepBizデータベースの初期データとして投入しました。

## 📊 データソース

### CSVファイル情報
- **ファイル名**: `csv/deepbiz_list - トリビュー.csv`
- **ファイルサイズ**: 1.3MB
- **データ構造**:
  ```csv
  ID,店舗名,住所,公式URL
  1,菊池皮膚科クリニック,北海道札幌市北区北17条西3丁目21 プロスTJビル1F,https://www.kikuchi-hifuka.jp/
  2,麻生形成外科クリニック,北海道札幌市北区北区北40条西4丁目2番1号 麻生メディカルビル5F,https://www.asabu-keisei.jp/
  ...
  ```

## 🔧 実装内容

### インポートスクリプト
- **ファイル**: `scripts/import_csv_clinics.py`
- **処理内容**:
  1. CSVファイル読み込み（UTF-8エンコーディング）
  2. 東京都のクリニックのみフィルタリング
  3. Salonテーブルに登録
  4. カテゴリ「美容クリニック」に自動紐付け
  5. 重複チェック（店舗名 + 住所）

### 処理ロジック

```python
def import_csv_clinics(csv_path, prefecture_filter='東京'):
    with app.app_context():
        category = Category.query.filter_by(name='美容クリニック').first()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            for row in rows[1:]:  # ヘッダースキップ
                name = row[1].strip()
                address = row[2].strip()
                official_url = row[3].strip()
                
                # 都道府県フィルタ
                if prefecture_filter not in address:
                    continue
                
                # 重複チェック
                existing = Salon.query.filter_by(
                    name=name,
                    address=address
                ).first()
                
                if existing:
                    continue
                
                # 新規登録
                new_salon = Salon(
                    name=name,
                    address=address,
                    website_url=official_url
                )
                db.session.add(new_salon)
                new_salon.categories.append(category)
                db.session.commit()
```

## 📈 結果

### 登録件数
- ✅ **総件数**: 1,905件
- ✅ **対象地域**: 東京都
- ✅ **カテゴリ**: 美容クリニック

### データ項目（初期状態）

| 項目 | 件数 | 備考 |
|-----|------|------|
| **name** | 1,905件（100%） | 店舗名 |
| **address** | 1,905件（100%） | 住所 |
| **website_url** | 一部のみ | CSVに記載のもののみ |
| place_id | 0件 | Phase 1で追加予定 |
| cid | 0件 | Phase 1で追加予定 |
| email | 0件 | Phase 1で追加予定 |
| phone | 0件 | Phase 1で追加予定 |

### データベーススキーマ

```sql
-- Salonテーブル（Phase 0時点）
CREATE TABLE salon (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,           -- ✅ 登録済み
    address VARCHAR(500) NOT NULL,        -- ✅ 登録済み
    website_url VARCHAR(500),             -- △ 一部のみ
    place_id VARCHAR(255),                -- ❌ NULL
    cid VARCHAR(255),                     -- ❌ NULL
    email VARCHAR(255),                   -- ❌ NULL
    phone VARCHAR(50),                    -- ❌ NULL
    ...
);

-- Categoryテーブル
INSERT INTO category (name) VALUES ('美容クリニック');

-- salon_category関連テーブル
-- 1,905件 × 「美容クリニック」カテゴリで紐付け
```

## 🔍 データ品質チェック

### 確認事項
1. ✅ 重複レコードなし（店舗名 + 住所でユニーク）
2. ✅ 必須項目（name, address）すべて入力済み
3. ✅ 東京都以外のレコード除外済み
4. ⚠️ website_url は一部のみ（Phase 1で補完予定）

### SQL確認コマンド

```sql
-- 総件数確認
SELECT COUNT(*) FROM salon;
-- → 1,905

-- カテゴリ別件数
SELECT c.name, COUNT(s.id)
FROM salon s
JOIN salon_category sc ON s.id = sc.salon_id
JOIN category c ON sc.category_id = c.id
GROUP BY c.name;
-- → 美容クリニック: 1,905

-- 住所の都道府県分布
SELECT SUBSTRING(address, 1, 3) AS prefecture, COUNT(*)
FROM salon
GROUP BY prefecture;
-- → 東京都: 1,905
```

## 📝 次のステップ

Phase 0で基礎データ（1,905件）が整いました。次のPhase 1では、Google Maps情報を追加取得します：

1. **Phase 1A**: Place ID取得（Google Maps Search API）
2. **Phase 1B**: CID取得（Seleniumスクレイピング）
3. **Phase 1C**: Web情報取得（Website, Email, Phone抽出）

詳細は [Phase 1: データ収集](01_PHASE1_DATA_COLLECTION.md) を参照してください。

## 🔗 関連ファイル

- **CSVデータ**: [csv/deepbiz_list - トリビュー.csv](../csv/deepbiz_list - トリビュー.csv)
- **インポートスクリプト**: [scripts/import_csv_clinics.py](../scripts/import_csv_clinics.py)
- **データモデル**: [models.py](../models.py)
