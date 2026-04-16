from __future__ import annotations
import math
import pandas as pd
import yfinance as yf
BENCHMARKS = ['SPY','QQQ','DIA','BTC-USD','ETH-USD']
DEFAULT_SCAN_UNIVERSE = ['SPY','QQQ','IWM','SMH','SOXL','ARKK','XLF','XLE','XLK','AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','PLTR','SOFI','MU','RKLB','ASTS','RIVN','PLUG','AMD','INTC']

def _find_col(df, opts):
    for c in opts:
        if c in df.columns: return c
    return None

def _symbol_col(df):
    c = _find_col(df,['Symbol','Ticker','symbol','ticker'])
    if not c: raise ValueError('CSV needs a Symbol or Ticker column.')
    return c

def _decision(m20,m60,vr):
    if m20>=0.10 and m60>=0.15 and vr>=1.2: return 'BUY'
    if m20>=0.04 and m60>=0 and vr>=0.9: return 'HOLD / ADD'
    if m20<=-0.10 and m60<=-0.12: return 'SELL / CUT RISK'
    if m20<=-0.04: return 'REDUCE'
    return 'DO NOTHING'

def _confidence(m20,m60,vr,rel):
    score=50
    score += max(-20,min(20,m20*200))
    score += max(-15,min(15,m60*100))
    score += max(-10,min(10,(vr-1.0)*25))
    score += max(-10,min(10,rel*100))
    return int(max(5,min(95,round(score))))

def _size(decision, conf):
    if decision=='BUY':
        if conf>=85: return 'Buy 8% to 10% of portfolio'
        if conf>=70: return 'Buy 5% to 7% of portfolio'
        return 'Buy 2% to 4% of portfolio'
    if decision=='HOLD / ADD':
        if conf>=75: return 'Add 2% to 3%'
        return 'Hold current size'
    if decision=='REDUCE': return 'Trim 25% to 35%'
    if decision=='SELL / CUT RISK': return 'Sell half or more'
    return 'No change'

def _reason(decision):
    return {'BUY':'Price is rising and buyers are active.','HOLD / ADD':'Trend is positive, but not explosive.','REDUCE':'Trend is getting weaker.','SELL / CUT RISK':'Price is falling hard and risk is high.','DO NOTHING':'No strong edge right now.'}[decision]

def _action_prices(last_price, decision):
    if decision=='BUY': return f'Buy near ${round(last_price*0.98,2)}', f'Stop near ${round(last_price*0.93,2)}'
    if decision=='HOLD / ADD': return f'Add near ${round(last_price*0.97,2)}', f'Stop near ${round(last_price*0.92,2)}'
    if decision=='REDUCE': return f'Trim near ${round(last_price*1.02,2)}', 'Use a tight stop'
    if decision=='SELL / CUT RISK': return f'Exit near ${round(last_price*0.99,2)}', 'Protect capital first'
    return f'Watch above ${round(last_price*1.03,2)}', 'No stop needed'

def _suggested_strike(last_price, decision):
    if not last_price or math.isnan(last_price): return '—'
    step = 1 if last_price < 25 else 2.5 if last_price < 100 else 5 if last_price < 200 else 10
    if decision in {'BUY','HOLD / ADD'}:
        strike = math.ceil((last_price*1.05)/step)*step; opt='Call'
    elif decision in {'SELL / CUT RISK','REDUCE'}:
        strike = math.floor((last_price*0.95)/step)*step; opt='Put'
    else:
        strike = round(last_price/step)*step; opt='Watch'
    strike = int(strike) if float(strike).is_integer() else round(strike,2)
    return f'{opt} {strike}'

def _extract_metrics(frame):
    close = frame['Close'].dropna(); vol = frame['Volume'].dropna()
    last = float(close.iloc[-1])
    m20 = float((close.iloc[-1]/close.iloc[-21])-1) if len(close)>21 else 0.0
    m60 = float((close.iloc[-1]/close.iloc[-61])-1) if len(close)>61 else 0.0
    vr = float(vol.iloc[-1]/max(vol.tail(60).mean(),1)) if len(vol) else 1.0
    return last,m20,m60,vr

def analyze_holdings(holdings):
    col = _symbol_col(holdings)
    holdings = holdings.copy(); holdings['Symbol'] = holdings[col].astype(str).str.upper().str.strip()
    shares_col = _find_col(holdings,['Shares','shares','Quantity','quantity'])
    cost_col = _find_col(holdings,['CostBasis','costbasis','AvgCost','avgcost','AverageCost'])
    tickers = sorted(set(holdings['Symbol'].tolist())); data = yf.download(tickers+BENCHMARKS, period='1y', interval='1d', auto_adjust=True, progress=False, group_by='ticker')
    spy = data['SPY']['Close'].dropna(); qqq = data['QQQ']['Close'].dropna()
    spy20 = float((spy.iloc[-1]/spy.iloc[-21])-1) if len(spy)>21 else 0.0
    qqq20 = float((qqq.iloc[-1]/qqq.iloc[-21])-1) if len(qqq)>21 else 0.0
    decisions=[]; profits=[]
    for _, row in holdings.iterrows():
        t = row['Symbol']
        try:
            last,m20,m60,vr = _extract_metrics(data[t]); rel = m20-spy20
            dec = _decision(m20,m60,vr); conf = _confidence(m20,m60,vr,rel); size = _size(dec,conf); reason = _reason(dec); action,risk = _action_prices(last,dec)
            decisions.append({'Ticker':t,'Last Price':round(last,2),'Decision':dec,'Confidence':conf,'Suggested Size':size,'Action Price':action,'Risk Line':risk,'Suggested Strike':_suggested_strike(last,dec),'Reason':reason})
            shares = float(row[shares_col]) if shares_col and pd.notna(row[shares_col]) else None
            cost = float(row[cost_col]) if cost_col and pd.notna(row[cost_col]) else None
            if shares is not None and cost is not None:
                mv = round(shares*last,2); tv = round(shares*cost,2); pnl = round(mv-tv,2); pnl_pct = round((pnl/tv)*100,2) if tv else None
                profits.append({'Ticker':t,'Shares':shares,'Avg Cost':round(cost,2),'Last Price':round(last,2),'Market Value':mv,'Cost Value':tv,'Profit $':pnl,'Profit %':pnl_pct})
        except Exception:
            continue
    avg = sum(d['Confidence'] for d in decisions)/max(len(decisions),1)
    mood = 'Bullish' if spy20>0.03 and qqq20>0.03 else 'Bearish' if spy20<-0.03 and qqq20<-0.03 else 'Mixed'
    buys = sum(1 for d in decisions if d['Decision']=='BUY'); sells = sum(1 for d in decisions if d['Decision']=='SELL / CUT RISK')
    health = 'Strong' if buys>sells else 'Weak' if sells>buys else 'Neutral'
    actionable = [d for d in decisions if d['Decision'] in {'BUY','HOLD / ADD','REDUCE','SELL / CUT RISK'}]
    top = sorted(actionable, key=lambda x:x['Confidence'], reverse=True)[:3]
    best = top[0] if top else {'Ticker':'None','Decision':'No strong setup','Confidence':0}
    total_profit = round(sum(r['Profit $'] for r in profits),2) if profits else 0.0
    lines = ['HOURLY EASY TRADER REPORT','',f'Market mood: {mood}',f'Portfolio health: {health}',f'Average confidence: {avg:.0f}%',f'Tracked profit: ${total_profit}','','BEST TRADE RIGHT NOW',f"{best.get('Ticker')}: {best.get('Decision')} | {best.get('Confidence')}% | {best.get('Action Price','')} | Strike {best.get('Suggested Strike','')}",'','TOP 3 TRADES TODAY']
    for r in top:
        lines.append(f"{r['Ticker']}: {r['Decision']} | {r['Confidence']}% | {r['Suggested Size']} | {r['Action Price']} | {r['Reason']}")
    return {'summary':{'market_mood':mood,'portfolio_health':health,'avg_confidence':avg},'decisions':decisions,'profit_tracking':profits,'top_trades':top,'best_trade_right_now':best,'email_report':'\n'.join(lines)}

def scan_trending_ideas(holdings, wsb_rows, max_results=5):
    owned = set(holdings[_symbol_col(holdings)].astype(str).str.upper().str.strip().tolist())
    watch = list(DEFAULT_SCAN_UNIVERSE)
    for row in wsb_rows:
        t = str(row.get('Ticker','')).upper().strip()
        if t and t not in watch and t not in {'WSB FEED UNAVAILABLE','NO CLEAR TICKERS FOUND'}: watch.append(t)
    scan = [t for t in watch if t not in owned][:30]
    if not scan: return []
    data = yf.download(scan+['SPY'], period='1y', interval='1d', auto_adjust=True, progress=False, group_by='ticker')
    spy = data['SPY']['Close'].dropna(); spy20 = float((spy.iloc[-1]/spy.iloc[-21])-1) if len(spy)>21 else 0.0
    wmap = {str(r.get('Ticker','')).upper():r for r in wsb_rows}; ideas=[]
    for t in scan:
        try:
            last,m20,m60,vr = _extract_metrics(data[t]); rel = m20-spy20; dec = _decision(m20,m60,vr); base = _confidence(m20,m60,vr,rel)
            info = wmap.get(t,{}); mentions = int(info.get('Mentions',0) or 0); sentiment = float(info.get('Sentiment',0) or 0)
            bonus = min(10, mentions//3) + (5 if sentiment>0.3 and dec in {'BUY','HOLD / ADD'} else 0); penalty = 5 if sentiment<-0.3 and dec in {'SELL / CUT RISK','REDUCE'} else 0
            conf = max(5,min(95,base+bonus+penalty)); action,_ = _action_prices(last,dec)
            ideas.append({'Ticker':t,'Last Price':round(last,2),'Decision':dec,'Confidence':conf,'Action Price':action,'Suggested Strike':_suggested_strike(last,dec),'Mentions':mentions,'Sentiment':round(sentiment,2),'Simple Read':info.get('Simple Read','No crowd read'),'Reason':_reason(dec)})
        except Exception:
            continue
    actionable=[r for r in ideas if r['Decision']!='DO NOTHING']
    return sorted(actionable, key=lambda x:(x['Confidence'],x['Mentions']), reverse=True)[:max_results]
def get_top_5_trades(holdings, results, ideas):
    combined = []

    # From your portfolio
    for r in results["top_trades"]:
        combined.append({
            "Ticker": r["Ticker"],
            "Decision": r["Decision"],
            "Confidence": r["Confidence"],
            "Source": "Portfolio",
            "Reason": r["Reason"]
        })

    # From trending ideas (WSB + momentum)
    for r in ideas:
        combined.append({
            "Ticker": r["Ticker"],
            "Decision": r["Decision"],
            "Confidence": r["Confidence"],
            "Source": "WSB + Market",
            "Reason": r["Reason"]
        })

    # Sort and dedupe
    seen = set()
    final = []
    for r in sorted(combined, key=lambda x: x["Confidence"], reverse=True):
        if r["Ticker"] not in seen:
            final.append(r)
            seen.add(r["Ticker"])
        if len(final) == 5:
            break

    return final
