"""
Capa del Dominio - Lógica de negocio core.

Contiene las entidades, value objects, y interfaces del dominio
que representan los conceptos fundamentales del trading.
"""

# Importar módulos principales
from src.domain import entities
from src.domain import repositories
from src.domain import value_objects

# Re-exportar clases principales
from src.domain.entities.candle import Candle
from src.domain.entities.position import Position, PositionType, PositionStatus
from src.domain.entities.order import Order, OrderType, OrderStatus, OrderFactory

# Interfaces de repositorios
from src.domain.repositories.abstract.market_data_repository import MarketDataRepository
from src.domain.repositories.abstract.order_repository import OrderRepository

__all__ = [
    # Módulos
    'entities',
    'repositories',
    'value_objects',
    
    # Entidades
    'Candle',
    'Position',
    'PositionType',
    'PositionStatus',
    'Order',
    'OrderType',
    'OrderStatus',
    'OrderFactory',
    
    # Repositorios
    'MarketDataRepository',
    'OrderRepository'
]