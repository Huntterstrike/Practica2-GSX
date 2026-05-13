# Quick Start - Challenge A

## Despliegue rapido en 3 pasos

### Paso 1: Desplegar todo automaticamente
```bash
cd /home/ubuntu/week-13-challenge-a
./deploy-all.sh
```

Este script hace todo lo necesario para la observabilidad de la week 13:
- despliega Prometheus
- despliega Grafana con el datasource ya configurado
- despliega `nginx-exporter`
- despliega `redis-exporter`
- prepara `nginx` y `simple-app` para exponer metricas sin editar archivos de otras weeks

### Paso 2: Acceder a las interfaces

**Prometheus**
```bash
# Opcion 1: NodePort
minikube ip
# Visita: http://<MINIKUBE_IP>:30090

# Opcion 2: Port-forward
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Visita: http://localhost:9090
```

**Grafana**
```bash
# Opcion 1: NodePort
# Visita: http://<MINIKUBE_IP>:30300

# Opcion 2: Port-forward
kubectl port-forward -n monitoring svc/grafana 3000:3000
# Visita: http://localhost:3000
# Credenciales: admin / admin
```

### Paso 3: Verificar que todo funciona
```bash
./test-observability.sh
```

---

## Proceso manual completo

Usa esta seccion si no quieres ejecutar `./deploy-all.sh` y prefieres hacer el proceso completo a mano.

### 0. Requisitos previos

Necesitas tener ya desplegado el stack base de las weeks anteriores en el namespace `default`:
- `deployment/nginx`
- `deployment/simple-app`
- `service/nginx`
- `service/simple-app`
- `service/redis`

Tambien necesitas:
- `kubectl`
- `minikube`
- `curl`
- `jq`

Comprueba acceso al cluster:

```bash
kubectl cluster-info
```

Trabaja siempre desde:

```bash
cd weeks/week-13-final/week-13-challenge-a
```

### 1. Preparar Nginx para exponer `/stub_status`

Aplica el ConfigMap auxiliar:

```bash
kubectl apply -f nginx-stub-status-config.yml
```

Parchea el deployment existente de `nginx` para:
- montar `stub_status.conf`
- abrir un listener en el puerto `8080`

```bash
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
)"
```

Expone el puerto `8080` tambien en el `service/nginx`:

```bash
kubectl patch service nginx -n default --type=strategic -p "$(cat <<'EOF'
spec:
  ports:
  - name: stub-status
    port: 8080
    targetPort: 8080
    protocol: TCP
EOF
)"
```

Espera a que reinicie y verifica el endpoint:

```bash
kubectl rollout status deployment/nginx -n default
kubectl port-forward svc/nginx -n default 8080:8080
curl http://localhost:8080/stub_status
```

Deberias ver algo parecido a:

```text
Active connections: 1
server accepts handled requests
...
```

### 2. Preparar `simple-app` para exponer `/metrics`

En este repo no hace falta reconstruir la imagen base. La week 13 ya incluye `simple-app-observability.py`, que se inyecta como `ConfigMap` sobre el deployment existente.

Crea el ConfigMap:

```bash
kubectl create configmap simple-app-observability \
  --from-file=app.py=./simple-app-observability.py \
  -n default \
  --dry-run=client -o yaml | kubectl apply -f -
```

Parchea el deployment para arrancar con ese archivo:

```bash
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
)"
```

Espera al rollout y verifica el endpoint:

```bash
kubectl rollout status deployment/simple-app -n default
kubectl port-forward svc/simple-app -n default 5000:5000
curl http://localhost:5000/metrics
```

### 3. Crear el namespace `monitoring`

```bash
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
```

### 4. Desplegar Prometheus

```bash
kubectl apply -f prometheus-configmap.yml -n monitoring
kubectl apply -f prometheus-deployment.yml -n monitoring
kubectl apply -f prometheus-service.yml -n monitoring
kubectl rollout status deployment/prometheus -n monitoring
```

### 5. Desplegar Exporters

```bash
kubectl apply -f nginx-exporter-deployment.yml -n monitoring
kubectl apply -f nginx-exporter-service.yml -n monitoring

kubectl apply -f redis-exporter-deployment.yml -n monitoring
kubectl apply -f redis-exporter-service.yml -n monitoring

kubectl rollout status deployment/nginx-exporter -n monitoring
kubectl rollout status deployment/redis-exporter -n monitoring
```

### 6. Desplegar Grafana

```bash
kubectl apply -f grafana-deployment.yml -n monitoring
kubectl apply -f grafana-service.yml -n monitoring
kubectl rollout status deployment/grafana -n monitoring
```

Si reaplicas cambios sobre un stack ya desplegado, reinicia Prometheus y Grafana para forzar la recarga:

```bash
kubectl rollout restart deployment/prometheus -n monitoring
kubectl rollout restart deployment/grafana -n monitoring
kubectl rollout status deployment/prometheus -n monitoring
kubectl rollout status deployment/grafana -n monitoring
```

### 7. Verificar el estado final

Comprueba los pods:

```bash
kubectl get pods -n monitoring
```

Abre Prometheus y revisa `Status -> Targets`:

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

Los targets importantes deberian quedar en `UP`:
- `prometheus`
- `redis`
- `nginx`
- `simple-app`
- `kubernetes-nodes`

Lanza despues el test:

```bash
./test-observability.sh
```

---

## Crear tu dashboard en Grafana

Esta es la parte que suele costar mas si no conoces bien la UI de Grafana 10. Sigue estos pasos tal cual.

### 1. Abrir Grafana

Si aun no lo tienes abierto:

```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

Abre:

```text
http://localhost:3000
```

Credenciales por defecto:
- usuario: `admin`
- password: `admin`

Importante:
- para que `./test-observability.sh` siga funcionando, no cambies la password antes de pasar el test
- si ya la cambiaste y el test falla por autenticacion, reiniciar `deployment/grafana` devuelve este setup a `admin/admin`

### 2. Encontrar el datasource de Prometheus

En Grafana 10 la ruta normal es:

- menu lateral izquierdo
- `Connections`
- `Data sources`
- `Prometheus`

Si no encuentras `Connections`, usa el buscador superior de Grafana y escribe `data sources`.

Dentro del datasource comprueba:
- Name: `Prometheus`
- URL: `http://prometheus:9090`
- `Default` activado

Pulsa:

- `Save & test`

Deberias ver un mensaje tipo:

```text
data source is working
```

### 3. Crear un dashboard nuevo

La ruta mas clara es:

- menu lateral izquierdo
- `Dashboards`
- `New`
- `New dashboard`
- `Add visualization`

Cuando te pregunte datasource, elige:

- `Prometheus`

Se abrira el editor de panel. Las zonas importantes son:

- centro: la grafica de previsualizacion
- parte inferior: la query PromQL
- panel derecho: `Panel options`, `Standard options`, `Legend`, etc.
- arriba a la derecha: `Run queries` y `Apply`

Consejo:
- cada vez que termines un panel, pulsa `Apply`
- si no pulsas `Apply`, el panel no se guarda en el dashboard

### 4. Crear primero un panel de diagnostico

Antes de hacer el dashboard final, crea un panel simple para comprobar que Grafana recibe datos.

#### Panel 0: Targets UP

En el editor:

- Titulo: `Targets UP`
- Visualization: `Stat`
- Query:

```promql
up
```

Pulsa:

- `Run queries`

Si todo esta bien, veras varios valores `1`.

Luego pulsa:

- `Apply`

Esto te devuelve al dashboard.

### 5. Crear los paneles del dashboard final

Para cada panel nuevo:

- arriba a la derecha en el dashboard
- `Add`
- `Visualization`
- elige `Prometheus`

#### Panel 1: Request Rate

Usa:

```promql
rate(app_requests_total[5m])
```

Configuralo asi:
- Titulo: `Request Rate`
- Visualization: `Time series`
- Unit: `reqps` si te aparece, o deja `short`
- Legend: muestra `{{endpoint}} {{http_status}}`

Que deberias ver:
- una linea moviendose cuando generas trafico

Si ves `No data`:
- genera trafico con `curl`
- espera 30-60 segundos

#### Panel 2: Request Latency P95

Usa esta query:

```promql
histogram_quantile(0.95, sum by (le, endpoint) (rate(app_request_latency_seconds_bucket[5m])))
```

Configuralo asi:
- Titulo: `Request Latency P95`
- Visualization: `Time series`
- Unit: `s`
- Legend: `{{endpoint}}`

Que deberias ver:
- latencia baja para `/`
- latencia alta si llamas a `/slow`

#### Panel 3: CPU Usage de simple-app

Usa esta query:

```promql
rate(container_cpu_usage_seconds_total{namespace="default",pod=~"simple-app.*"}[5m])
```

Configuralo asi:
- Titulo: `CPU Usage - simple-app`
- Visualization: `Time series`
- Unit: `percent (0.0-1.0)` o `short`
- Legend: `{{pod}}`

Importante:
- filtramos `namespace="default"` porque en tu cluster puede haber otros `simple-app` de otras weeks

#### Panel 4: Memory Usage de simple-app

Usa esta query:

```promql
container_memory_working_set_bytes{namespace="default",pod=~"simple-app.*"} / 1024 / 1024
```

Configuralo asi:
- Titulo: `Memory Usage - simple-app`
- Visualization: `Time series`
- Unit: `MiB`
- Legend: `{{pod}}`

Que deberias ver:
- una linea con el consumo de memoria del pod

#### Panel 5: Redis Commands

Usa:

```promql
rate(redis_commands_processed_total[5m])
```

Configuralo asi:
- Titulo: `Redis Commands`
- Visualization: `Time series`
- Unit: `ops`
- Legend: `{{instance}}`

Que deberias ver:
- actividad cuando `simple-app` recibe peticiones y toca Redis

#### Panel 6: Nginx Requests

Usa:

```promql
rate(nginx_http_requests_total[5m])
```

Configuralo asi:
- Titulo: `Nginx Requests`
- Visualization: `Time series`
- Unit: `reqps` si esta disponible
- Legend: `{{instance}}`

Que deberias ver:
- actividad cuando el trafico pasa por `nginx`

#### Panel 7: Error Rate

Usa:

```promql
rate(app_requests_total{http_status=~"5.."}[5m]) / rate(app_requests_total[5m]) * 100
```

Configuralo asi:
- Titulo: `Error Rate`
- Visualization: `Time series`
- Unit: `percent (0-100)`

Opcional:
- en `Thresholds`, marca amarillo a partir de `1`
- marca rojo a partir de `5`

#### Panel 8: Estado de servicios

Este panel ayuda mucho para la demo y para depurar.

Usa:

```promql
up
```

Configuralo asi:
- Titulo: `Service Status`
- Visualization: `Table` o `Stat`

### 6. Orden recomendado del dashboard

Una distribucion sencilla que queda bien:

- fila 1: `Targets UP`, `Error Rate`
- fila 2: `Request Rate`, `Request Latency P95`
- fila 3: `CPU Usage - simple-app`, `Memory Usage - simple-app`
- fila 4: `Redis Commands`, `Nginx Requests`

Para mover paneles:

- vuelve al dashboard
- arrastra cada panel desde la cabecera

### 7. Ajustes generales del dashboard

En la esquina superior derecha del dashboard:

- Time range: `Last 15 minutes`
- Refresh: `5s`

Luego pulsa guardar:

- icono `Save dashboard`
- Name: `GreenDevCorp Monitoring`
- Folder: `General`

### 8. Como generar datos para que se vean las graficas

Abre otra terminal y lanza trafico continuo:

```bash
while true; do curl -s $(minikube service nginx --url) > /dev/null; sleep 0.1; done
```

Si quieres provocar paneles concretos:

- latencia:

```bash
kubectl port-forward svc/simple-app -n default 5000:5000
curl http://localhost:5000/slow
```

- errores:

```bash
kubectl port-forward svc/simple-app -n default 5000:5000
curl -i http://localhost:5000/error
```

### 9. Si no encuentras algo en la UI

Casos comunes:

- no encuentras `Data sources`
  - usa el buscador superior y escribe `data sources`

- no encuentras `Add visualization`
  - entra en `Dashboards`
  - abre tu dashboard
  - arriba a la derecha usa `Add`

- haces una query y no sale nada
  - pulsa `Run queries`
  - comprueba `Status -> Targets` en Prometheus
  - genera trafico y espera unos segundos

- ves datos de pods de otras weeks
  - asegúrate de usar `namespace="default"` en CPU y memoria

### 10. Checklist rapido de Grafana

Antes de hacer la captura final:

- [ ] el datasource `Prometheus` responde `Save & test`
- [ ] el panel `Targets UP` muestra valores `1`
- [ ] `Request Rate` se mueve al generar trafico
- [ ] `Nginx Requests` se mueve al generar trafico
- [ ] `Redis Commands` se mueve al generar trafico
- [ ] `CPU` y `Memory` muestran datos del pod `simple-app`
- [ ] el dashboard esta guardado
- [ ] el time range y el refresh se ven en la captura

---

## Notas sobre `simple-app`

En este repo tienes dos opciones:

1. Usar el overlay de la week 13
   - es lo que hacen `deploy-all.sh` y el proceso manual de esta guia
   - no reconstruye la imagen base
   - no modifica archivos de otras weeks

2. Instrumentar tu propia aplicacion de forma nativa
   - usa `simple-app-metrics-example.py` como referencia
   - esta opcion es util si quieres integrar Prometheus dentro del codigo fuente real de la app

---

## Generar trafico para testing

### Opcion 1: Loop con curl
```bash
NGINX_URL=$(minikube service nginx --url)
while true; do
  curl -s "$NGINX_URL" > /dev/null
  sleep 0.1
done
```

### Opcion 2: Load testing con hey
```bash
go install github.com/rakyll/hey@latest
hey -z 60s -c 10 "$(minikube service nginx --url)"
```

---

## Screenshot para el entregable

1. Genera trafico durante 2-3 minutos
2. Abre Grafana con tu dashboard
3. Espera a que todos los paneles muestren datos
4. Toma una captura mostrando:
   - paneles con graficas
   - metricas actualizandose
   - time range visible
   - fecha/hora actual

---

## Si algo falla

### Ver logs de Prometheus
```bash
kubectl logs -n monitoring deployment/prometheus -f
```

### Ver logs de Grafana
```bash
kubectl logs -n monitoring deployment/grafana -f
```

### Ver logs de Nginx Exporter
```bash
kubectl logs -n monitoring deployment/nginx-exporter -f
```

### Ver targets en Prometheus
```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

Luego entra en:

```text
http://localhost:9090/targets
```

### Validar de nuevo el stack
```bash
./test-observability.sh
```

### Reiniciar solo monitoring
```bash
kubectl delete namespace monitoring
./deploy-all.sh
```

---

## Checklist del entregable

Antes de marcar Challenge A como completo:

- [ ] Prometheus desplegado y accesible
- [ ] Grafana desplegado con datasource conectado
- [ ] `prometheus`, `redis`, `nginx`, `simple-app` y `kubernetes-nodes` en `UP`
- [ ] Dashboard creado con al menos 5 paneles utiles
- [ ] Metricas actualizandose en tiempo real
- [ ] Screenshot del dashboard funcionando
- [ ] Test `./test-observability.sh` pasando

---

## Referencias rapidas

**PromQL basico**
```promql
up
rate(metric_name[5m])
sum by (label_name) (metric_name)
histogram_quantile(0.95, rate(metric_bucket[5m]))
topk(5, metric_name)
```

**Comandos utiles**
```bash
kubectl get pods -n monitoring
kubectl get svc -n monitoring
kubectl logs -n monitoring deployment/prometheus -f
kubectl logs -n monitoring deployment/grafana -f
kubectl describe pod -n monitoring <POD_NAME>
```

---

## Listo

Si completaste todos los pasos, ya tienes un stack de observabilidad funcionando para la week 13.

Siguientes challenges:
- Challenge B: Full Integration Test
- Challenge C: Documentation
- Challenge D: Interview Prep
