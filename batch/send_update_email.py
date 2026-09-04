#!/usr/bin/env python3
"""Send the order-form / checklist update email via the Gmail HTTPS API.

Attachments are read straight off disk and encoded by this script, so file
size is irrelevant - nothing has to pass through a model's output.

Credentials come from the environment (never commit them):

    GMAIL_CLIENT_ID       OAuth client id
    GMAIL_CLIENT_SECRET   OAuth client secret
    GMAIL_REFRESH_TOKEN   refresh token with the gmail.send scope
    MAIL_TO               comma-separated recipients

Usage:
    python3 send_update_email.py --subject "..." --html body.html \
        --attach output/checklist.pdf --attach "output/37_foo.png"
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def require_env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"missing required environment variable: {name}")
    return value


def access_token():
    """Exchange the long-lived refresh token for a short-lived access token."""
    payload = urllib.parse.urlencode({
        "client_id": require_env("GMAIL_CLIENT_ID"),
        "client_secret": require_env("GMAIL_CLIENT_SECRET"),
        "refresh_token": require_env("GMAIL_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=payload)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def build_message(to, subject, html, attachments):
    msg = EmailMessage()
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content("This message contains HTML and attachments.")
    msg.add_alternative(html, subtype="html")

    for path in attachments:
        ctype, _ = mimetypes.guess_type(path)
        maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
        with open(path, "rb") as fh:
            msg.add_attachment(
                fh.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(path),
            )
    return msg


def send(msg, token):
    body = json.dumps({
        "raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()
    }).encode()
    req = urllib.request.Request(
        SEND_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--html", required=True, help="path to the HTML body")
    parser.add_argument("--attach", action="append", default=[],
                        help="file to attach (repeatable)")
    parser.add_argument("--to", help="override MAIL_TO")
    parser.add_argument("--dry-run", action="store_true",
                        help="build the message and report its size, but do not send")
    args = parser.parse_args()

    to = [addr.strip() for addr in (args.to or require_env("MAIL_TO")).split(",") if addr.strip()]

    missing = [p for p in args.attach if not os.path.exists(p)]
    if missing:
        sys.exit("attachment(s) not found: " + ", ".join(missing))

    with open(args.html, encoding="utf-8") as fh:
        html = fh.read()

    msg = build_message(to, args.subject, html, args.attach)

    if args.dry_run:
        print(f"to:          {', '.join(to)}")
        print(f"subject:     {args.subject}")
        for path in args.attach:
            print(f"attachment:  {path} ({os.path.getsize(path):,} bytes)")
        print(f"total size:  {len(msg.as_bytes()):,} bytes")
        print("dry run - not sent")
        return

    result = send(msg, access_token())
    print("sent, message id:", result.get("id"))


if __name__ == "__main__":
    main()
