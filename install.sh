#!/bin/bash

# ================================================
# SCRIPT DE INSTALACIÓN AUTOMATIZADA
# Sistema de Análisis de Sentimientos con DevOps
# ================================================

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ================================================
# VERIFICAR REQUISITOS
# ================================================
check_requirements() {
    print_header "Verificando Requisitos"
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado"
        echo "Instala Docker desde: https://docs.docker.com/get-docker/"
        exit 1
    else
        print_success "Docker está instalado ($(docker --version))"
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose no está instalado"
        echo "Instala Docker Compose desde: https://docs.docker.com/compose/install/"
        exit 1
    else
        print_success "Docker Compose está instalado ($(docker-compose --version))"
    fi
    
    # Verificar Git
    if ! command -v git &> /dev/null; then
        print_warning "Git no está instalado (opcional pero recomendado)"
    else
        print_success "Git está instalado ($(git --version))"
    fi
    
    # Verificar Python (opcional, para desarrollo local)
    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 no está instalado (opcional para desarrollo local)"
    else
        print_success "Python 3 está instalado ($(python3 --version))"
    fi
}

# ================================================
# CREAR ESTRUCTURA DE DIRECTORIOS
# ================================================
create_directories() {
    print_header "Creando Estructura de Directorios"
    
    directories=(
        "backend/tests"
        "frontend/assets"
        "monitoring/prometheus"
        "monitoring/grafana/provisioning/datasources"
        "monitoring/grafana/provisioning/dashboards"
        "monitoring/grafana/dashboards"
        "data"
        "logs"
        "security_reports"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Creado: $dir"
        else
            print_info "Ya existe: $dir"
        fi
    done
}

# ================================================
# CONFIGURAR VARIABLES DE ENTORNO
# ================================================
setup_environment() {
    print_header "Configurando Variables de Entorno"
    
    if [ ! -f .env ]; then
        print_info "Creando archivo .env..."
        
        # Generar claves secretas aleatorias
        JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || echo "jwt-secret-change-this-in-production")
        ENCRYPTION_KEY=$(openssl rand -hex 16 2>/dev/null || echo "encryption-key-change-prod")
        
        cat > .env << EOF
# Variables de Entorno - Análisis de Sentimientos
# IMPORTANTE: Cambiar estos valores en producción

# Backend
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./data/palettes.db

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin

# Entorno
ENVIRONMENT=development
DEBUG=true
EOF
        
        print_success "Archivo .env creado"
        print_warning "¡IMPORTANTE! Cambia las claves secretas en producción"
    else
        print_info "Archivo .env ya existe"
    fi
}

# ================================================
# CONFIGURAR GRAFANA DATASOURCES
# ================================================
setup_grafana_datasources() {
    print_header "Configurando Grafana Datasources"
    
    cat > monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "5s"
EOF
    
    print_success "Datasource de Prometheus configurado"
}

# ================================================
# CONFIGURAR GRAFANA DASHBOARDS
# ================================================
setup_grafana_dashboards() {
    print_header "Configurando Grafana Dashboards"
    
    cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'Sentiment Analysis'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/dashboards
EOF
    
    print_success "Provisionamiento de dashboards configurado"
}

# ================================================
# CONFIGURAR NGINX
# ================================================
setup_nginx() {
    print_header "Configurando Nginx"
    
    if [ ! -f nginx.conf ]; then
        cat > nginx.conf << 'EOF'
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy para el backend (opcional)
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
        print_success "Configuración de Nginx creada"
    else
        print_info "nginx.conf ya existe"
    fi
}

# ================================================
# CREAR .GITIGNORE
# ================================================
create_gitignore() {
    print_header "Creando .gitignore"
    
    if [ ! -f .gitignore ]; then
        cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
*.egg-info/
dist/
build/

# Database
*.db
data/*.db

# Logs
logs/*.log
logs/*.json

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# Security reports
security_reports/*.docx
security_reports/*.html

# Docker
.dockerignore

# Tests
.pytest_cache/
htmlcov/
.coverage
coverage.xml

# OS
.DS_Store
Thumbs.db
EOF
        print_success ".gitignore creado"
    else
        print_info ".gitignore ya existe"
    fi
}

# ================================================
# CONSTRUIR IMÁGENES DOCKER
# ================================================
build_docker_images() {
    print_header "Construyendo Imágenes Docker"
    
    print_info "Esto puede tomar varios minutos..."
    
    if docker-compose build; then
        print_success "Imágenes Docker construidas exitosamente"
    else
        print_error "Error construyendo imágenes Docker"
        exit 1
    fi
}

# ================================================
# INICIAR SERVICIOS
# ================================================
start_services() {
    print_header "Iniciando Servicios"
    
    print_info "Levantando contenedores..."
    
    if docker-compose up -d; then
        print_success "Servicios iniciados exitosamente"
        
        # Esperar a que los servicios estén listos
        print_info "Esperando a que los servicios estén listos..."
        sleep 10
        
        # Verificar estado de los servicios
        docker-compose ps
    else
        print_error "Error iniciando servicios"
        exit 1
    fi
}

# ================================================
# CREAR USUARIO ADMIN POR DEFECTO
# ================================================
create_admin_user() {
    print_header "Configurando Usuario Admin"
    
    print_info "El usuario admin se crea automáticamente al iniciar el backend"
    print_info "Credenciales por defecto:"
    echo "  Usuario: admin"
    echo "  Password: admin123"
    print_warning "¡Cambia estas credenciales después del primer login!"
}

# ================================================
# EJECUTAR TESTS
# ================================================
run_tests() {
    print_header "Ejecutando Tests (Opcional)"
    
    read -p "¿Deseas ejecutar los tests ahora? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Ejecutando tests..."
        
        if docker-compose exec -T backend pytest tests/ -v; then
            print_success "Tests ejecutados exitosamente"
        else
            print_warning "Algunos tests fallaron (esto es normal si es la primera ejecución)"
        fi
    else
        print_info "Tests omitidos. Puedes ejecutarlos después con: docker-compose exec backend pytest tests/ -v"
    fi
}

# ================================================
# MOSTRAR INFORMACIÓN FINAL
# ================================================
show_final_info() {
    print_header "¡Instalación Completada!"
    
    echo ""
    echo -e "${GREEN}El sistema está listo para usar${NC}"
    echo ""
    echo "📱 Servicios disponibles:"
    echo ""
    echo -e "  🎨 Frontend:           ${BLUE}http://localhost:8081${NC}"
    echo -e "  🚀 Backend API:        ${BLUE}http://localhost:8000${NC}"
    echo -e "  📚 API Docs:           ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "  📊 Prometheus:         ${BLUE}http://localhost:9090${NC}"
    echo -e "  📈 Grafana:            ${BLUE}http://localhost:3000${NC}"
    echo -e "       Usuario: admin"
    echo -e "       Password: admin"
    echo ""
    echo "📋 Comandos útiles:"
    echo ""
    echo "  Ver logs:              docker-compose logs -f"
    echo "  Ver logs del backend:  docker-compose logs -f backend"
    echo "  Parar servicios:       docker-compose down"
    echo "  Reiniciar:             docker-compose restart"
    echo "  Ver estado:            docker-compose ps"
    echo "  Ejecutar tests:        docker-compose exec backend pytest tests/ -v"
    echo "  Análisis seguridad:    docker-compose exec backend python security_scan.py"
    echo ""
    echo "🔐 Credenciales por defecto:"
    echo ""
    echo "  Admin API:"
    echo "    Usuario: admin"
    echo "    Password: admin123"
    echo ""
    echo "  Grafana:"
    echo "    Usuario: admin"
    echo "    Password: admin"
    echo ""
    print_warning "¡Recuerda cambiar las contraseñas por defecto!"
    echo ""
    echo "📖 Documentación completa en README.md"
    echo ""
    print_success "¡Disfruta del sistema!"
}

# ================================================
# FUNCIÓN PRINCIPAL
# ================================================
main() {
    echo ""
    print_header "Sistema de Análisis de Sentimientos con DevOps"
    echo ""
    
    check_requirements
    create_directories
    setup_environment
    setup_grafana_datasources
    setup_grafana_dashboards
    setup_nginx
    create_gitignore
    build_docker_images
    start_services
    create_admin_user
    run_tests
    show_final_info
}

# Ejecutar instalación
main