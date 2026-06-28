import streamlit as st
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid

# ==========================================
# 0. 初始化 Firebase (雲端資料庫)
# ==========================================
# 確保 Firebase 應用程式只初始化一次
if not firebase_admin._apps:
    try:
        # 從 Streamlit Secrets 讀取 Firebase 金鑰
        # 注意：在本機測試時，需要在專案資料夾建立 .streamlit/secrets.toml
        # 部署到 Streamlit Cloud 時，則貼在 Advanced Settings 的 Secrets 中
        if "firebase" in st.secrets:
            firebase_secrets = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_secrets)
            
            # 取得 Storage Bucket 名稱
            storage_bucket_name = st.secrets.get("firebase_config", {}).get("storage_bucket", "")
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': storage_bucket_name
            })
        else:
            st.warning("尚未設定 Firebase Secrets 金鑰。")
    except Exception as e:
        st.error(f"Firebase 初始化失敗：{e}")

# 取得 Firestore 資料庫連線
try:
    db = firestore.client()
except:
    db = None

# ==========================================
# 引入 Google Calendar 模組
# ==========================================
try:
    from google_cal import add_diary_to_calendar
    GOOGLE_CAL_AVAILABLE = True
except ImportError:
    GOOGLE_CAL_AVAILABLE = False

# ==========================================
# 1. 基本設定
# ==========================================
st.set_page_config(page_title="DRKKY 的雲端日記", page_icon="☁️", layout="centered")

# ==========================================
# 2. 側邊欄：日期選擇
# ==========================================
st.sidebar.title("📅 日記導航")
selected_date = st.sidebar.date_input("選擇日期", datetime.today())
date_str_formatted = selected_date.strftime('%Y 年 %m 月 %d 日')
date_str_filename = selected_date.strftime('%Y-%m-%d')

# ==========================================
# 3. 讀取雲端資料
# ==========================================
existing_content = ""
existing_images_urls = []

if db:
    try:
        # 嘗試從 Firestore 讀取該日期的文件
        doc_ref = db.collection(u'diaries').document(date_str_filename)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            existing_content = data.get(u'content', "")
            existing_images_urls = data.get(u'image_urls', [])
    except Exception as e:
        st.error(f"讀取資料庫失敗：{e}")

# 主畫面標題
st.title("☁️ DRKKY 的雲端日記")
st.subheader(f"📅 {date_str_formatted}")

# ==========================================
# 4. 編輯與顯示區域
# ==========================================
diary_text = st.text_area(
    label="今天過得如何？寫點什麼吧...",
    value=existing_content,
    height=350,
    placeholder="紀錄今天發生的趣事、心情或心得..."
)

# 顯示已儲存的雲端圖片
if existing_images_urls:
    st.write("📸 **今日已儲存的圖片：**")
    cols = st.columns(3)
    for i, img_url in enumerate(existing_images_urls):
        # 顯示 Firebase Storage 提供的公開網址
        cols[i % 3].image(img_url, use_container_width=True)
    
    # 雲端版簡化操作，提供一鍵清除今日所有紀錄
    if st.button("🗑️ 清除今日所有紀錄", key="clear_all_btn"):
        if db:
            doc_ref.delete()
            st.success("今日紀錄已從雲端清除！")
            st.rerun()

# 圖片上傳區域
st.write("---")
uploaded_images = st.file_uploader("新增圖片 (將上傳至雲端)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_images:
    st.write("👀 **預覽即將上傳的圖片：**")
    cols_preview = st.columns(3)
    for i, img_file in enumerate(uploaded_images):
        cols_preview[i % 3].image(img_file, use_container_width=True)

# ==========================================
# 5. 儲存與同步邏輯
# ==========================================
st.divider()

col1, col2 = st.columns([1, 1])
with col1:
    save_btn = st.button("💾 儲存至雲端", type="primary", key="save_btn_main")
with col2:
    if GOOGLE_CAL_AVAILABLE:
        sync_to_google = st.checkbox("同時備份到 Google 行事曆", value=False)
    else:
        sync_to_google = False

if save_btn:
    if not db:
        st.error("無法連線至雲端資料庫，請檢查 Firebase 金鑰設定。")
    elif diary_text.strip() or uploaded_images or existing_images_urls:
        new_image_urls = []
        
        # 處理圖片上傳至 Firebase Storage
        if uploaded_images:
            with st.spinner('正在上傳圖片至雲端儲存空間...'):
                try:
                    bucket = storage.bucket()
                    for img_file in uploaded_images:
                        # 生成雲端唯一檔名
                        file_extension = img_file.name.split('.')[-1]
                        unique_filename = f"diaries/{date_str_filename}_{uuid.uuid4().hex[:8]}.{file_extension}"
                        
                        blob = bucket.blob(unique_filename)
                        # 將檔案上傳
                        blob.upload_from_string(img_file.getvalue(), content_type=img_file.type)
                        # 將檔案設為公開，才能在網頁上直接顯示預覽
                        blob.make_public()
                        new_image_urls.append(blob.public_url)
                except Exception as e:
                    st.error(f"圖片上傳失敗：{e}")
        
        # 合併舊圖片與新圖片網址
        all_image_urls = existing_images_urls + new_image_urls
        
        # 儲存資料到 Firestore
        with st.spinner('正在儲存日記內容...'):
            try:
                doc_ref.set({
                    u'content': diary_text,
                    u'image_urls': all_image_urls,
                    u'updated_at': firestore.SERVER_TIMESTAMP
                })
                st.success("✅ 成功儲存至雲端資料庫！")
            except Exception as e:
                st.error(f"儲存失敗：{e}")

        # 觸發 Google 行事曆同步
        if sync_to_google:
            with st.spinner('正在同步到 Google 行事曆...'):
                calendar_content = diary_text
                if all_image_urls:
                    calendar_content += f"\n\n[已附加 {len(all_image_urls)} 張圖片在雲端]"
                
                success, result = add_diary_to_calendar(date_str_filename, calendar_content)
                if success:
                    st.success(f"☁️ 行事曆同步成功！[點此查看]({result})")
                else:
                    st.error(f"❌ 行事曆同步失敗，錯誤訊息：{result}")
        
        st.rerun()
    else:
         st.warning("⚠️ 請先輸入內容或選擇圖片再儲存。")

# ==========================================
# 6. 實用小工具
# ==========================================
if diary_text:
    st.caption(f"✍️ 目前字數：{len(diary_text)} 字")