# ロールバック（復元）ガイド

## デプロイ後の復元可能性: ✅ 完全に可能

このガイドでは、リファクタリング版をデプロイした後に、元の状態に戻す方法を説明します。

---

## 復元の準備（デプロイ前に必ず実行）

### 1. VPS上で完全バックアップを作成

```bash
# VPSにSSHログイン
ssh ubuntu@133.167.116.58

# バックアップディレクトリ作成
BACKUP_DIR=~/backups/pre-refactor-$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

cd /var/www/salon_app

# ファイルをバックアップ
cp -r *.py $BACKUP_DIR/
cp -r templates/ $BACKUP_DIR/
cp -r static/ $BACKUP_DIR/
cp -r instance/ $BACKUP_DIR/
cp requirements.txt $BACKUP_DIR/

# バックアップ確認
ls -lh $BACKUP_DIR/
du -sh $BACKUP_DIR/

# バックアップパスを記録
echo $BACKUP_DIR > ~/LAST_BACKUP_PATH.txt
cat ~/LAST_BACKUP_PATH.txt
```

**このパスを必ずメモしてください！**

### 2. データベースのバックアップ

```bash
cd /var/www/salon_app

# SQLiteデータベースをバックアップ
cp instance/salon_data.db $BACKUP_DIR/
cp instance/scraping_data.db $BACKUP_DIR/

# バックアップの整合性確認
sqlite3 $BACKUP_DIR/salon_data.db "SELECT COUNT(*) FROM Salon;"
sqlite3 $BACKUP_DIR/scraping_data.db "SELECT COUNT(*) FROM Area;"
```

### 3. 現在のプロセス情報を記録

```bash
# Gunicornプロセス情報を保存
ps aux | grep gunicorn > $BACKUP_DIR/gunicorn_processes.txt

# 現在のポート使用状況
ss -tlnp | grep -E "(80|443|unix)" > $BACKUP_DIR/ports.txt
```

---

## 復元方法（3つの方法）

### 方法A: バックアップから直接復元（最速・推奨）

```bash
# 1. アプリケーションを停止
ssh ubuntu@133.167.116.58
cd /var/www/salon_app
pkill -f gunicorn

# 2. バックアップパスを確認
BACKUP_DIR=$(cat ~/LAST_BACKUP_PATH.txt)
echo "復元元: $BACKUP_DIR"

# 3. ファイルを復元
cd /var/www/salon_app
cp $BACKUP_DIR/*.py ./
cp -r $BACKUP_DIR/templates/* templates/
cp -r $BACKUP_DIR/static/* static/
cp $BACKUP_DIR/requirements.txt ./

# 4. データベースを復元（必要な場合）
cp $BACKUP_DIR/salon_data.db instance/
cp $BACKUP_DIR/scraping_data.db instance/

# 5. 権限を修正
chmod +x *.py
chmod 664 instance/*.db
chown ubuntu:www-data instance/*.db

# 6. アプリケーションを再起動
source venv/bin/activate
gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app &

# 7. 動作確認
sleep 3
ps aux | grep gunicorn
curl -I http://localhost/search
```

### 方法B: Gitリポジトリから復元（クリーン）

```bash
# 1. ローカルで元のバージョンを確認
cd /workspaces/deepbiz
git log --oneline
# f336df9 が元のバージョン

# 2. 元のバージョンをVPSにデプロイ
ssh ubuntu@133.167.116.58
cd /var/www/salon_app

# アプリケーション停止
pkill -f gunicorn

# Gitリポジトリを初期化（まだの場合）
git init
git remote add origin https://github.com/shintarospec/deepbiz.git

# 元のバージョンをチェックアウト
git fetch origin
git checkout f336df9  # 元のコミットID

# または特定のファイルだけ復元
git checkout origin/main -- app.py
git checkout origin/main -- get_all_*.py

# 依存関係を再インストール
source venv/bin/activate
pip install -r requirements.txt

# アプリケーション再起動
gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app &
```

### 方法C: 手動で個別ファイルを復元

特定のファイルだけ問題がある場合：

```bash
ssh ubuntu@133.167.116.58
BACKUP_DIR=$(cat ~/LAST_BACKUP_PATH.txt)
cd /var/www/salon_app

# 例: app.pyだけ復元
cp $BACKUP_DIR/app.py ./

# 例: スクレイパースクリプトを復元
cp $BACKUP_DIR/get_all_*.py ./

# アプリケーション再起動
pkill -f gunicorn
source venv/bin/activate
gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app &
```

---

## データベースだけを復元

新しいコードは使いつつ、データだけ元に戻したい場合：

```bash
ssh ubuntu@133.167.116.58
BACKUP_DIR=$(cat ~/LAST_BACKUP_PATH.txt)
cd /var/www/salon_app

# アプリケーション停止
pkill -f gunicorn

# データベースを復元
cp $BACKUP_DIR/salon_data.db instance/
cp $BACKUP_DIR/scraping_data.db instance/

# 権限修正
chmod 664 instance/*.db
chown ubuntu:www-data instance/*.db

# アプリケーション再起動
source venv/bin/activate
gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app &
```

---

## 復元の検証

復元後、以下を確認してください：

```bash
# 1. プロセス確認
ps aux | grep gunicorn

# 2. ファイル確認
cd /var/www/salon_app
ls -la app.py get_all_*.py

# 3. データベース確認
sqlite3 instance/salon_data.db "SELECT COUNT(*) FROM Salon;"
sqlite3 instance/scraping_data.db "SELECT COUNT(*) FROM Area;"

# 4. Web動作確認
curl -I http://133.167.116.58/search

# 5. ログ確認
tail -f logs/app.log
```

ブラウザで確認：
- http://133.167.116.58/search
- 検索機能が正常に動作するか
- サロン詳細ページが開けるか

---

## トラブルシューティング

### 問題: アプリケーションが起動しない

```bash
# ログを確認
tail -n 100 /var/www/salon_app/logs/app.log

# Pythonエラーを確認
cd /var/www/salon_app
source venv/bin/activate
python app.py  # エラーメッセージを確認
```

### 問題: データベースエラー

```bash
# データベースファイルの権限を確認
ls -la instance/*.db

# 権限を修正
chmod 664 instance/*.db
chown ubuntu:www-data instance/*.db
```

### 問題: 一部のページでエラー

特定のファイルだけ問題がある可能性：

```bash
BACKUP_DIR=$(cat ~/LAST_BACKUP_PATH.txt)
cd /var/www/salon_app

# 関連ファイルを個別に復元
cp $BACKUP_DIR/app.py ./
cp $BACKUP_DIR/models.py ./
cp -r $BACKUP_DIR/templates/* templates/

# 再起動
pkill -f gunicorn
source venv/bin/activate
gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app &
```

---

## バックアップの保持期間

```bash
# 古いバックアップの確認
ls -lh ~/backups/

# 30日以上古いバックアップを削除（必要に応じて）
find ~/backups/ -type d -mtime +30 -exec rm -rf {} \;
```

**推奨**: 少なくとも以下のバックアップは保持
- 最新の3つのバックアップ
- デプロイ前のバックアップ
- 重要な変更前のバックアップ

---

## 緊急時の連絡先情報

バックアップパスファイルの場所:
```
~/LAST_BACKUP_PATH.txt
```

バックアップディレクトリ:
```
~/backups/pre-refactor-YYYYMMDD_HHMMSS/
```

---

## まとめ

✅ **デプロイ前**: 必ずバックアップを作成
✅ **復元方法**: 3つの方法があり、どれでも完全復元可能
✅ **所要時間**: 5-10分で復元完了
✅ **データ保護**: データベースも完全に保護される
✅ **リスク**: ほぼゼロ（適切な手順を踏めば）

**結論: デプロイ後も100%復元可能です！**
