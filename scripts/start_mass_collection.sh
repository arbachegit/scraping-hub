#!/bin/bash
# IconsAI - Mass Collection Launcher
# Inicia a coleta massiva em background
# Meta: ~1.465.000 empresas

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     IconsAI - Mass Company Collector                      ║${NC}"
echo -e "${GREEN}║     Meta: ~1.465.000 empresas                            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado${NC}"
    exit 1
fi

# Verificar .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  Arquivo .env não encontrado${NC}"
    echo "   Criando a partir do .env.example..."
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    else
        echo -e "${RED}❌ .env.example não encontrado${NC}"
        exit 1
    fi
fi

# Verificar dependências
echo -e "\n${YELLOW}📦 Verificando dependências...${NC}"
pip install -q httpx structlog supabase pydantic-settings

# Criar diretório de logs
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Timestamp para o log
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/mass_collection_$TIMESTAMP.log"

# Popular CNAEs se necessário
echo -e "\n${YELLOW}📊 Populando CNAEs (se necessário)...${NC}"
python3 "$SCRIPT_DIR/populate_cnae.py" 2>/dev/null || true

# Iniciar coleta em background
echo -e "\n${GREEN}🚀 Iniciando coleta massiva em background...${NC}"
echo -e "   Log: ${LOG_FILE}"

# Usar nohup para rodar em background
nohup python3 "$SCRIPT_DIR/parallel_collector.py" \
    --workers 10 \
    --rate 50 \
    > "$LOG_FILE" 2>&1 &

PID=$!
echo $PID > "$PROJECT_DIR/.mass_collector.pid"

echo -e "\n${GREEN}✅ Coleta iniciada!${NC}"
echo -e "   PID: $PID"
echo -e "   Log: $LOG_FILE"
echo -e "\n${YELLOW}📋 Comandos úteis:${NC}"
echo -e "   Monitorar: tail -f $LOG_FILE"
echo -e "   Status:    ps aux | grep parallel_collector"
echo -e "   Parar:     kill $PID"
echo -e "\n${GREEN}💤 Pode dormir tranquilo! A coleta está rodando em background.${NC}"
