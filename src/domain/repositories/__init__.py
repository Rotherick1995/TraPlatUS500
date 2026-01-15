"""
Repositorios del Dominio.

Interfaces abstractas para acceder a datos persistentes.
Sigue el principio de Inversión de Dependencias.
"""

from .abstract.market_data_repository import MarketDataRepository
from .abstract.order_repository import OrderRepository

__all__ = [
    'MarketDataRepository',
    'OrderRepository'
]