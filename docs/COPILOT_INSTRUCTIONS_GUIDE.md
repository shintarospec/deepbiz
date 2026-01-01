# GitHub Copilot Instructions - 導入ガイド

**作成日:** 2025年12月23日  
**対象:** DeepBizプロジェクト関係者  
**目的:** AI開発アシスタントの効果的な活用

---

## 📌 概要

### `.copilot-instructions.md` とは？

GitHub Copilotや他のAI開発アシスタントに対して、**プロジェクト固有のルール・知識・制約**を伝えるための指示書です。

#### 人間用ドキュメントとの違い

| 項目 | 人間用ドキュメント | AI用指示書 |
|------|------------------|-----------|
| **ファイル例** | `SPECIFICATION.md`, `README.md` | `.copilot-instructions.md` |
| **読者** | 開発者、PM、関係者 | AI（GitHub Copilot等） |
| **内容** | 仕様、設計、背景、理由 | コーディングルール、パターン、制約 |
| **形式** | 説明的・包括的 | 指示的・実践的 |
| **更新頻度** | プロジェクト計画変更時 | コーディング規約変更時 |

---

## 🎯 なぜ必要なのか？

### 従来の問題点

AI開発アシスタントは**一般的なベストプラクティス**に基づいてコードを提案しますが、プロジェクト固有の事情を考慮できません：

**例1: API課金の問題**
```python
# ❌ AIが提案する一般的なコード
result = gmaps.place(place_id=place_id)  # 💸 課金が発生！

# ✅ 本プロジェクトでは避けるべき
# → スクレイピング経由で取得
```

**例2: データベース操作のミス**
```python
# ❌ Flaskの一般的なパターン（本プロジェクトではエラー）
salons = Salon.query.all()  # RuntimeError!

# ✅ 本プロジェクトで必須のパターン
with app.app_context():
    salons = Salon.query.all()
```

**例3: ブラウザの安定性**
```python
# ❌ 一般的なSelenium（検出されやすい）
driver = webdriver.Chrome()

# ✅ 本プロジェクトのパターン
driver = get_stealth_driver()  # undetected-chromedriver
```

### 解決策

`.copilot-instructions.md`により、AIが**プロジェクト固有のルール**を学習し、適切なコードを提案するようになります。

---

## 🚀 本プロジェクトでの運用方法

### 1. 配置場所

```
/workspaces/deepbiz/
  ├── .copilot-instructions.md  ← ここに配置（ルート）
  ├── app.py
  ├── models.py
  └── scripts/
```

### 2. 自動適用の仕組み

#### GitHub Copilot Chat
- ✅ **ワークスペースのルートに配置** → 自動的に読み込まれる
- ✅ **新しい会話から適用** → 次回のチャットセッションで有効
- ✅ **コード補完にも反映** → インラインの提案が改善

#### 他のAIツール（ChatGPT、Claude等）
- ⚠️ 自動適用されない → 手動でファイル内容を共有する必要あり

### 3. 効果の確認方法

**テスト例:**
```
Q: "Place IDからCIDを取得するコードを書いて"

【適用前】
→ Google Maps APIを使った実装を提案

【適用後】
→ Seleniumでスクレイピングする実装を提案
→ リトライロジック付き
→ ブラウザ再起動処理付き
```

---

## 📝 含まれている内容

### 1. プロジェクト固有のアーキテクチャ
- 技術スタック（Flask, SQLAlchemy, Selenium）
- インフラ構成（VPS、データベース構成）
- デプロイパス

### 2. データモデル
```python
# Salonモデルの構造とフィールドの意味
class Salon(db.Model):
    place_id: str  # Google Maps Place ID（ユニーク）
    cid: str       # Google Maps CID（ユニーク）
    # ... 他のフィールド
```

### 3. コーディング規約
- **ファイル命名:** `動詞_目的語.py` (例: `enrich_cid_from_embed_v2.py`)
- **関数命名:** `get_*()`, `enrich_*()`, `run_*()`
- **データベース操作:** 必ず`app.app_context()`を使用

### 4. 重要な制約
1. **API課金回避** - Google Maps APIの使用を最小限に
2. **Bot検出回避** - undetected-chromedriverを使用
3. **ブラウザ安定性** - 15件ごとに再起動

### 5. 開発ワークフロー
```bash
1. ローカルで開発
2. --testフラグで10件テスト
3. VPSにアップロード
4. VPSでテスト実行
5. 本番実行
```

### 6. よくあるコードパターン
- Place ID → CID変換
- リトライ処理
- 進捗表示
- エラーハンドリング

---

## 💼 期待される効果

### 開発効率の向上
- ⏱️ **コーディング時間 30-50%削減** - 正しいパターンを即座に提案
- 🐛 **バグ削減** - プロジェクト固有のミスを事前に防止
- 📚 **学習コスト削減** - 新メンバーが規約を覚える時間を短縮

### コード品質の向上
- ✅ **一貫性** - 全員が同じパターンでコーディング
- ✅ **ベストプラクティス** - プロジェクト固有の知見が蓄積
- ✅ **保守性** - 読みやすく理解しやすいコード

### 具体例

**Before（指示書なし）:**
```python
# 開発者Aが書いたコード
def get_cid(place_id):
    result = gmaps.place(place_id=place_id)  # 💸 課金
    return result['cid']

# 開発者Bが書いたコード
def fetch_cid(pid):
    url = f"https://maps.google.com/?place_id={pid}"  # 🐛 パターンが違う
    driver.get(url)
    # ...
```

**After（指示書あり）:**
```python
# 開発者A・Bともに同じパターン
def get_cid_from_place_id(place_id, driver):
    """Place IDからCIDを取得（標準パターン）"""
    url = f"https://www.google.com/maps/search/?api=1&query_place_id={place_id}"
    driver.get(url)
    time.sleep(5)  # JavaScriptロード待機
    
    # パターン1: URL内の16進数
    match = re.search(r'!1s0x[0-9a-f]+:0x([0-9a-f]+)', driver.current_url)
    if match:
        return str(int(match.group(1), 16))
    # ... リトライロジック
```

---

## 🔄 運用ルール

### 更新タイミング

以下の場合に`.copilot-instructions.md`を更新します：

1. **新しいコーディングパターンが確立** - 例: 新しいスクレイピング手法
2. **重要な制約が追加** - 例: 新しいAPIの使用禁止
3. **アーキテクチャ変更** - 例: データベース移行（SQLite→PostgreSQL）
4. **よくあるミスの発見** - 例: 頻出するバグパターン

### 更新プロセス

```bash
1. 人間用ドキュメント（SPECIFICATION.md等）を更新
2. .copilot-instructions.md に反映
3. チームに共有（Slack、GitHub等）
4. 次回の会話から新ルールが適用される
```

### バージョン管理

- ✅ Gitで管理（他のソースコードと同様）
- ✅ 変更履歴を記録
- ✅ Pull Requestでレビュー

---

## 📊 効果測定

### KPI例

| 指標 | 目標 | 測定方法 |
|-----|------|---------|
| コード品質 | エラー率 30%減 | GitHub Issues、バグレポート |
| 開発速度 | 実装時間 40%短縮 | タスク完了時間の比較 |
| 学習コスト | オンボーディング 50%短縮 | 新メンバーのセットアップ時間 |
| 規約遵守率 | 100% | コードレビュー時のチェック |

---

## 🔗 関連ドキュメント

### 人間用ドキュメント
- **SPECIFICATION.md** - プロジェクト仕様書（Why & What）
- **README.md** - システム概要とセットアップ
- **docs/PROJECT_PLAN.md** - プロジェクト計画

### AI用ドキュメント
- **.copilot-instructions.md** - コーディングルール（How）

### 併用することで最大効果
- **人間** → 仕様書を読んで「なぜ」を理解
- **AI** → 指示書を読んで「どのように」コーディングするか理解

---

## ❓ FAQ

### Q1: 既存のコードも修正すべき？
**A:** いいえ。`.copilot-instructions.md`は**今後のコード**に適用されます。既存コードは動作しているなら修正不要です。

### Q2: ChatGPTで使いたい場合は？
**A:** ファイルの内容をコピーしてプロンプトに含めてください：
```
以下のプロジェクトルールに従ってコードを書いてください：
[.copilot-instructions.mdの内容を貼り付け]
```

### Q3: チーム全員が設定する必要は？
**A:** はい。各自のローカル環境で`.copilot-instructions.md`があれば自動適用されます。Gitで管理しているのでclone時に自動取得されます。

### Q4: 適用されているか確認するには？
**A:** GitHub Copilot Chatで「データベースを操作するコードを書いて」と聞いて、`app.app_context()`付きのコードが提案されるか確認してください。

---

## 🎓 まとめ

### `.copilot-instructions.md` の役割

```
┌─────────────────────────────────────┐
│  人間用ドキュメント                   │
│  (SPECIFICATION.md等)               │
│  → Why（なぜ）& What（何を）         │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  .copilot-instructions.md           │
│  → How（どのように）                 │
│  → プロジェクト固有のルール          │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  AI開発アシスタント                  │
│  (GitHub Copilot)                   │
│  → 適切なコードを自動生成            │
└─────────────────────────────────────┘
```

### 成功の鍵

1. ✅ **継続的な更新** - プロジェクトの進化に合わせて改善
2. ✅ **チーム共有** - 全員が同じルールでコーディング
3. ✅ **効果測定** - KPIでメリットを可視化
4. ✅ **フィードバック** - AIの提案が不適切な場合は指示書を改善

---

**質問・フィードバック:** プロジェクトSlackチャンネルまで
