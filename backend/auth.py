"""
Sistema de Autenticación y Autorización
Implementa JWT, roles de usuario y control de acceso
"""

from datetime import datetime, timedelta
from typing import Optional, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os

# Configuración de seguridad
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secreto-cambiar-en-produccion")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Contexto para hasheo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 para obtener el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Roles disponibles
class UserRole:
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

# Permisos por rol
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "create_palette",
        "delete_palette",
        "view_palette",
        "delete_all_palettes",
        "view_stats",
        "manage_users"
    ],
    UserRole.USER: [
        "create_palette",
        "delete_own_palette",
        "view_palette",
        "view_stats"
    ],
    UserRole.VIEWER: [
        "view_palette",
        "view_stats"
    ]
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashear contraseña"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crear token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """Decodificar token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Obtener usuario actual desde el token"""
    payload = decode_token(token)
    username: str = payload.get("sub")
    role: str = payload.get("role")
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar las credenciales",
        )
    
    return {"username": username, "role": role}

def check_permission(user: dict, permission: str) -> bool:
    """Verificar si el usuario tiene un permiso específico"""
    role = user.get("role", UserRole.VIEWER)
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions

def require_permission(permission: str):
    """Decorador para requerir un permiso específico"""
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        if not check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso para: {permission}"
            )
        return current_user
    return permission_checker

# Dependencias comunes
async def get_current_admin(current_user: dict = Depends(get_current_user)):
    """Verificar que el usuario sea admin"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden acceder"
        )
    return current_user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Obtener usuario activo (cualquier rol autenticado)"""
    return current_user