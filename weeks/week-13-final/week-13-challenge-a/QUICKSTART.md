# Quick Start - Week 13 Challenge A

Esta guia recoge el proceso completo que hemos usado para validar Challenge A de la week 13:

- core/basic
- intermediate/alerting

## 0. Que valida esta guia

Al terminar, tendras validado todo esto:

- stack base de `nginx`, `simple-app` y `redis` funcionando en Kubernetes
- Prometheus desplegado y recolectando metricas
- Grafana desplegado y conectado a Prometheus
- dashboard con las metricas pedidas en el enunciado
- trafico real y metricas moviendose
- reglas de alerta cargadas en Prometheus
- Alertmanager desplegado
- notificaciones funcionando mediante webhook interno a `alert-receiver`

## 1. Requisitos

Necesitas:

- `minikube`
- `kubectl`
- `bash`
- `curl`
- `jq`

Trabaja desde la raiz del repo:

```bash
cd /c/Users/alvar/OneDrive/Desktop/UNI/3r_Curs/2n_quatri/GSX/Practiques/Practica2-GSX
```

## 2. Arrancar Minikube

```bash
minikube start
kubectl cluster-info
```

Si `kubectl cluster-info` falla, no sigas hasta arreglar eso.

## 3. Construir las imagenes base dentro de Minikube

Estas dos imagenes son las que usa el stack base:

```bash
minikube image build -t nginx-gsx:latest weeks/week-08-docker/nginx
minikube image build -t simple-app-gsx:latest -f weeks/week-11-iac/docker/simple-app.Dockerfile .
```

## 4. Desplegar el stack base de la week 10

La observabilidad de la week 13 esta preparada para trabajar sobre el stack base en el namespace `default`.

```bash
kubectl apply -f weeks/week-10-k8s/kubernetes
```

Espera a que todo quede listo:

```bash
kubectl rollout status deployment/simple-app --timeout=180s
kubectl rollout status deployment/nginx --timeout=180s
kubectl rollout status statefulset/redis --timeout=180s
kubectl get pods -n default
```

Debes ver en `Running`:

- `nginx`
- `simple-app`
- `redis-0`

## 5. Desplegar observabilidad y alerting de la week 13

```bash
cd weeks/week-13-final/week-13-challenge-a
bash ./deploy-all.sh
```

Este script hace todo esto:

- prepara `nginx` para exponer `/stub_status`
- inyecta una version instrumentada de `simple-app`
- despliega Prometheus
- despliega `nginx-exporter`
- despliega `redis-exporter`
- despliega Grafana
- despliega Alertmanager
- despliega `alert-receiver`
- reinicia Prometheus para cargar reglas y alerting

Comprueba el resultado:

```bash
kubectl get pods -n monitoring
```

Debes ver en `Running`:

- `prometheus`
- `grafana`
- `nginx-exporter`
- `redis-exporter`
- `alertmanager`
- `alert-receiver`

## 6. Abrir las interfaces y logs

Abre una terminal por comando y deja cada proceso corriendo.

### 6.1 Prometheus

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

Abre:

```text
http://localhost:9090
```

### 6.2 Grafana

```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

Abre:

```text
http://localhost:3000
```

Credenciales:

```text
admin / admin
```

### 6.3 Alertmanager

```bash
kubectl port-forward -n monitoring svc/alertmanager 9093:9093
```

Abre:

```text
http://localhost:9093
```

### 6.4 Logs del receptor de alertas

```bash
kubectl logs -n monitoring deployment/alert-receiver -f
```

### 6.5 Acceso directo a simple-app para pruebas de latencia y errores

```bash
kubectl port-forward -n default svc/simple-app 5000:5000
```

## 7. Validar Prometheus para el core

### 7.1 Targets

En Prometheus ve a:

- `Status -> Targets`

Estos jobs deben estar en `UP`:

- `prometheus`
- `redis`
- `nginx`
- `simple-app`
- `kubernetes-nodes`

### 7.2 Queries minimas

En la pestana `Graph`, ejecuta una por una:

```promql
up
```

```promql
app_requests_total
```

```promql
nginx_http_requests_total
```

```promql
container_memory_working_set_bytes{namespace="default",pod=~"simple-app.*"}
```

Resultado esperado:

- `up` devuelve varias series con valor `1`
- `app_requests_total` devuelve datos
- `nginx_http_requests_total` devuelve datos
- `container_memory_working_set_bytes{...}` devuelve datos

Si alguna sale vacia, no pases a Grafana todavia.

## 8. Validar el datasource en Grafana

En Grafana:

- `Connections -> Data sources -> Prometheus`
- pulsa `Save & test`

Debe salir algo como:

```text
data source is working
```

## 9. Crear el dashboard de Grafana

La UI que vas a usar es:

- `Dashboards -> New -> New dashboard -> Add visualization`
- elige `Prometheus`

Dentro del editor del panel veras:

- centro: previsualizacion
- parte inferior: query PromQL
- barra derecha: `Visualization`, `Panel options`, etc.
- arriba a la derecha: `Run queries` y `Apply`

Cada vez que crees o edites un panel:

1. pega la query
2. pulsa `Run queries`
3. ajusta `Visualization`
4. pon el titulo en `Panel options`
5. pulsa `Apply`

## 10. Crear los paneles del core

### 10.1 Panel de diagnostico: Targets UP

- `Visualization`: `Table`
- Titulo: `Targets UP`
- Query:

```promql
up
```

Pulsa `Apply`.

### 10.2 Generar trafico continuo

Abre otra terminal y deja esto corriendo:

```bash
while true; do curl -s $(minikube service nginx --url) > /dev/null; sleep 0.1; done
```

Muchas queries de tipo `rate(...)` no se mueven sin trafico.

### 10.3 Request Rate

- `Visualization`: `Time series`
- Titulo: `Request Rate`
- Query:

```promql
rate(app_requests_total[5m])
```

Si quieres distinguir lineas, usa esta leyenda:

```text
{{endpoint}} {{http_status}}
```

Es normal ver varias lineas si hay distintas combinaciones de `endpoint` y `http_status`.

### 10.4 Nginx Requests

- `Visualization`: `Time series`
- Titulo: `Nginx Requests`
- Query:

```promql
rate(nginx_http_requests_total[5m])
```

### 10.5 Request Latency P95

- `Visualization`: `Time series`
- Titulo: `Request Latency P95`
- Query:

```promql
histogram_quantile(0.95, sum by (le, endpoint) (rate(app_request_latency_seconds_bucket[5m])))
```

### 10.6 CPU Usage - simple-app

- `Visualization`: `Time series`
- Titulo: `CPU Usage - simple-app`
- Query:

```promql
rate(container_cpu_usage_seconds_total{namespace="default",pod=~"simple-app.*"}[5m])
```

### 10.7 Memory Usage - simple-app

- `Visualization`: `Time series`
- Titulo: `Memory Usage - simple-app`
- Query:

```promql
container_memory_working_set_bytes{namespace="default",pod=~"simple-app.*"} / 1024 / 1024
```

Si Grafana te deja elegir unidad, usa `MiB`.

### 10.8 Error Rate

- `Visualization`: `Time series`
- Titulo: `Error Rate`
- Query:

```promql
rate(app_requests_total{http_status=~"5.."}[5m]) / rate(app_requests_total[5m]) * 100
```

Nota importante:

- este panel no es un contador acumulado
- es una tasa/porcentaje sobre una ventana movil
- por eso la grafica puede subir y bajar

Si al principio sale `No data`, es normal si aun no has provocado errores `5xx`.

## 11. Hacer visibles latencia y errores

### 11.1 Forzar latencia

En una terminal:

```bash
curl http://localhost:5000/slow
```

Con esto deberias ver movimiento en `Request Latency P95`.

### 11.2 Forzar errores

En una terminal:

```bash
for i in {1..20}; do curl -i http://localhost:5000/error; sleep 0.2; done
```

Con esto deberias ver movimiento en `Error Rate`.

## 12. Ajustes finales del dashboard

En la esquina superior derecha del dashboard:

- `Last 15 minutes`
- `Refresh 5s`

Guarda el dashboard:

- `Save dashboard`
- nombre recomendado: `GreenDevCorp Monitoring`

Importante:

- si recargas la pagina, el dashboard guardado sigue ahi
- si se recrea el pod de Grafana, el dashboard se pierde porque el despliegue usa `emptyDir`

## 13. Validar el intermediate en Prometheus

Abre:

```text
http://localhost:9090/alerts
```

Debes ver estas reglas:

- `HighErrorRate`
- `HighCPUUsage`
- `HighMemoryUsage`
- `ServiceDown`
- `RedisHighRejectedConnections`
- `HighRequestLatency`

## 14. Probar una alerta real de punta a punta

La validacion principal del intermediate la haremos con `HighErrorRate`.

### 14.1 Deja abiertas estas tres cosas

- `http://localhost:9090/alerts`
- `http://localhost:9093`
- la terminal con:

```bash
kubectl logs -n monitoring deployment/alert-receiver -f
```

### 14.2 Disparar errores

Con el port-forward de `simple-app` aun corriendo, ejecuta:

```bash
for i in {1..50}; do curl -s -o /dev/null http://localhost:5000/error; sleep 1; done
```

### 14.3 Que debes ver

En Prometheus:

- `HighErrorRate` pasa por `inactive -> pending -> firing`

En Alertmanager:

- la alerta aparece en la UI de `http://localhost:9093`

En la terminal de logs:

```text
[alert-receiver] /alerts HighErrorRate=firing
```

Con esto queda validado:

- la regla existe
- Prometheus la evalua
- Alertmanager la recibe
- la notificacion sale por webhook
- el receptor la procesa

## 15. Que significa la notificacion en este proyecto

En esta practica, la notificacion del intermediate queda implementada asi:

- Prometheus envia la alerta a Alertmanager
- Alertmanager envia un webhook a `alert-receiver`
- `alert-receiver` deja la evidencia en logs

No estamos usando email externo. La notificacion funcional de esta entrega es por webhook interno y logs.

## 16. Ejecutar el test automatizado

Al final, ejecuta:

```bash
./test-observability.sh
```

Esto sirve como smoke test del stack, pero no sustituye la validacion manual del dashboard ni la prueba real de alertas.

## 17. Evidencias para la entrega

Minimo recomendable:

1. Captura de Grafana con:
   - `Request Rate`
   - `Request Latency P95`
   - `CPU Usage - simple-app`
   - `Memory Usage - simple-app`
   - `Error Rate`
   - `Last 15 minutes`
   - `Refresh 5s`

2. Captura de Prometheus en:
   - `Status -> Targets`
   - o `Alerts`

3. Captura de Alertmanager mostrando la alerta

4. Evidencia de logs del receptor:

```text
[alert-receiver] /alerts HighErrorRate=firing
```

## 18. Checklist final

Antes de dar Challenge A por cerrado, revisa:

- [ ] `nginx`, `simple-app` y `redis` estan en `Running`
- [ ] `prometheus`, `grafana`, `nginx-exporter`, `redis-exporter`, `alertmanager` y `alert-receiver` estan en `Running`
- [ ] `prometheus`, `redis`, `nginx`, `simple-app` y `kubernetes-nodes` estan en `UP`
- [ ] las queries base en Prometheus devuelven datos
- [ ] el datasource de Grafana responde `Save & test`
- [ ] el dashboard esta guardado
- [ ] el dashboard muestra request rate, latency, CPU, memory y error rate
- [ ] hay trafico real y las metricas se mueven
- [ ] `HighErrorRate` pasa a `firing`
- [ ] Alertmanager muestra la alerta
- [ ] `alert-receiver` recibe la notificacion
- [ ] `./test-observability.sh` pasa

## 19. Resumen corto

Si has seguido toda esta guia y todo responde como se espera, puedes defender honestamente que tienes:

- Challenge A core/basic completado
- Challenge A intermediate completado

En este proyecto, el intermediate queda demostrado con reglas reales, Alertmanager y notificacion por webhook interno con evidencia en logs.
