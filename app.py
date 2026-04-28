import streamlit as st
import pandas as pd
from io import StringIO
import requests
import yfinance as yf

from analyzer import analyze_holdings, scan_trending_ideas
from wsb_sentiment import get_wsb_snapshot

st.set_page_config(page_title="AI Trader", layout="wide")

# ---------- STYLE ----------
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    max-width: 900px;
}

html, body, [class*="css"] {
    background-color: #0b0f14;
}

.card {
    background:#121821;
    color:white !important;
    padding:18px;
    border-radius:18px;
    margin-bottom:16px;
}

.hero {
    color:white !important;
    padding:24px;
    border-radius:24px;
    margin-bottom:18px;
}

.hero h1, .hero h2, .hero h3, .hero p,
.card h1, .card h2, .card h3, .card p {
    color:white !important;
}

.buy-box {
    background:linear-gradient(135deg,#004d25,#00c853);
}

.sell-box {
    background:linear-gradient(135deg,#5c0000,#ff1744);
}

.hold-box {
    background:linear-gradient(135deg,#5c4b00,#ffd600);
}

.small {
    color:#e0e0e0 !important;
    font-size:14px;
}

.level-box {
    background:#0f172a;
    color:white !important;
    padding:12px;
    border-radius:12px;
    margin-top:12px;
    line-height:1.7;
    font-size:15px;
}

.level-box strong {
    color:white !important;
}

h1, h2, h3, p {
    color:white;
}
</style>
""", unsafe_allow_html=True)


# ---------- DATA LOADERS ----------
def load_holdings():
    file_id = st.secrets.get("holdings_file_id", "")
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text))


@st.cache_data(ttl=120)
def get_price_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="3mo",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df is None or df.empty:
            return None

        return df.dropna()

    except Exception:
        return None


# ---------- UI HELPERS ----------
def style_box(decision):
    d = str(decision)

    if "BUY" in d:
        return "buy-box", "🟢 BUY"

    if "SELL" in d or "REDUCE" in d:
        return "sell-box", "🔴 SELL"

    return "hold-box", "🟡 HOLD"


def safe_chart(ticker):
    df = get_price_data(ticker)

    if df is not None and "Close" in df.columns and not df["Close"].dropna().empty:
        st.line_chart(df["Close"].dropna())
    else:
        st.caption(f"No chart data for {ticker}")


def trade_levels_from_data(ticker):
    df = get_price_data(ticker)

    if df is None or len(df) < 20:
        return None

    try:
        recent = df.tail(20)

        current = float(recent["Close"].iloc[-1])
        low = float(recent["Low"].min())
        high = float(recent["High"].max())

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
            "rr": rr,
            "source": "Yahoo Finance"
        }

    except Exception:
        return None


def fallback_levels_from_row(row):
    action_price = row.get("Action Price", "")
    ticker = row.get("Ticker", "—")

    if not action_price:
        return {
            "entry": "Check chart",
            "stop": "Set before trade",
            "target": "Set before trade",
            "rr": "—",
            "source": "Fallback"
        }

    return {
        "entry": action_price,
        "stop": row.get("Risk Line", "Set before trade"),
        "target": "Use chart target",
        "rr": "—",
        "source": "Signal fallback"
    }


def level_box(levels):
    if not levels:
        return ""

    return f"""
    <div class="level-box">
        <strong>🎯 Entry:</strong> ${levels["entry"] if isinstance(levels["entry"], (int, float)) else levels["entry"]}<br>
        <strong>🛑 Stop:</strong> ${levels["stop"] if isinstance(levels["stop"], (int, float)) else levels["stop"]}<br>
        <strong>💰 Target:</strong> ${levels["target"] if isinstance(levels["target"], (int, float)) else levels["target"]}<br>
        <strong>⚖️ R/R:</strong> {levels["rr"]}<br>
        <span class="small">Source: {levels["source"]}</span>
    </div>
    """


def render_card(row):
    ticker = row.get("Ticker", "—")
    decision = row.get("Decision", "HOLD")
    confidence = row.get("Confidence", 0)
    reason = row.get("Reason", row.get("Simple Read", ""))

    box, label = style_box(decision)

    levels = trade_levels_from_data(ticker)
    if levels is None:
        levels = fallback_levels_from_row(row)

    st.markdown(f"""
    <div class="hero {box}">
      <h1>{ticker}</h1>
      <h2>{label}</h2>
      <h3>Confidence: {confidence}%</h3>
      <p class="small">{reason}</p>
      {level_box(levels)}
    </div>
    """, unsafe_allow_html=True)

    safe_chart(ticker)


def get_top5(results, ideas):
    combined = []

    for r in results.get("top_trades", []):
        r = dict(r)
        r["Source"] = "Portfolio"
        combined.append(r)

    for r in ideas:
        r = dict(r)
        r["Source"] = "WSB + Market"
        combined.append(r)

    seen = set()
    out = []

    for r in sorted(combined, key=lambda x: x.get("Confidence", 0), reverse=True):
        ticker = r.get("Ticker")

        if ticker and ticker not in seen:
            out.append(r)
            seen.add(ticker)

        if len(out) >= 5:
            break

    return out


# ---------- LOAD APP DATA ----------
holdings = load_holdings()
results = analyze_holdings(holdings)

wsb_rows = get_wsb_snapshot()
ideas = scan_trending_ideas(holdings, wsb_rows)

top5 = get_top5(results, ideas)
best = results.get("best_trade_right_now", top5[0] if top5 else {})


# ---------- APP ----------
st.title("📱 AI Trader")

tabs = st.tabs([
    "🏠 Home",
    "🔥 Top Trades",
    "💼 Portfolio",
    "📈 WSB / Ideas",
    "📘 Journal"
])


# ---------- HOME ----------
with tabs[0]:
    st.subheader("Best Trade Right Now")

    if best:
        render_card(best)
    else:
        st.info("No best trade available yet.")


# ---------- TOP TRADES ----------
with tabs[1]:
    st.subheader("Top 5 Trades")

    if top5:
        for r in top5:
            render_card(r)
    else:
        st.info("No top trades available yet.")


# ---------- PORTFOLIO ----------
with tabs[2]:
    st.subheader("Your Portfolio")

    decisions = results.get("decisions", [])

    if decisions:
        for row in decisions:
            render_card(row)
    else:
        st.info("No portfolio decisions available yet.")


# ---------- WSB / IDEAS ----------
with tabs[3]:
    st.subheader("Trending Ideas")

    if ideas:
        for row in ideas:
            render_card(row)
    else:
        st.info("No trending ideas available yet.")

    st.subheader("WSB Trend Feed")

    if wsb_rows:
        st.dataframe(pd.DataFrame(wsb_rows), use_container_width=True)
    else:
        st.info("No WSB trend data available.")


# ---------- JOURNAL ----------
with tabs[4]:
    st.subheader("Trade Journal")

    try:
        journal = pd.read_csv("trade_journal.csv").tail(30)
        st.dataframe(journal, use_container_width=True)
    except Exception:
        st.info("No journal yet.")
