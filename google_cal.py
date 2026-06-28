import json
from googleapiclient.discovery import build
import streamlit as st
from google.oauth2 import service_account

# 設定權限範圍
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    """從 Streamlit Secrets 讀取憑證 (直接沿用 Firebase 的金鑰)"""
    try:
        # 💡 終極解法：直接沿用已經成功運作的 Firebase 金鑰！
        # 這樣就不用再去處理那串很容易複製壞掉的 service_account_json 了
        service_account_info = dict(st.secrets["firebase"])
        
        # 修正 private_key 中的換行符號 (確保 PEM 格式正確)
        if "\\n" in service_account_info.get("private_key", ""):
            service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"行事曆初始化發生內部錯誤，詳細原因：{str(e)}")
        return None

def add_diary_to_calendar(date_str, content):
    """將日記內容新增為行事曆的全天事件"""
    service = get_calendar_service()
    if not service:
        return False, "無法初始化 Google Calendar 服務，請檢查 Secrets 設定。"
        
    try:
        event = {
            'summary': f'📝 日記',
            'description': content,
            'start': {'date': date_str},
            'end': {'date': date_str},
        }

        # 讀取目標行事曆 ID
        calendar_id = st.secrets["google_calendar"]["target_calendar_id"]

        # 寫入事件
        event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        # --- 除錯核心 ---
        st.success(f"同步成功！")
        st.info(f"事件已寫入行事曆 ID: {calendar_id}")
        st.info(f"事件 ID: {event_result.get('id')}")
        
        return True, event_result.get('htmlLink')
        
    except Exception as e:
        return False, f"錯誤詳情: {str(e)}"