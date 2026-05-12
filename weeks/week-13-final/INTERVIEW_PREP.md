# Preparación para la Entrevista Oral — Week 13

> Guía de estudio para defender el proyecto GreenDevCorp  
> Autor: Gaizka Alonso Martínez  
> Entrevista: Semana 14-15 (18–29 Mayo 2026)

## Índice

- [Explicación de la arquitectura](#1-explicación-de-la-arquitectura)
- [Defensa de decisiones técnicas](#2-defensa-de-decisiones-técnicas)
- [Escenarios de troubleshooting](#3-escenarios-de-troubleshooting)
- [Preguntas frecuentes del profesor](#4-preguntas-frecuentes-del-profesor)
- [Conceptos clave que dominar](#5-conceptos-clave-que-dominar)
- [Guion para la demostración en vivo](#6-guion-para-la-demostración-en-vivo)

---

## 1. Explicación de la arquitectura

### Discurso preparado (2 minutos)

> "Nuestro sistema implementa una aplicación web de tres capas desplegada en Kubernetes con Minikube. El flujo de tráfico es el siguiente:
>
> Un cliente externo envía una petición HTTP a la IP del nodo de Minikube en el puerto NodePort. Esta petición llega al **Service de nginx**, que la enruta al **pod de nginx**. Nginx actúa como reverse proxy: sirve contenido estático directamente y redirige las peticiones a `/api` hacia el backend.
>
> El backend es **simple-app**, una aplicación Python/Flask que expone un endpoint principal y un endpoint de health. Cuando recibe una petición, conecta con **Redis** para incrementar y leer un contador de visitas. Redis está desplegado como **StatefulSet** con un PersistentVolumeClaim, lo que garantiza que los datos sobreviven a reinicios de pods.
>
> La seguridad de red se gestiona con **NetworkPolicies** usando Calico como CNI. Implementamos un modelo deny-all por defecto y luego abrimos solo los flujos necesarios: externo→nginx, nginx→simple-app, simple-app→redis, y todos los pods pueden resolver DNS.
>
> La infraestructura se puede desplegar automáticamente con **Terraform**, que define todos los recursos de Kubernetes de forma declarativa."

### Diagrama para dibujar en la pizarra

```
Cliente → [NodePort 30080] → Nginx(:80) → [proxy_pass] → Simple-App(:5000) → Redis(:6379) → PVC
                                                              ↑ /health
                                                              ↑ env vars: REDIS_HOST, REDIS_PORT
```

**Puntos clave a señalar:**
- Solo nginx está expuesto al exterior (NodePort)
- Simple-app y Redis son ClusterIP (internos)
- Toda la comunicación usa nombres DNS (no IPs)
- Redis tiene almacenamiento persistente (PVC)

---

## 2. Defensa de decisiones técnicas

### "¿Por qué Kubernetes y no solo Docker Compose?"

> "Docker Compose es excelente para desarrollo local — con un solo comando levantamos los tres servicios. Pero para un entorno de producción real, Compose tiene limitaciones importantes:
>
> - **No tiene self-healing real.** Si un contenedor muere, `restart: unless-stopped` lo reinicia, pero no verifica que esté funcionando correctamente.
> - **No tiene rolling updates.** Para actualizar una versión hay que parar y recrear contenedores, lo que genera downtime.
> - **No tiene scheduling.** No puede distribuir cargas entre múltiples nodos.
> - **Las NetworkPolicies no existen en Compose.** No hay manera nativa de aislar tráfico entre servicios.
>
> Kubernetes resuelve todo esto: liveness/readiness probes, rolling updates, ReplicaSets, y NetworkPolicies con Calico."

### "¿Por qué StatefulSet para Redis y no Deployment?"

> "Redis es un servicio con estado (stateful). Necesita que su volumen persistente se re-asocie al mismo pod cada vez que se reinicia. Un Deployment no garantiza esto — puede crear un pod nuevo con un PVC nuevo, perdiendo los datos.
>
> StatefulSet garantiza:
> - **Identidad de red estable:** el pod siempre se llama `redis-0`
> - **PVC estable:** el claim `redis-data` se re-asocia al pod con el mismo ordinal
> - **Orden de arranque controlado:** importante si hubiera réplicas
>
> Para nginx y simple-app usamos Deployments porque son stateless — no tienen datos persistentes propios, se pueden crear y destruir libremente."

### "¿Por qué Calico y no el CNI por defecto de Minikube?"

> "El CNI por defecto de Minikube (kindnet o bridge) no soporta NetworkPolicies. Podemos crear objetos NetworkPolicy, pero no tienen ningún efecto — todo el tráfico pasa igualmente.
>
> Calico es un CNI que sí implementa NetworkPolicies a nivel de kernel con iptables/eBPF. Es ampliamente usado en producción (GKE, EKS, AKS lo soportan). Lo elegimos porque necesitábamos demostrar aislamiento de red real."

### "¿Por qué NodePort y no Ingress?"

> "NodePort es suficiente para nuestro entorno de Minikube con un solo servicio expuesto. Ingress tendría más sentido si tuviéramos múltiples dominios o paths complejos.
>
> En un entorno de producción real, usaría un Ingress Controller (como nginx-ingress o Traefik) porque ofrece:
> - Routing basado en host/path
> - TLS termination con cert-manager
> - Rate limiting y seguridad adicional
> - Un solo punto de entrada para todos los servicios"

### "¿Por qué variables de entorno y no ConfigMaps/Secrets?"

> "Para la simplicidad del proyecto, inyectamos las variables directamente en los manifiestos YAML. En producción usaría:
> - **ConfigMap** para `APP_MESSAGE`, `REDIS_HOST`, `REDIS_PORT` (configuración no sensible)
> - **Secret** para credenciales (passwords de Redis, API keys)
>
> Los ConfigMaps y Secrets permiten cambiar configuración sin modificar ni reconstruir los Deployments."

---

## 3. Escenarios de troubleshooting

### Escenario 1: "Un contenedor está crasheando. ¿Cómo lo diagnosticas?"

**Respuesta estructurada:**

```
Paso 1: Identificar el pod problemático
$ kubectl get pods
→ Buscar pods en CrashLoopBackOff o Error

Paso 2: Ver los logs
$ kubectl logs <pod-name>
$ kubectl logs <pod-name> --previous  ← logs del crash anterior

Paso 3: Describir el pod para ver eventos
$ kubectl describe pod <pod-name>
→ Buscar en la sección Events: OOM Kill, ImagePullBackOff, Probe failures

Paso 4: Verificar las dependencias
$ kubectl get pods  ← ¿Redis está Running?
$ kubectl exec <pod> -- nslookup redis  ← ¿DNS funciona?

Paso 5: Si es necesario, entrar al contenedor
$ kubectl exec -it <pod> -- /bin/sh
→ Verificar variables de entorno, conectividad, filesystem
```

### Escenario 2: "El servicio X no puede alcanzar el servicio Y. ¿Cómo lo depuras?"

**Respuesta:**

```
Paso 1: Verificar que ambos pods están Running
$ kubectl get pods -l app=nginx
$ kubectl get pods -l app=simple-app

Paso 2: Verificar que el Service tiene endpoints
$ kubectl get endpoints simple-app
→ Si está vacío: los labels del pod no coinciden con el selector del Service

Paso 3: Probar DNS
$ kubectl exec <nginx-pod> -- nslookup simple-app
→ Si falla: problema de DNS (CoreDNS o NetworkPolicy bloqueando puerto 53)

Paso 4: Probar conectividad directa
$ kubectl exec <nginx-pod> -- curl -s http://simple-app:5000/health
→ Si timeout: NetworkPolicy bloqueando el tráfico

Paso 5: Revisar NetworkPolicies
$ kubectl get networkpolicies
$ kubectl describe networkpolicy frontend-to-backend
→ Verificar que el selector y los puertos son correctos
```

### Escenario 3: "Dashboard muestra alta tasa de errores. ¿Qué verificas?"

**Respuesta:**

```
1. Verificar estado de los pods: kubectl get pods
2. Revisar logs de simple-app: kubectl logs -f deploy/simple-app
3. Verificar conexión a Redis: kubectl exec <app-pod> -- redis-cli -h redis ping
4. Comprobar resource limits: kubectl top pods (si metrics-server está instalado)
5. Revisar eventos recientes: kubectl get events --sort-by=.lastTimestamp
6. Si hay OOM kills: aumentar memory limits en el Deployment
7. Si Redis está saturado: verificar persistencia y número de conexiones
```

### Escenario 4: "¿Cómo manejaría este sistema 10x más tráfico?"

**Respuesta:**

> "Para escalar 10x haría varios cambios:
>
> 1. **Escalar nginx horizontalmente:** `kubectl scale deploy/nginx --replicas=3`
> 2. **Escalar simple-app:** `kubectl scale deploy/simple-app --replicas=5`
> 3. **HorizontalPodAutoscaler** para escalar automáticamente según CPU/memoria
> 4. **Redis Cluster o Sentinel** para escalar la base de datos (no simple replicación)
> 5. **Ingress Controller** con load balancing más sofisticado
> 6. **Resource limits** ajustados según el tráfico real (basado en métricas)
> 7. **Multi-nodo:** Pasar de Minikube a un clúster con varios nodos workers
> 8. **Observabilidad:** Prometheus + Grafana para monitorizar y alertar antes de que haya problemas"

---

## 4. Preguntas frecuentes del profesor

### Sobre Docker (Week 8)

**P: ¿Qué diferencia hay entre CMD y ENTRYPOINT?**
> ENTRYPOINT define el ejecutable principal del contenedor (difícil de sobreescribir). CMD define los argumentos por defecto (fácil de sobreescribir con `docker run <image> <args>`). En nuestro caso, nginx usa ENTRYPOINT para el daemon, y simple-app usa CMD para `python app.py`.

**P: ¿Por qué usar alpine como imagen base?**
> Las imágenes alpine son mucho más pequeñas (~5MB vs ~100MB para Debian). Esto significa builds más rápidos, menos superficie de ataque, y menos almacenamiento. Para nuestro proyecto es suficiente.

**P: ¿Qué es un multi-stage build y por qué lo usarías?**
> Un multi-stage build usa varias instrucciones FROM en un Dockerfile. La primera etapa compila/instala dependencias, la segunda copia solo los artefactos necesarios. Reduce el tamaño de la imagen final porque no incluye herramientas de compilación.

### Sobre Compose (Week 9)

**P: ¿Qué pasa si haces `docker compose down -v`?**
> Elimina los contenedores Y los volúmenes nombrados. En nuestro caso, `redis-data` se destruye y el contador de visitas se pierde. Sin `-v`, los volúmenes persisten.

**P: ¿Cómo funciona el service discovery en Compose?**
> Docker Compose crea una red bridge personalizada (`gsx-network` en nuestro caso). Dentro de esa red, cada servicio es accesible por su nombre. `simple-app` puede conectar a `redis:6379` porque Docker embeds un DNS server que resuelve `redis` a la IP del contenedor.

### Sobre Kubernetes (Weeks 10-13)

**P: ¿Qué es un Service y por qué es necesario?**
> Un Service proporciona un endpoint estable (ClusterIP o NodePort) para acceder a un conjunto de pods. Los pods son efímeros — pueden morir y recrearse con IPs diferentes. El Service mantiene una IP fija y usa selectors para enrutar tráfico a los pods correctos.

**P: ¿Cuál es la diferencia entre ClusterIP y NodePort?**
> ClusterIP solo es accesible dentro del clúster (para comunicación interna entre servicios). NodePort expone un puerto en la IP del nodo, accesible desde fuera del clúster. En nuestro proyecto, redis y simple-app son ClusterIP, y nginx es NodePort.

**P: ¿Qué pasa si un pod muere en Kubernetes?**
> Si el pod está gestionado por un Deployment o StatefulSet, el controller detecta que el número de réplicas es menor al deseado y crea un nuevo pod automáticamente. Si es un StatefulSet, el nuevo pod recupera el mismo PVC con los datos intactos.

**P: ¿Para qué sirven las liveness y readiness probes?**
> **Liveness probe:** verifica que el contenedor está vivo. Si falla, Kubernetes mata el contenedor y lo reinicia. Útil para detectar deadlocks.
> **Readiness probe:** verifica que el contenedor está listo para recibir tráfico. Si falla, el Service deja de enviar tráfico a ese pod. Útil durante el arranque o cuando una dependencia no está disponible.

---

## 5. Conceptos clave que dominar

### Vocabulario esencial

| Concepto | Definición breve |
|---|---|
| **Pod** | Unidad mínima de despliegue en K8s. Uno o más contenedores. |
| **Deployment** | Controller que gestiona ReplicaSets de pods stateless. |
| **StatefulSet** | Controller para pods stateful con identidad y storage estable. |
| **Service** | Endpoint estable para acceder a pods por selector. |
| **ClusterIP** | Service solo accesible dentro del clúster. |
| **NodePort** | Service accesible desde fuera del clúster por IP:puerto del nodo. |
| **PVC** | PersistentVolumeClaim: solicitud de almacenamiento persistente. |
| **NetworkPolicy** | Regla de firewall a nivel de pod (requiere CNI compatible). |
| **CNI** | Container Network Interface: plugin de red del clúster. |
| **Calico** | CNI que soporta NetworkPolicies. |
| **Ingress** | Reglas de routing HTTP/HTTPS para exponer servicios. |
| **ConfigMap** | Almacena configuración no sensible como pares clave-valor. |
| **Secret** | Almacena datos sensibles (passwords, tokens) codificados en base64. |
| **Namespace** | Agrupación lógica de recursos dentro del clúster. |
| **Rolling Update** | Estrategia de actualización que reemplaza pods gradualmente. |
| **IaC** | Infrastructure as Code: definir infraestructura en ficheros versionables. |
| **Terraform** | Herramienta de IaC declarativa que gestiona infraestructura. |

### Flujos que saber dibujar

1. **Flujo de petición HTTP:** Cliente → NodePort → nginx Pod → proxy_pass → simple-app Service → simple-app Pod → Redis Service → Redis Pod → PVC
2. **Flujo de despliegue:** `kubectl apply` → API Server → Controller Manager → Scheduler → Kubelet → Container Runtime → Pod Running
3. **Flujo de self-healing:** Pod muere → Controller detecta réplicas < deseado → Crea nuevo pod → Scheduler asigna nodo → Pod Running

---

## 6. Guion para la demostración en vivo

### Minuto 0-2: Arranque

```bash
# Mostrar que no hay nada corriendo
kubectl get pods
kubectl get svc

# Desplegar todo
kubectl apply -f kubernetes/
kubectl get pods -w  # Mostrar cómo arrancan
```

### Minuto 2-4: Verificación funcional

```bash
# Acceso externo
NGINX_URL=$(minikube service nginx --url)
curl $NGINX_URL/api
# Mostrar: "Hello from K8s | Visits: 1"

# Repetir para incrementar contador
curl $NGINX_URL/api
curl $NGINX_URL/api
```

### Minuto 4-5: Persistencia

```bash
# Verificar contador en Redis
REDIS_POD=$(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec $REDIS_POD -- redis-cli get visits

# Matar el pod de Redis
kubectl delete pod $REDIS_POD

# Esperar recreación
kubectl get pods -w

# Verificar que datos persisten
kubectl exec $(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli get visits
```

### Minuto 5-7: NetworkPolicies

```bash
# Mostrar policies activas
kubectl get networkpolicies

# Test: pod no autorizado intenta acceder
kubectl run test-intruder --image=busybox --labels=env=dev --restart=Never -- sleep 30
kubectl exec test-intruder -- wget -T 3 -qO- http://simple-app:5000/health
# Resultado: timeout (bloqueado por NetworkPolicy)

kubectl delete pod test-intruder --now
```

### Minuto 7-8: Escalado (si hay tiempo)

```bash
kubectl scale deploy/nginx --replicas=3
kubectl get pods -l app=nginx
# Mostrar 3 réplicas Running
kubectl scale deploy/nginx --replicas=1
```

---

*Documento preparado por Gaizka Alonso Martínez · Mayo 2026*
