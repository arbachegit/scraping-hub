#!/bin/bash

set -euo pipefail

conflicts=0

echo "Checking development ports..."

for port in 3002 3006 8000; do
  case "$port" in
    3002) label="Frontend Next.js" ;;
    3006) label="Backend Node.js" ;;
    8000) label="API Python" ;;
    *) label="Unknown service" ;;
  esac

  listeners="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$listeners" ]; then
    conflicts=1
    echo ""
    echo "Port $port is already in use ($label)."
    echo "$listeners"
  fi
done

if [ "$conflicts" -eq 1 ]; then
  echo ""
  echo "Start only one local stack at a time."
  echo "Use either \`npm run dev\` or \`npm run server\`, not both."
  echo ""
  echo "Typical cleanup commands:"
  echo "  pkill -f 'next dev --port 3002'"
  echo "  pkill -f 'node --watch src/index.js'"
  echo "  pkill -f 'uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload'"
  echo ""
  echo "If the stack was started with PM2, stop it with:"
  echo "  npm run server:stop"
  exit 1
fi

echo "Development ports are available."
