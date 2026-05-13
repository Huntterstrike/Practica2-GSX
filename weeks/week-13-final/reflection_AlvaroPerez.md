# Reflexión Personal — Práctica 2: Infraestructura IT Organizacional

**Autor:** Álvaro Pérez Caballer 
**Asignatura:** Gestió de Sistemes i Xarxes  
**Fecha:** Mayo 2026

---

## El momento en que de verdad entendí la complejidad del sistema

Si tengo que escoger un punto de inflexión en toda la práctica, me quedo con la transición entre las semanas 10, 11 y 12. Hasta ese momento, aunque cada bloque tenía su dificultad, yo aún pensaba en la infraestructura como una suma de piezas separadas: una imagen Docker, unos manifiestos de Kubernetes, unas variables, unas reglas de red. Lo que me hizo cambiar la perspectiva fue ver cómo un pequeño detalle mal resuelto en una capa afectaba a todo lo demás.

Un ejemplo muy claro fue el trabajo con Terraform en la semana 11. Sobre el papel, la idea era muy elegante: definir el stack una sola vez, parametrizarlo para `dev` y `staging`, y desplegarlo con `terraform apply`. Pero en la práctica aparecieron problemas que no eran evidentes al principio. El más molesto fue todo lo relacionado con las imágenes locales en Minikube. Yo podía tener `nginx-gsx:latest` y `simple-app-gsx:latest` construidas en mi máquina, pero eso no significaba que el clúster pudiera usarlas. Ver `ImagePullBackOff` cuando “la imagen sí existe” es una de esas situaciones que al principio desconciertan mucho, porque el error parece contradecir lo que tú mismo estás viendo.

Ahí entendí algo importante: en este tipo de entornos no basta con que una pieza exista, tiene que existir en el contexto correcto. La imagen no tenía que estar solo en Docker, sino también accesible desde el runtime de Minikube. Ese tipo de problemas me obligó a dejar de pensar en comandos sueltos y empezar a pensar en flujos completos de despliegue, validación y recuperación.

Otro momento que me marcó bastante fue la semana 12 con las `NetworkPolicy`. No tanto por escribir los YAML, sino por comprobar manualmente los caminos permitidos y los bloqueados. Ahí fue donde se vio con más claridad que una arquitectura segura no se basa solo en “que funcione”, sino en que funcione exactamente lo que debe funcionar y nada más. Ver que `nginx` podía llegar a `simple-app`, que `simple-app` podía llegar a `redis`, pero que no había comunicación cruzada entre entornos, me hizo entender de verdad el valor de modelar la red como una política declarativa.

## Lo que más me ha sorprendido del enfoque cloud-native

Lo que más me ha sorprendido no ha sido ninguna herramienta concreta, sino la manera de trabajar que aparece cuando todas encajan juntas.

En la semana 8, Docker me parecía sobre todo una forma cómoda de empaquetar una aplicación. En la 9, Compose me enseñó que varias piezas podían convivir de forma ordenada en una misma red y con dependencias claras. En la 10, Kubernetes añadió ideas que ya no eran solo de despliegue, sino de operación: probes, servicios internos, persistencia real, separación entre componentes stateless y stateful. En la 11, Terraform llevó eso un paso más allá, porque ya no se trataba de aplicar manifiestos, sino de gestionar el estado y la evolución del sistema de forma reproducible. Y en la 12, con Calico y las políticas de red, la seguridad dejó de ser una idea abstracta y pasó a formar parte del diseño técnico desde el principio.

Si tuviera que resumir qué me llevo de todo esto, diría que la infraestructura cloud-native me ha enseñado a pensar en términos de comportamiento esperado. No basta con “levantar contenedores”. Hay que poder responder preguntas como:

- qué componente puede hablar con cuál
- qué pasa si un pod desaparece
- cómo sé que el despliegue correcto está activo
- cómo verifico que la configuración aplicada es la que yo esperaba
- cómo recupero el sistema si cambio una imagen o una variable y algo sale mal

Me ha sorprendido también la importancia de la verificación automatizada. Scripts como los de las semanas 10, 11, 12 y 13 no son un extra bonito: son una forma de convertir supuestos en comprobaciones reales. Cuando un proyecto crece, la diferencia entre “creo que está bien” y “lo he validado” es enorme.

## Qué haría diferente si empezara otra vez

Si empezara desde cero, cambiaría varias cosas.

La primera sería dedicar más tiempo desde el inicio a unificar la experiencia de despliegue. En varias semanas el proyecto funciona, pero se nota la evolución natural de haber ido creciendo por fases: primero Docker, luego Compose, luego Kubernetes, después Terraform, después políticas de red y al final observabilidad. Eso es lógico en una práctica progresiva, pero si yo rediseñara el conjunto pensaría antes en una capa de automatización común que dejara más homogéneos los pasos manuales, los nombres y las verificaciones.

La segunda sería ser más estricto con los “preflight checks”. Muchas veces los errores no venían de una mala configuración profunda, sino de algo previo que no estaba listo: una imagen no cargada en Minikube, un workspace no seleccionado, una contraseña cambiada en Grafana, un namespace correcto pero un contexto incorrecto, o un plugin de red sin aplicar. Son fallos pequeños, pero consumen mucho tiempo porque rompen el flujo en momentos donde tú crees que ya deberías estar validando otra cosa. Tener más scripts de comprobación temprana habría reducido bastante la fricción.

La tercera sería dar más peso a la observabilidad antes, aunque en la práctica estuviera marcada como parte opcional o final. Añadir Prometheus y Grafana casi al final me hizo ver cuánto ayuda tener una visión operativa del sistema cuando ya llevas varias semanas depurando despliegues, networking y persistencia. No es lo mismo comprobar que algo responde que entender cómo se está comportando.

## Cómo ha cambiado mi forma de entender DevOps

Antes de esta práctica, DevOps me sonaba muchas veces a una palabra demasiado amplia, casi como una etiqueta para hablar de herramientas modernas. Después de estas semanas, lo veo de una forma mucho más concreta.

Para mí, DevOps ya no es “usar Docker” o “usar Kubernetes”. Es la idea de que desarrollo, despliegue, operación, seguridad y documentación no son fases separadas que se pasan unas a otras, sino partes del mismo sistema. Lo he visto en cosas muy concretas:

- una mala decisión en la imagen rompe el despliegue
- una mala sonda de salud afecta a la estabilidad
- una variable mal modelada en Terraform complica la promoción entre entornos
- una política de red demasiado estricta puede dejar el sistema aislado
- una falta de documentación convierte cualquier incidencia en una pérdida de tiempo

## Lo que más valoro de esta práctica

Lo que más valoro es que no se ha quedado en una colección de ejercicios aislados. Hay una continuidad real entre semanas, y eso obliga a arrastrar decisiones, errores y aprendizajes de una fase a la siguiente. Esa continuidad hace que el trabajo se parezca más a un proyecto de verdad que a una serie de prácticas independientes.

## Qué me gustaría seguir aprendiendo

Después de esta práctica, me gustaría profundizar sobre todo en tres líneas.

La primera es **observabilidad bien hecha**: no solo levantar Grafana, sino construir dashboards útiles, alertas razonables y una forma de interpretar métricas dentro de una operación real.

La segunda es **automatización de despliegues más madura**, por ejemplo con GitOps, para cerrar mejor el ciclo entre repositorio, validación, despliegue y estado real del clúster.

La tercera es **seguridad operativa en Kubernetes**. Las `NetworkPolicy` me han parecido una puerta de entrada muy interesante, pero está claro que solo son una parte de todo lo que implica securizar un entorno cloud-native.

En general, siento que esta práctica me ha dado algo más valioso que aprender comandos concretos: me ha dado una forma más estructurada de pensar sistemas distribuidos, reproducibles y operables.

---

*Álvaro Pérez Caballer · Mayo 2026*
