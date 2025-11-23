#!/bin/bash

# Solución completa para error de Grafana datasource

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Solución Completa Error Grafana${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Paso 1: Limpiar todo
echo -e "${YELLOW}Paso 1: Limpiando servicios...${NC}"
docker-compose down -v
echo -e "${GREEN}✓ Servicios detenidos${NC}"
echo ""

# Paso 2: Limpiar directorios de Grafana
echo -e "${YELLOW}Paso 2: Limpiando y recreando estructura...${NC}"
rm -rf monitoring/grafana/provisioning
rm -rf monitoring/grafana/dashboards
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards
echo -e "${GREEN}✓ Estructura recreada${NC}"
echo ""

# Paso 3: Crear datasource CORRECTO
echo -e "${YELLOW}Paso 3: Creando datasource de Prometheus...${NC}"
cat > monitoring/grafana/provisioning/datasources/datasource.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      httpMethod: POST
      timeInterval: 5s
EOF

echo -e "${GREEN}✓ Datasource creado${NC}"
echo ""

# Paso 4: Crear provisioning de dashboards
echo -e "${YELLOW}Paso 4: Creando provisioning de dashboards...${NC}"
cat > monitoring/grafana/provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
EOF

echo -e "${GREEN}✓ Provisioning de dashboards creado${NC}"
echo ""

# Paso 5: Crear dashboard SIMPLIFICADO
echo -e "${YELLOW}Paso 5: Creando dashboard simplificado...${NC}"
cat > monitoring/grafana/dashboards/main.json << 'EOF'
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              }
            ]
          }
        }
      },
      "gridPos": {
        "h": 8,
        "w": 6,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "textMode": "auto"
      },
      "pluginVersion": "10.0.0",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum(palettes_created_total)",
          "refId": "A"
        }
      ],
      "title": "Total Palettes Created",
      "type": "stat"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisCenteredZero": false,
            "axisColorMode": "text",
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 10,
            "gradientMode": "none",
            "hideFrom": {
              "tooltip": false,
              "viz": false,
              "legend": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "never",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "none"
            },
            "thresholdsStyle": {
              "mode": "off"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              }
            ]
          },
          "unit": "short"
        }
      },
      "gridPos": {
        "h": 8,
        "w": 18,
        "x": 6,
        "y": 0
      },
      "id": 2,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom",
          "showLegend": true
        },
        "tooltip": {
          "mode": "multi",
          "sort": "none"
        }
      },
      "pluginVersion": "10.0.0",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (sentiment_type) (rate(palettes_created_total[5m]))",
          "legendFormat": "{{sentiment_type}}",
          "refId": "A"
        }
      ],
      "title": "Sentiment Analysis Rate",
      "type": "timeseries"
    }
  ],
  "refresh": "10s",
  "schemaVersion": 38,
  "tags": [],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "Sentiment Analysis",
  "uid": "sentiment-main",
  "version": 1
}
EOF

echo -e "${GREEN}✓ Dashboard creado${NC}"
echo ""

# Paso 6: Modificar docker-compose para usar los volúmenes correctamente
echo -e "${YELLOW}Paso 6: Actualizando docker-compose.yml...${NC}"

# Crear backup del docker-compose
cp docker-compose.yml docker-compose.yml.backup

# Crear nuevo docker-compose con configuración correcta de Grafana
cat > docker-compose.yml << 'EOFCOMPOSE'
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: emotion-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/app/data
      - ./logs:/app/logs
      - ./security_reports:/app/security_reports
    environment:
      - DATABASE_URL=sqlite:///./data/palettes.db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-jwt-super-secret-key-change-in-production-32-chars}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY:-encryption-key-change-in-prod-32}
      - JWT_ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=30
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    networks:
      - emotion-network

  frontend:
    image: nginx:alpine
    container_name: emotion-frontend
    ports:
      - "8081:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - emotion-network

  prometheus:
    image: prom/prometheus:latest
    container_name: emotion-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - emotion-network

  grafana:
    image: grafana/grafana:latest
    container_name: emotion-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro
      - ./monitoring/grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=http://localhost:3000
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_INSTALL_PLUGINS=
      - GF_LOG_LEVEL=info
    depends_on:
      - prometheus
    restart: unless-stopped
    networks:
      - emotion-network

volumes:
  prometheus-data:
    driver: local
  grafana-data:
    driver: local

networks:
  emotion-network:
    driver: bridge
EOFCOMPOSE

echo -e "${GREEN}✓ docker-compose.yml actualizado (backup en docker-compose.yml.backup)${NC}"
echo ""

# Paso 7: Verificar estructura
echo -e "${YELLOW}Paso 7: Verificando estructura de archivos...${NC}"
echo ""

files=(
  "monitoring/grafana/provisioning/datasources/datasource.yml"
  "monitoring/grafana/provisioning/dashboards/dashboards.yml"
  "monitoring/grafana/dashboards/main.json"
  "monitoring/prometheus/prometheus.yml"
  "docker-compose.yml"
)

all_ok=true
for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo -e "${GREEN}✓${NC} $file"
  else
    echo -e "${RED}✗${NC} $file"
    all_ok=false
  fi
done

echo ""

if [ "$all_ok" = false ]; then
  echo -e "${RED}❌ Algunos archivos faltan. Revisa la estructura.${NC}"
  exit 1
fi

# Paso 8: Iniciar servicios
echo -e "${YELLOW}Paso 8: Iniciando servicios...${NC}"
docker-compose up -d

echo ""
echo -e "${GREEN}✓ Servicios iniciados${NC}"
echo ""

# Paso 9: Esperar y verificar
echo -e "${YELLOW}Paso 9: Esperando a que los servicios estén listos...${NC}"
echo ""

sleep 5

echo "Verificando Backend..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend está UP${NC}"
    break
  fi
  echo -n "."
  sleep 2
done
echo ""

echo "Verificando Prometheus..."
for i in {1..30}; do
  if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Prometheus está UP${NC}"
    break
  fi
  echo -n "."
  sleep 2
done
echo ""

echo "Verificando Grafana..."
for i in {1..60}; do
  if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Grafana está UP${NC}"
    break
  fi
  echo -n "."
  sleep 2
done
echo ""

# Paso 10: Mostrar logs de Grafana
echo -e "${YELLOW}Paso 10: Logs de Grafana (últimas 20 líneas)...${NC}"
echo ""
docker-compose logs --tail=20 grafana
echo ""

# Verificación final
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verificación Final${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Estado de contenedores:"
docker-compose ps
echo ""

echo -e "${GREEN}✅ Instalación completada${NC}"
echo ""
echo "🌐 Accede a los servicios:"
echo ""
echo -e "  Frontend:    ${BLUE}http://localhost:8081${NC}"
echo -e "  Backend API: ${BLUE}http://localhost:8000${NC}"
echo -e "  API Docs:    ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  Prometheus:  ${BLUE}http://localhost:9090${NC}"
echo -e "  Grafana:     ${BLUE}http://localhost:3000${NC}"
echo ""
echo "📊 Login Grafana:"
echo "  Usuario: admin"
echo "  Password: admin"
echo ""
echo "📋 Ver logs en tiempo real:"
echo "  docker-compose logs -f"
echo ""
echo "🔧 Si Grafana sigue con problemas:"
echo "  docker-compose logs grafana"
echo ""