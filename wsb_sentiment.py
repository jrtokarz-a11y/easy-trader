from __future__ import annotations
import re
from collections import Counter
import requests
try:
    from textblob import TextBlob
except Exception:
    TextBlob = None
COMMON_WORDS = {'THE','AND','FOR','YOU','ARE','BUT','HOLD','BUY','SELL','CALL','PUT','YOLO','GAIN','LOSS','WITH','THIS','THAT','WILL','JUST','FROM','HAVE','YOUR','ALL','NOT','OUT','NOW','WHY','WSB','EDIT','POST','LIKE','INTO','OVER','UNDER','WHEN','THEN','THAN','MAKE','MADE'}
TICKER_RE = re.compile(r'\b[A-Z]{2,5}\b')
def _extract_posts(payload):
    children = payload.get('data',{}).get('children',[])
    return [{'title': c.get('data',{}).get('title','') or '', 'body': c.get('data',{}).get('selftext','') or '', 'score': c.get('data',{}).get('score',0) or 0} for c in children]
def get_wsb_snapshot(limit=100, url=None):
    target = url or f'https://www.reddit.com/r/wallstreetbets/hot.json?limit={max(1, min(limit, 100))}'
    try:
        resp = requests.get(target, headers={'User-Agent':'easy-trader-dashboard/14.0 (public-json-fallback)'}, timeout=15)
        resp.raise_for_status(); posts = _extract_posts(resp.json())
    except Exception as exc:
        return [{'Ticker':'WSB feed unavailable','Mentions':0,'Sentiment':0.0,'Simple Read':f'Public JSON request failed: {type(exc).__name__}'}]
    mentions=Counter(); sentiments=Counter()
    for post in posts:
        text = f"{post['title']} {post['body']}".upper(); tickers=[t for t in TICKER_RE.findall(text) if t not in COMMON_WORDS]
        base = TextBlob(text).sentiment.polarity if TextBlob else 0.0; weight = max(1, min(int(post['score'] or 0),5000))/100.0
        for t in tickers:
            mentions[t]+=1; sentiments[t]+=base*weight
    if not mentions:
        return [{'Ticker':'No clear tickers found','Mentions':0,'Sentiment':0.0,'Simple Read':'WSB posts loaded, but no stock symbols were confidently detected.'}]
    rows=[]
    for t, count in mentions.most_common(50):
        sent=round(float(sentiments[t]),2); read='Crowd bullish' if sent>0.3 else 'Crowd bearish' if sent<-0.3 else 'Mixed chatter'; rows.append({'Ticker':t,'Mentions':count,'Sentiment':sent,'Simple Read':read})
    return rows
