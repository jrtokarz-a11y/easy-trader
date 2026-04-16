import smtplib
from email.mime.text import MIMEText

def send_email(report_text, sender, app_password, receiver):
    msg = MIMEText(report_text)
    msg['Subject'] = 'Hourly Easy Trader Report'
    msg['From'] = sender
    msg['To'] = receiver
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, app_password)
        server.send_message(msg)
