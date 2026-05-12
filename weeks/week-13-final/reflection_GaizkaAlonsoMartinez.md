# Reflexión Personal — Práctica 2: Infraestructura IT Organizacional

**Autor:** Gaizka Alonso Martínez  
**Asignatura:** Gestió de Sistemes i Xarxes  
**Fecha:** Mayo 2026

---

## El mayor desafío técnico

Si tuviera que señalar un momento concreto donde me sentí verdaderamente atascado, sería durante la semana 12, cuando implementamos las NetworkPolicies con Calico. Teníamos todo el stack funcionando perfectamente en Kubernetes — nginx haciendo proxy a simple-app, simple-app conectando con Redis, el contador de visitas funcionando — y entonces aplicamos la política `default-deny`. De repente, todo se rompió. Los pods seguían en estado Running, pero ningún servicio podía comunicarse con ningún otro.

Lo frustrante no era que fallara, sino que el error no era obvio. No había pods en CrashLoopBackOff, no había errores en los logs. Simplemente, las peticiones se quedaban colgadas hasta timeout. Tardé bastante en entender que el problema era que habíamos bloqueado también el tráfico DNS al puerto 53 de CoreDNS. Sin DNS, `simple-app` no podía resolver el nombre `redis`, y `nginx` no podía resolver `simple-app`. La solución fue crear `05-allow-dns.yml`, que permite egress al puerto 53 para todos los pods. Parece sencillo ahora, pero llegar a ese diagnóstico me enseñó la importancia de entender cada capa del sistema.

El otro momento difícil fue durante la semana 10, cuando migramos de Docker Compose a Kubernetes. En Compose, todo funcionaba con un simple `docker compose up -d`. En Kubernetes, tuve que crear manifiestos YAML separados para Deployments, Services, PersistentVolumeClaims, y configurar `imagePullPolicy: Never` para que Minikube usara las imágenes locales en lugar de intentar descargarlas de Docker Hub. El primer `ImagePullBackOff` que vi fue confuso, porque la imagen existía localmente — solo que no en el contexto Docker de Minikube. El comando `eval $(minikube docker-env)` se convirtió en algo que ya nunca olvidaré.

## Lo que me sorprendió de la infraestructura cloud-native

Antes de esta práctica, mi idea de "desplegar una aplicación" era básicamente subir archivos a un servidor y rezar para que funcionara. Lo que más me ha sorprendido es la cantidad de capas que existen entre escribir `app.py` y que un usuario pueda acceder a la aplicación de forma fiable.

Me impresionó especialmente el concepto de **self-healing** en Kubernetes. Cuando eliminé un pod de Redis como prueba, el StatefulSet lo recreó automáticamente y el PersistentVolumeClaim se re-asoció, conservando todos los datos. Eso no pasa en Docker Compose — si un contenedor muere, `restart: unless-stopped` lo reinicia, pero no hay garantía de que el volumen se monte exactamente igual en todos los escenarios.

También me sorprendió lo poderosas que son las NetworkPolicies como concepto de seguridad. El hecho de que puedas definir a nivel declarativo que "solo nginx puede hablar con simple-app en el puerto 5000" es algo que en una infraestructura tradicional requeriría configurar firewalls, reglas de iptables, y probablemente varios días de trabajo. Aquí lo defines en un YAML de 15 líneas.

Otra cosa que no esperaba: lo mucho que importa la **documentación operativa**. Escribir el RUNBOOK y la guía de troubleshooting me hizo darme cuenta de que si no documentas cómo funciona tu sistema, es como si no existiera para cualquier otra persona (o para ti mismo en dos meses).

## Qué haría diferente

Si empezara de nuevo, haría dos cosas distintas:

**Primero**, usaría ConfigMaps y Secrets de Kubernetes desde el principio en lugar de inyectar variables de entorno directamente en los manifiestos YAML. En nuestro proyecto, `APP_MESSAGE`, `REDIS_HOST` y `REDIS_PORT` están hardcodeados en los Deployments. Funciona, pero no es la manera correcta de gestionar configuración en producción. Un ConfigMap centralizado haría más fácil cambiar la configuración sin tocar los manifiestos de los Deployments.

**Segundo**, implementaría Ingress en lugar de NodePort desde el principio. NodePort funciona en Minikube, pero es un patrón que no escala a producción. Con un Ingress Controller (como nginx-ingress), podríamos tener routing basado en host o path, TLS termination, y una configuración mucho más limpia para exponer servicios.

También me habría gustado dedicar más tiempo a la observabilidad (Challenge A con Prometheus y Grafana). Tener métricas visibles en un dashboard cambia completamente la manera en que entiendes y operas un sistema.

## Cómo ha evolucionado mi visión del DevOps

Al principio de la semana 8, veía Docker como una herramienta para "empaquetar aplicaciones". Ahora entiendo que la containerización es solo el primer eslabón de una cadena mucho más larga: Docker para empaquetar → Compose para orquestar localmente → Kubernetes para orquestar en producción → Terraform para automatizar la infraestructura → NetworkPolicies para asegurar → documentación para operar.

Lo que más ha cambiado es mi comprensión de por qué existe cada herramienta. Antes de esta práctica, Kubernetes me parecía innecesariamente complejo comparado con Docker Compose. Ahora entiendo que Compose es perfecto para desarrollo local, pero para producción necesitas las garantías que ofrece Kubernetes: rolling updates, self-healing, resource limits reales, service discovery robusto, y control de acceso a nivel de red.

La infraestructura cloud-native no es solo una colección de herramientas — es una filosofía de trabajo donde todo es declarativo, versionable, reproducible y observable. Eso es lo que me llevo de estas seis semanas.

## Qué quiero aprender más

Me gustaría profundizar en tres áreas: **Helm charts** para gestionar manifiestos complejos de Kubernetes de forma más mantenible, **GitOps con ArgoCD** para cerrar el ciclo de CI/CD de verdad, y **observabilidad avanzada** con Prometheus, Grafana y distributed tracing. Creo que esas tres piezas completarían la visión que hemos empezado a construir en esta práctica.

---

*Gaizka Alonso Martínez · Mayo 2026*
