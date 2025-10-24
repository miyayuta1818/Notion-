#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
診療担当医カレンダー解析スクリプト
対象URL: https://www.myseikei.jp/information/
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_calendar_data():
    """Webページからカレンダーデータを取得"""
    url = 'https://www.myseikei.jp/information/'
    
    try:
        response = requests.get(url)
        response.encoding = response.apparent_encoding
        html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        return soup
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

def extract_calendar_info(soup):
    """カレンダー情報を抽出"""
    calendars = []
    
    # カレンダーのタイトルを探す（h2タグで「担当医表」を含むもの）
    calendar_headers = soup.find_all('h2', string=re.compile(r'.*担当医表.*'))
    
    for header in calendar_headers:
        title = header.get_text(strip=True)
        print(f"カレンダー発見: {title}")
        
        # タイトルの次のテーブルを取得
        table = header.find_next('table')
        if table:
            calendars.append({
                'title': title,
                'table': table
            })
    
    return calendars

def parse_calendar_table(table):
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
    
    print(f"曜日ヘッダー: {weekday_headers}")
    
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
            
            # より正確な解析
            # 例: "1AM院長PM大友医師" -> AM: 院長, PM: 大友医師
            # 例: "3院長" -> AM: 院長, PM: 記載なし
            # 例: "4AM院長PM新妻医師" -> AM: 院長, PM: 新妻医師
            
            # AM/PMの両方がある場合
            if 'AM' in cell_text and 'PM' in cell_text:
                # AMとPMの位置を特定
                am_pos = cell_text.find('AM')
                pm_pos = cell_text.find('PM')
                
                if am_pos < pm_pos:
                    # AMが先の場合
                    am_text = cell_text[am_pos + 2:pm_pos].strip()
                    pm_text = cell_text[pm_pos + 2:].strip()
                else:
                    # PMが先の場合
                    pm_text = cell_text[pm_pos + 2:am_pos].strip()
                    am_text = cell_text[am_pos + 2:].strip()
                
                if am_text:
                    am_doctors.append(am_text)
                if pm_text:
                    pm_doctors.append(pm_text)
            
            # AMのみの場合
            elif 'AM' in cell_text:
                am_pos = cell_text.find('AM')
                am_text = cell_text[am_pos + 2:].strip()
                if am_text:
                    am_doctors.append(am_text)
            
            # PMのみの場合
            elif 'PM' in cell_text:
                pm_pos = cell_text.find('PM')
                pm_text = cell_text[pm_pos + 2:].strip()
                if pm_text:
                    pm_doctors.append(pm_text)
            
            # AM/PMの記載がない場合（日付の後に直接医師名が書かれている場合）
            else:
                # 日付部分を除いたテキストを取得
                day_pos = cell_text.find(str(day_number))
                if day_pos != -1:
                    remaining_text = cell_text[day_pos + len(str(day_number)):].strip()
                    if remaining_text:
                        # 医師名として扱う（AM/PMの区別がない場合はAMとして扱う）
                        am_doctors.append(remaining_text)
            
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

def format_calendar_output(calendar_info):
    """カレンダー情報をNotion用フォーマットで整形"""
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

def main():
    """メイン処理"""
    print("診療担当医カレンダー解析を開始します...")
    
    # Webページからデータを取得
    soup = get_calendar_data()
    if not soup:
        print("Webページの取得に失敗しました。")
        return
    
    # カレンダー情報を抽出
    calendars = extract_calendar_info(soup)
    if not calendars:
        print("カレンダーが見つかりませんでした。")
        return
    
    # 各カレンダーを解析
    calendar_info = []
    for calendar in calendars:
        print(f"解析中: {calendar['title']}")
        data = parse_calendar_table(calendar['table'])
        calendar_info.append({
            'title': calendar['title'],
            'data': data
        })
    
    # 結果を整形
    output_text = format_calendar_output(calendar_info)
    
    # ファイルに保存
    with open('result.txt', 'w', encoding='utf-8') as f:
        f.write(output_text)
    
    print("result.txt に診療担当医カレンダーを保存しました。")
    print(f"抽出されたカレンダー数: {len(calendar_info)}")
    
    # 結果のプレビューを表示
    print("\n=== 結果プレビュー ===")
    lines = output_text.split('\n')
    for line in lines[:20]:  # 最初の20行を表示
        print(line)
    if len(lines) > 20:
        print("...")

if __name__ == "__main__":
    main()
