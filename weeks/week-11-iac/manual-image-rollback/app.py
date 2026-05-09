from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from urllib.parse import urlparse

import redis


HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "5000"))
MESSAGE = os.getenv("APP_MESSAGE", "Hello from Docker Compose")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


class Handler(BaseHTTPRequestHandler):
    def _send_text(self, status_code: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/":
            try:
                visits = redis_client.incr("visits")
            except Exception:
                self._send_text(503, "Redis unavailable")
                return

            self._send_text(200, f"{MESSAGE} | Visits: {visits} | Image: rollback-new")
            return

        if path == "/health":
            try:
                redis_client.ping()
            except Exception:
                self._send_text(500, "Redis unavailable")
                return

            self._send_text(200, "OK")
            return

        self._send_text(404, "Not Found")

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Listening on {HOST}:{PORT}")
    server.serve_forever()
