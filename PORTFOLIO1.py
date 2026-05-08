import streamlit as st
import pandas as pd
import yfinance as yf
import os
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="LongTerm Tracker Pro", layout="wide", page_icon="📈")

# --- Custom Styling (Bold Red Headers & Thin Dark Black Lines) ---
st.markdown("""
    <style>
    /* Monitor Table Styling */
    [data-testid="stTable"] {
        border: 1px solid #000000 !important;
        margin-top: 20px;
    }
    [data-testid="stTable"] thead tr th {
        color: #FF0000 !important;
        font-weight: bold !important;
        border: 1px solid #000000 !important;
        background-color: #f9f9f9 !important;
    }
    [data-testid="stTable"] tbody td {
        border: 1px solid #000000 !important;
        color: #000000 !important;
    }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- Storage Logic ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "portfolio_data.csv")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                return df.sort_values(by="Ticker").reset_index(drop=True)
        except:
            pass
    return pd.DataFrame(columns=["Ticker", "Qty"])

def save_data(df):
    df = df.sort_values(by="Ticker").reset_index(drop=True)
    df.to_csv(DB_FILE, index=False)
    return df

if 'df_portfolio' not in st.session_state:
    st.session_state.df_portfolio = load_data()

# 2. HEADER & ADD SECTION
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
                # Fixes Sync Error: Ensure .NS suffix for Indian stocks
                ticker = new_tk if new_tk.endswith(".NS") else f"{new_tk}.NS"
                new_row = pd.DataFrame([{"Ticker": ticker, "Qty": new_qty}])
                updated_df = pd.concat([st.session_state.df_portfolio, new_row]).drop_duplicates('Ticker', keep='last')
                st.session_state.df_portfolio = save_data(updated_df)
                st.rerun()

st.markdown("---")

# 3. DATA PROCESSING
if not st.session_state.df_portfolio.empty:
    tickers = st.session_state.df_portfolio['Ticker'].tolist()
    
    with st.spinner('Syncing Market Data...'):
        try:
            data = yf.download(tickers, period="2y", interval="1d", group_by='ticker', auto_adjust=True, progress=False)
            
            if data.empty:
                st.error("No data found.")
                st.stop()

            tab1, tab2, tab3 = st.tabs(["📊 Monitor", "📉 Allocation", "⚙️ Manage"])

            with tab1:
                display_list = []
                for ticker in tickers:
                    # Robust data extraction for single or multiple tickers
                    df_t = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
                    
                    if not df_t.empty and 'Close' in df_t.columns:
                        ema_200 = df_t['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                        curr_p = float(df_t['Close'].iloc[-1])
                        high_52 = float(df_t['Close'].tail(252).max())
                        qty = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == ticker, 'Qty'].values[0])
                        
                        display_list.append({
                            "Stock": ticker.replace(".NS", ""),
                            "Trend": "🟢 Bull" if curr_p > ema_200 else "🔴 Bear",
                            "Price": f"₹{curr_p:,.2f}",
                            "52W High Gap": f"{round(((curr_p - high_52) / high_52 * 100), 1)}%",
                            "Total Value": f"₹{int(qty * curr_p):,}"
                        })
                
                if display_list:
                    st.table(pd.DataFrame(display_list))

            with tab2:
                plot_data = []
                for t in tickers:
                    df_p = data[t].dropna() if len(tickers) > 1 else data.dropna()
                    if not df_p.empty:
                        q = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == t, 'Qty'].values[0])
                        plot_data.append({"Ticker": t.replace(".NS",""), "Value": q * float(df_p['Close'].iloc[-1])})
                
                if plot_data:
                    fig = px.pie(pd.DataFrame(plot_data), values='Value', names='Ticker', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)

            with tab3:
                st.subheader("Manage Holdings")
                new_df = st.data_editor(st.session_state.df_portfolio, use_container_width=True, hide_index=True)
                if st.button("💾 Save Changes"):
                    st.session_state.df_portfolio = save_data(new_df)
                    st.success("Changes Saved!")
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Sync Error: {str(e)}")
else:
    st.info("Portfolio is empty. Add a stock to begin.")