import streamlit as st
import pandas as pd
from io import StringIO
import requests
import os

from analyzer import analyze_holdings, scan_trending_ideas, get_top_5_trades
from wsb_sentiment import get_wsb_snapshot

# ---------- PAGE ----------
st.set_page_config(layout="wide")

# ---------- STYLING ----------
st.markdown("""
<style>
html, body {
    background-color: #0b0f14;
    color: white;
}

.card {
    background-color: #121821;
    padding: 15px;
    border-radius: 15px;
    margin-bottom: 10px;
}

.hero {
    background-color: #161b22;
    padding: 25px;
    border-radius: 20px;
    text-align: center;
    margin-bottom: 20px;
}

.buy { color: #00d26a; font-weight: bold; }
.sell { color: #ff5c5c; font-weight: bold; }
.hold { color: #ffd54a; font-weight: bold; }

.small { color: #aaa; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ---------- HELPERS ----------
def load_holdings():
    file_id = st.secrets.get("holdings_file_id", "")
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url)
    return pd.read_csv(StringIO(r.text))

def color(decision):
    if "BUY" in decision:
        return "buy"
    if "SELL" in decision or "REDUCE" in decision:
        return "sell"
    return "hold"

# ---------- DATA ----------
holdings = load_holdings()
results = analyze_holdings(holdings)
ideas = scan_trending_ideas(holdings, get_wsb_snapshot())
top5 = get_top_5_trades(holdings, results, ideas)
best = results["best_trade_right_now"]

# ---------- SIDEBAR ----------
st.sidebar.title("📱 Easy Trader")
section = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🔥 Top Trades", "💼 Portfolio", "📈 Opportunities", "📘 Journal"]
)

# ---------- HOME ----------
if section == "🏠 Home":

    st.markdown(f"""
    <div class="hero">
    <h1>{best["Ticker"]}</h1>
    <h2 class="{color(best["Decision"])}">{best["Decision"]}</h2>
    <h3>{best["Confidence"]}% Confidence</h3>
    <p>Entry: {best["Action Price"]}</p>
    <p>Option: {best["Suggested Strike"]}</p>
    <p class="small">{best["Reason"]}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    col1.markdown(f"""
    <div class="card">
    <p class="small">Market Mood</p>
    <h3>{results["summary"]["market_mood"]}</h3>
    </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
    <div class="card">
    <p class="small">Portfolio</p>
    <h3>{results["summary"]["portfolio_health"]}</h3>
    </div>
    """, unsafe_allow_html=True)

# ---------- TOP TRADES ----------
if section == "🔥 Top Trades":

    st.markdown("## 🔥 Top 5 Trades Right Now")

    for r in top5:
        st.markdown(f"""
        <div class="card">
        <h3>{r["Ticker"]}</h3>
        <p class="{color(r["Decision"])}">{r["Decision"]} ({r["Confidence"]}%)</p>
        <p class="small">Source: {r["Source"]}</p>
        <p class="small">{r["Reason"]}</p>
        </div>
        """, unsafe_allow_html=True)

# ---------- PORTFOLIO ----------
if section == "💼 Portfolio":

    st.markdown("## 💼 Your Positions")

    with st.expander("Tap to view positions", expanded=True):

        for row in results["decisions"]:
            st.markdown(f"""
            <div class="card">
            <h3>{row["Ticker"]}</h3>
            <p class="{color(row["Decision"])}">
            {row["Decision"]} ({row["Confidence"]}%)
            </p>
            <p>Action: {row["Suggested Size"]}</p>
            <p class="small">{row["Reason"]}</p>
            </div>
            """, unsafe_allow_html=True)

# ---------- OPPORTUNITIES ----------
if section == "📈 Opportunities":

    st.markdown("## 📈 Opportunities")

    with st.expander("Tap to view ideas", expanded=False):

        for row in ideas:
            st.markdown(f"""
            <div class="card">
            <h3>{row["Ticker"]}</h3>
            <p class="{color(row["Decision"])}">
            {row["Decision"]} ({row["Confidence"]}%)
            </p>
            <p>Strike: {row["Suggested Strike"]}</p>
            <p class="small">{row["Simple Read"]}</p>
            </div>
            """, unsafe_allow_html=True)

# ---------- JOURNAL ----------
if section == "📘 Journal":

    st.markdown("## 📘 Trade Journal")

    with st.expander("Tap to view journal", expanded=False):

        try:
            journal = pd.read_csv("trade_journal.csv").tail(15)
            st.dataframe(journal)
        except:
            st.info("Journal will appear after first run")
