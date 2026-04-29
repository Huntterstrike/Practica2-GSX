"""
Automated verification for Week 10 Kubernetes deliverables.

The script is intentionally split into small helper routines and test blocks so
it is easy to see which Kubernetes concept each check validates:

- manifest application
- resource existence
- workload readiness
- service exposure and ConfigMap injection
- in-cluster communication
- HTTP access through nginx
- scaling and self-healing
- persistent storage for both the app volume and Redis StatefulSet

Prerequisites:
- a running Kubernetes context (typically Minikube)
- local images already loaded into the cluster when needed
- kubectl available in PATH

Run with:
    py -3 verify_week10.py
"""

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
REDIS_HEADLESS_SERVICE = "redis-headless"

APP_CONFIGMAP = "simple-app-config"
NGINX_CONFIGMAP = "nginx-config"
APP_PV = "app-data-pv"
APP_PVC = "app-data-pvc"

APP_LABEL = "app=simple-app"
NGINX_LABEL = "app=nginx"
REDIS_LABEL = "app=redis"

TIMEOUT_SECONDS = 180
SLEEP_SECONDS = 5


# =========================
# HELPERS
# =========================
def run(cmd, check=True, capture_output=True, timeout=60):
    """Run a shell command and optionally fail fast if it exits with an error."""
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
    """Poll a condition until it becomes true or the timeout expires."""
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
    """Return True when a named Kubernetes resource exists."""
    result = run(["kubectl", "get", kind, name], check=False)
    return result.returncode == 0


def jsonpath_get(kind, name, path, check=True):
    """Read a single field from a Kubernetes resource using jsonpath."""
    result = run(
        ["kubectl", "get", kind, name, "-o", f"jsonpath={path}"],
        check=check
    )
    return result.stdout.strip()


def get_pod_name(label_selector):
    """Return the first pod name that matches the provided label selector."""
    result = run([
        "kubectl", "get", "pods",
        "-l", label_selector,
        "-o", "jsonpath={.items[0].metadata.name}"
    ])
    pod_name = result.stdout.strip()
    if not pod_name:
        raise RuntimeError(f"No pod found for selector: {label_selector}")
    return pod_name


def get_pod_names(label_selector):
    """Return every pod name that matches the provided label selector."""
    result = run([
        "kubectl", "get", "pods",
        "-l", label_selector,
        "-o", "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}"
    ])
    pod_names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not pod_names:
        raise RuntimeError(f"No pods found for selector: {label_selector}")
    return pod_names


def deployment_ready(name, expected_replicas=1):
    """Check whether a Deployment has the expected number of ready replicas."""
    result = run([
        "kubectl", "get", "deployment", name,
        "-o", "jsonpath={.status.readyReplicas}"
    ], check=False)
    return result.returncode == 0 and result.stdout.strip() == str(expected_replicas)


def statefulset_ready(name):
    """Check whether a StatefulSet has all desired replicas ready."""
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
    """Perform a simple HTTP GET and return the status code and response body."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


def find_free_port():
    """Ask the OS for a free localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_port_forward(resource_name, remote_port, timeout=20):
    """
    Start `kubectl port-forward` in the background and wait until the local
    socket becomes reachable.

    This is more reliable than `minikube service --url` on Windows with the
    Docker driver because that command keeps an interactive tunnel open.
    """
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
    """Terminate a background process cleanly if it is still running."""
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def exec_in_pod(pod_name, shell_cmd):
    """Execute a shell command inside a pod and return stdout."""
    result = run([
        "kubectl", "exec", pod_name, "--",
        "sh", "-c", shell_cmd
    ])
    return result.stdout.strip()


def check_equal(description, actual, expected):
    """Emit a PASS/FAIL line for an equality comparison."""
    if actual == expected:
        ok(description)
        return True
    fail(f"{description}: expected {expected!r}, got {actual!r}")
    return False


def check_nonempty(description, value):
    """Emit a PASS/FAIL line for a field that must be present."""
    if value:
        ok(description)
        return True
    fail(f"{description}: value is empty")
    return False


# =========================
# TESTS
# =========================
def test_apply_manifests():
    """Apply every manifest so the following checks run against the latest config."""
    if APPLY_MANIFESTS_FIRST:
        info("Applying manifests first...")
        run(["kubectl", "apply", "-f", MANIFESTS_PATH])
        ok("Manifests applied")


def test_resources_exist():
    """Verify that the expected Kubernetes resource objects were created."""
    checks = [
        ("deployment", NGINX_DEPLOYMENT),
        ("deployment", APP_DEPLOYMENT),
        ("statefulset", REDIS_STATEFULSET),
        ("service", NGINX_SERVICE),
        ("service", APP_SERVICE),
        ("service", REDIS_SERVICE),
        ("service", REDIS_HEADLESS_SERVICE),
        ("configmap", APP_CONFIGMAP),
        ("configmap", NGINX_CONFIGMAP),
        ("pv", APP_PV),
        ("pvc", APP_PVC),
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
    """Wait until Deployments and StatefulSet report ready replicas."""
    all_ok = True

    if not wait_until(lambda: deployment_ready(NGINX_DEPLOYMENT), "deployment/nginx ready"):
        all_ok = False

    if not wait_until(lambda: deployment_ready(APP_DEPLOYMENT), "deployment/simple-app ready"):
        all_ok = False

    if not wait_until(lambda: statefulset_ready(REDIS_STATEFULSET), "statefulset/redis ready"):
        all_ok = False

    return all_ok


def test_configuration_and_service_types():
    """Validate service exposure and the configuration injected through ConfigMaps."""
    all_ok = True

    all_ok &= check_equal(
        "service/nginx type is NodePort",
        jsonpath_get("service", NGINX_SERVICE, "{.spec.type}"),
        "NodePort"
    )
    all_ok &= check_equal(
        "service/simple-app type is ClusterIP",
        jsonpath_get("service", APP_SERVICE, "{.spec.type}"),
        "ClusterIP"
    )
    all_ok &= check_equal(
        "service/redis type is ClusterIP",
        jsonpath_get("service", REDIS_SERVICE, "{.spec.type}"),
        "ClusterIP"
    )
    all_ok &= check_equal(
        "service/redis-headless is headless",
        jsonpath_get("service", REDIS_HEADLESS_SERVICE, "{.spec.clusterIP}"),
        "None"
    )

    app_pod = get_pod_name(APP_LABEL)
    nginx_pod = get_pod_name(NGINX_LABEL)

    all_ok &= check_equal(
        "simple-app pod receives APP_MESSAGE from ConfigMap",
        exec_in_pod(app_pod, "printenv APP_MESSAGE"),
        "Hello from Kubernetes"
    )
    all_ok &= check_equal(
        "simple-app pod receives REDIS_HOST from ConfigMap",
        exec_in_pod(app_pod, "printenv REDIS_HOST"),
        "redis"
    )
    all_ok &= check_equal(
        "simple-app pod receives REDIS_PORT from ConfigMap",
        exec_in_pod(app_pod, "printenv REDIS_PORT"),
        "6379"
    )

    nginx_conf = exec_in_pod(nginx_pod, "cat /etc/nginx/conf.d/default.conf")
    if "proxy_pass http://simple-app:5000/;" in nginx_conf:
        ok("nginx pod received reverse-proxy ConfigMap")
    else:
        fail("nginx pod did not receive the expected reverse-proxy ConfigMap")
        all_ok = False

    return all_ok


def test_probes_and_resources():
    """Check that probes and CPU/memory requests/limits are present on all workloads."""
    all_ok = True

    all_ok &= check_equal(
        "nginx readiness probe path configured",
        jsonpath_get("deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].readinessProbe.httpGet.path}"),
        "/"
    )
    all_ok &= check_equal(
        "nginx liveness probe path configured",
        jsonpath_get("deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].livenessProbe.httpGet.path}"),
        "/"
    )
    all_ok &= check_equal(
        "simple-app readiness probe path configured",
        jsonpath_get("deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].readinessProbe.httpGet.path}"),
        "/health"
    )
    all_ok &= check_equal(
        "simple-app liveness probe path configured",
        jsonpath_get("deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].livenessProbe.httpGet.path}"),
        "/health"
    )
    all_ok &= check_equal(
        "redis readiness probe command configured",
        jsonpath_get("statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].readinessProbe.exec.command[0]}"),
        "redis-cli"
    )
    all_ok &= check_equal(
        "redis liveness probe command configured",
        jsonpath_get("statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].livenessProbe.exec.command[0]}"),
        "redis-cli"
    )

    resource_checks = [
        ("nginx CPU request", "deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.requests.cpu}"),
        ("nginx memory request", "deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.requests.memory}"),
        ("nginx CPU limit", "deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.limits.cpu}"),
        ("nginx memory limit", "deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.limits.memory}"),
        ("simple-app CPU request", "deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.requests.cpu}"),
        ("simple-app memory request", "deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.requests.memory}"),
        ("simple-app CPU limit", "deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.limits.cpu}"),
        ("simple-app memory limit", "deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].resources.limits.memory}"),
        ("redis CPU request", "statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].resources.requests.cpu}"),
        ("redis memory request", "statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].resources.requests.memory}"),
        ("redis CPU limit", "statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].resources.limits.cpu}"),
        ("redis memory limit", "statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].resources.limits.memory}"),
    ]

    for description, kind, name, path in resource_checks:
        all_ok &= check_nonempty(description, jsonpath_get(kind, name, path))

    return all_ok


def test_redis_ping():
    """Confirm that the Redis pod is alive and accepting commands."""
    redis_pod = get_pod_name(REDIS_LABEL)
    output = exec_in_pod(redis_pod, "redis-cli ping")
    if output.strip() == "PONG":
        ok("Redis responds with PONG")
        return True
    fail(f"Redis ping failed: {output}")
    return False


def test_in_cluster_connectivity():
    """Validate service-name communication between the workloads inside the cluster."""
    all_ok = True

    nginx_pod = get_pod_name(NGINX_LABEL)
    app_pod = get_pod_name(APP_LABEL)

    nginx_to_app = exec_in_pod(nginx_pod, "curl -fsS http://simple-app:5000/")
    if nginx_to_app:
        ok("nginx reaches simple-app through the ClusterIP service")
        info(f"nginx -> simple-app response: {nginx_to_app}")
    else:
        fail("nginx could not reach simple-app through the ClusterIP service")
        all_ok = False

    app_to_redis = exec_in_pod(
        app_pod,
        "python -c 'import socket; s=socket.create_connection((\"redis\", 6379), 5); print(\"OK\"); s.close()'"
    )
    all_ok &= check_equal(
        "simple-app reaches redis through the service name",
        app_to_redis,
        "OK"
    )

    return all_ok


def test_http_endpoints():
    """Expose nginx locally with port-forward and verify external HTTP access."""
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


def test_scaling():
    """Scale nginx up and back down to prove replica management works."""
    all_ok = True

    run(["kubectl", "scale", f"deployment/{NGINX_DEPLOYMENT}", "--replicas=3"])
    if not wait_until(
        lambda: deployment_ready(NGINX_DEPLOYMENT, expected_replicas=3),
        "deployment/nginx scaled to 3 replicas"
    ):
        all_ok = False

    run(["kubectl", "scale", f"deployment/{NGINX_DEPLOYMENT}", "--replicas=1"])
    if not wait_until(
        lambda: deployment_ready(NGINX_DEPLOYMENT, expected_replicas=1),
        "deployment/nginx scaled back to 1 replica"
    ):
        all_ok = False

    return all_ok


def test_resilience():
    """Delete an nginx pod and verify the Deployment recreates it automatically."""
    old_pod = get_pod_name(NGINX_LABEL)
    run(["kubectl", "delete", "pod", old_pod])

    recreated = wait_until(
        lambda: deployment_ready(NGINX_DEPLOYMENT) and get_pod_name(NGINX_LABEL) != old_pod,
        "deployment/nginx recreates a deleted pod"
    )
    return recreated


def test_persistence():
    """Write to the app PVC, restart the Deployment, and verify the data remains."""
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


def test_redis_persistence():
    """Write a Redis key, recreate the Redis pod, and verify the key survives."""
    marker = f"redis-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    write_output = exec_in_pod("redis-0", f"redis-cli set week10:persistence {marker}")
    if write_output.strip() != "OK":
        fail(f"Could not write persistence marker to Redis: {write_output}")
        return False
    ok("Redis persistence marker written")

    run(["kubectl", "delete", "pod", "redis-0"])
    if not wait_until(lambda: statefulset_ready(REDIS_STATEFULSET), "statefulset/redis ready after pod recreation"):
        return False

    read_output = exec_in_pod("redis-0", "redis-cli get week10:persistence")
    if read_output.strip() == marker:
        ok("Redis data survives StatefulSet pod recreation")
        return True

    fail("Redis data did not survive StatefulSet pod recreation")
    return False


# =========================
# MAIN
# =========================
def main():
    """Run the verification suite sequentially and summarize the outcome."""
    tests = [
        ("Apply manifests", test_apply_manifests),
        ("Resources exist", test_resources_exist),
        ("Workloads ready", test_workloads_ready),
        ("Configuration and service types", test_configuration_and_service_types),
        ("Probes and resources", test_probes_and_resources),
        ("Redis ping", test_redis_ping),
        ("In-cluster connectivity", test_in_cluster_connectivity),
        ("HTTP endpoints", test_http_endpoints),
        ("Scaling", test_scaling),
        ("Resilience", test_resilience),
        ("Persistence", test_persistence),
        ("Redis persistence", test_redis_persistence),
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
