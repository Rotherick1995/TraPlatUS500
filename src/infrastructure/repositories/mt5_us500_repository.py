"""
Repositorio MT5 completo para US500 implementando las interfaces abstractas.
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd

from src.domain.repositories.abstract.market_data_repository import MarketDataRepository
from src.domain.repositories.abstract.order_repository import OrderRepository
from src.domain.entities.candle import Candle


class MT5US500Repository(MarketDataRepository, OrderRepository):
    """Repositorio MT5 completo para US500 implementando ambas interfaces."""
    
    US500_SYMBOL = "US500"
    US500_MIN_VOLUME = 0.1
    US500_MAX_VOLUME = 10.0
    
    # Mapeo de timeframes a MT5
    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    
    def __init__(self, login: int, server: str, password: str, mt5_path: str = None):
        """
        Inicializa el repositorio MT5 para US500.
        
        Args:
            login: Login de MT5
            server: Servidor de MT5
            password: Contraseña de MT5
            mt5_path: Ruta al terminal MT5 (opcional)
        """
        self.logger = logging.getLogger(__name__)
        self.login = login
        self.server = server
        self.password = password
        self.mt5_path = mt5_path
        self.connected = False
        self.account_info = None
        self.terminal_info = None
        
    # ===== Métodos de MarketDataRepository =====
    
    def initialize(self) -> bool:
        """
        Inicializa la conexión con MT5.
        
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            self.logger.info(f"Inicializando conexión MT5 - Login: {self.login}, Server: {self.server}")
            
            if not mt5.initialize(
                path=self.mt5_path,
                login=self.login,
                server=self.server,
                password=self.password,
                timeout=5000,
                portable=False
            ):
                error = mt5.last_error()
                self.logger.error(f"Error inicializando MT5: {error}")
                return False
            
            self.connected = True
            self.account_info = mt5.account_info()
            self.terminal_info = mt5.terminal_info()
            
            # Verificar y seleccionar símbolo US500
            self._ensure_us500_available()
            
            self.logger.info(f"✅ Conectado a MT5 - Cuenta: {self.account_info.login}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error en initialize: {str(e)}")
            return False
    
    def disconnect(self):
        """Desconecta del repositorio."""
        if self.connected:
            try:
                mt5.shutdown()
                self.connected = False
                self.logger.info("✅ Desconectado de MT5")
            except Exception as e:
                self.logger.error(f"Error al desconectar: {str(e)}")
    
    def get_historical_data(self, symbol: str, timeframe: str, count: int = None,
                           start_date: datetime = None, end_date: datetime = None) -> Tuple[Optional[List[Candle]], Any]:
        """
        Obtiene datos históricos de mercado para US500.
        """
        try:
            if not self.connected:
                self.logger.error("No conectado a MT5")
                return None, "Not connected"
            
            # Forzar símbolo US500
            if symbol != self.US500_SYMBOL:
                self.logger.warning(f"Forzando símbolo a {self.US500_SYMBOL}")
                symbol = self.US500_SYMBOL
            
            # Convertir timeframe
            mt5_timeframe = self.TIMEFRAME_MAP.get(timeframe.upper())
            if mt5_timeframe is None:
                self.logger.error(f"Timeframe no soportado: {timeframe}")
                return None, f"Unsupported timeframe: {timeframe}"
            
            # Obtener datos
            if count:
                # Obtener número específico de velas
                rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
            elif start_date:
                # Obtener datos desde fecha específica
                if not end_date:
                    end_date = datetime.now()
                rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
            else:
                # Obtener 100 velas por defecto
                rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 100)
            
            if rates is None or len(rates) == 0:
                self.logger.warning(f"No se obtuvieron datos para {symbol} {timeframe}")
                return [], "No data"
            
            # Convertir a lista de Candle
            candles = []
            for rate in rates:
                candle = Candle(
                    time=datetime.fromtimestamp(rate['time']),
                    open=rate['open'],
                    high=rate['high'],
                    low=rate['low'],
                    close=rate['close'],
                    volume=rate['tick_volume'],
                    symbol=symbol,
                    timeframe=timeframe
                )
                candles.append(candle)
            
            self.logger.info(f"Obtenidas {len(candles)} velas para {symbol} {timeframe}")
            return candles, "OK"
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos históricos: {str(e)}")
            return None, str(e)
    
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Obtiene el precio actual de US500.
        """
        try:
            if not self.connected:
                self.logger.error("No conectado a MT5")
                return None
            
            if symbol != self.US500_SYMBOL:
                symbol = self.US500_SYMBOL
            
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"No se pudo obtener información de {symbol}")
                return None
            
            return {
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'last': symbol_info.last,
                'spread': symbol_info.ask - symbol_info.bid,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo precio actual: {str(e)}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información detallada de US500.
        """
        try:
            if not self.connected:
                self.logger.error("No conectado a MT5")
                return None
            
            if symbol != self.US500_SYMBOL:
                symbol = self.US500_SYMBOL
            
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"No se pudo obtener información de {symbol}")
                return None
            
            return {
                'symbol': symbol_info.symbol,
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'last': symbol_info.last,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'spread': symbol_info.ask - symbol_info.bid,
                'spread_float': symbol_info.spread_float,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'trade_mode': symbol_info.trade_mode,
                'trade_mode_description': symbol_info.trade_mode_description,
                'margin_initial': symbol_info.margin_initial,
                'margin_maintenance': symbol_info.margin_maintenance,
                'swap_long': symbol_info.swap_long,
                'swap_short': symbol_info.swap_short,
                'swap_mode': symbol_info.swap_mode,
                'currency_base': symbol_info.currency_base,
                'currency_profit': symbol_info.currency_profit,
                'currency_margin': symbol_info.currency_margin,
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información del símbolo: {str(e)}")
            return None
    
    def get_available_symbols(self) -> List[str]:
        """
        Obtiene lista de símbolos disponibles.
        """
        try:
            if not self.connected:
                return []
            
            symbols = mt5.symbols_get()
            if symbols is None:
                return []
            
            # Filtrar solo US500
            return [s.name for s in symbols if s.name == self.US500_SYMBOL]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo símbolos: {str(e)}")
            return []
    
    # ===== Métodos de OrderRepository =====
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = 0.0, stop_loss: float = 0.0, 
                   take_profit: float = 0.0, comment: str = "") -> Optional[int]:
        """
        Coloca una orden de mercado (BUY/SELL) para US500.
        """
        try:
            if not self.connected:
                self.logger.error("No conectado a MT5")
                return None
            
            if symbol != self.US500_SYMBOL:
                self.logger.warning(f"Forzando símbolo a {self.US500_SYMBOL}")
                symbol = self.US500_SYMBOL
            
            # Verificar AutoTrading
            if not self._check_autotrading_enabled():
                self.logger.warning("AutoTrading deshabilitado - la orden podría fallar")
            
            # Verificar símbolo
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Símbolo {symbol} no disponible")
                return None
            
            # Ajustar volumen
            adjusted_volume = self._get_appropriate_volume(volume)
            if adjusted_volume != volume:
                self.logger.info(f"Volumen ajustado de {volume} a {adjusted_volume}")
            
            # Determinar precio y tipo MT5
            order_type = order_type.upper()
            if order_type == 'BUY':
                mt5_order_type = mt5.ORDER_TYPE_BUY
                execution_price = price if price > 0 else symbol_info.ask
            elif order_type == 'SELL':
                mt5_order_type = mt5.ORDER_TYPE_SELL
                execution_price = price if price > 0 else symbol_info.bid
            else:
                self.logger.error(f"Tipo de orden no soportado: {order_type}")
                return None
            
            # Preparar solicitud MT5
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": adjusted_volume,
                "type": mt5_order_type,
                "price": execution_price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 10,  # Desviación en puntos
                "magic": 234000,
                "comment": comment or f"{order_type} {symbol} {datetime.now().strftime('%H:%M')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            self.logger.info(f"Enviando orden {order_type} - Volumen: {adjusted_volume}, Precio: {execution_price}")
            
            # Enviar orden
            result = mt5.order_send(request)
            
            return self._handle_order_result(result)
            
        except Exception as e:
            self.logger.error(f"Error colocando orden: {str(e)}")
            return None
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Obtiene posiciones abiertas para US500.
        """
        try:
            if not self.connected:
                return []
            
            positions = mt5.positions_get(symbol=self.US500_SYMBOL)
            if positions is None:
                return []
            
            positions_list = []
            for pos in positions:
                position_dict = {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,  # 0 = BUY, 1 = SELL
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'commission': pos.commission,
                    'time': datetime.fromtimestamp(pos.time),
                    'time_update': datetime.fromtimestamp(pos.time_update),
                    'time_msc': datetime.fromtimestamp(pos.time_msc / 1000) if pos.time_msc > 0 else None,
                }
                positions_list.append(position_dict)
            
            return positions_list
            
        except Exception as e:
            self.logger.error(f"Error obteniendo posiciones: {str(e)}")
            return []
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Obtiene órdenes pendientes para US500.
        """
        try:
            if not self.connected:
                return []
            
            orders = mt5.orders_get(symbol=self.US500_SYMBOL)
            if orders is None:
                return []
            
            orders_list = []
            for order in orders:
                order_dict = {
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': order.type,
                    'volume_current': order.volume_current,
                    'volume_initial': order.volume_initial,
                    'price_open': order.price_open,
                    'sl': order.sl,
                    'tp': order.tp,
                    'price_current': order.price_current,
                    'type_time': order.type_time,
                    'time_setup': datetime.fromtimestamp(order.time_setup),
                    'time_expiration': datetime.fromtimestamp(order.time_expiration) if order.time_expiration > 0 else None,
                    'state': order.state,
                    'comment': order.comment,
                }
                orders_list.append(order_dict)
            
            return orders_list
            
        except Exception as e:
            self.logger.error(f"Error obteniendo órdenes pendientes: {str(e)}")
            return []
    
    def close_position(self, ticket: int) -> bool:
        """
        Cierra una posición específica.
        """
        try:
            if not self.connected:
                return False
            
            # Buscar la posición
            positions = mt5.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                self.logger.error(f"No se encontró posición con ticket {ticket}")
                return False
            
            position = positions[0]
            
            # Obtener precio actual
            symbol_info = mt5.symbol_info_tick(position.symbol)
            if symbol_info is None:
                self.logger.error(f"No se pudo obtener precio de {position.symbol}")
                return False
            
            # Determinar orden de cierre
            if position.type == 0:  # BUY position -> close with SELL
                order_type = mt5.ORDER_TYPE_SELL
                price = symbol_info.bid
                type_str = "SELL"
            else:  # SELL position -> close with BUY
                order_type = mt5.ORDER_TYPE_BUY
                price = symbol_info.ask
                type_str = "BUY"
            
            # Preparar solicitud de cierre
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position.ticket,
                "price": price,
                "deviation": 10,
                "magic": 234000,
                "comment": f"CLOSE {type_str} {datetime.now().strftime('%H:%M')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            self.logger.info(f"Cerrando posición {ticket} - Tipo: {type_str}, Precio: {price}")
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ Posición {ticket} cerrada exitosamente")
                return True
            else:
                if result:
                    self.logger.error(f"❌ Error al cerrar posición {ticket}: {result.comment}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error cerrando posición: {str(e)}")
            return False
    
    def cancel_order(self, ticket: int) -> bool:
        """
        Cancela una orden pendiente.
        """
        try:
            if not self.connected:
                return False
            
            # Buscar la orden
            orders = mt5.orders_get(ticket=ticket)
            if not orders or len(orders) == 0:
                self.logger.error(f"No se encontró orden con ticket {ticket}")
                return False
            
            order = orders[0]
            
            # Preparar solicitud de cancelación
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
                "comment": f"Cancelled {datetime.now().strftime('%H:%M')}",
            }
            
            self.logger.info(f"Cancelando orden {ticket} - Símbolo: {order.symbol}")
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ Orden {ticket} cancelada exitosamente")
                return True
            else:
                if result:
                    self.logger.error(f"❌ Error al cancelar orden {ticket}: {result.comment}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error cancelando orden: {str(e)}")
            return False
    
    def modify_order(self, ticket: int, price: float = None, 
                    stop_loss: float = None, take_profit: float = None) -> bool:
        """
        Modifica una orden pendiente.
        """
        try:
            if not self.connected:
                return False
            
            # Buscar la orden
            orders = mt5.orders_get(ticket=ticket)
            if not orders or len(orders) == 0:
                self.logger.error(f"No se encontró orden con ticket {ticket}")
                return False
            
            order = orders[0]
            
            # Usar valores actuales si no se proporcionan nuevos
            new_price = price if price is not None else order.price_open
            new_sl = stop_loss if stop_loss is not None else order.sl
            new_tp = take_profit if take_profit is not None else order.tp
            
            # Preparar solicitud de modificación
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "price": new_price,
                "sl": new_sl,
                "tp": new_tp,
                "comment": f"Modified {datetime.now().strftime('%H:%M')}",
            }
            
            self.logger.info(f"Modificando orden {ticket} - Precio: {new_price}, SL: {new_sl}, TP: {new_tp}")
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ Orden {ticket} modificada exitosamente")
                return True
            else:
                if result:
                    self.logger.error(f"❌ Error al modificar orden {ticket}: {result.comment}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error modificando orden: {str(e)}")
            return False
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de la cuenta.
        """
        try:
            if not self.connected or not self.account_info:
                return None
            
            return {
                'login': self.account_info.login,
                'name': self.account_info.name,
                'server': self.account_info.server,
                'currency': self.account_info.currency,
                'balance': self.account_info.balance,
                'equity': self.account_info.equity,
                'margin': self.account_info.margin,
                'margin_free': self.account_info.margin_free,
                'margin_level': self.account_info.margin_level,
                'leverage': self.account_info.leverage,
                'trade_allowed': self.account_info.trade_allowed,
                'trade_expert': self.account_info.trade_expert,
                'profit': self.account_info.profit,
                'credit': self.account_info.credit,
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información de cuenta: {str(e)}")
            return None
    
    # ===== Métodos auxiliares =====
    
    def _ensure_us500_available(self) -> bool:
        """Asegurar que US500 esté disponible y seleccionado."""
        symbol_info = mt5.symbol_info(self.US500_SYMBOL)
        
        if symbol_info is None:
            self.logger.warning(f"Símbolo {self.US500_SYMBOL} no encontrado, seleccionando...")
            if not mt5.symbol_select(self.US500_SYMBOL, True):
                self.logger.error(f"No se pudo seleccionar {self.US500_SYMBOL}")
                return False
        
        if not symbol_info.visible:
            mt5.symbol_select(self.US500_SYMBOL, True)
        
        self.logger.info(f"✅ Símbolo {self.US500_SYMBOL} disponible")
        return True
    
    def _check_autotrading_enabled(self) -> bool:
        """Verificar si AutoTrading está habilitado."""
        if not self.connected or not self.terminal_info:
            return False
        
        trading_allowed = self.terminal_info.trade_allowed
        
        if not trading_allowed:
            self.logger.warning("⚠️ AutoTrading no está habilitado en MT5")
        
        return trading_allowed
    
    def _get_appropriate_volume(self, requested_volume: float) -> float:
        """Obtener volumen apropiado para US500."""
        symbol_info = mt5.symbol_info(self.US500_SYMBOL)
        if symbol_info is None:
            return self.US500_MIN_VOLUME
        
        # Asegurar que el volumen esté dentro de los límites
        volume = max(requested_volume, symbol_info.volume_min)
        volume = min(volume, symbol_info.volume_max)
        
        # Redondear al paso apropiado
        step = symbol_info.volume_step
        if step > 0:
            volume = round(volume / step) * step
        
        return volume
    
    def _handle_order_result(self, result) -> Optional[int]:
        """Manejar el resultado de una orden MT5."""
        if result is None:
            error = mt5.last_error()
            self.logger.error(f"Error al enviar orden: {error}")
            return None
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"✅ Orden exitosa - Ticket: {result.order}, Deal: {result.deal}")
            return result.order
        else:
            self.logger.error(f"❌ Orden rechazada - Código: {result.retcode}, Razón: {result.comment}")
            
            # Decodificar errores comunes
            error_messages = {
                10004: "Requote - precio cambiado",
                10006: "Rechazada por el dealer",
                10008: "Volumen insuficiente",
                10009: "Sin conexión",
                10010: "Timeout",
                10012: "Orden inválida",
                10013: "Volumen inválido",
                10014: "Precio inválido",
                10015: "Símbolo inválido",
                10016: "AutoTrading deshabilitado",
                10017: "No hay suficientes fondos",
                10018: "Mercado cerrado",
                10019: "Trade deshabilitado",
                10021: "Margen insuficiente",
            }
            
            if result.retcode in error_messages:
                self.logger.error(f"   Detalle: {error_messages[result.retcode]}")
            
            return None
    
    def get_last_error(self) -> str:
        """
        Obtiene el último error de MT5.
        
        Returns:
            str: Mensaje de error
        """
        error = mt5.last_error()
        if isinstance(error, tuple) and len(error) > 1:
            return error[1]
        return str(error)