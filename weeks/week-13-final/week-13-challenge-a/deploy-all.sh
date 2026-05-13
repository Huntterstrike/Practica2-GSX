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

echo -e "${YELLOW}[1/9]${NC} Checking Kubernetes access..."
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo -e "${RED}Error: Kubernetes cluster is not reachable${NC}"
    echo "Make sure Minikube is started and kubectl is configured"
    exit 1
fi
echo -e "${GREEN}Cluster is reachable${NC}"
echo ""

echo -e "${YELLOW}[2/9]${NC} Preparing base services for observability..."
bash "$SCRIPT_DIR/prepare-observability-targets.sh"
echo ""

echo -e "${YELLOW}[3/9]${NC} Creating namespace 'monitoring'..."
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}Namespace ready${NC}"
echo ""

echo -e "${YELLOW}[4/9]${NC} Deploying Prometheus..."
kubectl apply -f "$SCRIPT_DIR/prometheus-configmap.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/prometheus-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/prometheus-service.yml" -n monitoring
echo -e "${GREEN}Prometheus deployed${NC}"
echo ""

echo "Waiting for Prometheus..."
kubectl wait --for=condition=available --timeout=120s deployment/prometheus -n monitoring
echo ""

echo -e "${YELLOW}[5/9]${NC} Deploying Nginx Exporter..."
kubectl apply -f "$SCRIPT_DIR/nginx-exporter-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/nginx-exporter-service.yml" -n monitoring
echo -e "${GREEN}Nginx Exporter deployed${NC}"
echo ""

echo -e "${YELLOW}[6/9]${NC} Deploying Redis Exporter..."
kubectl apply -f "$SCRIPT_DIR/redis-exporter-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/redis-exporter-service.yml" -n monitoring
echo -e "${GREEN}Redis Exporter deployed${NC}"
echo ""

echo -e "${YELLOW}[7/9]${NC} Deploying Grafana..."
kubectl apply -f "$SCRIPT_DIR/grafana-deployment.yml" -n monitoring
kubectl apply -f "$SCRIPT_DIR/grafana-service.yml" -n monitoring
echo -e "${GREEN}Grafana deployed${NC}"
echo ""

echo "Waiting for Grafana..."
kubectl wait --for=condition=available --timeout=120s deployment/grafana -n monitoring
echo ""

echo -e "${YELLOW}[8/9]${NC} Checking monitoring pods..."
kubectl get pods -n monitoring
echo ""

echo -e "${YELLOW}[9/9]${NC} Collecting access URLs..."
echo ""
echo "============================================"
echo -e "${GREEN}Deployment completed${NC}"
echo "============================================"
echo ""
echo "Access URLs:"
echo ""

PROM_PORT=$(kubectl get svc prometheus-nodeport -n monitoring -o jsonpath='{.spec.ports[0].nodePort}' 2> /dev/null || echo "30090")
MINIKUBE_IP=$(minikube ip)
echo -e "  ${GREEN}Prometheus:${NC}"
echo "    - NodePort: http://${MINIKUBE_IP}:${PROM_PORT}"
echo "    - Port-forward: kubectl port-forward -n monitoring svc/prometheus 9090:9090"
echo "                    http://localhost:9090"
echo ""

GRAFANA_PORT=$(kubectl get svc grafana-nodeport -n monitoring -o jsonpath='{.spec.ports[0].nodePort}' 2> /dev/null || echo "30300")
echo -e "  ${GREEN}Grafana:${NC}"
echo "    - NodePort: http://${MINIKUBE_IP}:${GRAFANA_PORT}"
echo "    - Port-forward: kubectl port-forward -n monitoring svc/grafana 3000:3000"
echo "                    http://localhost:3000"
echo "    - Credentials: admin / admin"
echo ""

echo "============================================"
echo "Next steps:"
echo "============================================"
echo ""
echo "1. Open Prometheus targets:"
echo "   http://${MINIKUBE_IP}:${PROM_PORT}/targets"
echo ""
echo "2. Open Grafana and create the dashboard:"
echo "   http://${MINIKUBE_IP}:${GRAFANA_PORT}"
echo ""
echo "3. nginx and simple-app are prepared automatically from week 13 files only"
echo ""
echo "4. Generate traffic to see live metrics:"
echo "   while true; do curl -s \$(minikube service nginx --url) > /dev/null; sleep 0.1; done"
echo ""
echo "5. Run the validation script:"
echo "   ./test-observability.sh"
echo ""
echo "============================================"
echo "Useful commands:"
echo "============================================"
echo ""
echo "  kubectl logs -n monitoring deployment/prometheus -f"
echo "  kubectl logs -n monitoring deployment/grafana -f"
echo "  kubectl get svc -n monitoring"
echo "  kubectl delete namespace monitoring"
echo ""
echo "============================================"
echo -e "${GREEN}Challenge A is ready${NC}"
echo "============================================"
