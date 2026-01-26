# src/infrastructure/persistence/mt5/mt5_order_repository.py

from typing import Optional, List, Dict, Any
import MetaTrader5 as mt5
import datetime

from src.config.settings import DEFAULT_LOT_SIZE
from src.config.constants import get_mt5_order_type
from src.domain.repositories.abstract.order_repository import OrderRepository


class MT5OrderRepository(OrderRepository):
    """Implementación concreta de OrderRepository para MetaTrader 5."""
    
    def __init__(self):
        """Inicializa el repositorio de órdenes MT5."""
        self.initialized = False
        self.last_error = ""  # Nuevo: para almacenar el último error
    
    def initialize(self) -> bool:
        """
        Inicializa el repositorio.
        
        Returns:
            bool: True si se inicializó correctamente
        """
        try:
            # Verificar si MT5 ya está inicializado
            if mt5.initialize():
                self.initialized = True
                self.last_error = ""
                return True
            else:
                self.last_error = "No se pudo inicializar MT5"
                return False
        except Exception as e:
            self.last_error = f"Error al inicializar MT5: {str(e)}"
            return False
    
    def _ensure_connection(self) -> bool:
        """Verifica que haya conexión a MT5."""
        try:
            # Si no está inicializado, intentar inicializar
            if not self.initialized:
                return self.initialize()
            
            account_info = mt5.account_info()
            if account_info is None:
                self.last_error = "No hay conexión a la cuenta MT5"
                return False
            
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = f"Error de conexión: {str(e)}"
            return False
    
    def get_last_error(self) -> str:
        """Obtiene el último error registrado."""
        return self.last_error
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = 0.0, stop_loss: float = 0.0, 
                   take_profit: float = 0.0, comment: str = "") -> Optional[int]:
        """Coloca una orden en MT5."""
        if not self._ensure_connection():
            return None
        
        try:
            # Validar símbolo
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.last_error = f"Símbolo {symbol} no encontrado"
                return None
            
            if not symbol_info.visible:
                self.last_error = f"Símbolo {symbol} no está visible"
                return None
            
            if symbol_info.trade_mode != 0:  # 0 = TRADE_MODE_FULL
                self.last_error = f"Símbolo {symbol} no permite trading"
                return None
            
            # Preparar la orden
            order_type_mt5 = get_mt5_order_type(order_type)
            
            # Si el precio es 0, usar el precio actual
            if price == 0.0:
                tick = mt5.symbol_info_tick(symbol)
                if order_type_mt5 == mt5.ORDER_TYPE_BUY:
                    price = tick.ask if tick else 0.0
                else:
                    price = tick.bid if tick else 0.0
            
            # Validar que tenemos un precio válido
            if price <= 0:
                self.last_error = f"Precio inválido para {symbol}: {price}"
                return None
            
            # Validar volumen
            if volume < symbol_info.volume_min:
                self.last_error = f"Volumen mínimo para {symbol} es {symbol_info.volume_min}"
                return None
            
            if volume > symbol_info.volume_max:
                self.last_error = f"Volumen máximo para {symbol} es {symbol_info.volume_max}"
                return None
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type_mt5,
                "price": price,
                "sl": stop_loss if stop_loss > 0 else 0.0,
                "tp": take_profit if take_profit > 0 else 0.0,
                "deviation": 10,
                "magic": 234000,
                "comment": comment or f"{order_type} {symbol}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar la orden
            result = mt5.order_send(request)
            
            if result:
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.last_error = ""
                    # NUEVO: Registrar detalles de la orden ejecutada
                    order_details = {
                        'ticket': result.order,
                        'symbol': symbol,
                        'type': order_type,
                        'volume': volume,
                        'price': price,
                        'sl': stop_loss,
                        'tp': take_profit,
                        'comment': comment,
                        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'retcode': result.retcode,
                        'deal': result.deal
                    }
                    # Aquí podrías guardar estos detalles en una base de datos local
                    return result.order
                else:
                    # NUEVO: Obtener mensaje de error específico
                    error_msg = self._get_error_message(result.retcode)
                    self.last_error = f"Error MT5 ({result.retcode}): {error_msg}"
                    return None
            else:
                self.last_error = "No se recibió respuesta de MT5"
                return None
            
        except Exception as e:
            self.last_error = f"Excepción al colocar orden: {str(e)}"
            return None
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Obtiene posiciones abiertas."""
        if not self._ensure_connection():
            return []
        
        try:
            positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                # NUEVO: Calcular porcentaje de profit
                profit = pos.profit
                profit_percentage = 0.0
                if pos.price_open > 0:
                    if pos.type == mt5.POSITION_TYPE_BUY:
                        profit_percentage = ((pos.price_current - pos.price_open) / pos.price_open) * 100
                    else:
                        profit_percentage = ((pos.price_open - pos.price_current) / pos.price_open) * 100
                
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'profit': profit,
                    'profit_percentage': round(profit_percentage, 2),  # NUEVO
                    'swap': pos.swap,
                    'commission': pos.commission,
                    'time': datetime.datetime.fromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S") if pos.time else "",  # NUEVO
                    'magic': pos.magic  # NUEVO
                })
            
            return result
            
        except Exception as e:
            self.last_error = f"Error al obtener posiciones: {str(e)}"
            return []
    
    def get_position_by_ticket(self, ticket: int) -> Optional[Dict[str, Any]]:
        """NUEVO: Obtiene una posición específica por ticket."""
        if not self._ensure_connection():
            return None
        
        try:
            positions = mt5.positions_get(ticket=ticket)
            
            if positions is None or len(positions) == 0:
                return None
            
            pos = positions[0]
            profit_percentage = 0.0
            if pos.price_open > 0:
                if pos.type == mt5.POSITION_TYPE_BUY:
                    profit_percentage = ((pos.price_current - pos.price_open) / pos.price_open) * 100
                else:
                    profit_percentage = ((pos.price_open - pos.price_current) / pos.price_open) * 100
            
            return {
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'open_price': pos.price_open,
                'current_price': pos.price_current,
                'profit': pos.profit,
                'profit_percentage': round(profit_percentage, 2),
                'swap': pos.swap,
                'commission': pos.commission,
                'sl': pos.sl,
                'tp': pos.tp,
                'time': datetime.datetime.fromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S") if pos.time else "",
                'magic': pos.magic,
                'identifier': pos.identifier
            }
            
        except Exception as e:
            self.last_error = f"Error al obtener posición {ticket}: {str(e)}"
            return None
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Obtiene órdenes pendientes."""
        if not self._ensure_connection():
            return []
        
        try:
            orders = mt5.orders_get()
            
            if orders is None:
                return []
            
            result = []
            for order in orders:
                result.append({
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': self._get_order_type_string(order.type),
                    'type_code': order.type,  # NUEVO: código numérico
                    'volume': order.volume_current,
                    'price_open': order.price_open,
                    'sl': order.sl,
                    'tp': order.tp,
                    'time_setup': datetime.datetime.fromtimestamp(order.time_setup).strftime("%Y-%m-%d %H:%M:%S") if order.time_setup else "",  # NUEVO
                    'time_expiration': datetime.datetime.fromtimestamp(order.time_expiration).strftime("%Y-%m-%d %H:%M:%S") if order.time_expiration else "",  # NUEVO
                    'comment': order.comment,  # NUEVO
                    'magic': order.magic  # NUEVO
                })
            
            return result
            
        except Exception:
            return []
    
    def close_position(self, ticket: int) -> bool:
        """Cierra una posición."""
        if not self._ensure_connection():
            return False
        
        try:
            # Obtener la posición
            position = mt5.positions_get(ticket=ticket)
            
            if not position or len(position) == 0:
                self.last_error = f"Posición {ticket} no encontrada"
                return False
            
            position = position[0]
            
            # Obtener precio actual para el cierre
            tick = mt5.symbol_info_tick(position.symbol)
            if tick is None:
                self.last_error = f"No se pudo obtener precio para {position.symbol}"
                return False
            
            # Preparar la orden de cierre
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position.ticket,
                "price": price,
                "deviation": 10,
                "magic": 234000,
                "comment": "Closed by Python App",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar la orden de cierre
            result = mt5.order_send(request)
            
            if result:
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.last_error = ""
                    return True
                else:
                    error_msg = self._get_error_message(result.retcode)
                    self.last_error = f"Error al cerrar posición ({result.retcode}): {error_msg}"
                    return False
            else:
                self.last_error = "No se recibió respuesta de MT5"
                return False
            
        except Exception as e:
            self.last_error = f"Excepción al cerrar posición: {str(e)}"
            return False
    
    def close_position_partial(self, ticket: int, volume: float) -> bool:
        """NUEVO: Cierra parcialmente una posición."""
        if not self._ensure_connection():
            return False
        
        try:
            # Obtener la posición
            position = mt5.positions_get(ticket=ticket)
            
            if not position or len(position) == 0:
                self.last_error = f"Posición {ticket} no encontrada"
                return False
            
            position = position[0]
            
            # Validar volumen
            if volume <= 0 or volume > position.volume:
                self.last_error = f"Volumen inválido. Disponible: {position.volume}"
                return False
            
            # Obtener precio actual
            tick = mt5.symbol_info_tick(position.symbol)
            if tick is None:
                self.last_error = f"No se pudo obtener precio para {position.symbol}"
                return False
            
            # Preparar la orden de cierre parcial
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": volume,
                "type": order_type,
                "position": position.ticket,
                "price": price,
                "deviation": 10,
                "magic": 234000,
                "comment": f"Partial close {volume} lots",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar la orden
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.last_error = ""
                return True
            else:
                if result:
                    error_msg = self._get_error_message(result.retcode)
                    self.last_error = f"Error ({result.retcode}): {error_msg}"
                return False
            
        except Exception as e:
            self.last_error = f"Excepción al cerrar parcialmente: {str(e)}"
            return False
    
    def cancel_order(self, ticket: int) -> bool:
        """Cancela una orden pendiente."""
        if not self._ensure_connection():
            return False
        
        try:
            # Verificar que la orden existe
            orders = mt5.orders_get(ticket=ticket)
            if not orders or len(orders) == 0:
                self.last_error = f"Orden pendiente {ticket} no encontrada"
                return False
            
            # Preparar la solicitud de cancelación
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
                "comment": "Cancelled by Python App"
            }
            
            # Enviar la solicitud
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.last_error = ""
                return True
            else:
                if result:
                    error_msg = self._get_error_message(result.retcode)
                    self.last_error = f"Error al cancelar ({result.retcode}): {error_msg}"
                return False
            
        except Exception as e:
            self.last_error = f"Excepción al cancelar orden: {str(e)}"
            return False
    
    def modify_order(self, ticket: int, price: float = None, 
                    stop_loss: float = None, take_profit: float = None) -> bool:
        """Modifica una orden pendiente."""
        if not self._ensure_connection():
            return False
        
        try:
            # Obtener la orden
            orders = mt5.orders_get(ticket=ticket)
            
            if not orders or len(orders) == 0:
                self.last_error = f"Orden {ticket} no encontrada"
                return False
            
            order = orders[0]
            
            # Validar nuevos valores
            symbol_info = mt5.symbol_info(order.symbol)
            if symbol_info:
                point = symbol_info.point
                digits = symbol_info.digits
                
                # Validar que SL/TP estén a distancia mínima
                if price is not None:
                    # Validar que el nuevo precio sea válido
                    if price <= 0:
                        self.last_error = "Precio inválido"
                        return False
                
                if stop_loss is not None and stop_loss > 0:
                    # Validar distancia mínima para SL
                    current_price = price if price is not None else order.price_open
                    sl_distance = abs(current_price - stop_loss) / point
                    if sl_distance < 10:  # Mínimo 10 pips
                        self.last_error = "SL debe estar al menos a 10 pips"
                        return False
                
                if take_profit is not None and take_profit > 0:
                    # Validar distancia mínima para TP
                    current_price = price if price is not None else order.price_open
                    tp_distance = abs(take_profit - current_price) / point
                    if tp_distance < 10:  # Mínimo 10 pips
                        self.last_error = "TP debe estar al menos a 10 pips"
                        return False
            
            # Preparar la solicitud de modificación
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "price": price if price is not None else order.price_open,
                "sl": stop_loss if stop_loss is not None else order.sl,
                "tp": take_profit if take_profit is not None else order.tp,
                "comment": "Modified by Python App"
            }
            
            # Enviar la solicitud
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.last_error = ""
                return True
            else:
                if result:
                    error_msg = self._get_error_message(result.retcode)
                    self.last_error = f"Error al modificar ({result.retcode}): {error_msg}"
                return False
            
        except Exception as e:
            self.last_error = f"Excepción al modificar orden: {str(e)}"
            return False
    
    def modify_position(self, ticket: int, stop_loss: float = None, take_profit: float = None) -> bool:
        """NUEVO: Modifica una posición abierta (SL/TP)."""
        if not self._ensure_connection():
            return False
        
        try:
            # Obtener la posición
            positions = mt5.positions_get(ticket=ticket)
            
            if not positions or len(positions) == 0:
                self.last_error = f"Posición {ticket} no encontrada"
                return False
            
            position = positions[0]
            
            # Validar nuevos valores
            symbol_info = mt5.symbol_info(position.symbol)
            if symbol_info:
                point = symbol_info.point
                
                if stop_loss is not None and stop_loss > 0:
                    # Validar dirección del SL
                    if position.type == mt5.POSITION_TYPE_BUY:
                        if stop_loss >= position.price_open:
                            self.last_error = "Para compras, SL debe estar por debajo del precio de apertura"
                            return False
                    else:
                        if stop_loss <= position.price_open:
                            self.last_error = "Para ventas, SL debe estar por encima del precio de apertura"
                            return False
                    
                    # Validar distancia mínima
                    sl_distance = abs(position.price_open - stop_loss) / point
                    if sl_distance < 10:
                        self.last_error = "SL debe estar al menos a 10 pips"
                        return False
                
                if take_profit is not None and take_profit > 0:
                    # Validar dirección del TP
                    if position.type == mt5.POSITION_TYPE_BUY:
                        if take_profit <= position.price_open:
                            self.last_error = "Para compras, TP debe estar por encima del precio de apertura"
                            return False
                    else:
                        if take_profit >= position.price_open:
                            self.last_error = "Para ventas, TP debe estar por debajo del precio de apertura"
                            return False
                    
                    # Validar distancia mínima
                    tp_distance = abs(take_profit - position.price_open) / point
                    if tp_distance < 10:
                        self.last_error = "TP debe estar al menos a 10 pips"
                        return False
            
            # Preparar la solicitud de modificación
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": stop_loss if stop_loss is not None else position.sl,
                "tp": take_profit if take_profit is not None else position.tp,
                "comment": "SL/TP modified by Python App"
            }
            
            # Enviar la solicitud
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.last_error = ""
                return True
            else:
                if result:
                    error_msg = self._get_error_message(result.retcode)
                    self.last_error = f"Error al modificar posición ({result.retcode}): {error_msg}"
                return False
            
        except Exception as e:
            self.last_error = f"Excepción al modificar posición: {str(e)}"
            return False
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Obtiene información de la cuenta."""
        if not self._ensure_connection():
            return None
        
        try:
            account_info = mt5.account_info()
            
            if account_info is None:
                return None
            
            # NUEVO: Calcular márgenes y ratios adicionales
            balance = account_info.balance
            equity = account_info.equity
            margin = account_info.margin
            free_margin = account_info.margin_free
            margin_level = account_info.margin_level if hasattr(account_info, 'margin_level') else 0
            
            # Calcular ratios
            margin_ratio = (margin / equity * 100) if equity > 0 else 0
            free_margin_ratio = (free_margin / equity * 100) if equity > 0 else 0
            profit = equity - balance
            
            return {
                'login': account_info.login,
                'name': account_info.name if hasattr(account_info, 'name') else '',  # NUEVO
                'server': account_info.server,
                'balance': balance,
                'equity': equity,
                'margin': margin,
                'free_margin': free_margin,
                'margin_level': margin_level,  # NUEVO
                'margin_ratio': round(margin_ratio, 2),  # NUEVO
                'free_margin_ratio': round(free_margin_ratio, 2),  # NUEVO
                'profit': profit,  # NUEVO
                'profit_percentage': round((profit / balance * 100), 2) if balance > 0 else 0,  # NUEVO
                'leverage': account_info.leverage,
                'currency': account_info.currency,
                'company': account_info.company if hasattr(account_info, 'company') else ''  # NUEVO
            }
            
        except Exception as e:
            self.last_error = f"Error al obtener información de cuenta: {str(e)}"
            return None
    
    def _get_order_type_string(self, order_type: int) -> str:
        """Convierte tipo de orden MT5 a string."""
        if order_type == mt5.ORDER_TYPE_BUY:
            return "MARKET_BUY"
        elif order_type == mt5.ORDER_TYPE_SELL:
            return "MARKET_SELL"
        elif order_type == mt5.ORDER_TYPE_BUY_LIMIT:
            return "LIMIT_BUY"
        elif order_type == mt5.ORDER_TYPE_SELL_LIMIT:
            return "LIMIT_SELL"
        elif order_type == mt5.ORDER_TYPE_BUY_STOP:
            return "STOP_BUY"
        elif order_type == mt5.ORDER_TYPE_SELL_STOP:
            return "STOP_SELL"
        else:
            return "UNKNOWN"
    
    def _get_error_message(self, retcode: int) -> str:
        """NUEVO: Obtiene mensaje de error legible desde código de retorno."""
        error_messages = {
            mt5.TRADE_RETCODE_REQUOTE: "Requote",
            mt5.TRADE_RETCODE_REJECT: "Orden rechazada",
            mt5.TRADE_RETCODE_CANCEL: "Orden cancelada",
            mt5.TRADE_RETCODE_PLACED: "Orden colocada",
            mt5.TRADE_RETCODE_DONE: "Orden ejecutada",
            mt5.TRADE_RETCODE_DONE_PARTIAL: "Orden ejecutada parcialmente",
            mt5.TRADE_RETCODE_ERROR: "Error común",
            mt5.TRADE_RETCODE_TIMEOUT: "Timeout",
            mt5.TRADE_RETCODE_INVALID: "Orden inválida",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "Volumen inválido",
            mt5.TRADE_RETCODE_INVALID_PRICE: "Precio inválido",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Stops inválidos",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "Trading deshabilitado",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "Mercado cerrado",
            mt5.TRADE_RETCODE_NO_MONEY: "Fondos insuficientes",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "Precio cambiado",
            mt5.TRADE_RETCODE_PRICE_OFF: "Sin precios",
            mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Expiración inválida",
            mt5.TRADE_RETCODE_ORDER_CHANGED: "Orden cambiada",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Demasiadas solicitudes",
            mt5.TRADE_RETCODE_NO_CHANGES: "Sin cambios",
            mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Servidor deshabilitó AT",
            mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "Cliente deshabilitó AT",
            mt5.TRADE_RETCODE_LOCKED: "Cuenta bloqueada",
            mt5.TRADE_RETCODE_FROZEN: "Orden congelada",
            mt5.TRADE_RETCODE_INVALID_FILL: "Tipo de llenado inválido",
            mt5.TRADE_RETCODE_CONNECTION: "Sin conexión",
            mt5.TRADE_RETCODE_ONLY_REAL: "Solo cuentas reales",
            mt5.TRADE_RETCODE_LIMIT_ORDERS: "Límite de órdenes",
            mt5.TRADE_RETCODE_LIMIT_VOLUME: "Límite de volumen",
            mt5.TRADE_RETCODE_INVALID_ORDER: "Orden inválida",
            mt5.TRADE_RETCODE_POSITION_CLOSED: "Posición ya cerrada",
            mt5.TRADE_RETCODE_INVALID_CLOSE_VOLUME: "Volumen de cierre inválido",
            mt5.TRADE_RETCODE_CLOSE_ORDER_EXIST: "Ya existe orden de cierre",
            mt5.TRADE_RETCODE_LIMIT_POSITIONS: "Límite de posiciones",
            mt5.TRADE_RETCODE_REJECT_CANCEL: "Cancelación rechazada",
            mt5.TRADE_RETCODE_LONG_ONLY: "Solo posiciones largas",
            mt5.TRADE_RETCODE_SHORT_ONLY: "Solo posiciones cortas",
            mt5.TRADE_RETCODE_CLOSE_ONLY: "Solo cierres",
            mt5.TRADE_RETCODE_FIFO_CLOSE: "Cierre FIFO",
            mt5.TRADE_RETCODE_HEDGE_PROHIBITED: "Hedge prohibido",
        }
        
        return error_messages.get(retcode, f"Código de error desconocido: {retcode}")
    
    def get_total_profit(self) -> float:
        """NUEVO: Obtiene el profit total de todas las posiciones abiertas."""
        positions = self.get_open_positions()
        return sum(pos.get('profit', 0) for pos in positions)
    
    def get_positions_count(self) -> Dict[str, int]:
        """NUEVO: Obtiene conteo de posiciones por tipo."""
        positions = self.get_open_positions()
        buy_count = sum(1 for pos in positions if pos.get('type') == 'BUY')
        sell_count = len(positions) - buy_count
        
        return {
            'total': len(positions),
            'buy': buy_count,
            'sell': sell_count
        }
    
    def shutdown(self):
        """NUEVO: Cierra la conexión con MT5."""
        try:
            mt5.shutdown()
            self.initialized = False
            self.last_error = "Desconectado"
        except:
            pass


# Función factory para crear el repositorio
def create_mt5_order_repository() -> MT5OrderRepository:
    """Crea y retorna una instancia de MT5OrderRepository."""
    return MT5OrderRepository()