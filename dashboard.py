import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import datetime

st.set_page_config(page_title="Sales Dashboard", page_icon="📊", layout="wide")

CHALLENGE_TYPES = ["Race", "Streak", "Marathon", "Weekly Custom", "Journey"]
STATUS_OPTIONS  = ["Demo", "Live", "Not Converted"]
STATUS_COLORS   = {"Live": "#22c55e", "Demo": "#f59e0b", "Not Converted": "#ef4444"}
HEADERS         = ["ID", "Company Name", "Demo Start Date", "Challenge Type", "Status", "Sales Rep", "Notes"]

st.markdown("""
<style>
div[data-testid="stForm"] { background:#1e293b; border-radius:12px; padding:16px; }
</style>
""", unsafe_allow_html=True)

# ── Google Sheets connection ───────────────────────────────────────────────────
@st.cache_resource
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    sh     = client.open_by_key(st.secrets["SHEET_ID"])
    ws     = sh.sheet1
    # Write headers if sheet is empty
    if ws.row_count == 0 or ws.cell(1, 1).value != "ID":
        ws.clear()
        ws.append_row(HEADERS)
    return ws

def fetch_df(ws):
    rows = ws.get_all_records()
    if not rows:
        return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(rows)
    df["Demo Start Date"] = pd.to_datetime(df["Demo Start Date"], errors="coerce")
    return df

def next_id(df):
    return int(df["ID"].max()) + 1 if not df.empty and df["ID"].notna().any() else 1

def find_row(ws, client_id):
    ids = ws.col_values(1)          # column A = ID
    for i, v in enumerate(ids):
        if str(v) == str(client_id):
            return i + 1            # 1-based row index
    return None

# ── Load data ──────────────────────────────────────────────────────────────────
try:
    ws = get_sheet()
    df = fetch_df(ws)
except Exception as e:
    st.error(f"Could not connect to Google Sheets: {e}")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR – Add new client
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("➕ Add New Client")
    with st.form("add_client", clear_on_submit=True):
        company   = st.text_input("Company Name *")
        demo_date = st.date_input("Demo Start Date", value=datetime.date.today())
        challenge = st.selectbox("Challenge Type", CHALLENGE_TYPES)
        status    = st.selectbox("Initial Status", STATUS_OPTIONS)
        sales_rep = st.text_input("Sales Rep")
        notes     = st.text_area("Notes", height=80)
        add_btn   = st.form_submit_button("Add Client", type="primary", use_container_width=True)

    if add_btn:
        if not company.strip():
            st.error("Company Name is required.")
        else:
            new_id = next_id(df)
            ws.append_row([
                new_id,
                company.strip(),
                str(demo_date),
                challenge,
                status,
                sales_rep.strip(),
                notes.strip(),
            ])
            st.success(f"'{company}' added!")
            st.cache_data.clear()
            st.rerun()

    # Filters
    if not df.empty:
        st.markdown("---")
        st.subheader("Filters")
        filter_challenge = st.multiselect("Challenge Type", CHALLENGE_TYPES, default=CHALLENGE_TYPES)
        filter_status    = st.multiselect("Status", STATUS_OPTIONS, default=STATUS_OPTIONS)

# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════
st.title("📊 Sales Demo Dashboard")

if df.empty:
    st.info("No clients yet. Add your first client using the sidebar form.")
    st.stop()

# Apply filters
try:
    df_view = df[
        df["Challenge Type"].isin(filter_challenge) &
        df["Status"].isin(filter_status)
    ]
except NameError:
    df_view = df

# ══════════════════════════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════════════════════════
total    = len(df_view)
live     = (df_view["Status"] == "Live").sum()
not_conv = (df_view["Status"] == "Not Converted").sum()
in_demo  = (df_view["Status"] == "Demo").sum()
conv_pct = live / total * 100 if total else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Clients",    total)
c2.metric("Live (Converted)", live,     f"{conv_pct:.1f}%")
c3.metric("Not Converted",    not_conv, f"{not_conv/total*100:.1f}%" if total else "0%")
c4.metric("In Demo",          in_demo,  f"{in_demo/total*100:.1f}%"  if total else "0%")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# Update Client Status
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("✏️ Update Client Status")

company_map = {
    f"{row['Company Name']} (ID:{row['ID']}) — {row['Status']}": row["ID"]
    for _, row in df.iterrows()
}

selected_label = st.selectbox("Select client to update", list(company_map.keys()))

if selected_label:
    client_id   = company_map[selected_label]
    client_row  = df[df["ID"] == client_id].iloc[0]
    current_idx = STATUS_OPTIONS.index(client_row["Status"]) if client_row["Status"] in STATUS_OPTIONS else 0

    col_s, col_n, col_btn = st.columns([2, 3, 1])
    with col_s:
        new_status = st.selectbox("New Status", STATUS_OPTIONS, index=current_idx, key="upd_status")
    with col_n:
        new_notes = st.text_input("Reason / Notes", placeholder="e.g. Signed contract", key="upd_notes")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        upd_btn = st.button("Update", type="primary", use_container_width=True)

    if upd_btn:
        row_num = find_row(ws, client_id)
        if row_num:
            status_col = HEADERS.index("Status") + 1
            notes_col  = HEADERS.index("Notes") + 1
            ws.update_cell(row_num, status_col, new_status)
            if new_notes:
                old_notes = client_row.get("Notes", "")
                entry     = f"[{datetime.date.today()}] {client_row['Status']}→{new_status}: {new_notes}"
                ws.update_cell(row_num, notes_col, f"{old_notes} | {entry}".strip(" |"))
            st.success(f"Updated to **{new_status}**!")
            st.cache_data.clear()
            st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# Charts
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📈 Analytics")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Overall Conversion Breakdown**")
    counts = df_view["Status"].value_counts().reset_index()
    counts.columns = ["Status", "Count"]
    fig_pie = px.pie(counts, names="Status", values="Count",
                     color="Status", color_discrete_map=STATUS_COLORS, hole=0.45)
    fig_pie.update_traces(textinfo="percent+label", textposition="inside")
    fig_pie.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)

with col_b:
    st.markdown("**Status by Challenge Type**")
    ch_data = df_view.groupby(["Challenge Type","Status"]).size().reset_index(name="Count")
    fig_bar = px.bar(ch_data, x="Challenge Type", y="Count", color="Status",
                     color_discrete_map=STATUS_COLORS, barmode="group", text_auto=True)
    fig_bar.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

col_c, col_d = st.columns(2)

with col_c:
    st.markdown("**Conversion % by Challenge Type**")
    conv_ch = df_view.groupby("Challenge Type").apply(
        lambda x: round((x["Status"] == "Live").sum() / len(x) * 100, 1)
    ).reset_index(name="Conversion %")
    fig_pct = px.bar(conv_ch, x="Challenge Type", y="Conversion %",
                     color="Conversion %",
                     color_continuous_scale=["#ef4444","#f59e0b","#22c55e"],
                     text="Conversion %", range_color=[0, 100])
    fig_pct.update_traces(texttemplate="%{text}%", textposition="outside")
    fig_pct.update_layout(margin=dict(t=10, b=10), coloraxis_showscale=False)
    st.plotly_chart(fig_pct, use_container_width=True)

with col_d:
    st.markdown("**Monthly Demo Trend**")
    if df_view["Demo Start Date"].notna().any():
        df_t = df_view.copy()
        df_t["Month"] = df_t["Demo Start Date"].dt.to_period("M").astype(str)
        monthly = df_t.groupby(["Month","Status"]).size().reset_index(name="Count")
        fig_tr = px.line(monthly, x="Month", y="Count", color="Status",
                         color_discrete_map=STATUS_COLORS, markers=True)
        fig_tr.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig_tr, use_container_width=True)
    else:
        st.info("Add demo dates to see trends.")

# ── Insights ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("💡 Insights")

insights = []
if conv_pct >= 50:
    insights.append(f"Strong conversion at **{conv_pct:.1f}%** — over half of demos are going live.")
elif conv_pct >= 30:
    insights.append(f"Moderate conversion at **{conv_pct:.1f}%** — follow-up or demo pitch may need review.")
else:
    insights.append(f"Low conversion at **{conv_pct:.1f}%** — demo-to-close strategy needs attention.")

if not df_view.empty:
    ch_conv = df_view.groupby("Challenge Type").apply(
        lambda x: (x["Status"] == "Live").sum() / len(x) * 100
    )
    if not ch_conv.empty:
        insights.append(
            f"Best challenge type: **{ch_conv.idxmax()}** ({ch_conv.max():.1f}% live). "
            f"Lowest: **{ch_conv.idxmin()}** ({ch_conv.min():.1f}%)."
        )

if in_demo:
    insights.append(f"**{in_demo}** client(s) still in demo — active pipeline opportunities.")
if total and not_conv / total > 0.4:
    insights.append("High loss rate (>40%) — review notes on not-converted clients for patterns.")

for i in insights:
    st.markdown(f"- {i}")

# ── Client Table ───────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 All Clients")
display = df_view.copy()
display["Demo Start Date"] = display["Demo Start Date"].dt.strftime("%Y-%m-%d")
st.dataframe(display.drop(columns=["ID"], errors="ignore"), use_container_width=True, hide_index=True)

# ── Delete ─────────────────────────────────────────────────────────────────────
with st.expander("🗑️ Delete a client"):
    del_label = st.selectbox("Select client", list(company_map.keys()), key="del_sel")
    if st.button("Delete", type="secondary"):
        row_num = find_row(ws, company_map[del_label])
        if row_num:
            ws.delete_rows(row_num)
            st.success("Deleted.")
            st.cache_data.clear()
            st.rerun()
