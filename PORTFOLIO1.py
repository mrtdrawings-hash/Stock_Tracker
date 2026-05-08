import streamlit as st
import pandas as pd
import yfinance as yf
import os
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="LongTerm Tracker Pro", layout="wide", page_icon="📈")

# --- Storage Logic ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "portfolio_data.csv")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                # Sort A-Z on load
                return df.sort_values(by="Ticker").reset_index(drop=True)
        except:
            pass
    return pd.DataFrame(columns=["Ticker", "Qty"])

def save_data(df):
    # Sort A-Z before saving
    df = df.sort_values(by="Ticker").reset_index(drop=True)
    df.to_csv(DB_FILE, index=False)
    return df

# Initialize Session States
if 'df_portfolio' not in st.session_state:
    st.session_state.df_portfolio = load_data()

if 'confirm_delete_ticker' not in st.session_state:
    st.session_state.confirm_delete_ticker = None

# --- Custom Styling ---
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    hr { margin: 10px 0px !important; opacity: 0.3; }
    </style>
    """, unsafe_allow_html=True)

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
    # Ensure sorted order for the display loop
    st.session_state.df_portfolio = st.session_state.df_portfolio.sort_values(by="Ticker")
    tickers = st.session_state.df_portfolio['Ticker'].tolist()
    
    with st.spinner('Syncing Market Data...'):
        try:
            data = yf.download(tickers, period="2y", interval="1d", group_by='ticker', auto_adjust=True, progress=False)
            
            if data.empty:
                st.error("No data found for these tickers.")
                st.stop()

            tab1, tab2, tab3 = st.tabs(["📊 Monitor", "📉 Allocation", "⚙️ Manage"])

            with tab1:
                for ticker in tickers:
                    df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
                    if df.empty: continue
                    
                    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
                    curr_p = float(df['Close'].iloc[-1])
                    prev_p = float(df['Close'].iloc[-2])
                    ema_v = float(df['EMA_200'].iloc[-1])
                    high_52 = float(df['Close'].tail(252).max())
                    dd = ((curr_p - high_52) / high_52 * 100)
                    
                    col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.2, 1.2, 0.6])
                    
                    with col1:
                        status = "🟢" if curr_p > ema_v else "🔴"
                        st.markdown(f"#### {ticker.replace('.NS','')}")
                        st.caption(f"Trend: {'Bullish' if status == '🟢' else 'Bearish'} {status}")
                        
                    with col2:
                        st.metric("Price", f"₹{curr_p:,.1f}", f"{curr_p - prev_p:,.1f}")
                    
                    with col3:
                        st.metric("v 52W High", f"{dd:.1f}%")
                    
                    with col4:
                        row = st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == ticker]
                        qty = float(row['Qty'].values[0]) if not row.empty else 0
                        st.metric("Value", f"₹{(qty * curr_p):,.0f}")

                    with col5:
                        if st.session_state.confirm_delete_ticker != ticker:
                            if st.button("❌", key=f"btn_{ticker}"):
                                st.session_state.confirm_delete_ticker = ticker
                                st.rerun()
                        else:
                            if st.button("✔", key=f"y_{ticker}"):
                                st.session_state.df_portfolio = st.session_state.df_portfolio[st.session_state.df_portfolio['Ticker'] != ticker]
                                save_data(st.session_state.df_portfolio)
                                st.session_state.confirm_delete_ticker = None
                                st.rerun()
                            if st.button("✖", key=f"n_{ticker}"):
                                st.session_state.confirm_delete_ticker = None
                                st.rerun()
                    st.markdown("<hr>", unsafe_allow_html=True)

            with tab2:
                plot_data = []
                for t in tickers:
                    df_t = data[t].dropna() if len(tickers) > 1 else data.dropna()
                    if not df_t.empty:
                        q = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == t, 'Qty'].values[0])
                        plot_data.append({"Ticker": t.replace(".NS",""), "Value": q * float(df_t['Close'].iloc[-1])})
                
                if plot_data:
                    pdf = pd.DataFrame(plot_data)
                    fig = px.pie(pdf, values='Value', names='Ticker', hole=0.4, title="Portfolio Weightage")
                    st.plotly_chart(fig, use_container_width=True)

            with tab3:
                st.subheader("Holdings Management")
                new_df = st.data_editor(st.session_state.df_portfolio, use_container_width=True, hide_index=True)
                if st.button("💾 Save Changes"):
                    st.session_state.df_portfolio = save_data(new_df)
                    st.success("Saved and Sorted A-Z!")
                    st.rerun()
                
                if st.button("🗑️ Wipe All Data", type="primary"):
                    st.session_state.df_portfolio = pd.DataFrame(columns=["Ticker", "Qty"])
                    save_data(st.session_state.df_portfolio)
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Analysis Error: {str(e)}")
else:
    st.info("Portfolio is empty. Add a stock to begin.")