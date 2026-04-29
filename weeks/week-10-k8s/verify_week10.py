import subprocess
import sys
import time
import socket
import urllib.request
import urllib.error
from datetime import datetime, UTC

# =========================
# CONFIG
# =========================
APPLY_MANIFESTS_FIRST = True
MANIFESTS_PATH = "kubernetes"

NGINX_DEPLOYMENT = "nginx"
APP_DEPLOYMENT = "simple-app"
REDIS_STATEFULSET = "redis"

NGINX_SERVICE = "nginx"
APP_SERVICE = "simple-app"
REDIS_SERVICE = "redis"

APP_LABEL = "app=simple-app"
NGINX_LABEL = "app=nginx"
REDIS_LABEL = "app=redis"

TIMEOUT_SECONDS = 180
SLEEP_SECONDS = 5


# =========================
# HELPERS
# =========================
def run(cmd, check=True, capture_output=True, timeout=60):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=capture_output,
        timeout=timeout
    )
    if check and result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result


def ok(msg):
    print(f"[PASS] {msg}")


def fail(msg):
    print(f"[FAIL] {msg}")


def info(msg):
    print(f"[INFO] {msg}")


def wait_until(condition_fn, description, timeout=TIMEOUT_SECONDS, interval=SLEEP_SECONDS):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if condition_fn():
                ok(description)
                return True
        except Exception as e:
            info(f"Waiting for {description}: {e}")
        time.sleep(interval)
    fail(description)
    return False


def resource_exists(kind, name):
    result = run(["kubectl", "get", kind, name], check=False)
    return result.returncode == 0


def get_pod_name(label_selector):
    result = run([
        "kubectl", "get", "pods",
        "-l", label_selector,
        "-o", "jsonpath={.items[0].metadata.name}"
    ])
    pod_name = result.stdout.strip()
    if not pod_name:
        raise RuntimeError(f"No pod found for selector: {label_selector}")
    return pod_name


def deployment_ready(name):
    result = run([
        "kubectl", "get", "deployment", name,
        "-o", "jsonpath={.status.readyReplicas}"
    ], check=False)
    return result.returncode == 0 and result.stdout.strip() == "1"


def statefulset_ready(name):
    ready = run([
        "kubectl", "get", "statefulset", name,
        "-o", "jsonpath={.status.readyReplicas}"
    ], check=False)
    replicas = run([
        "kubectl", "get", "statefulset", name,
        "-o", "jsonpath={.spec.replicas}"
    ], check=False)

    return (
        ready.returncode == 0 and
        replicas.returncode == 0 and
        ready.stdout.strip() != "" and
        ready.stdout.strip() == replicas.stdout.strip()
    )


def http_get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_port_forward(resource_name, remote_port, timeout=20):
    local_port = find_free_port()
    cmd = [
        "kubectl", "port-forward",
        resource_name,
        f"{local_port}:{remote_port}"
    ]
    print(f"$ {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    start = time.time()
    while time.time() - start < timeout:
        if process.poll() is not None:
            output = ""
            if process.stdout:
                output = process.stdout.read()
            raise RuntimeError(
                f"Port-forward for {resource_name} exited early. Output:\n{output}"
            )

        try:
            with socket.create_connection(("127.0.0.1", local_port), timeout=1):
                return process, f"http://127.0.0.1:{local_port}"
        except OSError:
            time.sleep(0.5)

    process.terminate()
    raise RuntimeError(f"Timed out starting port-forward for {resource_name}")


def stop_process(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def exec_in_pod(pod_name, shell_cmd):
    result = run([
        "kubectl", "exec", pod_name, "--",
        "sh", "-c", shell_cmd
    ])
    return result.stdout.strip()


# =========================
# TESTS
# =========================
def test_apply_manifests():
    if APPLY_MANIFESTS_FIRST:
        info("Applying manifests first...")
        run(["kubectl", "apply", "-f", MANIFESTS_PATH])
        ok("Manifests applied")


def test_resources_exist():
    checks = [
        ("deployment", NGINX_DEPLOYMENT),
        ("deployment", APP_DEPLOYMENT),
        ("statefulset", REDIS_STATEFULSET),
        ("service", NGINX_SERVICE),
        ("service", APP_SERVICE),
        ("service", REDIS_SERVICE),
    ]

    all_ok = True
    for kind, name in checks:
        if resource_exists(kind, name):
            ok(f"{kind}/{name} exists")
        else:
            fail(f"{kind}/{name} exists")
            all_ok = False
    return all_ok


def test_workloads_ready():
    all_ok = True

    if not wait_until(lambda: deployment_ready(NGINX_DEPLOYMENT), "deployment/nginx ready"):
        all_ok = False

    if not wait_until(lambda: deployment_ready(APP_DEPLOYMENT), "deployment/simple-app ready"):
        all_ok = False

    if not wait_until(lambda: statefulset_ready(REDIS_STATEFULSET), "statefulset/redis ready"):
        all_ok = False

    return all_ok


def test_redis_ping():
    redis_pod = get_pod_name(REDIS_LABEL)
    output = exec_in_pod(redis_pod, "redis-cli ping")
    if output.strip() == "PONG":
        ok("Redis responds with PONG")
        return True
    fail(f"Redis ping failed: {output}")
    return False


def test_http_endpoints():
    port_forward = None
    all_ok = True

    try:
        port_forward, base_url = start_port_forward(f"service/{NGINX_SERVICE}", 80)
        info(f"Nginx URL via port-forward: {base_url}")

        try:
            status, body = http_get(base_url)
            if status == 200:
                ok("Nginx root endpoint returns HTTP 200")
            else:
                fail(f"Nginx root endpoint returned HTTP {status}")
                all_ok = False
        except Exception as e:
            fail(f"Nginx root endpoint failed: {e}")
            all_ok = False

        api_candidates = [
            base_url.rstrip("/") + "/api/",
            base_url.rstrip("/") + "/api",
        ]

        api_ok = False
        for api_url in api_candidates:
            try:
                status, body = http_get(api_url)
                if status == 200:
                    ok(f"Backend reachable through Nginx: {api_url}")
                    print(f"[INFO] Backend response: {body}")
                    api_ok = True
                    break
            except urllib.error.HTTPError as e:
                info(f"{api_url} returned HTTP {e.code}")
            except Exception as e:
                info(f"{api_url} failed: {e}")

        if not api_ok:
            fail("Backend not reachable through Nginx /api")
            all_ok = False

        return all_ok
    finally:
        stop_process(port_forward)


def test_persistence():
    marker = f"week10-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    app_pod_before = get_pod_name(APP_LABEL)

    write_cmd = f"echo {marker} > /data/test.txt && cat /data/test.txt"
    output = exec_in_pod(app_pod_before, write_cmd)

    if output.strip() != marker:
        fail("Could not write marker file to /data")
        return False
    ok("Marker file written to /data")

    run(["kubectl", "rollout", "restart", f"deployment/{APP_DEPLOYMENT}"])
    if not wait_until(lambda: deployment_ready(APP_DEPLOYMENT), "deployment/simple-app ready after restart"):
        return False

    # Wait for pod replacement/readiness
    time.sleep(5)

    app_pod_after = get_pod_name(APP_LABEL)
    read_output = exec_in_pod(app_pod_after, "cat /data/test.txt")

    if read_output.strip() == marker:
        ok("Persistent data survives app restart")
        return True

    fail("Persistent data did not survive app restart")
    return False


# =========================
# MAIN
# =========================
def main():
    tests = [
        ("Apply manifests", test_apply_manifests),
        ("Resources exist", test_resources_exist),
        ("Workloads ready", test_workloads_ready),
        ("Redis ping", test_redis_ping),
        ("HTTP endpoints", test_http_endpoints),
        ("Persistence", test_persistence),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        print("\n" + "=" * 60)
        print(f"TEST: {name}")
        print("=" * 60)

        try:
            result = fn()
            if result is False:
                failed += 1
            else:
                passed += 1
        except Exception as e:
            fail(f"{name} crashed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
