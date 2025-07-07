if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.username:
    st.session_state.username = st.text_input("👤 Please enter your name to continue:", key="username_input")
    if not st.session_state.username:
        st.stop()

user = st.session_state.username
st.write(f"👋 Welcome, **{user}**")
import streamlit as st
import pandas as pd
import jdatetime
import datetime
import os
import getpass

st.set_page_config(page_title="Activity Tracker", layout="wide")

EXCEL_FILE = "data.xlsx"  # اگر بعداً به Google Sheets منتقل شد، این بخش حذف می‌شود
DATE_FORMAT = "%Y/%m/%d"

st.title("📋 Activity Tracking System")

# Load Excel
if os.path.exists(EXCEL_FILE):
    df = pd.read_excel(EXCEL_FILE)
else:
    st.error("❌ Excel file 'data.xlsx' not found.")
    st.stop()

# گرفتن اسم یوزر از سیستم
user = st.text_input("Enter your name:", value=getpass.getuser())
if not user:
    st.stop()

# فیلتر بر اساس دیسیپلین
discipline = st.selectbox("Select your discipline", sorted(df["Discipline"].dropna().unique()))
filtered_df = df[df["Discipline"] == discipline].copy()
filtered_df.reset_index(inplace=True)

st.markdown("### 🖱 Click a row to edit")

# نمایش داده‌ها فقط برای مشاهده
st.dataframe(filtered_df.drop(columns="index"), use_container_width=True)

# انتخاب ردیف برای ویرایش
row_index = st.selectbox("✏️ Select a row to edit:", options=filtered_df.index, format_func=lambda x: f"{filtered_df.loc[x, 'Activity Title']}")
selected_row = filtered_df.loc[row_index]
real_index = selected_row["index"]

with st.form("edit_form"):
    st.markdown("### ✏️ Edit Activity")

    today_shamsi = jdatetime.date.today()
    today_greg = today_shamsi.togregorian()

    start_date_default = selected_row["Start Date"] if pd.notna(selected_row["Start Date"]) else today_greg
    end_date_default = selected_row["End Date"] if pd.notna(selected_row["End Date"]) else today_greg

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
    if pd.isna(current_status) or current_status not in status_options:
        default_index = status_options.index("Approved")
    else:
        default_index = status_options.index(current_status)

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
        df.at[real_index, "Start Date"] = start_date_greg
        df.at[real_index, "End Date"] = end_date_greg
        df.at[real_index, "Duration (days)"] = duration
        df.at[real_index, "Status"] = new_status
        df.at[real_index, "Physical Progress"] = new_progress
        df.at[real_index, "Plan"] = new_plan
        df.to_excel(EXCEL_FILE, index=False)
        st.success("✅ Updated successfully!")
