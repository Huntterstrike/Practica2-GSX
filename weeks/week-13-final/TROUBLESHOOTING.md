# Guía de Troubleshooting — Semanas 8–13

> Problemas comunes encontrados durante el desarrollo del proyecto GreenDevCorp y sus soluciones  
> Autor: Gaizka Alonso Martínez

## Índice

- [Docker (Week 8)](#1-docker-week-8)
- [Docker Compose (Week 9)](#2-docker-compose-week-9)
- [Kubernetes — Pods y Deployments (Week 10)](#3-kubernetes--pods-y-deployments-week-10)
- [Kubernetes — Service Discovery (Week 10)](#4-kubernetes--service-discovery-week-10)
- [Kubernetes — Persistent Volumes (Week 10)](#5-kubernetes--persistent-volumes-week-10)
- [Kubernetes — NetworkPolicies (Week 12)](#6-kubernetes--networkpolicies-week-12)
- [Terraform / IaC (Week 11)](#7-terraform--iac-week-11)
- [Integración completa (Week 13)](#8-integración-completa-week-13)
- [Comandos de diagnóstico esenciales](#9-comandos-de-diagnóstico-esenciales)

---

## 1. Docker (Week 8)

### Problema: `docker build` falla con "COPY failed: file not found"

**Síntomas:** El build de la imagen falla porque no encuentra un fichero en el contexto.

**Causa:** El fichero no está en el directorio de contexto del build, o `.dockerignore` lo está excluyendo.

**Solución:**
```bash
# Verificar que estás en el directorio correcto
ls -la ./nginx/default.conf
ls -la ./simple-app/app.py

# Comprobar .dockerignore
cat .dockerignore

# Build con contexto explícito
docker build -t nginx-gsx ./nginx
```

---

### Problema: La imagen se construye pero el contenedor no arranca

**Síntomas:** `docker run` termina inmediatamente o muestra errores.

**Diagnóstico:**
```bash
# Ver logs del contenedor
docker logs <container-id>

# Inspeccionar la imagen
docker inspect nginx-gsx

# Ejecutar shell para depurar
docker run -it --entrypoint /bin/sh nginx-gsx
```

**Causas comunes:**
- `CMD` o `ENTRYPOINT` incorrectos en el Dockerfile
- Dependencias de Python no instaladas (`requirements.txt` incompleto)
- Puerto incorrecto en la configuración

---

### Problema: "Cannot connect to the Docker daemon"

**Solución:**
```bash
# Verificar que Docker está corriendo
sudo systemctl status docker
sudo systemctl start docker

# Si usas Minikube con Docker driver
eval $(minikube docker-env)
```

---

## 2. Docker Compose (Week 9)

### Problema: Nginx no puede conectar con simple-app (`502 Bad Gateway`)

**Síntomas:** `curl http://localhost:8080/api` devuelve 502.

**Causa:** Nginx intenta conectar antes de que simple-app esté listo, o el nombre del servicio en `default.conf` no coincide.

**Diagnóstico:**
```bash
docker compose ps
docker compose logs nginx
docker compose logs simple-app

# Verificar resolución DNS dentro del contenedor
docker compose exec nginx ping simple-app
docker compose exec nginx wget -qO- http://simple-app:5000/health
```

**Solución:**
1. Verificar que `proxy_pass` en `default.conf` usa el nombre correcto:
   ```nginx
   proxy_pass http://simple-app:5000/;
   ```
2. Verificar que `depends_on` tiene `condition: service_healthy`
3. Verificar que simple-app tiene health check configurado

---

### Problema: Simple-app no conecta con Redis (`ConnectionError`)

**Síntomas:** El backend arranca pero devuelve error al intentar conectar con Redis.

**Diagnóstico:**
```bash
docker compose logs simple-app
docker compose exec simple-app env | grep REDIS
docker compose exec redis redis-cli ping
```

**Solución:**
1. Verificar las variables de entorno en `.env`:
   ```env
   REDIS_HOST=redis
   REDIS_PORT=6379
   ```
2. Verificar que Redis está healthy:
   ```bash
   docker compose ps redis
   ```
3. Verificar que ambos servicios están en la misma red:
   ```bash
   docker network inspect docker-compose_gsx-network
   ```

---

### Problema: Los datos de Redis se pierden al reiniciar

**Causa:** Se ejecutó `docker compose down -v` (que elimina volúmenes) en lugar de `docker compose down`.

**Solución:**
```bash
# Parar SIN eliminar volúmenes
docker compose down

# Verificar que el volumen existe
docker volume ls | grep redis

# Reiniciar
docker compose up -d
```

---

### Problema: Health check de simple-app falla repetidamente

**Diagnóstico:**
```bash
docker compose ps  # Ver estado "unhealthy"
docker compose logs simple-app
docker compose exec simple-app curl -s http://localhost:5000/health
```

**Causas comunes:**
- Redis no está disponible (simple-app depende de Redis para el health check)
- El endpoint `/health` no está implementado correctamente
- El intervalo del health check es demasiado corto para que Redis arranque

---

## 3. Kubernetes — Pods y Deployments (Week 10)

### Problema: Pod en estado `CrashLoopBackOff`

**Síntomas:** `kubectl get pods` muestra CrashLoopBackOff con múltiples reinicios.

**Diagnóstico:**
```bash
# Ver logs del pod actual
kubectl logs <pod-name>

# Ver logs del contenedor anterior (antes del crash)
kubectl logs <pod-name> --previous

# Describir el pod para ver eventos
kubectl describe pod <pod-name>

# Ver eventos del namespace
kubectl get events --sort-by=.lastTimestamp
```

**Causas comunes y soluciones:**

| Causa | Solución |
|---|---|
| Imagen no encontrada | Verificar `imagePullPolicy: Never` si usas imágenes locales en Minikube |
| Variables de entorno incorrectas | `kubectl describe pod <pod>` y verificar env |
| Dependencia no disponible | Verificar que Redis está Running antes que simple-app |
| OOM Kill (Out of Memory) | Aumentar `resources.limits.memory` |
| Comando de arranque incorrecto | Verificar CMD/ENTRYPOINT del Dockerfile |

---

### Problema: Pod en estado `ImagePullBackOff`

**Síntomas:** Kubernetes no puede descargar la imagen del contenedor.

**Diagnóstico:**
```bash
kubectl describe pod <pod-name> | grep -A 5 Events
```

**Solución para imágenes locales en Minikube:**
```bash
# Construir dentro del contexto Docker de Minikube
eval $(minikube docker-env)
docker build -t simple-app-gsx:latest ./simple-app

# En el manifiesto YAML, usar:
# imagePullPolicy: Never
```

---

### Problema: Pod en estado `Pending`

**Diagnóstico:**
```bash
kubectl describe pod <pod-name>
```

**Causas comunes:**
- **Insufficient CPU/memory:** Los resources requests exceden la capacidad del nodo
  ```bash
  kubectl describe node minikube | grep -A 10 "Allocated resources"
  ```
- **PVC no disponible:** El PersistentVolumeClaim no se puede satisfacer
  ```bash
  kubectl get pvc
  kubectl describe pvc redis-data
  ```

---

### Problema: Liveness/Readiness probe falla

**Diagnóstico:**
```bash
kubectl describe pod <pod-name> | grep -A 10 "Liveness\|Readiness"
kubectl logs <pod-name>
```

**Soluciones:**
- Aumentar `initialDelaySeconds` para dar tiempo al arranque
- Verificar que el endpoint de health existe y responde
- Verificar que el puerto es correcto en la probe

---

## 4. Kubernetes — Service Discovery (Week 10)

### Problema: Un pod no puede resolver el nombre DNS de otro servicio

**Síntomas:** `nslookup redis` falla desde dentro de un pod.

**Diagnóstico:**
```bash
# Verificar CoreDNS
kubectl -n kube-system get pods -l k8s-app=kube-dns

# Probar resolución DNS desde un pod
kubectl exec <pod-name> -- nslookup redis
kubectl exec <pod-name> -- nslookup simple-app

# Verificar que los Services existen
kubectl get svc
```

**Causas comunes:**
- CoreDNS no está running
- El Service no está creado
- NetworkPolicy bloquea el tráfico DNS (puerto 53)

**Solución para NetworkPolicy bloqueando DNS:**
```yaml
# 05-allow-dns.yml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

---

### Problema: Service existe pero no enruta tráfico

**Diagnóstico:**
```bash
# Verificar endpoints del Service
kubectl get endpoints <service-name>

# Si endpoints está vacío, los selectors no coinciden
kubectl describe svc <service-name>
kubectl get pods --show-labels
```

**Causa:** Los `selector` del Service no coinciden con los labels de los pods.

**Solución:** Asegurarse de que el Service tiene `selector: app: simple-app` y los pods tienen `labels: app: simple-app`.

---

## 5. Kubernetes — Persistent Volumes (Week 10)

### Problema: PVC en estado `Pending`

**Diagnóstico:**
```bash
kubectl get pvc
kubectl describe pvc redis-data
kubectl get storageclass
```

**Solución en Minikube:**
```bash
# Minikube proporciona un StorageClass por defecto
# Verificar que existe
kubectl get sc

# Si no hay SC, habilitar el addon
minikube addons enable default-storageclass
minikube addons enable storage-provisioner
```

---

### Problema: Datos de Redis se pierden al eliminar el pod

**Diagnóstico:**
```bash
# Verificar que el PVC está montado
kubectl describe pod <redis-pod> | grep -A 5 Volumes

# Verificar que Redis usa appendonly
kubectl exec <redis-pod> -- redis-cli CONFIG GET appendonly
```

**Causas comunes:**
- El PVC no está montado en `/data`
- Redis no arranca con `--appendonly yes`
- Se está usando Deployment en lugar de StatefulSet (los PVC no se re-asocian correctamente)

---

## 6. Kubernetes — NetworkPolicies (Week 12)

### Problema: Después de aplicar `default-deny`, nada funciona

**Síntomas:** Todos los pods están Running pero no pueden comunicarse entre sí.

**Causa:** `default-deny` bloquea TODO el tráfico. Hay que aplicar las excepciones.

**Solución:**
```bash
# Aplicar TODAS las policies, no solo default-deny
kubectl apply -f kubernetes/network-policies/

# Verificar el orden:
# 1. default-deny (bloquea todo)
# 2. frontend-to-backend (nginx → simple-app)
# 3. backend-to-redis (simple-app → redis)
# 4. allow-nginx-ingress (externo → nginx)
# 5. allow-dns (todos → CoreDNS)
```

---

### Problema: NetworkPolicies no tienen efecto (todo el tráfico pasa)

**Causa:** El CNI plugin no soporta NetworkPolicies (por ejemplo, el CNI por defecto de Minikube no las soporta).

**Solución:**
```bash
# Verificar qué CNI está instalado
kubectl -n kube-system get pods | grep calico

# Si Calico no está, reiniciar Minikube con Calico
minikube delete
minikube start --cni=calico
```

---

### Problema: DNS no funciona tras aplicar NetworkPolicies

**Síntomas:** Los pods no pueden resolver nombres de servicio.

**Causa:** La política `default-deny` bloquea el egress al puerto 53 de CoreDNS.

**Diagnóstico:**
```bash
kubectl exec <pod> -- nslookup kubernetes.default
# Si falla: "nslookup: can't resolve 'kubernetes.default'"
```

**Solución:** Aplicar `05-allow-dns.yml` que permite egress al puerto 53.

---

### Problema: El test de bloqueo (dev → prod) no funciona como se espera

**Diagnóstico:**
```bash
# Crear pod de prueba
kubectl run test-dev --image=busybox --labels=env=dev --restart=Never -- sleep 60

# Probar acceso (debería fallar con timeout)
kubectl exec test-dev -- wget -T 3 -qO- http://simple-app:5000/health

# Si tiene éxito → las NetworkPolicies no están aplicadas o Calico no está activo
kubectl get networkpolicies
kubectl -n kube-system get pods | grep calico

# Limpiar
kubectl delete pod test-dev --now
```

---

## 7. Terraform / IaC (Week 11)

### Problema: `terraform apply` falla con "provider not found"

**Solución:**
```bash
terraform init
# Si falla, verificar que el provider de Kubernetes está definido en main.tf
```

---

### Problema: Terraform quiere destruir y recrear recursos existentes

**Causa:** El estado de Terraform no está sincronizado con el clúster.

**Solución:**
```bash
# Importar recursos existentes
terraform import kubernetes_deployment.nginx default/nginx

# O refrescar el estado
terraform refresh
terraform plan  # Verificar antes de aplicar
```

---

## 8. Integración completa (Week 13)

### Problema: El script `verify_integration.py` falla en "Pods not ready"

**Diagnóstico:**
```bash
kubectl get pods
kubectl describe pods
kubectl get events --sort-by=.lastTimestamp
```

**Soluciones comunes:**
1. Aumentar el timeout: `--timeout 300`
2. Verificar que las imágenes están construidas en el contexto de Minikube
3. Verificar que Minikube tiene suficientes recursos

---

### Problema: El test de NetworkPolicy pasa pero no debería

**Causa:** Calico no está instalado o las policies no están aplicadas.

**Verificación:**
```bash
kubectl -n kube-system get pods | grep calico
kubectl get networkpolicies
# Ambos deben devolver resultados
```

---

## 9. Comandos de diagnóstico esenciales

### Diagrama de decisión para debugging

```
Pod no funciona
├── kubectl get pods → ¿Estado?
│   ├── Pending → kubectl describe pod → ¿Recursos? ¿PVC?
│   ├── CrashLoopBackOff → kubectl logs --previous → ¿Error de app?
│   ├── ImagePullBackOff → ¿Imagen existe? ¿imagePullPolicy?
│   └── Running pero no funciona
│       ├── kubectl logs → ¿Errores internos?
│       ├── kubectl exec -- curl → ¿Conectividad?
│       └── kubectl describe → ¿Probes fallando?
│
Servicio no accesible
├── kubectl get svc → ¿Existe?
│   ├── kubectl get endpoints → ¿Tiene endpoints?
│   │   └── No → Verificar selector vs labels de pods
│   └── Sí pero no funciona
│       ├── kubectl exec -- nslookup → ¿DNS funciona?
│       │   └── No → Verificar CoreDNS + allow-dns policy
│       └── Sí → Verificar NetworkPolicies
│           └── kubectl get netpol → ¿Tráfico permitido?
```

### Tabla de comandos clave

| Situación | Comando |
|---|---|
| Ver estado de pods | `kubectl get pods -o wide` |
| Ver por qué un pod falla | `kubectl describe pod <nombre>` |
| Ver logs actuales | `kubectl logs <pod>` |
| Ver logs del crash anterior | `kubectl logs <pod> --previous` |
| Ejecutar comando en pod | `kubectl exec -it <pod> -- /bin/sh` |
| Ver eventos recientes | `kubectl get events --sort-by=.lastTimestamp` |
| Verificar endpoints | `kubectl get endpoints <servicio>` |
| Probar DNS | `kubectl exec <pod> -- nslookup <servicio>` |
| Ver NetworkPolicies | `kubectl get netpol -o wide` |
| Verificar resources del nodo | `kubectl describe node minikube` |
| Ver PVCs | `kubectl get pvc` |
| Forzar recreación de pod | `kubectl delete pod <nombre>` |
