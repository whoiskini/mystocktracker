import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="centered", page_title="T212 Auto-Screener")
st.title("🇬🇧 T212 Automated Stock Screener")

@st.cache_data(ttl=3600)  # Caches the lists for 1 hour so your app loads fast
def get_screened_tickers():
    tickers = {}
    
    # 1. Fetching the FTSE 350 Dynamically via Wikipedia
    try:
        url = "https://en.wikipedia.org/wiki/FTSE_350_Index"
        tables = pd.read_html(url)
        # Wikipedia stores the constituents in the second table (index 1)
        ftse_df = tables[1]
        
        # Pull the ticker column (usually labeled 'Ticker')
        for t in ftse_df['Ticker'].dropna().tolist():
            # Clean up formatting (some have dots instead of hyphens, change to Yahoo format)
            clean_ticker = str(t).strip().replace('.', '-')
            yahoo_ticker = f"{clean_ticker}.L"
            tickers[yahoo_ticker] = f"{clean_ticker} (FTSE 350)"
    except Exception as e:
        st.warning("Could not auto-load FTSE 350 list. Using fallback.")
        tickers["AZN.L"] = "AstraZeneca (FTSE)"
        tickers["BP.L"] = "BP (FTSE)"

    # 2. Fetching Yahoo Undervalued Growth Assets
    # yfinance lets us call predefined screeners directly
    try:
        undervalued = yf.screener("undervalued_growth_stocks")
        # Extract tickers from the screener results
        for t in undervalued['quotes']['symbol'][:15]: # Take top 15 to keep it fast
            if t not in tickers:
                tickers[t] = f"{t} (Yahoo Undervalued)"
    except Exception as e:
        st.warning("Could not auto-load Yahoo Undervalued Stocks.")
        
    return tickers

st.write("🔄 Fetching live constituent lists & processing indicators...")

# Load our dynamic dictionary
TICKERS = get_screened_tickers()
ticker_list = list(TICKERS.keys())

try:
    # Mass download to stay under Yahoo's rate limits
    raw_data = yf.download(ticker_list, period="6m", group_by='ticker', progress=False)
    
    results = []
    for symbol in ticker_list:
        try:
            # Handle potential multi-index dataframe extraction safely
            if symbol in raw_data.columns.levels[0]:
                data = raw_data[symbol].dropna()
            else:
                continue
                
            if len(data) < 26:
                continue
                
            # Technical Indicators
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
        except:
            continue

    df = pd.DataFrame(results)
    
    # UI Filter Tabs for your phone screen layout
    tab1, tab2, tab3 = st.tabs(["🚀 BUY Signals", "🚨 SELL Signals", "😴 ALL Positions"])
    
    with tab1:
        buys = df[df['Signal'] == "🚀 BUY"]
        st.write(f"Found {len(buys)} action items")
        for _, row in buys.iterrows():
            with st.expander(f"{row['Stock']} — {row['Symbol']}"):
                st.metric("Price", f"{row['Price']}")
                st.caption(f"T212 FX Fee Status: {row['T212 FX Cost']}")
                
    with tab2:
        sells = df[df['Signal'] == "🚨 SELL"]
        st.write(f"Found {len(sells)} action items")
        for _, row in sells.iterrows():
            with st.expander(f"{row['Stock']} — {row['Symbol']}"):
                st.metric("Price", f"{row['Price']}")
                st.caption(f"T212 FX Fee Status: {row['T212 FX Cost']}")
                
    with tab3:
        st.dataframe(df[['Stock', 'Symbol', 'Price', 'Signal', 'T212 FX Cost']], use_container_width=True)

except Exception as e:
    st.error(f"Screener processing failure: {e}")
