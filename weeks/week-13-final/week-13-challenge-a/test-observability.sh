#!/bin/bash
# Script de testing para verificar el stack de observabilidad

set -e

echo "============================================"
echo "🧪 Testing Observability Stack"
echo "============================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

stop_port_forward() {
    local pid="$1"
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
}

# Test 1: Verificar que los pods están corriendo
echo -e "${YELLOW}[Test 1/7]${NC} Verificando pods..."
if kubectl get pods -n monitoring | grep -E "prometheus|grafana|exporter" | grep Running > /dev/null; then
    echo -e "${GREEN}✅ Todos los pods están corriendo${NC}"
else
    echo -e "${RED}❌ Algunos pods no están corriendo${NC}"
    kubectl get pods -n monitoring
    exit 1
fi
echo ""

# Test 2: Verificar que Prometheus está respondiendo
echo -e "${YELLOW}[Test 2/7]${NC} Verificando Prometheus..."
kubectl port-forward -n monitoring svc/prometheus 9090:9090 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

if curl -s http://localhost:9090/-/healthy | grep -q "Prometheus"; then
    echo -e "${GREEN}✅ Prometheus está healthy${NC}"
else
    echo -e "${RED}❌ Prometheus no responde${NC}"
    stop_port_forward "$PF_PID"
    exit 1
fi
stop_port_forward "$PF_PID"
echo ""

# Test 3: Verificar targets de Prometheus
echo -e "${YELLOW}[Test 3/7]${NC} Verificando targets de Prometheus..."
kubectl port-forward -n monitoring svc/prometheus 9090:9090 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

TARGETS=$(curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets | length')
if [ "$TARGETS" -gt 0 ]; then
    echo -e "${GREEN}✅ Prometheus tiene $TARGETS targets configurados${NC}"
else
    echo -e "${RED}❌ No se encontraron targets${NC}"
    stop_port_forward "$PF_PID"
    exit 1
fi
stop_port_forward "$PF_PID"
echo ""

# Test 4: Verificar que Grafana está respondiendo
echo -e "${YELLOW}[Test 4/7]${NC} Verificando Grafana..."
kubectl port-forward -n monitoring svc/grafana 3000:3000 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

if curl -s http://localhost:3000/api/health | grep -q "ok"; then
    echo -e "${GREEN}✅ Grafana está healthy${NC}"
else
    echo -e "${RED}❌ Grafana no responde${NC}"
    stop_port_forward "$PF_PID"
    exit 1
fi
stop_port_forward "$PF_PID"
echo ""

# Test 5: Verificar datasource de Prometheus en Grafana
echo -e "${YELLOW}[Test 5/7]${NC} Verificando datasource en Grafana..."
kubectl port-forward -n monitoring svc/grafana 3000:3000 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

# Login y obtener datasources
DATASOURCES=$(curl -s -u admin:admin http://localhost:3000/api/datasources)

if echo "$DATASOURCES" | jq -e '.[] | select(.type=="prometheus")' > /dev/null; then
    echo -e "${GREEN}✅ Datasource de Prometheus configurado en Grafana${NC}"
else
    echo -e "${RED}❌ No se encontró datasource de Prometheus${NC}"
    stop_port_forward "$PF_PID"
    exit 1
fi
stop_port_forward "$PF_PID"
echo ""

# Test 6: Verificar nginx-exporter
echo -e "${YELLOW}[Test 6/7]${NC} Verificando nginx-exporter..."
kubectl port-forward -n monitoring svc/nginx-exporter 9113:9113 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

if curl -s http://localhost:9113/metrics | grep -q "nginx"; then
    echo -e "${GREEN}✅ Nginx Exporter está exponiendo métricas${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx Exporter puede tener problemas conectando a nginx${NC}"
    echo "    Asegúrate de que nginx tiene /stub_status habilitado"
fi
stop_port_forward "$PF_PID"
echo ""

# Test 7: Verificar redis-exporter
echo -e "${YELLOW}[Test 7/7]${NC} Verificando redis-exporter..."
kubectl port-forward -n monitoring svc/redis-exporter 9121:9121 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

if curl -s http://localhost:9121/metrics | grep -q "redis"; then
    echo -e "${GREEN}✅ Redis Exporter está exponiendo métricas${NC}"
else
    echo -e "${YELLOW}⚠️  Redis Exporter puede tener problemas conectando a Redis${NC}"
    echo "    Verifica que Redis está corriendo en el namespace default"
fi
stop_port_forward "$PF_PID"
echo ""

# Resumen
echo "============================================"
echo -e "${GREEN}✅ Testing completado!${NC}"
echo "============================================"
echo ""
echo "📊 Para ver métricas en tiempo real:"
echo ""
echo "  1. Accede a Prometheus:"
echo "     kubectl port-forward -n monitoring svc/prometheus 9090:9090"
echo "     http://localhost:9090"
echo ""
echo "  2. Accede a Grafana:"
echo "     kubectl port-forward -n monitoring svc/grafana 3000:3000"
echo "     http://localhost:3000 (admin/admin)"
echo ""
echo "  3. Genera tráfico:"
echo "     while true; do curl -s \$(minikube service nginx --url); sleep 0.1; done"
echo ""
echo "============================================"
