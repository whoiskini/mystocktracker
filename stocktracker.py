import streamlit as st
import yfinance as yf
import pandas as pd

# Set page to mobile-friendly wide layout by default
st.set_page_config(layout="centered", page_title="T212 Smart Screener")

st.title("🇬🇧 T212 Smart Stock Screener")
st.write("Tracking FTSE 350 & Undervalued Tickers with FX Fee Penalties.")

# 1. Custom Stock List (Mix of FTSE 350 examples and Yahoo Undervalued)
# Note: LSE stocks need '.L' at the end for Yahoo Finance
TICKERS = {
    "AstraZeneca (LSE)": "AZN.L",
    "BP (LSE)": "BP.L",
    "Lloyds Banking Group (LSE)": "LLOY.L",
    "Vodafone (LSE)": "VOD.L",
    "Super Micro (US - FX Fee Applies)": "SMCI",
    "AT&T (US - FX Fee Applies)": "T",
    "Carnival (US - FX Fee Applies)": "CCL"
}

def calculate_signals(ticker):
    try:
        # Fetch 6 months of daily data
        data = yf.Ticker(ticker).history(period="6m")
        if len(data) < 26:
            return None
        
        # Calculate Technical Indicators
        data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # Trend Strategy Logic
        if latest['EMA12'] > latest['EMA26'] and prev['EMA12'] <= prev['EMA26']:
            signal = "🚀 BUY"
        elif latest['EMA12'] < latest['EMA26'] and prev['EMA12'] >= prev['EMA26']:
            signal = "🚨 SELL"
        else:
            signal = "😴 HOLD"
            
        # Trading 212 Fee logic
        # If it doesn't end in '.L', it's foreign -> apply 0.15% penalty flag
        is_foreign = not ticker.endswith(".L")
        fx_penalty = "0.30% Roundtrip" if is_foreign else "0.00% (Native)"
        
        return {
            "Price": round(latest['Close'], 2),
            "Signal": signal,
            "T212 FX Cost": fx_penalty,
            "Foreign Asset": is_foreign
        }
    except Exception as e:
        return None

# UI Display
results = []
for name, symbol in TICKERS.items():
    metrics = calculate_signals(symbol)
    if metrics:
        metrics['Stock'] = name
        metrics['Symbol'] = symbol
        results.append(metrics)

df = pd.DataFrame(results)

# Prioritize native LSE deals or warn about FX fees dynamically
st.subheader("Screener Dashboard")

# Custom styled dataframe output for mobile viewports
for index, row in df.iterrows():
    with st.expander(f"{row['Stock']} — {row['Signal']}"):
        st.metric(label="Current Price", value=f"{row['Price']}")
        st.write(f"**Exchange Fee Impact:** {row['T212 FX Cost']}")
        if row['Foreign Asset']:
            st.warning("⚠️ Non-LSE Stock: Trading 212 will ding you 0.15% on buy AND sell conversions.")
        else:
            st.success("✅ Native LSE Asset: 0% FX Conversion fees apply.")