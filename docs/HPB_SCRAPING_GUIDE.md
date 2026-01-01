# HPB（ホットペッパービューティー）スクレイピングとデータマージ実装ガイド

## 📋 概要

Google MapsとHPBの二重スクレイピング体制を構築し、より網羅的なクリニックデータを収集します。

## 🎯 実装内容

### 1. HPB URLスクレイピング
**スクリプト:** `scripts/get_tokyo23_clinic_urls.py`

- 東京23区の美容クリニック町名レベルURLを収集
- 推定タスク数: 500〜2,000件

**実行方法:**
```bash
cd /var/www/salon_app
source venv/bin/activate
python scripts/get_tokyo23_clinic_urls.py
```

**出力:** `tokyo23_clinic_urls.txt`

### 2. HPBタスク生成
**スクリプト:** `scripts/generate_hpb_tasks.py`

- tokyo23_clinic_urls.txtからタスクを生成
- ScrapingTaskテーブルに登録（task_type='HPB'）

**実行方法:**
```bash
python scripts/generate_hpb_tasks.py
```

### 3. HPBスクレイピング実行
**スクリプト:** `run_hpb_scraper.py`（既存）

- HPBタスクを実行してサロン情報を収集
- 自動的にGmapデータとのマッチングを試行

**実行方法:**
```bash
# 特定のタスクIDを指定
python run_hpb_scraper.py 1234

# 最も古い未実行タスクを実行
python run_hpb_scraper.py
```

## 🔄 データマージ戦略

### マージの判定基準

1. **住所の類似度** (70%の重み)
   - Levenshtein距離で計算
   - 正規化: 全角→半角、空白削除、ハイフン統一

2. **名前の類似度** (30%の重み)
   - fuzzy matching
   - 正規化: 空白削除、カタカナ統一、小文字化

3. **閾値**
   - 総合スコア 0.75以上でマッチと判定

### マージの動作

```
【パターン1: HPBで新規発見したクリニック】
1. HPBスクレイピングでクリニックを発見
2. Gmapの既存データを検索
3. 類似度0.75以上のマッチがあれば：
   → Gmapサロンにhotpepper_url, name_hpbを追加
   → HPBのみのレコードを削除
4. マッチなし：
   → HPBのみのサロンとして保存

【パターン2: Gmapで先に登録済み】
1. Gmapスクレイピングでplace_id付きで登録済み
2. 後日HPBスクレイピングで同じクリニックを発見
3. 自動マッチング→HPB情報を追加

【パターン3: 両方からデータがある（理想）】
- place_id: Google Mapsから
- hotpepper_url: HPBから
- name: Gmapの名前（マスター）
- name_hpb: HPBの名前
- address: Gmapの住所（マスター）
- ReviewSummary:
  - source_name='Google': Gmapの評価
  - source_name='Hot Pepper': HPBの評価
```

## 📂 ファイル構成

```
/var/www/salon_app/
├── scripts/
│   ├── get_tokyo23_clinic_urls.py  # [新] HPB URL収集
│   ├── generate_hpb_tasks.py       # [新] HPBタスク生成
│   └── merge_gmap_hpb.py           # [新] 手動マージツール
├── merge_helpers.py                # [新] マージロジック
├── run_hpb_scraper.py              # [既存] HPBスクレイピング実行
├── run_hpb_details_updater.py      # [既存] HPB詳細情報更新
└── tokyo23_clinic_urls.txt         # [生成] URL一覧
```

## ⚙️ 実行手順（完全版）

### Step 1: HPB URLの収集
```bash
cd /var/www/salon_app
source venv/bin/activate
python scripts/get_tokyo23_clinic_urls.py
```
→ `tokyo23_clinic_urls.txt` が生成される（数百〜2,000行）

### Step 2: HPBタスクの生成
```bash
python scripts/generate_hpb_tasks.py
```
→ 管理画面で確認: http://133.167.116.58/admin/tasks

### Step 3: HPBスクレイピングの実行
```bash
# 1件ずつ実行（テスト）
python run_hpb_scraper.py

# バッチ実行（cronで設定）
*/10 * * * * cd /var/www/salon_app && source venv/bin/activate && python run_hpb_scraper.py
```

### Step 4: 手動マージ（必要に応じて）
```bash
# HPBのみのサロンをGmapデータとマッチング
python scripts/merge_gmap_hpb.py
```

## 📊 データ品質の確認

```sql
-- HPBとGmap両方のデータがあるクリニック
SELECT COUNT(*) FROM salon 
WHERE place_id IS NOT NULL 
AND hotpepper_url IS NOT NULL;

-- HPBのみのクリニック
SELECT COUNT(*) FROM salon 
WHERE place_id IS NULL 
AND hotpepper_url IS NOT NULL;

-- Gmapのみのクリニック
SELECT COUNT(*) FROM salon 
WHERE place_id IS NOT NULL 
AND hotpepper_url IS NULL;
```

## 🛡️ エラー対処

### エラー1: URLが取得できない
```
原因: HPBサイトの構造変更
対処: get_tokyo23_clinic_urls.py のセレクタを更新
```

### エラー2: マージが正しく動作しない
```
原因: 住所や名前の表記揺れ
対処: 
1. merge_helpers.py の正規化ロジックを調整
2. 閾値（threshold）を調整（現在0.75）
3. 手動で管理画面から紐付け
```

### エラー3: スクレイピングが失敗する
```
原因: ボット検知、レート制限
対処:
1. time.sleep()の秒数を増やす
2. undetected-chromedriverのバージョン確認
3. User-Agentを最新に更新
```

## 🎓 カスタマイズ例

### マッチング閾値の調整
```python
# merge_helpers.py の threshold を変更
threshold = 0.75  # デフォルト
threshold = 0.80  # より厳格に（精度重視）
threshold = 0.70  # より緩く（網羅性重視）
```

### 重み付けの調整
```python
# 住所と名前の重みを変更
total_score = address_sim * 0.7 + name_sim * 0.3  # デフォルト
total_score = address_sim * 0.8 + name_sim * 0.2  # 住所重視
total_score = address_sim * 0.5 + name_sim * 0.5  # 均等
```

## 📈 期待される効果

1. **データ網羅性の向上**
   - Google Mapsで漏れたクリニックをHPBで補完
   - HPBにないクリニックをGmapで補完

2. **データ品質の向上**
   - 両方のレビューデータを保持
   - 情報の相互検証が可能

3. **ユーザー体験の向上**
   - より多くのクリニック選択肢
   - 複数サイトの評価を比較可能

## 🔧 今後の改善案

1. 電話番号マッチングの追加
2. 営業時間の比較機能
3. 管理画面でのマージ候補表示
4. マッチング精度のログ収集と分析
