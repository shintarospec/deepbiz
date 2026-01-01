#!/bin/bash
# VPS復元スクリプト
# 使い方: bash restore_backup.sh [バックアップディレクトリパス]

set -e

if [ -z "$1" ]; then
    # 引数がない場合は最新のバックアップを使用
    if [ -f ~/LAST_BACKUP_PATH.txt ]; then
        BACKUP_DIR=$(cat ~/LAST_BACKUP_PATH.txt)
        echo "最新のバックアップを使用します: $BACKUP_DIR"
    else
        echo "エラー: バックアップディレクトリを指定してください"
        echo "使い方: bash $0 [バックアップディレクトリパス]"
        exit 1
    fi
else
    BACKUP_DIR=$1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "エラー: バックアップディレクトリが見つかりません: $BACKUP_DIR"
    exit 1
fi

echo "=========================================="
echo "VPS復元スクリプト"
echo "=========================================="
echo ""
echo "復元元: $BACKUP_DIR"
echo ""
read -p "本当に復元しますか？ (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "キャンセルしました"
    exit 0
fi

cd /var/www/salon_app

# アプリケーション停止
echo ""
echo "アプリケーションを停止中..."
pkill -f gunicorn || true
sleep 2

# ファイル復元
echo ""
echo "ファイルを復元中..."
cp -v $BACKUP_DIR/*.py ./ 2>/dev/null || true
cp -v $BACKUP_DIR/requirements.txt ./
cp -rv $BACKUP_DIR/templates/* templates/
cp -rv $BACKUP_DIR/static/* static/

# データベース復元
echo ""
read -p "データベースも復元しますか？ (yes/no): " DB_CONFIRM

if [ "$DB_CONFIRM" = "yes" ]; then
    echo "データベースを復元中..."
    cp -v $BACKUP_DIR/instance/*.db instance/
    chmod 664 instance/*.db
    chown ubuntu:www-data instance/*.db
else
    echo "データベースはスキップしました"
fi

# 権限修正
echo ""
echo "権限を修正中..."
chmod +x *.py
chmod 664 instance/*.db 2>/dev/null || true

# アプリケーション再起動
echo ""
echo "アプリケーションを再起動中..."
source venv/bin/activate
nohup gunicorn --workers 3 --bind unix:salon_app.sock -m 007 app:app > logs/gunicorn.log 2>&1 &

sleep 3

# 検証
echo ""
echo "=========================================="
echo "復元完了！"
echo "=========================================="
echo ""
echo "プロセス確認:"
ps aux | grep gunicorn | grep -v grep

echo ""
echo "ファイル確認:"
ls -lh app.py get_all_*.py 2>/dev/null | head -5

if [ "$DB_CONFIRM" = "yes" ]; then
    echo ""
    echo "データベース確認:"
    sqlite3 instance/salon_data.db "SELECT COUNT(*) as salon_count FROM Salon;" 2>/dev/null || echo "確認できません"
fi

echo ""
echo "=========================================="
echo "ブラウザで動作確認してください:"
echo "  http://133.167.116.58/search"
echo "=========================================="
