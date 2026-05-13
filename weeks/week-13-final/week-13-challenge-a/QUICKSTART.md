# Quick Start - Challenge A

## 🚀 Despliegue Rápido en 3 Pasos

### Paso 1: Desplegar todo automáticamente
```bash
cd /home/ubuntu/week-13-challenge-a
./deploy-all.sh
```

Este script desplegará:
- ✅ Prometheus (con configuración completa)
- ✅ Grafana (con datasource preconfigurado)
- ✅ Nginx Exporter
- ✅ Redis Exporter

### Paso 2: Acceder a las interfaces

**Prometheus:**
```bash
# Opción 1: NodePort (más fácil)
minikube ip  # Obtener IP
# Visita: http://<MINIKUBE_IP>:30090

# Opción 2: Port-forward
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Visita: http://localhost:9090
```

**Grafana:**
```bash
# Opción 1: NodePort
# Visita: http://<MINIKUBE_IP>:30300

# Opción 2: Port-forward
kubectl port-forward -n monitoring svc/grafana 3000:3000
# Visita: http://localhost:3000
# Credenciales: admin / admin
```

### Paso 3: Verificar que todo funciona
```bash
./test-observability.sh
```

---

## 📊 Crear tu Dashboard en Grafana

### 1. Login en Grafana
- URL: http://localhost:3000
- User: `admin`
- Password: `admin`

### 2. Verificar Datasource
- Menu → Configuration → Data Sources
- Deberías ver "Prometheus" ya configurado
- Click en "Test" para verificar conexión

### 3. Crear Dashboard
- Menu → Create (+) → Dashboard
- Click "Add new panel"

### 4. Añadir Paneles (Queries PromQL)

**Panel 1: Request Rate**
```promql
rate(app_requests_total[5m])
```

**Panel 2: CPU Usage**
```promql
rate(container_cpu_usage_seconds_total{pod=~"simple-app.*"}[5m])
```

**Panel 3: Memory Usage**
```promql
container_memory_working_set_bytes{pod=~"simple-app.*"} / 1024 / 1024
```

**Panel 4: Redis Commands**
```promql
rate(redis_commands_processed_total[5m])
```

**Panel 5: Nginx Requests**
```promql
rate(nginx_http_requests_total[5m])
```

**Panel 6: Error Rate**
```promql
rate(app_requests_total{http_status=~"5.."}[5m]) / rate(app_requests_total[5m]) * 100
```

### 5. Configurar el Dashboard
- Time range: "Last 15 minutes"
- Refresh: "5s" (auto-refresh)
- Save dashboard: Click 💾 → Name: "GreenDevCorp Monitoring"

---

## 🔧 Instrumentar Simple-App

### Si tu app está en Python/Flask:

1. **Añadir dependencias** (requirements.txt):
```txt
prometheus-client==0.19.0
```

2. **Añadir código de métricas** (ver `simple-app-metrics-example.py`)

3. **Reconstruir y redesplegar**:
```bash
docker build -t simple-app:v2-metrics .
minikube image load simple-app:v2-metrics
kubectl set image deployment/simple-app simple-app=simple-app:v2-metrics
```

4. **Verificar endpoint /metrics**:
```bash
kubectl port-forward svc/simple-app 8000:8000
curl http://localhost:8000/metrics
```

---

## 🧪 Generar Tráfico para Testing

### Opción 1: Loop simple con curl
```bash
NGINX_URL=$(minikube service nginx --url)
while true; do 
  curl -s $NGINX_URL > /dev/null
  sleep 0.1
done
```

### Opción 2: Load testing con hey
```bash
# Instalar hey
go install github.com/rakyll/hey@latest

# Generar carga
hey -z 60s -c 10 $(minikube service nginx --url)
```

---

## 📸 Tomar Screenshot para Entregable

1. Genera tráfico durante 2-3 minutos
2. Abre Grafana con tu dashboard
3. Espera a que todos los paneles muestren datos
4. Toma captura de pantalla mostrando:
   - ✅ Todos los paneles con gráficos
   - ✅ Métricas actualizándose
   - ✅ Time range visible
   - ✅ Fecha/hora actual

---

## ❌ Si algo falla

### Ver logs de Prometheus
```bash
kubectl logs -n monitoring deployment/prometheus -f
```

### Ver logs de Grafana
```bash
kubectl logs -n monitoring deployment/grafana -f
```

### Ver targets en Prometheus
```bash
# Accede a: http://localhost:9090/targets
# Todos deberían estar "UP"
```

### Reiniciar todo
```bash
# Eliminar namespace monitoring
kubectl delete namespace monitoring

# Volver a desplegar
./deploy-all.sh
```

---

## 🎯 Checklist del Entregable

Antes de marcar como completo:

- [ ] Prometheus desplegado y accessible
- [ ] Grafana desplegado con datasource conectado
- [ ] Dashboard creado con al menos 5 paneles:
  - [ ] Request rate
  - [ ] Latency
  - [ ] CPU usage
  - [ ] Memory usage
  - [ ] Error rate
- [ ] Métricas actualizándose en tiempo real
- [ ] Screenshot guardado del dashboard
- [ ] (Opcional) Alertas configuradas
- [ ] (Opcional) Notificaciones testeadas

---

## 📚 Referencias Rápidas

**PromQL Básico:**
```promql
# Valor actual
up

# Tasa de incremento por segundo (últimos 5 min)
rate(metric_name[5m])

# Suma por label
sum by (label_name) (metric_name)

# Percentil 95
histogram_quantile(0.95, rate(metric_bucket[5m]))

# Top 5
topk(5, metric_name)
```

**Comandos kubectl útiles:**
```bash
# Ver todos los pods
kubectl get pods -n monitoring

# Ver servicios
kubectl get svc -n monitoring

# Port-forward múltiple
kubectl port-forward -n monitoring svc/prometheus 9090:9090 &
kubectl port-forward -n monitoring svc/grafana 3000:3000 &

# Ver logs
kubectl logs -n monitoring deployment/prometheus -f
kubectl logs -n monitoring deployment/grafana -f

# Describir pod (si hay problemas)
kubectl describe pod -n monitoring <POD_NAME>
```

---

## 🎉 ¡Listo!

Si completaste todos los pasos, ya tienes un stack de observabilidad completo funcionando.

**Próximos challenges:**
- Challenge B: Full Integration Test (Required)
- Challenge C: Documentation (Required)
- Challenge D: Interview Prep (Required)

¡Mucha suerte con tu Challenge A! 🚀📊
