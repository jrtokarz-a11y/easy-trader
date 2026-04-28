import streamlit as st
import pandas as pd
from io import StringIO
import requests
import yfinance as yf
import json

from analyzer import analyze_holdings, scan_trending_ideas, get_top_5_trades
from wsb_sentiment import get_wsb_snapshot

st.set_page_config(layout="wide", page_title="AI Trader V21.1")

st.markdown("""
<style>
body {background:#0b0f14;color:white;}
.card {background:#121821;padding:15px;border-radius:15px;margin-bottom:12px;}
.hero {padding:25px;border-radius:20px;text-align:center;margin-bottom:20px;}
.buy-box {background:linear-gradient(135deg,#003d1f,#00c853);}
.sell-box {background:linear-gradient(135deg,#3d0000,#ff1744);}
.hold-box {background:linear-gradient(135deg,#3d3000,#ffd600);}
.small {color:#aaa;font-size:13px;}
.score {font-size:20px;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

def load_holdings():
    file_id = st.secrets.get("holdings_file_id", "")
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url, timeout=20)
    return pd.read_csv(StringIO(r.text))

def style_box(decision):
    decision = str(decision)
    if "BUY" in decision:
        return "buy-box", "🟢 BUY"
    if "SELL" in decision or "REDUCE" in decision:
        return "sell-box", "🔴 SELL"
    return "hold-box", "🟡 HOLD"

def load_weights():
    try:
        with open("weights.json", "r") as f:
            return json.load(f)
    except:
        return {"confidence": 1.0, "momentum": 1.0, "breakout": 1.0}

def ai_score(conf, momentum, breakout, weights):
    score = (
        conf * weights.get("confidence", 1.0)
        + (10 if momentum else 0) * weights.get("momentum", 1.0)
        + (15 if breakout else 0) * weights.get("breakout", 1.0)
    )
    return min(100, round(score))

def score_label(score):
    if score > 85:
        return "🔥 Strong"
    if score > 70:
        return "✅ Good"
    if score > 60:
        return "⚠️ Watch"
    return "❌ Weak"

@st.cache_data(ttl=120)
def get_batch_data(tickers):
    clean = sorted(list(set([t for t in tickers if t and isinstance(t, str)])))
    if not clean:
        return None
    return yf.download(
        clean,
        period="3mo",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True
    )

def get_ticker_frame(market_data, ticker):
    try:
        if market_data is None or market_data.empty:
            return None

        if isinstance(market_data.columns, pd.MultiIndex):
            if ticker in market_data.columns.get_level_values(0):
                df = market_data[ticker].dropna()
                return df if not df.empty else None
        else:
            df = market_data.dropna()
            return df if not df.empty else None
    except:
        return None
    return None

def get_momentum(data):
    try:
        if data is None or len(data) < 5:
            return False
        move = (data["Close"].iloc[-1] - data["Close"].iloc[-4]) / data["Close"].iloc[-4] * 100
        vol = data["Volume"].iloc[-1] > data["Volume"].mean() * 1.5
        return abs(move) > 1 and vol
    except:
        return False

def get_breakout(data):
    try:
        if data is None or len(data) < 10:
            return False
        high = data["High"].tail(10).max()
        low = data["Low"].tail(10).min()
        current = data["Close"].iloc[-1]
        vol = data["Volume"].iloc[-1] > data["Volume"].mean() * 1.5
        return (current >= high or current <= low) and vol
    except:
        return False

def get_trade_levels(data):
    try:
        if data is None or len(data) < 20:
            return None

        recent = data.tail(20)
        high = recent["High"].max()
        low = recent["Low"].min()
        current = recent["Close"].iloc[-1]

        entry = round(current * 0.995, 2)
        stop = round(low * 0.98, 2)
        target = round(high * 1.03, 2)

        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {"entry": entry, "stop": stop, "target": target, "rr": rr}
    except:
        return None

def trade_box(levels):
    if not levels:
        return ""
    return f"""
    <div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:8px;font-size:14px;">
    🎯 Entry: ${levels["entry"]}<br>
    🛑 Stop: ${levels["stop"]}<br>
    💰 Target: ${levels["target"]}<br>
    ⚖️ R/R: {levels["rr"]}
    </div>
    """

def chart_block(data, ticker):
    if data is None or "Close" not in data.columns or data["Close"].dropna().empty:
        st.caption(f"No chart data available for {ticker}")
        return
    st.line_chart(data["Close"].dropna())

def render_trade_card(row, data, source=None):
    momentum = get_momentum(data)
    breakout = get_breakout(data)
    score = ai_score(row.get("Confidence", 0), momentum, breakout, weights)
    levels = get_trade_levels(data)

    box, label = style_box(row.get("Decision", "HOLD"))

    st.markdown(f"""
    <div class="card {box}">
    <h3>{row.get("Ticker", "—")}</h3>
    <h2>{label}</h2>
    <p>AI Score: {score}</p>
    <p class="score">{score_label(score)}</p>
    <p class="small">{row.get("Reason", row.get("Simple Read", ""))}</p>
    {trade_box(levels)}
    </div>
    """, unsafe_allow_html=True)

    chart_block(data, row.get("Ticker", ""))

# ---------- LOAD DATA ----------
holdings = load_holdings()
results = analyze_holdings(holdings)

wsb_rows = get_wsb_snapshot()
ideas = scan_trending_ideas(holdings, wsb_rows)
top5 = get_top_5_trades(holdings, results, ideas)

tickers = list(set(
    [r["Ticker"] for r in top5 if "Ticker" in r] +
    [r["Ticker"] for r in results["decisions"] if "Ticker" in r] +
    [r["Ticker"] for r in ideas if "Ticker" in r]
))

market_data = get_batch_data(tickers)
weights = load_weights()
best = results["best_trade_right_now"]

# ---------- SIDEBAR ----------
st.sidebar.title("📱 AI Trader V21.1")
section = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Home",
        "🔥 Top Trades",
        "💼 Portfolio",
        "📈 Opportunities / WSB",
        "📊 Performance",
        "📘 Journal"
    ]
)

# ---------- HOME ----------
if section == "🏠 Home":
    best_data = get_ticker_frame(market_data, best["Ticker"])
    momentum = get_momentum(best_data)
    breakout = get_breakout(best_data)
    score = ai_score(best["Confidence"], momentum, breakout, weights)
    levels = get_trade_levels(best_data)

    box, label = style_box(best["Decision"])

    st.markdown(f"""
    <div class="hero {box}">
    <h1>{best["Ticker"]}</h1>
    <h2>{label}</h2>
    <h3>AI Score: {score}</h3>
    <p class="score">{score_label(score)}</p>
    <p class="small">{best.get("Reason", "")}</p>
    {trade_box(levels)}
    </div>
    """, unsafe_allow_html=True)

    chart_block(best_data, best["Ticker"])

# ---------- TOP TRADES ----------
if section == "🔥 Top Trades":
    st.markdown("## 🔥 Top Trades")

    for r in top5:
        data = get_ticker_frame(market_data, r["Ticker"])
        render_trade_card(r, data)

# ---------- PORTFOLIO ----------
if section == "💼 Portfolio":
    st.markdown("## 💼 Portfolio")

    for row in results["decisions"]:
        data = get_ticker_frame(market_data, row["Ticker"])
        render_trade_card(row, data)

# ---------- OPPORTUNITIES / WSB ----------
if section == "📈 Opportunities / WSB":
    st.markdown("## 📈 Opportunities + WSB Trends")

    st.markdown("### 🔥 Outside Ideas")
    for row in ideas:
        data = get_ticker_frame(market_data, row["Ticker"])
        render_trade_card(row, data)

    st.markdown("### 🧠 WSB Trend Feed")
    if wsb_rows:
        st.dataframe(pd.DataFrame(wsb_rows), use_container_width=True)
    else:
        st.info("No WSB trend data available.")

# ---------- PERFORMANCE ----------
if section == "📊 Performance":
    st.markdown("## 📊 AI Performance")

    try:
        journal = pd.read_csv("trade_journal.csv")
        st.dataframe(journal.tail(25), use_container_width=True)

        if "confidence" in journal.columns:
            journal["confidence"] = pd.to_numeric(journal["confidence"], errors="coerce")
            st.line_chart(journal["confidence"].dropna())
    except:
        st.info("Waiting for performance data.")

# ---------- JOURNAL ----------
if section == "📘 Journal":
    st.markdown("## 📘 Trade Journal")

    try:
        journal = pd.read_csv("trade_journal.csv").tail(30)
        st.dataframe(journal, use_container_width=True)
    except:
        st.info("No journal yet.")
