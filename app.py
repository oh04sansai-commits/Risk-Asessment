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
# URL ของ Google Apps Script Web App ที่ Deploy แล้ว (URL ล่าสุดของคุณ)
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyJm3h-MaQoVL7q-cTZjawiIKmSeHgM_8W3Sj_iboGXZRXVFmOvh-XhFvgwaHv4m1s5/exec"
LOG_SHEET_NAME = "ขั้นตอนการทำงาน-ลักษณะงาน"

# ชื่อคอลัมน์ที่แสดงผลใน UI และคีย์ API ที่เกี่ยวข้อง
LOG_KEYS = {
    'กลุ่มงาน': 'id', # รหัส (Col A) เปลี่ยนเป็น กลุ่มงาน
    'ขั้นตอนการทำงาน-ลักษณะงาน': 'activity', # ขั้นตอนการทำงาน-ลักษณะงาน (Col B)
    'ตำแหน่งงาน': 'position' # ตำแหน่งงาน (Col C)
}
# --- 1. ฟังก์ชันการเชื่อมต่อ Google Apps Script API ---

def fetch_sheet_data(action, sheet_name, data=None):
    """ฟังก์ชันหลักสำหรับเรียกใช้ Google Apps Script API"""
    if GAS_WEB_APP_URL.startswith("---"):
        st.error("กรุณาแทนที่ **GAS_WEB_APP_URL** ด้วย URL ที่ Deploy แล้วในโค้ด.")
        return None

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
            # แปลง DataFrame เป็น List of Dicts เพื่อส่งไปยัง Apps Script
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
        # แสดง Error ที่ละเอียดขึ้น
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ API ({action}): กรุณาตรวจสอบ URL, การ Deploy และสิทธิ์เข้าถึง. Error: {e}")
        return None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุในการเรียก API: {e}")
        return None

# --- 2. ฟังก์ชันโหลดข้อมูลจริง (แทนที่ Mock Data) ---

def load_log_data():
    """โหลดข้อมูลขั้นตอนการทำงานจริงจาก Google Sheet ผ่าน Apps Script API"""
    with st.spinner("กำลังโหลดข้อมูลขั้นตอนการทำงานจาก Google Sheet..."):
        response = fetch_sheet_data('read', LOG_SHEET_NAME)
        
        if response and response.get('status') == 'success':
            data_list = response.get('data', [])
            
            if not data_list:
                return pd.DataFrame(columns=list(LOG_KEYS.keys()))
            
            # 1. แปลงรายการพจนานุกรม (Dict List) เป็น DataFrame
            df = pd.DataFrame(data_list)
            
            # 2. แมปชื่อคีย์กลับไปเป็นชื่อคอลัมน์ภาษาไทยที่ Streamlit คาดหวัง
            reverse_map = {v: k for k, v in LOG_KEYS.items()}
            df = df.rename(columns=reverse_map)
            
            # 3. ลบคอลัมน์ที่ไม่ต้องการ
            if 'rowIndex' in df.columns:
                df = df.drop(columns=['rowIndex'])
                
            # 4. เลือกเฉพาะคอลัมน์ที่ต้องการตามลำดับใหม่ (กลุ่มงาน, ขั้นตอนการทำงาน, ตำแหน่งงาน)
            df = df[list(LOG_KEYS.keys())]
            
            # 5. *** การกรอง: กรองเฉพาะแถวที่คอลัมน์ 'กลุ่มงาน' (Col A) มีข้อมูล ***
            # แปลงเป็น string เพื่อจัดการค่าว่าง/Null อย่างถูกต้อง
            df = df[df['กลุ่มงาน'].astype(str).str.strip() != ''] 
            
            return df
        else:
            st.warning("ไม่สามารถโหลดข้อมูลขั้นตอนการทำงานได้ (ใช้ข้อมูลว่างแทน).")
            return pd.DataFrame(columns=list(LOG_KEYS.keys()))


# จำลองข้อมูลประเมินความเสี่ยง (Mock Data for Assessment Tab)
def load_risk_mock_data():
    """จำลองข้อมูลความเสี่ยงตามหน่วยงาน (ไม่ได้เชื่อมต่อ API)"""
    return {
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
if 'log_data' not in st.session_state:
    st.session_state.log_data = load_log_data()
    st.session_state.risk_mock_data = load_risk_mock_data()
    st.session_state.edited_log = False


# --- ฟังก์ชันสำหรับเพิ่มแถวใหม่ ---
def add_new_row():
    """เพิ่มแถวว่างใหม่ใน Session State และสั่ง rerun"""
    # สร้างแถวว่างใหม่ตามคอลัมน์ปัจจุบัน
    new_row = pd.DataFrame({col: [''] for col in st.session_state.log_data.columns})
    # เชื่อมต่อแถวใหม่เข้ากับข้อมูลเดิม
    st.session_state.log_data = pd.concat([st.session_state.log_data, new_row], ignore_index=True)
    st.session_state.edited_log = True # เพื่อเปิดใช้งานปุ่มบันทึก
    # st.rerun() # ไม่ต้อง rerun เพราะการกดปุ่มจะทำให้โค้ดทำงานใหม่ตั้งแต่ต้นอยู่แล้ว

# --- 4. ฟังก์ชันการคำนวณและการแสดงผล ---
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

# ส่วนหัวข้อ
st.title("โปรแกรมประเมินความเสี่ยงจากการทำงาน โรงพยาบาลสันทราย")
st.subheader("Risk Assessment Program")

# สร้างแท็บ
tab1, tab2, tab3 = st.tabs([
    "1. คู่มือการประเมินความเสี่ยง", 
    "2. บันทึกขั้นตอนการทำงาน", 
    "3. ประเมินความเสี่ยงจากการทำงาน"
])

# --- แท็บ 1: คู่มือการประเมินความเสี่ยง ---
with tab1:
    st.header("คู่มือการประเมินความเสี่ยงจากการทำงาน")
    st.markdown("""
        <p style="font-size:16px;">
        คลิกที่ปุ่มด้านล่างเพื่อดาวน์โหลดคู่มือการประเมินความเสี่ยง
        </p>
    """, unsafe_allow_html=True)

    # ปุ่มดาวน์โหลด
    st.link_button(
        "คลิก เพื่อดาวน์โหลด", 
        url="https://drive.google.com/file/d/1VQb2pw5La9NPKjLDzKr_KnucMsRy_Wjl/view?usp=sharing",
        type="primary"
    )

# --- แท็บ 2: บันทึกขั้นตอนการทำงาน-ลักษณะงาน (Editable Table) ---
with tab2:
    st.header("2. บันทึกขั้นตอนการทำงาน-ลักษณะงาน")
    st.info("รายการนี้สามารถแก้ไขได้โดยตรงในตาราง และจะถูกบันทึกไว้ใน Google Sheet จริงเมื่อกดบันทึก")
    
    current_data = st.session_state.log_data.copy()

    # 5.1 Dropdown กรองข้อมูลตามกลุ่มงาน
    if 'กลุ่มงาน' in current_data.columns:
        # ใช้เฉพาะข้อมูลที่มีค่าไม่ว่างในการสร้างตัวเลือกกรอง
        non_empty_groups = current_data['กลุ่มงาน'].astype(str).str.strip().unique()
        filter_options = ['--- แสดงทั้งหมด ---'] + sorted(non_empty_groups[non_empty_groups != ''].tolist())
    else:
        filter_options = ['--- แสดงทั้งหมด ---']
        
    selected_id = st.selectbox(
        "กรองข้อมูลตามกลุ่มงาน:",
        options=filter_options,
        index=0,
        key="log_filter_select"
    )

    # 5.2 ตารางที่แก้ไขได้ (st.data_editor)
    
    # กรองข้อมูลก่อนนำเข้า Editor หากมีการเลือก Filter
    filtered_data = current_data.copy()
    if selected_id != '--- แสดงทั้งหมด ---' and 'กลุ่มงาน' in filtered_data.columns:
        filtered_data = filtered_data[filtered_data['กลุ่มงาน'] == selected_id]
        
    st.markdown("### ตารางขั้นตอนการทำงาน (แก้ไขได้)")
    
    # กำหนด Column Config
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

    # *** NEW: เพิ่มปุ่มเพิ่มรายการใหม่ ***
    col_add, col_spacer = st.columns([0.2, 0.8])
    with col_add:
        st.button(
            "➕ เพิ่มรายการใหม่", 
            on_click=add_new_row, 
            key="add_row_btn", 
            use_container_width=True
        )
        
    # ใช้ filtered_data ใน editor
    edited_df = st.data_editor(
        filtered_data,
        key="log_editor",
        column_config=column_config,
        column_order=list(LOG_KEYS.keys()), 
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic" # อนุญาตให้เพิ่มแถวใหม่จากปุ่ม + ใน Editor ได้ด้วย
    )
    
    # 5.3 ตรวจสอบการแก้ไขและปุ่มบันทึก
    # ตรวจสอบว่ามีการแก้ไขหรือไม่ โดยเทียบกับข้อมูลต้นฉบับ (current_data)
    # เนื่องจากเราใช้ filtered_data ใน editor, เราต้องเปรียบเทียบ edited_df กับ
    # ข้อมูลที่โหลดมาทั้งหมด (st.session_state.log_data)
    
    # 1. รวมข้อมูลที่แก้ไขแล้วกลับเข้าไปในข้อมูลหลักของ Session State
    # (หากมีการกรอง, ข้อมูลที่ไม่ได้กรองอาจถูกละเลย ซึ่งเป็นปัญหา)
    
    # วิธีที่ปลอดภัยที่สุด: ให้ st.data_editor ทำงานกับข้อมูลหลักโดยไม่มีการกรอง
    # แล้วใช้ st.rerun() เพื่อบังคับให้โหลดใหม่หลังจากบันทึก
    
    # *** ปรับปรุงการตรวจสอบการเปลี่ยนแปลง (เฉพาะกรณีที่ไม่มีการกรอง) ***
    
    # เนื่องจากเราใช้ filter: ต้องเก็บการเปลี่ยนแปลงจาก edited_df กลับเข้าสู่ st.session_state.log_data
    
    # ถ้ามีการแก้ไขใน editor
    if not edited_df.equals(filtered_data):
        st.session_state.edited_log = True
        
        # *** WARNING: การจัดการการกรอง/แก้ไขมีความซับซ้อนใน Streamlit data_editor
        # หากมีการกรองอยู่ การเปลี่ยนแปลงใน editor จะมีเฉพาะแถวที่กรอง
        # ในสถานการณ์นี้ เราจะอนุญาตให้บันทึกเมื่อมีการแก้ไข (edited_log = True)
        
        # หากไม่มีการกรอง: ให้อัปเดต st.session_state.log_data ด้วย edited_df
        if selected_id == '--- แสดงทั้งหมด ---':
            st.session_state.log_data = edited_df.copy()
            
        # หากมีการกรอง: ต้องทำการ Merge ข้อมูล
        # วิธีที่ง่ายที่สุดคือ บังคับให้ผู้ใช้กด Save เพื่อ Update
        
    else:
        st.session_state.edited_log = False

    
    def save_log_data_callback():
        # 1. *** ถ้ามีการกรองอยู่, ต้องรวมการแก้ไขจาก editor กลับเข้าสู่ข้อมูลหลัก ***
        if selected_id != '--- แสดงทั้งหมด ---':
             # หา Index ของแถวที่ถูกกรองในข้อมูลหลัก (current_data)
             original_indices = filtered_data.index
             
             # อัปเดตข้อมูลหลัก (st.session_state.log_data) ด้วยค่าจาก edited_df
             for i, idx in enumerate(original_indices):
                 if i < len(edited_df):
                     st.session_state.log_data.loc[idx] = edited_df.iloc[i]
                     
             # จัดการแถวใหม่ที่อาจเพิ่มเข้ามาใน edited_df ที่ยังไม่ถูกรวม
             if len(edited_df) > len(original_indices):
                 new_rows = edited_df.iloc[len(original_indices):]
                 st.session_state.log_data = pd.concat([st.session_state.log_data, new_rows], ignore_index=True)
                 
             df_to_save = st.session_state.log_data.copy()
             
        else:
             # หากไม่มีการกรอง: ใช้ edited_df ที่มีข้อมูลครบทั้งหมด
             df_to_save = edited_df.copy()

        # 2. ทำความสะอาดข้อมูล: ลบแถวที่เป็นค่าว่างทั้งหมด (ยึดตาม 'กลุ่มงาน')
        # ต้องทำหลังจากรวมข้อมูลกลับแล้ว
        df_to_save = df_to_save[df_to_save['กลุ่มงาน'].astype(str).str.strip() != '']
        
        # 3. แปลงชื่อคอลัมน์จากภาษาไทยกลับเป็นคีย์ API (id, activity, position)
        reverse_rename_map = {k: v for k, v in LOG_KEYS.items()} 
        df_to_save = df_to_save.rename(columns=reverse_rename_map)
        
        # 4. เลือกเฉพาะคอลัมน์ที่ต้องการ (id, activity, position) ตามลำดับที่ Apps Script คาดหวัง
        columns_to_keep = list(LOG_KEYS.values())
        if not df_to_save.empty:
            df_to_save = df_to_save[columns_to_keep]

        # 5. เรียก API เพื่อเขียนข้อมูล
        with st.spinner("กำลังบันทึกข้อมูลขั้นตอนการทำงานไปยัง Google Sheet..."):
            response = fetch_sheet_data('write', LOG_SHEET_NAME, df_to_save)

        if response and response.get('status') == 'success':
            st.toast("บันทึกข้อมูลขั้นตอนการทำงานเรียบร้อยแล้ว!", icon='✅')
            # โหลดข้อมูลใหม่เพื่อยืนยันการบันทึกและอัปเดต Session State
            st.session_state.log_data = load_log_data()
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


# --- แท็บ 3: ประเมินความเสี่ยงจากการทำงาน ---
with tab3:
    st.header("3. ประเมินความเสี่ยงจากการทำงาน")
    
    # 5.1 ส่วนเลือกหน่วยงาน
    department_options = ["--- กรุณาเลือกหน่วยงาน ---"] + list(st.session_state.risk_mock_data.keys())
    selected_department = st.selectbox(
        "เลือกหน่วยงานที่ต้องการประเมิน:",
        options=department_options,
        index=0,
        key="department_select"
    )

    if selected_department != "--- กรุณาเลือกหน่วยงาน ---":
        st.markdown(f"## ตารางประเมินความเสี่ยง: {selected_department}")
        
        # 5.2 ดึงข้อมูลและคำนวณความเสี่ยง
        risk_df = st.session_state.risk_mock_data[selected_department].copy()
        
        # แสดงตารางผลลัพธ์
        st.dataframe(
            calculate_risk_level(risk_df),
            hide_index=True,
            use_container_width=True
        )

        # 5.3 ปุ่มบันทึก (จำลอง)
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
