import streamlit as st
import pandas as pd
import numpy as np
import requests # สำหรับการเรียก HTTP API
from datetime import datetime # นำเข้า datetime สำหรับการบันทึกเวลา
import pytz # NEW: นำเข้า pytz สำหรับจัดการ Timezone ในไทย

# --- การตั้งค่าเบื้องต้นของหน้า (Page Configuration) ---
st.set_page_config(
    page_title="โปรแกรมประเมินความเสี่ยงจากการทำงาน",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: ปรับแต่งพื้นหลังเป็นสีฟ้าอ่อน ---
st.markdown(
    """
    <style>
    /* กำหนดพื้นหลังของแอปทั้งหมดเป็นสีฟ้าอ่อนมาก ๆ */
    .stApp {
        background-color: #F2F8FD; 
    }
    
    /* (ทางเลือก) ปรับสีพื้นหลังของ Sidebar ให้เข้ากันเล็กน้อย หรือจะลบออกก็ได้ถ้าชอบสีเดิม */
    [data-testid="stSidebar"] {
        background-color: #E6F2FF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 0. การตั้งค่าการเชื่อมต่อ API ---
# ID ของ Google Sheet (จาก URL ของ Sheet)
SPREADSHEET_ID = "10HEC9q7mwhvCkov1sd8IMWFNYhXLZ7-nQj0S10tAATQ" 
# URL ของ Google Apps Script Web App ที่ Deploy แล้ว (URL ล่าสุดของคุณ)
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyJm3h-MaQoVL7q-cTZjawiIKmSeHgM_8W3Sj_iboGXZRXVFmOvh-XhFvgwaHv4m1s5/exec"
LOG_SHEET_NAME = "ขั้นตอนการทำงาน-ลักษณะงาน"

# ชื่อคอลัมน์ที่แสดงผลใน UI และคีย์ API ที่เกี่ยวข้อง
LOG_KEYS = {
    'กลุ่มงาน': 'id', # รหัส (Col A)
    'ขั้นตอนการทำงาน-ลักษณะงาน': 'activity', # ขั้นตอนการทำงาน-ลักษณะงาน (Col B)
    'ตำแหน่งงาน': 'position', # ตำแหน่งงาน (Col C)
    'อัพเดทล่าสุด': 'update_date' # วันที่อัปเดต (Col D)
}

# กำหนดให้เฉพาะคอลัมน์ที่ต้องการแสดงผลและแก้ไขได้เท่านั้น
# IMPORTANT: เพิ่ม 'อัพเดทล่าสุด' เข้ามา เพื่อให้ข้อมูลถูกโหลดจาก Sheet และแสดงผลในตาราง
REQUIRED_COLUMNS = ['กลุ่มงาน', 'ขั้นตอนการทำงาน-ลักษณะงาน', 'ตำแหน่งงาน', 'อัพเดทล่าสุด'] 

# --- 1. ฟังก์ชันการเชื่อมต่อ Google Apps Script API ---

def fetch_sheet_data(action, sheet_name, data=None):
    """ฟังก์ชันหลักสำหรับเรียกใช้ Google Apps Script API"""
    try:
        if action == 'read':
            params = {
                'action': action,
                'sheet': sheet_name,
                'spreadsheetId': SPREADSHEET_ID
            }
            response = requests.get(GAS_WEB_APP_URL, params=params)
        
        elif action == 'write':
            # POST request
            payload = {
                'action': action,
                'sheet': sheet_name,
                'spreadsheetId': SPREADSHEET_ID,
                'data': data.to_dict('records') if data is not None else []
            }
            response = requests.post(GAS_WEB_APP_URL, json=payload, timeout=60) 

        response.raise_for_status() # ตรวจสอบ HTTP errors (เช่น 4xx, 5xx)
        return response.json()

    except requests.exceptions.RequestException as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ API ({action}): กรุณาตรวจสอบ URL, การDeploy และสิทธิ์เข้าถึง. Error: {e}")
        return None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุในการเรียก API: {e}")
        return None

# --- 2. ฟังก์ชันโหลดข้อมูลจริง ---

def load_log_data(show_spinner=True):
    """
    โหลดข้อมูลขั้นตอนการทำงานจริงจาก Google Sheet 
    สามารถปิดการแสดงผล st.spinner ได้เมื่อโหลดหลังการบันทึกสำเร็จ
    """
    
    # ใช้ออปเจ็กต์สำหรับจัดการ context
    if show_spinner:
        # เปลี่ยนข้อความแสดงผลตอนโหลดหน้าเพจเป็น "Loading"
        context_manager = st.spinner("Loading")
    else:
        # Dummy context manager ที่ไม่มีการแสดงผลใดๆ
        class DummyContext:
            def __enter__(self):
                pass
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        context_manager = DummyContext()
        
    with context_manager:
        response = fetch_sheet_data('read', LOG_SHEET_NAME)
        
        if response and response.get('status') == 'success':
            data_list = response.get('data', [])
            
            # เนื่องจากตอนนี้มีเพียง 3 คอลัมน์ที่ต้องการแสดงผลใน REQUIRED_COLUMNS 
            columns_to_load = list(LOG_KEYS.keys())
            
            if not data_list:
                # ใช้ REQUIRED_COLUMNS สำหรับ DataFrame ว่างที่ใช้ใน Session State
                return pd.DataFrame(columns=REQUIRED_COLUMNS) 
            
            df = pd.DataFrame(data_list)
            
            # --- FIX: Ensure all required API keys are present before renaming ---
            api_keys_to_check = list(LOG_KEYS.values())
            for api_key in api_keys_to_check:
                if api_key not in df.columns:
                    # Initialize missing column with empty string to avoid KeyError
                    df[api_key] = '' 
            # -------------------------------------------------------------------
            
            # 1. แมปชื่อคีย์กลับไปเป็นชื่อคอลัมน์ภาษาไทยที่ Streamlit คาดหวัง
            reverse_map = {v: k for k, v in LOG_KEYS.items()}
            df = df.rename(columns=reverse_map)
            
            # 2. ทำความสะอาดคอลัมน์ที่ไม่ต้องการ
            if 'rowIndex' in df.columns:
                df = df.drop(columns=['rowIndex'])
                  
            # 3. เลือกเฉพาะคอลัมน์ที่ต้องการตามลำดับใหม่ (ตอนนี้รวม 'อัพเดทล่าสุด' ด้วย)
            df = df[REQUIRED_COLUMNS] 
            
            # 4. การกรอง: ยึดคอลัมน์ 'กลุ่มงาน' (Col A) เป็นหลักมีมีข้อมูลในบรรทัดนั้น ๆ
            df = df[df['กลุ่มงาน'].astype(str).str.strip() != '']
            
            return df
        else:
            st.warning("ไม่สามารถโหลดข้อมูลขั้นตอนการทำงานได้ (ใช้ข้อมูลว่างแทน).")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)


# จำลองข้อมูลประเมินความเสี่ยง (Mock Data)
def load_risk_mock_data():
    """จำลองข้อมูลความเสี่ยงตามหน่วยงาน (ไม่ได้เชื่อมต่อ API)"""
    return {
        "แผนกการผลิต": pd.DataFrame({
            'กิจกรรม': ["ยกกล่องหนัก", "ใช้เครื่องจักรเจาะ"],
            'อันตรายที่อาจเกิดขึ้น': ["บาดเจ็บหลัง/กล้ามเนื้อ", "นิ้วติด/เศษโลหะกระเด็น"],
            'มาตรการควบคุมปัจจุบัน': ["ใช้รถเข็นหรือยกสองคน", "สวมถุงมือและแว่นตานิรภัย, มีการ์ดป้องกัน"],
            'L': [3, 2], 'C': [4, 5]
        }),
        "แผนกบัญชี": pd.DataFrame({
            'กิจกรรม': ["นั่งทำงานหน้าคอมพิวเตอร์นาน"],
            'อันตรายที่อาจเกิดขึ้น': ["ปวดตา/ปวดหลัง/ออฟฟิศซินโดรม"],
            'มาตรการควบคุมปัจจุบัน': ["พักสายตา 20-20-20, เก้าอี้ Ergonomic"],
            'L': [4], 'C': [2]
        }),
    }


# --- 3. การจัดการ Session State และข้อมูลเริ่มต้น ---
if 'log_data' not in st.session_state:
    st.session_state.log_data = load_log_data() # ใช้ค่า Default: show_spinner=True (จะแสดง "Loading")
    st.session_state.initial_log_data = st.session_state.log_data.copy() # ข้อมูลเริ่มต้นสำหรับการเปรียบเทียบ
    st.session_state.risk_mock_data = load_risk_mock_data()
    st.session_state.edited_log = False


# --- ฟังก์ชันสำหรับเพิ่มแถวใหม่ ---
def add_new_row():
    """เพิ่มแถวว่างใหม่ใน Session State และตั้งค่าว่ามีการแก้ไข"""
    new_row = pd.DataFrame({col: [''] for col in REQUIRED_COLUMNS})
    st.session_state.log_data = pd.concat([st.session_state.log_data, new_row], ignore_index=True)
    st.session_state.edited_log = True # ตั้งค่าทันทีเมื่อกดเพิ่ม
    
# --- ฟังก์ชันการคำนวณและการแสดงผล ---
def calculate_risk_level(df):
    """คำนวณระดับความเสี่ยง (L x C) และกำหนดสี"""
    if df.empty:
        return df
    
    df['ระดับความเสี่ยง (L x C)'] = df['L'] * df['C']
    
    def highlight_risk(val):
        color = ''
        if val >= 15: color = 'background-color: #fca5a5; color: #991b1b; font-weight: bold;' # Red
        elif val >= 8: color = 'background-color: #fcd34d; color: #92400e; font-weight: bold;' # Orange
        elif val >= 4: color = 'background-color: #fde68a; color: #9a3412;' # Yellow
        else: color = 'background-color: #a7f3d0; color: #065f46;' # Green
        return color

    return df.style.applymap(
        highlight_risk, 
        subset=['ระดับความเสี่ยง (L x C)']
    )

# --- 4. โครงสร้าง UI หลัก ---

st.title("โปรแกรมประเมินความเสี่ยงจากการทำงาน")
st.subheader("Risk Assessment Program")

# ตรวจสอบสถานะการแก้ไขเพื่อใช้ในการปิดการใช้งานแท็บอื่น
is_edited = st.session_state.edited_log
disabled_text = "คุณมีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก กรุณากด Save / Update ก่อน"
disabled_state = is_edited

# สร้างแท็บ
tab1, tab2, tab3 = st.tabs([
    "1. คู่มือการประเมินความเสี่ยง", 
    "2. บันทึกขั้นตอนการทำงาน", 
    "3. ประเมินความเสี่ยงจากการทำงาน"
])

# --- แท็บ 2: บันทึกขั้นตอนการทำงาน-ลักษณะงาน (Editable Table) ---
with tab2:
    st.header("2. บันทึกขั้นตอนการทำงาน-ลักษณะงาน")
    
    # 4.1 Dropdown กรองข้อมูล
    current_data_for_display = st.session_state.log_data.copy()

    if 'กลุ่มงาน' in current_data_for_display.columns:
        non_empty_groups = current_data_for_display['กลุ่มงาน'].astype(str).str.strip().unique()
        filter_options = ['--- แสดงทั้งหมด ---'] + sorted(non_empty_groups[non_empty_groups != ''].tolist())
    else:
        filter_options = ['--- แสดงทั้งหมด ---']
          
    selected_id = st.selectbox(
        "กรองข้อมูลตามกลุ่มงาน:",
        options=filter_options,
        index=0,
        key="log_filter_select"
    )

    st.markdown("### ตารางขั้นตอนการทำงาน (แก้ไข/เพิ่ม/ลบได้)")
    
    # แสดงคำแนะนำการใช้งาน
    st.markdown('<p style="font-size: 16px;">แก้ไขข้อมูลในตารางโดยตรง เพิ่ม/ลบรายการใหม่ และกด <strong>Save / Update</strong> เพื่ออัปเดตข้อมูล</p>', unsafe_allow_html=True)
    
    # กำหนดค่าคอลัมน์ (เพิ่ม 'อัพเดทล่าสุด' และทำให้เป็นคอลัมน์อ่านอย่างเดียว)
    column_config = {
        "กลุ่มงาน": st.column_config.TextColumn("กลุ่มงาน", width="small"), 
        "ขั้นตอนการทำงาน-ลักษณะงาน": st.column_config.TextColumn(
            "ขั้นตอนการทำงาน-ลักษณะงาน", 
            width="large", 
        ),
        "ตำแหน่งงาน": st.column_config.TextColumn("ตำแหน่งงาน", width="medium"),
        # NEW: เพิ่มคอลัมน์วันที่อัปเดต (อ่านอย่างเดียว)
        "อัพเดทล่าสุด": st.column_config.DatetimeColumn(
            "อัพเดทล่าสุด (Col D)", 
            format="YYYY-MM-DD HH:mm:ss", 
            width="medium",
            disabled=True # ไม่อนุญาตให้แก้ไขใน UI
        ),
    }

    # 4.3 กรองข้อมูลที่จะแสดงผลใน Editor
    display_df = st.session_state.log_data.copy()
    if selected_id != '--- แสดงทั้งหมด ---':
        # เก็บ Index ของแถวที่ถูกกรอง เพื่อให้ง่ายต่อการ Merge กลับ
        original_indices_filtered = display_df[display_df['กลุ่มงาน'] == selected_id].index
        display_df = display_df[display_df['กลุ่มงาน'] == selected_id]
          
    edited_df = st.data_editor(
        display_df,
        key="log_editor",
        column_config=column_config,
        column_order=REQUIRED_COLUMNS, # REQUIRED_COLUMNS ตอนนี้รวม 'อัพเดทล่าสุด' แล้ว
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    # 4.4 จัดการการเปลี่ยนแปลง (ตรวจจับการแก้ไข/การเพิ่ม/การลบ)
    # ส่วนนี้สำคัญมาก: อัปเดต st.session_state.log_data ทันทีที่มีการแก้ไข
    if not edited_df.equals(display_df):
        st.session_state.edited_log = True
          
        if selected_id == '--- แสดงทั้งหมด ---':
            st.session_state.log_data = edited_df.copy()
        else:
            # มี Filter: ต้องทำการ Merge ข้อมูลที่แก้ไข/เพิ่ม/ลบ กลับเข้าสู่ข้อมูลหลัก
            data_without_current_group = st.session_state.log_data[st.session_state.log_data['กลุ่มงาน'] != selected_id]
            st.session_state.log_data = pd.concat([data_without_current_group, edited_df], ignore_index=True)

    # --- ปุ่ม Save / Update (ทำงานได้ตลอดเวลา) ---
    if st.button("Save / Update", type="primary"): 
        
        # เตรียมข้อมูลสำหรับการบันทึกจาก st.session_state.log_data ล่าสุด (ซึ่งอัปเดตแล้ว)
        df_to_save = st.session_state.log_data.copy()

        # 1. Clean data: ลบแถวที่ไม่มีกลุ่มงาน
        df_to_save = df_to_save[df_to_save['กลุ่มงาน'].astype(str).str.strip() != '']
        
        # 2. Add Update Timestamp (ใช้ Timezone ไทย)
        # เพิ่มวันที่และเวลาที่บันทึกข้อมูลล่าสุด
        bangkok_tz = pytz.timezone('Asia/Bangkok')
        current_timestamp = datetime.now(bangkok_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        # อัปเดตคอลัมน์ 'อัพเดทล่าสุด' ในข้อมูลที่จะบันทึกทั้งหมด
        # ตอนนี้คอลัมน์นี้ถูกรวมอยู่ใน df_to_save แล้วจากการอัปเดต REQUIRED_COLUMNS 
        # ดังนั้นการกำหนดค่านี้จะอัปเดตค่าของแถวทั้งหมด
        df_to_save['อัพเดทล่าสุด'] = current_timestamp 
        
        # 3. Rename columns ให้ตรงกับ API
        reverse_rename_map = {k: v for k, v in LOG_KEYS.items()} 
        df_to_save = df_to_save.rename(columns=reverse_rename_map)
        
        # 4. Select columns และจัดลำดับให้ถูกต้องตามที่ Apps Script คาดหวัง (id, activity, position, update_date)
        # ใช้ LOG_KEYS.values() เพื่อให้รวม 'update_date' ที่จำเป็นต้องบันทึก
        columns_to_keep = list(LOG_KEYS.values()) 
        if not df_to_save.empty:
            df_to_save = df_to_save[columns_to_keep]

        # --- Debugging check ---
        # หากวันที่ยังไม่ขึ้นใน Google Sheet ให้ลบเครื่องหมาย # ด้านหน้าบรรทัดถัดไปเพื่อดู Payload ที่ส่งไป
        # st.write("DEBUG: Payload to be sent to Google Sheet:", df_to_save.to_dict('records'))
        # -----------------------

        # 5. เรียก API
        with st.spinner("กำลังบันทึกข้อมูล...... กรุณารอสักครู่"):
            response = fetch_sheet_data('write', LOG_SHEET_NAME, df_to_save)
            
        # 6. ตรวจสอบผลลัพธ์
        if response and response.get('status') == 'success':
            st.success(f"✅ บันทึกข้อมูลและอัปเดต เรียบร้อยแล้ว! (อัปเดตล่าสุดตามเวลาไทย: {current_timestamp})")
            
            # รีเซ็ตข้อมูลและสถานะการแก้ไข
            # เรียก load_log_data(show_spinner=False) เพื่อโหลดข้อมูลใหม่ (ซึ่งจะรวมคอลัมน์อัพเดทล่าสุดแล้ว)
            st.session_state.log_data = load_log_data(show_spinner=False) 
            st.session_state.initial_log_data = st.session_state.log_data.copy()
            st.session_state.edited_log = False
            
            # รอสักครู่แล้ว Rerun เพื่อรีเฟรชหน้าจอ
            import time
            time.sleep(1) 
            st.rerun()
        else:
            error_msg = response.get('message') if response else 'API Error'
            st.error(f"❌ บันทึกข้อมูลล้มเหลว: {error_msg}")
            st.session_state.edited_log = True
          
# --- แท็บ 1: คู่มือการประเมินความเสี่ยง ---
with tab1:
    st.header("1. คู่มือการประเมินความเสี่ยงจากการทำงาน")
    
    # เตือนเมื่อมีข้อมูลที่ยังไม่ได้บันทึก
    if disabled_state:
        st.warning(f"**{disabled_text}** ก่อนเข้าถึงแท็บนี้")
    
    st.link_button(
        "คลิก เพื่อดาวน์โหลด", 
        url="https://drive.google.com/file/d/1Vgx2zuMCW8khnhQ2_QHI_sLC8wUw8_Bv/view?usp=sharing",
        type="primary",
        disabled=disabled_state
    )

# --- แท็บ 3: ประเมินความเสี่ยงจากการทำงาน ---
with tab3:
    st.header("3. ประเมินความเสี่ยงจากการทำงาน")

    # เตือนเมื่อมีข้อมูลที่ยังไม่ได้บันทึก
    if disabled_state:
        st.warning(f"**{disabled_text}** ก่อนเข้าถึงแท็บนี้")
          
    department_options = ["--- กรุณาเลือกหน่วยงาน ---"] + list(st.session_state.risk_mock_data.keys())
    
    # ปิดการใช้งาน Selectbox หากมีข้อมูลที่ยังไม่ได้บันทึก
    selected_department = st.selectbox(
        "เลือกหน่วยงานที่ต้องการประเมิน:",
        options=department_options,
        index=0,
        key="department_select",
        disabled=disabled_state
    )

    if selected_department != "--- กรุณาเลือกหน่วยงาน ---" and not disabled_state:
        st.markdown(f"## ตารางประเมินความเสี่ยง: {selected_department}")
        
        risk_df = st.session_state.risk_mock_data[selected_department].copy()
        
        st.dataframe(
            calculate_risk_level(risk_df),
            hide_index=True,
            use_container_width=True
        )

        def save_risk_callback():
            st.toast(f"บันทึกข้อมูลความเสี่ยงของ {selected_department} (Mock Save) เรียบร้อยแล้ว!", icon='💾')

        st.button(
            "บันทึกข้อมูล (Mock Save)", 
            on_click=save_risk_callback,
            type="secondary",
            disabled=disabled_state
        )

    elif selected_department == "--- กรุณาเลือกหน่วยงาน ---" and not disabled_state:
        st.warning("กรุณาเลือกหน่วยงานเพื่อเริ่มต้นการประเมินความเสี่ยง")
