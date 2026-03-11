#!/bin/bash
# IconsAI - Monitor de Coleta

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  IconsAI - Status da Coleta Massiva                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Smart Collector
SMART_PID=$(pgrep -f "smart_collector.py" 2>/dev/null)
if [ -n "$SMART_PID" ]; then
    echo "✅ Smart Collector: RODANDO (PID: $SMART_PID)"
    echo "   Últimas linhas:"
    tail -3 logs/smart_collection_*.log 2>/dev/null | grep "progresso" | tail -1
else
    echo "❌ Smart Collector: PARADO"
fi

echo ""

# RF Importer
RF_PID=$(pgrep -f "rf_data_importer.py" 2>/dev/null)
if [ -n "$RF_PID" ]; then
    echo "✅ RF Importer: RODANDO (PID: $RF_PID)"
    echo "   Últimas linhas:"
    tail -3 logs/rf_import_*.log 2>/dev/null | tail -1
else
    echo "❌ RF Importer: PARADO"
fi

echo ""
echo "📁 Arquivos gerados:"
ls -lh data/empresas/*.json 2>/dev/null | wc -l | xargs echo "   Batches:"
du -sh data/empresas/ 2>/dev/null | xargs echo "   Tamanho:"

echo ""
echo "📊 Checkpoint Smart Collector:"
if [ -f scripts/.smart_collector_checkpoint.json ]; then
    cat scripts/.smart_collector_checkpoint.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
s = d.get('stats', {})
print(f\"   Empresas salvas: {s.get('empresas_salvas', 0):,}\")
print(f\"   Sócios coletados: {s.get('socios_coletados', 0):,}\")
print(f\"   CNPJs tentados: {s.get('cnpjs_tentados', 0):,}\")
"
fi

echo ""
echo "💡 Comandos úteis:"
echo "   tail -f logs/smart_collection_*.log"
echo "   tail -f logs/rf_import_*.log"
echo "   kill \$(cat .mass_collector.pid)"
