"""
Sistema de Monitoreo con Prometheus para Análisis Emocional a Color
Implementa métricas personalizadas y exportación para Prometheus
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from prometheus_client.exposition import start_http_server
import time
from functools import wraps
from typing import Callable
import psutil
import os

# ==========================================
# MÉTRICAS PERSONALIZADAS
# ==========================================

# Contadores
palettes_created_total = Counter(
    'palettes_created_total',
    'Total de paletas creadas',
    ['sentiment_type', 'analysis_method']
)

palettes_deleted_total = Counter(
    'palettes_deleted_total',
    'Total de paletas eliminadas',
    ['deletion_type']
)

api_requests_total = Counter(
    'api_requests_total',
    'Total de requests a la API',
    ['endpoint', 'method', 'status']
)

errors_total = Counter(
    'errors_total',
    'Total de errores',
    ['error_type', 'severity']
)

translations_total = Counter(
    'translations_total',
    'Total de textos traducidos',
    ['source_lang', 'target_lang']
)

# Histogramas
request_duration_seconds = Histogram(
    'request_duration_seconds',
    'Duración de requests HTTP',
    ['endpoint', 'method'],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

sentiment_analysis_duration_seconds = Histogram(
    'sentiment_analysis_duration_seconds',
    'Duración del análisis de sentimientos',
    ['method'],
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
)

color_generation_duration_seconds = Histogram(
    'color_generation_duration_seconds',
    'Duración de generación de paleta',
    ['harmony_type'],
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0)
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Duración de queries a la base de datos',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
)

sentiment_polarity = Histogram(
    'sentiment_polarity',
    'Distribución de polaridad de sentimientos',
    buckets=(-1.0, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1.0)
)

confidence_scores = Histogram(
    'confidence_scores',
    'Distribución de scores de confianza',
    buckets=(0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0)
)

# Gauges
active_database_connections = Gauge(
    'active_database_connections',
    'Conexiones activas a la base de datos'
)

total_palettes_in_db = Gauge(
    'total_palettes_in_db',
    'Total de paletas almacenadas en BD'
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Tamaño del caché en bytes'
)

system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'Uso de CPU del sistema'
)

system_memory_usage = Gauge(
    'system_memory_usage_bytes',
    'Uso de memoria del sistema'
)

system_disk_usage = Gauge(
    'system_disk_usage_percent',
    'Uso de disco del sistema',
    ['mount_point']
)

app_info = Info(
    'app_info',
    'Información de la aplicación'
)

# ==========================================
# DECORADORES PARA TRACKING AUTOMÁTICO
# ==========================================

def track_request_duration(endpoint: str, method: str):
    """Decorador para medir duración de requests"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start
                request_duration_seconds.labels(
                    endpoint=endpoint,
                    method=method
                ).observe(duration)
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start
                request_duration_seconds.labels(
                    endpoint=endpoint,
                    method=method
                ).observe(duration)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

def track_sentiment_analysis(method: str):
    """Decorador para medir análisis de sentimientos"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            sentiment_analysis_duration_seconds.labels(
                method=method
            ).observe(duration)
            
            if isinstance(result, tuple) and len(result) > 0:
                polarity = result[0]
                sentiment_polarity.observe(polarity)
            
            return result
        return wrapper
    return decorator

def track_db_operation(operation: str, table: str):
    """Decorador para medir operaciones de BD"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            db_query_duration_seconds.labels(
                operation=operation,
                table=table
            ).observe(duration)
            
            return result
        return wrapper
    return decorator

# ==========================================
# FUNCIONES HELPER
# ==========================================

def record_palette_created(sentiment_type: str, method: str, 
                          polarity: float, confidence: float):
    """Registrar creación de paleta"""
    palettes_created_total.labels(
        sentiment_type=sentiment_type,
        analysis_method=method
    ).inc()
    
    sentiment_polarity.observe(polarity)
    confidence_scores.observe(confidence)

def record_palette_deleted(deletion_type: str = "manual"):
    """Registrar eliminación de paleta"""
    palettes_deleted_total.labels(
        deletion_type=deletion_type
    ).inc()

def record_api_request(endpoint: str, method: str, status: int):
    """Registrar request a la API"""
    status_label = "2xx" if 200 <= status < 300 else \
                   "4xx" if 400 <= status < 500 else \
                   "5xx" if 500 <= status < 600 else "other"
    
    api_requests_total.labels(
        endpoint=endpoint,
        method=method,
        status=status_label
    ).inc()

def record_error(error_type: str, severity: str = "error"):
    """Registrar error"""
    errors_total.labels(
        error_type=error_type,
        severity=severity
    ).inc()

def record_translation(source_lang: str, target_lang: str):
    """Registrar traducción"""
    translations_total.labels(
        source_lang=source_lang,
        target_lang=target_lang
    ).inc()

def update_system_metrics():
    """Actualizar métricas del sistema"""
    cpu_percent = psutil.cpu_percent(interval=1)
    system_cpu_usage.set(cpu_percent)
    
    memory = psutil.virtual_memory()
    system_memory_usage.set(memory.used)
    
    disk = psutil.disk_usage('/')
    system_disk_usage.labels(mount_point='/').set(disk.percent)

def update_database_metrics(db_session):
    """Actualizar métricas de base de datos"""
    try:
        from models import Palette
        total = db_session.query(Palette).count()
        total_palettes_in_db.set(total)
    except Exception:
        pass

def set_app_info(version: str, python_version: str):
    """Establecer información de la aplicación"""
    app_info.info({
        'version': version,
        'python_version': python_version,
        'app_name': 'Emotion Color Palette API'
    })

# ==========================================
# EXPORTADOR PROMETHEUS
# ==========================================

class MetricsExporter:
    """Clase para exportar métricas a Prometheus"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self.server_started = False
    
    def start_server(self):
        """Iniciar servidor HTTP para métricas"""
        if not self.server_started:
            try:
                start_http_server(self.port)
                self.server_started = True
                print(f" Servidor de métricas Prometheus iniciado en puerto {self.port}")
                print(f"  Accede a http://localhost:{self.port}/metrics")
            except Exception as e:
                print(f"Error iniciando servidor de métricas: {e}")
    
    def get_metrics_text(self) -> str:
        """Obtener métricas en formato Prometheus"""
        return generate_latest(REGISTRY).decode('utf-8')

# Instancia global
metrics_exporter = MetricsExporter()