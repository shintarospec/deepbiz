# DeepBiz プロジェクト開発履歴

このドキュメントは、プロジェクトの時系列での開発記録です。各フェーズの目的・実施内容・成果を記載しています。

---

## Phase 0: CSV Import（2025年12月21日）

### 目的
トリビュー社から提供されたCSVデータを初期データとして投入

### 実施内容
1. **CSVファイル確認**
   - ファイル名: `csv/deepbiz_list - トリビュー.csv`（1.3MB）
   - データ構造: ID, 店舗名, 住所, 公式URL

2. **インポートスクリプト実行**
   - スクリプト: `scripts/import_csv_clinics.py`
   - 対象: 東京都のクリニックのみフィルタ
   - カテゴリ: 「美容クリニック」で登録

### 成果
- ✅ **登録件数**: 1,905件
- ✅ **データ項目**: 店舗名、住所、公式URL（一部）
- ✅ **カテゴリ**: 美容クリニックに自動紐付け

### データベース状態
```
Salon テーブル: 1,905レコード
  - name: 100%
  - address: 100%
  - website_url: 一部（CSVに記載のもののみ）
  - place_id: NULL
  - cid: NULL
  - email: NULL
  - phone: NULL
```

---

## Phase 1: データ収集（2025年12月22-24日）

### 目的
既存1,905件のクリニックに対して、Google Maps情報を追加取得

### Phase 1A: Place ID取得（12月22日）

#### 実施内容
- Google Maps Search APIで店舗名+住所検索
- Place IDを取得してSalonテーブルに保存

#### 成果
- ✅ **取得成功**: 1,722件 / 1,905件
- ✅ **成功率**: 90.4%
- ❌ **失敗**: 183件（閉業・移転・存在しない店舗）

### Phase 1B: CID取得（12月22-24日）

#### 実施内容
- SeleniumでGoogle Maps URLを解析
- Place IDからCIDに変換（URL内の16進数パターン抽出）
- 改善版v2実装（6つの抽出パターン、リトライロジック）

#### 成果
- ✅ **取得成功**: 1,512件 / 1,722件（Place ID保有者）
- ✅ **成功率**: 87.8%
- ❌ **失敗**: 210件（タイムアウト、無効Place ID）
- 🔄 **ブラウザ再起動**: 114回（メモリリーク対策）

#### 技術改善点
1. JavaScriptロード待機時間延長（3秒 → 5秒）
2. URL確認の複数回試行（3回チェック）
3. 6つの抽出パターン実装（ludocid、data-cid等）
4. リトライロジック（最大3回）
5. 定期的ブラウザ再起動（15件ごと）

### Phase 1C: Web情報取得（12月23-24日）

#### 実施内容
- 公式WebサイトからHTML取得
- メールアドレス、電話番号、問い合わせフォームURLを抽出
- BeautifulSoup + 正規表現による自動抽出

#### 成果
- ✅ **Website URL**: 1,749件（91.8%）
- ✅ **問い合わせURL**: 762件（40.0%）
- ✅ **Phone**: 1,328件（69.7%）
- ⚠️ **Email**: 367件（19.3%）← 要改善

#### 連絡可能性
- Website/Phone **いずれか有り**: 1,749件（91.8%）
- **問い合わせ手段**（inquiry/email いずれか）: 838件（44.0%）
- **完全連絡先**（Website+問い合わせ+Phone）: 797件（41.8%）

### Phase 1 最終状態（12月24日時点）

```
データ充足率:
  Place ID:   1,722件（90.4%）✅
  CID:        1,512件（79.4%）✅
  Website:    1,749件（91.8%）✅
  問い合わせ:   762件（40.0%）✅
  Phone:      1,328件（69.7%）✅
  Email:        367件（19.3%）⚠️
```

### 関連ドキュメント
- [PHASE1_RESULTS_SUMMARY.md](PHASE1_RESULTS_SUMMARY.md) - 詳細結果レポート

---

## Phase 2: AI企業分析（2025年12月 - 2026年1月4日）

### 目的
Gemini AIを活用した企業Webサイト自動解析機能の実装

### 設計フェーズ（12月末）

#### 検討内容
1. **AIモデル選定**
   - Gemini 2.0 Flash → 2.5 Flash-Lite に変更
   - コスト: 0.12円/社（90日キャッシュで実質0円に近づく）

2. **アーキテクチャ設計**
   - Webスクレイピング → AI解析 → キャッシュ保存
   - 90日間有効キャッシュで再解析コスト削減

3. **データモデル設計**
   - `CompanyAnalysis` テーブル作成
   - 14フィールド（domain, business_description, industry等）

### 実装フェーズ（12月末 - 1月3日）

#### 実施内容
1. **Webスクレイピング機能**
   - `services/web_scraper.py` 実装
   - requests + Seleniumフォールバック
   - HTMLクリーニング（15,000文字制限）

2. **Gemini AI連携**
   - `services/gemini_analyzer.py` 実装
   - Gemini 2.5 Flash-Lite統合
   - 構造化プロンプト設計
   - JSON自動抽出機能

3. **データベース**
   - `CompanyAnalysis` モデル実装
   - マイグレーション作成・適用

4. **API実装**
   - `api/company_analysis.py` 実装
   - RESTful APIエンドポイント
   - Bearer認証（DEEPBIZ_API_KEY）

5. **管理画面**
   - テストページ実装（`/admin/test_company_analysis`）
   - Bootstrap 5 ベースのモダンUI
   - リアルタイム分析結果表示

6. **キャッシュ管理**
   - `scripts/cleanup_company_cache.py` 実装
   - 期限切れキャッシュ自動削除
   - cron定期実行対応

### VPSデプロイフェーズ（1月4日）

#### 実施内容
1. **VPS環境準備**
   - Git管理移行（SCPからgit pullへ）
   - Python venv再構築
   - API鍵設定（GOOGLE_MAPS + GEMINI）

2. **SSH認証強化**
   - パスワード認証 → SSH鍵認証
   - ED25519鍵ペア生成
   - ~/.ssh/config設定

3. **デプロイ実行**
   - コード同期（git pull）
   - Gunicorn再起動
   - 動作確認

4. **トラブルシューティング**
   - WebScraperメソッド名修正
   - UI可視性改善
   - コスト表示修正
   - データベース復旧（git reset事故からのリカバリー）

### Phase 2 成果（1月4日時点）

#### 機能
- ✅ Web自動スクレイピング（requests + Seleniumフォールバック）
- ✅ Gemini 2.5 Flash-Lite解析（0.12円/社）
- ✅ 90日間キャッシュ（再利用時0円）
- ✅ RESTful API（Bearer認証）
- ✅ 管理画面GUIテストページ
- ✅ 自動キャッシュクリーンアップ

#### VPS本番環境
- ✅ Git管理有効化
- ✅ SSH鍵認証
- ✅ Phase 2機能稼働中
- ✅ http://133.167.116.58/admin/test_company_analysis

#### コスト実績
- 初回解析: 0.12円/社
- キャッシュヒット時: 0円
- 90日間で実質コストほぼ0円

### データベース状態（1月4日時点）

```
Salon テーブル: 1,905レコード（変更なし）
CompanyAnalysis テーブル: 新規作成
  - テスト解析データ数件保存済み
  - 本格運用は Phase 3 以降
```

### 関連ドキュメント
- [COMPANY_ANALYSIS_IMPLEMENTATION.md](COMPANY_ANALYSIS_IMPLEMENTATION.md) - 実装詳細
- [docs/COMPANY_ANALYSIS_API.md](docs/COMPANY_ANALYSIS_API.md) - API仕様
- [docs/COMPANY_ANALYSIS_INTEGRATION.md](docs/COMPANY_ANALYSIS_INTEGRATION.md) - 統合ガイド

---

## Phase 3: HPB肉付け（計画中）

### 目的
Hot Pepper Beauty（HPB）情報を追加して、より詳細なビジネスプロフィールを提供

### 予定される実装内容

#### Step 1: HPB URL取得
- 店舗名+住所でHPB検索
- HPB URLをSalonテーブルに保存

#### Step 2: HPB詳細情報スクレイピング
- クーポン情報
- スタッフ情報
- メニュー・料金
- 営業時間・定休日
- 詳細な口コミ

#### Step 3: データ統合
- Google Maps情報 + AI分析 + HPB情報
- 重複排除・データクレンジング
- 充実したビジネスプロフィール生成

### 期待される成果
- より詳細な店舗情報
- クーポン・求人情報の提供
- ユーザー体験の向上
- SEO効果の増大

### 技術的課題
- HPB側のBot検出回避
- データ統合ロジックの設計
- スクレイピング速度とコストのバランス

### 関連ドキュメント
- [docs/HPB_SCRAPING_GUIDE.md](docs/HPB_SCRAPING_GUIDE.md) - HPBスクレイピング技術ガイド

---

## Phase 4: TheSide連携（将来計画）

### 目的
営業支援プラットフォーム「TheSide」との連携

### 予定される機能
- DeepBizデータのTheSide側での活用
- 営業リスト自動生成
- 企業分析データの相互連携

### 関連ドキュメント
- [docs/DeepBiz_TheSide_AI_Cost_Integration.md](docs/DeepBiz_TheSide_AI_Cost_Integration.md)

---

## 技術スタック推移

### Phase 0-1
- Flask 3.1.2
- SQLite（salon_data.db）
- Selenium + BeautifulSoup
- Google Maps API

### Phase 2追加
- Gemini 2.5 Flash-Lite
- services/web_scraper.py
- services/gemini_analyzer.py
- CompanyAnalysisモデル
- RESTful API（/api/v1/companies）

### Phase 3予定
- Hot Pepper Beauty連携
- データ統合ロジック
- 拡張データモデル

---

## データ推移

```
Phase 0: 1,905件（基礎情報のみ）
    ↓
Phase 1: 1,905件（Google Maps情報追加）
  Place ID: 90.4%
  CID: 79.4%
  Website: 91.8%
  問い合わせ: 40.0%
    ↓
Phase 2: 1,905件（AI解析機能追加）
  CompanyAnalysis: 随時生成（90日キャッシュ）
    ↓
Phase 3: 予定（HPB情報追加）
  クーポン・求人・詳細情報
```

---

## 今後の展開

1. **Phase 3実装** - HPB情報統合（次のステップ）
2. **多業種展開** - 飲食店・宿泊施設への拡大
3. **TheSide連携** - 営業支援機能との統合
4. **SEO強化** - コンテンツマーケティング
5. **API公開** - 外部サービスとの連携

---

## トラブル事例と対策

### データベース消失事故（2026年1月4日）

#### 発生内容
- VPSで `git reset --hard origin/main` 実行
- 本番データベース（1,905件）が空のdev版で上書き

#### 原因
- instance/salon_data.db がGit追跡対象だった
- .gitignoreルールが機能していなかった

#### 対策
1. ~/backup/から最新バックアップ復元（1.2MB版）
2. `git rm --cached instance/salon_data.db` でGit追跡解除
3. .gitignore再確認・コミット
4. VPS上のデータ完全復旧確認

#### 教訓
- **データベースは絶対にGit管理しない**
- **本番環境では事前バックアップ必須**
- **git reset --hard は慎重に**

---

## 参考リンク

- **VPS**: http://133.167.116.58
- **管理画面**: http://133.167.116.58/admin
- **AI分析テスト**: http://133.167.116.58/admin/test_company_analysis
- **Git Repository**: https://github.com/shintarospec/deepbiz
