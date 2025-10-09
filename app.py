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
# URL ของ Google Apps Script Web App ที่ Deploy แล้ว
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx-as69Nz5nweImjexBgFN6yWbtgaSz7g6jBeZBE6c/dev"
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
        # ใช้ requests.get สำหรับการอ่าน
        if action == 'read':
            params = {
                'action': action,
                'sheet': sheet_name,
                'spreadsheetId': SPREADSHEET_ID
            }
            response = requests.get(GAS_WEB_APP_URL, params=params)
        
        # ใช้ requests.post สำหรับการเขียน (Overwrite ข้อมูล)
        elif action == 'write':
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
        # ข้อผิดพลาดจากการเชื่อมต่อ (เช่น URL ผิด, timeout, 404/500)
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ API ({action}): กรุณาตรวจสอบ URL, การ Deploy และสิทธิ์เข้าถึง. Error: {e}")
        return None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุในการเรียก API: {e}")
        return None

# --- 2. ฟังก์ชันโหลดข้อมูลจริง ---

@st.cache_data(ttl=600) # แคชข้อมูล 10 นาทีเพื่อลดการเรียก API ซ้ำ
def load_log_data():
    """โหลดข้อมูลขั้นตอนการทำงานจริงจาก Google Sheet และกรองตามคอลัมน์ A"""
    # NOTE: ลบ st.spinner ออกจากฟังก์ชันนี้เพื่อใช้ st.cache_data
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
    # โหลดข้อมูลจริง
    with st.spinner("กำลังโหลดข้อมูลขั้นตอนการทำงานจาก Google Sheet..."):
        st.session_state.log_data = load_log_data()
        
    st.session_state.initial_log_data = st.session_state.log_data.copy() # ข้อมูลเริ่มต้นสำหรับการเปรียบเทียบ
    st.session_state.risk_mock_data = load_risk_mock_data()
    st.session_state.edited_log = False # สถานะการแก้ไข


# --- ฟังก์ชันการคำนวณและการแสดงผล ---
def calculate_risk_level(df):
    """คำนวณระดับความเสี่ยง (L x C) และกำหนดสี"""
    if df.empty:
        return df
    
    df['ระดับความเสี่ยง (L x C)'] = df['L'] * df['C']
    
    def highlight_risk(val):
        color = ''
        if val >= 15: color = 'background-color: #fca5a5; color: #991b1b; font-weight: bold;' # Red (สูง)
        elif val >= 8: color = 'background-color: #fcd34d; color: #92400e; font-weight: bold;' # Orange (ปานกลางค่อนข้างสูง)
        elif val >= 4: color = 'background-color: #fde68a; color: #9a3412;' # Yellow (ปานกลาง)
        else: color = 'background-color: #a7f3d0; color: #065f46;' # Green (ต่ำ)
        return color

    return df.style.applymap(
        highlight_risk, 
        subset=['ระดับความเสี่ยง (L x C)']
    )

# --- 4. โครงสร้าง UI หลัก ---

st.title("โปรแกรมประเมินความเสี่ยงจากการทำงาน โรงพยาบาลสันทราย")
st.subheader("Risk Assessment Program")

# ตรวจสอบสถานะการแก้ไขเพื่อใช้ในการปิดการใช้งานแท็บอื่น (ป้องกันการเด้งไปแท็บอื่นขณะมีการเปลี่ยนแปลง)
is_edited = st.session_state.edited_log
disabled_text = "คุณมีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก กรุณากด 💾 บันทึก ก่อน"
disabled_state = is_edited

# สร้างแท็บ
tab_labels = [
    "1. คู่มือการประเมินความเสี่ยง", 
    "2. บันทึกขั้นตอนการทำงาน", 
    "3. ประเมินความเสี่ยงจากการทำงาน"
]

tab1, tab2, tab3 = st.tabs(
    tab_labels,
    key="main_tabs", # Key นี้จะเก็บชื่อแท็บที่ถูกเลือกไว้ใน st.session_state.main_tabs โดยอัตโนมัติ
)

# --- แท็บ 2: บันทึกขั้นตอนการทำงาน-ลักษณะงาน (Editable Table) ---
with tab2:
    st.header("2. บันทึกขั้นตอนการทำงาน-ลักษณะงาน")
    st.info("แก้ไขข้อมูลในตารางโดยตรง เพิ่ม (ปุ่ม **+**) หรือลบ (เมนู **...**) รายการใหม่ และกด **💾 บันทึกข้อมูล** เพื่ออัปเดต Google Sheet ทันที")
    
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
    
    # 4.2 Column Config (รองรับการตัดคำและเพิ่มบรรทัด)
    column_config = {
        "กลุ่มงาน": st.column_config.TextColumn("กลุ่มงาน", width="small"), 
        "ขั้นตอนการทำงาน-ลักษณะงาน": st.column_config.TextColumn(
            "ขั้นตอนการทำงาน-ลักษณะงาน", 
            width="large", # กำหนดให้ใหญ่เพื่อรองรับการตัดคำและเพิ่มบรรทัด
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
        num_rows="dynamic" # เปิดใช้งานปุ่มลบและปุ่มเพิ่มแถวในตาราง
    )
    
    # 4.4 จัดการการเปลี่ยนแปลง (ตรวจจับการแก้ไข/การเพิ่ม/การลบ)
    
    # ตรวจสอบว่า edited_df แตกต่างจาก display_df หรือไม่
    if not edited_df.equals(display_df):
        st.session_state.edited_log = True
        
        # อัปเดตข้อมูลหลักทั้งหมดด้วย edited_df (รวมถึงแถวที่เพิ่ม/ลบ/แก้ไข)
        if selected_id == '--- แสดงทั้งหมด ---':
            st.session_state.log_data = edited_df.copy()
        else:
            # มี Filter: ทำการ Merge ข้อมูลที่แก้ไข/เพิ่ม/ลบ กลับเข้าสู่ข้อมูลหลัก
            
            # 1. ข้อมูลหลักที่ไม่มีแถวของกลุ่มงานที่กำลังถูกแก้ไข
            data_without_current_group = st.session_state.log_data[st.session_state.log_data['กลุ่มงาน'] != selected_id]
            
            # 2. นำข้อมูลที่แก้ไข/ลบ/เพิ่มใหม่มาเชื่อมต่อ
            st.session_state.log_data = pd.concat([data_without_current_group, edited_df], ignore_index=True)
            
    # 4.5 ปุ่มบันทึกข้อมูล
    
    def save_log_data_callback():
        
        df_to_save = st.session_state.log_data.copy()

        # 1. ทำความสะอาดข้อมูล: ลบแถวที่เป็นค่าว่างทั้งหมด (ยึดตาม 'กลุ่มงาน')
        df_to_save = df_to_save[df_to_save['กลุ่มงาน'].astype(str).str.strip() != '']
        
        # 2. แปลงชื่อคอลัมน์จากภาษาไทยกลับเป็นคีย์ API
        reverse_rename_map = {k: v for k, v in LOG_KEYS.items()} 
        df_to_save = df_to_save.rename(columns=reverse_rename_map)
        
        # 3. เลือกเฉพาะคอลัมน์ที่ต้องการตามลำดับที่ Apps Script คาดหวัง
        columns_to_keep = list(LOG_KEYS.values())
        if not df_to_save.empty:
            df_to_save = df_to_save[columns_to_keep]

        # 4. เรียก API เพื่อเขียนข้อมูล (Overwrite)
        with st.spinner("กำลังบันทึกข้อมูลขั้นตอนการทำงานไปยัง Google Sheet..."):
            response = fetch_sheet_data('write', LOG_SHEET_NAME, df_to_save)

        if response and response.get('status') == 'success':
            st.toast("บันทึกข้อมูลขั้นตอนการทำงานเรียบร้อยแล้ว!", icon='✅')
            # โหลดข้อมูลใหม่ทั้งหมดเพื่อรีเซ็ตสถานะการแก้ไข
            st.session_state.log_data = load_log_data()
            st.session_state.initial_log_data = st.session_state.log_data.copy()
            st.session_state.edited_log = False
            
            # เมื่อมีการบันทึกสำเร็จ Streamlit จะคงสถานะแท็บเดิมไว้เนื่องจากใช้ key="main_tabs"
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

# --- แท็บ 1: คู่มือการประเมินความเสี่ยง ---
with tab1:
    st.header("1. คู่มือการประเมินความเสี่ยงจากการทำงาน")
    
    # ป้องกันการใช้งานหากมีการแก้ไข
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

    # ป้องกันการใช้งานหากมีการแก้ไข
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
