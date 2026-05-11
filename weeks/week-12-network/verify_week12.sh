#!/usr/bin/env bash

set -u

DEV_NS="green-dev-dev"
STAGING_NS="green-dev-staging"
PROD_NS="green-dev-prod"

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  echo "[PASS] $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "[FAIL] $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

info() {
  echo "[INFO] $1"
}

resource_exists() {
  local kind="$1"
  local name="$2"
  local namespace="${3:-}"

  if [[ -n "$namespace" ]]; then
    kubectl get "$kind" "$name" -n "$namespace" >/dev/null 2>&1
  else
    kubectl get "$kind" "$name" >/dev/null 2>&1
  fi
}

get_pod_name() {
  local namespace="$1"
  local label="$2"
  kubectl get pod -n "$namespace" -l "$label" -o jsonpath='{.items[0].metadata.name}'
}

check_equals() {
  local description="$1"
  local actual="$2"
  local expected="$3"

  if [[ "$actual" == "$expected" ]]; then
    pass "$description"
  else
    fail "$description (expected '$expected', got '$actual')"
  fi
}

check_nonempty() {
  local description="$1"
  local actual="$2"

  if [[ -n "$actual" ]]; then
    pass "$description"
  else
    fail "$description"
  fi
}

check_prerequisites() {
  info "Checking kubectl context and Calico CNI..."

  local context
  context="$(kubectl config current-context 2>/dev/null || true)"
  check_equals "current kubectl context is minikube" "$context" "minikube"

  if kubectl get pods -n kube-system -o name 2>/dev/null | grep -qi calico; then
    pass "Calico pods are present in kube-system"
  else
    fail "Calico pods are present in kube-system"
  fi
}

check_namespaces() {
  info "Checking namespaces..."

  for namespace in "$DEV_NS" "$STAGING_NS" "$PROD_NS"; do
    if resource_exists namespace "$namespace"; then
      pass "namespace/$namespace exists"
    else
      fail "namespace/$namespace exists"
    fi
  done
}

check_network_policies() {
  info "Checking NetworkPolicy objects..."

  for namespace in "$DEV_NS" "$STAGING_NS"; do
    for policy in \
      default-deny-all \
      allow-nginx-egress-to-backend \
      allow-backend-egress-to-redis \
      allow-backend-ingress-from-nginx \
      allow-redis-ingress-from-backend \
      allow-dns-egress
    do
      if resource_exists networkpolicy "$policy" "$namespace"; then
        pass "networkpolicy/$policy exists in $namespace"
      else
        fail "networkpolicy/$policy exists in $namespace"
      fi
    done
  done

  for policy in \
    default-deny-all \
    allow-nginx-egress-to-backend \
    allow-backend-egress-to-redis \
    allow-backend-ingress-from-nginx \
    allow-redis-ingress-from-backend \
    allow-partner-and-office-ingress-to-nginx \
    allow-dns-egress
  do
    if resource_exists networkpolicy "$policy" "$PROD_NS"; then
      pass "networkpolicy/$policy exists in $PROD_NS"
    else
      fail "networkpolicy/$policy exists in $PROD_NS"
    fi
  done
}

check_workload_paths() {
  info "Checking allowed application paths..."

  local namespace
  for namespace in "$DEV_NS" "$STAGING_NS" "$PROD_NS"; do
    local nginx_pod
    local app_pod
    local dns_ip

    nginx_pod="$(get_pod_name "$namespace" "app=nginx")"
    app_pod="$(get_pod_name "$namespace" "app=simple-app")"

    check_nonempty "nginx pod is discoverable in $namespace" "$nginx_pod"
    check_nonempty "simple-app pod is discoverable in $namespace" "$app_pod"

    if kubectl exec -n "$namespace" "$nginx_pod" -c nginx -- curl -fsS http://simple-app:5000/health >/dev/null 2>&1; then
      pass "nginx reaches simple-app in $namespace"
    else
      fail "nginx reaches simple-app in $namespace"
    fi

    if kubectl exec -n "$namespace" "$app_pod" -c simple-app -- python -c "import socket; s=socket.create_connection(('redis', 6379), 5); print('OK'); s.close()" >/dev/null 2>&1; then
      pass "simple-app reaches redis in $namespace"
    else
      fail "simple-app reaches redis in $namespace"
    fi

    dns_ip="$(kubectl exec -n "$namespace" "$app_pod" -c simple-app -- python -c "import socket; print(socket.gethostbyname('redis'))" 2>/dev/null || true)"
    check_nonempty "DNS resolution works inside $namespace" "$dns_ip"
  done
}

check_cross_environment_isolation() {
  info "Checking cross-environment isolation..."

  local dev_app
  local staging_app
  local prod_app

  dev_app="$(get_pod_name "$DEV_NS" "app=simple-app")"
  staging_app="$(get_pod_name "$STAGING_NS" "app=simple-app")"
  prod_app="$(get_pod_name "$PROD_NS" "app=simple-app")"

  if kubectl exec -n "$DEV_NS" "$dev_app" -c simple-app -- python -c "import socket; s=socket.create_connection(('simple-app.${STAGING_NS}.svc.cluster.local', 5000), 5); s.close()" >/dev/null 2>&1; then
    fail "dev backend cannot reach staging backend"
  else
    pass "dev backend cannot reach staging backend"
  fi

  if kubectl exec -n "$STAGING_NS" "$staging_app" -c simple-app -- python -c "import socket; s=socket.create_connection(('redis.${PROD_NS}.svc.cluster.local', 6379), 5); s.close()" >/dev/null 2>&1; then
    fail "staging backend cannot reach prod redis"
  else
    pass "staging backend cannot reach prod redis"
  fi

  if kubectl exec -n "$PROD_NS" "$prod_app" -c simple-app -- python -c "import socket; s=socket.create_connection(('simple-app.${DEV_NS}.svc.cluster.local', 5000), 5); s.close()" >/dev/null 2>&1; then
    fail "prod backend cannot reach dev backend"
  else
    pass "prod backend cannot reach dev backend"
  fi
}

check_partner_policy_shape() {
  info "Checking partner ingress policy..."

  local cidr_one
  local cidr_two
  local port_one
  local port_two

  cidr_one="$(kubectl get networkpolicy allow-partner-and-office-ingress-to-nginx -n "$PROD_NS" -o jsonpath='{.spec.ingress[0].from[0].ipBlock.cidr}' 2>/dev/null || true)"
  cidr_two="$(kubectl get networkpolicy allow-partner-and-office-ingress-to-nginx -n "$PROD_NS" -o jsonpath='{.spec.ingress[0].from[1].ipBlock.cidr}' 2>/dev/null || true)"
  port_one="$(kubectl get networkpolicy allow-partner-and-office-ingress-to-nginx -n "$PROD_NS" -o jsonpath='{.spec.ingress[0].ports[0].port}' 2>/dev/null || true)"
  port_two="$(kubectl get networkpolicy allow-partner-and-office-ingress-to-nginx -n "$PROD_NS" -o jsonpath='{.spec.ingress[0].ports[1].port}' 2>/dev/null || true)"

  check_equals "prod partner CIDR is 10.0.10.0/24" "$cidr_one" "10.0.10.0/24"
  check_equals "prod office CIDR is 10.0.20.0/24" "$cidr_two" "10.0.20.0/24"
  check_equals "prod nginx ingress allows port 80" "$port_one" "80"
  check_equals "prod nginx ingress allows port 443" "$port_two" "443"
}

main() {
  echo "=== Week 12: Network and Identity Verification ==="
  echo

  check_prerequisites
  echo
  check_namespaces
  echo
  check_network_policies
  echo
  check_workload_paths
  echo
  check_cross_environment_isolation
  echo
  check_partner_policy_shape
  echo
  echo "FINAL SUMMARY"
  echo "Passed: $PASS_COUNT"
  echo "Failed: $FAIL_COUNT"

  if [[ "$FAIL_COUNT" -ne 0 ]]; then
    exit 1
  fi
}

main "$@"
