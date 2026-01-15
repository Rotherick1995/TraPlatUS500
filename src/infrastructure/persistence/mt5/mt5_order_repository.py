# src/infrastructure/persistence/mt5/mt5_order_repository.py

from typing import Optional, List, Dict, Any
import MetaTrader5 as mt5

from src.config.settings import DEFAULT_LOT_SIZE
from src.config.constants import get_mt5_order_type
from src.domain.repositories.abstract.order_repository import OrderRepository


class MT5OrderRepository(OrderRepository):
    """Implementación concreta de OrderRepository para MetaTrader 5."""
    
    def __init__(self):
        """Inicializa el repositorio de órdenes MT5."""
        self.initialized = False
    
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
                return True
            else:
                return False
        except Exception:
            return False
    
    def _ensure_connection(self) -> bool:
        """Verifica que haya conexión a MT5."""
        try:
            # Si no está inicializado, intentar inicializar
            if not self.initialized:
                return self.initialize()
            
            account_info = mt5.account_info()
            return account_info is not None
        except:
            return False
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = 0.0, stop_loss: float = 0.0, 
                   take_profit: float = 0.0, comment: str = "") -> Optional[int]:
        """Coloca una orden en MT5."""
        if not self._ensure_connection():
            return None
        
        try:
            # Preparar la orden
            order_type_mt5 = get_mt5_order_type(order_type)
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type_mt5,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 10,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar la orden
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return result.order
            
            return None
            
        except Exception:
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
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'commission': pos.commission
                })
            
            return result
            
        except Exception:
            return []
    
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
                    'volume': order.volume_current,
                    'price_open': order.price_open,
                    'sl': order.sl,
                    'tp': order.tp
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
                return False
            
            position = position[0]
            
            # Preparar la orden de cierre
            order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position.ticket,
                "price": mt5.symbol_info_tick(position.symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(position.symbol).ask,
                "deviation": 10,
                "magic": 234000,
                "comment": "Closed by Python",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar la orden de cierre
            result = mt5.order_send(request)
            
            return result and result.retcode == mt5.TRADE_RETCODE_DONE
            
        except Exception:
            return False
    
    def cancel_order(self, ticket: int) -> bool:
        """Cancela una orden pendiente."""
        if not self._ensure_connection():
            return False
        
        try:
            # Preparar la solicitud de cancelación
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
                "comment": "Cancelled by Python"
            }
            
            # Enviar la solicitud
            result = mt5.order_send(request)
            
            return result and result.retcode == mt5.TRADE_RETCODE_DONE
            
        except Exception:
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
                return False
            
            order = orders[0]
            
            # Preparar la solicitud de modificación
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "price": price if price is not None else order.price_open,
                "sl": stop_loss if stop_loss is not None else order.sl,
                "tp": take_profit if take_profit is not None else order.tp,
                "comment": "Modified by Python"
            }
            
            # Enviar la solicitud
            result = mt5.order_send(request)
            
            return result and result.retcode == mt5.TRADE_RETCODE_DONE
            
        except Exception:
            return False
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Obtiene información de la cuenta."""
        if not self._ensure_connection():
            return None
        
        try:
            account_info = mt5.account_info()
            
            if account_info is None:
                return None
            
            return {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'leverage': account_info.leverage,
                'currency': account_info.currency
            }
            
        except Exception:
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


# Función factory para crear el repositorio
def create_mt5_order_repository() -> MT5OrderRepository:
    """Crea y retorna una instancia de MT5OrderRepository."""
    return MT5OrderRepository()