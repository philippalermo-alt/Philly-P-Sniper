import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config
from utils import log

class EmailNotifier:
    """Handles sending email notifications via SMTP."""
    
    def __init__(self):
        self.host = Config.EMAIL_HOST
        self.port = Config.EMAIL_PORT
        self.user = Config.EMAIL_USER
        self.password = Config.EMAIL_PASSWORD
        self.recipient = Config.EMAIL_RECIPIENT

    def send_email(self, subject, body, is_html=True):
        """
        Send an email to the configured recipient.
        
        Args:
            subject (str): Email subject line.
            body (str): Email body content (HTML or Plain Text).
            is_html (bool): True to send as HTML, False for plain text.
        """
        if not self.user or not self.password or not self.recipient:
            log("EMAIL", "⚠️ Email credentials missing in config. Skipping email.")
            return False

        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = self.recipient
        msg['Subject'] = subject

        # Attach body
        mime_type = 'html' if is_html else 'plain'
        msg.attach(MIMEText(body, mime_type))

        try:
            # Create unverified SSL context (for self-signed certs)
            context = ssl._create_unverified_context()
            
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls(context=context) # Secure the connection
                server.login(self.user, self.password)
                server.sendmail(self.user, self.recipient, msg.as_string())
            
            log("EMAIL", f"✅ Email sent to {self.recipient}: {subject}")
            return True
            
        except Exception as e:
            log("EMAIL", f"❌ Failed to send email: {e}")
            return False

# Quick test if run directly
if __name__ == "__main__":
    notifier = EmailNotifier()
    notifier.send_email("Test Alert", "<h1>This is a test from Philly P Sniper</h1>")
