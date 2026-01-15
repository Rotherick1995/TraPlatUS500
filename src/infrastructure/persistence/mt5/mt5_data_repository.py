# src/infrastructure/persistence/mt5/mt5_data_repository.py

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import MetaTrader5 as mt5
import pandas as pd

from src.config.settings import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, DEFAULT_DATA_COUNT
from src.config.constants import get_mt5_timeframe
from src.domain.entities.candle import Candle
from src.domain.repositories.abstract.market_data_repository import MarketDataRepository


class MT5DataRepository(MarketDataRepository):
    """Implementación concreta de MarketDataRepository para MetaTrader 5."""
    
    def __init__(self):
        """Inicializa el repositorio de datos MT5."""
        self._initialized = False
    
    def _ensure_connection(self) -> bool:
        """Asegura que haya una conexión activa a MT5."""
        try:
            account_info = mt5.account_info()
            return account_info is not None
        except:
            return False
    
    def _mt5_to_candle(self, mt5_rate: tuple) -> Optional[Candle]:
        """Convierte una tupla de datos de MT5 a una entidad Candle."""
        try:
            return Candle(
                timestamp=pd.to_datetime(mt5_rate[0], unit='s'),
                open=float(mt5_rate[1]),
                high=float(mt5_rate[2]),
                low=float(mt5_rate[3]),
                close=float(mt5_rate[4]),
                volume=int(mt5_rate[5])
            )
        except:
            return None
    
    def initialize(self) -> bool:
        """Inicializa el repositorio."""
        try:
            if not mt5.initialize():
                return False
            self._initialized = True
            return True
        except:
            return False
    
    def get_historical_data(self, symbol: str, timeframe: str, count: int = None,
                           start_date: datetime = None, end_date: datetime = None) -> Tuple[Optional[List[Candle]], Any]:
        """Obtiene datos históricos de mercado."""
        if not self._ensure_connection():
            return None, None
        
        # Usar valores por defecto si no se especifican
        if count is None:
            count = DEFAULT_DATA_COUNT
        
        try:
            # Convertir timeframe a formato MT5
            mt5_timeframe = get_mt5_timeframe(timeframe)
            
            # Obtener datos de MT5
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
            
            if rates is None or len(rates) == 0:
                return None, None
            
            # Convertir a lista de Candle
            candles = []
            for rate in rates:
                candle = self._mt5_to_candle(rate)
                if candle:
                    candles.append(candle)
            
            return candles, "OK"
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return None, None
    
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Obtiene el precio actual de un símbolo."""
        if not self._ensure_connection():
            return None
        
        try:
            symbol_info = mt5.symbol_info_tick(symbol)
            
            if symbol_info is None:
                return None
            
            return {
                'bid': float(symbol_info.bid),
                'ask': float(symbol_info.ask),
                'last': float(symbol_info.last)
            }
            
        except:
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtiene información detallada de un símbolo."""
        if not self._ensure_connection():
            return None
        
        try:
            info = mt5.symbol_info(symbol)
            
            if info is None:
                return None
            
            # Extraer información relevante
            return {
                'name': info.name,
                'point': info.point,
                'digits': info.digits,
                'spread': info.spread,
                'trade_mode': info.trade_mode,
                'trade_allowed': info.trade_allowed,
                'margin_rate': info.margin_rate
            }
            
        except:
            return None
    
    def get_available_symbols(self) -> List[str]:
        """Obtiene lista de símbolos disponibles."""
        if not self._ensure_connection():
            return []
        
        try:
            symbols = mt5.symbols_get()
            
            if symbols is None:
                return []
            
            # Filtrar solo símbolos activos
            active_symbols = []
            for symbol in symbols:
                if hasattr(symbol, 'visible') and symbol.visible:
                    if hasattr(symbol, 'trade_mode') and symbol.trade_mode == 0:  # TRADE_MODE_FULL
                        active_symbols.append(symbol.name)
            
            return sorted(active_symbols)
            
        except:
            return []
    
    def disconnect(self):
        """Desconecta del repositorio."""
        mt5.shutdown()
        self._initialized = False


# Función factory para crear el repositorio
def create_mt5_data_repository() -> MT5DataRepository:
    """Crea y retorna una instancia de MT5DataRepository."""
    return MT5DataRepository()