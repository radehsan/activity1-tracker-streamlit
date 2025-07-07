import streamlit as st
import pandas as pd
import jdatetime
import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# بارگذاری اعتبارنامه از متغیر محیطی (یا می‌تونی مستقیم فایل بخونی)
credentials_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

# تعیین دسترسی‌ها
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ساخت Credentials و احراز هویت
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)

# اتصال به Google Sheets
gc = gspread.authorize(credentials)
worksheet = gc.open("Activity_Tracker_Data").worksheet("Sheet1")

# دریافت داده‌ها از شیت و تبدیل به DataFrame
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# تنظیمات استریم‌لیت
st.set_page_config(page_title="Activity Tracker", layout="wide")
DATE_FORMAT = "%Y/%m/%d"

# دریافت نام کاربر
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.username:
    st.session_state.username = st.text_input("👤 Please enter your name to continue:", key="username_input")
    if not st.session_state.username:
        st.stop()

user = st.session_state.username
st.write(f"👋 Welcome, **{user}**")

# فیلتر بر اساس دیسیپلین
discipline = st.selectbox("Select your discipline", sorted(df["Discipline"].dropna().unique()))
filtered_df = df[df["Discipline"] == discipline].reset_index()

st.markdown("### 🖱 Click a row to edit")

# نمایش جدول و انتخاب ردیف جهت ویرایش
edited_df = st.data_editor(
    filtered_df,
    use_container_width=True,
    num_rows="dynamic",
    disabled=True,
    hide_index=True,
    key="row_selector",
)

selected_index = st.session_state.get("selected_index")

# دکمه ویرایش برای هر ردیف
for i in range(len(filtered_df)):
    if st.button(f"✏️ Edit row {i+1}", key=f"edit_button_{i}"):
        selected_index = i
        st.session_state["selected_index"] = i
        break

if selected_index is not None:
    selected_row = filtered_df.loc[selected_index]
    real_index = selected_row["index"]

    with st.form("edit_form"):
        st.markdown("### ✏️ Edit Activity")

        today_shamsi = jdatetime.date.today()
        today_greg = today_shamsi.togregorian()

        start_date_default = pd.to_datetime(selected_row["Start Date"]) if pd.notna(selected_row["Start Date"]) else today_greg
        end_date_default = pd.to_datetime(selected_row["End Date"]) if pd.notna(selected_row["End Date"]) else today_greg

        start_date_greg = st.date_input("📅 Start Date (Shamsi)", start_date_default)
        end_date_greg = st.date_input("📅 End Date (Shamsi)", end_date_default)

        start_date_shamsi = jdatetime.date.fromgregorian(date=start_date_greg)
        end_date_shamsi = jdatetime.date.fromgregorian(date=end_date_greg)
        st.write("📆 Selected Start (Shamsi):", start_date_shamsi.strftime(DATE_FORMAT))
        st.write("📆 Selected End (Shamsi):", end_date_shamsi.strftime(DATE_FORMAT))

        duration = (end_date_greg - start_date_greg).days
        st.write("📏 Duration (days):", duration)

        status_options = [
            "Approved with Comments",
            "Approved",
            "Commented",
            "Rejected",
            "Finished"
        ]
        current_status = selected_row["Status"]
        default_index = status_options.index(current_status) if current_status in status_options else 0
        new_status = st.selectbox("🔄 New Status", status_options, index=default_index)

        old_progress = selected_row["Physical Progress"]
        if pd.isna(old_progress):
            old_progress = 0

        if new_status == "":
            new_progress = 0
        elif new_status == "Commented":
            new_progress = 60
        elif new_status == "Approved with Comments":
            new_progress = 80
        elif new_status == "Finished":
            new_progress = 100
        elif new_status == "Rejected":
            new_progress = int(old_progress)
        else:
            new_progress = int(old_progress)

        st.write(f"📈 Calculated Physical Progress: **{new_progress}%**")

        current_plan = selected_row["Plan"] if "Plan" in selected_row and pd.notna(selected_row["Plan"]) else ""
        new_plan = st.text_area("📝 Plan / Notes", value=current_plan)

        submitted = st.form_submit_button("✅ Save Changes")
        if submitted:
            try:
                # بروزرسانی در DataFrame
                df.at[real_index, "Start Date"] = start_date_greg
                df.at[real_index, "End Date"] = end_date_greg
                df.at[real_index, "Duration (days)"] = duration
                df.at[real_index, "Status"] = new_status
                df.at[real_index, "Physical Progress"] = new_progress
                df.at[real_index, "Plan"] = new_plan
                df.at[real_index, "Last Edited"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # آپدیت ردیف مربوطه در Google Sheets
                updated_row = df.loc[real_index].astype(str).tolist()
                col_count = len(df.columns)
                end_col_letter = chr(65 + col_count - 1)  # فرض شده ستون‌ها تا Z باشند
                worksheet.update(f'A{real_index + 2}:{end_col_letter}{real_index + 2}', [updated_row])

                st.success("✅ Row updated successfully!")
            except Exception as e:
                st.error(f"❌ Failed to update Google Sheet: {e}")
