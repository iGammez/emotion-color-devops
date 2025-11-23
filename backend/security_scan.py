#!/usr/bin/env python3
"""
Script de Análisis de Seguridad Automático
Escanea vulnerabilidades con Safety, Bandit y genera reporte
"""

import subprocess
import json
from datetime import datetime
import os

print("🔒 INICIANDO ANÁLISIS DE SEGURIDAD")
print("=" * 70)

# Crear directorio de reportes
os.makedirs("security_reports", exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report_file = f"security_reports/security_report_{timestamp}.txt"

vulnerabilities = []

# ============================================================================
# 1. ANÁLISIS CON SAFETY (Dependencias vulnerables)
# ============================================================================
print("\n📦 1. Analizando dependencias con Safety...")
try:
    result = subprocess.run(
        ["safety", "check", "--json", "-r", "backend/requirements.txt"],
        capture_output=True,
        text=True
    )
    
    safety_data = json.loads(result.stdout) if result.stdout else []
    
    print(f"   ✅ Análisis completado: {len(safety_data)} vulnerabilidades encontradas")
    
    for vuln in safety_data:
        vulnerabilities.append({
            "tipo": "Dependencia Vulnerable",
            "severidad": "Alta",
            "paquete": vuln.get("package", "Unknown"),
            "version": vuln.get("installed_version", "Unknown"),
            "vulnerabilidad": vuln.get("vulnerability", "Unknown"),
            "recomendacion": f"Actualizar a versión {vuln.get('fixed_in', 'latest')}"
        })
        
except Exception as e:
    print(f"   ⚠️  Error ejecutando Safety: {e}")
    vulnerabilities.append({
        "tipo": "Error de Análisis",
        "severidad": "Info",
        "detalle": f"No se pudo ejecutar Safety: {e}"
    })

# ============================================================================
# 2. ANÁLISIS CON BANDIT (Código fuente)
# ============================================================================
print("\n🔍 2. Analizando código fuente con Bandit...")
try:
    result = subprocess.run(
        ["bandit", "-r", "backend/", "-f", "json", "-o", "security_reports/bandit_temp.json"],
        capture_output=True,
        text=True
    )
    
    if os.path.exists("security_reports/bandit_temp.json"):
        with open("security_reports/bandit_temp.json", "r") as f:
            bandit_data = json.load(f)
        
        issues = bandit_data.get("results", [])
        print(f"   ✅ Análisis completado: {len(issues)} problemas encontrados")
        
        for issue in issues:
            vulnerabilities.append({
                "tipo": "Problema en Código",
                "severidad": issue.get("issue_severity", "Medium"),
                "archivo": issue.get("filename", "Unknown"),
                "linea": issue.get("line_number", "N/A"),
                "problema": issue.get("issue_text", "Unknown"),
                "confianza": issue.get("issue_confidence", "Medium"),
                "recomendacion": "Revisar y corregir según mejores prácticas"
            })
    else:
        print("   ℹ️  No se generó reporte de Bandit")
        
except Exception as e:
    print(f"   ⚠️  Error ejecutando Bandit: {e}")

# ============================================================================
# 3. VERIFICACIONES MANUALES
# ============================================================================
print("\n🔐 3. Verificaciones de seguridad manuales...")

# Verificar archivos de configuración sensibles
sensitive_files = [
    ".env",
    "backend/.env",
    "database.db",
    "data/palettes.db"
]

for file in sensitive_files:
    if os.path.exists(file):
        vulnerabilities.append({
            "tipo": "Archivo Sensible Detectado",
            "severidad": "Media",
            "archivo": file,
            "problema": "Archivo con datos sensibles en el repositorio",
            "recomendacion": f"Asegurar que {file} esté en .gitignore y no se suba al repositorio"
        })

# Verificar .gitignore
if not os.path.exists(".gitignore"):
    vulnerabilities.append({
        "tipo": "Configuración Faltante",
        "severidad": "Alta",
        "problema": "No existe archivo .gitignore",
        "recomendacion": "Crear .gitignore para excluir archivos sensibles"
    })

# Verificar SECRET_KEY
if os.path.exists("backend/main.py"):
    with open("backend/main.py", "r", encoding="utf-8") as f:
        content = f.read()
        if "SECRET_KEY" in content and ("123" in content or "secret" in content.lower()):
            vulnerabilities.append({
                "tipo": "Credencial Insegura",
                "severidad": "Crítica",
                "archivo": "backend/main.py",
                "problema": "SECRET_KEY débil o hardcodeada detectada",
                "recomendacion": "Usar variables de entorno y claves fuertes"
            })

print(f"   ✅ Verificaciones completadas")

# ============================================================================
# 4. GENERAR REPORTE
# ============================================================================
print(f"\n📄 4. Generando reporte en {report_file}...")

with open(report_file, "w", encoding="utf-8") as f:
    f.write("=" * 70 + "\n")
    f.write("REPORTE DE ANÁLISIS DE SEGURIDAD\n")
    f.write("=" * 70 + "\n")
    f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Proyecto: Análisis Emocional a Color\n")
    f.write(f"Total de vulnerabilidades encontradas: {len(vulnerabilities)}\n")
    f.write("=" * 70 + "\n\n")
    
    # Agrupar por severidad
    criticas = [v for v in vulnerabilities if v.get("severidad") == "Crítica"]
    altas = [v for v in vulnerabilities if v.get("severidad") in ["Alta", "High"]]
    medias = [v for v in vulnerabilities if v.get("severidad") in ["Media", "Medium"]]
    bajas = [v for v in vulnerabilities if v.get("severidad") in ["Baja", "Low", "Info"]]
    
    f.write(f"RESUMEN POR SEVERIDAD:\n")
    f.write(f"  🔴 Críticas: {len(criticas)}\n")
    f.write(f"  🟠 Altas: {len(altas)}\n")
    f.write(f"  🟡 Medias: {len(medias)}\n")
    f.write(f"  🟢 Bajas/Info: {len(bajas)}\n")
    f.write("\n" + "=" * 70 + "\n\n")
    
    # Detalles de vulnerabilidades
    for i, vuln in enumerate(vulnerabilities, 1):
        f.write(f"VULNERABILIDAD #{i}\n")
        f.write("-" * 70 + "\n")
        for key, value in vuln.items():
            f.write(f"{key.capitalize()}: {value}\n")
        f.write("\n")
    
    # Recomendaciones generales
    f.write("=" * 70 + "\n")
    f.write("RECOMENDACIONES GENERALES:\n")
    f.write("=" * 70 + "\n")
    f.write("1. Mantener todas las dependencias actualizadas\n")
    f.write("2. Usar variables de entorno para credenciales\n")
    f.write("3. Implementar autenticación y autorización\n")
    f.write("4. Encriptar datos sensibles en la base de datos\n")
    f.write("5. Configurar HTTPS en producción\n")
    f.write("6. Implementar rate limiting en la API\n")
    f.write("7. Realizar análisis de seguridad periódicos\n")
    f.write("8. Mantener logs de seguridad\n")
    f.write("9. Implementar validación de entrada estricta\n")
    f.write("10. Configurar CORS apropiadamente\n")

print(f"   ✅ Reporte generado exitosamente")

# ============================================================================
# 5. RESUMEN EN CONSOLA
# ============================================================================
print("\n" + "=" * 70)
print("📊 RESUMEN DEL ANÁLISIS")
print("=" * 70)
print(f"Total de vulnerabilidades: {len(vulnerabilities)}")
print(f"  🔴 Críticas: {len(criticas)}")
print(f"  🟠 Altas: {len(altas)}")
print(f"  🟡 Medias: {len(medias)}")
print(f"  🟢 Bajas/Info: {len(bajas)}")
print("\n📄 Reporte completo guardado en:")
print(f"   {report_file}")
print("\n💡 Siguiente paso:")
print("   Revisar el reporte y aplicar las recomendaciones de seguridad")
print("=" * 70)