import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

class EmailSender:
    def __init__(self):
        """
        Initializes the EmailSender with settings from environment variables.
        """
        self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.example.com')
        self.SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
        self.USERNAME = os.getenv('SMTP_USERNAME', 'your-sender@example.com')
        self.PASSWORD = os.getenv('SMTP_PASSWORD')
        
        if not self.USERNAME:
            raise ValueError("SMTP_USERNAME environment variable is required (sender email account)")
        if not self.PASSWORD:
            raise ValueError("SMTP_PASSWORD environment variable is required (sender email account password)")

    def send_email(self, subject, body, notification_email, attachment_paths=None, html_body=None):
        """
        Sends an email with the provided subject, body, and recipient email address.
        Optionally includes multiple attachments and HTML body.

        :param subject: Subject of the email
        :param body: Plain text body of the email
        :param notification_email: Recipient email address
        :param attachment_paths: List of paths to files to be attached (optional)
        :param html_body: HTML version of the email body (optional)
        """
        # Create a multipart message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.USERNAME
        msg['To'] = notification_email

        # Attach the plain text body
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach HTML body if provided
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))

        # If attachment paths are provided, attach them to the email
        if attachment_paths:
            for attachment_path in attachment_paths:
                if os.path.isfile(attachment_path):
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={os.path.basename(attachment_path)}',
                        )
                        msg.attach(part)

        try:
            # Connect to the SMTP server and send the email
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()  # Secure the connection
                server.login(self.USERNAME, self.PASSWORD)  # Login to the SMTP server
                server.sendmail(self.USERNAME, notification_email, msg.as_string())  # Send the email
            print(f"Email sent successfully to {notification_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")
