# Sistema Escalable de Adquisicion de Entradas

Implementacion de la practica de sistemas distribuidos con dos arquitecturas:

- **Directa**: cliente -> NGINX -> API REST -> Redis
- **Indirecta**: cliente -> gateway -> RabbitMQ -> workers -> Redis

El sistema soporta entradas no numeradas y numeradas, mantiene idempotencia por
`request_id` y compara rendimiento, contencion y escalabilidad bajo carga.

## Estructura util del repositorio

- `src/concert_ticketing/`: codigo de aplicacion, adaptadores y puntos de entrada
- `scripts/`: arranque, parada, benchmarks, reseteo y generacion de reportes
- `tools/local_dev/`: Docker Compose y `seed_state.py` para Redis y RabbitMQ
- `deploy/nginx/`: configuracion del balanceador REST
- `deploy/rabbitmq/`: artefactos auxiliares de RabbitMQ
- `benchmarks/input/`: benchmarks base entregados
- `benchmarks/generated/`: generacion del benchmark hotspot
- `benchmarks/outputs/`: resultados finales, graficos y reportes
- `docs/`: troubleshooting puntual

## Resultados finales

Los artefactos canonicos de la entrega estan en:

- `benchmarks/outputs/direct/`
- `benchmarks/outputs/indirect/`
- `benchmarks/outputs/scalability/latest/`
- `benchmarks/outputs/contention/latest/normal/`
- `benchmarks/outputs/contention/latest/hotspot/`
- `benchmarks/outputs/dynamic_scaling/latest/`
- `benchmarks/outputs/plots/`
- `benchmarks/outputs/reports/`

El reporte final generado queda en:

- `benchmarks/outputs/reports/benchmark_report.html`
- `benchmarks/outputs/reports/benchmark_report.md`
- `benchmarks/outputs/reports/summary_table.json`

## Ejecucion rapida

Desde la raiz del proyecto:

```bash
bash scripts/start_all.sh
bash scripts/verify_system.sh
bash scripts/stop_all.sh
```

Para regenerar el reporte a partir de los resultados de `benchmarks/outputs/`:

```bash
bash scripts/generate_report.sh benchmarks/outputs
```

## Reproduccion de la entrega

Todos los comandos de esta seccion deben ejecutarse desde la raiz del proyecto.
En Windows, usa **Git Bash** para todos los scripts `.sh`.

### A. Reproduccion local de `benchmarks/outputs`

Esta es la via canonica para regenerar el arbol de resultados que forma parte
de la entrega actual.

#### 1. Preparar el entorno

Windows Git Bash:

```bash
python3 -m venv .venv
source .venv/Scripts/activate
pip install -e .
```

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### 2. Verificar `NGINX` para la arquitectura directa

Antes de lanzar pruebas directas, `deploy/nginx/upstream.conf` debe apuntar a
las dos APIs locales:

```nginx
upstream direct_backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=10s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=10s;
}
```

#### 3. Limpiar resultados anteriores

```bash
bash scripts/stop_all.sh
rm -rf benchmarks/outputs/direct \
       benchmarks/outputs/indirect \
       benchmarks/outputs/scalability/latest \
       benchmarks/outputs/contention/latest \
       benchmarks/outputs/dynamic_scaling/latest \
       benchmarks/outputs/plots \
       benchmarks/outputs/reports
```

#### 4. Test directo local

El test directo genera los ficheros canonicos en `benchmarks/outputs/direct/`
y siempre debe ejecutarse a traves de `NGINX`, es decir, usando
`http://localhost` como punto unico de entrada.

Paso 1. Levantar el sistema completo con la configuracion base:

```bash
WORKER_COUNT=3 bash scripts/start_all.sh
```

Paso 2. Ejecutar el benchmark directo de entradas no numeradas:

```bash
BASE_URL=http://localhost \
CONCURRENCY=50 \
TIMEOUT=60 \
OUTPUT_DIR=benchmarks/outputs/direct \
bash scripts/run_direct_benchmark.sh benchmarks/input/benchmark_unnumbered_20000.txt
```

Paso 3. Resetear el estado antes del benchmark numerado:

```bash
bash scripts/init_state.sh
```

Paso 4. Ejecutar el benchmark directo de entradas numeradas:

```bash
BASE_URL=http://localhost \
CONCURRENCY=50 \
TIMEOUT=60 \
OUTPUT_DIR=benchmarks/outputs/direct \
bash scripts/run_direct_benchmark.sh benchmarks/input/benchmark_numbered_60000.txt
```

Paso 5. Verificar la correctitud del bloque directo:

```bash
bash scripts/verify_correctness.sh benchmarks/outputs/direct
```

#### 5. Test indirecto local

El test indirecto genera los ficheros canonicos en
`benchmarks/outputs/indirect/` y usa siempre `http://localhost:8080`.

Paso 1. Parar el sistema anterior y volver a levantarlo:

```bash
bash scripts/stop_all.sh
WORKER_COUNT=3 bash scripts/start_all.sh
```

Paso 2. Ejecutar el benchmark indirecto de entradas no numeradas:

```bash
BASE_URL=http://localhost:8080 \
CONCURRENCY=50 \
TIMEOUT=60 \
OUTPUT_DIR=benchmarks/outputs/indirect \
bash scripts/run_indirect_benchmark.sh benchmarks/input/benchmark_unnumbered_20000.txt
```

Paso 3. Resetear el estado antes del benchmark numerado:

```bash
bash scripts/init_state.sh
```

Paso 4. Ejecutar el benchmark indirecto de entradas numeradas:

```bash
BASE_URL=http://localhost:8080 \
CONCURRENCY=50 \
TIMEOUT=60 \
OUTPUT_DIR=benchmarks/outputs/indirect \
bash scripts/run_indirect_benchmark.sh benchmarks/input/benchmark_numbered_60000.txt
```

Paso 5. Verificar la correctitud del bloque indirecto:

```bash
bash scripts/verify_correctness.sh benchmarks/outputs/indirect
```

#### 6. Test de escalabilidad local

Este test genera `benchmarks/outputs/scalability/latest/` con los escenarios
`workers_1`, `workers_2`, `workers_4` y `workers_8`, comparando arquitectura
directa e indirecta sobre `benchmark_unnumbered_20000.txt`.

Paso 1. Parar cualquier ejecucion anterior:

```bash
bash scripts/stop_all.sh
```

Paso 2. Ejecutar el script completo de escalabilidad:

```bash
BENCHMARK_CONCURRENCY=50 \
BENCHMARK_TIMEOUT=60 \
WORKERS_LIST="1 2 4 8" \
bash scripts/run_scalability_test.sh
```

Paso 3. Verificar que exista la salida esperada:

```bash
bash scripts/verify_correctness.sh benchmarks/outputs/scalability/latest
```

#### 7. Test de hotspot / contencion local

Este test genera:

- `benchmarks/outputs/contention/latest/normal/direct/`
- `benchmarks/outputs/contention/latest/normal/indirect/`
- `benchmarks/outputs/contention/latest/hotspot/direct/`
- `benchmarks/outputs/contention/latest/hotspot/indirect/`

Paso 1. Parar cualquier ejecucion anterior:

```bash
bash scripts/stop_all.sh
```

Paso 2. Ejecutar el test completo de contencion:

```bash
BENCHMARK_CONCURRENCY=50 \
BENCHMARK_TIMEOUT=60 \
WORKER_COUNT=3 \
bash scripts/run_contention_test.sh
```

Paso 3. Verificar la correctitud del bloque de contencion:

```bash
bash scripts/verify_correctness.sh benchmarks/outputs/contention/latest
```

#### 8. Test de dynamic scaling local

Paso 1. Parar cualquier ejecucion anterior:

```bash
bash scripts/stop_all.sh
```

Paso 2. Ejecutar el escenario:

```bash
INITIAL_WORKERS=2 \
TARGET_WORKERS=4 \
SCALE_AFTER_SECONDS=20 \
BENCHMARK_CONCURRENCY=50 \
BENCHMARK_TIMEOUT=60 \
bash scripts/run_dynamic_scaling_test.sh
```

#### 9. Generar graficos y reporte final

```bash
bash scripts/generate_report.sh benchmarks/outputs
bash scripts/verify_correctness.sh benchmarks/outputs
bash scripts/stop_all.sh
```

Ese flujo vuelve a dejar rellenados los directorios canonicos:

- `benchmarks/outputs/direct/`
- `benchmarks/outputs/indirect/`
- `benchmarks/outputs/scalability/latest/`
- `benchmarks/outputs/contention/latest/normal/`
- `benchmarks/outputs/contention/latest/hotspot/`
- `benchmarks/outputs/dynamic_scaling/latest/`
- `benchmarks/outputs/plots/`
- `benchmarks/outputs/reports/`

### B. Validacion distribuida en LAN

Esta seccion describe el proceso real seguido en la validacion distribuida, sin
usar scripts como flujo principal. Los resultados se guardan siempre en
`PC-A`, dentro de `benchmarks/outputs/`.

Topologia usada:

- `PC-A`: Redis, RabbitMQ, NGINX, gateway indirecto, una API directa local y el lanzador de benchmarks
- `PC-B`: una API directa remota y los workers remotos

Parametros usados en las pruebas LAN:

- concurrencia del benchmark: `10`
- timeout por peticion: `180`

#### 1. Preparacion inicial

En `PC-A` y `PC-B`.

Windows Git Bash:

```bash
python3 -m venv .venv
source .venv/Scripts/activate
pip install -e .
```

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

En `PC-A`, configurar `deploy/nginx/upstream.conf` para balancear entre la API
local y la API remota de `PC-B`:

```nginx
upstream direct_backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=10s;
    server <IP_PC_B>:8000 max_fails=3 fail_timeout=10s;
}
```

#### 2. Arranque manual de `PC-A`

Terminal `PC-A infra`:

```bash
cd <ruta-del-repo>
source .venv/Scripts/activate  # en Linux: .venv/bin/activate
docker compose -f tools/local_dev/docker-compose.yml down
docker compose -f tools/local_dev/docker-compose.yml up -d
python3 tools/local_dev/seed_state.py
docker exec concert-ticketing-rabbitmq rabbitmqctl add_user lanuser lanpass 2>/dev/null || true
docker exec concert-ticketing-rabbitmq rabbitmqctl set_permissions -p / lanuser ".*" ".*" ".*"
docker exec concert-ticketing-rabbitmq rabbitmqctl set_user_tags lanuser administrator
```

Terminal `PC-A api-local`:

```bash
cd <ruta-del-repo>
source .venv/Scripts/activate  # en Linux: .venv/bin/activate
python3 -m concert_ticketing.apps.direct_api.main --port 8000
```

Terminal `PC-A gateway`:

```bash
cd <ruta-del-repo>
source .venv/Scripts/activate  # en Linux: .venv/bin/activate
python3 -m concert_ticketing.apps.indirect_gateway.main
```

Terminal `PC-A nginx`:

```bash
cd <ruta-del-repo>
nginx -s stop 2>/dev/null || true
nginx -c "$PWD/deploy/nginx/nginx.conf" -p "$PWD/deploy/nginx/"
```

Comprobaciones en `PC-A`:

```bash
curl http://localhost/health
curl http://localhost:8080/health
```

#### 3. Arranque manual de `PC-B`

Terminal `PC-B api-remota`:

```bash
cd <ruta-del-repo>
source .venv/bin/activate
export REDIS_HOST=<IP_PC_A>
export RABBITMQ_HOST=<IP_PC_A>
export RABBITMQ_USER=lanuser
export RABBITMQ_PASSWORD=lanpass
python3 -m concert_ticketing.apps.direct_api.main --port 8000
```

Desde `PC-A`, comprobar que la API remota responde:

```bash
curl http://<IP_PC_B>:8000/health
```

Plantilla de terminal worker en `PC-B`:

```bash
cd <ruta-del-repo>
source .venv/bin/activate
export REDIS_HOST=<IP_PC_A>
export RABBITMQ_HOST=<IP_PC_A>
export RABBITMQ_USER=lanuser
export RABBITMQ_PASSWORD=lanpass
python3 -m concert_ticketing.apps.worker.main
```

Durante las pruebas no usamos `scale_workers_up.sh` ni `scale_workers_down.sh`.
Lo que hicimos fue abrir o cerrar manualmente terminales `worker` en `PC-B`.

#### 4. Test directo en LAN

Para la arquitectura directa no hacen falta workers. Basta con que sigan vivos:

- `PC-A api-local`
- `PC-B api-remota`
- `PC-A nginx`

Paso 1. Resetear el estado en `PC-A`:

```bash
cd <ruta-del-repo>
source .venv/Scripts/activate  # en Linux: .venv/bin/activate
python3 tools/local_dev/seed_state.py
```

Paso 2. Ejecutar el benchmark directo no numerado en `PC-A`:

```bash
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/direct
```

Paso 3. Resetear de nuevo el estado en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
```

Paso 4. Ejecutar el benchmark directo numerado en `PC-A`:

```bash
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_numbered_60000.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/direct
```

Los ficheros generados quedan en:

- `benchmarks/outputs/direct/benchmark_unnumbered_20000_summary.json`
- `benchmarks/outputs/direct/benchmark_unnumbered_20000_results.jsonl`
- `benchmarks/outputs/direct/benchmark_numbered_60000_summary.json`
- `benchmarks/outputs/direct/benchmark_numbered_60000_results.jsonl`

#### 5. Test indirecto en LAN

Para esta parte dejamos abiertos en `PC-B` tres terminales:

- `PC-B worker 1`
- `PC-B worker 2`
- `PC-B worker 3`

Cada una ejecutando la plantilla de worker indicada antes.

Paso 1. Resetear el estado en `PC-A`:

```bash
cd <ruta-del-repo>
source .venv/Scripts/activate  # en Linux: .venv/bin/activate
python3 tools/local_dev/seed_state.py
```

Paso 2. Ejecutar el benchmark indirecto no numerado en `PC-A`:

```bash
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/indirect
```

Paso 3. Resetear de nuevo el estado en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
```

Paso 4. Ejecutar el benchmark indirecto numerado en `PC-A`:

```bash
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_numbered_60000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/indirect
```

Los ficheros generados quedan en:

- `benchmarks/outputs/indirect/benchmark_unnumbered_20000_summary.json`
- `benchmarks/outputs/indirect/benchmark_unnumbered_20000_results.jsonl`
- `benchmarks/outputs/indirect/benchmark_numbered_60000_summary.json`
- `benchmarks/outputs/indirect/benchmark_numbered_60000_results.jsonl`

#### 6. Test de escalabilidad en LAN

En esta prueba cambiamos manualmente cuantas terminales `worker` habia abiertas
en `PC-B`. Siempre usamos `benchmark_unnumbered_20000.txt`.

Configuracion por escenario:

- `workers_1`: abierta solo `PC-B worker 1`
- `workers_2`: abiertas `PC-B worker 1` y `PC-B worker 2`
- `workers_4`: abiertas `PC-B worker 1`, `worker 2`, `worker 3` y `worker 4`
- `workers_8`: abiertas `PC-B worker 1` hasta `worker 8`

Escenario `workers_1`, ejecutado en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_1/direct

python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_1/indirect
```

Escenario `workers_2`, ejecutado en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_2/direct

python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_2/indirect
```

Escenario `workers_4`, ejecutado en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_4/direct

python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_4/indirect
```

Escenario `workers_8`, ejecutado en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_8/direct

python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/scalability/latest/workers_8/indirect
```

#### 7. Test de hotspot / contencion en LAN

Para esta prueba dejamos abiertas tres terminales de worker en `PC-B`.

Paso 1. Generar el benchmark hotspot en `PC-A`:

```bash
python3 benchmarks/generated/generate_hotspot.py \
  --output benchmarks/generated/hotspot_benchmark.txt \
  --total-ops 60000 \
  --hotspot-pct 80 \
  --hotspot-seats-pct 5
```

Paso 2. Ejecutar `normal/direct` en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_numbered_60000.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/contention/latest/normal/direct
```

Paso 3. Ejecutar `normal/indirect` en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_numbered_60000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/contention/latest/normal/indirect
```

Paso 4. Ejecutar `hotspot/direct` en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/generated/hotspot_benchmark.txt \
  --base-url http://localhost \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/contention/latest/hotspot/direct
```

Paso 5. Ejecutar `hotspot/indirect` en `PC-A`:

```bash
python3 tools/local_dev/seed_state.py
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/generated/hotspot_benchmark.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/contention/latest/hotspot/indirect
```

#### 8. Dynamic scaling en LAN

Aqui no usamos scripts de escalado. Empezamos con dos terminales worker en
`PC-B` y, a mitad del benchmark, abrimos dos terminales adicionales.

Paso 1. Dejar abiertas solo `PC-B worker 1` y `PC-B worker 2`.

Paso 2. En `PC-A`, resetear el estado:

```bash
python3 tools/local_dev/seed_state.py
```

Paso 3. En `PC-A`, lanzar el benchmark indirecto en segundo plano:

```bash
START_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 -m concert_ticketing.apps.benchmark_runner.main \
  --benchmark benchmarks/input/benchmark_unnumbered_20000.txt \
  --base-url http://localhost:8080 \
  --concurrency 10 \
  --timeout 180 \
  --output-dir benchmarks/outputs/dynamic_scaling/latest \
  > logs/dynamic_scaling.log 2>&1 &
BENCH_PID=$!
```

Paso 4. Esperar `20` segundos.

Paso 5. Abrir `PC-B worker 3` y `PC-B worker 4` usando la misma plantilla de
worker. Ese fue el escalado real. Justo en ese momento, en `PC-A`, registrar
el instante de escalado:

```bash
SCALE_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

Paso 6. Cuando termine el benchmark en `PC-A`, guardar la metadata:

```bash
wait "$BENCH_PID"
END_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 - <<PY
import json
from pathlib import Path

data = {
    "benchmark_file": "benchmarks/input/benchmark_unnumbered_20000.txt",
    "base_url": "http://localhost:8080",
    "initial_workers": 2,
    "target_workers": 4,
    "scale_after_seconds": 20,
    "started_at": "${START_TS}",
    "scaled_at": "${SCALE_TS}",
    "finished_at": "${END_TS}",
}

Path("benchmarks/outputs/dynamic_scaling/latest/dynamic_scaling_metadata.json").write_text(
    json.dumps(data, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
PY
```

#### 9. Que partes podrian hacerse con scripts

Aunque la validacion LAN se hizo manualmente, estas partes si podrian
automatizarse con los scripts actuales:

- resetear estado en `PC-A` con `bash scripts/init_state.sh`
- lanzar benchmarks directos con `bash scripts/run_direct_benchmark.sh ...`
- lanzar benchmarks indirectos con `bash scripts/run_indirect_benchmark.sh ...`
- escalar workers en `PC-B` con `bash scripts/scale_workers_up.sh N` y `bash scripts/scale_workers_down.sh N`
- regenerar graficos y reporte final en `PC-A` con `bash scripts/generate_report.sh benchmarks/outputs`

Lo que no queda automatizado por un unico script es la coordinacion completa
entre `PC-A` y `PC-B`, porque la API remota y la apertura/cierre de terminales
de worker siguen dependiendo de dos maquinas distintas.

## Notas

- Redis es el backend de consistencia del sistema.
- RabbitMQ se usa exclusivamente en la arquitectura indirecta.
- La practica se valido tanto en local como en un despliegue distribuido en LAN.
