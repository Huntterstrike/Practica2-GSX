# Week 13 — Integration, Observability & Finalization

## Objetivo
Consolidar todo lo hecho en las semanas anteriores: desplegar desde cero usando IaC, comprobar la integración, añadir observabilidad (opcional) y preparar la documentación y el runbook para la entrega y la entrevista.

## Prioridad
1. Challenge B — Full Integration Test (REQUIRED)
2. Challenge C — Documentation (REQUIRED)
3. Challenge D — Reflection & Interview Prep (REQUIRED)
4. Challenge A — Observability (OPTIONAL, recomendado)

## Quick start
### Requisitos
- minikube (v1.x)
- kubectl
- python3 (para scripts de verificación)
- helm (opcional, para observability)

### Estructura recomendada
- `kubernetes/`           # manifests YAML (Weeks 10-12)
- `ansible/`              # (opcional) playbooks de despliegue
- `terraform/`            # (opcional) IaC ejemplo
- `manifests/observability/`  # Prometheus + Grafana (opcional)
- `scripts/`              # verify_integration.py
- `docs/`                 # diagramas y documentación

### Despliegue desde 0 (ejemplo)
1. Iniciar clúster limpio:
```bash
minikube delete
minikube start --network-plugin=cni --cni=calico
```
2. (Opcional) Cargar imágenes en Minikube:
```bash
minikube image load nginx-gsx:latest
minikube image load simple-app-gsx:latest
```
3. Desplegar (IaC recomendado):
- Ansible: `ansible-playbook ansible/deploy.yml`
- Terraform: `terraform init && terraform apply -auto-approve`
- (Solo pruebas) kubectl apply -f kubernetes/

4. Ejecutar verificación automática:
```bash
python3 scripts/verify_integration.py --apply-manifests --manifests kubernetes/ --timeout 240
```

## Qué entregar (evidencias)
- Log/output del script de verificación (`verify_integration.py`)
- `kubectl get pods,svc,networkpolicies -o wide` (captura o texto)
- `diagram.png` o `diagram.drawio`
- `RUNBOOK_week13.md` y `TROUBLESHOOTING.md`
- `reflection_<user>.md` (individual)
- (Opcional) Screenshot del dashboard Grafana

## Notas rápidas
- Prioriza un integration test reproducible y buena documentación antes que montar observability incompleto.
- Asegúrate de que `nginx` es el único servicio público (NodePort/Ingress) y que backend/redis son `ClusterIP` o accesibles solo mediante policies.
