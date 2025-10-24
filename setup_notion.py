#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion自動更新セットアップスクリプト
初回設定をガイドします
"""

import json
import os
import sys

def setup_notion_config():
    """Notion設定ファイルを作成"""
    print("🔧 Notion自動更新のセットアップを開始します")
    print("=" * 50)
    
    # 設定ファイルのパス
    config_file = os.path.join(os.path.dirname(__file__), 'notion_config.json')
    
    if os.path.exists(config_file):
        print("⚠️  設定ファイルが既に存在します")
        overwrite = input("上書きしますか？ (y/N): ").lower()
        if overwrite != 'y':
            print("セットアップをキャンセルしました")
            return False
    
    print("\n📋 以下の手順でNotion APIの設定を行ってください：")
    print()
    print("1. Notionインテグレーションの作成")
    print("   - https://www.notion.so/my-integrations にアクセス")
    print("   - 「新しいインテグレーション」をクリック")
    print("   - 名前を入力（例：診療カレンダー自動更新）")
    print("   - 「送信」をクリック")
    print("   - 「内部トークン」をコピー")
    print()
    
    notion_token = input("🔑 Notion内部トークンを入力してください: ").strip()
    
    print("\n2. Notionページの設定")
    print("   - 更新したいNotionページを開く")
    print("   - ページのURLをコピー")
    print("   - URLの最後の部分がページIDです")
    print("   - 例: ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("   - ページID: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print()
    
    page_id = input("📄 NotionページIDを入力してください: ").strip()
    
    print("\n3. ページへのアクセス権付与")
    print("   - 更新対象のNotionページを開く")
    print("   - 右上の「共有」をクリック")
    print("   - 作成したインテグレーションを招待")
    print("   - 「編集」権限を付与")
    print()
    
    input("設定が完了したらEnterキーを押してください...")
    
    # 設定ファイルを作成
    config = {
        "notion_token": notion_token,
        "page_id": page_id,
        "update_schedule": "weekly",
        "log_level": "INFO"
    }
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("\n✅ 設定ファイルが作成されました")
        print(f"📁 ファイル: {config_file}")
        
        # テスト実行の提案
        print("\n🧪 設定をテストしますか？")
        test_run = input("テスト実行しますか？ (Y/n): ").lower()
        
        if test_run != 'n':
            print("\n🔄 テスト実行中...")
            try:
                from notion_auto_update import NotionCalendarUpdater
                
                updater = NotionCalendarUpdater(notion_token, page_id)
                success = updater.run_update()
                
                if success:
                    print("✅ テスト実行が成功しました！")
                    print("Notionページが更新されているか確認してください")
                else:
                    print("❌ テスト実行に失敗しました")
                    print("ログファイル notion_update.log を確認してください")
                    
            except Exception as e:
                print(f"❌ テスト実行エラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 設定ファイル作成エラー: {e}")
        return False

def create_cron_setup():
    """cron設定のガイド"""
    print("\n⏰ 週一回の自動実行設定")
    print("=" * 50)
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'notion_auto_update.py'))
    
    print("以下のコマンドでcronジョブを設定できます：")
    print()
    print("1. crontabを編集:")
    print("   crontab -e")
    print()
    print("2. 以下の行を追加（毎週月曜日 午前3時に実行）:")
    print(f"   0 3 * * 1 cd {os.path.dirname(script_path)} && python3 {script_path}")
    print()
    print("3. または、毎週日曜日 午後11時に実行:")
    print(f"   0 23 * * 0 cd {os.path.dirname(script_path)} && python3 {script_path}")
    print()
    print("📝 cronの設定例:")
    print("   # 分 時 日 月 曜日 コマンド")
    print("   0 3 * * 1  # 毎週月曜日 3:00")
    print("   0 23 * * 0 # 毎週日曜日 23:00")
    print()
    print("💡 ヒント:")
    print("   - 曜日: 0=日曜日, 1=月曜日, 2=火曜日, ...")
    print("   - 時間は24時間形式")
    print("   - 設定後は 'crontab -l' で確認できます")

def main():
    """メイン処理"""
    print("🏥 診療カレンダー Notion自動更新セットアップ")
    print("=" * 50)
    
    # Notion設定
    if setup_notion_config():
        print("\n🎉 セットアップが完了しました！")
        
        # cron設定のガイド
        create_cron_setup()
        
        print("\n📚 次のステップ:")
        print("1. cronジョブを設定して週一回の自動実行を有効にする")
        print("2. ログファイル notion_update.log で動作を確認する")
        print("3. 必要に応じて実行時間を調整する")
        
    else:
        print("\n❌ セットアップに失敗しました")
        print("手動で設定ファイルを作成してください")

if __name__ == "__main__":
    main()
