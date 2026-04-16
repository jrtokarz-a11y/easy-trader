import requests

def get_wsb_snapshot(limit=10):
    try:
        url = "https://apewisdom.io/api/v1.0/filter/all-stocks"
        r = requests.get(url, timeout=10)
        data = r.json()["results"]

        rows = []
        for stock in data[:limit]:
            sentiment = stock.get("sentiment", 0)

            if sentiment > 0.6:
                simple = "Crowd very bullish"
            elif sentiment > 0.2:
                simple = "Crowd bullish"
            elif sentiment < -0.2:
                simple = "Crowd bearish"
            else:
                simple = "Mixed chatter"

            rows.append({
                "Ticker": stock["ticker"],
                "Mentions": stock["mentions"],
                "Sentiment": round(sentiment, 2),
                "Simple Read": simple
            })

        return rows

    except Exception as e:
        return [{
            "Ticker": "WSB unavailable",
            "Mentions": 0,
            "Sentiment": 0,
            "Simple Read": str(e)
        }]
