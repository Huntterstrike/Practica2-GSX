#!/usr/bin/env python3
"""
verify_integration.py
Week 13 - Full Integration Test (Python)

This script runs automated checks for the full-integration test described in the PDF.
Checks performed:
  - dependency check (kubectl, minikube)
  - optional: apply manifests folder
  - wait for pods to be ready
  - external access to nginx via NodePort
  - internal connectivity (nginx -> simple-app)
  - network policy test (dev pod -> prod app should be blocked)
  - optional: redis ping (if redis service exists)

Usage:
  python3 verify_integration.py [--apply-manifests] [--manifests PATH] [--timeout SECONDS]

Examples:
  python3 verify_integration.py --apply-manifests --manifests kubernetes/ --timeout 180

Note: script assumes services named: nginx, simple-app, redis (if present), and that
'minikube' is used as the cluster. Adjust service names via constants below if needed.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time

# --- Configuration (adjust if your resource names differ) ---
NGINX_SVC_NAME = "nginx"
SIMPLE_APP_SVC_NAME = "simple-app"
REDIS_SVC_NAME = "redis"
NAMESPACE = None  # set to None or "gsx" if you use a namespace

# --- Utilities ---

def run(cmd, check=True, capture_output=False, text=True):
    if isinstance(cmd, (list, tuple)):
        pass
    else:
        cmd = cmd if isinstance(cmd, list) else cmd.split()
    try:
        res = subprocess.run(cmd, check=check, capture_output=capture_output, text=text)
        return res
    except subprocess.CalledProcessError as e:
        if capture_output:
            print(e.stdout)
            print(e.stderr, file=sys.stderr)
        raise


def has_binary(name):
    return shutil.which(name) is not None


def kubectl(cmd_args, capture_output=False):
    cmd = ["kubectl"] + cmd_args
    if NAMESPACE:
        cmd += ["-n", NAMESPACE]
    return run(cmd, capture_output=capture_output)


# --- Checks ---

def check_dependencies():
    missing = []
    for b in ("kubectl", "minikube", "curl"):
        if not has_binary(b):
            missing.append(b)
    if missing:
        print("[ERROR] Missing dependencies:", ", ".join(missing))
        print("Please install them and ensure they are in PATH.")
        sys.exit(2)
    print("[OK] All required binaries available.")


def apply_manifests(manifests_path):
    print(f"Applying manifests from: {manifests_path}")
    run(["kubectl", "apply", "-f", manifests_path])


def wait_for_pods_ready(timeout):
    print("Waiting for pods to be in Running state...")
    start = time.time()
    while True:
        try:
            res = kubectl(["get", "pods", "-o", "json"], capture_output=True)
            data = json.loads(res.stdout)
            items = data.get("items", [])
            if not items:
                print("No pods found yet...")
            all_ready = True
            for it in items:
                phase = it.get("status", {}).get("phase", "")
                name = it.get("metadata", {}).get("name")
                # consider Ready condition
                conditions = it.get("status", {}).get("conditions", [])
                ready_cond = next((c for c in conditions if c.get("type") == "Ready"), {})
                ready = ready_cond.get("status") == "True"
                if phase != "Running" or not ready:
                    all_ready = False
                    # don't spam, but you can uncomment next line for details
                    # print(f"Pod {name} not ready: phase={phase} ready={ready}")
            if all_ready and items:
                print("[OK] All pods Running and Ready.")
                return True
        except Exception as e:
            print("Warning while checking pods:", e)
        if time.time() - start > timeout:
            print(f"[ERROR] Timeout waiting for pods after {timeout} seconds")
            return False
        time.sleep(5)


def get_minikube_ip():
    try:
        res = run(["minikube", "ip"], capture_output=True)
        ip = res.stdout.strip()
        print(f"Minikube IP: {ip}")
        return ip
    except Exception:
        print("[ERROR] Could not get minikube IP")
        return None


def get_nodeport(svc_name):
    try:
        res = kubectl(["get", "svc", svc_name, "-o", "json"], capture_output=True)
        svc = json.loads(res.stdout)
        ports = svc.get("spec", {}).get("ports", [])
        if not ports:
            return None
        node_port = ports[0].get("nodePort")
        print(f"Service {svc_name} NodePort: {node_port}")
        return node_port
    except Exception as e:
        print(f"[WARN] Could not read Service {svc_name}: {e}")
        return None


def check_external_access(ip, nodeport):
    if not ip or not nodeport:
        print("[SKIP] External access test skipped (missing IP or nodePort)")
        return False
    url = f"http://{ip}:{nodeport}"
    print(f"Checking external access at {url} ...")
    try:
        res = run(["curl", "-sS", "--connect-timeout", "5", url], capture_output=True)
        body = res.stdout
        ok = len(body) > 0
        if ok:
            print("[OK] External access succeeded (curl returned content).")
            return True
        else:
            print("[FAIL] External access returned empty body.")
            return False
    except Exception as e:
        print("[FAIL] External access test failed:", e)
        return False


def exec_in_pod(label_selector, cmd):
    # find pod
    try:
        res = kubectl(["get", "pods", "-l", label_selector, "-o", "json"], capture_output=True)
        data = json.loads(res.stdout)
        items = data.get("items", [])
        if not items:
            print(f"[WARN] No pod found with selector {label_selector}")
            return None, "no-pod"
        pod = items[0]["metadata"]["name"]
        full_cmd = ["kubectl", "exec", pod, "--"] + cmd
        res = run(full_cmd, capture_output=True)
        return pod, res.stdout
    except Exception as e:
        print("[WARN] exec_in_pod failed:", e)
        return None, None


def check_internal_connectivity():
    print("Testing internal connectivity: nginx -> simple-app")
    # attempt curl from nginx pod
    pod, output = exec_in_pod("app=nginx", ["curl", "-sS", "--max-time", "3", "http://simple-app:5000/health"])
    if output and ("OK" in output or "ok" in output.lower() or len(output) > 0):
        print(f"[OK] Internal connectivity: nginx({pod}) -> simple-app: {output.strip()}")
        return True
    else:
        print("[FAIL] Internal connectivity test failed. Output:", output)
        return False


def check_redis_ping():
    print("Checking Redis (if present) by trying redis-cli PING from simple-app pod")
    pod, _ = exec_in_pod("app=simple-app", ["sh", "-c", "which redis-cli >/dev/null 2>&1 && redis-cli -h redis PING || true"])
    if pod is None:
        print("[SKIP] simple-app pod not found for redis check")
        return None
    # run redis-cli
    try:
        pod, output = exec_in_pod("app=simple-app", ["sh", "-c", "python -c 'import socket,sys;s=socket.socket();s.settimeout(2);s.connect(("redis",6379));print("OK")'" ])
        if output and "OK" in output:
            print("[OK] Redis reachable from simple-app pod")
            return True
    except Exception:
        pass
    print("[WARN] Redis check inconclusive or failed")
    return False


def check_network_policy_block():
    print("Testing NetworkPolicy: create temporary pod with label env=dev and try access to simple-app")
    # create a temporary pod that sleeps long enough
    try:
        run(["kubectl", "run", "test-dev-tmp", "--image=busybox", "--labels=env=dev", "--restart=Never", "--", "sh", "-c", "sleep 30 & wait" ], check=True)
        time.sleep(2)
        # try wget
        try:
            res = run(["kubectl", "exec", "test-dev-tmp", "--", "wget", "-T", "2", "-qO-", "http://simple-app:5000/health"], check=True, capture_output=True)
            print("[FAIL] NetworkPolicy test failed: test-dev reached simple-app (output snippet):", res.stdout[:200])
            success = False
        except subprocess.CalledProcessError:
            print("[OK] NetworkPolicy: test-dev could not reach simple-app (expected)")
            success = True
    finally:
        run(["kubectl", "delete", "pod", "test-dev-tmp", "--now"], check=False)
    return success


# --- Main ---

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-manifests", action="store_true", help="Apply manifests before running checks")
    parser.add_argument("--manifests", default="kubernetes/", help="Path to manifests folder to apply")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds to wait for pods to be ready")

    args = parser.parse_args()

    check_dependencies()

    if args.apply_manifests:
        apply_manifests(args.manifests)

    ok_ready = wait_for_pods_ready(args.timeout)
    if not ok_ready:
        print("[ERROR] Pods did not become ready in time. Exiting.")
        sys.exit(3)

    # External access
    ip = get_minikube_ip()
    nodeport = get_nodeport(NGINX_SVC_NAME)
    ext_ok = check_external_access(ip, nodeport)

    # Internal connectivity
    int_ok = check_internal_connectivity()

    # Redis check (best-effort)
    redis_ok = check_redis_ping()

    # NetworkPolicy block test
    np_ok = check_network_policy_block()

    print("
--- SUMMARY ---")
    print(f"Pods ready: {ok_ready}")
    print(f"External access (nginx): {ext_ok}")
    print(f"Internal connectivity (nginx->simple-app): {int_ok}")
    print(f"Redis reachable (best-effort): {redis_ok}")
    print(f"NetworkPolicy block test: {np_ok}")

    # decide exit code
    if ok_ready and ext_ok and int_ok and np_ok:
        print("
All critical checks passed ✅")
        sys.exit(0)
    else:
        print("
Some checks failed. Please inspect the output above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
