# src/application/use_cases/fetch_market_data.py
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.domain.entities.candle import Candle
from src.infrastructure.persistence.mt5.mt5_data_repository import create_mt5_data_repository


class FetchMarketDataUseCase:
    """Caso de uso para obtener datos de mercado."""
    
    def __init__(self, mt5_use_case=None):
        self.mt5_use_case = mt5_use_case
        self.data_repository = create_mt5_data_repository()
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        count: int = 100,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtiene datos históricos."""
        try:
            # Inicializar repositorio
            if not self.data_repository._initialized:
                self.data_repository.initialize()
            
            # Obtener datos
            candles, message = self.data_repository.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                count=count,
                start_date=from_date,
                end_date=to_date
            )
            
            # Obtener información del símbolo (precio mínimo, dígitos, etc.)
            symbol_info = self.data_repository.get_symbol_info(symbol)
            
            if candles:
                result = {
                    'success': True,
                    'data': candles,
                    'message': f"Obtenidas {len(candles)} velas",
                    'count': len(candles),
                    'symbol_info': symbol_info  # Agregar información del símbolo
                }
                
                # Agregar hora del servidor si está disponible
                server_time = self.data_repository.get_server_time()
                if server_time:
                    result['server_time'] = server_time
                
                return result
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': message or "No se pudieron obtener datos",
                    'count': 0,
                    'symbol_info': None
                }
            
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f"Error: {str(e)}",
                'count': 0,
                'symbol_info': None
            }
    
    def get_real_time_data(self, symbol: str) -> Dict[str, Any]:
        """Obtiene datos en tiempo real."""
        try:
            # Inicializar repositorio
            if not self.data_repository._initialized:
                self.data_repository.initialize()
            
            # Obtener tick
            tick = self.data_repository.get_current_tick(symbol)
            
            # Obtener información del símbolo
            symbol_info = self.data_repository.get_symbol_info(symbol)
            
            # Obtener hora del servidor
            server_time = self.data_repository.get_server_time()
            
            if tick:
                return {
                    'success': True,
                    'data': {
                        'bid': tick['bid'],
                        'ask': tick['ask'],
                        'spread': tick['ask'] - tick['bid'],
                        'timestamp': tick['time']
                    },
                    'symbol_info': symbol_info,
                    'server_time': server_time,
                    'message': "Datos en tiempo real obtenidos"
                }
            else:
                return {
                    'success': False,
                    'data': {},
                    'symbol_info': symbol_info,
                    'server_time': server_time,
                    'message': "No se pudo obtener el tick actual"
                }
                
        except Exception as e:
            return {
                'success': False,
                'data': {},
                'symbol_info': None,
                'server_time': None,
                'message': f"Error: {str(e)}"
            }
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Obtiene información detallada del símbolo."""
        try:
            if not self.data_repository._initialized:
                self.data_repository.initialize()
            
            info = self.data_repository.get_symbol_info(symbol)
            
            if info:
                return {
                    'success': True,
                    'data': info,
                    'message': "Información del símbolo obtenida"
                }
            else:
                return {
                    'success': False,
                    'data': {},
                    'message': "No se pudo obtener información del símbolo"
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