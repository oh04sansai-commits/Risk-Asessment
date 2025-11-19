import streamlit as st
import pandas as pd
import numpy as np
import requests # สำหรับการเรียก HTTP API

# --- การตั้งค่าเบื้องต้นของหน้า (Page Configuration) ---
st.set_page_config(
    page_title="โปรแกรมประเมินความเสี่ยงจากการทำงาน",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: ปรับแต่งพื้นหลังและ Radio Button ให้เหมือน Tab ---
st.markdown(
    """
    <style>
    /* กำหนดพื้นหลังของแอปทั้งหมดเป็นสีฟ้าอ่อนมาก ๆ */
    .stApp {
        background-color: #F2F8FD; 
    }
    
    /* (ทางเลือก) ปรับสีพื้นหลังของ Sidebar */
    [data-testid="stSidebar"] {
        background-color: #E6F2FF;
    }

    /* ปรับแต่ง Radio Button ให้ดูเหมือน Menu Bar */
    div.row-widget.stRadio > div {
        flex-direction: row;
        justify-content: center;
        background-color: #ffffff;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div.row-widget.stRadio > div > label {
        background-color: #f0f2f6;
        padding: 10px 20px;
        border-radius: 5px;
        margin: 0 5px;
        border: 1px solid #d1d5db;
        cursor: pointer;
    }
    div.row-widget.stRadio > div > label[data-baseweb="radio"] {
        background-color: #bfdbfe; /* สีเมื่อเลือก */
        border-color: #3b82f6;
        font-weight: bold;
        color: #1e3a8a;
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
    'ตำแหน่งงาน': 'position' # ตำแหน่งงาน (Col C)
}
REQUIRED_COLUMNS = list(LOG_KEYS.keys())

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
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ API ({action}): กรุณาตรวจสอบ URL, การ Deploy และสิทธิ์เข้าถึง. Error: {e}")
        return None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุในการเรียก API: {e}")
        return None

# --- 2. ฟังก์ชันโหลดข้อมูลจริง ---

def load_log_data():
    """โหลดข้อมูลขั้นตอนการทำงานจริงจาก Google Sheet และกรองตามคอลัมน์ A"""
    with st.spinner("กำลังโหลดข้อมูลขั้นตอนการทำงานจาก Google Sheet..."):
        response = fetch_sheet_data('read', LOG_SHEET_NAME)
        
        if response and response.get('status') == 'success':
            data_list = response.get('data', [])
            
            if not data_list:
                return pd.DataFrame(columns=REQUIRED_COLUMNS)
            
            df = pd.DataFrame(data_list)
            
            # 1. แมปชื่อคีย์กลับไปเป็นชื่อคอลัมน์ภาษาไทยที่ Streamlit คาดหวัง
            reverse_map = {v: k for k, v in LOG_KEYS.items()}
            df = df.rename(columns=reverse_map)
            
            # 2. ทำความสะอาดคอลัมน์ที่ไม่ต้องการ
            if 'rowIndex' in df.columns:
                df = df.drop(columns=['rowIndex'])
                  
            # 3. เลือกเฉพาะคอลัมน์ที่ต้องการตามลำดับใหม่
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
    st.session_state.log_data = load_log_data()
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
disabled_text = "คุณมีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก กรุณากด 💾 บันทึก ก่อน"
disabled_state = is_edited

# --- เปลี่ยนจาก st.tabs เป็น st.radio เพื่อความเสถียรของหน้าจอ (แก้ปัญหาหน้าเด้ง) ---
menu_options = [
    "1. คู่มือการประเมินความเสี่ยง", 
    "2. บันทึกขั้นตอนการทำงาน", 
    "3. ประเมินความเสี่ยงจากการทำงาน"
]

selected_tab = st.radio(
    "เลือกเมนู:", 
    menu_options, 
    index=1, # ตั้งค่าเริ่มต้นเป็นหน้าที่ 2 (หรือ 0 หากต้องการหน้าแรก)
    horizontal=True,
    label_visibility="collapsed" # ซ่อน Label
)

st.markdown("---") # เส้นคั่นสวยงาม

# --- แท็บ 1: คู่มือการประเมินความเสี่ยง ---
if selected_tab == "1. คู่มือการประเมินความเสี่ยง":
    st.header("1. คู่มือการประเมินความเสี่ยงจากการทำงาน")
    
    # Req 4: เตือนเมื่อมีข้อมูลที่ยังไม่ได้บันทึก
    if disabled_state:
        st.warning(f"**{disabled_text}** ก่อนเข้าถึงหน้านี้")
    
    st.link_button(
        "คลิก เพื่อดาวน์โหลด", 
        url="https://drive.google.com/file/d/1VQb2pw5La9NPKjLDzKr_KnucMsRy_Wjl/view?usp=sharing",
        type="primary",
        disabled=disabled_state
    )

# --- แท็บ 2: บันทึกขั้นตอนการทำงาน-ลักษณะงาน (Editable Table) ---
elif selected_tab == "2. บันทึกขั้นตอนการทำงาน":
    st.header("2. บันทึกขั้นตอนการทำงาน-ลักษณะงาน")
    st.info("แก้ไขข้อมูลในตารางโดยตรง เพิ่ม/ลบรายการใหม่ และกด **💾 บันทึกข้อมูล** เพื่ออัปเดต Google Sheet ทันที")
    
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
    
    # 4.2 Column Config
    column_config = {
        "กลุ่มงาน": st.column_config.TextColumn("กลุ่มงาน", width="small"), 
        "ขั้นตอนการทำงาน-ลักษณะงาน": st.column_config.TextColumn(
            "ขั้นตอนการทำงาน-ลักษณะงาน", 
            width="large", 
        ),
        "ตำแหน่งงาน": st.column_config.TextColumn("ตำแหน่งงาน", width="medium")
    }

    # 4.3 กรองข้อมูลที่จะแสดงผลใน Editor
    display_df = st.session_state.log_data.copy()
    if selected_id != '--- แสดงทั้งหมด ---':
        # เก็บ Index ของแถวที่ถูกกรอง เพื่อให้ง่ายต่อการ Merge กลับ
        original_indices_filtered = display_df[display_df['กลุ่มงาน'] == selected_id].index
        display_df = display_df[display_df['กลุ่มงาน'] == selected_id]
    
    # **FIX**: ใช้ Dynamic Key (เติม selected_id) เพื่อป้องกัน State ชนกันซึ่งทำให้แอปเด้ง/รีเซ็ต
    editor_key = f"log_editor_{selected_id}"

    edited_df = st.data_editor(
        display_df,
        key=editor_key, # Key เปลี่ยนตาม Filter ทำให้ไม่ Error
        column_config=column_config,
        column_order=REQUIRED_COLUMNS, 
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    # 4.4 จัดการการเปลี่ยนแปลง
    if not edited_df.equals(display_df):
        st.session_state.edited_log = True
          
        if selected_id == '--- แสดงทั้งหมด ---':
            st.session_state.log_data = edited_df.copy()
        else:
            # Merge Logic
            data_without_current_group = st.session_state.log_data[st.session_state.log_data['กลุ่มงาน'] != selected_id]
            st.session_state.log_data = pd.concat([data_without_current_group, edited_df], ignore_index=True)

    # --- REMOVED: ปุ่มเพิ่มข้อมูลด้านล่างตาราง (ถูกลบตามคำขอ) ---
    
    def save_log_data_callback():
        df_to_save = st.session_state.log_data.copy()
        df_to_save = df_to_save[df_to_save['กลุ่มงาน'].astype(str).str.strip() != '']
        
        reverse_rename_map = {k: v for k, v in LOG_KEYS.items()} 
        df_to_save = df_to_save.rename(columns=reverse_rename_map)
        
        columns_to_keep = list(LOG_KEYS.values())
        if not df_to_save.empty:
            df_to_save = df_to_save[columns_to_keep]

        with st.spinner("กำลังบันทึกข้อมูลขั้นตอนการทำงานไปยัง Google Sheet..."):
            response = fetch_sheet_data('write', LOG_SHEET_NAME, df_to_save)

        if response and response.get('status') == 'success':
            st.toast("บันทึกข้อมูลขั้นตอนการทำงานเรียบร้อยแล้ว!", icon='✅')
            st.session_state.log_data = load_log_data()
            st.session_state.initial_log_data = st.session_state.log_data.copy()
            st.session_state.edited_log = False
            st.rerun() 
        else:
            st.error(f"บันทึกข้อมูลล้มเหลว: {response.get('message') if response else 'API Error'}")
            st.session_state.edited_log = True
          
    st.button(
        "💾 บันทึกข้อมูล (Update Google Sheet)", 
        on_click=save_log_data_callback,
        disabled=not is_edited,
        type="primary"
    )
    st.caption("ข้อมูลนี้จะถูกบันทึกถาวรใน Google Sheet ของคุณ")

# --- แท็บ 3: ประเมินความเสี่ยงจากการทำงาน ---
elif selected_tab == "3. ประเมินความเสี่ยงจากการทำงาน":
    st.header("3. ประเมินความเสี่ยงจากการทำงาน")

    # Req 4: เตือนเมื่อมีข้อมูลที่ยังไม่ได้บันทึก
    if disabled_state:
        st.warning(f"**{disabled_text}** ก่อนเข้าถึงหน้านี้")
          
    department_options = ["--- กรุณาเลือกหน่วยงาน ---"] + list(st.session_state.risk_mock_data.keys())
    
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
