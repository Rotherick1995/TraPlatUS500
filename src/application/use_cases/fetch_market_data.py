# src/application/use_cases/fetch_market_data.py
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import MetaTrader5 as mt5

from src.domain.entities.candle import Candle
from src.infrastructure.persistence.mt5.mt5_data_repository import create_mt5_data_repository


class FetchMarketDataUseCase:
    """Caso de uso para obtener datos de mercado con soporte en tiempo real."""
    
    def __init__(self, mt5_use_case=None):
        self.mt5_use_case = mt5_use_case
        self.data_repository = create_mt5_data_repository()
        self.last_ticks = {}  # Cache de últimos ticks por símbolo
        self.last_symbol_info = {}  # Cache de información de símbolos
        
    def initialize(self):
        """Inicializar el repositorio de datos."""
        try:
            if not self.data_repository._initialized:
                return self.data_repository.initialize()
            return True
        except Exception as e:
            print(f"Error inicializando fetch market data: {e}")
            return False
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        count: int = 100,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtiene datos históricos con información del símbolo."""
        try:
            # Inicializar si es necesario
            if not self.data_repository._initialized:
                if not self.initialize():
                    return {
                        'success': False,
                        'data': [],
                        'message': "No se pudo inicializar MT5",
                        'count': 0,
                        'symbol_info': None,
                        'server_time': None
                    }
            
            # Verificar que el símbolo existe
            if not mt5.symbol_select(symbol, True):
                return {
                    'success': False,
                    'data': [],
                    'message': f"Símbolo {symbol} no disponible",
                    'count': 0,
                    'symbol_info': None,
                    'server_time': None
                }
            
            # Obtener datos históricos
            candles, message = self.data_repository.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                count=count,
                start_date=from_date,
                end_date=to_date
            )
            
            # Obtener información del símbolo
            symbol_info = self._get_cached_symbol_info(symbol)
            
            # Obtener hora del servidor
            server_time = self._get_server_time()
            
            if candles:
                # Ordenar por tiempo (más antiguo a más reciente)
                sorted_candles = sorted(candles, key=lambda x: x.time if hasattr(x, 'time') else datetime.now())
                
                return {
                    'success': True,
                    'data': sorted_candles,
                    'message': f"Obtenidas {len(sorted_candles)} velas de {symbol} ({timeframe})",
                    'count': len(sorted_candles),
                    'symbol_info': symbol_info,
                    'server_time': server_time
                }
            else:
                return {
                    'success': False,
                    'data': [],
                    'message': message or f"No se pudieron obtener datos de {symbol}",
                    'count': 0,
                    'symbol_info': symbol_info,
                    'server_time': server_time
                }
            
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'message': f"Error obteniendo datos históricos: {str(e)}",
                'count': 0,
                'symbol_info': None,
                'server_time': None
            }
    
    def get_real_time_data(self, symbol: str, fast_mode: bool = True) -> Dict[str, Any]:
        """Obtiene datos en tiempo real de manera eficiente."""
        try:
            # Inicializar si es necesario
            if not self.data_repository._initialized:
                if not self.initialize():
                    return {
                        'success': False,
                        'data': {},
                        'symbol_info': None,
                        'server_time': None,
                        'message': "No se pudo inicializar MT5"
                    }
            
            # Verificar que el símbolo existe
            if not mt5.symbol_select(symbol, True):
                return {
                    'success': False,
                    'data': {},
                    'symbol_info': None,
                    'server_time': None,
                    'message': f"Símbolo {symbol} no disponible"
                }
            
            # Modo rápido: usar directamente mt5 para mejor rendimiento
            if fast_mode:
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    return {
                        'success': False,
                        'data': {},
                        'symbol_info': None,
                        'server_time': None,
                        'message': f"No se pudo obtener tick de {symbol}"
                    }
                
                # Obtener información del símbolo (cacheada si es posible)
                symbol_info = self._get_cached_symbol_info(symbol)
                
                # Calcular spread en pips
                spread_pips = 0
                if symbol_info and 'digits' in symbol_info:
                    spread = abs(tick.ask - tick.bid)
                    spread_pips = spread * (10 ** symbol_info['digits'])
                
                # Obtener hora del servidor
                server_time = self._get_server_time()
                
                # Cachear el último tick
                self.last_ticks[symbol] = {
                    'bid': tick.bid,
                    'ask': tick.ask,
                    'time': tick.time_msc if hasattr(tick, 'time_msc') else datetime.now(),
                    'symbol': symbol
                }
                
                return {
                    'success': True,
                    'data': {
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'spread': spread_pips,
                        'spread_points': abs(tick.ask - tick.bid),
                        'timestamp': tick.time if hasattr(tick, 'time') else datetime.now(),
                        'time_msc': tick.time_msc if hasattr(tick, 'time_msc') else None,
                        'symbol': symbol
                    },
                    'symbol_info': symbol_info,
                    'server_time': server_time,
                    'message': f"Datos en tiempo real de {symbol}"
                }
            else:
                # Modo usando el repositorio (más robusto pero más lento)
                tick = self.data_repository.get_current_tick(symbol)
                symbol_info = self.data_repository.get_symbol_info(symbol)
                server_time = self.data_repository.get_server_time()
                
                if tick:
                    # Cachear el último tick
                    self.last_ticks[symbol] = tick
                    
                    return {
                        'success': True,
                        'data': {
                            'bid': tick['bid'],
                            'ask': tick['ask'],
                            'spread': tick['ask'] - tick['bid'],
                            'timestamp': tick['time'],
                            'symbol': symbol
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
                'message': f"Error obteniendo datos en tiempo real: {str(e)}"
            }
    
    def get_last_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtiene el último tick cacheado."""
        return self.last_ticks.get(symbol)
    
    def get_multiple_symbols_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Obtiene datos de múltiples símbolos de manera eficiente."""
        results = {}
        
        for symbol in symbols:
            data = self.get_real_time_data(symbol, fast_mode=True)
            if data['success']:
                results[symbol] = data['data']
        
        return results
    
    def get_symbol_info(self, symbol: str, use_cache: bool = True) -> Dict[str, Any]:
        """Obtiene información detallada del símbolo."""
        try:
            if not self.data_repository._initialized:
                if not self.initialize():
                    return {
                        'success': False,
                        'data': {},
                        'message': "No se pudo inicializar MT5"
                    }
            
            # Usar cache si está disponible y solicitado
            if use_cache and symbol in self.last_symbol_info:
                info = self.last_symbol_info[symbol]
                return {
                    'success': True,
                    'data': info,
                    'message': "Información del símbolo obtenida (cache)"
                }
            
            # Verificar que el símbolo existe
            if not mt5.symbol_select(symbol, True):
                return {
                    'success': False,
                    'data': {},
                    'message': f"Símbolo {symbol} no disponible"
                }
            
            # Obtener información usando el repositorio
            info = self.data_repository.get_symbol_info(symbol)
            
            if info:
                # Cachear la información
                self.last_symbol_info[symbol] = info
                
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
                'message': f"Error obteniendo información del símbolo: {str(e)}"
            }
    
    def _get_cached_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Obtiene información del símbolo cacheada o la obtiene si no está cacheada."""
        if symbol in self.last_symbol_info:
            return self.last_symbol_info[symbol]
        
        # Si no está cacheada, obtenerla
        result = self.get_symbol_info(symbol, use_cache=False)
        if result['success']:
            return result['data']
        
        return {
            'digits': 5,
            'point': 0.00001,
            'spread': 0,
            'name': symbol,
            'description': symbol,
            'trade_mode': 0
        }
    
    def _get_server_time(self) -> Optional[datetime]:
        """Obtiene la hora del servidor de manera eficiente."""
        try:
            # Intentar obtener hora del servidor usando MT5 directamente
            server_time = mt5.symbol_info_tick("US500").time_msc if mt5.symbol_info_tick("US500") else None
            
            if server_time:
                # Convertir timestamp a datetime
                return datetime.fromtimestamp(server_time / 1000.0)
            
            # Fallback al repositorio
            return self.data_repository.get_server_time()
        except:
            # Fallback a hora local
            return datetime.now()
    
    def update_last_candle_realtime(self, symbol: str, timeframe: str, current_price: float) -> Dict[str, Any]:
        """Actualiza la última vela en tiempo real con el precio actual."""
        try:
            # Obtener las últimas 2 velas
            result = self.get_historical_data(symbol, timeframe, count=2)
            
            if not result['success'] or len(result['data']) < 2:
                return {
                    'success': False,
                    'message': "No se pudieron obtener datos para actualizar última vela"
                }
            
            # Obtener última vela
            last_candle = result['data'][-1]
            
            # Verificar si la última vela aún está activa (dependiendo del timeframe)
            candle_end_time = self._get_candle_end_time(last_candle, timeframe)
            current_time = datetime.now()
            
            # Si aún estamos en el timeframe de la última vela, actualizarla
            if current_time < candle_end_time:
                # Aquí podrías implementar la lógica para actualizar la vela
                # Esto dependería de cómo manejas las velas en tu aplicación
                pass
            
            return {
                'success': True,
                'message': "Última vela verificada",
                'current_price': current_price,
                'candle_end_time': candle_end_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error actualizando última vela: {str(e)}"
            }
    
    def _get_candle_end_time(self, candle, timeframe: str) -> datetime:
        """Calcula el tiempo de finalización de una vela basado en su timeframe."""
        if not hasattr(candle, 'time'):
            return datetime.now()
        
        candle_time = candle.time
        if isinstance(candle_time, datetime):
            start_time = candle_time
        else:
            start_time = datetime.fromtimestamp(candle_time / 1000.0) if candle_time > 1000000000000 else datetime.fromtimestamp(candle_time)
        
        # Calcular duración basada en timeframe
        timeframe_map = {
            'M1': timedelta(minutes=1),
            'M5': timedelta(minutes=5),
            'M15': timedelta(minutes=15),
            'M30': timedelta(minutes=30),
            'H1': timedelta(hours=1),
            'H4': timedelta(hours=4),
            'D1': timedelta(days=1),
            'W1': timedelta(weeks=1),
            'MN1': timedelta(days=30)  # Aproximado
        }
        
        duration = timeframe_map.get(timeframe, timedelta(hours=1))
        return start_time + duration
    
    def get_active_indicators_info(self, symbol: str, indicators_config: Dict[str, Any]) -> List[str]:
        """Obtiene información de indicadores activos para un símbolo."""
        active_indicators = []
        
        for name, config in indicators_config.items():
            if config.get('enabled', False):
                if name == 'sma':
                    period = config.get('params', {}).get('period', 20)
                    active_indicators.append(f"SMA{period}")
                elif name == 'ema':
                    period = config.get('params', {}).get('period', 12)
                    active_indicators.append(f"EMA{period}")
                elif name == 'rsi':
                    period = config.get('params', {}).get('period', 14)
                    active_indicators.append(f"RSI{period}")
                elif name == 'macd':
                    active_indicators.append("MACD")
                elif name == 'bollinger':
                    active_indicators.append("BB")
                elif name == 'stochastic':
                    active_indicators.append("STOCH")
        
        return active_indicators


def create_fetch_market_data_use_case(mt5_use_case=None) -> FetchMarketDataUseCase:
    """Crea una instancia de FetchMarketDataUseCase optimizada para tiempo real."""
    return FetchMarketDataUseCase(mt5_use_case=mt5_use_case)