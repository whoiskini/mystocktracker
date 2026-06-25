import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="centered", page_title="T212 Auto-Screener")
st.title("🇬🇧 T212 Automated Stock Screener")

@st.cache_data(ttl=3600)  # Cache for 1 hour to keep it ultra-fast
def get_screened_tickers():
    tickers = {}
    
    # 1. Fetching the FTSE 100/350 via an alternate reliable source
    try:
        # Pulling directly from a clean financial data repo
        url = "https://raw.githubusercontent.com/datasets/ftse-100/master/data/ftse-100-components.csv"
        ftse_df = pd.read_csv(url)
        for t in ftse_df['Ticker'].dropna().tolist():
            clean_ticker = str(t).strip().replace('.', '-')
            yahoo_ticker = f"{clean_ticker}.L"
            tickers[yahoo_ticker] = f"{clean_ticker} (FTSE Core)"
    except Exception as e:
        st.sidebar.warning("Could not auto-load live LSE tracker. Using core fallbacks.")

    # 2. Fetching Yahoo Undervalued Growth Assets using the correct yf.screen function
    try:
        undervalued = yf.screen("undervalued_growth_stocks")
        if undervalued and 'quotes' in undervalued:
            for quote in undervalued['quotes'][:15]: # Top 15 tickers
                symbol = quote['symbol']
                if symbol not in tickers:
                    tickers[symbol] = f"{symbol} (Yahoo Undervalued)"
    except Exception as e:
        st.sidebar.warning("Could not auto-load Yahoo Undervalued. Using fallbacks.")
        
    # 3. ABSOLUTE HARD FALLBACK (Guarantees the app never starts empty)
    fallback_defaults = {
        "AZN.L": "AstraZeneca (LSE)",
        "BP.L": "BP (LSE)",
        "LLOY.L": "Lloyds Banking Group (LSE)",
        "VOD.L": "Vodafone (LSE)",
        "SMCI": "Super Micro (US - FX)",
        "T": "AT&T (US - FX)",
        "CCL": "Carnival (US - FX)"
    }
    for k, v in fallback_defaults.items():
        if k not in tickers:
            tickers[k] = v
            
    return tickers

st.write("🔄 Fetching live constituent lists & processing indicators...")

TICKERS = get_screened_tickers()
ticker_list = list(TICKERS.keys())

try:
    # Mass download to stay under Yahoo's rate limits safely
    raw_data = yf.download(ticker_list, period="6m", group_by='ticker', progress=False)
    
    results = []
    
    # Ensure raw_data is not completely empty
    if not raw_data.empty:
        for symbol in ticker_list:
            try:
                # Defensive Multi-Index check
                if isinstance(raw_data.columns, pd.MultiIndex):
                    if symbol in raw_data.columns.levels[0]:
                        data = raw_data[symbol].dropna()
                    else:
                        continue
                else:
                    data = raw_data.dropna()
                    
                if len(data) < 26:
                    continue
                    
                # Indicators
                data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
                data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
                
                latest = data.iloc[-1]
                prev = data.iloc[-2]
                
                # Signal Generation
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

    # Turn results safely into a DataFrame
    if len(results) > 0:
        df = pd.DataFrame(results)
    else:
        # Empty placeholder if absolutely everything failed to compute
        df = pd.DataFrame(columns=["Stock", "Symbol", "Price", "Signal", "T212 FX Cost", "Foreign"])

    st.success("Analysis Complete!")

    # Tab Display System
    tab1, tab2, tab3 = st.tabs(["🚀 BUY Signals", "🚨 SELL Signals", "😴 ALL Positions"])
    
    with tab1:
        buys = df[df['Signal'] == "🚀 BUY"]
        st.write(f"Found {len(buys)} active BUY recommendations")
        for _, row in buys.iterrows():
            with st.expander(f"{row['Stock']} ({row['Symbol']})"):
                st.metric("Price", f"{row['Price']}")
                st.caption(f"T212 FX Fee Status: {row['T212 FX Cost']}")
                
    with tab2:
        sells = df[df['Signal'] == "🚨 SELL"]
        st.write(f"Found {len(sells)} active SELL recommendations")
        for _, row in sells.iterrows():
            with st.expander(f"{row['Stock']} ({row['Symbol']})"):
                st.metric("Price", f"{row['Price']}")
                st.caption(f"T212 FX Fee Status: {row['T212 FX Cost']}")
                
    with tab3:
        if not df.empty:
            st.dataframe(df[['Stock', 'Symbol', 'Price', 'Signal', 'T212 FX Cost']], use_container_width=True)
        else:
            st.info("No market data currently tracked.")

except Exception as e:
    st.error(f"Screener processing failure: {e}")
