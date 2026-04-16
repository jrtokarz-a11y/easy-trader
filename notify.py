import os, requests

def send_ntfy(message, title='Easy Trader Alert'):
    topic = os.getenv('NTFY_TOPIC')
    enabled = os.getenv('NTFY_ENABLED','false').lower() == 'true'
    if not enabled or not topic:
        return False
    resp = requests.post(f'https://ntfy.sh/{topic}', data=message.encode('utf-8'), headers={'Title':title,'Priority':'4','Tags':'chart_with_upwards_trend,moneybag'}, timeout=15)
    resp.raise_for_status()
    return True
