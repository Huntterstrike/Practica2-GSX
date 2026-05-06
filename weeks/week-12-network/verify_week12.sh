#!/bin/bash

echo "=== Week 12: Network Policy Verification ==="
echo ""

NGINX_POD=$(kubectl get pod -l app=nginx -o jsonpath='{.items[0].metadata.name}')
APP_POD=$(kubectl get pod -l app=simple-app -o jsonpath='{.items[0].metadata.name}')

echo "[1] Verificando que nginx puede hablar con simple-app..."
kubectl exec -it $NGINX_POD -- curl -s --max-time 3 http://simple-app:5000/health
if [ $? -eq 0 ]; then
  echo "✅ nginx -> simple-app: OK"
else
  echo "❌ nginx -> simple-app: FALLO"
fi

echo ""
echo "[2] Verificando que simple-app NO puede hablar directamente con redis desde nginx..."
kubectl exec -it $NGINX_POD -- curl -s --max-time 3 http://redis:6379
if [ $? -ne 0 ]; then
  echo "✅ nginx -> redis: BLOQUEADO (correcto)"
else
  echo "❌ nginx -> redis: ACCESO PERMITIDO (incorrecto)"
fi

echo ""
echo "[3] Verificando que simple-app puede hablar con redis..."
kubectl exec -it $APP_POD -- nc -zv redis 6379 2>&1
if [ $? -eq 0 ]; then
  echo "✅ simple-app -> redis: OK"
else
  echo "❌ simple-app -> redis: FALLO"
fi

echo ""
echo "[4] Estado de NetworkPolicies:"
kubectl get networkpolicies

echo ""
echo "=== Verificación completada ==="