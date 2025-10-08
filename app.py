import streamlit as st
import pandas as pd
import numpy as np

# --- การตั้งค่าเบื้องต้นของหน้า (Page Configuration) ---
# ตั้งชื่อหน้าเว็บและไอคอน
st.set_page_config(
    page_title="โปรแกรมประเมินความเสี่ยงจากการทำงาน",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. ฟังก์ชันโหลด/จำลองข้อมูล (Mock Data Initialization) ---

# จำลองข้อมูลขั้นตอนการทำงาน (ชีท 'ขั้นตอนการทำงาน-ลักษณะงาน')
def load_log_data():
    """จำลองการโหลดข้อมูลขั้นตอนการทำงานจาก Google Sheet/DB"""
    data = {
        'รหัส (Col A)': ['T001', 'T002', 'T003', 'T004', 'T005'],
        'ขั้นตอนการทำงาน-ลักษณะงาน (Col B)': [
            'การตรวจสอบวัสดุสิ้นเปลือง', 
            'การบันทึกบัญชีรายรับ', 
            'การให้คำแนะนำผู้ป่วยใหม่', 
            'การจัดทำรายงานประจำเดือน', 
            'การจัดเก็บยาและเวชภัณฑ์'
        ],
        'ตำแหน่งงาน (Col C)': [
            'เจ้าหน้าที่พัสดุ', 
            'เจ้าหน้าที่บัญชี', 
            'พยาบาลวิชาชีพ', 
            'เจ้าหน้าที่บัญชี', 
            'เภสัชกร/ผู้ช่วย'
        ]
    }
    return pd.DataFrame(data)

# จำลองข้อมูลประเมินความเสี่ยง (Mock Data for Assessment Tab)
def load_risk_mock_data():
    """จำลองข้อมูลความเสี่ยงตามหน่วยงาน"""
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
        # เพิ่มข้อมูลหน่วยงานอื่น ๆ ที่นี่
    }


# --- 2. การจัดการ Session State และข้อมูลเริ่มต้น ---
if 'log_data' not in st.session_state:
    st.session_state.log_data = load_log_data()
    st.session_state.risk_mock_data = load_risk_mock_data()
    st.session_state.edited_log = False


# --- 3. ฟังก์ชันการคำนวณและการแสดงผล ---
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

    # ฟังก์ชันสำหรับจัดรูปแบบตาราง
    return df.style.applymap(
        highlight_risk, 
        subset=['ระดับความเสี่ยง (L x C)']
    )

# --- 4. โครงสร้าง UI หลัก ---

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
    st.info("รายการนี้สามารถแก้ไขได้โดยตรงในตาราง (เหมือนใน Google Sheet) และจะถูกบันทึกไว้ใน Session ของแอปฯ")
    
    current_data = st.session_state.log_data.copy()

    # 4.1 Dropdown กรองข้อมูลตามรหัส
    filter_options = ['--- แสดงทั้งหมด ---'] + current_data['รหัส (Col A)'].unique().tolist()
    selected_id = st.selectbox(
        "กรองข้อมูลตามรหัส (คอลัมน์ A):",
        options=filter_options,
        index=0,
        key="log_filter_select"
    )

    if selected_id != '--- แสดงทั้งหมด ---':
        current_data = current_data[current_data['รหัส (Col A)'] == selected_id]

    # 4.2 ตารางที่แก้ไขได้ (st.data_editor)
    st.markdown("### ตารางขั้นตอนการทำงาน (แก้ไขได้)")
    edited_df = st.data_editor(
        current_data,
        key="log_editor",
        # กำหนดความกว้างของคอลัมน์ที่แก้ไขได้
        column_config={
            "รหัส (Col A)": st.column_config.Column(
                "รหัส (Col A)",
                disabled=True # คอลัมน์รหัสไม่สามารถแก้ไขได้
            ),
            "ขั้นตอนการทำงาน-ลักษณะงาน (Col B)": st.column_config.Column(
                "ขั้นตอนการทำงาน-ลักษณะงาน (Col B)",
                width="large"
            ),
            "ตำแหน่งงาน (Col C)": st.column_config.Column(
                "ตำแหน่งงาน (Col C)",
                width="medium"
            )
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic" # อนุญาตให้เพิ่มแถวใหม่ได้
    )
    
    # 4.3 ตรวจสอบการแก้ไขและปุ่มบันทึก
    if not edited_df.equals(current_data):
        st.session_state.edited_log = True
    else:
        st.session_state.edited_log = False

    def save_log_data_callback():
        # การรวมข้อมูลที่แก้ไขเข้ากับข้อมูลหลัก
        # ต้องจัดการกรณีที่มีการเพิ่มแถวใหม่ด้วย
        
        # 1. ดึงข้อมูลหลักที่ไม่มีการกรอง
        original_data_all = st.session_state.log_data.copy()
        
        # 2. จัดการข้อมูลที่ถูกแก้ไข (edited_df)
        # เนื่องจาก st.data_editor ส่งคืนตารางที่อาจถูกกรองหรือเพิ่มแถว
        
        # 3. อัปเดตเฉพาะแถวที่ถูกแก้ไขในข้อมูลหลัก
        if selected_id == '--- แสดงทั้งหมด ---':
            # ถ้าไม่ได้กรอง: ข้อมูลใน edited_df คือข้อมูลหลักทั้งหมด (พร้อมแถวใหม่)
            st.session_state.log_data = edited_df.dropna(how='all')
        else:
            # ถ้ามีการกรอง: ต้องแทนที่เฉพาะแถวที่ถูกกรองในข้อมูลหลัก
            # (เนื่องจาก Streamlit ไม่ได้ออกแบบมาให้ทำแบบนี้โดยง่าย, เราจะทำแบบง่ายๆ)
            st.session_state.log_data = edited_df.dropna(how='all')
            # หมายเหตุ: ในการใช้งานจริง, ถ้ามีการกรอง, เราควรต้องใช้คีย์ ID เพื่ออัปเดตข้อมูลเดิมใน DB 
            
        st.session_state.edited_log = False
        st.toast("บันทึกข้อมูลขั้นตอนการทำงานเรียบร้อยแล้ว!", icon='✅')
        
    st.button(
        "บันทึกข้อมูล (Update Session State)", 
        on_click=save_log_data_callback,
        disabled=not st.session_state.edited_log,
        type="primary"
    )
    st.caption("ข้อมูลนี้จะถูกบันทึกไว้ชั่วคราวใน Session State จนกว่าแอปฯ จะถูกรีเซ็ต")


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
        # Streamlit ไม่รองรับการแก้ไขตารางที่ใช้ st.dataframe() โดยตรง 
        # ดังนั้น เราจะแสดงเป็นตารางผลลัพธ์ที่คำนวณแล้ว
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
