"""
Endpoints adicionales para administración de usuarios
Agregar estos endpoints al main.py
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

# Importar desde los módulos existentes
from auth import get_current_admin
from database import get_db
import models_auth
from encryption import decrypt_data

# ============================================================================
# SCHEMAS PARA ADMIN
# ============================================================================

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

# ============================================================================
# ENDPOINTS DE ADMINISTRACIÓN (Agregar a main.py)
# ============================================================================

# @app.get("/users", response_model=List[UserAdminResponse])
async def list_all_users(
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Listar todos los usuarios (solo admin)
    Endpoint: GET /users
    """
    try:
        users = db.query(models_auth.User).all()
        
        # Desencriptar datos sensibles para admin
        users_response = []
        for user in users:
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": decrypt_data(user.email) if user.email else user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
            users_response.append(user_dict)
        
        return users_response
    
    except Exception as e:
        app_logger.error(f"Error listando usuarios: {e}")
        raise HTTPException(status_code=500, detail="Error al listar usuarios")


# @app.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Cambiar rol de un usuario (solo admin)
    Endpoint: PUT /users/{user_id}/role
    Body: {"role": "admin"|"user"|"viewer"}
    """
    try:
        # Verificar que el rol es válido
        valid_roles = ["admin", "user", "viewer"]
        if role_update.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}"
            )
        
        # Buscar usuario
        user = db.query(models_auth.User).filter(
            models_auth.User.id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # No permitir que un admin se quite su propio rol de admin
        if user.username == current_user["username"] and role_update.role != "admin":
            raise HTTPException(
                status_code=400,
                detail="No puedes quitarte tu propio rol de administrador"
            )
        
        # Actualizar rol
        user.role = role_update.role
        db.commit()
        
        app_logger.info(f"Admin {current_user['username']} cambió rol de {user.username} a {role_update.role}")
        
        return {
            "message": "Rol actualizado exitosamente",
            "user_id": user_id,
            "new_role": role_update.role
        }
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Error actualizando rol: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar rol")


# @app.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Activar/Desactivar usuario (solo admin)
    Endpoint: PUT /users/{user_id}/status
    Body: {"is_active": true|false}
    """
    try:
        # Buscar usuario
        user = db.query(models_auth.User).filter(
            models_auth.User.id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # No permitir que un admin se desactive a sí mismo
        if user.username == current_user["username"] and not status_update.is_active:
            raise HTTPException(
                status_code=400,
                detail="No puedes desactivar tu propia cuenta"
            )
        
        # Actualizar estado
        user.is_active = status_update.is_active
        db.commit()
        
        action = "activado" if status_update.is_active else "desactivado"
        app_logger.info(f"Admin {current_user['username']} {action} al usuario {user.username}")
        
        return {
            "message": f"Usuario {action} exitosamente",
            "user_id": user_id,
            "is_active": status_update.is_active
        }
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Error actualizando estado: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar estado")


# @app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Eliminar usuario (solo admin)
    Endpoint: DELETE /users/{user_id}
    """
    try:
        # Buscar usuario
        user = db.query(models_auth.User).filter(
            models_auth.User.id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # No permitir que un admin se elimine a sí mismo
        if user.username == current_user["username"]:
            raise HTTPException(
                status_code=400,
                detail="No puedes eliminar tu propia cuenta"
            )
        
        # Eliminar usuario
        db.delete(user)
        db.commit()
        
        app_logger.warning(f"Admin {current_user['username']} eliminó al usuario {user.username}")
        
        return {
            "message": "Usuario eliminado exitosamente",
            "user_id": user_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Error eliminando usuario: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar usuario")


# @app.get("/users/stats")
async def get_users_stats(
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de usuarios (solo admin)
    Endpoint: GET /users/stats
    """
    try:
        total_users = db.query(models_auth.User).count()
        total_admins = db.query(models_auth.User).filter(
            models_auth.User.role == "admin"
        ).count()
        total_regular = db.query(models_auth.User).filter(
            models_auth.User.role == "user"
        ).count()
        total_active = db.query(models_auth.User).filter(
            models_auth.User.is_active == True
        ).count()
        
        return {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_regular": total_regular,
            "total_active": total_active,
            "total_inactive": total_users - total_active
        }
    
    except Exception as e:
        app_logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas")
