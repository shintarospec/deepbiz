# VPSへのデプロイ手順書

## ⚠️ 注意事項

**必ずデータベースのバックアップを取ってから実行してください！**

## 1. データベースバックアップ

```bash
# VPSにSSHログイン
ssh ubuntu@133.167.116.58

# バックアップディレクトリ作成
mkdir -p ~/backups/$(date +%Y%m%d)

# データベースをバックアップ
cd /var/www/salon_app
cp instance/salon_data.db ~/backups/$(date +%Y%m%d)/
cp instance/scraping_data.db ~/backups/$(date +%Y%m%d)/

# バックアップ確認
ls -lh ~/backups/$(date +%Y%m%d)/
```

## 2. 現在のアプリケーションを停止

```bash
# Gunicornプロセスを停止
sudo systemctl stop gunicorn
# または
pkill -f gunicorn
```

## 3. コードの更新

```bash
cd /var/www/salon_app

# Gitで最新版を取得
git fetch origin
git pull origin main

# 権限を確認
chmod +x scripts/*.py
```

## 4. データベースのクリーンアップ（オプション）

**警告**: このステップは不可逆です。必ずバックアップを確認してから実行してください。

```bash
cd /var/www/salon_app

# 仮想環境を有効化
source venv/bin/activate

# クリーンアップスクリプト実行
python scripts/cleanup_database.py

# プロンプトに対して:
# 1. "yes" と入力して続行
# 2. 美容クリニック以外も削除するか選択（"yes" または "no"）
```

実行内容:
- 東京都以外のエリアデータを削除
- 23区以外のエリアデータを削除
- 既存のスクレイピングタスクを削除
- オプション: 美容クリニック以外のサロンデータを削除

## 5. 新しいタスクを生成

```bash
cd /var/www/salon_app
source venv/bin/activate

# 23区×美容クリニックのタスクを生成
python scripts/generate_simple_tasks.py

# 既存タスク削除の確認が出たら "yes" と入力
```

結果: 23件のGoogle Mapタスクが生成されます（各区1タスク）

## 6. アプリケーションの再起動

```bash
# Gunicornを再起動
cd /var/www/salon_app
source venv/bin/activate
gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app &

# または systemd を使用している場合
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

## 7. 動作確認

```bash
# ログを確認
tail -f /var/www/salon_app/logs/app.log

# プロセス確認
ps aux | grep gunicorn

# Nginxのステータス確認
sudo systemctl status nginx
```

ブラウザでアクセスして動作確認:
- http://133.167.116.58/search

## 8. スクレイピングタスクの実行

```bash
cd /var/www/salon_app
source venv/bin/activate

# 管理画面からタスクを実行するか、手動で実行
python run_gmap_scraper.py <task_id>
```

## トラブルシューティング

### アプリケーションが起動しない

```bash
# ログを確認
tail -n 50 /var/www/salon_app/logs/app.log

# Pythonエラーを確認
cd /var/www/salon_app
source venv/bin/activate
python -c "from app import app; print('OK')"
```

### データベースエラー

```bash
# バックアップから復元
cp ~/backups/YYYYMMDD/salon_data.db /var/www/salon_app/instance/
cp ~/backups/YYYYMMDD/scraping_data.db /var/www/salon_app/instance/

# 権限を修正
chmod 664 /var/www/salon_app/instance/*.db
chown ubuntu:www-data /var/www/salon_app/instance/*.db
```

### 元に戻す場合

```bash
cd /var/www/salon_app
git reset --hard HEAD~1
cp ~/backups/YYYYMMDD/*.db instance/
sudo systemctl restart gunicorn
```

## 統計情報

### 変更前
- エリアデータ: 160,275件（全国47都道府県）
- カテゴリ: 6種類
- 想定タスク数: 約960,000件

### 変更後
- エリアデータ: 約3,524件（東京23区のみ）
- カテゴリ: 1種類（美容クリニック）
- タスク数: 23件

**削減率: 約99.998%**

## 次のステップ

1. 23区の美容クリニックデータを収集
2. HPB詳細情報を更新
3. レビュー情報を収集
4. UI/UXの改善
