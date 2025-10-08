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
# NOTE: กรุณาตรวจสอบให้แน่ใจว่า SPREADSHEET_ID และ GAS_WEB_APP_URL ถูกต้อง
SPREADSHEET_ID = "10HEC9q7mwhvCkov1sd8IMWFNYhXLZ7-nQj0S10tAATQ" 
# URL ของ Google Apps Script Web App ที่ Deploy แล้ว
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
    if GAS_WEB_APP_URL.startswith("https://script.google.com/macros/s/AKfycbyJm3h-MaQoVL7q-cTZjawiIKmSeHgM_8W3Sj_iboGXZRXVFmOvh-XhFvgwaHv4m1s5/exec"):
        # ไม่มีการแจ้งเตือนว่า URL เป็นค่าเริ่มต้น
        pass

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
            
            # 4. *** การกรอง: ยึดคอลัมน์ 'กลุ่มงาน' (Col A) เป็นหลักมีมีข้อมูลในบรรทัดนั้น ๆ ***
            # กรองแถวที่คอลัมน์ 'กลุ่มงาน' ไม่เป็นค่าว่าง (null/NaN) และไม่ใช่สตริงว่างหลังจากลบช่องว่างหัวท้าย
            df = df[df['กลุ่มงาน'].astype(str).str.strip() != '']
            
            return df
        else:
            st.warning("ไม่สามารถโหลดข้อมูลขั้นตอนการทำงานได้ (ใช้ข้อมูลว่างแทน).")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)


# จำลองข้อมูลประเมินความเสี่ยง (Mock Data for Assessment Tab)
def load_risk_mock_data():
    """จำลองข้อมูลความเสี่ยงตามหน่วยงาน (ไม่ได้เชื่อมต่อ API)"""
    return {
        # ... (ข้อมูล Mock Data ยังคงเหมือนเดิม)
        "แผนกการผลิต": pd.DataFrame({
            'กิจกรรม': ["ยกกล่องหนัก", "ใช้เครื่องจักรเจาะ"],
            'อันตรายที่อาจเกิดขึ้น': ["บาดเจ็บหลัง/กล้ามเนื้อ", "นิ้วติด/เศษโลหะกระเด็น"],
            'มาตรการควบคุมปัจจุบัน': ["ใช้รถเข็นหรือยกสองคน", "สวมถุงมือและแว่นตานิรภัย, มีการ์ดป้องกัน"],
            'L': [3, 2], # Likelihood
            'C': [4, 5]  # Consequence
        }),
        "แผนกบัญชี": pd.DataFrame({
            'กิจกรรม': ["นั่งทำงานหน้าคอมพิวเตอร์นาน"],
            'อันตรายที่อาจเกิดขึ้น': ["ปวดตา/ปวดหลัง/ออฟฟิศซินโดรม"],
            'มาตรการควบคุมปัจจุบัน': ["พักสายตา 20-20-20, เก้าอี้ Ergonomic"],
            'L': [4],
            'C': [2]
        }),
    }


# --- 3. การจัดการ Session State และข้อมูลเริ่มต้น ---
# โหลดข้อมูลเริ่มต้นและเก็บใน Session State
if 'log_data' not in st.session_state:
    st.session_state.log_data = load_log_data()
    st.session_state.initial_log_data = st.session_state.log_data.copy() # เก็บไว้สำหรับเปรียบเทียบ
    st.session_state.risk_mock_data = load_risk_mock_data()
    st.session_state.edited_log = False


# --- ฟังก์ชันสำหรับเพิ่มแถวใหม่ ---
def add_new_row():
    """เพิ่มแถวว่างใหม่ใน Session State"""
    # สร้างแถวว่างใหม่ตามคอลัมน์ปัจจุบัน
    new_row = pd.DataFrame({col: [''] for col in REQUIRED_COLUMNS})
    # เชื่อมต่อแถวใหม่เข้ากับข้อมูลเดิม
    st.session_state.log_data = pd.concat([st.session_state.log_data, new_row], ignore_index=True)
    # ไม่ต้องตั้งค่า edited_log = True ตรงนี้ เพราะ st.data_editor จะจัดการให้เมื่อผู้ใช้เริ่มแก้ไข
    
# --- 4. ฟังก์ชันการคำนวณและการแสดงผล ---
# ... (calculate_risk_level ยังคงเหมือนเดิม)
def calculate_risk_level(df):
    """คำนวณระดับความเสี่ยง (L x C) และกำหนดสี"""
    if df.empty:
        return df
    
    # คำนวณ Risk Level
    df['ระดับความเสี่ยง (L x C)'] = df['L'] * df['C']
    
    # กำหนดสไตล์ตามระดับความเสี่ยง
    def highlight_risk(val):
        color = ''
        if val >= 15:
            color = 'background-color: #fca5a5; color: #991b1b; font-weight: bold;' # Red
        elif val >= 8:
            color = 'background-color: #fcd34d; color: #92400e; font-weight: bold;' # Orange
        elif val >= 4:
            color = 'background-color: #fde68a; color: #9a3412;' # Yellow
        else:
            color = 'background-color: #a7f3d0; color: #065f46;' # Green
        return color

    return df.style.applymap(
        highlight_risk, 
        subset=['ระดับความเสี่ยง (L x C)']
    )

# --- 5. โครงสร้าง UI หลัก ---

st.title("โปรแกรมประเมินความเสี่ยงจากการทำงาน โรงพยาบาลสันทราย")
st.subheader("Risk Assessment Program")

# สร้างแท็บ
tab1, tab2, tab3 = st.tabs([
    "1. คู่มือการประเมินความเสี่ยง", 
    "2. บันทึกขั้นตอนการทำงาน", 
    "3. ประเมินความเสี่ยงจากการทำงาน"
])

# --- แท็บ 2: บันทึกขั้นตอนการทำงาน-ลักษณะงาน (Editable Table) ---
with tab2:
    st.header("2. บันทึกขั้นตอนการทำงาน-ลักษณะงาน")
    st.info("แก้ไขข้อมูลในตารางโดยตรง เพิ่มรายการใหม่ด้านล่าง และกด **💾 บันทึกข้อมูล** เพื่ออัปเดต Google Sheet ทันที")
    
    # *** 5.1 Dropdown กรองข้อมูล (ใช้สำหรับการแสดงผลเท่านั้น) ***
    
    current_data_for_display = st.session_state.log_data.copy()

    if 'กลุ่มงาน' in current_data_for_display.columns:
        # ใช้เฉพาะข้อมูลที่มีค่าไม่ว่างในการสร้างตัวเลือกกรอง
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

    # กรองข้อมูลก่อนนำเข้า Editor หากมีการเลือก Filter
    filtered_data = current_data_for_display.copy()
    if selected_id != '--- แสดงทั้งหมด ---' and 'กลุ่มงาน' in filtered_data.columns:
        filtered_data = filtered_data[filtered_data['กลุ่มงาน'] == selected_id]
        
    st.markdown("### ตารางขั้นตอนการทำงาน (แก้ไขได้)")
    
    # กำหนด Column Config (Requirement 2: Fix width และรองรับการเพิ่มบรรทัด)
    column_config = {
        "กลุ่มงาน": st.column_config.TextColumn(
            "กลุ่มงาน", 
            width="small",
        ), 
        "ขั้นตอนการทำงาน-ลักษณะงาน": st.column_config.TextColumn(
            "ขั้นตอนการทำงาน-ลักษณะงาน", 
            width="large", # กำหนดให้ใหญ่เพื่อรองรับการตัดคำและเพิ่มบรรทัด
        ),
        "ตำแหน่งงาน": st.column_config.TextColumn(
            "ตำแหน่งงาน", 
            width="medium"
        )
    }

    # *** 5.2 ตารางที่แก้ไขได้ (st.data_editor) ***
    # ให้ st.data_editor ทำงานกับข้อมูลใน Session State โดยตรง (เพื่อการติดตามที่ง่าย)
    # แต่เราต้องแน่ใจว่ามันถูกกรองแล้วสำหรับการแสดงผล
    
    # NOTE: เนื่องจาก st.data_editor ไม่สามารถรองรับการกรองข้อมูลโดยตรงและยังอนุญาตให้เพิ่มแถวได้พร้อมกัน
    # เราจะใช้ data_editor กับข้อมูลหลัก (st.session_state.log_data)
    # แต่เราจะแสดงคำเตือนว่าการกรองอาจทำให้ข้อมูลที่เพิ่มใหม่ไม่ปรากฏทันที
    
    # **เพื่อความง่ายและปลอดภัยในการบันทึก, เราจะใช้ data_editor กับข้อมูลหลัก**
    # และใช้การกรองเพียงแค่ใน Dropdown ด้านบนเท่านั้น
    
    # ถ้ามีการกรอง: จะแสดงข้อมูลที่กรองเท่านั้น
    # ถ้าไม่มีการกรอง: แสดงข้อมูลหลักทั้งหมด
    
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
        num_rows="dynamic" # อนุญาตให้เพิ่มแถวใหม่จากปุ่ม + ใน Editor ได้ด้วย
    )
    
    # *** 5.3 จัดการการเปลี่ยนแปลงและปุ่มบันทึก (Requirement 4) ***
    
    # ตรวจสอบการเปลี่ยนแปลง
    # 1. เทียบ edited_df กับ filtered_data (ข้อมูลที่แสดงผลก่อนแก้ไข)
    if not edited_df.equals(display_df):
        st.session_state.edited_log = True
        
        # อัปเดตข้อมูลหลักใน Session State ให้เป็น edited_df
        if selected_id == '--- แสดงทั้งหมด ---':
            st.session_state.log_data = edited_df.copy()
        else:
            # หากมีการกรอง: ต้องทำการ Merge ข้อมูลที่แก้ไขกลับเข้าสู่ข้อมูลหลัก
            
            # ลบแถวเดิมที่ถูกกรองออกจากข้อมูลหลัก
            data_to_save = st.session_state.log_data[st.session_state.log_data['กลุ่มงาน'] != selected_id]
            
            # เพิ่มข้อมูลที่ถูกแก้ไข/เพิ่มใหม่ของกลุ่มงานนี้กลับเข้าไป
            data_to_save = pd.concat([data_to_save, edited_df], ignore_index=True)
            
            # อัปเดต Session State
            st.session_state.log_data = data_to_save.copy()

    # 2. เปรียบเทียบกับข้อมูลเริ่มต้นที่โหลดมา (สำหรับกรณีที่ไม่ได้แก้ไขในรอบปัจจุบัน)
    elif not st.session_state.log_data.equals(st.session_state.initial_log_data):
         # ตรวจสอบว่ามีการเปลี่ยนแปลงเกิดขึ้นใน Session State จากรอบก่อนหน้าหรือไม่ (เช่น จากการกดปุ่มเพิ่มรายการ)
         st.session_state.edited_log = True
    else:
         st.session_state.edited_log = False


    # ปุ่มเพิ่มรายการใหม่ (Requirement 3: ปุ่มอยู่ด้านล่างตาราง)
    st.button(
        "➕ เพิ่มข้อมูลด้านล่างตาราง", 
        on_click=add_new_row, 
        key="add_row_btn_bottom", 
        type="secondary"
    )
    
    def save_log_data_callback():
        # ข้อมูลที่จะบันทึกคือข้อมูลปัจจุบันใน Session State
        df_to_save = st.session_state.log_data.copy()

        # 1. ทำความสะอาดข้อมูล: ลบแถวที่เป็นค่าว่างทั้งหมด (ยึดตาม 'กลุ่มงาน')
        df_to_save = df_to_save[df_to_save['กลุ่มงาน'].astype(str).str.strip() != '']
        
        # 2. แปลงชื่อคอลัมน์จากภาษาไทยกลับเป็นคีย์ API (id, activity, position)
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
            # ต้องเรียก st.rerun() เพื่อให้ UI แสดงผลข้อมูลที่โหลดมาใหม่
            st.rerun() 
        else:
            st.error(f"บันทึกข้อมูลล้มเหลว: {response.get('message') if response else 'API Error'}")
            st.session_state.edited_log = True # ยังไม่ได้บันทึก
        
    st.button(
        "💾 บันทึกข้อมูล (Update Google Sheet)", 
        on_click=save_log_data_callback,
        disabled=not st.session_state.edited_log,
        type="primary"
    )
    st.caption("ข้อมูลนี้จะถูกบันทึกถาวรใน Google Sheet ของคุณ")

# --- แท็บ 1 และ 3 (ไม่เปลี่ยนแปลง) ---
with tab1:
    st.header("คู่มือการประเมินความเสี่ยงจากการทำงาน")
    st.markdown("""
        <p style="font-size:16px;">
        คลิกที่ปุ่มด้านล่างเพื่อดาวน์โหลดคู่มือการประเมินความเสี่ยง
        </p>
    """, unsafe_allow_html=True)

    st.link_button(
        "คลิก เพื่อดาวน์โหลด", 
        url="https://drive.google.com/file/d/1VQb2pw5La9NPKjLDzKr_KnucMsRy_Wjl/view?usp=sharing",
        type="primary"
    )
    
with tab3:
    st.header("3. ประเมินความเสี่ยงจากการทำงาน")
    
    department_options = ["--- กรุณาเลือกหน่วยงาน ---"] + list(st.session_state.risk_mock_data.keys())
    selected_department = st.selectbox(
        "เลือกหน่วยงานที่ต้องการประเมิน:",
        options=department_options,
        index=0,
        key="department_select"
    )

    if selected_department != "--- กรุณาเลือกหน่วยงาน ---":
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
            type="secondary"
        )
        st.caption("ปุ่มนี้จำลองการบันทึกข้อมูล ซึ่งในการใช้งานจริงจะต้องเชื่อมต่อกับฐานข้อมูล")

    else:
        st.warning("กรุณาเลือกหน่วยงานเพื่อเริ่มต้นการประเมินความเสี่ยง")
