# Runbook Operativo — Week 13

> Procedimientos estándar de operación para el stack GreenDevCorp  
> Autor: Gaizka Alonso Martínez

## Índice

- [Acceso y comprobaciones básicas](#acceso-y-comprobaciones-básicas)
- [Despliegue completo desde cero](#despliegue-completo-desde-cero)
- [Despliegue de nueva versión](#despliegue-de-nueva-versión)
- [Rollback](#rollback)
- [Escalado de servicios](#escalado-de-servicios)
- [Gestión de logs](#gestión-de-logs)
- [Verificación end-to-end](#verificación-end-to-end)
- [Backups y persistencia](#backups-y-persistencia)
- [Gestión de NetworkPolicies](#gestión-de-networkpolicies)
- [Mantenimiento programado](#mantenimiento-programado)
- [Comandos de referencia rápida](#comandos-de-referencia-rápida)

---

## Acceso y comprobaciones básicas

### Verificar estado del clúster

```bash
kubectl cluster-info
minikube status
```

### Ver estado general de todos los recursos

```bash
kubectl get pods -o wide
kubectl get svc -o wide
kubectl get deploy -o wide
kubectl get statefulsets -o wide
kubectl get networkpolicies
kubectl get pvc
```

### Verificar que todos los pods están Running y Ready

```bash
kubectl get pods -o json | jq '.items[] | {name: .metadata.name, phase: .status.phase, ready: (.status.conditions[] | select(.type=="Ready") | .status)}'
```

### Verificar conectividad del servicio

```bash
minikube service nginx --url
# Copiar la URL y probar con curl
curl <URL>/api
```

---

## Despliegue completo desde cero

### Paso 1: Iniciar Minikube con Calico

```bash
minikube start --cni=calico --memory=4096 --cpus=2
# Esperar a que Calico esté listo
kubectl -n kube-system wait --for=condition=Ready pods -l k8s-app=calico-node --timeout=120s
```

### Paso 2: Construir imágenes base (Week 8)

```bash
cd weeks/week-08-docker
eval $(minikube docker-env)
docker build -t nginx-gsx:latest ./nginx
docker build -t simple-app-gsx:latest ./simple-app
```

### Paso 3: Aplicar manifiestos de Kubernetes

```bash
kubectl apply -f kubernetes/
```

### Paso 4: Esperar a que todos los pods estén listos

```bash
kubectl wait --for=condition=Ready pods --all --timeout=120s
```

### Paso 5: Verificar

```bash
kubectl get pods
kubectl get svc
NGINX_URL=$(minikube service nginx --url)
curl $NGINX_URL/api
# Esperado: "Hello from K8s | Visits: 1"
```

### Alternativa con Terraform

```bash
cd terraform/
terraform init
terraform apply -auto-approve
```

---

## Despliegue de nueva versión

### Procedimiento seguro (rolling update)

1. **Construir nueva imagen con tag específico:**

```bash
eval $(minikube docker-env)
docker build -t simple-app-gsx:v2.0 ./simple-app
```

2. **Actualizar el deployment:**

```bash
kubectl set image deployment/simple-app simple-app=simple-app-gsx:v2.0
```

3. **Monitorizar el rollout:**

```bash
kubectl rollout status deployment/simple-app
```

4. **Verificar que la nueva versión funciona:**

```bash
curl $(minikube service nginx --url)/api
kubectl get pods -l app=simple-app
```

5. **Comprobar historial de rollouts:**

```bash
kubectl rollout history deployment/simple-app
```

---

## Rollback

### Si falla un despliegue

```bash
# Ver historial
kubectl rollout history deployment/simple-app

# Rollback a la versión anterior
kubectl rollout undo deployment/simple-app

# Rollback a una revisión específica
kubectl rollout undo deployment/simple-app --to-revision=2

# Verificar estado
kubectl rollout status deployment/simple-app
kubectl get pods -l app=simple-app
```

---

## Escalado de servicios

### Escalar nginx

```bash
# Escalar a 3 réplicas
kubectl scale deployment/nginx --replicas=3

# Verificar
kubectl get pods -l app=nginx
```

### Escalar simple-app

```bash
kubectl scale deployment/simple-app --replicas=3
kubectl get pods -l app=simple-app
```

### ⚠️ Redis NO debe escalarse sin configurar replicación

Redis en modo standalone (StatefulSet con 1 réplica) no soporta escalado horizontal directo. Escalar a >1 réplica sin configurar Redis Sentinel o Cluster causará inconsistencias de datos.

---

## Gestión de logs

### Ver logs de un pod específico

```bash
kubectl logs -f deployment/nginx
kubectl logs -f deployment/simple-app
kubectl logs -f statefulset/redis
```

### Ver las últimas 50 líneas

```bash
kubectl logs --tail=50 deployment/simple-app
```

### Logs de un pod que ha fallado (pod anterior)

```bash
kubectl logs <pod-name> --previous
```

### Logs con timestamp

```bash
kubectl logs -f deployment/simple-app --timestamps=true
```

### Logs de todos los pods con un label

```bash
kubectl logs -l app=simple-app --all-containers
```

---

## Verificación end-to-end

### Test completo automatizado

```bash
python3 verify_integration.py --apply-manifests --manifests kubernetes/ --timeout 180
```

### Tests manuales

#### 1. Acceso externo (cliente → nginx)

```bash
NGINX_URL=$(minikube service nginx --url)
curl -v $NGINX_URL/api
# Esperado: HTTP 200, body contiene "Visits:"
```

#### 2. Conectividad interna (nginx → simple-app)

```bash
NGINX_POD=$(kubectl get pod -l app=nginx -o jsonpath='{.items[0].metadata.name}')
kubectl exec $NGINX_POD -- curl -s http://simple-app:5000/health
# Esperado: "OK" o respuesta de health check
```

#### 3. Backend → Redis

```bash
APP_POD=$(kubectl get pod -l app=simple-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec $APP_POD -- python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('redis',6379)); print('OK')"
```

#### 4. Redis datos

```bash
REDIS_POD=$(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec $REDIS_POD -- redis-cli get visits
```

#### 5. NetworkPolicy — bloqueo de tráfico no autorizado

```bash
# Crear pod de prueba con label env=dev
kubectl run test-dev --image=busybox --labels=env=dev --restart=Never -- sleep 30

# Intentar acceder a simple-app (debería fallar/timeout)
kubectl exec test-dev -- wget -T 2 -qO- http://simple-app:5000/health
# Esperado: timeout o connection refused

# Limpiar
kubectl delete pod test-dev --now
```

#### 6. Test de persistencia

```bash
# Anotar el valor actual
kubectl exec $REDIS_POD -- redis-cli get visits

# Eliminar el pod de Redis (se recrea automáticamente)
kubectl delete pod $REDIS_POD

# Esperar a que el nuevo pod esté listo
kubectl wait --for=condition=Ready pod -l app=redis --timeout=60s

# Verificar que el contador sigue intacto
kubectl exec $(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli get visits
```

---

## Backups y persistencia

### Exportar datos de Redis

```bash
REDIS_POD=$(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}')

# Forzar guardado en disco
kubectl exec $REDIS_POD -- redis-cli BGSAVE

# Copiar el dump a local
kubectl cp $REDIS_POD:/data/dump.rdb ./backup-redis-$(date +%Y%m%d).rdb
```

### Verificar PVC

```bash
kubectl get pvc
kubectl describe pvc redis-data
```

### Restaurar datos

```bash
# Copiar dump al pod
kubectl cp ./backup-redis-YYYYMMDD.rdb $REDIS_POD:/data/dump.rdb

# Reiniciar Redis para cargar el dump
kubectl delete pod $REDIS_POD
# StatefulSet recrea el pod automáticamente con el PVC
```

---

## Gestión de NetworkPolicies

### Ver policies activas

```bash
kubectl get networkpolicies
kubectl describe networkpolicy <nombre>
```

### Aplicar nueva policy

```bash
kubectl apply -f kubernetes/network-policies/
```

### Verificar que DNS funciona (tras aplicar policies)

```bash
kubectl exec $APP_POD -- nslookup redis
kubectl exec $NGINX_POD -- nslookup simple-app
```

---

## Mantenimiento programado

### Actualizar imágenes base

```bash
eval $(minikube docker-env)
docker pull nginx:1.25-alpine
docker pull redis:7-alpine
docker pull python:3.11-slim
# Reconstruir imágenes personalizadas
docker build -t nginx-gsx:latest ./nginx
docker build -t simple-app-gsx:latest ./simple-app
# Reiniciar deployments
kubectl rollout restart deployment/nginx
kubectl rollout restart deployment/simple-app
```

### Limpieza de recursos

```bash
# Eliminar pods evicted o en error
kubectl delete pods --field-selector=status.phase=Failed

# Limpiar imágenes no usadas en Minikube
minikube ssh -- docker image prune -f
```

---

## Comandos de referencia rápida

| Acción | Comando |
|---|---|
| Estado de pods | `kubectl get pods -o wide` |
| Logs en tiempo real | `kubectl logs -f deploy/<nombre>` |
| Escalar servicio | `kubectl scale deploy/<nombre> --replicas=N` |
| Rollback | `kubectl rollout undo deploy/<nombre>` |
| Exec en pod | `kubectl exec -it <pod> -- /bin/sh` |
| Describir recurso | `kubectl describe pod/<nombre>` |
| Ver eventos | `kubectl get events --sort-by=.lastTimestamp` |
| IP de Minikube | `minikube ip` |
| URL del servicio | `minikube service nginx --url` |
| Aplicar manifiestos | `kubectl apply -f kubernetes/` |
| Eliminar todo | `kubectl delete -f kubernetes/` |
| Validar YAML | `kubectl apply --dry-run=client -f <fichero>` |
