import os
from io import StringIO
import requests
import pandas as pd
from analyzer import analyze_holdings, scan_trending_ideas
from wsb_sentiment import get_wsb_snapshot
from emailer import send_email
from notify import send_ntfy
from journal import append_journal

def load_holdings():
    file_id = os.getenv('HOLDINGS_FILE_ID'); csv_url = os.getenv('HOLDINGS_CSV_URL')
    if file_id: csv_url = f'https://drive.google.com/uc?export=download&id={file_id}'
    if not csv_url: raise RuntimeError('Set HOLDINGS_FILE_ID or HOLDINGS_CSV_URL')
    resp = requests.get(csv_url, timeout=20); resp.raise_for_status(); return pd.read_csv(StringIO(resp.text))

def main():
    holdings = load_holdings(); results = analyze_holdings(holdings); ideas = scan_trending_ideas(holdings, get_wsb_snapshot(), max_results=5); best = results['best_trade_right_now']
    dashboard_url = os.getenv('DASHBOARD_URL', 'https://YOUR-APP.streamlit.app')
    report = results['email_report'] + '\n\nTRENDING IDEAS OUTSIDE YOUR PORTFOLIO\n'
    for row in ideas:
        report += f"{row['Ticker']}: {row['Decision']} | {row['Confidence']}% | {row['Action Price']} | Strike {row['Suggested Strike']} | {row['Simple Read']}\n"
    report += '\nOpen dashboard: ' + dashboard_url
    if os.getenv('EMAIL_ENABLED','true').lower() == 'true':
        send_email(report, os.environ['EMAIL_SENDER'], os.environ['EMAIL_APP_PASSWORD'], os.environ['EMAIL_RECIPIENT'])
    send_ntfy(f"{best.get('Ticker')}: {best.get('Decision')} | {best.get('Confidence')}% | {best.get('Action Price','')} | Strike {best.get('Suggested Strike','')}", title='Best trade right now')
    append_journal(best, results['top_trades'], ideas)
    print(report)

if __name__ == '__main__':
    main()
