import json
import os
import re
import smtplib
import ssl
import threading
import time

from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).parent

PAGES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/sign-in": "sign-in.html",
    "/volunteer": "volunteer.html",
    "/driver-verification": "driver-verification.html",
    "/request-ride": "request-ride.html",
    "/volunteer-rides": "volunteer-rides.html",
    "/ride-status": "ride-status.html",
    "/notifications": "notifications.html",
    "/profile": "profile.html",
}

HELP_RECIPIENTS = [
    "laukia2011@gmail.com",
    "lokithg2011@gmail.com",
]

EMAIL_PATTERN = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")

RATE_LOCK = threading.Lock()
RECENT_ATTEMPTS = []


def allow_submission(client):
    now = time.monotonic()

    with RATE_LOCK:
        RECENT_ATTEMPTS[:] = [
            item for item in RECENT_ATTEMPTS
            if now - item[1] < 3600
        ]

        if len(RECENT_ATTEMPTS) >= 30:
            return False

        if any(
            address == client and now - timestamp < 60
            for address, timestamp in RECENT_ATTEMPTS
        ):
            return False

        RECENT_ATTEMPTS.append((client, now))
        return True


class Drive2DocHandler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/help-widget.js":
            filename = "help-widget.js"
            content_type = "text/javascript; charset=utf-8"
        else:
            filename = PAGES.get(path)
            content_type = "text/html; charset=utf-8"

        if filename is None:
            self.send_error(404, "Page not found")
            return

        file_path = BASE_DIR / filename

        if not file_path.is_file():
            self.send_error(404, f"Missing file: {filename}")
            return

        content = file_path.read_bytes()

        # Help button ; very very important
        if content_type.startswith("text/html"):
            widget = b'<script src="/help-widget.js" defer></script>'
            content = content.replace(
                b"</body>",
                widget + b"\n</body>",
                1,
            )

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if urlparse(self.path).path != "/api/help":
            self.send_json(404, {"error": "Page not found."})
            return

        
        content_type = self.headers.get("Content-Type", "")
        if content_type.split(";")[0].strip().lower() != "application/json":
            self.send_json(415, {"error": "JSON is required."})
            return

        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.send_json(403, {"error": "Request not allowed."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid request."})
            return

        if not 0 < length <= 20000:
            self.send_json(413, {"error": "Your message is too large."})
            return

        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "Invalid request."})
            return

        if not isinstance(data, dict):
            self.send_json(400, {"error": "Invalid request."})
            return

        limits = {
            "name": 100,
            "email": 254,
            "subject": 150,
            "message": 4000,
            "page": 200,
        }

        fields = {}

        for key, limit in limits.items():
            value = data.get(key, "")
            if not isinstance(value, str) or len(value) > limit:
                self.send_json(400, {"error": "Invalid or oversized field."})
                return
            fields[key] = value.strip()

        if not all(fields[key] for key in ("name", "email", "subject", "message")):
            self.send_json(400, {"error": "Please complete every required field."})
            return

        if (
            not EMAIL_PATTERN.fullmatch(fields["email"])
            or any(
                "\r" in fields[key] or "\n" in fields[key]
                for key in ("name", "email", "subject")
            )
        ):
            self.send_json(400, {"error": "Enter a valid email and subject."})
            return

        sender = "".join(os.environ.get("GMAIL_ADDRESS", "").split())
        password = "".join(os.environ.get("GMAIL_APP_PASSWORD", "").split())

        if not sender or not password:
            self.send_json(503, {
                "error": "Help email is not configured yet. Please try later."
            })
            return


        if not allow_submission(self.client_address[0]):
            self.send_json(429, {
                "error": "Too many attempts. Please wait before trying again."
            })
            return

        email = EmailMessage()
        email["Date"] = formatdate(localtime=True)
        email["Message-ID"] = make_msgid()
        email["From"] = sender
        email["To"] = ", ".join(HELP_RECIPIENTS)
        email["Reply-To"] = fields["email"]
        email["Subject"] = f"Drive2Doc Help: {fields['subject']}"

        email.set_content(
            "A new Drive2Doc help question was submitted.\n\n"
            f"Name: {fields['name']}\n"
            f"Reply email: {fields['email']}\n"
            f"Page: {fields['page']}\n\n"
            f"Subject: {fields['subject']}\n\n"
            f"{fields['message']}\n"
        )

        try:
            with smtplib.SMTP_SSL(
                "smtp.gmail.com",
                465,
                context=ssl.create_default_context(),
                timeout=20,
            ) as smtp:
                smtp.login(sender, password)
                refused = smtp.send_message(email)

            if refused:
                self.send_json(502, {
                    "error": (
                        "The email service did not accept all recipients. "
                        "Please contact the team directly."
                    )
                })
                return

        except (smtplib.SMTPException, OSError):
            self.send_json(502, {
                "error": "We couldn't send your question. Please try again later."
            })
            return

        self.send_json(200, {
            "message": "Your question was sent to the Drive2Doc team."
        })


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Drive2DocHandler)
    print("Drive2Doc is running at http://localhost:8000")
    server.serve_forever()