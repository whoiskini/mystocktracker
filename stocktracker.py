import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="centered", page_title="T212 Auto-Screener")
st.title("🇬🇧 T212 Automated Stock Screener")

@st.cache_data(ttl=3600)  # Keeps the asset watchlists cached for 1 hour
def get_screened_tickers():
    # Keep the initial watchlists tight to prevent data timeouts
    tickers = {
        "AZN.L": "AstraZeneca (LSE)",
        "BP.L": "BP (LSE)",
        "LLOY.L": "Lloyds Banking Group (LSE)",
        "VOD.L": "Vodafone (LSE)",
        "RR.L": "Rolls-Royce (LSE)",
        "BA.L": "BAE Systems (LSE)",
        "SMCI": "Super Micro (US - FX)",
        "T": "AT&T (US - FX)",
        "CCL": "Carnival (US - FX)",
        "AAPL": "Apple (US - FX)"
    }
    return tickers

st.write("🔄 Executing optimized historical sync...")

TICKERS = get_screened_tickers()
ticker_list = list(TICKERS.keys())

try:
    # ONE SINGLE network request for everything. Yahoo loves this.
    raw_data = yf.download(ticker_list, period="6m", progress=False)
    
    results = []
    
    if not raw_data.empty:
        for symbol in ticker_list:
            try:
                # Safely extract data for just this ticker out of the big multi-index table
                if isinstance(raw_data.columns, pd.MultiIndex):
                    # MultiIndex structure fallback: extract by ticker level
                    if symbol in raw_data.columns.get_level_values(1):
                        data = raw_data.xs(symbol, axis=1, level=1).dropna()
                    elif symbol in raw_data.columns.get_level_values(0):
                        data = raw_data.xs(symbol, axis=1, level=0).dropna()
                    else:
                        continue
                else:
                    data = raw_data.dropna()

                if data.empty or len(data) < 26:
                    continue
                
                # Math Indicators
                data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
                data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
                
                latest = data.iloc[-1]
                prev = data.iloc[-2]
                
                if latest['EMA12'] > latest['EMA26'] and prev['EMA12'] <= prev['EMA26']:
                    signal = "🚀 BUY"
                elif latest['EMA12'] < latest['EMA26'] and prev['EMA12'] >= prev['EMA26']:
                    signal = "🚨 SELL"
                else:
                    signal = "😴 HOLD"
                    
                is_foreign = not symbol.endswith(".L")
                fx_penalty = "0.30% Roundtrip" if is_foreign else "0.00% (Native)"
                
                results.append({
                    "Stock": TICKERS[symbol],
                    "Symbol": symbol,
                    "Price": round(float(latest['Close']), 2),
                    "Signal": signal,
                    "T212 FX Cost": fx_penalty,
                    "Foreign": is_foreign
                })
            except Exception as item_error:
                continue

    if len(results) > 0:
        df = pd.DataFrame(results)
        st.success(f"Successfully processed {len(df)} live market trackers!")
        
        tab1, tab2, tab3 = st.tabs(["🚀 BUY Signals", "🚨 SELL Signals", "😴 ALL Positions"])
        
        with tab1:
            buys = df[df['Signal'] == "🚀 BUY"]
            st.write(f"Found {len(buys)} assets flashing entry signals.")
            for _, row in buys.iterrows():
                with st.expander(f"{row['Stock']} ({row['Symbol']})"):
                    st.metric("Price", f"{row['Price']}")
                    st.caption(f"Trading 212 FX Impact: {row['T212 FX Cost']}")
                    
        with tab2:
            sells = df[df['Signal'] == "🚨 SELL"]
            st.write(f"Found {len(sells)} assets flashing exit signals.")
            for _, row in sells.iterrows():
                with st.expander(f"{row['Stock']} ({row['Symbol']})"):
                    st.metric("Price", f"{row['Price']}")
                    st.caption(f"Trading 212 FX Impact: {row['T212 FX Cost']}")
                    
        with tab3:
            st.dataframe(df[['Stock', 'Symbol', 'Price', 'Signal', 'T212 FX Cost']], use_container_width=True)
            
    else:
        st.error("Yahoo Finance rejected the host request context. Try hitting clear cache in settings.")

except Exception as e:
    st.error(f"Global processing failure: {e}")
