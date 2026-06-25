import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="centered", page_title="T212 Auto-Screener")
st.title("🇬🇧 T212 Automated Stock Screener")

@st.cache_data(ttl=3600)  # Caches the watchlists for 1 hour
def get_screened_tickers():
    tickers = {}
    
    # 1. Fetching Core FTSE Components from GitHub Data Feed
    try:
        url = "https://raw.githubusercontent.com/datasets/ftse-100/master/data/ftse-100-components.csv"
        ftse_df = pd.read_csv(url)
        for t in ftse_df['Ticker'].dropna().tolist():
            clean_ticker = str(t).strip().replace('.', '-')
            if not clean_ticker.endswith(".L"):
                yahoo_ticker = f"{clean_ticker}.L"
            else:
                yahoo_ticker = clean_ticker
            tickers[yahoo_ticker] = f"{clean_ticker} (FTSE Core)"
    except Exception as e:
        st.sidebar.warning("Live LSE tracker feed down, using backups.")

    # 2. Fetching Yahoo Undervalued Growth Assets
    try:
        undervalued = yf.screen("undervalued_growth_stocks")
        if undervalued and 'quotes' in undervalued:
            for quote in undervalued['quotes'][:15]: # Grab top 15
                symbol = quote['symbol']
                if symbol not in tickers:
                    tickers[symbol] = f"{symbol} (Yahoo Undervalued)"
    except Exception as e:
        st.sidebar.warning("Yahoo Screeners currently throttled, using backups.")
        
    # 3. Dynamic Fallback list to ensure stocks always show up
    fallback_defaults = {
        "AZN.L": "AstraZeneca (LSE)",
        "BP.L": "BP (LSE)",
        "LLOY.L": "Lloyds Banking Group (LSE)",
        "VOD.L": "Vodafone (LSE)",
        "SMCI": "Super Micro (US)",
        "T": "AT&T (US)",
        "CCL": "Carnival (US)"
    }
    for k, v in fallback_defaults.items():
        if k not in tickers:
            tickers[k] = v
            
    return tickers

st.write("🔄 Extracting metrics and computing Exponential Moving Averages...")

TICKERS = get_screened_tickers()
results = []

# Fetch using Tickers container to preserve individual data structures perfectly
tickers_container = yf.Tickers(list(TICKERS.keys()))

for symbol, name in TICKERS.items():
    try:
        # Request 6 months of historical context for this precise ticker object
        data = tickers_container.tickers[symbol].history(period="6m")
        
        if data.empty or len(data) < 26:
            continue
            
        # Calculate Technical Moving Averages
        data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # Trend Analysis
        if latest['EMA12'] > latest['EMA26'] and prev['EMA12'] <= prev['EMA26']:
            signal = "🚀 BUY"
        elif latest['EMA12'] < latest['EMA26'] and prev['EMA12'] >= prev['EMA26']:
            signal = "🚨 SELL"
        else:
            signal = "😴 HOLD"
            
        is_foreign = not symbol.endswith(".L")
        fx_penalty = "0.30% Roundtrip" if is_foreign else "0.00% (Native)"
        
        results.append({
            "Stock": name,
            "Symbol": symbol,
            "Price": round(float(latest['Close']), 2),
            "Signal": signal,
            "T212 FX Cost": fx_penalty,
            "Foreign": is_foreign
        })
    except:
        continue # Ignore broken symbols or tickers suspended from trading

# Render interface output structures
if results:
    df = pd.DataFrame(results)
    st.success(f"Successfully processed {len(df)} assets!")
    
    tab1, tab2, tab3 = st.tabs(["🚀 BUY Signals", "🚨 SELL Signals", "😴 ALL Positions"])
    
    with tab1:
        buys = df[df['Signal'] == "🚀 BUY"]
        st.write(f"Found {len(buys)} matching entries")
        for _, row in buys.iterrows():
            with st.expander(f"{row['Stock']} ({row['Symbol']})"):
                st.metric("Price", f"{row['Price']}")
                st.caption(f"T212 FX Fee Status: {row['T212 FX Cost']}")
                
    with tab2:
        sells = df[df['Signal'] == "🚨 SELL"]
        st.write(f"Found {len(sells)} matching entries")
        for _, row in sells.iterrows():
            with st.expander(f"{row['Stock']} ({row['Symbol']})"):
                st.metric("Price", f"{row['Price']}")
                st.caption(f"T212 FX Fee Status: {row['T212 FX Cost']}")
                
    with tab3:
        st.dataframe(df[['Stock', 'Symbol', 'Price', 'Signal', 'T212 FX Cost']], use_container_width=True)
else:
    st.error("Data tracking pipeline encountered an unexpected sync failure. Refresh page.")
