#!/bin/bash

set -euo pipefail

echo "Cleaning local development stack..."

if command -v pm2 >/dev/null 2>&1; then
  echo "Stopping PM2 processes..."
  pm2 stop all >/dev/null 2>&1 || true
fi

for port in 3002 3006 8000; do
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    echo "Port $port is already free."
    continue
  fi

  echo "Stopping listeners on port $port: $pids"
  kill $pids 2>/dev/null || true
done

sleep 1

for port in 3002 3006 8000; do
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    continue
  fi

  echo "Force killing remaining listeners on port $port: $pids"
  kill -9 $pids 2>/dev/null || true
done

echo "Development stack cleanup complete."
