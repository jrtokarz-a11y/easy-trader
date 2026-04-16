import os, json
from pathlib import Path
from io import StringIO
import pandas as pd
import requests
import streamlit as st
from analyzer import analyze_holdings, scan_trending_ideas, get_top_5_trades
from wsb_sentiment import get_wsb_snapshot

st.sidebar.title("📱 Navigation")

section = st.sidebar.radio(
    "Go to:",
    [
        "🏠 Home",
        "🔥 Top Trades",
        "💼 Portfolio",
        "📈 Opportunities",
        "📘 Journal"
    ]
)

def load_settings():
    settings = {}
    cfg = Path('config.json')
    if cfg.exists():
        try:
            settings.update(json.loads(cfg.read_text()))
        except Exception:
            pass
    try:
        for k in st.secrets:
            settings[k] = st.secrets[k]
    except Exception:
        pass
    for key in ['HOLDINGS_FILE_ID','HOLDINGS_CSV_URL','DASHBOARD_URL','EMAIL_ENABLED','EMAIL_SENDER','EMAIL_APP_PASSWORD','EMAIL_RECIPIENT','NTFY_TOPIC','NTFY_ENABLED']:
        if os.getenv(key):
            settings[key.lower()] = os.getenv(key)
    return settings

def load_holdings_from_gdrive(settings):
    file_id = settings.get('holdings_file_id')
    csv_url = settings.get('holdings_csv_url')
    if file_id:
        csv_url = f'https://drive.google.com/uc?export=download&id={file_id}'
    if not csv_url:
        return None, 'No Google Drive file configured yet.'
    try:
        resp = requests.get(csv_url, timeout=20)
        resp.raise_for_status()
        return pd.read_csv(StringIO(resp.text)), 'Loaded holdings from Google Drive.'
    except Exception as exc:
        return None, f'Could not load holdings from Google Drive: {type(exc).__name__}'

st.set_page_config(page_title='Easy Trader Mobile', layout='wide')
st.markdown("""
<style>
html, body, [class*='css'] {background-color:#0b0f14;color:#fff;}
.block-container {padding-top:1rem;padding-bottom:2rem;max-width:820px;}
h1,h2,h3 {letter-spacing:-0.02em;}
.hero-card {background:linear-gradient(180deg,#141922 0%,#10151d 100%);border:1px solid #1f2835;border-radius:24px;padding:24px;margin-bottom:16px;box-shadow:0 8px 24px rgba(0,0,0,0.25);}
.info-card {background:#121821;border:1px solid #1f2835;border-radius:20px;padding:16px;margin-bottom:14px;}
.tag-buy {color:#00d26a;font-weight:700;}.tag-sell {color:#ff5c5c;font-weight:700;}.tag-hold {color:#ffd54a;font-weight:700;}
.muted {color:#9db0c4;font-size:0.92rem;}.big {font-size:2rem;font-weight:800;margin-bottom:4px;}.med {font-size:1.15rem;font-weight:700;}
.section-title {margin-top:20px;margin-bottom:10px;font-size:1.2rem;font-weight:800;}
.stButton>button {border-radius:999px;background:#1d9bf0;color:white;border:none;font-weight:700;padding:0.5rem 1rem;}
</style>
""", unsafe_allow_html=True)

def color_class(decision):
    d = str(decision)
    if 'BUY' in d: return 'tag-buy'
    if 'SELL' in d or 'REDUCE' in d: return 'tag-sell'
    return 'tag-hold'

settings = load_settings()
dashboard_url = settings.get('dashboard_url', 'https://YOUR-APP.streamlit.app')
left, right = st.columns([1,1])
with left:
    st.markdown("<div class='med'>📱 Easy Trader V14</div><div class='muted'>Mobile-first trading assistant</div>", unsafe_allow_html=True)
with right:
    if st.button('Refresh data'):
        st.rerun()

uploaded = st.file_uploader('Optional: upload a holdings CSV just for this session', type=['csv'])
if uploaded is not None:
    holdings = pd.read_csv(uploaded)
    status = 'Using uploaded holdings for this session only.'
else:
    holdings, status = load_holdings_from_gdrive(settings)
st.caption(status)
if holdings is None:
    st.warning('No holdings loaded. Add a Google Drive file ID / URL in secrets or upload a CSV.')
    st.stop()

results = analyze_holdings(holdings)
wsb_rows = get_wsb_snapshot()
ideas = scan_trending_ideas(holdings, wsb_rows)
top5 = get_top_5_trades(holdings, results, ideas)
best = results['best_trade_right_now']

st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
st.markdown("<div class='muted'>🚀 BEST TRADE RIGHT NOW</div>", unsafe_allow_html=True)
st.markdown(f"<div class='big'>{best.get('Ticker','—')}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='{color_class(best.get('Decision'))}' style='font-size:1.4rem'>{best.get('Decision','—')}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='med'>{best.get('Confidence',0)}% confidence</div>", unsafe_allow_html=True)
st.markdown(f"<div class='muted'>Entry: {best.get('Action Price','—')}<br>Option: {best.get('Suggested Strike','—')}<br>{best.get('Reason','')}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"<div class='info-card'><div class='muted'>Market mood</div><div class='med'>{results['summary']['market_mood']}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='info-card'><div class='muted'>Portfolio</div><div class='med'>{results['summary']['portfolio_health']}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>🔥 Top 3 trades today</div>", unsafe_allow_html=True)
for row in results['top_trades']:
    st.markdown(f"<div class='info-card'><div class='med'>{row['Ticker']}</div><div class='{color_class(row['Decision'])}'>{row['Decision']} ({row['Confidence']}%)</div><div class='muted'>Action: {row['Suggested Size']}<br>Entry: {row['Action Price']}<br>Option: {row.get('Suggested Strike','—')}<br>{row['Reason']}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>💼 Your positions</div>", unsafe_allow_html=True)
for row in results['decisions']:
    st.markdown(f"<div class='info-card'><div class='med'>{row['Ticker']}</div><div class='{color_class(row['Decision'])}'>{row['Decision']} ({row['Confidence']}%)</div><div class='muted'>Action: {row['Suggested Size']}<br>Entry: {row['Action Price']}<br>Option: {row.get('Suggested Strike','—')}<br>{row['Reason']}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>🔥 Opportunities</div>", unsafe_allow_html=True)
for row in ideas[:5]:
    st.markdown(f"<div class='info-card'><div class='med'>{row['Ticker']}</div><div class='{color_class(row['Decision'])}'>{row['Decision']} ({row['Confidence']}%)</div><div class='muted'>Entry: {row['Action Price']}<br>Option: {row.get('Suggested Strike','—')}<br>{row['Simple Read']}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>📘 Trade journal</div>", unsafe_allow_html=True)
journal_path = Path('trade_journal.csv')
if journal_path.exists():
    journal = pd.read_csv(journal_path).tail(12)
    for _, j in journal.iterrows():
        st.markdown(f"<div class='info-card'><div class='med'>{j.get('ticker','—')}</div><div class='{color_class(j.get('decision',''))}'>{j.get('decision','—')} ({j.get('confidence','')})</div><div class='muted'>{j.get('timestamp_utc','')}<br>{j.get('action_price','')}</div></div>", unsafe_allow_html=True)
else:
    st.info('Trade journal will appear after the first cloud run.')

with st.expander('WSB snapshot'):
    st.dataframe(pd.DataFrame(wsb_rows).head(15), use_container_width=True)
st.caption(f'Dashboard URL: {dashboard_url}')
