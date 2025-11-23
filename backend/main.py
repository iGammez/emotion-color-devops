from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, validator
from textblob import TextBlob
from deep_translator import GoogleTranslator
from sqlalchemy.orm import Session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
import colorsys
from typing import Optional
import time
from contextlib import asynccontextmanager
from datetime import datetime
import os

# Importar sistema de logging y métricas
from logger_config import app_logger, event_logger
from metrics import (
    record_palette_created, record_palette_deleted, record_api_request,
    record_error, record_translation, update_system_metrics, 
    update_database_metrics, set_app_info, metrics_exporter
)

# Importar autenticación y encriptación
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_active_user, get_current_admin,
    require_permission, UserRole
)
from encryption import encrypt_data, decrypt_data
from schemas import UserCreate, UserResponse, Token, PasswordChange

import models
import models_auth
from database import SessionLocal, engine
from color_generator import AdvancedColorGenerator

# Crear tablas
models.Base.metadata.create_all(bind=engine)
models_auth.Base.metadata.create_all(bind=engine)

# Configurar información de la aplicación
set_app_info(version="2.0.0", python_version="3.12")

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación"""
    # ========== STARTUP ==========
    app_logger.info("🚀 Iniciando Emotion Color Palette API v2.0 con Seguridad")
    
    # Iniciar métricas
    try:
        metrics_exporter.start_server()
        app_logger.info("✅ Servidor de métricas iniciado en puerto 9090")
    except Exception as e:
        app_logger.error(f"⚠️ Error en métricas: {e}")
    
    update_system_metrics()
    
    # Crear usuario admin por defecto
    db = SessionLocal()
    try:
        admin_user = db.query(models_auth.User).filter(
            models_auth.User.username == "admin"
        ).first()
        
        if not admin_user:
            # CONTRASEÑA CORTA (máximo 72 bytes para bcrypt)
            admin_password = "Admin123!"  # ← 10 caracteres
            
            admin_user = models_auth.User(
                username="admin",
                email="admin@emotion-color.com",
                hashed_password=get_password_hash(admin_password),
                full_name="Administrador del Sistema",
                role=UserRole.ADMIN,
                phone=encrypt_data("555-0000"),  # ← ENCRIPTADO
                address=encrypt_data("Oficina Central")  # ← ENCRIPTADO
            )
            db.add(admin_user)
            db.commit()
            app_logger.info("✅ Usuario admin creado (admin/Admin123!)")
        else:
            app_logger.info("ℹ️ Usuario admin ya existe")
    except Exception as e:
        app_logger.error(f"❌ Error creando admin: {e}")
        db.rollback()
    finally:
        db.close()
    
    yield
    
    # ========== SHUTDOWN ==========
    app_logger.info("👋 Cerrando aplicación")

app = FastAPI(
    title="Emotion Color Palette API",
    description="API con autenticación, encriptación y análisis de sentimientos",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #Asegurar 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "unknown"
    
    app_logger.info(f"📥 {method} {endpoint} desde {client_ip}")
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        execution_time = time.time() - start_time
        
        event_logger.log_api_call(endpoint, method, status_code, execution_time, client_ip)
        record_api_request(endpoint, method, status_code)
        
        return response
    except Exception as e:
        app_logger.error(f"❌ Error: {e}", exc_info=True)
        record_error("request_processing", "error")
        raise

# Analizadores
vader_analyzer = SentimentIntensityAnalyzer()

# Modelos Pydantic
class TextInput(BaseModel):
    text: str
    method: str = "hybrid"

    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('El texto no puede estar vacío')
        if len(v.strip()) < 2:
            raise ValueError('El texto debe tener al menos 2 caracteres')
        if len(v) > 1000:
            raise ValueError('El texto no puede exceder 1000 caracteres')
        return v.strip()

class AnalysisResponse(BaseModel):
    colors: list[str]
    polarity: float
    sentiment: str
    confidence: float
    method_used: str
    translated_text: str
    original_text: str
    intensity: str
    emotion_details: dict

ENHANCED_PALETTES = {
    "very_positive": {"emotion": "Alegría intensa", "description": "Colores vibrantes"},
    "positive": {"emotion": "Optimismo", "description": "Colores cálidos"},
    "slightly_positive": {"emotion": "Satisfacción", "description": "Colores suaves"},
    "neutral": {"emotion": "Equilibrio", "description": "Colores balanceados"},
    "slightly_negative": {"emotion": "Melancolía", "description": "Tonos grises"},
    "negative": {"emotion": "Tristeza", "description": "Colores oscuros"},
    "very_negative": {"emotion": "Angustia", "description": "Colores intensos oscuros"}
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funciones auxiliares
def translate_text(text: str, target_lang: str = 'en') -> str:
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        record_translation("auto", target_lang)
        return translated if translated else text
    except Exception as e:
        app_logger.warning(f"⚠️ Error traducción: {e}")
        return text

def analyze_with_textblob(text: str) -> tuple[float, float]:
    blob = TextBlob(text)
    return blob.sentiment.polarity, blob.sentiment.subjectivity

def analyze_with_vader(text: str) -> tuple[float, dict]:
    scores = vader_analyzer.polarity_scores(text)
    return scores['compound'], scores

def hybrid_analysis(text: str) -> tuple[float, float, dict]:
    tb_polarity, tb_subjectivity = analyze_with_textblob(text)
    vader_polarity, vader_scores = analyze_with_vader(text)
    combined_polarity = (vader_polarity * 0.6) + (tb_polarity * 0.4)
    agreement = 1 - abs(tb_polarity - vader_polarity) / 2
    confidence = max(0.3, agreement)
    
    analysis_details = {
        "textblob_polarity": round(tb_polarity, 3),
        "vader_compound": round(vader_polarity, 3),
        "agreement_score": round(agreement, 3)
    }
    return combined_polarity, confidence, analysis_details

def get_enhanced_sentiment(polarity: float, confidence: float = 1.0) -> tuple[str, str, dict]:
    intensity_factor = abs(polarity) * confidence
    
    if polarity > 0.6: sentiment_key = "very_positive"
    elif polarity > 0.3: sentiment_key = "positive"
    elif polarity > 0.05: sentiment_key = "slightly_positive"
    elif polarity < -0.6: sentiment_key = "very_negative"
    elif polarity < -0.3: sentiment_key = "negative"
    elif polarity < -0.05: sentiment_key = "slightly_negative"
    else: sentiment_key = "neutral"
    
    if intensity_factor > 0.7: intensity = "muy alta"
    elif intensity_factor > 0.4: intensity = "alta"
    elif intensity_factor > 0.2: intensity = "media"
    else: intensity = "baja"
    
    sentiment_label = sentiment_key.replace("_", " ")
    return sentiment_label, intensity, ENHANCED_PALETTES[sentiment_key]

def generate_advanced_colors(sentiment_key: str, confidence: float) -> dict:
    return AdvancedColorGenerator.generate_advanced_palette(sentiment_key, confidence)

def generate_dynamic_palette(polarity: float, confidence: float) -> list[str]:
    base_hue = np.interp(polarity, [-1, 1], [0, 120]) / 360.0
    base_saturation = np.interp(confidence, [0, 1], [0.45, 0.95])
    base_lightness = np.interp(abs(polarity), [0, 1], [0.9, 0.5])

    palette_hsl = [
        (base_hue, base_saturation, min(0.95, base_lightness + 0.15)),
        ((base_hue - 30/360.0) % 1.0, base_saturation, base_lightness),
        (base_hue, base_saturation, base_lightness),
        ((base_hue + 30/360.0) % 1.0, base_saturation, base_lightness),
        (base_hue, base_saturation, max(0.2, base_lightness - 0.15))
    ]

    palette_hex = []
    for h, s, l in palette_hsl:
        rgb = colorsys.hls_to_rgb(h, l, s)
        hex_color = f"#{''.join(f'{int(c * 255):02x}' for c in rgb)}"
        palette_hex.append(hex_color)
    return palette_hex

# ============================================================================
# ENDPOINTS DE AUTENTICACIÓN
# ============================================================================

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Registrar nuevo usuario con datos encriptados"""
    app_logger.info(f"📝 Registro de usuario: {user.username}")
    
    # Verificar si existe
    existing = db.query(models_auth.User).filter(
        (models_auth.User.username == user.username) | 
        (models_auth.User.email == user.email)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Usuario o email ya existe")
    
    # Crear usuario con datos encriptados
    db_user = models_auth.User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        phone=encrypt_data(user.phone) if user.phone else None,  # ← ENCRIPTADO
        address=encrypt_data(user.address) if user.address else None,  # ← ENCRIPTADO
        role=UserRole.USER
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    app_logger.info(f"✅ Usuario {user.username} registrado")
    return db_user

from fastapi import Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime


class LoginForm:
    def __init__(
        self,
        username: str = Form(...),
        password: str = Form(...),
        grant_type: str = Form(default="password")
    ):
        self.username = username
        self.password = password
        self.grant_type = grant_type


@app.post("/token", response_model=Token)
def login(form_data: LoginForm = Depends(), db: Session = Depends(get_db)):
    """Login con JWT"""
    app_logger.info(f"🔐 Login: {form_data.username}")
    
    user = db.query(models_auth.User).filter(
        models_auth.User.username == form_data.username
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        app_logger.warning(f"❌ Login fallido: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    app_logger.info(f"✅ Login exitoso: {user.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@app.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtener info del usuario actual (con datos desencriptados)"""
    user = db.query(models_auth.User).filter(
        models_auth.User.username == current_user["username"]
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # DESENCRIPTAR datos para mostrar
    if user.phone:
        user.phone = decrypt_data(user.phone)
    if user.address:
        user.address = decrypt_data(user.address)
    
    return user

# ============================================================================
# ENDPOINTS PRINCIPALES (CON AUTENTICACIÓN)
# ============================================================================

@app.get("/")
async def root():
    return {"message": "Emotion Color Palette API v2.0", "features": ["auth", "encryption"]}

@app.get("/health")
async def health():
    return {"status": "healthy", "security": "enabled"}

@app.get("/metrics")
async def get_metrics():
    metrics_text = metrics_exporter.get_metrics_text()
    return Response(content=metrics_text, media_type="text/plain")

@app.post("/analyze", response_model=AnalysisResponse)
def analyze_text(
    request: TextInput,
    current_user: dict = Depends(require_permission("create_palette")),  # ← REQUIERE AUTH
    db: Session = Depends(get_db)
):
    """Analizar texto (requiere autenticación)"""
    start_time = time.time()
    
    try:
        app_logger.info(f"🔍 Análisis por {current_user['username']}")
        
        original_text = request.text
        translated_text = translate_text(original_text)
        
        if request.method == "textblob":
            polarity, subjectivity = analyze_with_textblob(translated_text)
            confidence = 1 - subjectivity
            analysis_details = {"subjectivity": round(subjectivity, 3)}
        elif request.method == "vader":
            polarity, vader_scores = analyze_with_vader(translated_text)
            confidence = abs(polarity)
            analysis_details = {"vader_scores": vader_scores}
        else:
            polarity, confidence, analysis_details = hybrid_analysis(translated_text)
        
        sentiment_label, intensity, palette_info = get_enhanced_sentiment(polarity, confidence)
        
        try:
            palette_data = generate_advanced_colors(sentiment_label, confidence)
            dynamic_colors = palette_data["colors"]
            emotion_details = {
                "emotion": palette_data.get("emotion", palette_info["emotion"]),
                "description": palette_data.get("description", "Paleta generada"),
                "temperature": palette_data.get("temperature", "neutral"),
                "harmony": palette_data.get("harmony", "balanced"),
                "mood": palette_data.get("mood", "neutral"),
                "energy": palette_data.get("energy", "medium"),
                "color_meanings": palette_data.get("color_meanings", []),
                "analysis": analysis_details
            }
        except Exception:
            dynamic_colors = generate_dynamic_palette(polarity, confidence)
            emotion_details = {
                "emotion": palette_info["emotion"],
                "description": "Paleta de respaldo",
                "analysis": analysis_details
            }
        
        response_data = {
            "colors": dynamic_colors,
            "polarity": round(polarity, 3),
            "sentiment": sentiment_label,
            "confidence": round(confidence, 3),
            "method_used": request.method,
            "translated_text": translated_text,
            "original_text": original_text,
            "intensity": intensity,
            "emotion_details": emotion_details
        }
        
        # Guardar asociado al usuario
        try:
            user = db.query(models_auth.User).filter(
                models_auth.User.username == current_user["username"]
            ).first()
            
            db_palette = models_auth.PaletteWithUser(
                input_text=original_text,
                translated_text=translated_text,
                polarity=f"{polarity:.3f}",
                colors=",".join(dynamic_colors),
                analysis_method=request.method,
                confidence_score=str(confidence),
                sentiment_label=sentiment_label,
                intensity=intensity,
                emotion_type=emotion_details.get("emotion"),
                user_id=user.id
            )
            db.add(db_palette)
            db.commit()
            app_logger.info(f"💾 Paleta guardada (user: {user.id})")
        except Exception as e:
            app_logger.error(f"❌ Error BD: {e}")
        
        execution_time = time.time() - start_time
        record_palette_created(sentiment_label, request.method, polarity, confidence)
        event_logger.log_palette_created(
            original_text, sentiment_label, dynamic_colors,
            request.method, confidence, execution_time
        )
        
        return AnalysisResponse(**response_data)
        
    except ValueError as ve:
        record_error("validation", "warning")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        app_logger.error(f"❌ Error: {e}", exc_info=True)
        record_error("analysis", "critical")
        raise HTTPException(status_code=500, detail="Error interno")

@app.get("/gallery")
def get_gallery(
    current_user: dict = Depends(require_permission("view_palette")),  # ← REQUIERE AUTH
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Ver galería (solo paletas del usuario o todas si es admin)"""
    limit = min(limit, 100)
    
    if current_user["role"] == UserRole.ADMIN:
        palettes = db.query(models_auth.PaletteWithUser).order_by(
            models_auth.PaletteWithUser.created_at.desc()
        ).limit(limit).all()
    else:
        user = db.query(models_auth.User).filter(
            models_auth.User.username == current_user["username"]
        ).first()
        palettes = db.query(models_auth.PaletteWithUser).filter(
            models_auth.PaletteWithUser.user_id == user.id
        ).order_by(
            models_auth.PaletteWithUser.created_at.desc()
        ).limit(limit).all()
    
    return {"total": len(palettes), "palettes": [
        {
            "id": p.id,
            "input_text": p.input_text,
            "colors": p.colors,
            "sentiment_label": p.sentiment_label,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in palettes
    ]}

@app.delete("/palettes/{palette_id}")
def delete_palette(
    palette_id: int,
    current_user: dict = Depends(get_current_active_user),  # ← REQUIERE AUTH
    db: Session = Depends(get_db)
):
    """Eliminar paleta (solo propietario o admin)"""
    palette = db.query(models_auth.PaletteWithUser).filter(
        models_auth.PaletteWithUser.id == palette_id
    ).first()
    
    if not palette:
        raise HTTPException(status_code=404, detail="Paleta no encontrada")
    
    user = db.query(models_auth.User).filter(
        models_auth.User.username == current_user["username"]
    ).first()
    
    # Solo el dueño o admin puede eliminar
    if palette.user_id != user.id and current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Sin permiso")
    
    db.delete(palette)
    db.commit()
    
    record_palette_deleted("manual")
    event_logger.log_palette_deleted(palette_id, user_action=True)
    
    return {"message": "Paleta eliminada", "id": palette_id}

@app.get("/stats")
def get_stats(
    current_user: dict = Depends(require_permission("view_stats")),  # ← REQUIERE AUTH
    db: Session = Depends(get_db)
):
    """Estadísticas (requiere autenticación)"""
    total_palettes = db.query(models_auth.PaletteWithUser).count()
    total_users = db.query(models_auth.User).count()
    
    return {
        "total_palettes": total_palettes,
        "total_users": total_users,
        "api_version": "2.0.0",
        "security": "enabled"
    }

# ===== ADMIN ENDPOINTS =====
from typing import List

class UserRoleUpdate(BaseModel):
    role: str

class UserStatusUpdate(BaseModel):
    is_active: bool

class UserAdminResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str = None
    role: str
    is_active: bool
    created_at: str = None
    last_login: str = None
    class Config:
        from_attributes = True

@app.get("/users", response_model=List[UserAdminResponse])
async def list_all_users(current_user: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(models_auth.User).all()
    return [{
        "id": u.id,
        "username": u.username,
        "email": decrypt_data(u.email) if u.email else u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None
    } for u in users]

@app.put("/users/{user_id}/role")
async def update_user_role(user_id: int, role_update: UserRoleUpdate, current_user: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(models_auth.User).filter(models_auth.User.id == user_id).first()
    if not user: raise HTTPException(404, "Usuario no encontrado")
    if user.username == current_user["username"] and role_update.role != "admin":
        raise HTTPException(400, "No puedes quitarte tu rol de admin")
    user.role = role_update.role
    db.commit()
    return {"message": "Rol actualizado", "user_id": user_id, "new_role": role_update.role}

@app.put("/users/{user_id}/status")
async def update_user_status(user_id: int, status_update: UserStatusUpdate, current_user: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(models_auth.User).filter(models_auth.User.id == user_id).first()
    if not user: raise HTTPException(404, "Usuario no encontrado")
    if user.username == current_user["username"] and not status_update.is_active:
        raise HTTPException(400, "No puedes desactivarte a ti mismo")
    user.is_active = status_update.is_active
    db.commit()
    return {"message": "Estado actualizado", "user_id": user_id, "is_active": status_update.is_active}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)