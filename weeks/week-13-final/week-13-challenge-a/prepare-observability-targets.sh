#!/bin/bash
# Prepara nginx y simple-app existentes para que el stack de observabilidad de la week 13
# pueda monitorizarlos sin modificar archivos de weeks anteriores.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

require_resource() {
    local kind="$1"
    local name="$2"
    local namespace="$3"

    if ! kubectl get "$kind" "$name" -n "$namespace" > /dev/null 2>&1; then
        echo -e "${RED}❌ Falta ${kind}/${name} en namespace ${namespace}${NC}"
        echo "   Despliega primero la infraestructura base de week 10/week 11."
        exit 1
    fi
}

echo -e "${YELLOW}Preparando nginx y simple-app para observabilidad...${NC}"

require_resource deployment nginx default
require_resource deployment simple-app default
require_resource service nginx default
require_resource service simple-app default
require_resource service redis default

echo "  - Añadiendo endpoint /stub_status dedicado a nginx"
kubectl apply -f "$SCRIPT_DIR/nginx-stub-status-config.yml" > /dev/null
kubectl patch deployment nginx -n default --type=strategic -p "$(cat <<'EOF'
spec:
  template:
    spec:
      volumes:
      - name: stub-status-config
        configMap:
          name: nginx-stub-status-config
      containers:
      - name: nginx
        ports:
        - containerPort: 8080
          name: stub-status
          protocol: TCP
        volumeMounts:
        - name: stub-status-config
          mountPath: /etc/nginx/conf.d/stub_status.conf
          subPath: stub_status.conf
EOF
)" > /dev/null
kubectl patch service nginx -n default --type=strategic -p "$(cat <<'EOF'
spec:
  ports:
  - name: stub-status
    port: 8080
    targetPort: 8080
    protocol: TCP
EOF
)" > /dev/null

echo "  - Inyectando variante instrumentada de simple-app"
kubectl create configmap simple-app-observability \
    --from-file=app.py="$SCRIPT_DIR/simple-app-observability.py" \
    -n default \
    --dry-run=client \
    -o yaml | kubectl apply -f - > /dev/null

kubectl patch deployment simple-app -n default --type=strategic -p "$(cat <<'EOF'
spec:
  template:
    spec:
      volumes:
      - name: observability-app
        configMap:
          name: simple-app-observability
      containers:
      - name: simple-app
        command:
        - python
        - /opt/observability/app.py
        volumeMounts:
        - name: observability-app
          mountPath: /opt/observability/app.py
          subPath: app.py
EOF
)" > /dev/null

echo "  - Esperando a que los despliegues base reinicien"
kubectl rollout status deployment/nginx -n default --timeout=180s > /dev/null
kubectl rollout status deployment/simple-app -n default --timeout=180s > /dev/null

echo -e "${GREEN}✅ Targets base preparados para observabilidad${NC}"
