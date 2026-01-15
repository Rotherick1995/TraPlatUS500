"""
Configuración del sistema.

Contiene configuraciones, constantes y parámetros del sistema.
"""

from .settings import (
    MT5_LOGIN,
    MT5_SERVER,
    MT5_PASSWORD,
    DEFAULT_SYMBOL,
    FALLBACK_SYMBOL,
    MT5_PATH,
    AUTO_CONNECT,
    MT5_ALTERNATIVE_PATHS
)

from .constants import (
    TimeFrame,
    OrderType as OrderTypeConst,
    PositionType,
    ConnectionStatus
)

__all__ = [
    'MT5_LOGIN',
    'MT5_SERVER',
    'MT5_PASSWORD',
    'DEFAULT_SYMBOL',
    'FALLBACK_SYMBOL',
    'MT5_PATH',
    'AUTO_CONNECT',
    'MT5_ALTERNATIVE_PATHS',
    'TimeFrame',
    'OrderTypeConst',
    'PositionType',
    'ConnectionStatus'
]