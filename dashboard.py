import streamlit as st
import pandas as pd
import plotly.express as px
import database

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
df_raw = database.get_all_expenses()  # Contains both expenses and credits now
df_portfolio = database.get_portfolio()

# Standardize date field up front if data is available
if not df_raw.empty:
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
    # Ensure backward compatibility: if transaction_type column is missing from older rows, default to 'expense'
    if "transaction_type" not in df_raw.columns:
        df_raw["transaction_type"] = "expense"
    else:
        df_raw["transaction_type"] = df_raw["transaction_type"].fillna("expense")

tab_weekly, tab_monthly, tab_yearly, tab_zerodha = st.tabs([
    "🗓️ Weekly Cash Flow", "📅 Monthly Summary", "📊 Yearly Macro Trends", "📈 Zerodha Holdings"
])

# 1. Weekly Cash Flow Tab
with tab_weekly:
    if df_raw.empty:
        st.info("No transaction entries detected.")
    else:
        df_raw["Week"] = df_raw["timestamp"].dt.to_period("W").astype(str)
        
        # Group data by type to give top summary statistics
        expenses_only = df_raw[df_raw["transaction_type"] == "expense"]
        credits_only = df_raw[df_raw["transaction_type"] == "credit"]
        
        total_exp = expenses_only["amount"].sum()
        total_cred = credits_only["amount"].sum()
        net_flow = total_cred - total_exp
        
        # Overview Cards
        w1, w2, w3 = st.columns(3)
        w1.metric("Total Credits (Income)", f"₹{total_cred:,.2f}")
        w2.metric("Total Expenses (Outflows)", f"₹{total_exp:,.2f}")
        w3.metric("Net Cash Flow", f"₹{net_flow:,.2f}", delta=f"₹{net_flow:,.2f}")
        
        st.markdown("---")
        
        # Stacked bar chart showing inflow vs outflow trends per week
        weekly_trend = df_raw.groupby(["Week", "transaction_type"])["amount"].sum().reset_index()
        fig_week = px.bar(
            weekly_trend, 
            x="Week", 
            y="amount", 
            color="transaction_type", 
            barmode="group",
            title="Inflow (Credit) vs Outflow (Expense) Comparison",
            color_discrete_map={"expense": "#EF553B", "credit": "#00CC96"}
        )
        st.plotly_chart(fig_week, use_container_width=True)
        
        # Historical Ledger view with explicit transaction indicator
        st.subheader("Transaction History Ledger")
        st.dataframe(
            df_raw[["timestamp", "transaction_type", "clean_description", "amount", "category"]]
            .sort_values(by="timestamp", ascending=False), 
            use_container_width=True
        )

# 2. Monthly Summary Tab
with tab_monthly:
    if not df_raw.empty:
        df_raw["Month"] = df_raw["timestamp"].dt.to_period("M").astype(str)
        
        selected_month = st.selectbox("Choose Month Partition", options=df_raw["Month"].unique())
        month_data = df_raw[df_raw["Month"] == selected_month]
        
        # Slices for Pie Charts
        m_expenses = month_data[month_data["transaction_type"] == "expense"]
        m_credits = month_data[month_data["transaction_type"] == "credit"]
        
        col_pie1, col_pie2 = st.columns(2)
        
        with col_pie1:
            if not m_expenses.empty:
                monthly_exp_grouped = m_expenses.groupby("category")["amount"].sum().reset_index()
                fig_pie_exp = px.pie(monthly_exp_grouped, values="amount", names="category", hole=0.4, title=f"Expense Allocation: {selected_month}")
                st.plotly_chart(fig_pie_exp, use_container_width=True)
            else:
                st.info("No expenses found for this month partition.")
                
        with col_pie2:
            if not m_credits.empty:
                monthly_cred_grouped = m_credits.groupby("category")["amount"].sum().reset_index()
                fig_pie_cred = px.pie(monthly_cred_grouped, values="amount", names="category", hole=0.4, title=f"Income Allocation: {selected_month}", color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie_cred, use_container_width=True)
            else:
                st.info("No credit streams found for this month partition.")

# 3. Yearly Macro Trends Tab
with tab_yearly:
    if not df_raw.empty:
        df_raw["Month"] = df_raw["timestamp"].dt.to_period("M").astype(str)
        
        # Map separate structural line series for income vs burn rates
        yearly_trends = df_raw.groupby(["Month", "transaction_type"])["amount"].sum().reset_index()
        
        fig_line = px.line(
            yearly_trends, 
            x="Month", 
            y="amount", 
            color="transaction_type",
            title="Monthly Burn Rate vs Income Trajectory Profile", 
            markers=True,
            color_discrete_map={"expense": "#EF553B", "credit": "#00CC96"}
        )
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