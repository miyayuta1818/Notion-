#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
診療カレンダー Notion自動更新スクリプト
週一回の自動更新でNotionドキュメントを更新します
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notion_update.log'),
        logging.StreamHandler()
    ]
)

class NotionCalendarUpdater:
    def __init__(self, notion_token, page_id):
        """Notion API設定"""
        self.notion_token = notion_token
        self.page_id = page_id
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
    def get_calendar_data(self):
        """Webページからカレンダーデータを取得"""
        url = 'https://www.myseikei.jp/information/'
        
        try:
            response = requests.get(url)
            response.encoding = response.apparent_encoding
            html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            return soup
            
        except Exception as e:
            logging.error(f"Webページの取得に失敗しました: {e}")
            return None

    def extract_calendar_info(self, soup):
        """カレンダー情報を抽出"""
        calendars = []
        
        # カレンダーのタイトルを探す（h2タグで「担当医表」を含むもの）
        calendar_headers = soup.find_all('h2', string=re.compile(r'.*担当医表.*'))
        
        for header in calendar_headers:
            title = header.get_text(strip=True)
            logging.info(f"カレンダー発見: {title}")
            
            # タイトルの次のテーブルを取得
            table = header.find_next('table')
            if table:
                calendars.append({
                    'title': title,
                    'table': table
                })
        
        return calendars

    def parse_calendar_table(self, table):
        """カレンダーテーブルを解析"""
        # ヘッダー行から曜日を取得
        header_row = table.find('tr')
        if not header_row:
            return []
        
        weekday_headers = []
        for th in header_row.find_all(['th', 'td']):
            text = th.get_text(strip=True)
            if text and text not in ['', ' ']:
                weekday_headers.append(text)
        
        # データ行を取得
        data_rows = table.find_all('tr')[1:]  # ヘッダー行を除く
        calendar_data = []
        
        for row in data_rows:
            cells = row.find_all(['td', 'th'])
            
            for col_index, cell in enumerate(cells):
                if col_index >= len(weekday_headers):
                    continue
                    
                weekday = weekday_headers[col_index]
                
                # 日付を探す
                day_element = cell.find('div', class_='day')
                if not day_element:
                    continue
                    
                day_text = day_element.get_text(strip=True)
                if not day_text or not day_text.isdigit():
                    continue
                    
                day_number = int(day_text)
                
                # セル内のテキスト全体を取得
                cell_text = cell.get_text(strip=True)
                
                # AM/PMの担当医を抽出（改善版）
                am_doctors = []
                pm_doctors = []
                
                # 「終日」の記載をチェック
                if '終日' in cell_text:
                    # 終日の場合はAM/PM両方に同じ医師を設定
                    doctor_name = cell_text.replace('終日', '').strip()
                    if doctor_name:
                        # 複数医師の場合は分割
                        doctors = self.parse_multiple_doctors(doctor_name)
                        am_doctors.extend(doctors)
                        pm_doctors.extend(doctors)
                
                # AM/PMの両方がある場合
                elif 'AM' in cell_text and 'PM' in cell_text:
                    am_pos = cell_text.find('AM')
                    pm_pos = cell_text.find('PM')
                    
                    if am_pos < pm_pos:
                        am_text = cell_text[am_pos + 2:pm_pos].strip()
                        pm_text = cell_text[pm_pos + 2:].strip()
                    else:
                        pm_text = cell_text[pm_pos + 2:am_pos].strip()
                        am_text = cell_text[am_pos + 2:].strip()
                    
                    if am_text:
                        am_doctors.extend(self.parse_multiple_doctors(am_text))
                    if pm_text:
                        pm_doctors.extend(self.parse_multiple_doctors(pm_text))
                
                # AMのみの場合
                elif 'AM' in cell_text:
                    am_pos = cell_text.find('AM')
                    am_text = cell_text[am_pos + 2:].strip()
                    if am_text:
                        am_doctors.extend(self.parse_multiple_doctors(am_text))
                
                # PMのみの場合
                elif 'PM' in cell_text:
                    pm_pos = cell_text.find('PM')
                    pm_text = cell_text[pm_pos + 2:].strip()
                    if pm_text:
                        pm_doctors.extend(self.parse_multiple_doctors(pm_text))
                
                # AM/PMの記載がない場合（日付の後に直接医師名が書かれている場合）
                else:
                    day_pos = cell_text.find(str(day_number))
                    if day_pos != -1:
                        remaining_text = cell_text[day_pos + len(str(day_number)):].strip()
                        if remaining_text:
                            # 医師名として扱う（AM/PMの区別がない場合は終日として扱う）
                            doctors = self.parse_multiple_doctors(remaining_text)
                            am_doctors.extend(doctors)
                            pm_doctors.extend(doctors)
                
                # 重複を除去
                am_doctors = list(set(am_doctors))
                pm_doctors = list(set(pm_doctors))
                
                # 結果を格納
                calendar_data.append({
                    'day': day_number,
                    'weekday': weekday,
                    'am_doctors': am_doctors,
                    'pm_doctors': pm_doctors,
                    'raw_text': cell_text
                })
        
        return calendar_data

    def parse_multiple_doctors(self, doctor_text):
        """複数医師の記載を解析してリストに分割"""
        doctors = []
        
        # 複数医師のパターンを検出
        # 例: "院長宇佐見医師＊" -> ["院長", "宇佐見医師＊"]
        # 例: "院長、大友医師" -> ["院長", "大友医師"]
        # 例: "院長 大友医師" -> ["院長", "大友医師"]
        
        # カンマ区切りの場合
        if '、' in doctor_text or ',' in doctor_text:
            separator = '、' if '、' in doctor_text else ','
            doctors = [doc.strip() for doc in doctor_text.split(separator) if doc.strip()]
        
        # スペース区切りの場合（院長 宇佐見医師＊など）
        elif ' ' in doctor_text and any(keyword in doctor_text for keyword in ['院長', '医師', '＊']):
            parts = doctor_text.split()
            current_doctor = ""
            
            for part in parts:
                if part in ['院長']:
                    if current_doctor:
                        doctors.append(current_doctor.strip())
                    current_doctor = part
                elif '医師' in part or '＊' in part:
                    current_doctor += " " + part
                    doctors.append(current_doctor.strip())
                    current_doctor = ""
                else:
                    current_doctor += " " + part
            
            if current_doctor.strip():
                doctors.append(current_doctor.strip())
        
        # 単一医師の場合
        else:
            doctors = [doctor_text.strip()]
        
        # 空の要素を除去
        doctors = [doc for doc in doctors if doc]
        
        return doctors

    def format_calendar_for_notion(self, calendar_info):
        """Notion用フォーマットで整形"""
        output_lines = []
        
        for calendar in calendar_info:
            title = calendar['title']
            data = calendar['data']
            
            # タイトルを整形
            output_lines.append(f"🗓️ {title}")
            output_lines.append("")
            
            # 日付順にソート
            data.sort(key=lambda x: x['day'])
            
            # 各日付の情報を出力
            for day_info in data:
                day = day_info['day']
                weekday = day_info['weekday']
                am_doctors = day_info['am_doctors']
                pm_doctors = day_info['pm_doctors']
                
                output_lines.append(f"{day}日（{weekday}）")
                
                # AM担当医
                if am_doctors:
                    am_text = "、".join(am_doctors)
                    output_lines.append(f"AM：{am_text}")
                else:
                    output_lines.append("AM：記載なし")
                
                # PM担当医
                if pm_doctors:
                    pm_text = "、".join(pm_doctors)
                    output_lines.append(f"PM：{pm_text}")
                else:
                    output_lines.append("PM：記載なし")
                
                output_lines.append("")
        
        return "\n".join(output_lines)

    def get_page_blocks(self):
        """Notionページの既存ブロックを取得（ページネーション対応）"""
        url = f"https://api.notion.com/v1/blocks/{self.page_id}/children"
        all_blocks = []
        
        try:
            while url:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    blocks = data.get('results', [])
                    all_blocks.extend(blocks)
                    
                    # 次のページがあるかチェック
                    if data.get('has_more', False):
                        url = f"https://api.notion.com/v1/blocks/{self.page_id}/children?start_cursor={data['next_cursor']}"
                    else:
                        url = None
                else:
                    logging.error(f"ページブロック取得エラー: {response.status_code}")
                    break
            
            logging.info(f"取得したブロック数: {len(all_blocks)}")
            return all_blocks
            
        except Exception as e:
            logging.error(f"ページブロック取得エラー: {e}")
            return []

    def clear_page_content(self):
        """Notionページの内容を完全にクリア（質と速度を両立）"""
        logging.info("既存のページ内容を完全に削除中...")
        
        # ページの全ブロックを取得
        blocks = self.get_page_blocks()
        
        if not blocks:
            logging.info("削除するブロックがありません")
            return True
        
        logging.info(f"削除対象ブロック数: {len(blocks)}")
        
        # 段階的削除アプローチ
        max_retries = 3
        archived_count = 0
        
        for attempt in range(max_retries):
            logging.info(f"削除試行 {attempt + 1}/{max_retries}")
            
            # 現在のブロックを再取得（前回の削除で残ったもの）
            current_blocks = self.get_page_blocks()
            if not current_blocks:
                logging.info("すべてのブロックが削除されました")
                break
            
            logging.info(f"残りブロック数: {len(current_blocks)}")
            
            # バッチ削除（API制限を考慮）
            batch_size = 20  # 安全なバッチサイズ
            success_count = 0
            
            for i in range(0, len(current_blocks), batch_size):
                batch = current_blocks[i:i + batch_size]
                
                # バッチ内のブロックを並列削除
                import concurrent.futures
                import time
                
                def archive_block(block):
                    block_id = block['id']
                    archive_url = f"https://api.notion.com/v1/blocks/{block_id}"
                    
                    try:
                        response = requests.patch(
                            archive_url, 
                            headers=self.headers, 
                            json={"archived": True}
                        )
                        return response.status_code == 200, block_id
                    except Exception as e:
                        logging.error(f"ブロックアーカイブエラー: {e}, ブロックID: {block_id}")
                        return False, block_id
                
                # 並列処理でバッチ削除
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(archive_block, block) for block in batch]
                    
                    for future in concurrent.futures.as_completed(futures):
                        success, block_id = future.result()
                        if success:
                            success_count += 1
                
                logging.info(f"バッチ削除完了: {success_count}/{len(current_blocks)}")
                
                # API制限を考慮して待機
                time.sleep(0.3)
            
            archived_count += success_count
            
            # 削除が完了したかチェック
            remaining_blocks = self.get_page_blocks()
            if not remaining_blocks:
                logging.info(f"削除完了: 合計 {archived_count} ブロックを削除")
                break
            
            logging.info(f"削除後残りブロック数: {len(remaining_blocks)}")
            
            # 次の試行まで少し待機
            if attempt < max_retries - 1:
                time.sleep(1)
        
        # 最終確認
        final_blocks = self.get_page_blocks()
        if final_blocks:
            logging.warning(f"削除できなかったブロック数: {len(final_blocks)}")
            # 個別に削除を試行
            for block in final_blocks:
                try:
                    block_id = block['id']
                    archive_url = f"https://api.notion.com/v1/blocks/{block_id}"
                    response = requests.patch(
                        archive_url, 
                        headers=self.headers, 
                        json={"archived": True}
                    )
                    if response.status_code == 200:
                        logging.info(f"個別削除成功: {block_id}")
                    else:
                        logging.error(f"個別削除失敗: {block_id}, ステータス: {response.status_code}")
                except Exception as e:
                    logging.error(f"個別削除エラー: {e}")
        else:
            logging.info("✅ すべてのブロックが正常に削除されました")
        
        # 削除完了後の待機
        import time
        time.sleep(2)
        
        return True

    def update_page_content(self, content):
        """Notionページに新しいコンテンツを追加（バッチ処理対応）"""
        url = f"https://api.notion.com/v1/blocks/{self.page_id}/children"
        
        # コンテンツを行ごとに分割
        lines = content.split('\n')
        
        # Notionブロック形式に変換
        blocks = []
        for line in lines:
            if line.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line}
                        }]
                    }
                })
            else:
                # 空行の場合は改行ブロック
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": []
                    }
                })
        
        # 更新日時を追加（日本時間）
        import pytz
        jst = pytz.timezone('Asia/Tokyo')
        update_time = datetime.now(jst).strftime("%Y年%m月%d日 %H:%M 更新")
        blocks.insert(0, {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"🔄 {update_time}"}
                }]
            }
        })
        
        # Notion APIの制限（100ブロック）を考慮してバッチ処理
        batch_size = 95  # 安全マージンを考慮
        success_count = 0
        
        try:
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i:i + batch_size]
                
                response = requests.patch(
                    url, 
                    headers=self.headers, 
                    json={"children": batch}
                )
                
                if response.status_code == 200:
                    success_count += len(batch)
                    logging.info(f"バッチ {i//batch_size + 1}: {len(batch)}ブロックを追加しました")
                else:
                    logging.error(f"バッチ {i//batch_size + 1} エラー: {response.status_code}")
                    logging.error(f"レスポンス: {response.text}")
                    return False
            
            logging.info(f"合計 {success_count} ブロックを正常に追加しました")
            return True
                
        except Exception as e:
            logging.error(f"ページ更新エラー: {e}")
            return False

    def run_update(self):
        """メインの更新処理"""
        logging.info("診療カレンダー自動更新を開始します")
        
        # カレンダーデータを取得
        soup = self.get_calendar_data()
        if not soup:
            logging.error("カレンダーデータの取得に失敗しました")
            return False
        
        # カレンダー情報を抽出
        calendars = self.extract_calendar_info(soup)
        if not calendars:
            logging.error("カレンダーが見つかりませんでした")
            return False
        
        # 各カレンダーを解析
        calendar_info = []
        for calendar in calendars:
            logging.info(f"解析中: {calendar['title']}")
            data = self.parse_calendar_table(calendar['table'])
            calendar_info.append({
                'title': calendar['title'],
                'data': data
            })
        
        # Notion用フォーマットで整形
        content = self.format_calendar_for_notion(calendar_info)
        
        # Notionページを更新
        logging.info("Notionページを更新中...")
        
        # 既存の内容をクリア
        self.clear_page_content()
        
        # 新しい内容を追加
        success = self.update_page_content(content)
        
        if success:
            logging.info("診療カレンダーの自動更新が完了しました")
            return True
        else:
            logging.error("Notionページの更新に失敗しました")
            return False

def main():
    """メイン処理"""
    # 設定ファイルから認証情報を読み込み
    config_file = os.path.join(os.path.dirname(__file__), 'notion_config.json')
    
    # 環境変数から認証情報を取得（GitHub Actions対応）
    notion_token = os.getenv('NOTION_TOKEN')
    page_id = os.getenv('NOTION_PAGE_ID')
    
    # 環境変数がない場合は設定ファイルから読み込み
    if not notion_token or not page_id:
        if not os.path.exists(config_file):
            logging.error("設定ファイル notio_config.json が見つかりません")
            logging.error("設定ファイルを作成するか、環境変数を設定してください")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            notion_token = config.get('notion_token')
            page_id = config.get('page_id')
            
            if not notion_token or not page_id:
                logging.error("設定ファイルにnotion_tokenまたはpage_idが設定されていません")
                return
                
        except Exception as e:
            logging.error(f"設定ファイル読み込みエラー: {e}")
            return
    
    # Notion更新を実行
    updater = NotionCalendarUpdater(notion_token, page_id)
    success = updater.run_update()
    
    if success:
        print("✅ 診療カレンダーの自動更新が完了しました")
    else:
        print("❌ 診療カレンダーの自動更新に失敗しました")
        print("ログファイル notion_update.log を確認してください")

if __name__ == "__main__":
    main()
