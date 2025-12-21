# 東京23区×美容クリニック特化版へのリファクタリング計画

## 削除する機能

### 1. 不要なスクレイパースクリプト
- `get_all_hair_prefecture_urls.py` - 美容院用
- `get_all_nail_prefecture_urls.py` - ネイルサロン用
- `get_all_eyelash_prefecture_urls.py` - まつエク用
- `get_all_relax_prefecture_urls.py` - リラクサロン用
- `get_all_esthe_prefecture_urls.py` - エステ用
- `get_area_urls.py` - 汎用エリアURL取得
- これらの対応するテキストファイルも削除

### 2. app.py から削除する機能
- 都道府県選択機能（23区固定に）
- 複数カテゴリ選択（美容クリニックのみに）
- 複雑なタスク生成ロジック（`_generate_tasks_background`）
- 求人取得機能（リジョブ関連、オプション）
- HPB詳細更新機能（美容クリニックはclinic.beauty.hotpepper.jpなので調整必要）

### 3. models.py の簡素化
- Coupon モデル（未使用）
- Advertisement モデル（必要に応じて保持）

### 4. テンプレートの簡素化
- エリア選択UIを23区のみに
- カテゴリ選択UIを削除または非表示

## 保持する機能

### コア機能
- サロン検索（23区×美容クリニック）
- Google Map API連携
- HPBスクレイピング（クリニック版）
- レビュー表示（Google/HPB）
- 管理画面（CRUD）
- スクレイピングタスク管理

### データベース
- Salon, Category, ReviewSummary, Job
- Area（23区のみ）
- ScrapingTask

## 実装手順

1. ✓ スクリプト作成
   - create_tokyo23_areas.py
   - cleanup_database.py
   - generate_simple_tasks.py

2. app.py のリファクタリング
   - 都道府県選択ロジックを23区固定に
   - カテゴリを美容クリニック固定に
   - 不要なルートを削除

3. 不要ファイルの削除

4. テンプレート更新

5. VPS上で実行
   - データベースバックアップ
   - クリーンアップ実行
   - タスク再生成
   - アプリ再起動

## メリット

- タスク数: 160,275 × 6カテゴリ → 23区のみ（約23タスク）
- コード量: 50%削減目標
- 保守性: 大幅向上
- パフォーマンス: スクレイピング効率化
- フォーカス: 美容クリニックに特化
