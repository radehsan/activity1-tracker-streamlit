import streamlit as st
import pandas as pd
import jdatetime
import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# اتصال به Google Sheets
credentials_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)
worksheet = gc.open("Activity-Tracker-Data").worksheet("Sheet1")
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# پیکربندی صفحه
st.set_page_config(page_title="Activity Tracker", layout="wide")
DATE_FORMAT = "%Y/%m/%d"

# دریافت نام کاربر (فقط یکبار)
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

st.markdown("### 🖱 Click '✏️ Edit' to edit an activity")

selected_index = st.session_state.get("selected_index", None)

# نمایش جدول با دکمه ویرایش کنار هر ردیف
for i in range(len(filtered_df)):
    row = filtered_df.loc[i]
    cols = st.columns([8, 1])
    with cols[0]:
        st.markdown(f"**Activity {i+1}:** {row.get('Activity Title', '')}")
        st.markdown(f"📅 Start Date: {row.get('Start Date', '')} | End Date: {row.get('End Date', '')}")
        st.markdown(f"📊 Status: {row.get('Status', '')} | Progress: {row.get('Physical Progress', '')}%")
        st.markdown(f"📝 Plan / Notes: {row.get('Plan', '')}")
    with cols[1]:
        if st.button("✏️ Edit", key=f"edit_button_{i}"):
            selected_index = i
            st.session_state["selected_index"] = i
            st.experimental_rerun()

# اگر ردیفی انتخاب شده بود، فرم ویرایش نمایش داده شود
if selected_index is not None and selected_index < len(filtered_df):
    selected_row = filtered_df.loc[selected_index]
    real_index = selected_row["index"]  # ایندکس اصلی در df

    with st.form("edit_form"):
        st.markdown("### ✏️ Edit Activity")

        # بررسی و مقداردهی پیش‌فرض تاریخ‌ها، در صورت خالی بودن مقدار امروز قرار می‌گیرد
        today_shamsi = jdatetime.date.today()
        today_greg = today_shamsi.togregorian()

        def safe_to_datetime(val):
            if pd.isna(val) or val == "":
                return today_greg
            try:
                return pd.to_datetime(val)
            except:
                return today_greg

        start_date_default = safe_to_datetime(selected_row.get("Start Date", ""))
        end_date_default = safe_to_datetime(selected_row.get("End Date", ""))

        start_date_greg = st.date_input("📅 Start Date (Gregorian)", start_date_default)
        end_date_greg = st.date_input("📅 End Date (Gregorian)", end_date_default)

        start_date_shamsi = jdatetime.date.fromgregorian(date=start_date_greg)
        end_date_shamsi = jdatetime.date.fromgregorian(date=end_date_greg)
        st.write("📆 Selected Start (Shamsi):", start_date_shamsi.strftime(DATE_FORMAT))
        st.write("📆 Selected End (Shamsi):", end_date_shamsi.strftime(DATE_FORMAT))

        duration = (end_date_greg - start_date_greg).days
        if duration < 0:
            st.error("❌ End Date cannot be before Start Date.")
            duration = 0
        st.write("📏 Duration (days):", duration)

        status_options = [
            "Approved with Comments",
            "Approved",
            "Commented",
            "Rejected",
            "Finished"
        ]
        current_status = selected_row.get("Status", "")
        default_index = status_options.index(current_status) if current_status in status_options else 0
        new_status = st.selectbox("🔄 New Status", status_options, index=default_index)

        old_progress = selected_row.get("Physical Progress", 0)
        try:
            old_progress_int = int(old_progress)
        except:
            old_progress_int = 0

        if new_status == "":
            new_progress = 0
        elif new_status == "Commented":
            new_progress = 60
        elif new_status == "Approved with Comments":
            new_progress = 80
        elif new_status == "Finished":
            new_progress = 100
        elif new_status == "Rejected":
            new_progress = old_progress_int
        else:
            new_progress = old_progress_int

        st.write(f"📈 Calculated Physical Progress: **{new_progress}%**")

        current_plan = selected_row.get("Plan", "")
        new_plan = st.text_area("📝 Plan / Notes", value=current_plan)

        submitted = st.form_submit_button("✅ Save Changes")
        if submitted:
            try:
                # به‌روزرسانی داده‌ها در DataFrame اصلی
                df.at[real_index, "Start Date"] = start_date_greg.strftime("%Y-%m-%d")
                df.at[real_index, "End Date"] = end_date_greg.strftime("%Y-%m-%d")
                df.at[real_index, "Duration (days)"] = duration
                df.at[real_index, "Status"] = new_status
                df.at[real_index, "Physical Progress"] = new_progress
                df.at[real_index, "Plan"] = new_plan
                df.at[real_index, "Last Edited"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # آماده‌سازی داده‌ها برای آپدیت سطر در Google Sheets
                updated_row = df.loc[real_index].astype(str).tolist()
                col_count = len(df.columns)
                end_col_letter = chr(65 + col_count - 1)  # تا ستون Z فرض شده
                worksheet.update(f'A{real_index + 2}:{end_col_letter}{real_index + 2}', [updated_row])

                st.success("✅ Row updated successfully!")
                # پاک کردن انتخاب بعد از ذخیره
                del st.session_state["selected_index"]
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Failed to update Google Sheet: {e}")

