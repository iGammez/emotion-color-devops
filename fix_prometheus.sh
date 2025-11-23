#!/bin/bash

# Script para diagnosticar y solucionar problemas de Prometheus

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Diagnóstico de Prometheus${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Función para verificar
check_step() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
        return 0
    else
        echo -e "${RED}✗ $1${NC}"
        return 1
    fi
}

# 1. Verificar si el contenedor está corriendo
echo -e "${YELLOW}1. Verificando contenedor de Prometheus...${NC}"
if docker ps | grep -q emotion-prometheus; then
    echo -e "${GREEN}✓ Contenedor corriendo${NC}"
    docker ps | grep emotion-prometheus
else
    echo -e "${RED}✗ Contenedor NO está corriendo${NC}"
    echo ""
    echo "Intentando ver el estado:"
    docker ps -a | grep emotion-prometheus
    echo ""
    echo "Logs del contenedor:"
    docker logs emotion-prometheus 2>&1 | tail -20
fi
echo ""

# 2. Verificar puerto
echo -e "${YELLOW}2. Verificando puerto 9090...${NC}"
if netstat -tuln 2>/dev/null | grep -q :9090 || ss -tuln 2>/dev/null | grep -q :9090; then
    echo -e "${GREEN}✓ Puerto 9090 está en uso${NC}"
else
    echo -e "${RED}✗ Puerto 9090 NO está escuchando${NC}"
fi
echo ""

# 3. Verificar archivo de configuración
echo -e "${YELLOW}3. Verificando archivo prometheus.yml...${NC}"
if [ -f "monitoring/prometheus/prometheus.yml" ]; then
    echo -e "${GREEN}✓ Archivo existe${NC}"
    echo ""
    echo "Contenido:"
    cat monitoring/prometheus/prometheus.yml
    echo ""
    
    # Validar sintaxis YAML
    if docker run --rm -v "$(pwd)/monitoring/prometheus:/prometheus" prom/prometheus:latest promtool check config /prometheus/prometheus.yml 2>&1; then
        echo -e "${GREEN}✓ Sintaxis válida${NC}"
    else
        echo -e "${RED}✗ Error de sintaxis en prometheus.yml${NC}"
    fi
else
    echo -e "${RED}✗ Archivo prometheus.yml NO existe${NC}"
fi
echo ""

# 4. Intentar acceder a Prometheus
echo -e "${YELLOW}4. Intentando acceder a Prometheus...${NC}"
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Prometheus responde (healthy)${NC}"
elif curl -s http://localhost:9090 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Prometheus responde pero no está healthy${NC}"
else
    echo -e "${RED}✗ No se puede acceder a Prometheus${NC}"
fi
echo ""

# 5. Ver logs recientes
echo -e "${YELLOW}5. Logs de Prometheus (últimas 30 líneas):${NC}"
echo ""
docker logs emotion-prometheus 2>&1 | tail -30
echo ""

# 6. Verificar targets
echo -e "${YELLOW}6. Verificando targets configurados...${NC}"
if curl -s http://localhost:9090/api/v1/targets 2>/dev/null | grep -q "backend"; then
    echo -e "${GREEN}✓ Targets configurados${NC}"
    echo ""
    echo "Targets activos:"
    curl -s http://localhost:9090/api/v1/targets 2>/dev/null | grep -o '"job":"[^"]*"' | sort -u
else
    echo -e "${RED}✗ No se pueden obtener targets${NC}"
fi
echo ""

# Diagnóstico final y sugerencias
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Diagnóstico Completo${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Estado del contenedor:"
docker inspect emotion-prometheus --format='{{.State.Status}}' 2>/dev/null || echo "Contenedor no encontrado"
echo ""

echo -e "${YELLOW}Posibles soluciones:${NC}"
echo ""
echo "1. Si el contenedor no está corriendo:"
echo "   docker-compose restart prometheus"
echo ""
echo "2. Si hay error de configuración:"
echo "   ./fix_prometheus_config.sh"
echo ""
echo "3. Si el puerto está en uso:"
echo "   sudo lsof -i :9090"
echo "   # Matar el proceso o cambiar el puerto"
echo ""
echo "4. Reiniciar desde cero:"
echo "   docker-compose down"
echo "   docker-compose up -d"
echo ""
echo "5. Ver logs detallados:"
echo "   docker logs -f emotion-prometheus"
echo ""

# Preguntar si desea intentar solución automática
echo ""
read -p "¿Deseas intentar una solución automática? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}Aplicando solución automática...${NC}"
    
    # Crear configuración correcta
    mkdir -p monitoring/prometheus
    
    cat > monitoring/prometheus/prometheus.yml << 'EOF'
# Configuración de Prometheus
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'emotion-color-analysis'
    environment: 'production'

# Configuración de scraping
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'backend-api'
    scrape_interval: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['backend:8000']
EOF
    
    echo -e "${GREEN}✓ Configuración creada${NC}"
    
    # Crear alerts.yml si no existe
    if [ ! -f "monitoring/prometheus/alerts.yml" ]; then
        cat > monitoring/prometheus/alerts.yml << 'EOF'
groups:
  - name: basic_alerts
    interval: 30s
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
EOF
        echo -e "${GREEN}✓ Alerts creado${NC}"
    fi
    
    # Reiniciar Prometheus
    echo ""
    echo -e "${YELLOW}Reiniciando Prometheus...${NC}"
    docker-compose restart prometheus
    
    echo ""
    echo -e "${YELLOW}Esperando a que Prometheus inicie...${NC}"
    sleep 10
    
    # Verificar
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ¡Prometheus está funcionando!${NC}"
        echo ""
        echo "Accede en: http://localhost:9090"
    else
        echo -e "${RED}❌ Prometheus sigue sin responder${NC}"
        echo ""
        echo "Ver logs:"
        docker logs emotion-prometheus 2>&1 | tail -20
    fi
fi