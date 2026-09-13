import os
import base64
import smtplib
import ssl
import requests
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TODAY_STR = date.today().strftime("%m_%d_%Y")

# --- Config pulled from environment variables (never hardcode these) ---
# Microsoft (only required if you actually send via MS Graph)
TENANT_ID = os.environ.get("MS_TENANT_ID")
CLIENT_ID = os.environ.get("MS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET")

# Google (only required if you actually send via Gmail SMTP)
# NOTE: this must be a Gmail "App Password", NOT your normal Google
# account password. Requires 2-Step Verification to be enabled on the
# account, then generate one at https://myaccount.google.com/apppasswords
GOOGLE_APP_PASSWORD = os.environ.get("GOOGLE_PASS")

GOOGLE_SMTP_HOST = "smtp.gmail.com"
GOOGLE_SMTP_PORT = 587


def get_ms_access_token():
    """
    Requests an app-only OAuth2 access token from Microsoft Entra ID
    using the client credentials flow. This token authorizes calls
    to Microsoft Graph as the app itself (no user login involved).
    """
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        raise RuntimeError(
            "MS_TENANT_ID, MS_CLIENT_ID, and MS_CLIENT_SECRET must all be set "
            "to send via Microsoft Graph."
        )

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def _send_email_ms(receiver_emails, subject, html_content, attachment_path, sender_email):
    """Send via Microsoft Graph API (app-only client credentials flow)."""
    access_token = get_ms_access_token()
    to_recipients = [{"emailAddress": {"address": addr}} for addr in receiver_emails]

    message = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": html_content,
        },
        "toRecipients": to_recipients,
    }

    if attachment_path:
        with open(attachment_path, "rb") as f:
            file_bytes = f.read()
        encoded_content = base64.b64encode(file_bytes).decode("utf-8")
        message["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": os.path.basename(attachment_path),
                "contentBytes": encoded_content,
            }
        ]

    url = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"message": message, "saveToSentItems": "true"}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 202:
        print(f"[MS] Email sent successfully to {len(receiver_emails)} recipient(s)!")
    else:
        print(f"[MS] An error occurred: {response.status_code} - {response.text}")


def _send_email_google(receiver_emails, subject, text_content, html_content,
                        attachment_path, sender_email):
    """
    Send via Gmail SMTP using an App Password.

    sender_email must be the full address the app password was generated
    for (e.g. reports@buriantech.com on Google Workspace, or
    someone@gmail.com for a personal account).
    """
    if not GOOGLE_APP_PASSWORD:
        raise RuntimeError("GOOGLE_PASS environment variable is not set.")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(receiver_emails)

    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(text_content or "", "plain"))
    alt_part.attach(MIMEText(html_content, "html"))
    msg.attach(alt_part)

    if attachment_path:
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(attachment_path)}"',
        )
        msg.attach(part)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(GOOGLE_SMTP_HOST, GOOGLE_SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(sender_email, GOOGLE_APP_PASSWORD)
            server.sendmail(sender_email, receiver_emails, msg.as_string())
        print(f"[Google] Email sent successfully to {len(receiver_emails)} recipient(s)!")
    except smtplib.SMTPException as e:
        print(f"[Google] An error occurred: {e}")


def send_email(receiver_emails, subject, text_content, html_content,
                attachment_path, sender_email, provider="ms"):
    """
    Sends an email via Microsoft Graph API or Gmail SMTP, optionally with a file attached.

    receiver_emails: list of recipient email addresses
    sender_email: the mailbox to send FROM.
                  - For provider="ms": must be a real mailbox in your MS tenant,
                    and the app must have Mail.Send permission.
                  - For provider="google": must be the address the Gmail App
                    Password (GOOGLE_PASS) was generated for.
    attachment_path: full path to a file to attach (optional, pass None to skip)
    provider: "ms" (default) or "google" - selects which service/credentials to use.
    """
    provider = provider.lower()
    if provider == "ms":
        _send_email_ms(receiver_emails, subject, html_content, attachment_path, sender_email)
    elif provider == "google":
        _send_email_google(receiver_emails, subject, text_content, html_content,
                            attachment_path, sender_email)
    else:
        raise ValueError(f"Unknown provider '{provider}'. Use 'ms' or 'google'.")


# --- Test run ---
if __name__ == "__main__":
    attachment_path = os.path.join(BASE_DIR, "Data", f"Renew_Soon.csv")
    receiver_emails = ["support@testdomain.com"]

    text_content = "Tech Doctor Report!\nBelow is the current information on Tech Doctor customers."
    html_content = """\
    <html>
      <body>
        <h2 style="color: #2e6cbb;">Tech Doctor Report!</h2>
        <p>Attached is the Tech Doctor customers that need to renew within the next 14 days.</p>
        </body>
    </html>
    """

    # Microsoft 365 send (unchanged behavior)
    send_email(
        receiver_emails,
        "Automated Tech Doctor Report",
        text_content,
        html_content,
        attachment_path,
        sender_email="info@testdomain.com",
        provider="ms",
    )

    # Gmail send example - uncomment and set sender_email to the address
    # your GOOGLE_PASS app password was generated for.
    # send_email(
    #     receiver_emails,
    #     "Automated Tech Doctor Report",
    #     text_content,
    #     html_content,
    #     attachment_path,
    #     sender_email="youraddress@gmail.com",
    #     provider="google",
    # )