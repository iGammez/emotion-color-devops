#!/usr/bin/env python3
"""
Script para crear el usuario administrador
Ejecutar: python backend/crear_admin.py
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models_auth
from auth import get_password_hash

def crear_admin():
    """Crear usuario administrador en la base de datos"""
    
    print("🔧 Creando usuario administrador...")
    print("")
    
    # Crear tablas si no existen
    models_auth.Base.metadata.create_all(bind=engine)
    print("✓ Tablas verificadas")
    
    # Crear sesión
    db = SessionLocal()
    
    try:
        # Verificar si el admin ya existe
        admin_existente = db.query(models_auth.User).filter(
            models_auth.User.username == "admin"
        ).first()
        
        if admin_existente:
            print("⚠️  Usuario 'admin' ya existe")
            print(f"   Usuario: {admin_existente.username}")
            print(f"   Email: {admin_existente.email}")
            print(f"   Rol: {admin_existente.role}")
            print(f"   Activo: {admin_existente.is_active}")
            print("")
            
            # Preguntar si desea actualizar
            respuesta = input("¿Deseas actualizar la contraseña a 'admin123'? (s/n): ")
            if respuesta.lower() == 's':
                admin_existente.hashed_password = get_password_hash("admin123")
                admin_existente.role = "admin"
                admin_existente.is_active = True
                db.commit()
                print(" Contraseña actualizada exitosamente")
            else:
                print(" Operación cancelada")
            
        else:
            # Crear nuevo usuario admin
            print("Creando nuevo usuario admin...")
            
            admin = models_auth.User(
                username="admin",
                email="admin@emotion-color.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrador del Sistema",
                role="admin",
                is_active=True,
                phone=None,
                address=None
            )
            
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
            print("✅ Usuario administrador creado exitosamente")
            print("")
            print(f"   ID: {admin.id}")
            print(f"   Usuario: {admin.username}")
            print(f"   Email: {admin.email}")
            print(f"   Nombre: {admin.full_name}")
            print(f"   Rol: {admin.role}")
        
        print("")
        print("=" * 50)
        print("CREDENCIALES DE ADMINISTRADOR")
        print("=" * 50)
        print("")
        print("   Usuario:  admin")
        print("   Password: admin123")
        print("")
        print("Usa estas credenciales para iniciar sesión en:")
        print("   http://localhost:8081/login.html")
        print("")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

def listar_usuarios():
    """Listar todos los usuarios en la base de datos"""
    
    print("")
    print("=" * 50)
    print("USUARIOS EN LA BASE DE DATOS")
    print("=" * 50)
    print("")
    
    db = SessionLocal()
    
    try:
        usuarios = db.query(models_auth.User).all()
        
        if not usuarios:
            print("   No hay usuarios registrados")
        else:
            for user in usuarios:
                print(f"   • {user.username} ({user.role})")
                print(f"     Email: {user.email}")
                print(f"     Nombre: {user.full_name or 'N/A'}")
                print(f"     Activo: {'Sí' if user.is_active else 'No'}")
                print("")
    
    except Exception as e:
        print(f"❌ Error al listar usuarios: {e}")
    finally:
        db.close()

def verificar_login():
    """Verificar que el login funcione"""
    
    print("")
    print("=" * 50)
    print("VERIFICANDO LOGIN")
    print("=" * 50)
    print("")
    
    from auth import verify_password
    
    db = SessionLocal()
    
    try:
        admin = db.query(models_auth.User).filter(
            models_auth.User.username == "admin"
        ).first()
        
        if not admin:
            print(" Usuario 'admin' no encontrado")
            return False
        
        # Verificar contraseña
        if verify_password("admin123", admin.hashed_password):
            print("Login verificado correctamente")
            print("   Las credenciales admin/admin123 funcionan")
            return True
        else:
            print("   Contraseña incorrecta")
            print("   Ejecuta el script nuevamente para actualizar")
            return False
            
    except Exception as e:
        print(f" Error al verificar: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("")
    print("╔════════════════════════════════════════════╗")
    print("║   CREACIÓN DE USUARIO ADMINISTRADOR       ║")
    print("╚════════════════════════════════════════════╝")
    print("")
    
    # Crear admin
    if crear_admin():
        # Listar usuarios
        listar_usuarios()
        
        # Verificar login
        verificar_login()
        
        print("")
        print(" ¡Todo listo! Ahora puedes iniciar sesión")
        print("")
    else:
        print("")
        print(" Hubo un problema. Revisa los errores arriba.")
        print("")
        sys.exit(1)