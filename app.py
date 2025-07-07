import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import jdatetime
import datetime

# تنظیمات Google Sheets
scopes = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

credentials = Credentials.from_service_account_info(
    st.secrets["google_credentials"], scopes=scopes)
gc = gspread.authorize(credentials)

spreadsheet = gc.open("Activity_tracker_Data")
worksheet = spreadsheet.worksheet("Sheet1")

# خواندن داده‌ها و تبدیل به DataFrame
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# تبدیل ستون تاریخ به datetime و مدیریت مقادیر خالی
for col in ["Start Date", "End Date"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# پر کردن ستون‌های احتمالا خالی
for col in ["Status", "Plan"]:
    if col in df.columns:
        df[col] = df[col].fillna("")

if "Duration (days)" in df.columns:
    df["Duration (days)"] = pd.to_numeric(df["Duration (days)"], errors='coerce').fillna(0).astype(int)

if "Physical Progress" in df.columns:
    df["Physical Progress"] = pd.to_numeric(df["Physical Progress"], errors='coerce').fillna(0).astype(int)

# افزودن ستون Edit به ابتدای df
df.insert(0, "Edit", "✏️")

# آماده‌سازی AgGrid
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_selection('single')
gb.configure_column("Edit", editable=False, cellRenderer='''function(params) {
    return '<button class="btn-edit" data-row="'+params.rowIndex+'">Edit</button>'
}''', width=80)
grid_options = gb.build()

st.write(f"👋 Welcome, {st.session_state.get('username', 'User')}")

grid_response = AgGrid(
    df,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.NO_UPDATE,
    allow_unsafe_jscode=True,
    theme='balham',
    fit_columns_on_grid_load=True,
)

selected_rows = grid_response['selected_rows']
if selected_rows:
    selected_row = selected_rows[0]
    row_index = selected_row['_selectedRowNodeInfo']['nodeRowIndex']

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
        st.write("📆 Selected Start (Shamsi):", start_date_shamsi.strftime("%Y/%m/%d"))
        st.write("📆 Selected End (Shamsi):", end_date_shamsi.strftime("%Y/%m/%d"))

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
            df.at[row_index, "Start Date"] = start_date_greg.strftime("%Y-%m-%d")
            df.at[row_index, "End Date"] = end_date_greg.strftime("%Y-%m-%d")
            df.at[row_index, "Duration (days)"] = duration
            df.at[row_index, "Status"] = new_status
            df.at[row_index, "Physical Progress"] = new_progress
            df.at[row_index, "Plan"] = new_plan

            # آپدیت گوگل شیت
            rows_to_save = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()
            worksheet.clear()
            worksheet.update(rows_to_save)

            st.success("✅ Updated successfully!")
            st.rerun()

