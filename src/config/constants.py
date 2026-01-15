# src/config/constants.py

from enum import Enum, IntEnum
from typing import Dict

# ============================================================================
# ENUMS PARA EL DOMINIO
# ============================================================================

class TimeFrame(Enum):
    """Timeframes disponibles para gráficos"""
    M1 = "1M"
    M5 = "5M"
    M15 = "15M"
    M30 = "30M"
    H1 = "1H"
    H4 = "4H"
    D1 = "1D"
    W1 = "1W"

class OrderType(Enum):
    """Tipos de órdenes"""
    MARKET_BUY = "MARKET_BUY"
    MARKET_SELL = "MARKET_SELL"
    LIMIT_BUY = "LIMIT_BUY"
    LIMIT_SELL = "LIMIT_SELL"
    STOP_BUY = "STOP_BUY"
    STOP_SELL = "STOP_SELL"

class OrderStatus(Enum):
    """Estados de una orden"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TradeDirection(Enum):
    """Dirección de una operación"""
    BUY = "BUY"
    SELL = "SELL"

# AÑADIR PositionType AQUÍ
class PositionType(Enum):
    """Tipos de posición (BUY/SELL)"""
    BUY = "BUY"
    SELL = "SELL"
    
    def __str__(self):
        return self.value
    
    @property
    def is_buy(self):
        return self == PositionType.BUY
    
    @property
    def is_sell(self):
        return self == PositionType.SELL

class ConnectionStatus(Enum):
    """Estados de conexión MT5"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
    RECONNECTING = "RECONNECTING"

class DataQuality(Enum):
    """Calidad de los datos obtenidos"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    INSUFFICIENT = "INSUFFICIENT"

# ============================================================================
# CONSTANTES NUMÉRICAS MT5
# ============================================================================

# MT5 Timeframes
MT5_TIMEFRAME_M1 = 1          # 1 minute
MT5_TIMEFRAME_M2 = 2          # 2 minutes
MT5_TIMEFRAME_M3 = 3          # 3 minutes
MT5_TIMEFRAME_M4 = 4          # 4 minutes
MT5_TIMEFRAME_M5 = 5          # 5 minutes
MT5_TIMEFRAME_M6 = 6          # 6 minutes
MT5_TIMEFRAME_M10 = 10        # 10 minutes
MT5_TIMEFRAME_M12 = 12        # 12 minutes
MT5_TIMEFRAME_M15 = 15        # 15 minutes
MT5_TIMEFRAME_M20 = 20        # 20 minutes
MT5_TIMEFRAME_M30 = 30        # 30 minutes
MT5_TIMEFRAME_H1 = 60         # 1 hour
MT5_TIMEFRAME_H2 = 120        # 2 hours
MT5_TIMEFRAME_H3 = 180        # 3 hours
MT5_TIMEFRAME_H4 = 240        # 4 hours
MT5_TIMEFRAME_H6 = 360        # 6 hours
MT5_TIMEFRAME_H8 = 480        # 8 hours
MT5_TIMEFRAME_H12 = 720       # 12 hours
MT5_TIMEFRAME_D1 = 1440       # 1 day
MT5_TIMEFRAME_W1 = 10080      # 1 week
MT5_TIMEFRAME_MN1 = 43200     # 1 month

# MT5 Order Types
MT5_ORDER_TYPE_BUY = 0        # Market Buy order
MT5_ORDER_TYPE_SELL = 1       # Market Sell order
MT5_ORDER_TYPE_BUY_LIMIT = 2  # Buy Limit pending order
MT5_ORDER_TYPE_SELL_LIMIT = 3 # Sell Limit pending order
MT5_ORDER_TYPE_BUY_STOP = 4   # Buy Stop pending order
MT5_ORDER_TYPE_SELL_STOP = 5  # Sell Stop pending order

# MT5 Order Filling Types
MT5_ORDER_FILLING_FOK = 0     # Fill or Kill
MT5_ORDER_FILLING_IOC = 1     # Immediate or Cancel
MT5_ORDER_FILLING_RETURN = 2  # Return order to the queue

# MT5 Order Time Types
MT5_ORDER_TIME_GTC = 0        # Good till cancelled
MT5_ORDER_TIME_DAY = 1        # Good till the end of the day
MT5_ORDER_TIME_SPECIFIED = 2  # Good till specified date
MT5_ORDER_TIME_SPECIFIED_DAY = 3 # Good till specified day

# MT5 Trade Actions
MT5_TRADE_ACTION_DEAL = 1     # Place a trade order
MT5_TRADE_ACTION_PENDING = 2  # Place a pending order
MT5_TRADE_ACTION_SLTP = 3     # Modify Stop Loss and Take Profit
MT5_TRADE_ACTION_MODIFY = 4   # Modify pending order
MT5_TRADE_ACTION_REMOVE = 5   # Remove pending order
MT5_TRADE_ACTION_CLOSE_BY = 6 # Close a position by an opposite one

# ============================================================================
# MAPEOS Y CONVERSIONES
# ============================================================================

# Conversión de timeframes propios a MT5
TIMEFRAME_TO_MT5: Dict[str, int] = {
    "1M": MT5_TIMEFRAME_M1,
    "5M": MT5_TIMEFRAME_M5,
    "15M": MT5_TIMEFRAME_M15,
    "30M": MT5_TIMEFRAME_M30,
    "1H": MT5_TIMEFRAME_H1,
    "4H": MT5_TIMEFRAME_H4,
    "1D": MT5_TIMEFRAME_D1,
    "1W": MT5_TIMEFRAME_W1,
}

# Conversión inversa MT5 a timeframes propios
MT5_TO_TIMEFRAME: Dict[int, str] = {v: k for k, v in TIMEFRAME_TO_MT5.items()}

# Conversión de tipos de orden propios a MT5
ORDER_TYPE_TO_MT5: Dict[str, int] = {
    "MARKET_BUY": MT5_ORDER_TYPE_BUY,
    "MARKET_SELL": MT5_ORDER_TYPE_SELL,
    "LIMIT_BUY": MT5_ORDER_TYPE_BUY_LIMIT,
    "LIMIT_SELL": MT5_ORDER_TYPE_SELL_LIMIT,
    "STOP_BUY": MT5_ORDER_TYPE_BUY_STOP,
    "STOP_SELL": MT5_ORDER_TYPE_SELL_STOP,
}

# Conversión inversa MT5 a tipos de orden propios
MT5_TO_ORDER_TYPE: Dict[int, str] = {v: k for k, v in ORDER_TYPE_TO_MT5.items()}

# ============================================================================
# CONSTANTES DE OPERACIÓN Y TRADING
# ============================================================================

# Acciones de trading
class TradeAction(Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"

# Métodos de cálculo de tamaño de posición
class PositionSizeMethod(Enum):
    FIXED = "FIXED"           # Tamaño fijo
    PERCENTAGE = "PERCENTAGE" # Porcentaje del capital
    RISK_BASED = "RISK_BASED" # Basado en riesgo y stop loss

# Tipos de indicadores
class IndicatorType(Enum):
    TREND = "TREND"           # Indicadores de tendencia
    MOMENTUM = "MOMENTUM"     # Indicadores de momento
    VOLATILITY = "VOLATILITY" # Indicadores de volatilidad
    VOLUME = "VOLUME"         # Indicadores de volumen

# ============================================================================
# CÓDIGOS DE ERROR MT5
# ============================================================================

MT5_ERROR_CODES = {
    # Éxitos
    10009: "TRADE_RETCODE_DONE",
    10010: "TRADE_RETCODE_DONE_PARTIAL",
    10011: "TRADE_RETCODE_ERROR",
    10012: "TRADE_RETCODE_TIMEOUT",
    10013: "TRADE_RETCODE_INVALID",
    10014: "TRADE_RETCODE_INVALID_VOLUME",
    10015: "TRADE_RETCODE_INVALID_PRICE",
    10016: "TRADE_RETCODE_INVALID_STOPS",
    10017: "TRADE_RETCODE_TRADE_DISABLED",
    10018: "TRADE_RETCODE_MARKET_CLOSED",
    10019: "TRADE_RETCODE_NO_MONEY",
    10020: "TRADE_RETCODE_PRICE_CHANGED",
    10021: "TRADE_RETCODE_PRICE_OFF",
    10022: "TRADE_RETCODE_INVALID_EXPIRATION",
    10023: "TRADE_RETCODE_ORDER_CHANGED",
    10024: "TRADE_RETCODE_TOO_MANY_REQUESTS",
    10025: "TRADE_RETCODE_NO_CHANGES",
    10026: "TRADE_RETCODE_SERVER_DISABLES_AT",
    10027: "TRADE_RETCODE_CLIENT_DISABLES_AT",
    10028: "TRADE_RETCODE_LOCKED",
    10029: "TRADE_RETCODE_FROZEN",
    10030: "TRADE_RETCODE_INVALID_FILL",
    10031: "TRADE_RETCODE_CONNECTION",
    10032: "TRADE_RETCODE_ONLY_REAL",
    10033: "TRADE_RETCODE_LIMIT_ORDERS",
    10034: "TRADE_RETCODE_LIMIT_VOLUME",
    10035: "TRADE_RETCODE_INVALID_ORDER",
    10036: "TRADE_RETCODE_POSITION_CLOSED",
    10038: "TRADE_RETCODE_INVALID_CLOSE_VOLUME",
    10039: "TRADE_RETCODE_CLOSE_ORDER_EXIST",
    10040: "TRADE_RETCODE_LIMIT_POSITIONS",
    10041: "TRADE_RETCODE_REJECT",
    10042: "TRADE_RETCODE_LONG_ONLY",
    10043: "TRADE_RETCODE_SHORT_ONLY",
    10044: "TRADE_RETCODE_CLOSE_ONLY",
    10045: "TRADE_RETCODE_FIFO_CLOSE",
}

# Errores generales MT5
MT5_GENERAL_ERRORS = {
    1: "RES_S_OK",
    -1: "RES_E_FAIL",
    -2: "RES_E_INVALID_PARAMS",
}

# ============================================================================
# VALORES POR DEFECTO
# ============================================================================

# Valores por defecto para órdenes
DEFAULT_ORDER_VALUES = {
    "volume": 0.01,
    "slippage": 10,
    "magic": 123456,
    "comment": "Python MT5 Order",
    "type_time": MT5_ORDER_TIME_GTC,
    "type_filling": MT5_ORDER_FILLING_RETURN,
}

# Límites de trading
TRADING_LIMITS = {
    "max_positions": 100,
    "max_orders": 100,
    "max_volume": 100.0,
    "min_volume": 0.01,
    "volume_step": 0.01,
}

# ============================================================================
# CONSTANTES DE CACHE
# ============================================================================

CACHE_CONFIG = {
    "max_size": 1000,          # Máximo de elementos en cache
    "ttl": 300,                # Time To Live en segundos (5 minutos)
    "cleanup_interval": 60,    # Intervalo de limpieza en segundos
}

# ============================================================================
# CONSTANTES DE INTERFAZ
# ============================================================================

# Colores para la interfaz
UI_COLORS = {
    "background": "#1e1e1e",
    "foreground": "#ffffff",
    "primary": "#007acc",
    "secondary": "#2d2d30",
    "success": "#4CAF50",
    "danger": "#F44336",
    "warning": "#FF9800",
    "info": "#2196F3",
    "buy": "#4CAF50",
    "sell": "#F44336",
    "profit": "#4CAF50",
    "loss": "#F44336",
}

# Iconos para estados
UI_ICONS = {
    "connected": "✅",
    "disconnected": "❌",
    "connecting": "🔄",
    "error": "⚠️",
    "buy": "🔼",
    "sell": "🔽",
    "info": "ℹ️",
    "warning": "⚠️",
    "success": "✅",
}

# ============================================================================
# MENSAJES DEL SISTEMA
# ============================================================================

SYSTEM_MESSAGES = {
    "mt5_initialized": "MT5 inicializado correctamente",
    "mt5_login_success": "Login exitoso en cuenta {login}",
    "mt5_login_failed": "Error de login: {error}",
    "mt5_not_initialized": "MT5 no está inicializado",
    "connection_success": "Conexión establecida con MT5",
    "connection_failed": "Error de conexión con MT5",
    "disconnected": "Desconectado de MT5",
    "order_sent": "Orden enviada: {ticket}",
    "order_failed": "Error al enviar orden: {error}",
    "position_opened": "Posición abierta: {ticket}",
    "position_closed": "Posición cerrada: {ticket}",
    "data_loaded": "Datos cargados: {count} velas",
    "data_error": "Error al cargar datos: {error}",
}

# ============================================================================
# CONFIGURACIONES POR DEFECTO
# ============================================================================

DEFAULT_CONFIG = {
    "symbol": "US500",
    "timeframe": "1H",
    "bars_count": 100,
    "auto_refresh": True,
    "refresh_interval": 5,
    "show_volume": True,
    "show_indicators": True,
    "theme": "dark",
    "language": "es",
}

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_mt5_timeframe(timeframe_str: str) -> int:
    """Convierte un timeframe string a constante MT5"""
    return TIMEFRAME_TO_MT5.get(timeframe_str.upper(), MT5_TIMEFRAME_H1)

def get_string_timeframe(mt5_timeframe: int) -> str:
    """Convierte una constante MT5 a timeframe string"""
    return MT5_TO_TIMEFRAME.get(mt5_timeframe, "1H")

def get_order_type_string(mt5_order_type: int) -> str:
    """Convierte tipo de orden MT5 a string"""
    return MT5_TO_ORDER_TYPE.get(mt5_order_type, "MARKET_BUY")

def get_mt5_order_type(order_type_str: str) -> int:
    """Convierte string de tipo de orden a constante MT5"""
    return ORDER_TYPE_TO_MT5.get(order_type_str.upper(), MT5_ORDER_TYPE_BUY)

def error_code_to_string(error_code: int) -> str:
    """Convierte código de error MT5 a mensaje legible"""
    if error_code in MT5_ERROR_CODES:
        return MT5_ERROR_CODES[error_code]
    elif error_code in MT5_GENERAL_ERRORS:
        return MT5_GENERAL_ERRORS[error_code]
    else:
        return f"UNKNOWN_ERROR_{error_code}"