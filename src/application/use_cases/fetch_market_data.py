# src/application/use_cases/fetch_market_data.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Importar con manejo de errores
try:
    from src.domain.entities.candle import Candle
    from src.infrastructure.persistence.mt5.mt5_data_repository import create_mt5_data_repository
    REPOSITORY_AVAILABLE = True
except ImportError:
    REPOSITORY_AVAILABLE = False
    print("⚠️ MT5 data repository no disponible")


class FetchMarketDataUseCase:
    """Caso de uso para obtener datos de mercado."""
    
    def __init__(self, mt5_use_case=None):
        self.mt5_use_case = mt5_use_case
        if REPOSITORY_AVAILABLE:
            self.data_repository = create_mt5_data_repository()
        else:
            self.data_repository = None
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        count: int = 100,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtiene datos históricos."""
        if not REPOSITORY_AVAILABLE or not self.data_repository:
            return {
                'success': False,
                'message': "Repositorio de datos no disponible",
                'data': []
            }
        
        try:
            # Primero inicializar si es necesario
            if not hasattr(self.data_repository, 'initialized') or not self.data_repository.initialized:
                self.data_repository.initialize()
            
            candles = self.data_repository.get_candles(
                symbol=symbol,
                timeframe=timeframe,
                count=count,
                from_date=from_date,
                to_date=to_date
            )
            
            return {
                'success': True,
                'data': candles,
                'message': f"Obtenidas {len(candles)} velas"
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f"Error: {str(e)}"
            }
    
    def get_real_time_data(self, symbol: str) -> Dict[str, Any]:
        """Obtiene datos en tiempo real."""
        if not REPOSITORY_AVAILABLE or not self.data_repository:
            return {
                'success': False,
                'message': "Repositorio de datos no disponible",
                'data': {}
            }
        
        try:
            # Primero inicializar si es necesario
            if not hasattr(self.data_repository, 'initialized') or not self.data_repository.initialized:
                self.data_repository.initialize()
            
            # Intentar obtener tick
            tick = None
            if hasattr(self.data_repository, 'get_current_tick'):
                tick = self.data_repository.get_current_tick(symbol)
            
            if tick and hasattr(tick, 'bid') and hasattr(tick, 'ask'):
                return {
                    'success': True,
                    'data': {
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'spread': (tick.ask - tick.bid) * 10000,
                        'timestamp': getattr(tick, 'time', datetime.now())
                    },
                    'message': "Datos en tiempo real obtenidos"
                }
            else:
                # Fallback: usar datos simulados
                return {
                    'success': True,
                    'data': {
                        'bid': 4500.0,
                        'ask': 4500.1,
                        'spread': 1.0,
                        'timestamp': datetime.now()
                    },
                    'message': "Datos simulados (modo fallback)"
                }
                
        except Exception as e:
            return {
                'success': False,
                'data': {},
                'message': f"Error: {str(e)}"
            }


def create_fetch_market_data_use_case(mt5_use_case=None) -> FetchMarketDataUseCase:
    """Crea una instancia de FetchMarketDataUseCase."""
    return FetchMarketDataUseCase(mt5_use_case=mt5_use_case)