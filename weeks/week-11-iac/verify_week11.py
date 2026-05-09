"""
Automated verification for Week 11 Terraform + CI/CD deliverables.

The script mirrors the same checks used during the manual validation:

- build both application images
- load the deployable images into Minikube
- validate Terraform configuration
- recreate the dev environment from scratch
- verify Kubernetes resources, probes, connectivity, scaling, resilience,
  persistence, and rollback behaviour in dev
- deploy an independent staging environment from the same Terraform codebase
- confirm Terraform idempotence in both workspaces
- statically verify that the GitHub Actions workflow includes the required
  CI, security, caching, SBOM, and tagging steps

Run with:
    py -3 weeks/week-11-iac/verify_week11.py
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TERRAFORM_DIR = SCRIPT_DIR / "terraform"
DEV_TFVARS = TERRAFORM_DIR / "environments" / "dev.tfvars"
STAGING_TFVARS = TERRAFORM_DIR / "environments" / "staging.tfvars"
NGINX_CONTEXT = Path("weeks/week-08-docker/nginx")
APP_DOCKERFILE = Path("weeks/week-11-iac/docker/simple-app.Dockerfile")
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

DEV_NAMESPACE = "green-dev-dev"
STAGING_NAMESPACE = "green-dev-staging"
DEV_MESSAGE = "Hello from Terraform dev"
STAGING_MESSAGE = "Hello from Terraform staging"
ROLLBACK_MESSAGE = "Hello from Terraform rollback candidate"
DEV_NODE_PORT = "31080"
STAGING_NODE_PORT = "31081"
DEV_PV = "green-dev-dev-app-data-pv"
STAGING_PV = "green-dev-staging-app-data-pv"

NGINX_DEPLOYMENT = "nginx"
APP_DEPLOYMENT = "simple-app"
REDIS_STATEFULSET = "redis"

NGINX_SERVICE = "nginx"
APP_SERVICE = "simple-app"
REDIS_SERVICE = "redis"
REDIS_HEADLESS_SERVICE = "redis-headless"

APP_CONFIGMAP = "simple-app-config"
NGINX_CONFIGMAP = "nginx-config"
APP_PVC = "app-data-pvc"

NGINX_LABEL = "app=nginx"
APP_LABEL = "app=simple-app"
REDIS_LABEL = "app=redis"

TIMEOUT_SECONDS = 180
SLEEP_SECONDS = 5


def run(
    cmd: list[str],
    *,
    cwd: Path = REPO_ROOT,
    check: bool = True,
    capture_output: bool = True,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    """Run a command and optionally fail fast when it exits with an error."""
    print(f"$ {' '.join(str(part) for part in cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        timeout=timeout,
    )

    if check and result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}")

    return result


def ok(message: str) -> None:
    print(f"[PASS] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def info(message: str) -> None:
    print(f"[INFO] {message}")


def current_context() -> str:
    """Return the active kubectl context name when available."""
    result = run(["kubectl", "config", "current-context"], check=False, timeout=20)
    if result.returncode != 0:
        return "<unknown>"
    return result.stdout.strip() or "<unknown>"


def cluster_accessible() -> bool:
    """Return True when kubectl can reach the active Kubernetes API server."""
    result = run(["kubectl", "cluster-info"], check=False, timeout=20)
    return result.returncode == 0


def minikube_running() -> bool:
    """Return True when the Minikube control plane reports a running state."""
    result = run(["minikube", "status"], check=False, timeout=20)
    status_output = f"{result.stdout}\n{result.stderr}"
    return (
        result.returncode == 0
        and "host: Running" in status_output
        and "apiserver: Running" in status_output
    )


def docker_daemon_accessible() -> bool:
    """Return True when the Docker daemon answers server-side API requests."""
    result = run(["docker", "version", "--format", "{{.Server.Version}}"], check=False, timeout=20)
    return result.returncode == 0 and bool(result.stdout.strip())


def wait_until(condition_fn, description: str, timeout: int = TIMEOUT_SECONDS, interval: int = SLEEP_SECONDS) -> bool:
    """Poll a condition until it becomes true or timeout expires."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            if condition_fn():
                ok(description)
                return True
        except Exception as exc:
            info(f"Waiting for {description}: {exc}")
        time.sleep(interval)
    fail(description)
    return False


def check_equal(description: str, actual: str, expected: str) -> bool:
    """Emit PASS/FAIL for an equality assertion."""
    if actual == expected:
        ok(description)
        return True
    fail(f"{description}: expected {expected!r}, got {actual!r}")
    return False


def check_contains(description: str, actual: str, expected_fragment: str) -> bool:
    """Emit PASS/FAIL for a substring assertion."""
    if expected_fragment in actual:
        ok(description)
        return True
    fail(f"{description}: expected fragment {expected_fragment!r} not found")
    return False


def check_nonempty(description: str, actual: str) -> bool:
    """Emit PASS/FAIL for a non-empty assertion."""
    if actual:
        ok(description)
        return True
    fail(f"{description}: value is empty")
    return False


def kubectl_cmd(namespace: str | None = None) -> list[str]:
    """Return a base kubectl command, optionally scoped to a namespace."""
    cmd = ["kubectl"]
    if namespace:
        cmd.extend(["-n", namespace])
    return cmd


def resource_exists(kind: str, name: str, namespace: str | None = None) -> bool:
    """Return True when the requested Kubernetes resource exists."""
    result = run(kubectl_cmd(namespace) + ["get", kind, name], check=False)
    return result.returncode == 0


def jsonpath_get(kind: str, name: str, path: str, namespace: str | None = None, check: bool = True) -> str:
    """Read a field from a Kubernetes resource using jsonpath."""
    result = run(
        kubectl_cmd(namespace) + ["get", kind, name, "-o", f"jsonpath={path}"],
        check=check,
    )
    return result.stdout.strip()


def get_pod_name(label_selector: str, namespace: str) -> str:
    """Return the first pod name matching the label selector."""
    result = run(
        kubectl_cmd(namespace)
        + ["get", "pods", "-l", label_selector, "-o", "jsonpath={.items[0].metadata.name}"]
    )
    pod_name = result.stdout.strip()
    if not pod_name:
        raise RuntimeError(f"No pod found for selector {label_selector!r} in namespace {namespace}")
    return pod_name


def get_pod_names(label_selector: str, namespace: str) -> list[str]:
    """Return all pod names matching the label selector."""
    result = run(
        kubectl_cmd(namespace)
        + ["get", "pods", "-l", label_selector, "-o", "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}"]
    )
    pod_names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not pod_names:
        raise RuntimeError(f"No pods found for selector {label_selector!r} in namespace {namespace}")
    return pod_names


def exec_in_pod(pod_name: str, namespace: str, shell_cmd: str, *, container: str | None = None) -> str:
    """Execute a shell command inside a pod and return stdout."""
    cmd = kubectl_cmd(namespace) + ["exec", pod_name]
    if container:
        cmd.extend(["-c", container])
    cmd.extend(["--", "sh", "-c", shell_cmd])
    result = run(cmd)
    return result.stdout.strip()


def deployment_ready(name: str, namespace: str, expected_replicas: int = 1) -> bool:
    """Check whether a Deployment has the expected number of ready replicas."""
    result = run(
        kubectl_cmd(namespace) + ["get", "deployment", name, "-o", "jsonpath={.status.readyReplicas}"],
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == str(expected_replicas)


def statefulset_ready(name: str, namespace: str) -> bool:
    """Check whether a StatefulSet has all desired replicas ready."""
    ready = run(
        kubectl_cmd(namespace) + ["get", "statefulset", name, "-o", "jsonpath={.status.readyReplicas}"],
        check=False,
    )
    replicas = run(
        kubectl_cmd(namespace) + ["get", "statefulset", name, "-o", "jsonpath={.spec.replicas}"],
        check=False,
    )
    return (
        ready.returncode == 0
        and replicas.returncode == 0
        and ready.stdout.strip() != ""
        and ready.stdout.strip() == replicas.stdout.strip()
    )


def namespace_absent(namespace: str) -> bool:
    """Return True when the namespace no longer exists."""
    result = run(["kubectl", "get", "namespace", namespace], check=False)
    return result.returncode != 0


def http_get(url: str, timeout: int = 10) -> tuple[int, str]:
    """Perform a simple HTTP GET and return the status code and body."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


def find_free_port() -> int:
    """Ask the OS for a free localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_port_forward(namespace: str, resource_name: str, remote_port: int, timeout: int = 20):
    """Start a kubectl port-forward process and wait until it becomes reachable."""
    local_port = find_free_port()
    cmd = kubectl_cmd(namespace) + ["port-forward", resource_name, f"{local_port}:{remote_port}"]
    print(f"$ {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    start = time.time()
    while time.time() - start < timeout:
        if process.poll() is not None:
            output = ""
            if process.stdout:
                output = process.stdout.read()
            raise RuntimeError(f"Port-forward for {resource_name} exited early. Output:\n{output}")

        try:
            with socket.create_connection(("127.0.0.1", local_port), timeout=1):
                return process, f"http://127.0.0.1:{local_port}"
        except OSError:
            time.sleep(0.5)

    process.terminate()
    raise RuntimeError(f"Timed out starting port-forward for {resource_name}")


def stop_process(process) -> None:
    """Terminate a background process cleanly if it is still running."""
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def terraform_cmd(*args: str, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run Terraform in the week 11 Terraform directory."""
    return run(["terraform", *args], cwd=TERRAFORM_DIR, check=check, timeout=timeout)


def ensure_workspace(name: str) -> None:
    """Create the workspace when needed, otherwise select it."""
    listed = terraform_cmd("workspace", "list").stdout
    workspaces = {line.replace("*", "").strip() for line in listed.splitlines() if line.strip()}
    if name in workspaces:
        terraform_cmd("workspace", "select", name)
    else:
        terraform_cmd("workspace", "new", name)


def terraform_apply(var_file: Path, extra_vars: list[str] | None = None) -> None:
    """Apply the Terraform stack for the selected workspace."""
    cmd = ["apply", "-var-file", str(var_file), "-auto-approve"]
    if extra_vars:
        cmd.extend(extra_vars)
    terraform_cmd(*cmd, timeout=300)


def terraform_destroy(var_file: Path) -> None:
    """Destroy the Terraform stack for the selected workspace."""
    terraform_cmd("destroy", "-var-file", str(var_file), "-auto-approve", timeout=300)


def check_plan_is_clean(var_file: Path, description: str) -> bool:
    """Validate Terraform idempotence using detailed exit codes."""
    result = terraform_cmd(
        "plan",
        "-var-file",
        str(var_file),
        "-detailed-exitcode",
        check=False,
        timeout=180,
    )
    if result.returncode == 0:
        ok(description)
        return True
    if result.returncode == 2:
        fail(f"{description}: Terraform still reports pending changes")
        return False
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    fail(f"{description}: terraform plan failed")
    return False


def test_prerequisites() -> bool:
    """Confirm the required CLIs exist and the local infrastructure is reachable."""
    all_ok = True
    commands = [
        ("Terraform is available", ["terraform", "version"]),
        ("kubectl is available", ["kubectl", "version", "--client"]),
        ("minikube is available", ["minikube", "version"]),
        ("docker CLI is available", ["docker", "--version"]),
    ]

    for description, cmd in commands:
        try:
            run(cmd, timeout=30)
            ok(description)
        except Exception as exc:
            fail(f"{description}: {exc}")
            all_ok = False

    context = current_context()
    all_ok &= check_equal("kubectl current context is minikube", context, "minikube")

    if docker_daemon_accessible():
        ok("Docker daemon is reachable")
    else:
        fail("Docker daemon is reachable")
        all_ok = False

    if minikube_running():
        ok("Minikube control plane is running")
    else:
        fail("Minikube control plane is running")
        all_ok = False

    if cluster_accessible():
        ok("Kubernetes API is reachable through kubectl")
    else:
        fail("Kubernetes API is reachable through kubectl")
        all_ok = False

    return all_ok


def test_build_images() -> bool:
    """Build the Docker images locally and inside the Minikube runtime."""
    run(["docker", "build", "-t", "nginx-gsx:latest", str(NGINX_CONTEXT)], timeout=600)
    ok("nginx image builds locally with Docker")

    run(
        [
            "docker",
            "build",
            "-t",
            "simple-app-gsx:latest",
            "-f",
            str(APP_DOCKERFILE),
            str(REPO_ROOT),
        ],
        timeout=600,
    )
    ok("simple-app image builds locally with Docker")

    run(["minikube", "image", "build", "-t", "nginx-gsx:latest", str(NGINX_CONTEXT)], timeout=900)
    ok("nginx image builds inside Minikube")

    run(
        [
            "minikube",
            "image",
            "build",
            "-t",
            "simple-app-gsx:latest",
            "-f",
            str(APP_DOCKERFILE),
            str(REPO_ROOT),
        ],
        timeout=900,
    )
    ok("simple-app image builds inside Minikube")
    return True


def test_terraform_validation() -> bool:
    """Run formatting and validation checks on the Terraform code."""
    terraform_cmd("fmt", "-check", "-recursive")
    ok("terraform fmt -check passes")

    terraform_cmd("init", "-backend=false")
    ok("terraform init -backend=false passes")

    terraform_cmd("validate")
    ok("terraform validate passes")
    return True


def deploy_environment(workspace: str, namespace: str, var_file: Path) -> bool:
    """Destroy any previous instance and recreate the environment from scratch."""
    ensure_workspace(workspace)
    terraform_destroy(var_file)
    if not wait_until(
        lambda: namespace_absent(namespace),
        f"namespace/{namespace} removed after destroy",
        timeout=120,
        interval=3,
    ):
        return False
    terraform_apply(var_file)
    return True


def wait_for_environment(namespace: str) -> bool:
    """Wait for nginx, backend, and redis to become ready."""
    all_ok = True
    all_ok &= wait_until(lambda: deployment_ready(NGINX_DEPLOYMENT, namespace), f"deployment/{NGINX_DEPLOYMENT} ready in {namespace}")
    all_ok &= wait_until(lambda: deployment_ready(APP_DEPLOYMENT, namespace), f"deployment/{APP_DEPLOYMENT} ready in {namespace}")
    all_ok &= wait_until(lambda: statefulset_ready(REDIS_STATEFULSET, namespace), f"statefulset/{REDIS_STATEFULSET} ready in {namespace}")
    return all_ok


def test_terraform_outputs(namespace: str, node_port: str, app_pv: str) -> bool:
    """Validate the Terraform outputs for the selected workspace."""
    all_ok = True
    all_ok &= check_equal("terraform output namespace", terraform_cmd("output", "-raw", "namespace").stdout.strip(), namespace)
    all_ok &= check_equal("terraform output nginx_node_port", terraform_cmd("output", "-raw", "nginx_node_port").stdout.strip(), node_port)
    all_ok &= check_equal(
        "terraform output app_persistent_volume_name",
        terraform_cmd("output", "-raw", "app_persistent_volume_name").stdout.strip(),
        app_pv,
    )
    all_ok &= check_equal(
        "terraform output nginx_image",
        terraform_cmd("output", "-raw", "nginx_image").stdout.strip(),
        "nginx-gsx:latest",
    )
    all_ok &= check_equal(
        "terraform output simple_app_image",
        terraform_cmd("output", "-raw", "simple_app_image").stdout.strip(),
        "simple-app-gsx:latest",
    )
    return all_ok


def test_resources_exist(namespace: str, app_pv: str) -> bool:
    """Verify that the expected resource objects were created."""
    checks = [
        ("deployment", NGINX_DEPLOYMENT, namespace),
        ("deployment", APP_DEPLOYMENT, namespace),
        ("statefulset", REDIS_STATEFULSET, namespace),
        ("service", NGINX_SERVICE, namespace),
        ("service", APP_SERVICE, namespace),
        ("service", REDIS_SERVICE, namespace),
        ("service", REDIS_HEADLESS_SERVICE, namespace),
        ("configmap", APP_CONFIGMAP, namespace),
        ("configmap", NGINX_CONFIGMAP, namespace),
        ("pvc", APP_PVC, namespace),
        ("pv", app_pv, None),
        ("namespace", namespace, None),
    ]

    all_ok = True
    for kind, name, target_namespace in checks:
        if resource_exists(kind, name, target_namespace):
            ok(f"{kind}/{name} exists")
        else:
            fail(f"{kind}/{name} exists")
            all_ok = False
    return all_ok


def test_configuration_and_service_types(namespace: str, expected_message: str, expected_node_port: str) -> bool:
    """Validate service exposure and configuration injection."""
    all_ok = True
    all_ok &= check_equal(
        f"service/{NGINX_SERVICE} type is NodePort in {namespace}",
        jsonpath_get("service", NGINX_SERVICE, "{.spec.type}", namespace),
        "NodePort",
    )
    all_ok &= check_equal(
        f"service/{NGINX_SERVICE} nodePort matches tfvars in {namespace}",
        jsonpath_get("service", NGINX_SERVICE, "{.spec.ports[0].nodePort}", namespace),
        expected_node_port,
    )
    all_ok &= check_equal(
        f"service/{APP_SERVICE} type is ClusterIP in {namespace}",
        jsonpath_get("service", APP_SERVICE, "{.spec.type}", namespace),
        "ClusterIP",
    )
    all_ok &= check_equal(
        f"service/{REDIS_SERVICE} type is ClusterIP in {namespace}",
        jsonpath_get("service", REDIS_SERVICE, "{.spec.type}", namespace),
        "ClusterIP",
    )
    all_ok &= check_equal(
        f"service/{REDIS_HEADLESS_SERVICE} is headless in {namespace}",
        jsonpath_get("service", REDIS_HEADLESS_SERVICE, "{.spec.clusterIP}", namespace),
        "None",
    )

    app_pod = get_pod_name(APP_LABEL, namespace)
    nginx_pod = get_pod_name(NGINX_LABEL, namespace)

    all_ok &= check_equal(
        f"simple-app receives APP_MESSAGE in {namespace}",
        exec_in_pod(app_pod, namespace, "printenv APP_MESSAGE", container="simple-app"),
        expected_message,
    )
    all_ok &= check_equal(
        f"simple-app receives REDIS_HOST in {namespace}",
        exec_in_pod(app_pod, namespace, "printenv REDIS_HOST", container="simple-app"),
        "redis",
    )
    all_ok &= check_equal(
        f"simple-app receives REDIS_PORT in {namespace}",
        exec_in_pod(app_pod, namespace, "printenv REDIS_PORT", container="simple-app"),
        "6379",
    )

    nginx_conf = exec_in_pod(nginx_pod, namespace, "cat /etc/nginx/conf.d/default.conf", container="nginx")
    all_ok &= check_contains(
        f"nginx ConfigMap reverse proxy is mounted in {namespace}",
        nginx_conf,
        "proxy_pass http://simple-app:5000/;",
    )
    return all_ok


def test_probes_and_resources(namespace: str) -> bool:
    """Check probe definitions and resource requests/limits."""
    all_ok = True
    all_ok &= check_equal(
        f"nginx readiness path is configured in {namespace}",
        jsonpath_get("deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].readinessProbe.httpGet.path}", namespace),
        "/",
    )
    all_ok &= check_equal(
        f"nginx liveness path is configured in {namespace}",
        jsonpath_get("deployment", NGINX_DEPLOYMENT, "{.spec.template.spec.containers[0].livenessProbe.httpGet.path}", namespace),
        "/",
    )
    all_ok &= check_equal(
        f"simple-app readiness path is configured in {namespace}",
        jsonpath_get("deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].readinessProbe.httpGet.path}", namespace),
        "/health",
    )
    all_ok &= check_equal(
        f"simple-app liveness path is configured in {namespace}",
        jsonpath_get("deployment", APP_DEPLOYMENT, "{.spec.template.spec.containers[0].livenessProbe.httpGet.path}", namespace),
        "/health",
    )
    all_ok &= check_equal(
        f"redis readiness command is configured in {namespace}",
        jsonpath_get("statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].readinessProbe.exec.command[0]}", namespace),
        "redis-cli",
    )
    all_ok &= check_equal(
        f"redis liveness command is configured in {namespace}",
        jsonpath_get("statefulset", REDIS_STATEFULSET, "{.spec.template.spec.containers[0].livenessProbe.exec.command[0]}", namespace),
        "redis-cli",
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
        all_ok &= check_nonempty(f"{description} is set in {namespace}", jsonpath_get(kind, name, path, namespace))
    return all_ok


def test_redis_ping(namespace: str) -> bool:
    """Confirm that Redis is up and responding."""
    output = exec_in_pod("redis-0", namespace, "redis-cli ping", container="redis")
    return check_equal(f"redis responds with PONG in {namespace}", output, "PONG")


def test_in_cluster_connectivity(namespace: str, expected_message: str) -> bool:
    """Validate service discovery and in-cluster communication."""
    all_ok = True
    nginx_pod = get_pod_name(NGINX_LABEL, namespace)
    app_pod = get_pod_name(APP_LABEL, namespace)

    nginx_to_app = exec_in_pod(nginx_pod, namespace, "curl -fsS http://simple-app:5000/", container="nginx")
    all_ok &= check_contains(f"nginx reaches simple-app in {namespace}", nginx_to_app, expected_message)

    app_to_redis = exec_in_pod(
        app_pod,
        namespace,
        "python -c 'import socket; s=socket.create_connection((\"redis\", 6379), 5); print(\"OK\"); s.close()'",
        container="simple-app",
    )
    all_ok &= check_equal(f"simple-app reaches redis in {namespace}", app_to_redis, "OK")
    return all_ok


def test_http_endpoints(namespace: str, expected_message: str) -> bool:
    """Expose nginx locally with port-forward and verify HTTP responses."""
    process = None
    all_ok = True
    try:
        process, base_url = start_port_forward(namespace, f"service/{NGINX_SERVICE}", 80)
        info(f"Nginx URL via port-forward for {namespace}: {base_url}")

        status, body = http_get(base_url)
        all_ok &= check_equal(f"nginx root endpoint returns HTTP 200 in {namespace}", str(status), "200")
        all_ok &= check_nonempty(f"nginx root response body is not empty in {namespace}", body.strip())

        status, body = http_get(base_url.rstrip("/") + "/api/")
        all_ok &= check_equal(f"backend is reachable through nginx in {namespace}", str(status), "200")
        all_ok &= check_contains(f"backend response contains the expected message in {namespace}", body, expected_message)
        return all_ok
    finally:
        stop_process(process)


def test_scaling(namespace: str) -> bool:
    """Scale nginx up and back down."""
    all_ok = True
    run(kubectl_cmd(namespace) + ["scale", f"deployment/{NGINX_DEPLOYMENT}", "--replicas=3"])
    all_ok &= wait_until(
        lambda: deployment_ready(NGINX_DEPLOYMENT, namespace, expected_replicas=3),
        f"deployment/{NGINX_DEPLOYMENT} scales to 3 replicas in {namespace}",
    )

    run(kubectl_cmd(namespace) + ["scale", f"deployment/{NGINX_DEPLOYMENT}", "--replicas=1"])
    all_ok &= wait_until(
        lambda: deployment_ready(NGINX_DEPLOYMENT, namespace, expected_replicas=1),
        f"deployment/{NGINX_DEPLOYMENT} scales back to 1 replica in {namespace}",
    )
    return all_ok


def test_resilience(namespace: str) -> bool:
    """Delete an nginx pod and verify the Deployment replaces it."""
    old_pod = get_pod_name(NGINX_LABEL, namespace)
    run(kubectl_cmd(namespace) + ["delete", "pod", old_pod], timeout=120)
    return wait_until(
        lambda: deployment_ready(NGINX_DEPLOYMENT, namespace) and get_pod_name(NGINX_LABEL, namespace) != old_pod,
        f"deployment/{NGINX_DEPLOYMENT} recreates a deleted pod in {namespace}",
    )


def test_app_persistence(namespace: str) -> bool:
    """Write data to the app volume, restart the app, and verify the data survives."""
    marker = f"week11-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    app_pod = get_pod_name(APP_LABEL, namespace)
    written = exec_in_pod(app_pod, namespace, f"echo {marker} > /data/test.txt && cat /data/test.txt", container="simple-app")
    if written != marker:
        fail(f"Could not write the backend persistence marker in {namespace}")
        return False
    ok(f"backend persistence marker written in {namespace}")

    run(kubectl_cmd(namespace) + ["rollout", "restart", f"deployment/{APP_DEPLOYMENT}"], timeout=120)
    if not wait_until(lambda: deployment_ready(APP_DEPLOYMENT, namespace), f"deployment/{APP_DEPLOYMENT} ready after restart in {namespace}"):
        return False

    time.sleep(5)
    app_pod = get_pod_name(APP_LABEL, namespace)
    persisted = exec_in_pod(app_pod, namespace, "cat /data/test.txt", container="simple-app")
    return check_equal(f"backend data survives restart in {namespace}", persisted, marker)


def test_redis_persistence(namespace: str) -> bool:
    """Write a Redis key, recreate the Redis pod, and verify the key survives."""
    marker = f"redis-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    written = exec_in_pod("redis-0", namespace, f"redis-cli set week11:persistence {marker}", container="redis")
    if written != "OK":
        fail(f"Could not write the Redis persistence marker in {namespace}")
        return False
    ok(f"Redis persistence marker written in {namespace}")

    run(kubectl_cmd(namespace) + ["delete", "pod", "redis-0"], timeout=120)
    if not wait_until(lambda: statefulset_ready(REDIS_STATEFULSET, namespace), f"statefulset/{REDIS_STATEFULSET} ready after recreation in {namespace}"):
        return False

    restored = exec_in_pod("redis-0", namespace, "redis-cli get week11:persistence", container="redis")
    return check_equal(f"Redis data survives pod recreation in {namespace}", restored, marker)


def backend_response_contains(namespace: str, expected_message: str) -> bool:
    """Return True when nginx can fetch the expected backend response."""
    nginx_pod = get_pod_name(NGINX_LABEL, namespace)
    response = exec_in_pod(nginx_pod, namespace, "curl -fsS http://simple-app:5000/", container="nginx")
    return expected_message in response


def test_rollback() -> bool:
    """Apply a temporary backend message change and roll back to the baseline tfvars."""
    all_ok = True
    try:
        terraform_apply(DEV_TFVARS, extra_vars=["-var", f"app_message={ROLLBACK_MESSAGE}"])
        all_ok &= wait_for_environment(DEV_NAMESPACE)
        all_ok &= wait_until(
            lambda: backend_response_contains(DEV_NAMESPACE, ROLLBACK_MESSAGE),
            "backend serves the rollback candidate message in dev",
        )
    finally:
        terraform_apply(DEV_TFVARS)
        all_ok &= wait_for_environment(DEV_NAMESPACE)
        all_ok &= wait_until(
            lambda: backend_response_contains(DEV_NAMESPACE, DEV_MESSAGE),
            "backend serves the baseline message again in dev",
        )
    return all_ok


def test_multiple_environments() -> bool:
    """Confirm dev and staging can coexist from the same Terraform codebase."""
    all_ok = True
    result = run(["kubectl", "get", "namespace", DEV_NAMESPACE, STAGING_NAMESPACE], check=False)
    all_ok &= check_equal("dev and staging namespaces coexist", str(result.returncode), "0")

    dev_app = exec_in_pod(get_pod_name(APP_LABEL, DEV_NAMESPACE), DEV_NAMESPACE, "printenv APP_MESSAGE", container="simple-app")
    staging_app = exec_in_pod(get_pod_name(APP_LABEL, STAGING_NAMESPACE), STAGING_NAMESPACE, "printenv APP_MESSAGE", container="simple-app")
    all_ok &= check_equal("dev keeps the dev message", dev_app, DEV_MESSAGE)
    all_ok &= check_equal("staging keeps the staging message", staging_app, STAGING_MESSAGE)
    return all_ok


def test_ci_workflow_static() -> bool:
    """Verify that the GitHub Actions workflow covers the required CI/CD features."""
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    checks = [
        ("CI workflow file exists", CI_WORKFLOW.exists()),
        ("workflow validates Terraform formatting", "terraform fmt -check -recursive" in workflow),
        ("workflow initializes Terraform without backend", "terraform init -backend=false" in workflow),
        ("workflow validates Terraform", "terraform validate" in workflow),
        ("workflow builds and pushes images", "docker/build-push-action@v6" in workflow),
        ("workflow logs in to GHCR", "docker/login-action@v3" in workflow),
        ("workflow generates metadata tags", "docker/metadata-action@v5" in workflow),
        ("workflow publishes SHA tags", "type=sha,prefix=sha-" in workflow),
        ("workflow publishes main tags", "type=raw,value=main" in workflow),
        ("workflow supports a stable release tag", "type=raw,value=stable" in workflow),
        ("workflow uses Buildx cache", "cache-from: type=gha" in workflow and "cache-to: type=gha" in workflow),
        ("workflow scans images with Trivy", "aquasecurity/trivy-action" in workflow),
        ("workflow uploads SARIF results", "upload-sarif" in workflow),
        ("workflow generates an SBOM", "anchore/sbom-action" in workflow),
        ("workflow uploads deployable artifacts", "actions/upload-artifact@v4" in workflow),
        ("workflow saves the deployable image reference", "IMAGE_NAME=%s" in workflow),
    ]

    all_ok = True
    for description, passed in checks:
        if passed:
            ok(description)
        else:
            fail(description)
            all_ok = False
    return all_ok


def test_dev_environment() -> bool:
    """Run the full validation suite against the dev environment."""
    all_ok = True
    all_ok &= test_terraform_outputs(DEV_NAMESPACE, DEV_NODE_PORT, DEV_PV)
    all_ok &= test_resources_exist(DEV_NAMESPACE, DEV_PV)
    all_ok &= wait_for_environment(DEV_NAMESPACE)
    all_ok &= test_configuration_and_service_types(DEV_NAMESPACE, DEV_MESSAGE, DEV_NODE_PORT)
    all_ok &= test_probes_and_resources(DEV_NAMESPACE)
    all_ok &= test_redis_ping(DEV_NAMESPACE)
    all_ok &= test_in_cluster_connectivity(DEV_NAMESPACE, DEV_MESSAGE)
    all_ok &= test_http_endpoints(DEV_NAMESPACE, DEV_MESSAGE)
    all_ok &= test_scaling(DEV_NAMESPACE)
    all_ok &= test_resilience(DEV_NAMESPACE)
    all_ok &= test_app_persistence(DEV_NAMESPACE)
    all_ok &= test_redis_persistence(DEV_NAMESPACE)
    all_ok &= check_plan_is_clean(DEV_TFVARS, "terraform plan is clean for dev")
    all_ok &= test_rollback()
    all_ok &= check_plan_is_clean(DEV_TFVARS, "terraform plan is still clean for dev after rollback")
    return all_ok


def test_staging_environment() -> bool:
    """Validate the independent staging environment."""
    all_ok = True
    all_ok &= test_terraform_outputs(STAGING_NAMESPACE, STAGING_NODE_PORT, STAGING_PV)
    all_ok &= test_resources_exist(STAGING_NAMESPACE, STAGING_PV)
    all_ok &= wait_for_environment(STAGING_NAMESPACE)
    all_ok &= test_configuration_and_service_types(STAGING_NAMESPACE, STAGING_MESSAGE, STAGING_NODE_PORT)
    all_ok &= test_redis_ping(STAGING_NAMESPACE)
    all_ok &= test_in_cluster_connectivity(STAGING_NAMESPACE, STAGING_MESSAGE)
    all_ok &= test_http_endpoints(STAGING_NAMESPACE, STAGING_MESSAGE)
    all_ok &= check_plan_is_clean(STAGING_TFVARS, "terraform plan is clean for staging")
    return all_ok


def main() -> None:
    """Run the verification suite sequentially and summarize the outcome."""
    tests = [
        ("Prerequisites", test_prerequisites),
        ("Build images", test_build_images),
        ("Terraform validation", test_terraform_validation),
        (
            "Deploy dev from scratch",
            lambda: deploy_environment("dev", DEV_NAMESPACE, DEV_TFVARS),
        ),
        ("Verify dev environment", test_dev_environment),
        (
            "Deploy staging from scratch",
            lambda: deploy_environment("staging", STAGING_NAMESPACE, STAGING_TFVARS),
        ),
        ("Verify staging environment", test_staging_environment),
        ("Multiple environments", test_multiple_environments),
        ("CI workflow static checks", test_ci_workflow_static),
    ]

    passed = 0
    failed = 0
    critical_tests = {"Prerequisites"}

    for name, fn in tests:
        print("\n" + "=" * 72)
        print(f"TEST: {name}")
        print("=" * 72)

        try:
            result = fn()
            if result is False:
                failed += 1
                if name in critical_tests:
                    info(f"Stopping after critical test failure: {name}")
                    break
            else:
                passed += 1
        except Exception as exc:
            fail(f"{name} crashed: {exc}")
            failed += 1
            if name in critical_tests:
                info(f"Stopping after critical test failure: {name}")
                break

    print("\n" + "=" * 72)
    print("FINAL SUMMARY")
    print("=" * 72)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
