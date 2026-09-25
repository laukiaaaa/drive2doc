from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BASE_DIR = Path(__file__).parent


class Drive2DocHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_html("index.html")
            return

        if self.path == "/volunteer":
            self.send_html("volunteer.html")
            return

        if self.path == "/request-ride":
            self.send_html("request-ride.html")
            return

        self.send_error(404, "Page not found")

    def send_html(self, filename):
        content = (BASE_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Drive2DocHandler)
    print("Drive2Doc is running at http://0.0.0.0:8000")
    server.serve_forever()
