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
st.title("📈 Portfolio Analytics")

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
                st.error("No data found.")
                st.stop()

            tab1, tab2, tab3 = st.tabs(["📊 Monitor", "📉 Allocation", "⚙️ Manage"])

            with tab1:
                display_list = []
                for ticker in tickers:
                    df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
                    if df.empty: continue
                    
                    # Calculations
                    ema_200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                    curr_p = float(df['Close'].iloc[-1])
                    prev_p = float(df['Close'].iloc[-2])
                    high_52 = float(df['Close'].tail(252).max())
                    
                    qty = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == ticker, 'Qty'].values[0])
                    status = "🟢" if curr_p > ema_200 else "🔴"
                    change = curr_p - prev_p
                    
                    display_list.append({
                        "Ticker": ticker.replace(".NS", ""),
                        "Trend": status,
                        "Price": round(curr_p, 2),
                        "Change": round(change, 2),
                        "v 52W High": f"{round(((curr_p - high_52) / high_52 * 100), 1)}%",
                        "Value": int(qty * curr_p)
                    })
                
                # Convert list to DataFrame for Table View
                df_monitor = pd.DataFrame(display_list)
                
                # Using st.dataframe forces a table structure even on mobile
                st.dataframe(
                    df_monitor, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "Trend": st.column_config.TextColumn("Trend", width="small"),
                        "Price": st.column_config.NumberColumn("Price (₹)"),
                        "Value": st.column_config.NumberColumn("Total Value (₹)", format="₹%d"),
                    }
                )

            with tab2:
                plot_data = []
                for t in tickers:
                    df_t = data[t].dropna() if len(tickers) > 1 else data.dropna()
                    if not df_t.empty:
                        q = float(st.session_state.df_portfolio.loc[st.session_state.df_portfolio['Ticker'] == t, 'Qty'].values[0])
                        plot_data.append({"Ticker": t.replace(".NS",""), "Value": q * float(df_t['Close'].iloc[-1])})
                
                if plot_data:
                    pdf = pd.DataFrame(plot_data)
                    fig = px.pie(pdf, values='Value', names='Ticker', hole=0.4)
                    fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig, use_container_width=True)

            with tab3:
                st.subheader("Manage Holdings")
                new_df = st.data_editor(st.session_state.df_portfolio, use_container_width=True, hide_index=True)
                if st.button("💾 Save Changes"):
                    st.session_state.df_portfolio = save_data(new_df)
                    st.success("Saved!")
                    st.rerun()
                
                if st.button("🗑️ Wipe All Data", type="primary"):
                    st.session_state.df_portfolio = pd.DataFrame(columns=["Ticker", "Qty"])
                    save_data(st.session_state.df_portfolio)
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error: {str(e)}")
else:
    st.info("Portfolio is empty.")