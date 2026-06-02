import streamlit as st
import pandas as pd
import plotly.express as px
import Personal_Finance_Tracker.database as database

st.set_page_config(page_title="Personal Capital Engine", layout="wide")
st.title("📱 My Wealth Dashboard")

# --- SIDEBAR: ZERODHA IMPORT ENGINE ---
st.sidebar.header("📁 Upload Portfolio")
uploaded_file = st.sidebar.file_uploader("Upload Zerodha Console Holdings CSV/XLSX", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            portfolio_df = pd.read_csv(uploaded_file)
        else:
            portfolio_df = pd.read_excel(uploaded_file)
        
        portfolio_df.columns = portfolio_df.columns.str.strip().str.lower()
        
        # Target column markers used within Console distributions
        sym_col = next((c for c in ['instrument', 'symbol', 'isin name'] if c in portfolio_df.columns), None)
        qty_col = next((c for c in ['quantity', 'qty', 'available quantity'] if c in portfolio_df.columns), None)
        cost_col = next((c for c in ['average cost', 'avg cost', 'buy price'] if c in portfolio_df.columns), None)
        val_col = next((c for c in ['current value', 'cur value', 'present value'] if c in portfolio_df.columns), None)
        
        if all([sym_col, qty_col, cost_col, val_col]):
            for _, row in portfolio_df.iterrows():
                database.save_portfolio_row(
                    symbol=str(row[sym_col]).upper(),
                    qty=int(row[qty_col]),
                    avg_cost=float(row[cost_col]),
                    curr_val=float(row[val_col])
                )
            st.sidebar.success("Portfolio ledger updated!")
        else:
            st.sidebar.error("CSV Columns do not match required Zerodha template.")
    except Exception as e:
        st.sidebar.error(f"Error handling document parsing sequence: {e}")

# --- PULL RECORDS FOR CHARTS ---
df_raw = database.get_all_expenses()
df_portfolio = database.get_portfolio()

tab_weekly, tab_monthly, tab_yearly, tab_zerodha = st.tabs([
    "🗓️ Weekly Outflows", "📅 Monthly Summary", "📊 Yearly Macro Trends", "📈 Zerodha Holdings"
])

# 1. Weekly Outflows Tab
with tab_weekly:
    if df_raw.empty:
        st.info("No expense entries detected.")
    else:
        df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
        df_raw["Week"] = df_raw["timestamp"].dt.to_period("W").astype(str)
        weekly_df = df_raw.groupby(["Week", "category"])["amount"].sum().reset_index()
        
        fig_week = px.bar(weekly_df, x="Week", y="amount", color="category", title="Outflows Split by Week")
        st.plotly_chart(fig_week, use_container_width=True)
        st.dataframe(df_raw[["timestamp", "clean_description", "amount", "category"]].sort_values(by="timestamp", ascending=False), use_container_width=True)

# 2. Monthly Summary Tab
with tab_monthly:
    if not df_raw.empty:
        df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
        df_raw["Month"] = df_raw["timestamp"].dt.to_period("M").astype(str)
        monthly_df = df_raw.groupby(["Month", "category"])["amount"].sum().reset_index()
        
        selected_month = st.selectbox("Choose Month Partition", options=monthly_df["Month"].unique())
        filtered_month = monthly_df[monthly_df["Month"] == selected_month]
        
        fig_pie = px.pie(filtered_month, values="amount", names="category", hole=0.4, title=f"Allocation Split: {selected_month}")
        st.plotly_chart(fig_pie, use_container_width=True)

# 3. Yearly Macro Trends Tab
with tab_yearly:
    if not df_raw.empty:
        df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
        df_raw["Month"] = df_raw["timestamp"].dt.to_period("M").astype(str)
        yearly_df = df_raw.groupby(["Month"])["amount"].sum().reset_index()
        fig_line = px.line(yearly_df, x="Month", y="amount", title="Burn Rate Trajectory Profile", markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

# 4. Zerodha Performance Tab
with tab_zerodha:
    if df_portfolio.empty:
        st.warning("Please upload a holdings report in the sidebar menu to populate portfolio views.")
    else:
        total_investment = (df_portfolio["quantity"] * df_portfolio["avg_cost"]).sum()
        total_current_value = df_portfolio["current_value"].sum()
        total_pnl = total_current_value - total_investment
        pnl_pct = (total_pnl / total_investment) * 100 if total_investment > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Invested Book Value", f"₹{total_investment:,.2f}")
        c2.metric("Current Portfolio Market Value", f"₹{total_current_value:,.2f}")
        c3.metric("Net Gain / Loss Return Yield", f"₹{total_pnl:,.2f}", f"{pnl_pct:+.2f}%")
        
        fig_tree = px.treemap(df_portfolio, path=["symbol"], values="current_value", title="Asset Weight Distribution Profile")
        st.plotly_chart(fig_tree, use_container_width=True)
        st.dataframe(df_portfolio.sort_values(by="current_value", ascending=False), use_container_width=True)