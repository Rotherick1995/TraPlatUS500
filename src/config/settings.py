# src/config/settings.py

import os
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================================
# CREDENCIALES MT5
# ============================================================================

# Credenciales de la cuenta demo de MT5
MT5_LOGIN = 61454844
MT5_SERVER = "Pepperstone-Demo"
MT5_PASSWORD = "b;hsd6vetP"

# Configuración de conexión MT5
MT5_TIMEOUT = 10000  # Timeout en milisegundos (10 segundos)
MT5_POLLING_INTERVAL = 0.5  # Intervalo de polling para eventos
MT5_ENCODING = "utf-8"

# ============================================================================
# RUTAS DE MT5
# ============================================================================

# Ruta principal a MT5 (Windows)
MT5_PATH = "C:/Program Files/MetaTrader 5/terminal64.exe"

# Rutas alternativas para MT5
MT5_ALTERNATIVE_PATHS = [
    "C:/Program Files (x86)/MetaTrader 5/terminal64.exe",
    "C:/Program Files/MetaTrader 5/terminal.exe",
    "C:/Program Files (x86)/MetaTrader 5/terminal.exe",
]

# Configuración de conexión
MAX_CONNECTION_RETRIES = 3  # Número máximo de reintentos de conexión
CONNECTION_RETRY_DELAY = 2  # Segundos entre reintentos

# ============================================================================
# CONFIGURACIÓN BÁSICA
# ============================================================================
AUTO_CONNECT = True
# Símbolo principal
DEFAULT_SYMBOL = "US500"
FALLBACK_SYMBOL = "US500"
# Timeframes disponibles
TIMEFRAMES = {
    "1M": 1,      # 1 minuto
    "5M": 5,      # 5 minutos
    "15M": 15,    # 15 minutos
    "30M": 30,    # 30 minutos
    "1H": 60,     # 1 hora
    "4H": 240,    # 4 horas
    "1D": 1440,   # 1 día
    "1W": 10080,  # 1 semana
}

# Configuración de datos
DEFAULT_TIMEFRAME = "1H"
DEFAULT_DATA_COUNT = 100
MAX_DATA_COUNT = 10000  # NUEVO: Máximo de velas que se pueden cargar
MIN_DATA_COUNT = 10     # NUEVO: Mínimo de velas que se pueden cargar

# ============================================================================
# CONFIGURACIÓN DE TRADING
# ============================================================================

# Configuración de lotaje
DEFAULT_LOT_SIZE = 0.01
MIN_LOT_SIZE = 0.01
MAX_LOT_SIZE = 1.0
LOT_STEP = 0.01

# Stop Loss y Take Profit por defecto
DEFAULT_STOP_LOSS_PIPS = 50
DEFAULT_TAKE_PROFIT_PIPS = 100

# Slippage permitido
DEFAULT_SLIPPAGE = 3  # pips

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

# Nivel de logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Formato del log
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-d %H:%M:%S"

# ============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ============================================================================

# Tamaños de ventana
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
CHART_HEIGHT_RATIO = 0.7  # 70% para el gráfico, 30% para controles

# Actualización de datos en tiempo real
REFRESH_INTERVAL = 1000  # ms (1 segundo)

# Colores de la interfaz (tema oscuro)
UI_COLORS = {
    "background": "#1e1e1e",
    "foreground": "#ffffff",
    "primary": "#007acc",
    "secondary": "#2d2d30",
    "success": "#4CAF50",
    "danger": "#F44336",
    "warning": "#FF9800",
    "info": "#2196F3",
    "bullish": "#4CAF50",  # NUEVO: Color para velas alcistas
    "bearish": "#F44336",  # NUEVO: Color para velas bajistas
}