#!/bin/bash
# VPS上の完全バックアップスクリプト
# デプロイ前に必ず実行してください

set -e  # エラーで停止

echo "=========================================="
echo "VPS完全バックアップスクリプト"
echo "=========================================="
echo ""

# バックアップディレクトリ作成
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups/pre-refactor-${TIMESTAMP}

echo "バックアップ先: $BACKUP_DIR"
mkdir -p $BACKUP_DIR

cd /var/www/salon_app

# ファイルバックアップ
echo "ファイルをバックアップ中..."
cp -v *.py $BACKUP_DIR/ 2>/dev/null || true
cp -v requirements.txt $BACKUP_DIR/
cp -rv templates/ $BACKUP_DIR/
cp -rv static/ $BACKUP_DIR/
cp -rv migrations/ $BACKUP_DIR/ 2>/dev/null || true

# データベースバックアップ
echo ""
echo "データベースをバックアップ中..."
mkdir -p $BACKUP_DIR/instance
cp -v instance/*.db $BACKUP_DIR/instance/

# プロセス情報保存
echo ""
echo "プロセス情報を保存中..."
ps aux | grep gunicorn > $BACKUP_DIR/gunicorn_processes.txt || true
ss -tlnp | grep -E "(80|443|unix)" > $BACKUP_DIR/ports.txt || true

# バックアップパスを記録
echo $BACKUP_DIR > ~/LAST_BACKUP_PATH.txt

# バックアップ検証
echo ""
echo "=========================================="
echo "バックアップ完了！"
echo "=========================================="
echo ""
echo "バックアップパス: $BACKUP_DIR"
echo ""
echo "バックアップ内容:"
ls -lh $BACKUP_DIR/
echo ""
echo "バックアップサイズ:"
du -sh $BACKUP_DIR/
echo ""
echo "データベース確認:"
sqlite3 $BACKUP_DIR/instance/salon_data.db "SELECT COUNT(*) as salon_count FROM Salon;" 2>/dev/null || echo "salon_data.db: 確認できません"
sqlite3 $BACKUP_DIR/instance/scraping_data.db "SELECT COUNT(*) as area_count FROM Area;" 2>/dev/null || echo "scraping_data.db: 確認できません"
echo ""
echo "=========================================="
echo "このパスをメモしてください:"
echo "  $BACKUP_DIR"
echo "=========================================="
echo ""
echo "復元が必要な場合は以下を実行:"
echo "  bash ~/restore_backup.sh $BACKUP_DIR"
echo ""
