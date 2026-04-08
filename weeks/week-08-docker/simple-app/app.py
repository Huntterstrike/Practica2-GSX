from http.server import BaseHTTPRequestHandler, HTTPServer
import os


HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "5000"))
MESSAGE = os.getenv("APP_MESSAGE", "Hello from container")


class Handler(BaseHTTPRequestHandler):
    def _send_text(self, status_code: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_text(200, MESSAGE)
            return

        if self.path == "/health":
            self._send_text(200, "OK")
            return

        self._send_text(404, "Not Found")

    def log_message(self, format: str, *args) -> None:
        # Keep container logs focused on startup/runtime issues.
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Listening on {HOST}:{PORT}")
    server.serve_forever()
