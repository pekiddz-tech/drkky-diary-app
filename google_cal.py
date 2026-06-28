import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import streamlit as st
from google.oauth2 import service_account

# 設定權限範圍
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    """從 Streamlit Secrets 讀取 Google 服務帳戶憑證"""
    try:
        # 從 st.secrets 中讀取我們設定好的 Google Service Account 資訊
        # 注意：這裡我們改用 Service Account，而不是原本的 OAuth 用戶端
        # 因為雲端環境無法跳出瀏覽器讓你點擊「授權」
        service_account_info = json.loads(st.secrets["google_calendar"]["service_account_json"])
        
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

        # 這裡需要指定你要寫入的行事曆 ID。
        # 如果使用 Service Account，'primary' 會是指 Service Account 自己的行事曆。
        # 你必須把你的個人行事曆「共用」給這個 Service Account 的信箱，並給予「有權變更活動」權限。
        # 然後在這裡填入你的個人 Gmail 信箱作為 calendarId。
        calendar_id = st.secrets["google_calendar"]["target_calendar_id"]

        event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
        return True, event_result.get('htmlLink')
        
    except Exception as e:
        return False, str(e)