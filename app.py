import streamlit as st
import pandas as pd
from io import StringIO
import requests
import yfinance as yf
import json

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
.score {font-size:20px;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ---------- LOAD HOLDINGS ----------
def load_holdings():
    file_id = st.secrets.get("holdings_file_id", "")
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url)
    return pd.read_csv(StringIO(r.text))

# ---------- STYLE ----------
def style_box(decision):
    if "BUY" in decision:
        return "buy-box", "🟢 BUY"
    if "SELL" in decision or "REDUCE" in decision:
        return "sell-box", "🔴 SELL"
    return "hold-box", "🟡 HOLD"

# ---------- WEIGHTS ----------
def load_weights():
    try:
        with open("weights.json", "r") as f:
            return json.load(f)
    except:
        return {"confidence": 1.0, "momentum": 1.0, "breakout": 1.0}

def save_weights(w):
    with open("weights.json", "w") as f:
        json.dump(w, f)

# ---------- AI SCORE ----------
def ai_score(conf, momentum, breakout, weights):
    score = (
        conf * weights["confidence"]
        + (10 if momentum else 0) * weights["momentum"]
        + (15 if breakout else 0) * weights["breakout"]
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

# ---------- DATA ENGINE ----------
@st.cache_data(ttl=120)
def get_batch_data(tickers):
    return yf.download(tickers, period="3mo", group_by="ticker", progress=False)

# ---------- MOMENTUM ----------
def get_momentum(data):
    try:
        move = (data["Close"].iloc[-1] - data["Close"].iloc[-4]) / data["Close"].iloc[-4] * 100
        vol = data["Volume"].iloc[-1] > data["Volume"].mean() * 1.5
        return abs(move) > 1 and vol
    except:
        return False

# ---------- BREAKOUT ----------
def get_breakout(data):
    try:
        high = data["High"].tail(10).max()
        low = data["Low"].tail(10).min()
        current = data["Close"].iloc[-1]
        vol = data["Volume"].iloc[-1] > data["Volume"].mean() * 1.5
        return (current >= high or current <= low) and vol
    except:
        return False

# ---------- ENTRY / EXIT ENGINE ----------
def get_trade_levels(data):
    try:
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

        return {
            "entry": entry,
            "stop": stop,
            "target": target,
            "rr": rr
        }

    except:
        return None

def trade_box(levels):
    if not levels:
        return ""

    return f"""
    <div style="
        background:#0f172a;
        padding:10px;
        border-radius:10px;
        margin-top:8px;
        font-size:14px;
    ">
    🎯 Entry: ${levels["entry"]} <br>
    🛑 Stop: ${levels["stop"]} <br>
    💰 Target: ${levels["target"]} <br>
    ⚖️ R/R: {levels["rr"]}
    </div>
    """

# ---------- PERFORMANCE ----------
def calculate_performance(df):
    results = []
    for _, row in df.iterrows():
        try:
            data = yf.download(row["ticker"], period="5d")
            future_price = data["Close"].iloc[-1]
            ret = (future_price - row["entry_price"]) / row["entry_price"] * 100
            results.append({"score": row["ai_score"], "return": ret})
        except:
            continue
    return pd.DataFrame(results)

# ---------- SELF LEARNING ----------
def update_weights(perf_df):
    weights = load_weights()

    if len(perf_df) < 20:
        return weights

    high = perf_df[perf_df["score"] > 75]
    low = perf_df[perf_df["score"] < 60]

    if len(high) > 5:
        weights["confidence"] *= 1.05 if high["return"].mean() > 0 else 0.95

    if len(low) > 5:
        if low["return"].mean() < 0:
            weights["momentum"] *= 1.05
            weights["breakout"] *= 1.05

    for k in weights:
        weights[k] = max(0.5, min(2.0, weights[k]))

    save_weights(weights)
    return weights

# ---------- LOAD ----------
holdings = load_holdings()
results = analyze_holdings(holdings)
ideas = scan_trending_ideas(holdings, get_wsb_snapshot())
top5 = get_top_5_trades(holdings, results, ideas)

tickers = list(set(
    [r["Ticker"] for r in top5] +
    [r["Ticker"] for r in results["decisions"]]
))

market_data = get_batch_data(tickers)
weights = load_weights()

best = results["best_trade_right_now"]

# ---------- SIDEBAR ----------
st.sidebar.title("📱 AI Trader V21")
section = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🔥 Trades", "💼 Portfolio", "📊 Performance"]
)

# ---------- HOME ----------
if section == "🏠 Home":

    data = market_data.get(best["Ticker"])
    momentum = get_momentum(data)
    breakout = get_breakout(data)
    score = ai_score(best["Confidence"], momentum, breakout, weights)
    levels = get_trade_levels(data)

    box, label = style_box(best["Decision"])

    st.markdown(f"""
    <div class="hero {box}">
    <h1>{best["Ticker"]}</h1>
    <h2>{label}</h2>
    <h3>AI Score: {score}</h3>
    <p class="score">{score_label(score)}</p>
    {trade_box(levels)}
    </div>
    """, unsafe_allow_html=True)

    if data is not None:
        st.line_chart(data["Close"])

# ---------- TRADES ----------
if section == "🔥 Trades":

    for r in top5:

        data = market_data.get(r["Ticker"])
        momentum = get_momentum(data)
        breakout = get_breakout(data)
        score = ai_score(r["Confidence"], momentum, breakout, weights)
        levels = get_trade_levels(data)

        if levels and levels["rr"] < 1.2:
            continue

        box, label = style_box(r["Decision"])

        st.markdown(f"""
        <div class="card {box}">
        <h3>{r["Ticker"]}</h3>
        <h2>{label}</h2>
        <p>AI Score: {score}</p>
        <p class="score">{score_label(score)}</p>
        {trade_box(levels)}
        </div>
        """, unsafe_allow_html=True)

        if data is not None:
            st.line_chart(data["Close"])

# ---------- PORTFOLIO ----------
if section == "💼 Portfolio":

    for row in results["decisions"]:

        data = market_data.get(row["Ticker"])
        momentum = get_momentum(data)
        breakout = get_breakout(data)
        score = ai_score(row["Confidence"], momentum, breakout, weights)
        levels = get_trade_levels(data)

        box, label = style_box(row["Decision"])

        st.markdown(f"""
        <div class="card {box}">
        <h3>{row["Ticker"]}</h3>
        <h2>{label}</h2>
        <p>AI Score: {score}</p>
        <p class="score">{score_label(score)}</p>
        {trade_box(levels)}
        </div>
        """, unsafe_allow_html=True)

# ---------- PERFORMANCE ----------
if section == "📊 Performance":

    st.markdown("## 📊 AI Performance")

    try:
        journal = pd.read_csv("trade_journal.csv")
        perf = calculate_performance(journal)

        if len(perf) > 0:
            st.metric("Win Rate", f"{round((perf['return'] > 0).mean()*100,1)}%")
            st.metric("Avg Return", f"{round(perf['return'].mean(),2)}%")

            st.line_chart(perf["return"])

            weights = update_weights(perf)

            st.markdown("### 🧠 AI Weights")
            st.write(weights)

        else:
            st.info("Not enough data yet")

    except:
        st.info("Waiting for performance data")
