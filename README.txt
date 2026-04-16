Easy Trader Dashboard V14 - Mobile Cloud Assistant

What this package includes
- Mobile-first Streamlit dashboard
- Google Drive holdings file support
- GitHub Actions hourly email runner
- Best trade right now alert
- Phone push notifications with ntfy
- Trade journal saved in trade_journal.csv
- Outside trending ideas from Yahoo Finance + WSB fallback

SUPER SIMPLE SETUP

1. Put your holdings CSV in Google Drive
Format:
Symbol,Shares,CostBasis
AAPL,10,180
TSLA,5,240
NVDA,3,900

2. Share the CSV
- Right-click the file in Google Drive
- Share
- Set General access to "Anyone with the link"
- Copy the file link

3. Get the Google Drive file ID
From a link like:
https://drive.google.com/file/d/FILE_ID/view
copy the FILE_ID part

4. Upload this whole folder to a new GitHub repo

5. Deploy app.py on Streamlit Community Cloud

6. Add Streamlit secrets
holdings_file_id="YOUR_GOOGLE_DRIVE_FILE_ID"
dashboard_url="https://YOUR-APP.streamlit.app"

7. Add GitHub repo secrets
HOLDINGS_FILE_ID = YOUR_GOOGLE_DRIVE_FILE_ID
DASHBOARD_URL = your Streamlit app URL
EMAIL_ENABLED = true
EMAIL_SENDER = your Gmail
EMAIL_APP_PASSWORD = your Gmail app password
EMAIL_RECIPIENT = where you want the report sent

8. Optional phone push notifications
- Install the ntfy app on your phone
- Subscribe to a random topic name like easytrader-john-4821
- Add these GitHub secrets:
  NTFY_ENABLED = true
  NTFY_TOPIC = easytrader-john-4821

9. Turn on GitHub Actions
- Open the Actions tab in your repo
- Enable workflows
- Run the workflow once manually if you want a test

10. Use it on iPhone
- Open your Streamlit app URL in Safari
- Tap Share
- Add to Home Screen
