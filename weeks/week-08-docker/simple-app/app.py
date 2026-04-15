from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import redis

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "5000"))
MESSAGE = os.getenv("APP_MESSAGE", "Hello from container")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Connect to Redis
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

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
            visits = r.incr("visits")
            self._send_text(200, f"{MESSAGE} | Visits: {visits}")
            return

        if self.path == "/health":
            try:
                r.ping()
                self._send_text(200, "OK")
            except Exception:
                self._send_text(500, "Redis unavailable")
            return

        self._send_text(404, "Not Found")

    def log_message(self, format: str, *args) -> None:
        return

if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Listening on {HOST}:{PORT}")
    server.serve_forever()