from __future__ import annotations

import html
import secrets
import threading
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


SESSIONS: dict[str, dict] = {}


def page(body: str, title: str = "Local Careers") -> bytes:
    return f"""<!doctype html><html><head><meta charset=utf-8><title>{title}</title>
<style>body{{font:16px system-ui;max-width:720px;margin:40px auto}}label{{display:block;margin:12px 0}}
input,textarea{{display:block;width:100%;padding:8px}}button{{padding:10px 18px}}</style></head>
<body><h1>{title}</h1>{body}</body></html>""".encode()


class TestSiteHandler(BaseHTTPRequestHandler):
    uploads: Path = Path("artifacts/testsite_uploads")

    def log_message(self, format: str, *args) -> None:
        return

    def send_page(self, body: str, status: int = 200, title: str = "Local Careers") -> None:
        data = page(body, title)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self.send_page(
                '<p>Controlled research environment.</p><a id="apply" href="/apply">Apply</a>'
            )
        elif route == "/apply":
            self.send_page(
                """<form method=post action=/step1>
<label>Full name<input name=name required autocomplete=name></label>
<label>Email<input name=email type=email required autocomplete=email></label>
<label>Start date<input name=start_date type=date required></label>
<button>Continue</button></form>""",
                title="Application step 1",
            )
        elif route == "/health":
            data = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        content_type = self.headers.get("Content-Type", "")
        if content_type.startswith("multipart/form-data"):
            length = int(self.headers.get("Content-Length", 0))
            message = BytesParser(policy=default).parsebytes(
                b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + self.rfile.read(length)
            )
            values, uploaded = {}, None
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if part.get_filename():
                    uploaded = part.get_payload(decode=True)
                elif name:
                    values[name] = part.get_content()
        else:
            length = int(self.headers.get("Content-Length", 0))
            values = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
            uploaded = None
        if route == "/step1":
            missing = [key for key in ("name", "email", "start_date") if not values.get(key)]
            if missing:
                self.send_page(f"<p class=error>Missing {html.escape(', '.join(missing))}</p>", 422)
                return
            token = secrets.token_hex(12)
            SESSIONS[token] = values
            self.send_page(
                f"""<form method=post enctype=multipart/form-data action=/step2>
<input type=hidden name=token value={token}>
<label>Resume<input name=resume type=file accept=.pdf required></label>
<label>Why this role?<textarea name=motivation required></textarea></label>
<label><input name=ai_used type=checkbox value=yes required>I truthfully disclose that AI assisted this answer.</label>
<button>Continue</button></form>""",
                title="Application step 2",
            )
        elif route == "/step2":
            token = str(values.get("token", ""))
            if (
                token not in SESSIONS
                or uploaded is None
                or not values.get("motivation")
                or values.get("ai_used") != "yes"
            ):
                self.send_page("<p class=error>Validation failed</p>", 422)
                return
            self.uploads.mkdir(parents=True, exist_ok=True)
            blob = uploaded
            (self.uploads / f"{token}.pdf").write_bytes(blob)
            SESSIONS[token].update(
                {"motivation": values["motivation"], "ai_used": "yes", "resume_bytes": len(blob)}
            )
            self.send_page(
                f"""<form method=post action=/submit>
<input type=hidden name=token value={token}>
<p>Verification challenge: enter the result of 7 + 6. This is not a CAPTCHA.</p>
<label>Answer<input name=verification required></label>
<button id=submit>Submit controlled application</button></form>""",
                title="Verification",
            )
        elif route == "/submit":
            token = str(values.get("token", ""))
            if token not in SESSIONS or values.get("verification") != "13":
                self.send_page("<p class=error>Incorrect verification answer</p>", 422)
                return
            confirmation = f"LOCAL-{token.upper()}"
            SESSIONS[token]["confirmation"] = confirmation
            self.send_page(
                f'<p id="success">Application submitted.</p><code id="confirmation">{confirmation}</code>',
                title="Complete",
            )
        else:
            self.send_error(404)


def serve(host: str = "127.0.0.1", port: int = 0, upload_dir: str | Path | None = None):
    if upload_dir:
        TestSiteHandler.uploads = Path(upload_dir)
    server = ThreadingHTTPServer((host, port), TestSiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
