from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
JOURNAL_PATH = Path('trade_journal.csv')

def append_journal(best_trade, top_trades, ideas):
    rows=[]; ts = datetime.now(timezone.utc).isoformat()
    if best_trade:
        rows.append({'timestamp_utc':ts,'type':'best_trade','ticker':best_trade.get('Ticker'),'decision':best_trade.get('Decision'),'confidence':best_trade.get('Confidence'),'action_price':best_trade.get('Action Price'),'suggested_strike':best_trade.get('Suggested Strike',''),'note':'Best trade right now'})
    for row in top_trades[:3]:
        rows.append({'timestamp_utc':ts,'type':'top_trade','ticker':row.get('Ticker'),'decision':row.get('Decision'),'confidence':row.get('Confidence'),'action_price':row.get('Action Price'),'suggested_strike':row.get('Suggested Strike',''),'note':'Top 3 trade'})
    for row in ideas[:3]:
        rows.append({'timestamp_utc':ts,'type':'outside_idea','ticker':row.get('Ticker'),'decision':row.get('Decision'),'confidence':row.get('Confidence'),'action_price':row.get('Action Price'),'suggested_strike':row.get('Suggested Strike',''),'note':row.get('Simple Read','')})
    new_df = pd.DataFrame(rows)
    out = pd.concat([pd.read_csv(JOURNAL_PATH), new_df], ignore_index=True) if JOURNAL_PATH.exists() else new_df
    out.to_csv(JOURNAL_PATH, index=False)
