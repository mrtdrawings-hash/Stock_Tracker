import streamlit as st
import pandas as pd
import yfinance as yf
import os
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="LongTerm Tracker Pro", layout="wide", page_icon="📈")

# --- Custom Styling ---
st.markdown("""
    <style>
    [data-testid="stTable"] { border: 1px solid #000000 !important; margin-top: 20px; }
    [data-testid="stTable"] thead tr th {
        color: #FF0000 !important; font-weight: bold !important;
        border: 1px solid #000000 !important; background-color: #f9f9f9 !important;
        text-align: center !important;
    }
    [data-testid="stTable"] tbody td {
        border: 1px solid #000000 !important; color: #000000 !important;
        text-align: center !important; padding: 8px !important;
    }
    [data-testid="stTable"] tbody tr:last-child td {
        color: #00008B !important; font-weight: 900 !important;
        background-color: #eeeeee !important; border-top: 2px solid #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Storage Logic ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "portfolio_data.csv")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            return df.sort_values(by="Ticker").reset_index(drop=True)
        except: pass
    return pd.DataFrame(columns=["Ticker", "Qty"])

def save_and_sort_data(df):
    df_sorted = df.sort_values(by="Ticker").reset_index(drop=True)
    df_sorted.to_csv(DB_FILE, index=False)
    return df_sorted

if 'df_portfolio' not in st.session_state:
    st.session_state.df_portfolio = load_data()

# 2. HEADER
st.title("📈 Long-Term Portfolio Analytics")

with st.expander("➕ Add New Asset", expanded=st.session_state.df_portfolio.empty):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        new_tk = st.text_input("Ticker Symbol", placeholder="e.g. RELIANCE").upper().strip()
    with c2:
        new_qty = st.number_input("Quantity", min_value=0.0, step=1.0, value=1.0)
    with c3:
        st.write("##")
        if st.button("Add to Portfolio", use_container_width=True):
            if new_tk:
                ticker = new_tk if new_tk.endswith(".NS") else f"{new_tk}.NS"
                new_row = pd.DataFrame([{"Ticker": ticker, "Qty": new_qty}])
                combined_df = pd.concat([st.session_state.df_portfolio, new_row]).drop_duplicates('Ticker', keep='last')
                st.session_state.df_portfolio = save_and_sort_data(combined_df)
                st.rerun()

st.markdown("---")

# 3. MAIN LOGIC
if not st.session_state.df_portfolio.empty:
    tickers = st.session_state.df_portfolio['Ticker'].tolist()
    
    with st.spinner('Analyzing Market Data & Fundamentals...'):
        try:
            # Download Price Data for Monitor/52W
            data = yf.download(tickers, period="1y", group_by='ticker', progress=False)
            
            monitor_list = []
            fifty_two_list = []
            fundamental_list = []
            quarterly_list = []
            grand_total_val = 0.0
            
            for idx, ticker in enumerate(tickers, start=1):
                df_t = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
                clean_name = ticker.replace(".NS", "")
                
                if not df_t.empty:
                    # 1. Price Metrics
                    curr_p = float(df_t['Close'].iloc[-1])
                    prev_p = float(df_t['Close'].iloc[-2]) if len(df_t) > 1 else curr_p
                    day_chg = ((curr_p - prev_p) / prev_p) * 100
                    
                    # 2. Techs
                    ema_200 = df_t['Close'].ewm(span=200).mean().iloc[-1]
                    delta = df_t['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
                    rsi = 100 - (100 / (1 + (gain / loss))) if loss != 0 else 50
                    
                    # 3. Fetch Ticker Object for Fundamentals
                    stock_obj = yf.Ticker(ticker)
                    info = stock_obj.info
                    
                    # Portfolio Calc
                    qty = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == ticker, 'Qty'].values[0])
                    val = qty * curr_p
                    grand_total_val += val
                    
                    # --- TAB DATA POPULATION ---
                    
                    # Monitor Tab
                    monitor_list.append({
                        "Sl. No.": str(idx),
                        "Stock": clean_name,
                        "Day Change": f"{'🟢' if day_chg >= 0 else '🔴'} {day_chg:.2f}%",
                        "CMP": f"₹{curr_p:,.2f}",
                        "Trend": "🟢 Bull" if curr_p > ema_200 else "🔴 Bear",
                        "RSI": f"{int(rsi)}",
                        "Value": f"₹{int(val):,}"
                    })
                    
                    # Fundamental Tab
                    mkt_cap_cr = (info.get('marketCap', 0) or 0) / 10**7
                    fundamental_list.append({
                        "Stock": clean_name,
                        "Market Cap": f"₹{mkt_cap_cr:,.0f} Cr",
                        "P/E Ratio": info.get('trailingPE', 'N/A'),
                        "P/B Ratio": info.get('priceToBook', 'N/A'),
                        "Debt/Equity": info.get('debtToEquity', 'N/A'),
                        "Div. Yield": f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "0.00%",
                        "ROE": f"{info.get('returnOnEquity', 0)*100:.1f}%" if info.get('returnOnEquity') else "N/A"
                    })

                    # 52W Tab
                    fifty_two_list.append({
                        "Stock": clean_name,
                        "52W High": f"₹{df_t['High'].max():,.2f}",
                        "52W Low": f"₹{df_t['Low'].min():,.2f}",
                        "From High": f"{((curr_p / df_t['High'].max()) - 1) * 100:.1f}%"
                    })

                    # Quarterly Tab (Simple Net Income)
                    q_fin = stock_obj.quarterly_financials
                    q_prof = "N/A"
                    if not q_fin.empty and 'Net Income' in q_fin.index:
                        q_prof = f"₹{q_fin.loc['Net Income'].iloc[0]/10**7:.1f} Cr"
                    
                    quarterly_list.append({
                        "Stock": clean_name,
                        "Quarter": q_fin.columns[0].strftime('%b %Y') if not q_fin.empty else "N/A",
                        "Net Profit (Q)": q_prof
                    })

            # 4. TABS UI
            tabs = st.tabs(["📊 Monitor", "🏛️ Fundamentals", "📑 Quarterly", "🏔️ 52W Range", "📉 Allocation", "⚙️ Manage"])
            
            with tabs[0]: # Monitor
                st.metric("Total Portfolio Value", f"₹{grand_total_val:,.2f}")
                total_row = {"Sl. No.": "", "Stock": "GRAND TOTAL", "Day Change": "", "CMP": "", "Trend": "", "RSI": "", "Value": f"₹{int(grand_total_val):,}"}
                st.table(pd.concat([pd.DataFrame(monitor_list), pd.DataFrame([total_row])], ignore_index=True))

            with tabs[1]: # Fundamentals
                st.subheader("Key Fundamental Ratios")
                st.table(pd.DataFrame(fundamental_list))

            with tabs[2]: # Quarterly
                st.table(pd.DataFrame(quarterly_list))

            with tabs[3]: # 52W
                st.table(pd.DataFrame(fifty_two_list))

            with tabs[4]: # Allocation
                plot_df = pd.DataFrame([{"T": d["Stock"], "V": int(d["Value"].replace('₹','').replace(',',''))} for d in monitor_list])
                st.plotly_chart(px.pie(plot_df, values='V', names='T', hole=0.4), use_container_width=True)

            with tabs[5]: # Manage
                stock_to_del = st.selectbox("Select to Delete", options=tickers, index=None)
                if st.button("Delete Selected"):
                    if stock_to_del:
                        st.session_state.df_portfolio = save_and_sort_data(st.session_state.df_portfolio[st.session_state.df_portfolio['Ticker'] != stock_to_del])
                        st.rerun()
                st.divider()
                edited_df = st.data_editor(st.session_state.df_portfolio, use_container_width=True, num_rows="dynamic")
                if st.button("💾 Save All Changes"):
                    st.session_state.df_portfolio = save_and_sort_data(edited_df)
                    st.rerun()

        except Exception as e:
            st.error(f"Error fetching data: {e}")
else:
    st.info("Your portfolio is empty.")