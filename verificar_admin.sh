#!/bin/bash

# Script para verificar y crear el usuario admin

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verificación de Usuario Admin${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. Verificar que el backend está corriendo
echo -e "${YELLOW}1. Verificando backend...${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend está corriendo${NC}"
else
    echo -e "${RED}✗ Backend NO está corriendo${NC}"
    echo "Intenta: docker-compose restart backend"
    exit 1
fi
echo ""

# 2. Verificar base de datos
echo -e "${YELLOW}2. Verificando base de datos...${NC}"
if [ -f "data/palettes.db" ]; then
    echo -e "${GREEN}✓ Base de datos existe${NC}"
    
    # Ver usuarios en la BD
    echo ""
    echo "Usuarios en la base de datos:"
    sqlite3 data/palettes.db "SELECT username, email, role, is_active FROM users;" 2>/dev/null || echo "No se pudo leer la BD"
else
    echo -e "${RED}✗ Base de datos NO existe${NC}"
fi
echo ""

# 3. Intentar login con admin
echo -e "${YELLOW}3. Probando login con admin/admin123...${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

status_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✓ Login exitoso con admin/admin123${NC}"
    echo "Respuesta:"
    echo "$body" | jq . 2>/dev/null || echo "$body"
else
    echo -e "${RED}✗ Login falló (HTTP $status_code)${NC}"
    echo "Respuesta:"
    echo "$body" | jq . 2>/dev/null || echo "$body"
    echo ""
    echo -e "${YELLOW}Vamos a crear el usuario admin...${NC}"
fi
echo ""

# 4. Crear usuario admin si no existe
echo -e "${YELLOW}4. Creando usuario admin...${NC}"

register_response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@emotion-color.com",
    "password": "admin123",
    "full_name": "Administrador del Sistema"
  }')

register_status=$(echo "$register_response" | tail -n 1)
register_body=$(echo "$register_response" | head -n -1)

if [ "$register_status" = "201" ]; then
    echo -e "${GREEN}✓ Usuario admin creado exitosamente${NC}"
    echo "Detalles:"
    echo "$register_body" | jq . 2>/dev/null || echo "$register_body"
elif [ "$register_status" = "400" ]; then
    echo -e "${YELLOW}⚠ Usuario admin ya existe${NC}"
else
    echo -e "${RED}✗ Error al crear admin (HTTP $register_status)${NC}"
    echo "$register_body"
fi
echo ""

# 5. Actualizar rol a admin en la BD
echo -e "${YELLOW}5. Asegurando que el usuario admin tenga rol de administrador...${NC}"
if [ -f "data/palettes.db" ]; then
    sqlite3 data/palettes.db "UPDATE users SET role='admin', is_active=1 WHERE username='admin';" 2>/dev/null
    
    # Verificar
    admin_info=$(sqlite3 data/palettes.db "SELECT username, role, is_active FROM users WHERE username='admin';" 2>/dev/null)
    if [ ! -z "$admin_info" ]; then
        echo -e "${GREEN}✓ Usuario admin configurado:${NC}"
        echo "  $admin_info"
    fi
else
    echo -e "${RED}✗ No se pudo acceder a la base de datos${NC}"
fi
echo ""

# 6. Probar login nuevamente
echo -e "${YELLOW}6. Probando login nuevamente...${NC}"
final_response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

final_status=$(echo "$final_response" | tail -n 1)
final_body=$(echo "$final_response" | head -n -1)

if [ "$final_status" = "200" ]; then
    echo -e "${GREEN}✅ ¡LOGIN EXITOSO!${NC}"
    echo ""
    echo "Credenciales confirmadas:"
    echo -e "${BLUE}Usuario: admin${NC}"
    echo -e "${BLUE}Password: admin123${NC}"
    echo ""
    echo "Token recibido:"
    echo "$final_body" | jq -r .access_token 2>/dev/null | head -c 50
    echo "..."
else
    echo -e "${RED}✗ Login sigue fallando${NC}"
    echo "HTTP Status: $final_status"
    echo "Respuesta: $final_body"
    echo ""
    echo -e "${YELLOW}Solución alternativa:${NC}"
    echo "Ejecuta: docker-compose restart backend"
fi
echo ""

# 7. Resumen
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RESUMEN${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Credenciales del admin:"
echo -e "  Usuario:  ${GREEN}admin${NC}"
echo -e "  Password: ${GREEN}admin123${NC}"
echo ""
echo "Para probar en el navegador:"
echo "  1. Ve a: http://localhost:8081/login.html"
echo "  2. Ingresa las credenciales de arriba"
echo ""
echo "Si sigue sin funcionar:"
echo "  1. docker-compose restart backend"
echo "  2. Espera 10 segundos"
echo "  3. Ejecuta este script nuevamente"
echo ""