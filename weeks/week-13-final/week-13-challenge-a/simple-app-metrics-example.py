#!/usr/bin/env python3
"""
Ejemplo de instrumentación de simple-app con Prometheus metrics
Añade este código a tu aplicación Flask/FastAPI para exponer métricas
"""

from flask import Flask, Response, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import time
import redis
import os

app = Flask(__name__)

# Configurar conexión a Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ============================================================================
# MÉTRICAS DE PROMETHEUS
# ============================================================================

# Counter: Número total de requests (siempre incrementa)
REQUEST_COUNT = Counter(
    'app_requests_total',
    'Total de requests recibidos',
    ['method', 'endpoint', 'http_status']
)

# Histogram: Latencia de requests (percentiles, buckets)
REQUEST_LATENCY = Histogram(
    'app_request_latency_seconds',
    'Latencia de requests en segundos',
    ['endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Counter: Errores totales
ERROR_COUNT = Counter(
    'app_errors_total',
    'Total de errores',
    ['type', 'endpoint']
)

# Gauge: Conexiones activas a Redis (puede subir/bajar)
REDIS_CONNECTIONS = Gauge(
    'app_redis_connections_active',
    'Número de conexiones activas a Redis'
)

# Counter: Operaciones de Redis
REDIS_OPERATIONS = Counter(
    'app_redis_operations_total',
    'Total de operaciones en Redis',
    ['operation']
)

# ============================================================================
# MIDDLEWARE PARA AUTO-INSTRUMENTACIÓN
# ============================================================================

@app.before_request
def before_request():
    """Captura el tiempo de inicio del request"""
    request.start_time = time.time()

@app.after_request
def after_request(response):
    """Registra métricas después de cada request"""
    if hasattr(request, 'start_time'):
        # Calcular latencia
        latency = time.time() - request.start_time
        
        # Registrar en métricas
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            http_status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            endpoint=request.path
        ).observe(latency)
    
    return response

# ============================================================================
# ENDPOINTS DE LA APLICACIÓN
# ============================================================================

@app.route('/')
def index():
    """Endpoint principal"""
    try:
        # Incrementar contador en Redis
        redis_client.incr('visit_count')
        REDIS_OPERATIONS.labels(operation='incr').inc()
        
        visit_count = redis_client.get('visit_count')
        return f"""
        <h1>GreenDevCorp - Simple App</h1>
        <p>Esta página ha sido visitada {visit_count} veces.</p>
        <p>Prometheus metrics disponibles en <a href="/metrics">/metrics</a></p>
        """
    except redis.RedisError as e:
        ERROR_COUNT.labels(type='redis_error', endpoint='/').inc()
        return f"Error conectando a Redis: {str(e)}", 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Verificar conexión a Redis
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}, 200
    except redis.RedisError:
        ERROR_COUNT.labels(type='redis_error', endpoint='/health').inc()
        return {"status": "unhealthy", "redis": "disconnected"}, 503

@app.route('/slow')
def slow():
    """Endpoint simulando operación lenta (para testing de latencia)"""
    time.sleep(2)
    return "Esta operación tomó 2 segundos", 200

@app.route('/error')
def error():
    """Endpoint simulando error (para testing de alertas)"""
    ERROR_COUNT.labels(type='simulated_error', endpoint='/error').inc()
    return "Error simulado", 500

@app.route('/metrics')
def metrics():
    """
    Endpoint de métricas de Prometheus
    Este es el endpoint que Prometheus scrapeará
    """
    try:
        # Actualizar gauge de conexiones activas de Redis
        info = redis_client.info('clients')
        REDIS_CONNECTIONS.set(info.get('connected_clients', 0))
    except redis.RedisError:
        pass
    
    # Generar y devolver métricas en formato Prometheus
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("🚀 Starting Simple App with Prometheus metrics...")
    print("📊 Metrics available at http://0.0.0.0:8000/metrics")
    app.run(host='0.0.0.0', port=8000, debug=False)

# ============================================================================
# DOCKERFILE ACTUALIZADO
# ============================================================================
"""
# Dockerfile para simple-app con métricas
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()"

# Comando de inicio
CMD ["python", "app.py"]
"""

# ============================================================================
# REQUIREMENTS.TXT
# ============================================================================
"""
flask==3.0.0
redis==5.0.1
prometheus-client==0.19.0
requests==2.31.0
"""

# ============================================================================
# COMANDOS PARA RECONSTRUIR Y REDESPLEGAR
# ============================================================================
"""
# 1. Reconstruir imagen
docker build -t simple-app:v2-metrics .

# 2. Cargar en Minikube
minikube image load simple-app:v2-metrics

# 3. Actualizar deployment
kubectl set image deployment/simple-app simple-app=simple-app:v2-metrics -n default

# 4. Verificar que funcionan las métricas
kubectl port-forward svc/simple-app 8000:8000
curl http://localhost:8000/metrics

# Deberías ver output como:
# HELP app_requests_total Total de requests recibidos
# TYPE app_requests_total counter
# app_requests_total{endpoint="/",http_status="200",method="GET"} 42.0
# ...
"""
