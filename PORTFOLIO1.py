import streamlit as st
import pandas as pd
import yfinance as yf
import os
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="LongTerm Tracker Pro", layout="wide", page_icon="📈")

# --- Custom Styling (Thin Black Lines, Bold Red Headers, Blue Bold Total Row) ---
st.markdown("""
    <style>
    /* Monitor Table Frame */
    [data-testid="stTable"] {
        border: 1px solid #000000 !important;
        margin-top: 20px;
    }
    /* Headers: Bold Red with Dark Grid */
    [data-testid="stTable"] thead tr th {
        color: #FF0000 !important;
        font-weight: bold !important;
        text-transform: uppercase;
        border: 1px solid #000000 !important;
        background-color: #f9f9f9 !important;
        text-align: center !important;
    }
    /* Data Cells: Thin Black Lines */
    [data-testid="stTable"] tbody td {
        border: 1px solid #000000 !important;
        color: #000000 !important;
        text-align: center !important;
        padding: 8px !important;
    }
    /* GRAND TOTAL ROW: Force Blue Font, Bold, and Grey Background */
    [data-testid="stTable"] tbody tr:last-child td {
        font-weight: 900 !important;
        color: #0000FF !important; /* Blue Font */
        background-color: #eeeeee !important;
        border-top: 2px solid #000000 !important;
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
                st.error("No data found. Check your tickers.")
                st.stop()

            tab1, tab2, tab3 = st.tabs(["📊 Monitor", "📉 Allocation", "⚙️ Manage"])

            with tab1:
                display_list = []
                grand_total_val = 0.0
                
                for idx, ticker in enumerate(tickers, start=1):
                    # Handle single vs multi ticker dataframe shape
                    df_t = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
                    
                    if not df_t.empty and 'Close' in df_t.columns:
                        ema_200 = df_t['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                        curr_p = float(df_t['Close'].iloc[-1])
                        high_52 = float(df_t['Close'].tail(252).max())
                        qty = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == ticker, 'Qty'].values[0])
                        
                        row_value = qty * curr_p
                        grand_total_val += row_value
                        
                        display_list.append({
                            "Sl. No.": str(idx),
                            "Stock": ticker.replace(".NS", ""),
                            "Trend": "🟢 Bull" if curr_p > ema_200 else "🔴 Bear",
                            "Price": f"₹{curr_p:,.2f}",
                            "52W High Gap": f"{round(((curr_p - high_52) / high_52 * 100), 1)}%",
                            "Value": f"₹{int(row_value):,}"
                        })
                
                if display_list:
                    # Create the Grand Total row
                    total_row = {
                        "Sl. No.": "",
                        "Stock": "GRAND TOTAL",
                        "Trend": "",
                        "Price": "",
                        "52W High Gap": "",
                        "Value": f"₹{int(grand_total_val):,}"
                    }
                    df_display = pd.DataFrame(display_list)
                    df_display = pd.concat([df_display, pd.DataFrame([total_row])], ignore_index=True)
                    
                    st.table(df_display)

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
                st.subheader("Edit Portfolio")
                new_df = st.data_editor(st.session_state.df_portfolio, use_container_width=True, hide_index=True)
                if st.button("💾 Save Changes"):
                    st.session_state.df_portfolio = save_data(new_df)
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Sync Error: {str(e)}")
else:
    st.info("Portfolio is empty. Add a stock symbol above to begin.")