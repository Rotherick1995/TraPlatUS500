"""
Interfaces Abstractas de Repositorios.

Define los contratos que deben implementar las
concreciones de infraestructura.
"""

from .market_data_repository import MarketDataRepository
from .order_repository import OrderRepository

__all__ = [
    'MarketDataRepository',
    'OrderRepository'
]