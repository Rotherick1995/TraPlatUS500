# src/domain/repositories/abstract/market_data_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from src.domain.entities.candle import Candle


class MarketDataRepository(ABC):
    """Interfaz abstracta para repositorios de datos de mercado."""
    
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, count: int = None,
                           start_date: datetime = None, end_date: datetime = None) -> Tuple[Optional[List[Candle]], Any]:
        """
        Obtiene datos históricos de mercado.
        
        Args:
            symbol: Símbolo a consultar.
            timeframe: Timeframe (ej: "1H", "4H", "1D").
            count: Número de velas a obtener (opcional).
            start_date: Fecha de inicio (opcional).
            end_date: Fecha de fin (opcional).
            
        Returns:
            Tuple con (lista de Candle, calidad o estado).
        """
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Obtiene el precio actual de un símbolo.
        
        Args:
            symbol: Símbolo a consultar.
            
        Returns:
            Dict con precios (bid, ask, last) o None.
        """
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información detallada de un símbolo.
        
        Args:
            symbol: Símbolo a consultar.
            
        Returns:
            Dict con información del símbolo o None.
        """
        pass
    
    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """
        Obtiene lista de símbolos disponibles.
        
        Returns:
            Lista de símbolos disponibles.
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Inicializa el repositorio.
        
        Returns:
            True si se inicializó correctamente.
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Desconecta del repositorio."""
        pass