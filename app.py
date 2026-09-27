import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

st.set_page_config(page_title="极简记账", layout="centered")

st.markdown("""
<style>
    .block-container {padding: 1rem !important; max-width: 480px;}
    div[data-testid="stMetricValue"] {font-size: 1.4rem;}
    .stButton>button {width: 100%;}
</style>
""", unsafe_allow_html=True)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_gsheet_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_sheet():
    client = get_gsheet_client()
    url = st.secrets["gsheet"]["spreadsheet_url"]
    worksheet_name = st.secrets["gsheet"]["worksheet_name"]
    return client.open_by_url(url).worksheet(worksheet_name)


def load_records():
    sheet = get_sheet()
    rows = sheet.get_all_records()
    records = []
    for r in rows:
        records.append({
            "id": int(r["id"]),
            "type": r["type"],
            "amount": float(r["amount"]),
            "description": r["description"],
            "date": r["date"],
        })
    return records


def get_next_id(records):
    if not records:
        return 1
    return max(r["id"] for r in records) + 1


def add_record(type_, amount, description):
    sheet = get_sheet()
    records = load_records()
    new_id = get_next_id(records)
    desc = description or ("支出" if type_ == "expense" else "收入")
    sheet.append_row([new_id, type_, float(amount), desc, date.today().isoformat()])


def delete_record(record_id):
    sheet = get_sheet()
    records = load_records()
    for i, r in enumerate(records, start=2):
        if r["id"] == record_id:
            sheet.delete_rows(i)
            return


def calc_balance(records, month_only=False):
    balance = 0
    today = date.today()
    for r in records:
        d = date.fromisoformat(r["date"])
        if month_only and (d.month != today.month or d.year != today.year):
            continue
        balance += r["amount"] if r["type"] == "income" else -r["amount"]
    return balance


records = load_records()

st.title("💰 极简记账")

col1, col2 = st.columns([1, 2])
with col1:
    expense_amount = st.number_input("支出", min_value=0.0, step=1.0, format="%.2f", key="exp_amt")
with col2:
    expense_desc = st.text_input("描述", key="exp_desc", placeholder="吃饭、交通...")

col3, col4 = st.columns([1, 2])
with col3:
    income_amount = st.number_input("收入", min_value=0.0, step=1.0, format="%.2f", key="inc_amt")
with col4:
    income_desc = st.text_input("描述", key="inc_desc", placeholder="工资、红包...")

if st.button("保存", use_container_width=True, type="primary"):
    added = False
    if expense_amount > 0:
        add_record("expense", expense_amount, expense_desc)
        added = True
    if income_amount > 0:
        add_record("income", income_amount, income_desc)
        added = True
    if added:
        st.success("已保存")
        st.cache_resource.clear()
        st.rerun()
    else:
        st.warning("请至少填写一项金额")

records = load_records()
month_bal = calc_balance(records, month_only=True)
total_bal = calc_balance(records, month_only=False)

col_m, col_t = st.columns(2)
col_m.metric("月收支", f"¥{month_bal:.2f}")
col_t.metric("总收支", f"¥{total_bal:.2f}")

with st.expander("📋 明细", expanded=False):
    if not records:
        st.info("暂无记录")
    else:
        for r in reversed(records):
            cols = st.columns([3, 2, 0.5])
            with cols[0]:
                st.write(f"{r['date']} · {r['description']}")
            with cols[1]:
                sign = "+" if r["type"] == "income" else "-"
                color = "green" if r["type"] == "income" else "red"
                st.markdown(
                    f"<span style='color:{color};font-weight:bold'>{sign}¥{r['amount']:.2f}</span>",
                    unsafe_allow_html=True,
                )
            with cols[2]:
                if st.button("×", key=f"del_{r['id']}"):
                    delete_record(r["id"])
                    st.cache_resource.clear()
                    st.rerun()