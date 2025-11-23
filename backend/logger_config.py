"""
Sistema de Logging Estructurado para Análisis Emocional a Color
Implementa logging en JSON y texto, con rotación automática
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from pathlib import Path
import traceback
from typing import Any, Dict

# Crear directorio de logs
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Formateador para logs en JSON estructurado"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Agregar información adicional si existe
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'sentiment'):
            log_data['sentiment'] = record.sentiment
        if hasattr(record, 'colors_count'):
            log_data['colors_count'] = record.colors_count
        if hasattr(record, 'execution_time'):
            log_data['execution_time'] = record.execution_time
        
        # Agregar excepción si existe
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False)

class ColoredFormatter(logging.Formatter):
    """Formateador con colores para consola"""
    
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logging(app_name: str = "emotion_color_api") -> logging.Logger:
    """
    Configurar sistema de logging con múltiples handlers
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    
    # Evitar duplicación de handlers
    if logger.handlers:
        return logger
    
    # 1. Handler para consola (con colores)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 2. Handler para archivo JSON (estructurado)
    json_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "app_structured.json",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    json_handler.setLevel(logging.DEBUG)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    # 3. Handler para archivo de texto (legible)
    text_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    text_handler.setLevel(logging.INFO)
    text_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    text_handler.setFormatter(text_formatter)
    logger.addHandler(text_handler)
    
    # 4. Handler para errores críticos (separado)
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "errors.log",
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(text_formatter)
    logger.addHandler(error_handler)
    
    logger.info(f"Sistema de logging inicializado para {app_name}")
    return logger

class MetricsFilter(logging.Filter):
    """Filtro para separar logs de métricas"""
    def filter(self, record: logging.LogRecord) -> bool:
        return hasattr(record, 'metric_type')

class EventLogger:
    """Clase helper para logging de eventos específicos"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_palette_created(self, text: str, sentiment: str, colors: list, 
                           method: str, confidence: float, execution_time: float):
        """Log cuando se crea una paleta"""
        extra = {
            'metric_type': 'palette_created',
            'sentiment': sentiment,
            'colors_count': len(colors),
            'method': method,
            'confidence': confidence,
            'execution_time': execution_time,
            'text_length': len(text)
        }
        self.logger.info(
            f"Paleta creada | Sentimiento: {sentiment} | "
            f"Método: {method} | Tiempo: {execution_time:.3f}s",
            extra=extra
        )
    
    def log_palette_deleted(self, palette_id: int, user_action: bool = True):
        """Log cuando se elimina una paleta"""
        extra = {
            'metric_type': 'palette_deleted',
            'palette_id': palette_id,
            'user_action': user_action
        }
        self.logger.info(
            f"Paleta eliminada | ID: {palette_id} | "
            f"Acción usuario: {user_action}",
            extra=extra
        )
    
    def log_gallery_viewed(self, total_palettes: int, execution_time: float):
        """Log cuando se visualiza la galería"""
        extra = {
            'metric_type': 'gallery_viewed',
            'total_palettes': total_palettes,
            'execution_time': execution_time
        }
        self.logger.info(
            f"Galería visualizada | Total: {total_palettes} | "
            f"Tiempo: {execution_time:.3f}s",
            extra=extra
        )
    
    def log_error(self, error_type: str, error_message: str, 
                  context: Dict[str, Any] = None):
        """Log de errores con contexto"""
        extra = {
            'metric_type': 'error',
            'error_type': error_type,
            'context': context or {}
        }
        self.logger.error(
            f"Error: {error_type} | {error_message}",
            extra=extra,
            exc_info=True
        )
    
    def log_api_call(self, endpoint: str, method: str, status_code: int,
                     execution_time: float, client_ip: str = None):
        """Log de llamadas a la API"""
        extra = {
            'metric_type': 'api_call',
            'endpoint': endpoint,
            'http_method': method,
            'status_code': status_code,
            'execution_time': execution_time,
            'client_ip': client_ip
        }
        self.logger.info(
            f"API: {method} {endpoint} | Status: {status_code} | "
            f"Tiempo: {execution_time:.3f}s",
            extra=extra
        )
    
    def log_database_operation(self, operation: str, table: str, 
                              records_affected: int, execution_time: float):
        """Log de operaciones de base de datos"""
        extra = {
            'metric_type': 'db_operation',
            'operation': operation,
            'table': table,
            'records_affected': records_affected,
            'execution_time': execution_time
        }
        self.logger.debug(
            f"DB: {operation} en {table} | "
            f"Registros: {records_affected} | Tiempo: {execution_time:.3f}s",
            extra=extra
        )
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              unit: str = "ms"):
        """Log de métricas de rendimiento"""
        extra = {
            'metric_type': 'performance',
            'metric_name': metric_name,
            'value': value,
            'unit': unit
        }
        self.logger.info(
            f"Métrica: {metric_name} = {value} {unit}",
            extra=extra
        )

# Exportar logger configurado
app_logger = setup_logging()
event_logger = EventLogger(app_logger)