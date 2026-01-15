"""
Paquete principal de US500 Trading Platform.

Este paquete contiene toda la lógica de la plataforma de trading
para el índice US500 (S&P 500) con integración MetaTrader 5.
"""

__version__ = "1.0.0"
__author__ = "US500 Trading Platform Team"
__description__ = "Plataforma de trading profesional para US500 con MT5"

# Re-exportar componentes principales para acceso fácil
from src.config.settings import (
    MT5_LOGIN,
    MT5_SERVER,
    MT5_PASSWORD,
    DEFAULT_SYMBOL,
    FALLBACK_SYMBOL
)

from src.application.use_cases.connect_to_mt5 import create_connect_to_mt5_use_case
from src.application.use_cases.fetch_market_data import create_fetch_market_data_use_case

__all__ = [
    'MT5_LOGIN',
    'MT5_SERVER',
    'MT5_PASSWORD',
    'DEFAULT_SYMBOL',
    'FALLBACK_SYMBOL',
    'create_connect_to_mt5_use_case',
    'create_fetch_market_data_use_case'
]