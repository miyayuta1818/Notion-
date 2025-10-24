# 診療カレンダー解析ツール

## 📋 概要
明石整形外科病院の診療担当医カレンダーを自動解析し、Notion用のテキスト形式で出力するPythonスクリプトです。

## 🎯 対象URL
https://www.myseikei.jp/information/

## 📁 ファイル構成
- `calendar_parser.py`: メインの解析スクリプト（手動実行用）
- `notion_auto_update.py`: Notion自動更新スクリプト（週一回自動実行用）
- `setup_notion.py`: Notion設定セットアップスクリプト
- `setup_cron.sh`: 週一回自動実行設定スクリプト
- `notion_config_template.json`: 設定ファイルテンプレート
- `result.txt`: 生成されたNotion用テキストファイル
- `README.md`: このファイル

## 🚀 使用方法

### 1. 手動実行（一回だけ実行）
```bash
cd 診療カレンダー解析
python calendar_parser.py
```

### 2. Notion自動更新設定（週一回自動実行）

#### ステップ1: Notion設定
```bash
python setup_notion.py
```
- Notionインテグレーションの作成
- ページIDの取得
- 設定ファイルの作成

#### ステップ2: 自動実行設定
```bash
./setup_cron.sh
```
- 週一回の実行スケジュール設定
- cronジョブの作成

## 📊 機能
- WebページからHTMLを自動取得
- カレンダーテーブルを解析
- 曜日を自動判定（日曜スタート対応）
- AM/PM担当医を正確に抽出
- Notion用フォーマットで出力
- **週一回の自動更新**
- **同じNotionドキュメントの更新**

## 📝 出力形式
```
🗓️ 2025年10月　担当医表

1日（水）
AM：院長
PM：大友医師

2日（木）
AM：記載なし
PM：記載なし
...
```

## 🔧 必要なライブラリ
- requests
- beautifulsoup4

インストール方法:
```bash
pip install requests beautifulsoup4
```

## 📅 対応カレンダー
- 2025年10月担当医表
- 2025年11月担当医表
- その他の月のカレンダーも自動対応

## ⚠️ 注意事項
- Webページの構造が変更された場合、スクリプトの修正が必要になる可能性があります
- インターネット接続が必要です
- Notion APIの認証情報が必要です
- 自動実行にはcronの設定が必要です

## 🔄 自動更新の仕組み
1. **週一回の自動実行**: cronジョブでスケジュール実行
2. **同じドキュメント更新**: 新しいドキュメントを作成せず、既存のページを更新
3. **ログ機能**: 実行ログとエラーログを記録
4. **更新日時表示**: Notionページに最終更新日時を表示

## 📊 ログファイル
- `notion_update.log`: 実行ログとエラーログ
- `cron.log`: cron実行時のログ

## 🛠️ トラブルシューティング
- 設定ファイル `notion_config.json` が正しく作成されているか確認
- Notionページにインテグレーションのアクセス権限があるか確認
- cronジョブが正しく設定されているか確認: `crontab -l`
- ログファイルでエラー内容を確認