#!/bin/bash
# Script de despliegue completo para Challenge A
# Ejecuta este script desde el directorio week-13-challenge-a/

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================"
echo "Deploying Challenge A: Observability"
echo "============================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}[1/12]${NC} Checking Kubernetes access..."
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo -e "${RED}Error: Kubernetes cluster is not reachable${NC}"
    echo "Make sure Minikube is started and kubectl is configured"
    exit 1
fi
echo -e "${GREEN}Cluster is reachable${NC}"
echo ""

echo -e "${YELLOW}[2/12]${NC} Preparing base services for observability..."
bash "$SCRIPT_DIR/prepare-observability-targets.sh"
echo ""

echo -e "${YELLOW}[3/12]${NC} Creating namespace 'monitoring'..."
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}Namespace ready${NC}"
echo ""

echo -e "${YELLOW}[4/12]${NC} Deploying Prometheus..."
kubectl apply -f "$SCRIPT_DIR/prometheus-configmap.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/prometheus-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/prometheus-service.yml" -n monitoring
echo -e "${GREEN}Prometheus deployed${NC}"
echo ""

echo "Waiting for Prometheus..."
kubectl wait --for=condition=available --timeout=120s deployment/prometheus -n monitoring
echo ""

echo -e "${YELLOW}[5/12]${NC} Deploying Nginx Exporter..."
kubectl apply -f "$SCRIPT_DIR/nginx-exporter-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/nginx-exporter-service.yml" -n monitoring
echo -e "${GREEN}Nginx Exporter deployed${NC}"
echo ""

echo -e "${YELLOW}[6/12]${NC} Deploying Redis Exporter..."
kubectl apply -f "$SCRIPT_DIR/redis-exporter-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/redis-exporter-service.yml" -n monitoring
echo -e "${GREEN}Redis Exporter deployed${NC}"
echo ""

echo -e "${YELLOW}[7/12]${NC} Deploying Grafana..."
kubectl apply -f "$SCRIPT_DIR/grafana-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/grafana-service.yml" -n monitoring
echo -e "${GREEN}Grafana deployed${NC}"
echo ""

echo "Waiting for Grafana..."
kubectl wait --for=condition=available --timeout=120s deployment/grafana -n monitoring
echo ""

echo -e "${YELLOW}[8/12]${NC} Deploying Alertmanager..."
kubectl apply -f "$SCRIPT_DIR/alertmanager-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/alertmanager-service.yml" -n monitoring
echo -e "${GREEN}Alertmanager deployed${NC}"
echo ""

echo "Waiting for Alertmanager..."
kubectl wait --for=condition=available --timeout=120s deployment/alertmanager -n monitoring
echo ""

echo -e "${YELLOW}[9/12]${NC} Deploying alert receiver..."
kubectl apply -f "$SCRIPT_DIR/alert-receiver-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/alert-receiver-service.yml" -n monitoring
echo -e "${GREEN}Alert receiver deployed${NC}"
echo ""

echo "Waiting for alert receiver..."
kubectl wait --for=condition=available --timeout=120s deployment/alert-receiver -n monitoring
echo ""

echo -e "${YELLOW}[10/12]${NC} Restarting Prometheus to reload alerting..."
kubectl rollout restart deployment/prometheus -n monitoring > /dev/null
kubectl rollout status deployment/prometheus -n monitoring --timeout=120s
echo ""

echo -e "${YELLOW}[11/12]${NC} Checking monitoring pods..."
kubectl get pods -n monitoring
echo ""

echo -e "${YELLOW}[12/12]${NC} Collecting access URLs..."
echo ""
echo "============================================"
echo -e "${GREEN}Deployment completed${NC}"
echo "============================================"
echo ""
echo "Access URLs:"
echo ""

PROM_PORT=$(kubectl get svc prometheus-nodeport -n monitoring -o jsonpath='{.spec.ports[0].nodePort}' 2> /dev/null || echo "30090")
if MINIKUBE_IP=$(minikube ip 2> /dev/null); then
    HAS_MINIKUBE_IP=true
else
    MINIKUBE_IP="localhost"
    HAS_MINIKUBE_IP=false
fi
echo -e "  ${GREEN}Prometheus:${NC}"
if [ "$HAS_MINIKUBE_IP" = true ]; then
    echo "    - NodePort: http://${MINIKUBE_IP}:${PROM_PORT}"
else
    echo "    - NodePort: not available from this shell, use port-forward instead"
fi
echo "    - Port-forward: kubectl port-forward -n monitoring svc/prometheus 9090:9090"
echo "                    http://localhost:9090"
echo ""

GRAFANA_PORT=$(kubectl get svc grafana-nodeport -n monitoring -o jsonpath='{.spec.ports[0].nodePort}' 2> /dev/null || echo "30300")
echo -e "  ${GREEN}Grafana:${NC}"
if [ "$HAS_MINIKUBE_IP" = true ]; then
    echo "    - NodePort: http://${MINIKUBE_IP}:${GRAFANA_PORT}"
else
    echo "    - NodePort: not available from this shell, use port-forward instead"
fi
echo "    - Port-forward: kubectl port-forward -n monitoring svc/grafana 3000:3000"
echo "                    http://localhost:3000"
echo "    - Credentials: admin / admin"
echo ""

ALERTMANAGER_PORT=$(kubectl get svc alertmanager-nodeport -n monitoring -o jsonpath='{.spec.ports[0].nodePort}' 2> /dev/null || echo "30093")
echo -e "  ${GREEN}Alertmanager:${NC}"
if [ "$HAS_MINIKUBE_IP" = true ]; then
    echo "    - NodePort: http://${MINIKUBE_IP}:${ALERTMANAGER_PORT}"
else
    echo "    - NodePort: not available from this shell, use port-forward instead"
fi
echo "    - Port-forward: kubectl port-forward -n monitoring svc/alertmanager 9093:9093"
echo "                    http://localhost:9093"
echo ""

echo "============================================"
echo "Next steps:"
echo "============================================"
echo ""
echo "1. Open Prometheus targets:"
if [ "$HAS_MINIKUBE_IP" = true ]; then
    echo "   http://${MINIKUBE_IP}:${PROM_PORT}/targets"
else
    echo "   use: kubectl port-forward -n monitoring svc/prometheus 9090:9090"
fi
echo ""
echo "2. Open Grafana and create the dashboard:"
if [ "$HAS_MINIKUBE_IP" = true ]; then
    echo "   http://${MINIKUBE_IP}:${GRAFANA_PORT}"
else
    echo "   use: kubectl port-forward -n monitoring svc/grafana 3000:3000"
fi
echo ""
echo "3. Open Alertmanager to inspect routed alerts:"
if [ "$HAS_MINIKUBE_IP" = true ]; then
    echo "   http://${MINIKUBE_IP}:${ALERTMANAGER_PORT}"
else
    echo "   use: kubectl port-forward -n monitoring svc/alertmanager 9093:9093"
fi
echo ""
echo "4. nginx and simple-app are prepared automatically from week 13 files only"
echo ""
echo "5. Generate traffic to see live metrics:"
echo "   while true; do curl -s \$(minikube service nginx --url) > /dev/null; sleep 0.1; done"
echo ""
echo "6. Inspect notifications in the alert receiver logs:"
echo "   kubectl logs -n monitoring deployment/alert-receiver -f"
echo ""
echo "7. Run the validation script:"
echo "   ./test-observability.sh"
echo ""
echo "============================================"
echo "Useful commands:"
echo "============================================"
echo ""
echo "  kubectl logs -n monitoring deployment/prometheus -f"
echo "  kubectl logs -n monitoring deployment/grafana -f"
echo "  kubectl logs -n monitoring deployment/alertmanager -f"
echo "  kubectl logs -n monitoring deployment/alert-receiver -f"
echo "  kubectl get svc -n monitoring"
echo "  kubectl delete namespace monitoring"
echo ""
echo "============================================"
echo -e "${GREEN}Challenge A is ready${NC}"
echo "============================================"
