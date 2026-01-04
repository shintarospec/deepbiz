#!/bin/bash
#
# Salon → Biz 一括リネームスクリプト
# 全てのPythonファイルとテンプレートファイルを対象に置換
#

set -e

echo "================================"
echo "Salon → Biz 一括リネーム開始"
echo "================================"
echo ""

# 1. Pythonファイルの置換
echo "1. Pythonファイルの置換..."

# Salon → Biz (クラス名)
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -exec sed -i 's/class Salon(/class Biz(/g' {} \;
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -exec sed -i 's/from models import.*Salon/&/g' {} \;
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -exec sed -i 's/\bSalon\b/Biz/g' {} \;

# salon_categories → biz_categories
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -exec sed -i 's/salon_categories/biz_categories/g' {} \;

# salon_id → biz_id (カラム名)
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -exec sed -i 's/salon_id/biz_id/g' {} \;

# salon_data.db → biz_data.db
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -exec sed -i 's/salon_data\.db/biz_data.db/g' {} \;

echo "  ✓ Python ファイル完了"

# 2. テンプレートファイルの置換
echo "2. テンプレートファイルの置換..."

# /salon/ → /biz/ (URL)
find ./templates -name "*.html" -exec sed -i 's/\/salon\//\/biz\//g' {} \;

# salon. → biz. (オブジェクト参照)
find ./templates -name "*.html" -exec sed -i 's/\bsalon\./biz./g' {} \;

# salons → bizs (リスト変数)
find ./templates -name "*.html" -exec sed -i 's/\bsalons\b/bizs/g' {} \;

echo "  ✓ テンプレートファイル完了"

# 3. 確認
echo ""
echo "================================"
echo "置換完了！"
echo "================================"
echo ""
echo "以下のファイルが変更されました:"
git status --short

echo ""
echo "次のステップ:"
echo "  1. git diff で変更内容を確認"
echo "  2. python scripts/migrate_salon_to_biz.py でDBマイグレーション実行"
echo "  3. 動作テスト"
echo "  4. git commit"
