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
    margin-top:10px;
}

.level-box p {
    color:white !important;
}

h1, h2, h3, p {
    color:white;
}
</style>
""", unsafe_allow_html=True)


# ---------- DATA LOADERS ----------
def load_holdings():
    file_id = st.se
