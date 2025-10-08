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

# --- 0. การตั้งค่าการเชื่อมต่อ API ---
# ID ของ Google Sheet (จาก URL ของ Sheet)
SPREADSHEET_ID = "10HEC9q7mwhvCkov1sd8IMWFNYhXLZ7-nQj0S10tAATQ" 
# URL ของ Google Apps Script Web App ที่ Deploy แล้ว (กรุณาแทนที่ด้วย URL จริงของคุณ)
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
            # เพิ่ม timeout เพื่อป้องกันการรอนานเกินไป
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
    """โหลดข้อมูลขั้นตอนการทำงานจริงจาก Google Sheet"""
    with st.spinner("กำลังโหลดข้อมูลขั้นตอนการทำงานจาก Google Sheet..."):
        response = fetch_sheet_data('read', LOG_SHEET_NAME)
        
        if response and response.get('status') == 'success':
            data_list = response.get('data', [])
            
            if not data_list:
                return pd.DataFrame(columns=REQUIRED_COLUMNS)
            
            df = pd.DataFrame(data_list)
            
            # แมปชื่อคีย์กลับไปเป็นชื่อคอลัมน์ภาษาไทย
            reverse_map = {v: k for k, v in LOG_KEYS.items()}
            df = df.rename(columns=reverse_map)
            
            # ทำความสะอาดคอลัมน์ที่ไม่ต้องการและเลือกเฉพาะที่จำเป็น
            if 'rowIndex' in df.columns:
                df = df.drop(columns=['rowIndex'])
                
            df = df[REQUIRED_COLUMNS]
            
            # กรองแถวที่คอลัมน์ 'กลุ่มงาน' ว่างเปล่า
            df = df[df['กลุ่มงาน'].astype(str).str.strip() != '']
            
            return df
        else:
            st.warning("ไม่สามารถโหลดข้อมูลขั้นตอนการทำงานได้ (ใช้ข้อมูลว่างแทน).")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)


# จำลองข้อมูลประเมินความเสี่ยง (Mock Data)
def load_risk_mock_data():
    """จำลองข้อมูลความเสี่ยงตามหน่วยงาน (ไม่ได้เชื่อมต่อ API)"""
    # ... (ข้อมูลจำลองเหมือนเดิม)
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
    st.session_state.initial_log_data = st.session_state.log_data.copy()
    st.session_state.risk_mock_data = load_risk_mock_data()
    st.session_state.edited_log = False # สถานะการแก้ไข

# NEW: Session state to track the active tab, defaulting to Tab 2
# This helps ensure the tab is restored after an explicit st.rerun()
if 'active_tab_label' not in st.session_state:
    st.session_state.active_tab_label = "2. บันทึกขั้นตอนการทำงาน"


# --- ฟังก์ชันสำหรับเพิ่มแถวใหม่ (Req 1) ---
def add_new_row():
    """เพิ่มแถวว่างใหม่ใน Session State และตั้งค่าว่ามีการแก้ไข"""
    new_row = pd.DataFrame({col: [''] for col in REQUIRED_COLUMNS})
    st.session_state.log_data = pd.concat([st.session_state.log_data, new_row], ignore_index=True)
    st.session_state.edited_log = True # ตั้งค่าสถานะการแก้ไข
    # NEW FIX: บังคับให้แท็บยังอยู่ที่เดิมหลัง RERUN
    st.session_state.active_tab_label = "2. บันทึกขั้นตอนการทำงาน"
    st.rerun() 


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

st.title("โปรแกรมประเมินความเสี่ยงจากการทำงาน โรงพยาบาลสันทราย")
st.subheader("Risk Assessment Program")

# ตรวจสอบสถานะการแก้ไขเพื่อใช้ในการปิดการใช้งานแท็บอื่น (Req 3)
is_edited = st.session_state.edited_log
disabled_text = "คุณมีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก กรุณากด 💾 บันทึก ก่อน"
disabled_state = is_edited

# Define tab names and find the index of the desired active tab
tab_labels = [
    "1. คู่มือการประเมินความเสี่ยง", 
    "2. บันทึกขั้นตอนการทำงาน", 
    "3. ประเมินความเสี่ยงจากการทำงาน"
]

# NEW FIX: ใช้ `index` เพื่อให้ Streamlit เปิดแท็บที่ถูกต้องเมื่อมีการ RERUN
try:
    initial_tab_index = tab_labels.index(st.session_state.active_tab_label)
except ValueError:
    initial_tab_index = 1 # Default to tab 2 if state is invalid


# สร้างแท็บ โดยใช้ `initial_sidebar_state` (ไม่ได้ใช้ แต่เพิ่ม `key` เพื่อช่วย tracking)
# st.tabs จะจำสถานะการเลือกแท็บโดยอัตโนมัติ ยกเว้นเมื่อถูกบังคับ rerun
tab1, tab2, tab3 = st.tabs(
    tab_labels, 
    key="main_tabs" # เพิ่ม key เพื่อช่วยในการ track state 
)

# --- แท็บ 2: บันทึกขั้นตอนการทำงาน-ลักษณะงาน (Editable Table) ---
with tab2:
    st.header("2. บันทึกขั้นตอนการทำงาน-ลักษณะงาน")
    st.info("แก้ไขข้อมูลในตารางโดยตรง ลบ (เมนู ...) หรือเพิ่มแถว (ปุ่ม + ด้านล่าง) และกด **💾 บันทึกข้อมูล** เพื่ออัปเดต Google Sheet ทันที")
    
    # 4.1 Dropdown กรองข้อมูล 
    current_data_for_display = st.session_state.log_data.copy()

    if 'กลุ่มงาน' in current_data_for_display.columns:
        non_empty_groups = current_data_for_display['กลุ่มงาน'].astype(str).str.strip().unique()
        filter_options = ['--- แสดงทั้งหมด ---'] + sorted(non_empty_groups[non_empty_groups != ''].tolist())
    else:
        filter_options = ['--- แสดงทั้งหมด ---']
        
    # NEW: Add a key to selectbox to help track state.
    selected_id = st.selectbox(
        "กรองข้อมูลตามกลุ่มงาน:",
        options=filter_options,
        index=0,
        key="log_filter_select",
    )

    st.markdown("### ตารางขั้นตอนการทำงาน (แก้ไข/เพิ่ม/ลบได้)")
    
    # 4.2 Column Config (รองรับการตัดคำและเพิ่มบรรทัด)
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
        display_df = display_df[display_df['กลุ่มงาน'] == selected_id]
        
    edited_df = st.data_editor(
        display_df,
        key="log_editor",
        column_config=column_config,
        column_order=REQUIRED_COLUMNS, 
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic" 
    )
    
    # 4.4 จัดการการเปลี่ยนแปลง (ตรวจจับการแก้ไข/การเพิ่ม/การลบ)
    
    if not edited_df.equals(display_df):
        st.session_state.edited_log = True
        # NEW FIX: ให้แน่ใจว่าแท็บยังอยู่ที่ Tab 2 เมื่อมีการแก้ไขในตาราง
        st.session_state.active_tab_label = "2. บันทึกขั้นตอนการทำงาน"
        
        if selected_id == '--- แสดงทั้งหมด ---':
            # ไม่มี Filter: อัปเดตข้อมูลหลักทั้งหมดด้วย edited_df
            st.session_state.log_data = edited_df.copy()
        else:
            # มี Filter: ต้องทำการ Merge ข้อมูลที่แก้ไข/เพิ่ม/ลบ กลับเข้าสู่ข้อมูลหลัก
            data_without_current_group = st.session_state.log_data[st.session_state.log_data['กลุ่มงาน'] != selected_id]
            st.session_state.log_data = pd.concat([data_without_current_group, edited_df], ignore_index=True)
            
    # 4.5 ปุ่มเพิ่มแถวใหม่
    st.button(
        "➕ เพิ่มแถวใหม่", 
        on_click=add_new_row, 
        key="add_row_btn_bottom", 
        type="secondary"
    )

    # 4.6 ปุ่มบันทึกข้อมูล
    
    def save_log_data_callback():
        
        df_to_save = st.session_state.log_data.copy()

        # 1. ทำความสะอาดข้อมูล: ลบแถวที่เป็นค่าว่างทั้งหมด (ยึดตาม 'กลุ่มงาน') ก่อนส่งไปบันทึก
        df_to_save = df_to_save[df_to_save['กลุ่มงาน'].astype(str).str.strip() != '']
        
        # 2. แปลงชื่อคอลัมน์จากภาษาไทยกลับเป็นคีย์ API
        reverse_rename_map = {k: v for k, v in LOG_KEYS.items()} 
        df_to_save = df_to_save.rename(columns=reverse_rename_map)
        
        # 3. เลือกเฉพาะคอลัมน์ที่ต้องการตามลำดับที่ Apps Script คาดหวัง
        columns_to_keep = list(LOG_KEYS.values())
        if not df_to_save.empty:
            df_to_save = df_to_save[columns_to_keep]

        # 4. เรียก API เพื่อเขียนข้อมูล (Full Overwrite)
        with st.spinner("กำลังบันทึกข้อมูลขั้นตอนการทำงานไปยัง Google Sheet..."):
            response = fetch_sheet_data('write', LOG_SHEET_NAME, df_to_save)

        if response and response.get('status') == 'success':
            st.toast("บันทึกข้อมูลขั้นตอนการทำงานเรียบร้อยแล้ว!", icon='✅')
            # โหลดข้อมูลใหม่ทั้งหมดเพื่อรีเซ็ตสถานะการแก้ไข
            st.session_state.log_data = load_log_data()
            st.session_state.initial_log_data = st.session_state.log_data.copy()
            st.session_state.edited_log = False
            # NEW FIX: ให้แน่ใจว่าแท็บยังอยู่ที่เดิมหลังจากการบันทึกและ RERUN
            st.session_state.active_tab_label = "2. บันทึกขั้นตอนการทำงาน"
            st.rerun() 
        else:
            st.error(f"บันทึกข้อมูลล้มเหลว: {response.get('message') if response else 'API Error'}")
            st.session_state.edited_log = True
            # หากบันทึกไม่สำเร็จ ให้สถานะแท็บยังอยู่ที่ 2
            st.session_state.active_tab_label = "2. บันทึกขั้นตอนการทำงาน"
        
    st.button(
        "💾 บันทึกข้อมูล (Update Google Sheet)", 
        on_click=save_log_data_callback,
        disabled=not is_edited,
        type="primary"
    )
    st.caption("การบันทึกนี้จะเขียนทับข้อมูลทั้งหมดใน Google Sheet ด้วยข้อมูลล่าสุดที่แสดงในตาราง")

# --- แท็บ 1: คู่มือการประเมินความเสี่ยง ---
with tab1:
    st.header("1. คู่มือการประเมินความเสี่ยงจากการทำงาน")
    
    # Req 3: ป้องกันการใช้งานหากมีการแก้ไข
    if disabled_state:
        st.warning(f"**{disabled_text}** ก่อนเข้าถึงแท็บนี้")
    
    st.link_button(
        "คลิก เพื่อดาวน์โหลด", 
        url="https://drive.google.com/file/d/1VQb2pw5La9NPKjLDzKr_KnucMsRy_Wjl/view?usp=sharing",
        type="primary",
        disabled=disabled_state
    )

# --- แท็บ 3: ประเมินความเสี่ยงจากการทำงาน ---
with tab3:
    st.header("3. ประเมินความเสี่ยงจากการทำงาน")

    # Req 3: ป้องกันการใช้งานหากมีการแก้ไข
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
