"""
Tests Automatizados para API de Análisis de Sentimientos
Requisito 3: Pruebas automatizadas con múltiples escenarios
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Agregar el directorio backend al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app, get_db
from database import Base
from auth import get_password_hash
import models_auth

# ================================================
# CONFIGURACIÓN DE TESTS
# ================================================

# Base de datos en memoria para tests
TEST_DATABASE_URL = "sqlite:///./test_database.db"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Crear tablas de test
Base.metadata.create_all(bind=test_engine)

# Override de la dependencia de DB
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Cliente de test
client = TestClient(app)

# ================================================
# FIXTURES
# ================================================

@pytest.fixture(scope="function")
def test_db():
    """Fixture que proporciona una base de datos limpia para cada test"""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_user(test_db):
    """Fixture que crea un usuario de prueba"""
    user = models_auth.User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("Password123"),
        full_name="Test User",
        role="user",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_admin(test_db):
    """Fixture que crea un administrador de prueba"""
    admin = models_auth.User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("Admin123"),
        full_name="Admin User",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin

@pytest.fixture
def auth_token(test_user):
    """Fixture que proporciona un token de autenticación válido"""
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "Password123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
def admin_token(test_admin):
    """Fixture que proporciona un token de administrador"""
    response = client.post(
        "/token",
        data={"username": "admin", "password": "Admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

# ================================================
# TESTS DE ENDPOINTS BÁSICOS
# ================================================

def test_root_endpoint():
    """Test 1: Endpoint raíz responde correctamente"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data

def test_health_check():
    """Test 2: Health check responde correctamente"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "features" in data

# ================================================
# TESTS DE REGISTRO Y AUTENTICACIÓN
# ================================================

def test_register_user_success(test_db):
    """Test 3: Registro exitoso de usuario"""
    response = client.post(
        "/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Password123",
            "full_name": "New User",
            "phone": "555-1234",
            "address": "Test Address 123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "hashed_password" not in data

def test_register_user_duplicate_username(test_user):
    """Test 4: ERROR - Usuario duplicado"""
    response = client.post(
        "/register",
        json={
            "username": "testuser",  # Ya existe
            "email": "another@example.com",
            "password": "Password123",
            "full_name": "Another User"
        }
    )
    assert response.status_code == 400
    assert "ya registrado" in response.json()["detail"]

def test_register_user_weak_password(test_db):
    """Test 5: ERROR - Contraseña débil"""
    response = client.post(
        "/register",
        json={
            "username": "weakpass",
            "email": "weak@example.com",
            "password": "123",  # Muy corta
            "full_name": "Weak Pass"
        }
    )
    assert response.status_code == 422  # Validation error

def test_login_success(test_user):
    """Test 6: Login exitoso"""
    response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "Password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(test_user):
    """Test 7: ERROR - Contraseña incorrecta"""
    response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "WrongPassword"
        }
    )
    assert response.status_code == 401
    assert "incorrectas" in response.json()["detail"]

def test_login_nonexistent_user(test_db):
    """Test 8: ERROR - Usuario no existe"""
    response = client.post(
        "/token",
        data={
            "username": "nonexistent",
            "password": "Password123"
        }
    )
    assert response.status_code == 401

# ================================================
# TESTS DE ANÁLISIS DE SENTIMIENTOS
# ================================================

def test_analyze_positive_sentiment(auth_token):
    """Test 9: Análisis de sentimiento positivo"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "Estoy muy feliz y emocionado",
            "method": "hybrid"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "colors" in data
    assert len(data["colors"]) == 5
    assert data["polarity"] > 0
    assert "positive" in data["sentiment"]

def test_analyze_negative_sentiment(auth_token):
    """Test 10: Análisis de sentimiento negativo"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "Me siento muy triste y deprimido",
            "method": "hybrid"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "colors" in data
    assert data["polarity"] < 0
    assert "negative" in data["sentiment"]

def test_analyze_neutral_sentiment(auth_token):
    """Test 11: Análisis de sentimiento neutral"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "El cielo es azul",
            "method": "hybrid"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "colors" in data
    assert abs(data["polarity"]) < 0.3  # Cercano a neutral

def test_analyze_empty_text(auth_token):
    """Test 12: ERROR - Texto vacío"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "",
            "method": "hybrid"
        }
    )
    assert response.status_code == 400 or response.status_code == 422

def test_analyze_very_long_text(auth_token):
    """Test 13: ERROR - Texto muy largo"""
    long_text = "a" * 1500  # Más de 1000 caracteres
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": long_text,
            "method": "hybrid"
        }
    )
    assert response.status_code == 400 or response.status_code == 422

def test_analyze_different_methods(auth_token):
    """Test 14: Diferentes métodos de análisis"""
    methods = ["textblob", "vader", "hybrid"]
    text = "Me siento genial hoy"
    
    for method in methods:
        response = client.post(
            "/analyze",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "text": text,
                "method": method
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["method_used"] == method

def test_analyze_without_auth():
    """Test 15: ERROR - Sin autenticación"""
    response = client.post(
        "/analyze",
        json={
            "text": "Test text",
            "method": "hybrid"
        }
    )
    assert response.status_code == 401

def test_analyze_invalid_token():
    """Test 16: ERROR - Token inválido"""
    response = client.post(
        "/analyze",
        headers={"Authorization": "Bearer invalid_token_here"},
        json={
            "text": "Test text",
            "method": "hybrid"
        }
    )
    assert response.status_code == 401

# ================================================
# TESTS DE GALERÍA
# ================================================

def test_get_gallery_empty(auth_token, test_db):
    """Test 17: Galería vacía"""
    response = client.get(
        "/gallery",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["palettes"]) == 0

def test_get_gallery_with_palettes(auth_token, test_user, test_db):
    """Test 18: Galería con paletas"""
    # Crear una paleta primero
    client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "Soy feliz", "method": "hybrid"}
    )
    
    response = client.get(
        "/gallery",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["palettes"]) > 0

def test_get_gallery_without_auth():
    """Test 19: ERROR - Galería sin autenticación"""
    response = client.get("/gallery")
    assert response.status_code == 401

# ================================================
# TESTS DE ELIMINACIÓN DE PALETAS
# ================================================

def test_delete_own_palette(auth_token, test_user, test_db):
    """Test 20: Eliminar propia paleta"""
    # Crear paleta
    create_response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "Test", "method": "hybrid"}
    )
    assert create_response.status_code == 200
    
    # Obtener ID de la paleta creada
    gallery_response = client.get(
        "/gallery",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    palette_id = gallery_response.json()["palettes"][0]["id"]
    
    # Eliminar paleta
    delete_response = client.delete(
        f"/palettes/{palette_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert delete_response.status_code == 200

def test_delete_nonexistent_palette(auth_token):
    """Test 21: ERROR - Eliminar paleta inexistente"""
    response = client.delete(
        "/palettes/99999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404

# ================================================
# TESTS DE PERMISOS Y ROLES
# ================================================

def test_admin_can_see_all_palettes(admin_token, auth_token, test_admin, test_user, test_db):
    """Test 22: Admin ve todas las paletas"""
    # Usuario normal crea paleta
    client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "User palette", "method": "hybrid"}
    )
    
    # Admin ve la galería
    response = client.get(
        "/gallery",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0

def test_user_sees_only_own_palettes(auth_token, test_user, test_db):
    """Test 23: Usuario normal solo ve sus paletas"""
    # Crear paleta
    client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"text": "My palette", "method": "hybrid"}
    )
    
    response = client.get(
        "/gallery",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    # Solo debería ver sus propias paletas
    assert all(p["input_text"] == "My palette" for p in data["palettes"])

# ================================================
# TESTS DE ESTADÍSTICAS
# ================================================

def test_get_stats(auth_token):
    """Test 24: Obtener estadísticas"""
    response = client.get(
        "/stats",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_palettes" in data
    assert "total_users" in data

def test_get_stats_without_auth():
    """Test 25: ERROR - Estadísticas sin autenticación"""
    response = client.get("/stats")
    assert response.status_code == 401

# ================================================
# TESTS DE VALIDACIÓN DE DATOS
# ================================================

def test_analyze_with_special_characters(auth_token):
    """Test 26: Análisis con caracteres especiales"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "¡Estoy súper feliz! 😊 #BuenosDías",
            "method": "hybrid"
        }
    )
    assert response.status_code == 200

def test_analyze_with_numbers(auth_token):
    """Test 27: Análisis con números"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "Tengo 100 razones para ser feliz",
            "method": "hybrid"
        }
    )
    assert response.status_code == 200

def test_color_format_validation(auth_token):
    """Test 28: Validación de formato de colores hexadecimales"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "Feliz",
            "method": "hybrid"
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    # Verificar que todos los colores tengan formato hexadecimal válido
    import re
    hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
    for color in data["colors"]:
        assert hex_pattern.match(color), f"Color inválido: {color}"

# ================================================
# TESTS DE MÉTRICAS
# ================================================

def test_metrics_endpoint():
    """Test 29: Endpoint de métricas Prometheus"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    # Verificar que contenga algunas métricas esperadas
    assert "palettes_created_total" in response.text or "python_info" in response.text

# ================================================
# TESTS DE EDGE CASES
# ================================================

def test_analyze_with_only_punctuation(auth_token):
    """Test 30: ERROR - Solo puntuación"""
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "text": "!!!???...",
            "method": "hybrid"
        }
    )
    # Debería fallar o devolver neutral
    assert response.status_code in [200, 400]

def test_concurrent_palette_creation(auth_token):
    """Test 31: Creación concurrente de paletas"""
    import concurrent.futures
    
    def create_palette():
        return client.post(
            "/analyze",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"text": "Concurrente", "method": "hybrid"}
        )
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_palette) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Todas deberían ser exitosas
    assert all(r.status_code == 200 for r in results)

# ================================================
# CLEANUP
# ================================================

def teardown_module(module):
    """Limpieza después de todos los tests"""
    try:
        os.remove("test_database.db")
    except:
        pass

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=html"])