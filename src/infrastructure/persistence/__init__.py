"""
Persistencia de Datos.

Implementaciones concretas de repositorios para
diferentes fuentes de datos (MT5, bases de datos, etc.)
"""

from src.infrastructure.persistence import mt5

__all__ = [
    'mt5'
]