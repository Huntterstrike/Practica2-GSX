from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import threading
import time
from urllib.parse import urlparse

import redis


HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "5000"))
MESSAGE = os.getenv("APP_MESSAGE", "Hello from Kubernetes")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

LATENCY_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")]

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

metrics_lock = threading.Lock()
request_counts = defaultdict(int)
latency_bucket_counts = defaultdict(lambda: [0] * len(LATENCY_BUCKETS))
latency_sums = defaultdict(float)
latency_counts = defaultdict(int)
error_counts = defaultdict(int)
redis_operation_counts = defaultdict(int)
redis_connections_active = 0


def prom_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def format_labels(labels):
    if not labels:
        return ""
    parts = [f'{key}="{prom_escape(str(value))}"' for key, value in labels.items()]
    return "{" + ",".join(parts) + "}"


def format_metric_line(name, value, labels=None):
    return f"{name}{format_labels(labels or {})} {value}"


def record_request(method, endpoint, status_code, latency_seconds):
    with metrics_lock:
        request_counts[(method, endpoint, str(status_code))] += 1
        latency_counts[endpoint] += 1
        latency_sums[endpoint] += latency_seconds
        for index, bucket in enumerate(LATENCY_BUCKETS):
            if latency_seconds <= bucket:
                latency_bucket_counts[endpoint][index] += 1


def record_error(error_type, endpoint):
    with metrics_lock:
        error_counts[(error_type, endpoint)] += 1


def record_redis_operation(operation):
    with metrics_lock:
        redis_operation_counts[operation] += 1


def set_redis_connections_active(value):
    global redis_connections_active
    with metrics_lock:
        redis_connections_active = value


def refresh_redis_gauge():
    try:
        info = redis_client.info("clients")
        set_redis_connections_active(int(info.get("connected_clients", 0)))
    except Exception:
        set_redis_connections_active(0)


def render_metrics():
    refresh_redis_gauge()

    lines = [
        "# HELP app_requests_total Total HTTP requests handled by simple-app.",
        "# TYPE app_requests_total counter",
    ]

    with metrics_lock:
        request_snapshot = dict(request_counts)
        latency_bucket_snapshot = {key: list(value) for key, value in latency_bucket_counts.items()}
        latency_sum_snapshot = dict(latency_sums)
        latency_count_snapshot = dict(latency_counts)
        error_snapshot = dict(error_counts)
        redis_ops_snapshot = dict(redis_operation_counts)
        redis_connections_snapshot = redis_connections_active

    for (method, endpoint, status_code), value in sorted(request_snapshot.items()):
        lines.append(
            format_metric_line(
                "app_requests_total",
                value,
                {
                    "method": method,
                    "endpoint": endpoint,
                    "http_status": status_code,
                },
            )
        )

    lines.extend(
        [
            "# HELP app_request_latency_seconds Latency histogram for simple-app requests.",
            "# TYPE app_request_latency_seconds histogram",
        ]
    )

    for endpoint in sorted(latency_count_snapshot):
        bucket_values = latency_bucket_snapshot.get(endpoint, [0] * len(LATENCY_BUCKETS))
        for bucket, value in zip(LATENCY_BUCKETS, bucket_values):
            bucket_label = "+Inf" if bucket == float("inf") else bucket
            lines.append(
                format_metric_line(
                    "app_request_latency_seconds_bucket",
                    value,
                    {"endpoint": endpoint, "le": bucket_label},
                )
            )
        lines.append(
            format_metric_line(
                "app_request_latency_seconds_sum",
                round(latency_sum_snapshot.get(endpoint, 0.0), 6),
                {"endpoint": endpoint},
            )
        )
        lines.append(
            format_metric_line(
                "app_request_latency_seconds_count",
                latency_count_snapshot.get(endpoint, 0),
                {"endpoint": endpoint},
            )
        )

    lines.extend(
        [
            "# HELP app_errors_total Total application errors grouped by type and endpoint.",
            "# TYPE app_errors_total counter",
        ]
    )

    for (error_type, endpoint), value in sorted(error_snapshot.items()):
        lines.append(
            format_metric_line(
                "app_errors_total",
                value,
                {"type": error_type, "endpoint": endpoint},
            )
        )

    lines.extend(
        [
            "# HELP app_redis_connections_active Active Redis connections seen by simple-app.",
            "# TYPE app_redis_connections_active gauge",
            format_metric_line("app_redis_connections_active", redis_connections_snapshot),
            "# HELP app_redis_operations_total Redis operations performed by simple-app.",
            "# TYPE app_redis_operations_total counter",
        ]
    )

    for operation, value in sorted(redis_ops_snapshot.items()):
        lines.append(
            format_metric_line(
                "app_redis_operations_total",
                value,
                {"operation": operation},
            )
        )

    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def _send_bytes(self, status_code, body, content_type):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status_code, body, content_type="text/plain; charset=utf-8"):
        self._send_bytes(status_code, body.encode("utf-8"), content_type)

    def _handle_path(self, path):
        if path == "/":
            try:
                visits = redis_client.incr("visits")
                record_redis_operation("incr")
            except Exception:
                record_error("redis_error", path)
                return 503, "Redis unavailable", "text/plain; charset=utf-8"

            return 200, f"{MESSAGE} | Visits: {visits}", "text/plain; charset=utf-8"

        if path == "/health":
            try:
                redis_client.ping()
                record_redis_operation("ping")
            except Exception:
                record_error("redis_error", path)
                return 500, "Redis unavailable", "text/plain; charset=utf-8"

            return 200, "OK", "text/plain; charset=utf-8"

        if path == "/slow":
            time.sleep(2)
            return 200, "Slow request completed", "text/plain; charset=utf-8"

        if path == "/error":
            record_error("simulated_error", path)
            return 500, "Simulated error", "text/plain; charset=utf-8"

        if path == "/metrics":
            return 200, render_metrics(), "text/plain; version=0.0.4; charset=utf-8"

        return 404, "Not Found", "text/plain; charset=utf-8"

    def do_GET(self):
        path = urlparse(self.path).path
        started_at = time.time()
        status_code = 500

        try:
            status_code, body, content_type = self._handle_path(path)
            self._send_text(status_code, body, content_type)
        except BrokenPipeError:
            pass
        except Exception:
            status_code = 500
            record_error("unexpected_error", path)
            try:
                self._send_text(status_code, "Internal Server Error")
            except BrokenPipeError:
                pass
        finally:
            latency = time.time() - started_at
            record_request("GET", path, status_code, latency)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Listening on {HOST}:{PORT} with /metrics enabled")
    server.serve_forever()
