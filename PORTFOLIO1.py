import streamlit as st
import pandas as pd
import yfinance as yf
import os
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="LongTerm Tracker Pro", layout="wide", page_icon="📈")

# --- Custom Styling (Dark Grid + Blue Bold Totals) ---
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
    /* GRAND TOTAL ROW: Blue Font + Bold */
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

def save_data(df):
    df.to_csv(DB_FILE, index=False)
    return df

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
                st.session_state.df_portfolio = pd.concat([st.session_state.df_portfolio, new_row]).drop_duplicates('Ticker', keep='last')
                save_data(st.session_state.df_portfolio)
                st.rerun()

st.markdown("---")

# 3. DATA PROCESSING
if not st.session_state.df_portfolio.empty:
    tickers = st.session_state.df_portfolio['Ticker'].tolist()
    
    with st.spinner('Updating CMP and Industry Data...'):
        try:
            # Fetch data
            data = yf.download(tickers, period="1y", group_by='ticker', progress=False)
            
            display_list = []
            grand_total_val = 0.0
            
            for idx, ticker in enumerate(tickers, start=1):
                df_t = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
                
                if not df_t.empty and 'Close' in df_t.columns:
                    curr_p = float(df_t['Close'].iloc[-1])
                    ema_200 = df_t['Close'].ewm(span=200).mean().iloc[-1]
                    
                    # RSI Calculation
                    delta = df_t['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs.iloc[-1]))
                    
                    # Valuation
                    info = yf.Ticker(ticker).info
                    stock_pe = info.get('trailingPE', 'N/A')
                    ind_pe = info.get('industryAverage', 'N/A')
                    
                    stock_pe = round(stock_pe, 1) if isinstance(stock_pe, (int, float)) else "N/A"
                    ind_pe = round(ind_pe, 1) if isinstance(ind_pe, (int, float)) else "N/A"

                    qty = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == ticker, 'Qty'].values[0])
                    row_value = qty * curr_p
                    grand_total_val += row_value
                    
                    display_list.append({
                        "Sl. No.": str(idx),
                        "Stock": ticker.replace(".NS", ""),
                        "Trend": "🟢 Bull" if curr_p > ema_200 else "🔴 Bear",
                        "CMP": f"₹{curr_p:,.2f}", # Changed Header to CMP
                        "RSI": f"{round(rsi, 1)}",
                        "Stock P/E": f"{stock_pe}",
                        "Ind. P/E": f"{ind_pe}",
                        "Value": f"₹{int(row_value):,}"
                    })
            
            tab1, tab2, tab3 = st.tabs(["📊 Monitor", "📉 Allocation", "⚙️ Manage"])
            
            with tab1:
                total_row = {
                    "Sl. No.": "", "Stock": "GRAND TOTAL", "Trend": "", 
                    "CMP": "", "RSI": "", "Stock P/E": "", "Ind. P/E": "", 
                    "Value": f"₹{int(grand_total_val):,}"
                }
                st.table(pd.concat([pd.DataFrame(display_list), pd.DataFrame([total_row])], ignore_index=True))

            with tab2:
                plot_data = [{"Ticker": d["Stock"], "Value": int(d["Value"].replace('₹','').replace(',',''))} for d in display_list]
                st.plotly_chart(px.pie(pd.DataFrame(plot_data), values='Value', names='Ticker', hole=0.4), use_container_width=True)

            with tab3:
                new_df = st.data_editor(st.session_state.df_portfolio, use_container_width=True, hide_index=True)
                if st.button("💾 Save Changes"):
                    st.session_state.df_portfolio = save_data(new_df)
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Sync Error: {str(e)}")
else:
    st.info("Portfolio is empty.")