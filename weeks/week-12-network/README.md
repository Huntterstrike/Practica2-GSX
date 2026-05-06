# Week 12: Network Design & Identity

## Objetivo
Implementar segmentación de red en Kubernetes usando NetworkPolicies aplicadas
por el CNI Calico, siguiendo un modelo Zero Trust.

## Arquitectura

```
Internet
   │
   ▼
[Nginx] (env: prod, app: nginx)
   │  ← solo nginx recibe tráfico externo
   ▼
[Simple App] (env: prod, app: simple-app)
   │  ← solo simple-app puede hablar con redis
   ▼
[Redis] (env: prod, app: redis)
```

## Requisito previo: Calico CNI

Las NetworkPolicies solo funcionan si el clúster usa un CNI compatible.
Arrancar Minikube con Calico:

```bash
minikube delete
minikube start --network-plugin=cni --cni=calico
```

Verificar que Calico está activo:

```bash
kubectl get pods -n kube-system | grep calico
```

## Despliegue

```bash
# Aplicar primero los recursos de Week 10
kubectl apply -f ../week-10-k8s/kubernetes/

# Aplicar las políticas de red
kubectl apply -f kubernetes/
```

## Verificación

```bash
chmod +x verify_week12.sh
./verify_week12.sh
```

## Archivos

| Archivo | Descripción |
|---|---|
| `00-default-deny.yml` | Bloquea todo el tráfico por defecto |
| `01-env-isolation.yml` | Solo pods del mismo entorno se comunican |
| `02-frontend-to-backend.yml` | Nginx → Simple App (puerto 5000) |
| `03-backend-to-redis.yml` | Simple App → Redis (puerto 6379) |
| `04-allow-nginx-ingress.yml` | Permite tráfico externo a Nginx |
| `05-allow-dns.yml` | Permite resolución DNS (CoreDNS) |

## Conceptos clave

**Calico** actúa como motor CNI que lee las NetworkPolicies y configura
reglas de firewall a nivel de kernel en cada nodo del clúster.

**Zero Trust:** por defecto todo está bloqueado (`00-default-deny.yml`).
Solo se abre lo estrictamente necesario.

**Labels:** son la base del sistema. Sin `env: prod` y `app: X` en los pods,
las políticas no tienen efecto.
