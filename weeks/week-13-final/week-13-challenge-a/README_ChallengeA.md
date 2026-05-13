# Challenge A: Observabilidad con Prometheus & Grafana

## 📋 Índice
- [Objetivo del Challenge](#objetivo-del-challenge)
- [Arquitectura de Observabilidad](#arquitectura-de-observabilidad)
- [Requisitos Previos](#requisitos-previos)
- [Paso 1: Desplegar Prometheus](#paso-1-desplegar-prometheus)
- [Paso 2: Configurar Exporters para tus Servicios](#paso-2-configurar-exporters-para-tus-servicios)
- [Paso 3: Desplegar Grafana](#paso-3-desplegar-grafana)
- [Paso 4: Crear Dashboards en Grafana](#paso-4-crear-dashboards-en-grafana)
- [Paso 5: Verificación y Testing](#paso-5-verificación-y-testing)
- [Paso 6 (Opcional): Configurar Alertas](#paso-6-opcional-configurar-alertas)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Objetivo del Challenge

**Challenge A (Opcional pero Recomendado)** de la Semana 13 consiste en añadir observabilidad a tu infraestructura existente de GreenDevCorp mediante la implementación de un stack de monitorización con Prometheus y Grafana.

### ¿Qué aprenderás?
- Desplegar y configurar Prometheus para recolectar métricas
- Integrar exporters de métricas en tus servicios (nginx, redis, simple-app)
- Crear dashboards en Grafana para visualizar el estado del sistema
- Definir métricas clave: latencia, tasa de errores, uso de CPU/memoria
- Configurar alertas básicas (nivel intermedio)

### Entregables
✅ **Core (Básico):**
- [ ] Prometheus desplegado en Kubernetes
- [ ] Grafana desplegado y conectado a Prometheus
- [ ] Dashboard mostrando: request rate, latency, CPU/memoria, error rate
- [ ] Screenshot del dashboard funcionando con métricas en tiempo real

✅ **Intermedio:**
- [ ] Reglas de alertas configuradas (error rate > 5%, CPU > 80%)
- [ ] Notificaciones de alertas funcionando
- [ ] Testing de condiciones de alerta

---

## 🏗️ Arquitectura de Observabilidad

```
┌─────────────────────────────────────────────────────────────┐
│                      Minikube Cluster                        │
│                                                              │
│  ┌──────────────┐      ┌──────────────┐    ┌────────────┐  │
│  │    Nginx     │◄─────┤ nginx-exporter│───►│ Prometheus │  │
│  │ (Load Bal.)  │      └──────────────┘    │            │  │
│  └──────────────┘                          │ :9090      │  │
│         │                                  │            │  │
│         ▼                                  │ - Scrapes  │  │
│  ┌──────────────┐                         │ - Stores   │  │
│  │  simple-app  │────metrics:8000/metrics─►│ - Queries  │  │
│  │              │                          └─────┬──────┘  │
│  └──────┬───────┘                                │         │
│         │                                        │         │
│         ▼                                        │         │
│  ┌──────────────┐      ┌──────────────┐         │         │
│  │    Redis     │◄─────┤redis-exporter │─────────┘         │
│  └──────────────┘      └──────────────┘         │         │
│                                                  │         │
│                        ┌─────────────┐           │         │
│                        │  Grafana    │◄──────────┘         │
│                        │  :3000      │                     │
│                        │             │                     │
│                        │ - Dashboards│                     │
│                        │ - Alerting  │                     │
│                        └─────────────┘                     │
└─────────────────────────────────────────────────────────────┘
        │                        │
        ▼                        ▼
   NodePort 30080          NodePort 30300
   (nginx acceso)          (Grafana UI)
```

**Flujo de métricas:**
1. **Prometheus** hace "scraping" (recolección) cada 15-30 segundos
2. **Exporters** exponen métricas en formato Prometheus
3. **Grafana** consulta a Prometheus y visualiza los datos
4. **Alertmanager** (opcional) procesa reglas y envía notificaciones

---

## ✅ Requisitos Previos

### Tu stack actual (Week 10)
Debes tener ya desplegados en Minikube:
```bash
kubectl get pods
# Deberías ver:
# - nginx (deployment/service)
# - simple-app (deployment/service)
# - redis (deployment/service)
```

### Herramientas necesarias
```bash
# Verificar Minikube
minikube status

# Verificar kubectl
kubectl version --client

# Verificar que tienes acceso al cluster
kubectl cluster-info
```

---

## 📦 Paso 1: Desplegar Prometheus

### 1.1 Crear Namespace (Opcional pero recomendado)
```bash
kubectl create namespace monitoring
```

### 1.2 Aplicar ConfigMap de Prometheus
El ConfigMap contiene la configuración de scraping:

```bash
kubectl apply -f prometheus-configmap.yml -n monitoring
```

**¿Qué hace este ConfigMap?**
- Define los **scrape_configs**: qué servicios monitorizar
- Intervalo de recolección (scrape_interval: 15s)
- Targets: nginx-exporter, redis-exporter, simple-app

### 1.3 Desplegar Prometheus
```bash
kubectl apply -f prometheus-deployment.yml -n monitoring
kubectl apply -f prometheus-service.yml -n monitoring
```

### 1.4 Verificar que Prometheus está corriendo
```bash
# Ver el pod
kubectl get pods -n monitoring

# Ver logs
kubectl logs -n monitoring deployment/prometheus

# Acceder a la UI de Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

Abre en tu navegador: `http://localhost:9090`

**Verificaciones en la UI:**
- Ve a **Status > Targets**: deberías ver tus servicios listados
- Ve a **Graph**: prueba queries como `up` o `prometheus_build_info`

---

## 🔌 Paso 2: Configurar Exporters para tus Servicios

Para que Prometheus pueda recolectar métricas de nginx y redis, necesitamos **exporters**.

### 2.1 Nginx Exporter

```bash
kubectl apply -f nginx-exporter-deployment.yml -n monitoring
kubectl apply -f nginx-exporter-service.yml -n monitoring
```

**¿Qué métricas expone nginx-exporter?**
- Requests por segundo
- Conexiones activas
- Bytes enviados/recibidos

### 2.2 Redis Exporter

```bash
kubectl apply -f redis-exporter-deployment.yml -n monitoring
kubectl apply -f redis-exporter-service.yml -n monitoring
```

**¿Qué métricas expone redis-exporter?**
- Comandos ejecutados
- Memoria usada
- Clientes conectados
- Keys totales

### 2.3 Simple-App (tu aplicación)

**Instrumentar tu aplicación** para exponer métricas:

Si tu `simple-app` está en Python (Flask/FastAPI), añade la librería Prometheus:

```python
# requirements.txt
prometheus-client==0.19.0

# app.py (ejemplo con Flask)
from prometheus_client import Counter, Histogram, generate_latest
from flask import Flask, Response
import time

app = Flask(__name__)

# Métricas
REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Request latency', ['endpoint'])

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/')
def index():
    start = time.time()
    REQUEST_COUNT.labels(method='GET', endpoint='/', http_status=200).inc()
    # Tu lógica...
    REQUEST_LATENCY.labels(endpoint='/').observe(time.time() - start)
    return "Hello from simple-app!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

Reconstruye y redespliega tu imagen:
```bash
docker build -t simple-app:v2 .
minikube image load simple-app:v2
kubectl set image deployment/simple-app simple-app=simple-app:v2
```

**Verificar el endpoint de métricas:**
```bash
kubectl port-forward svc/simple-app 8000:8000
curl http://localhost:8000/metrics
```

Deberías ver output como:
```
# HELP app_requests_total Total requests
# TYPE app_requests_total counter
app_requests_total{endpoint="/",http_status="200",method="GET"} 42.0
...
```

---

## 📊 Paso 3: Desplegar Grafana

### 3.1 Aplicar manifiestos
```bash
kubectl apply -f grafana-deployment.yml -n monitoring
kubectl apply -f grafana-service.yml -n monitoring
```

### 3.2 Acceder a Grafana
```bash
# Via port-forward
kubectl port-forward -n monitoring svc/grafana 3000:3000

# O via NodePort (si configuraste NodePort en grafana-service.yml)
minikube service grafana -n monitoring
```

Abre: `http://localhost:3000`

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `admin` (te pedirá cambiarla en el primer login)

---

## 📈 Paso 4: Crear Dashboards en Grafana

### 4.1 Añadir Prometheus como Data Source

1. En Grafana, ve a **Configuration** (⚙️) → **Data Sources**
2. Click **Add data source**
3. Selecciona **Prometheus**
4. Configura:
   - **Name**: Prometheus
   - **URL**: `http://prometheus:9090` (si está en el mismo namespace)
   - O: `http://prometheus.monitoring.svc.cluster.local:9090`
5. Click **Save & Test** (debería decir "Data source is working")

### 4.2 Crear Dashboard Principal

Ve a **Create** (+) → **Dashboard** → **Add new panel**

#### Panel 1: Request Rate (Tasa de solicitudes)

**Métrica PromQL:**
```promql
rate(app_requests_total[5m])
```

**Configuración:**
- Visualization: **Graph** o **Time series**
- Title: "Request Rate (req/s)"
- Legend: `{{method}} {{endpoint}}`

#### Panel 2: Request Latency (Latencia)

**Métrica PromQL:**
```promql
histogram_quantile(0.95, rate(app_request_latency_seconds_bucket[5m]))
```

**Configuración:**
- Title: "95th Percentile Latency"
- Unit: seconds (s)
- Legend: `{{endpoint}}`

#### Panel 3: CPU Usage (Uso de CPU)

**Métrica PromQL:**
```promql
rate(container_cpu_usage_seconds_total{pod=~"simple-app.*"}[5m])
```

**Configuración:**
- Title: "CPU Usage by Pod"
- Unit: percent (0-1)

#### Panel 4: Memory Usage (Uso de Memoria)

**Métrica PromQL:**
```promql
container_memory_working_set_bytes{pod=~"simple-app.*"} / 1024 / 1024
```

**Configuración:**
- Title: "Memory Usage (MiB)"
- Unit: MiB

#### Panel 5: Error Rate (Tasa de errores)

**Métrica PromQL:**
```promql
rate(app_requests_total{http_status=~"5.."}[5m]) / rate(app_requests_total[5m]) * 100
```

**Configuración:**
- Title: "Error Rate (%)"
- Threshold: > 5% (alerta visual)

#### Panel 6: Redis Metrics

**Métricas:**
```promql
# Comandos por segundo
rate(redis_commands_processed_total[5m])

# Memoria usada
redis_memory_used_bytes / 1024 / 1024

# Clientes conectados
redis_connected_clients
```

#### Panel 7: Nginx Metrics

**Métricas:**
```promql
# Requests por segundo
rate(nginx_http_requests_total[5m])

# Conexiones activas
nginx_connections_active
```

### 4.3 Organizar el Dashboard

1. Arrastra los paneles para organizarlos en una cuadrícula lógica
2. Ajusta el **time range** (arriba derecha): Last 15 minutes, Last 1 hour, etc.
3. Habilita **Auto-refresh**: 5s o 10s
4. **Guarda el dashboard**: Click en el icono de disquete (💾) arriba → "Save dashboard"
   - Name: "GreenDevCorp - Monitorización de Infraestructura"
   - Folder: General

---

## ✅ Paso 5: Verificación y Testing

### 5.1 Generar tráfico a tu aplicación

Usa `curl` en un loop para generar requests:

```bash
# Obtener la URL de tu nginx
minikube service nginx --url

# Generar tráfico (ejecuta en una terminal separada)
while true; do
  curl -s http://<NGINX_URL>/ > /dev/null
  sleep 0.1
done
```

O usa `hey` (herramienta de load testing):
```bash
# Instalar hey
go install github.com/rakyll/hey@latest

# Generar carga
hey -z 60s -c 10 http://<NGINX_URL>/
```

### 5.2 Observar métricas en tiempo real

1. Ve a tu dashboard de Grafana
2. Deberías ver:
   - **Request Rate** aumentando
   - **Latency** variando
   - **CPU/Memory** incrementándose ligeramente
   - **Redis commands** si tu app usa Redis

### 5.3 Tomar Screenshot del Dashboard

**Requisito del entregable:** Captura de pantalla mostrando:
- Todos los paneles con datos reales
- Time range visible
- Fecha/hora actual
- Métricas actualizándose

```bash
# Guarda la captura en tu repo
# Nombre sugerido: grafana-dashboard-screenshot.png
```

---

## 🚨 Paso 6 (Opcional): Configurar Alertas

### 6.1 Crear Reglas de Alerta en Prometheus

Edita `prometheus-configmap.yml` y añade:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-alerts
  namespace: monitoring
data:
  alerts.yml: |
    groups:
    - name: application_alerts
      interval: 30s
      rules:
      - alert: HighErrorRate
        expr: rate(app_requests_total{http_status=~"5.."}[5m]) / rate(app_requests_total[5m]) * 100 > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% for {{ $labels.instance }}"
      
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total{pod=~"simple-app.*"}[5m]) > 0.8
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High CPU usage on pod {{ $labels.pod }}"
          description: "CPU usage is {{ $value | humanizePercentage }}"
      
      - alert: HighMemoryUsage
        expr: container_memory_working_set_bytes{pod=~"simple-app.*"} / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on pod {{ $labels.pod }}"
```

Aplica:
```bash
kubectl apply -f prometheus-configmap.yml -n monitoring
kubectl rollout restart deployment/prometheus -n monitoring
```

### 6.2 Ver Alertas en Prometheus

1. Abre Prometheus UI: `http://localhost:9090`
2. Ve a **Alerts**
3. Deberías ver tus reglas listadas (HighErrorRate, HighCPUUsage, etc.)

### 6.3 Configurar Notificaciones en Grafana

1. En Grafana, ve a **Alerting** → **Notification channels**
2. Click **Add channel**
3. Opciones:
   - **Type**: Email, Slack, Webhook, etc.
   - **Name**: "Email Alerts"
   - Configura según tu método preferido

**Ejemplo Email (requiere SMTP):**
```yaml
# Añadir a grafana-deployment.yml en env:
- name: GF_SMTP_ENABLED
  value: "true"
- name: GF_SMTP_HOST
  value: "smtp.gmail.com:587"
- name: GF_SMTP_USER
  value: "tu-email@gmail.com"
- name: GF_SMTP_PASSWORD
  value: "tu-app-password"
```

### 6.4 Testing de Alertas

**Simular High Error Rate:**
```bash
# Modifica tu app para devolver 500 errors temporalmente
# O usa curl para llamar a un endpoint inexistente
for i in {1..100}; do
  curl -s http://<URL>/nonexistent > /dev/null
done
```

**Simular High CPU:**
```bash
# Genera carga intensiva
hey -z 120s -c 50 -q 200 http://<NGINX_URL>/
```

**Verificar:**
- En Prometheus, la alerta debería pasar de "Inactive" → "Pending" → "Firing"
- En Grafana, deberías recibir una notificación

---

## 🔧 Troubleshooting

### Problema 1: Prometheus no encuentra targets

**Síntoma:** Status > Targets muestra "0/0 up"

**Solución:**
```bash
# Verificar que los servicios existen
kubectl get svc -n monitoring

# Verificar que los pods están corriendo
kubectl get pods -n monitoring

# Ver logs de Prometheus
kubectl logs -n monitoring deployment/prometheus

# Verificar DNS dentro del cluster
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup prometheus.monitoring.svc.cluster.local
```

### Problema 2: Grafana no puede conectar con Prometheus

**Síntoma:** "Data source is working" falla

**Solución:**
```bash
# Verificar que Prometheus está accesible desde Grafana
kubectl exec -it -n monitoring deployment/grafana -- curl http://prometheus:9090/-/healthy

# Si falla, revisa el servicio
kubectl get svc prometheus -n monitoring -o yaml
```

### Problema 3: No veo métricas de mi aplicación

**Síntoma:** Queries en Grafana devuelven "No data"

**Solución:**
```bash
# Verificar que el endpoint /metrics funciona
kubectl port-forward svc/simple-app 8000:8000
curl http://localhost:8000/metrics

# Verificar que Prometheus está scrapeando
# En Prometheus UI > Status > Targets > busca "simple-app"

# Ver logs del exporter
kubectl logs -n monitoring deployment/nginx-exporter
```

### Problema 4: Exporters no están corriendo

**Síntoma:** Pods de exporters en estado CrashLoopBackOff

**Solución:**
```bash
# Ver por qué falla
kubectl describe pod -n monitoring <POD_NAME>
kubectl logs -n monitoring <POD_NAME>

# Para nginx-exporter, verificar que puede alcanzar nginx
kubectl exec -it -n monitoring deployment/nginx-exporter -- wget -O- http://nginx.default.svc.cluster.local/stub_status

# Para redis-exporter, verificar conexión a Redis
kubectl exec -it -n monitoring deployment/redis-exporter -- redis-cli -h redis.default.svc.cluster.local ping
```

---

## 📚 Queries PromQL Útiles

### Disponibilidad (Uptime)
```promql
up{job="simple-app"}
```

### Tasa de requests por método HTTP
```promql
sum by (method) (rate(app_requests_total[5m]))
```

### Top 5 endpoints más lentos
```promql
topk(5, histogram_quantile(0.95, rate(app_request_latency_seconds_bucket[5m])))
```

### Memoria disponible en nodos
```promql
node_memory_MemAvailable_bytes / 1024 / 1024 / 1024
```

### Pods que han reiniciado recientemente
```promql
changes(kube_pod_container_status_restarts_total[30m]) > 0
```

---

## 🎓 Conceptos Clave

### ¿Qué es observabilidad?
La capacidad de entender el estado interno de un sistema basándose en sus salidas (logs, métricas, traces).

**Los 3 pilares:**
1. **Métricas**: Datos numéricos agregados (CPU, requests/s, latencia)
2. **Logs**: Eventos discretos con contexto
3. **Traces**: Seguimiento de requests a través de servicios

### ¿Por qué Prometheus?
- **Pull-based**: Prometheus scrapea métricas (vs push)
- **Time-series database**: Optimizado para datos temporales
- **PromQL**: Lenguaje de queries potente
- **Service discovery**: Detecta automáticamente targets en Kubernetes

### ¿Por qué Grafana?
- **Visualización flexible**: Múltiples tipos de gráficos
- **Multi-datasource**: Puede combinar Prometheus, Loki, Elasticsearch, etc.
- **Alerting integrado**: Reglas y notificaciones
- **Dashboards como código**: JSON exportable/versionable

---

## 📝 Checklist Final del Entregable

Antes de marcar Challenge A como completo, verifica:

- [ ] **Prometheus desplegado** y accesible en `http://localhost:9090`
- [ ] **Targets configurados**: nginx-exporter, redis-exporter, simple-app aparecen en Status > Targets
- [ ] **Grafana desplegado** y accesible en `http://localhost:3000`
- [ ] **Data source** de Prometheus conectado correctamente
- [ ] **Dashboard creado** con al menos 5 paneles:
  - Request rate
  - Latency (percentil 95)
  - CPU usage
  - Memory usage
  - Error rate
- [ ] **Métricas actualizándose** en tiempo real (auto-refresh activo)
- [ ] **Screenshot** guardado mostrando el dashboard completo con datos reales
- [ ] **Traffic generado** para validar que las métricas responden
- [ ] **(Intermedio)** Reglas de alerta configuradas y testeadas
- [ ] **(Intermedio)** Notificaciones funcionando (logs o email)

---

## 🚀 Próximos Pasos

Una vez completado Challenge A:

1. **Challenge B**: Full Integration Test (Required)
2. **Challenge C**: Documentación completa (Required)
3. **Challenge D**: Preparación para entrevista (Required)

**Consejo:** Mantén Prometheus y Grafana corriendo para Challenge B, ya que las métricas te ayudarán a verificar que todo funciona correctamente durante la integración completa.

---

## 📖 Referencias

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [Nginx Prometheus Exporter](https://github.com/nginxinc/nginx-prometheus-exporter)
- [Redis Exporter](https://github.com/oliver006/redis_exporter)
- [Prometheus Client Libraries](https://prometheus.io/docs/instrumenting/clientlibs/)

---

**¡Éxito con tu Challenge A! 🎯📊**
