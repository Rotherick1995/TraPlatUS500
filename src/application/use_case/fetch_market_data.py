# src/application/use_cases/fetch_market_data.py

from typing import Dict, Any, List, Optional
from datetime import datetime

from src.infrastructure.persistence.mt5.mt5_data_repository import create_mt5_data_repository
from src.domain.entities.candle import Candle


class FetchMarketDataUseCase:
    """Caso de uso para obtener datos de mercado."""
    
    def __init__(self, mt5_connection_use_case=None):
        """
        Inicializa el caso de uso.
        
        Args:
            mt5_connection_use_case: Caso de uso de conexión MT5 (opcional).
        """
        self.data_repository = create_mt5_data_repository()
        self.connection_use_case = mt5_connection_use_case
    
    def execute(self, symbol: str, timeframe: str, count: int = 100) -> Dict[str, Any]:
        """
        Obtiene datos históricos de mercado.
        
        Args:
            symbol: Símbolo a consultar.
            timeframe: Timeframe (ej: "1H", "4H", "1D").
            count: Número de velas a obtener.
            
        Returns:
            Dict con resultado de la operación.
        """
        try:
            # Verificar conexión si se proporcionó el caso de uso de conexión
            if self.connection_use_case:
                status = self.connection_use_case.get_status()
                if not status['data']['connected']:
                    return {
                        'success': False,
                        'message': "No hay conexión a MT5",
                        'data': None
                    }
            
            # Inicializar repositorio si es necesario
            if not self.data_repository.initialize():
                return {
                    'success': False,
                    'message': "No se pudo inicializar el repositorio de datos",
                    'data': None
                }
            
            # Obtener datos
            candles, quality = self.data_repository.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                count=count
            )
            
            if candles:
                return {
                    'success': True,
                    'message': f"Datos obtenidos exitosamente",
                    'data': {
                        'candles': candles,
                        'count': len(candles),
                        'quality': quality,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'timestamp': datetime.now()
                    }
                }
            else:
                return {
                    'success': False,
                    'message': "No se pudieron obtener datos",
                    'data': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data': None
            }
    
    def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """
        Obtiene el precio actual de un símbolo.
        
        Args:
            symbol: Símbolo a consultar.
            
        Returns:
            Dict con precio actual.
        """
        try:
            # Inicializar repositorio si es necesario
            if not self.data_repository.initialize():
                return {
                    'success': False,
                    'message': "No se pudo inicializar el repositorio de datos",
                    'data': None
                }
            
            # Obtener precio
            price_info = self.data_repository.get_current_price(symbol)
            
            if price_info:
                return {
                    'success': True,
                    'message': "Precio obtenido",
                    'data': {
                        'price': price_info,
                        'symbol': symbol,
                        'timestamp': datetime.now()
                    }
                }
            else:
                return {
                    'success': False,
                    'message': "No se pudo obtener el precio",
                    'data': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data': None
            }
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Obtiene información de un símbolo.
        
        Args:
            symbol: Símbolo a consultar.
            
        Returns:
            Dict con información del símbolo.
        """
        try:
            # Inicializar repositorio si es necesario
            if not self.data_repository.initialize():
                return {
                    'success': False,
                    'message': "No se pudo inicializar el repositorio de datos",
                    'data': None
                }
            
            # Obtener información
            info = self.data_repository.get_symbol_info(symbol)
            
            if info:
                return {
                    'success': True,
                    'message': "Información obtenida",
                    'data': {
                        'info': info,
                        'symbol': symbol
                    }
                }
            else:
                return {
                    'success': False,
                    'message': "No se pudo obtener información",
                    'data': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data': None
            }
    
    def disconnect(self):
        """Desconecta el repositorio de datos."""
        self.data_repository.disconnect()


# Función factory para crear el caso de uso
def create_fetch_market_data_use_case(mt5_connection_use_case=None) -> FetchMarketDataUseCase:
    """
    Crea y retorna una instancia de FetchMarketDataUseCase.
    
    Args:
        mt5_connection_use_case: Caso de uso de conexión MT5 (opcional).
        
    Returns:
        FetchMarketDataUseCase: Instancia configurada.
    """
    return FetchMarketDataUseCase(mt5_connection_use_case)