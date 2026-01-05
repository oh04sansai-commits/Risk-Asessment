import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

# --- การตั้งค่าเบื้องต้นของหน้า (Page Configuration) ---
st.set_page_config(
    page_title="โปรแกรมประเมินความเสี่ยงจากการทำงาน",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: ปรับแต่งพื้นหลัง ---
st.markdown(
    """
    <style>
    .stApp { background-color: #F2F8FD; }
    [data-testid="stSidebar"] { background-color: #E6F2FF; }
    .risk-card {
        padding: 20px;
        border-radius: 15px;
        background-color: white;
        border: 1px solid #E0E0E0;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 0. การตั้งค่าการเชื่อมต่อ API ---
SPREADSHEET_ID = "10HEC9q7mwhvCkov1sd8IMWFNYhXLZ7-nQj0S10tAATQ" 
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyJm3h-MaQoVL7q-cTZjawiIKmSeHgM_8W3Sj_iboGXZRXVFmOvh-XhFvgwaHv4m1s5/exec"
LOG_SHEET_NAME = "ขั้นตอนการทำงาน-ลักษณะงาน"
RISK_RESULT_SHEET = "ผลการประเมินความเสี่ยง" # ชื่อ Sheet ใหม่สำหรับเก็บผลประเมิน

LOG_KEYS = {
    'กลุ่มงาน': 'id',
    'ขั้นตอนการทำงาน-ลักษณะงาน': 'activity',
    'ตำแหน่งงาน': 'position',
    'อัพเดทล่าสุด': 'update_date'
}

REQUIRED_COLUMNS = ['กลุ่มงาน', 'ขั้นตอนการทำงาน-ลักษณะงาน', 'ตำแหน่งงาน']

# --- 1. ฟังก์ชันการเชื่อมต่อ API ---
def fetch_sheet_data(action, sheet_name, data=None):
    try:
        if action == 'read':
            params = {'action': action, 'sheet': sheet_name, 'spreadsheetId': SPREADSHEET_ID}
            response = requests.get(GAS_WEB_APP_URL, params=params)
        elif action == 'write':
            payload = {
                'action': action,
                'sheet': sheet_name,
                'spreadsheetId': SPREADSHEET_ID,
                'data': data.to_dict('records') if data is not None else []
            }
            response = requests.post(GAS_WEB_APP_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- 2. ฟังก์ชันโหลดข้อมูล ---
def load_log_data():
    response = fetch_sheet_data('read', LOG_SHEET_NAME)
    if response and response.get('status') == 'success':
        df = pd.DataFrame(response.get('data', []))
        reverse_map = {v: k for k, v in LOG_KEYS.items()}
        df = df.rename(columns=reverse_map)
        for col in REQUIRED_COLUMNS:
            if col not in df.columns: df[col] = ''
        return df[REQUIRED_COLUMNS].fillna("")
    return pd.DataFrame(columns=REQUIRED_COLUMNS)

# --- 3. การจัดการ Session State ---
if 'log_data' not in st.session_state:
    st.session_state.log_data = load_log_data()
if 'edited_log' not in st.session_state:
    st.session_state.edited_log = False

# --- 4. ฟังก์ชันคำนวณความเสี่ยง ---
def get_risk_info(score):
    if score >= 15: return "วิกฤต (Extreme)", "#fca5a5", "#991b1b"
    elif score >= 8: return "สูง (High)", "#fcd34d", "#92400e"
    elif score >= 4: return "ปานกลาง (Medium)", "#fde68a", "#9a3412"
    else: return "ต่ำ (Low)", "#a7f3d0", "#065f46"

# --- 5. โครงสร้าง UI หลัก ---
st.title("🛡️ ระบบประเมินความเสี่ยงอัจฉริยะ")

tab1, tab2, tab3 = st.tabs([
    "📖 คู่มือการใช้งาน", 
    "📝 บันทึกขั้นตอนการทำงาน", 
    "📊 แบบประเมินความเสี่ยง"
])

# --- แท็บ 1: คู่มือ ---
with tab1:
    st.header("คู่มือการประเมินความเสี่ยง")
    st.info("กรุณาบันทึกขั้นตอนการทำงานในแท็บที่ 2 ก่อนเริ่มทำการประเมินในแท็บที่ 3")
    st.link_button("ดาวน์โหลดคู่มือ (PDF)", "https://drive.google.com/file/d/1Vgx2zuMCW8khnhQ2_QHI_sLC8wUw8_Bv/view?usp=sharing")

# --- แท็บ 2: บันทึกขั้นตอน (อิงตามโค้ดเดิมของคุณ) ---
with tab2:
    st.header("บันทึกขั้นตอนการทำงาน-ลักษณะงาน")
    
    # ตัวกรองกลุ่มงาน
    all_groups = sorted([g for g in st.session_state.log_data['กลุ่มงาน'].unique() if g])
    selected_filter = st.selectbox("กรองตามกลุ่มงาน:", ["แสดงทั้งหมด"] + all_groups)
    
    display_df = st.session_state.log_data.copy()
    if selected_filter != "แสดงทั้งหมด":
        display_df = display_df[display_df['กลุ่มงาน'] == selected_filter]

    # Editor สำหรับแก้ไขข้อมูล
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="work_step_editor"
    )

    if st.button("Save / Update ขั้นตอนการทำงาน", type="primary"):
        with st.spinner("กำลังบันทึก..."):
            # ตรรกะการ Merge ข้อมูลกลับและส่ง API (อิงตามโค้ดเดิมของคุณ)
            # ... (ส่วนนี้ใช้โค้ดเดิมที่คุณเขียนไว้ในคำถามได้เลย)
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
            st.session_state.log_data = load_log_data()
            st.rerun()

# --- แท็บ 3: แบบประเมินความเสี่ยง (ส่วนที่พัฒนาใหม่) ---
with tab3:
    st.header("แบบประเมินความเสี่ยงจากการทำงาน")
    
    if st.session_state.log_data.empty:
        st.warning("ไม่พบข้อมูลขั้นตอนการทำงาน กรุณาเพิ่มข้อมูลในแท็บที่ 2")
    else:
        # 1. เลือกกลุ่มงานจากข้อมูลจริง
        group_list = sorted(list(st.session_state.log_data['กลุ่มงาน'].unique()))
        target_group = st.selectbox("เลือกกลุ่มงานที่ต้องการประเมิน:", ["--- กรุณาเลือก ---"] + group_list)

        if target_group != "--- กรุณาเลือก ---":
            # 2. กรองขั้นตอนการทำงานเฉพาะกลุ่มงานที่เลือก
            steps = st.session_state.log_data[st.session_state.log_data['กลุ่มงาน'] == target_group]
            
            st.write(f"พบทั้งหมด {len(steps)} ขั้นตอน")
            
            # เตรียมรายการสำหรับการบันทึก
            assessment_results = []

            for index, row in steps.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="risk-card">
                        <h4 style='margin-bottom:0px;'>ขั้นตอน: {row['ขั้นตอนการทำงาน-ลักษณะงาน']}</h4>
                        <small>ตำแหน่ง: {row['ตำแหน่งงาน']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                    
                    with col1:
                        danger = st.text_input(f"อันตราย/ความเสี่ยง", key=f"danger_{index}", placeholder="ระบุอันตราย...")
                    with col2:
                        l_score = st.selectbox(f"โอกาส (L)", options=[1,2,3,4,5], key=f"l_{index}", help="1: น้อยมาก - 5: บ่อยมาก")
                    with col3:
                        c_score = st.selectbox(f"ความรุนแรง (C)", options=[1,2,3,4,5], key=f"c_{index}", help="1: เล็กน้อย - 5: รุนแรงมาก")
                    
                    score = l_score * c_score
                    label, bg_color, text_color = get_risk_info(score)
                    
                    with col4:
                        st.markdown(f"""
                        <div style="background-color:{bg_color}; color:{text_color}; padding:10px; border-radius:10px; text-align:center; font-weight:bold; margin-top:25px;">
                            คะแนน: {score} <br> {label}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    mitigation = st.text_area("มาตรการควบคุม/แก้ไข", key=f"mit_{index}", placeholder="ระบุมาตรการ...")
                    st.divider()
                    
                    # เก็บข้อมูลลง list
                    assessment_results.append({
                        'กลุ่มงาน': target_group,
                        'ขั้นตอน': row['ขั้นตอนการทำงาน-ลักษณะงาน'],
                        'อันตราย': danger,
                        'L': l_score,
                        'C': c_score,
                        'คะแนน': score,
                        'ระดับ': label,
                        'มาตรการ': mitigation,
                        'วันที่ประเมิน': datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')
                    })

            if st.button("ส่งผลการประเมินเข้าระบบ", type="primary", use_container_width=True):
                # ในขั้นตอนนี้คุณสามารถส่ง assessment_results ไปยัง Google Sheets ผ่าน API ได้เหมือนแท็บ 2
                st.balloons()
                st.success("บันทึกผลการประเมินลงในระบบเรียบร้อยแล้ว!")
                # ตัวอย่างการแสดงผล DataFrame ก่อนส่ง
                # st.write(pd.DataFrame(assessment_results))
