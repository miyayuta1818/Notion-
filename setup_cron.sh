#!/bin/bash
# 診療カレンダー Notion自動更新 - cron設定スクリプト

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/notion_auto_update.py"

echo "🏥 診療カレンダー Notion自動更新 - cron設定"
echo "=============================================="

# Pythonスクリプトの存在確認
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ エラー: notion_auto_update.py が見つかりません"
    echo "   パス: $PYTHON_SCRIPT"
    exit 1
fi

# 設定ファイルの存在確認
CONFIG_FILE="$SCRIPT_DIR/notion_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  警告: notion_config.json が見つかりません"
    echo "   まず setup_notion.py を実行して設定を行ってください"
    echo ""
    echo "   実行コマンド:"
    echo "   python3 setup_notion.py"
    exit 1
fi

echo "📋 現在のcron設定を表示します:"
echo "----------------------------------------"
crontab -l 2>/dev/null || echo "現在cronジョブは設定されていません"
echo ""

echo "⏰ 実行スケジュールを選択してください:"
echo "1) 毎週月曜日 午前3時 (推奨)"
echo "2) 毎週日曜日 午後11時"
echo "3) 毎週火曜日 午前2時"
echo "4) カスタム設定"
echo "5) cron設定を削除"
echo ""

read -p "選択してください (1-5): " choice

case $choice in
    1)
        CRON_TIME="0 3 * * 1"
        DESCRIPTION="毎週月曜日 午前3時"
        ;;
    2)
        CRON_TIME="0 23 * * 0"
        DESCRIPTION="毎週日曜日 午後11時"
        ;;
    3)
        CRON_TIME="0 2 * * 2"
        DESCRIPTION="毎週火曜日 午前2時"
        ;;
    4)
        echo ""
        echo "📝 cronの設定方法:"
        echo "   分 時 日 月 曜日"
        echo "   0-59 0-23 1-31 1-12 0-6 (0=日曜日)"
        echo ""
        read -p "分 (0-59): " minute
        read -p "時 (0-23): " hour
        read -p "曜日 (0=日曜日, 1=月曜日, ..., 6=土曜日): " weekday
        
        CRON_TIME="$minute $hour * * $weekday"
        DESCRIPTION="カスタム設定 ($hour:$minute, 曜日:$weekday)"
        ;;
    5)
        echo "🗑️  cron設定を削除しますか？"
        read -p "削除しますか？ (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            crontab -r
            echo "✅ cron設定を削除しました"
        else
            echo "キャンセルしました"
        fi
        exit 0
        ;;
    *)
        echo "❌ 無効な選択です"
        exit 1
        ;;
esac

# cronジョブを作成
CRON_JOB="$CRON_TIME cd $SCRIPT_DIR && python3 $PYTHON_SCRIPT >> $SCRIPT_DIR/cron.log 2>&1"

echo ""
echo "🔧 以下のcronジョブを設定します:"
echo "   時間: $DESCRIPTION"
echo "   コマンド: $CRON_JOB"
echo ""

read -p "この設定でcronジョブを作成しますか？ (Y/n): " confirm

if [[ $confirm =~ ^[Nn]$ ]]; then
    echo "キャンセルしました"
    exit 0
fi

# 既存のcronジョブを取得
EXISTING_CRON=$(crontab -l 2>/dev/null)

# 同じスクリプトの既存ジョブを削除
if [ -n "$EXISTING_CRON" ]; then
    EXISTING_CRON=$(echo "$EXISTING_CRON" | grep -v "$PYTHON_SCRIPT")
fi

# 新しいcronジョブを追加
if [ -n "$EXISTING_CRON" ]; then
    echo "$EXISTING_CRON" | { cat; echo "$CRON_JOB"; } | crontab -
else
    echo "$CRON_JOB" | crontab -
fi

if [ $? -eq 0 ]; then
    echo "✅ cronジョブが正常に設定されました"
    echo ""
    echo "📋 設定内容:"
    echo "   実行時間: $DESCRIPTION"
    echo "   ログファイル: $SCRIPT_DIR/cron.log"
    echo ""
    echo "🔍 設定確認:"
    echo "   crontab -l"
    echo ""
    echo "🧪 テスト実行:"
    echo "   python3 $PYTHON_SCRIPT"
    echo ""
    echo "📊 ログ確認:"
    echo "   tail -f $SCRIPT_DIR/cron.log"
    echo "   tail -f $SCRIPT_DIR/notion_update.log"
else
    echo "❌ cronジョブの設定に失敗しました"
    exit 1
fi
