#!/bin/bash
# Script de despliegue completo para Challenge A
# Ejecuta este script desde el directorio week-13-challenge-a/

set -e  # Salir si algún comando falla

echo "============================================"
echo "🚀 Desplegando Challenge A: Observabilidad"
echo "============================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que estamos en Minikube
echo -e "${YELLOW}[1/8]${NC} Verificando Minikube..."
if ! minikube status &> /dev/null; then
    echo -e "${RED}❌ Error: Minikube no está corriendo${NC}"
    echo "Inicia Minikube con: minikube start"
    exit 1
fi
echo -e "${GREEN}✅ Minikube está corriendo${NC}"
echo ""

# Crear namespace monitoring
echo -e "${YELLOW}[2/8]${NC} Creando namespace 'monitoring'..."
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✅ Namespace creado${NC}"
echo ""

# Desplegar Prometheus
echo -e "${YELLOW}[3/8]${NC} Desplegando Prometheus..."
kubectl apply -f prometheus-configmap.yml -n monitoring
kubectl apply -f prometheus-deployment.yml -n monitoring
kubectl apply -f prometheus-service.yml -n monitoring
echo -e "${GREEN}✅ Prometheus desplegado${NC}"
echo ""

# Esperar a que Prometheus esté listo
echo "Esperando a que Prometheus esté listo..."
kubectl wait --for=condition=available --timeout=120s deployment/prometheus -n monitoring
echo ""

# Desplegar Exporters
echo -e "${YELLOW}[4/8]${NC} Desplegando Nginx Exporter..."
kubectl apply -f nginx-exporter-deployment.yml -n monitoring
kubectl apply -f nginx-exporter-service.yml -n monitoring
echo -e "${GREEN}✅ Nginx Exporter desplegado${NC}"
echo ""

echo -e "${YELLOW}[5/8]${NC} Desplegando Redis Exporter..."
kubectl apply -f redis-exporter-deployment.yml -n monitoring
kubectl apply -f redis-exporter-service.yml -n monitoring
echo -e "${GREEN}✅ Redis Exporter desplegado${NC}"
echo ""

# Desplegar Grafana
echo -e "${YELLOW}[6/8]${NC} Desplegando Grafana..."
kubectl apply -f grafana-deployment.yml -n monitoring
kubectl apply -f grafana-service.yml -n monitoring
echo -e "${GREEN}✅ Grafana desplegado${NC}"
echo ""

# Esperar a que Grafana esté listo
echo "Esperando a que Grafana esté listo..."
kubectl wait --for=condition=available --timeout=120s deployment/grafana -n monitoring
echo ""

# Verificar estado de todos los pods
echo -e "${YELLOW}[7/8]${NC} Verificando estado de los pods..."
kubectl get pods -n monitoring
echo ""

# Obtener URLs de acceso
echo -e "${YELLOW}[8/8]${NC} Obteniendo URLs de acceso..."
echo ""
echo "============================================"
echo -e "${GREEN}✅ Despliegue completado!${NC}"
echo "============================================"
echo ""
echo "📊 URLs de acceso:"
echo ""

# Prometheus
PROM_PORT=$(kubectl get svc prometheus-nodeport -n monitoring -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30090")
MINIKUBE_IP=$(minikube ip)
echo -e "  ${GREEN}Prometheus:${NC}"
echo "    - NodePort: http://${MINIKUBE_IP}:${PROM_PORT}"
echo "    - Port-forward: kubectl port-forward -n monitoring svc/prometheus 9090:9090"
echo "                    http://localhost:9090"
echo ""

# Grafana
GRAFANA_PORT=$(kubectl get svc grafana-nodeport -n monitoring -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30300")
echo -e "  ${GREEN}Grafana:${NC}"
echo "    - NodePort: http://${MINIKUBE_IP}:${GRAFANA_PORT}"
echo "    - Port-forward: kubectl port-forward -n monitoring svc/grafana 3000:3000"
echo "                    http://localhost:3000"
echo "    - Credenciales: admin / admin"
echo ""

echo "============================================"
echo "📋 Próximos pasos:"
echo "============================================"
echo ""
echo "1. Accede a Prometheus y verifica que los targets están UP:"
echo "   http://${MINIKUBE_IP}:${PROM_PORT}/targets"
echo ""
echo "2. Accede a Grafana y crea tu dashboard:"
echo "   http://${MINIKUBE_IP}:${GRAFANA_PORT}"
echo ""
echo "3. Instrumenta tu simple-app (ver simple-app-metrics-example.py)"
echo ""
echo "4. Genera tráfico para ver métricas en tiempo real:"
echo "   while true; do curl -s \$(minikube service nginx --url) > /dev/null; sleep 0.1; done"
echo ""
echo "5. Toma screenshots del dashboard para el entregable"
echo ""
echo "============================================"
echo "💡 Comandos útiles:"
echo "============================================"
echo ""
echo "  # Ver logs de Prometheus"
echo "  kubectl logs -n monitoring deployment/prometheus -f"
echo ""
echo "  # Ver logs de Grafana"
echo "  kubectl logs -n monitoring deployment/grafana -f"
echo ""
echo "  # Ver todos los servicios"
echo "  kubectl get svc -n monitoring"
echo ""
echo "  # Eliminar todo (cleanup)"
echo "  kubectl delete namespace monitoring"
echo ""
echo "============================================"
echo -e "${GREEN}🎉 ¡Buena suerte con tu Challenge A!${NC}"
echo "============================================"
