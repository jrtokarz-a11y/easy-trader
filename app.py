import streamlit as st
import pandas as pd
from io import StringIO
import requests
import yfinance as yf

from analyzer import analyze_holdings, scan_trending_ideas, get_top_5_trades
from wsb_sentiment import get_wsb_snapshot

st.set_page_config(layout="wide")

# ---------- STYLE ----------
st.markdown("""
<style>
body {background:#0b0f14;color:white;}
.card {background:#121821;padding:15px;border-radius:15px;margin-bottom:12px;}
.hero {padding:25px;border-radius:20px;text-align:center;margin-bottom:20px;}
.buy-box {background:linear-gradient(135deg,#003d1f,#00c853);}
.sell-box {background:linear-gradient(135deg,#3d0000,#ff1744);}
.hold-box {background:linear-gradient(135deg,#3d3000,#ffd600);}
.small {color:#aaa;font-size:13px;}
</style>
""", unsafe_allow_html=True)

# ---------- HELPERS ----------
def load_holdings():
    file_id = st.secrets.get("holdings_file_id", "")
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url)
    return pd.read_csv(StringIO(r.text))

def style_box(decision):
    if "BUY" in decision:
        return "buy-box", "🟢 BUY"
    if "SELL" in decision or "REDUCE" in decision:
        return "sell-box", "🔴 SELL"
    return "hold-box", "🟡 HOLD"

def get_candles(ticker):
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        return df
    except:
        return None

def trade_checklist(conf):
    checks = [
        ("Trend strength", conf > 70),
        ("Momentum confirmed", conf > 60),
        ("Risk defined", True),
        ("Market aligned", conf > 65)
    ]
    return checks

# ---------- LOAD ----------
holdings = load_holdings()
results = analyze_holdings(holdings)
ideas = scan_trending_ideas(holdings, get_wsb_snapshot())
top5 = get_top_5_trades(holdings, results, ideas)
best = results["best_trade_right_now"]

# ---------- SIDEBAR ----------
st.sidebar.title("💰 Hedge Fund Mode")
section = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🎯 Focus", "🔥 Trades", "📊 Risk", "💼 Portfolio", "📘 Journal"]
)

# ---------- HOME ----------
if section == "🏠 Home":
    box, label = style_box(best["Decision"])
    st.markdown(f"""
    <div class="hero {box}">
    <h1>{best["Ticker"]}</h1>
    <h2>{label}</h2>
    <h3>{best["Confidence"]}%</h3>
    <p>{best["Action Price"]}</p>
    </div>
    """, unsafe_allow_html=True)

# ---------- FOCUS ----------
if section == "🎯 Focus":

    st.markdown("## 🎯 Trade Execution")

    if best["Confidence"] >= 70:

        box, label = style_box(best["Decision"])

        st.markdown(f"""
        <div class="hero {box}">
        <h1>{best["Ticker"]}</h1>
        <h2>{label}</h2>
        <h3>{best["Confidence"]}%</h3>
        </div>
        """, unsafe_allow_html=True)

        # Checklist
        st.markdown("### ✔ Trade Checklist")
        for name, ok in trade_checklist(best["Confidence"]):
            st.write(f"{'✅' if ok else '❌'} {name}")

        # Chart
        data = get_candles(best["Ticker"])
        if data is not None:
            st.line_chart(data["Close"])

    else:
        st.info("No high-quality trade right now")

# ---------- TRADES ----------
if section == "🔥 Trades":

    for r in top5:

        if r["Confidence"] < 60:
            continue

        box, label = style_box(r["Decision"])

        st.markdown(f"""
        <div class="card {box}">
        <h3>{r["Ticker"]}</h3>
        <h2>{label}</h2>
        <p>{r["Confidence"]}%</p>
        </div>
        """, unsafe_allow_html=True)

# ---------- RISK DASHBOARD ----------
if section == "📊 Risk":

    st.markdown("## 📊 Portfolio Risk")

    total_positions = len(results["decisions"])
    high_risk = len([r for r in results["decisions"] if r["Decision"] == "SELL / CUT RISK"])

    st.metric("Total Positions", total_positions)
    st.metric("High Risk Positions", high_risk)

    st.progress(min(1.0, high_risk / max(1, total_positions)))

# ---------- PORTFOLIO ----------
if section == "💼 Portfolio":

    for row in results["decisions"]:
        box, label = style_box(row["Decision"])

        st.markdown(f"""
        <div class="card {box}">
        <h3>{row["Ticker"]}</h3>
        <h2>{label}</h2>
        <p>{row["Confidence"]}%</p>
        </div>
        """, unsafe_allow_html=True)

# ---------- JOURNAL ----------
if section == "📘 Journal":

    try:
        journal = pd.read_csv("trade_journal.csv").tail(20)
        st.dataframe(journal)
    except:
        st.info("No journal yet")
