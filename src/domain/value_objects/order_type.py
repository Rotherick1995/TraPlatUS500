# src/domain/value_objects/order_type.py
from enum import Enum
from typing import Dict, Any, Optional


class OrderType(Enum):
    """
    Value Object que representa el tipo de orden.
    
    Define los diferentes tipos de órdenes disponibles en el trading.
    """
    
    # Órdenes de mercado (ejecución inmediata)
    MARKET_BUY = 0
    MARKET_SELL = 1
    
    # Órdenes pendientes
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5
    
    # Órdenes de stop para cierre
    STOP_LOSS = 6
    TAKE_PROFIT = 7
    
    def __str__(self) -> str:
        """Representación legible."""
        names = {
            0: "MARKET BUY",
            1: "MARKET SELL",
            2: "BUY LIMIT",
            3: "SELL LIMIT",
            4: "BUY STOP",
            5: "SELL STOP",
            6: "STOP LOSS",
            7: "TAKE PROFIT"
        }
        return names.get(self.value, "UNKNOWN")
    
    @property
    def short_name(self) -> str:
        """Nombre corto."""
        names = {
            0: "MKT BUY",
            1: "MKT SELL",
            2: "BUY LIM",
            3: "SELL LIM",
            4: "BUY STP",
            5: "SELL STP",
            6: "SL",
            7: "TP"
        }
        return names.get(self.value, "UNK")
    
    @property
    def is_market(self) -> bool:
        """Retorna True si es orden de mercado."""
        return self in [OrderType.MARKET_BUY, OrderType.MARKET_SELL]
    
    @property
    def is_pending(self) -> bool:
        """Retorna True si es orden pendiente."""
        return self in [OrderType.BUY_LIMIT, OrderType.SELL_LIMIT,
                       OrderType.BUY_STOP, OrderType.SELL_STOP]
    
    @property
    def is_stop_order(self) -> bool:
        """Retorna True si es orden de stop (SL/TP)."""
        return self in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]
    
    @property
    def is_buy(self) -> bool:
        """Retorna True si es orden de compra."""
        return self in [OrderType.MARKET_BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]
    
    @property
    def is_sell(self) -> bool:
        """Retorna True si es orden de venta."""
        return self in [OrderType.MARKET_SELL, OrderType.SELL_LIMIT, OrderType.SELL_STOP]
    
    @property
    def is_limit(self) -> bool:
        """Retorna True si es orden límite."""
        return self in [OrderType.BUY_LIMIT, OrderType.SELL_LIMIT]
    
    @property
    def is_stop(self) -> bool:
        """Retorna True si es orden stop."""
        return self in [OrderType.BUY_STOP, OrderType.SELL_STOP]
    
    @property
    def direction_symbol(self) -> str:
        """Símbolo de dirección."""
        return "📈" if self.is_buy else "📉"
    
    @property
    def execution_type(self) -> str:
        """Tipo de ejecución."""
        if self.is_market:
            return "IMMEDIATE"
        elif self.is_pending:
            return "PENDING"
        else:
            return "CONDITIONAL"
    
    def get_description(self) -> str:
        """Descripción detallada."""
        descriptions = {
            0: "Compra al precio de mercado actual",
            1: "Venta al precio de mercado actual",
            2: "Compra cuando el precio baja al nivel especificado",
            3: "Venta cuando el precio sube al nivel especificado",
            4: "Compra cuando el precio sube al nivel especificado",
            5: "Venta cuando el precio baja al nivel especificado",
            6: "Cierra posición cuando alcanza pérdida máxima",
            7: "Cierra posición cuando alcanza ganancia objetivo"
        }
        return descriptions.get(self.value, "Tipo de orden no especificado")
    
    def get_execution_condition(self, price: float, current_price: float) -> str:
        """
        Retorna la condición de ejecución.
        
        Args:
            price: Precio de la orden
            current_price: Precio actual
        
        Returns:
            Condición de ejecución
        """
        if self.is_market:
            return "Ejecución inmediata"
        
        elif self == OrderType.BUY_LIMIT:
            if current_price > price:
                return f"Ejecutar cuando precio BAJE a {price}"
            else:
                return f"Precio actual ({current_price}) ya está por debajo del límite ({price})"
        
        elif self == OrderType.SELL_LIMIT:
            if current_price < price:
                return f"Ejecutar cuando precio SUBA a {price}"
            else:
                return f"Precio actual ({current_price}) ya está por encima del límite ({price})"
        
        elif self == OrderType.BUY_STOP:
            if current_price < price:
                return f"Ejecutar cuando precio SUBA a {price}"
            else:
                return f"Precio actual ({current_price}) ya está por encima del stop ({price})"
        
        elif self == OrderType.SELL_STOP:
            if current_price > price:
                return f"Ejecutar cuando precio BAJE a {price}"
            else:
                return f"Precio actual ({current_price}) ya está por debajo del stop ({price})"
        
        elif self == OrderType.STOP_LOSS:
            return f"Cerrar posición cuando precio alcance {price}"
        
        elif self == OrderType.TAKE_PROFIT:
            return f"Cerrar posición cuando precio alcance {price}"
        
        return "Condición no definida"
    
    @classmethod
    def from_string(cls, value: str) -> 'OrderType':
        """
        Crea desde string.
        
        Args:
            value: String como "MARKET_BUY", "BUY_LIMIT", etc.
        
        Returns:
            Instancia de OrderType
        """
        value = value.upper()
        
        # Mapeo de nombres alternativos
        mapping = {
            'MARKETBUY': 'MARKET_BUY',
            'MARKETSELL': 'MARKET_SELL',
            'BUYLIMIT': 'BUY_LIMIT',
            'SELLLIMIT': 'SELL_LIMIT',
            'BUYSTOP': 'BUY_STOP',
            'SELLSTOP': 'SELL_STOP',
            'STOPLOSS': 'STOP_LOSS',
            'TAKEPROFIT': 'TAKE_PROFIT',
            'SL': 'STOP_LOSS',
            'TP': 'TAKE_PROFIT',
            'M_BUY': 'MARKET_BUY',
            'M_SELL': 'MARKET_SELL'
        }
        
        normalized = mapping.get(value, value)
        
        try:
            return cls[normalized]
        except KeyError:
            # Intentar por valor numérico
            try:
                return cls(int(value))
            except:
                raise ValueError(f"OrderType '{value}' no válido")
    
    @classmethod
    def from_mt5_order_type(cls, mt5_type: int) -> 'OrderType':
        """
        Convierte desde tipo de orden MT5.
        
        Args:
            mt5_type: Tipo de orden de MT5
        
        Returns:
            OrderType correspondiente
        """
        mapping = {
            0: cls.MARKET_BUY,
            1: cls.MARKET_SELL,
            2: cls.BUY_LIMIT,
            3: cls.SELL_LIMIT,
            4: cls.BUY_STOP,
            5: cls.SELL_STOP
        }
        return mapping.get(mt5_type, cls.MARKET_BUY)
    
    def to_mt5_order_type(self) -> int:
        """
        Convierte a tipo de orden MT5.
        
        Returns:
            Tipo de orden MT5
        """
        mapping = {
            OrderType.MARKET_BUY: 0,
            OrderType.MARKET_SELL: 1,
            OrderType.BUY_LIMIT: 2,
            OrderType.SELL_LIMIT: 3,
            OrderType.BUY_STOP: 4,
            OrderType.SELL_STOP: 5
        }
        return mapping.get(self, 0)
    
    @classmethod
    def market_orders(cls) -> list['OrderType']:
        """Retorna todos los tipos de órdenes de mercado."""
        return [cls.MARKET_BUY, cls.MARKET_SELL]
    
    @classmethod
    def pending_orders(cls) -> list['OrderType']:
        """Retorna todos los tipos de órdenes pendientes."""
        return [cls.BUY_LIMIT, cls.SELL_LIMIT, cls.BUY_STOP, cls.SELL_STOP]
    
    @classmethod
    def stop_orders(cls) -> list['OrderType']:
        """Retorna órdenes de stop (SL/TP)."""
        return [cls.STOP_LOSS, cls.TAKE_PROFIT]
    
    @classmethod
    def buy_orders(cls) -> list['OrderType']:
        """Retorna todos los tipos de órdenes de compra."""
        return [order_type for order_type in cls if order_type.is_buy]
    
    @classmethod
    def sell_orders(cls) -> list['OrderType']:
        """Retorna todos los tipos de órdenes de venta."""
        return [order_type for order_type in cls if order_type.is_sell]
    
    def get_opposite_type(self) -> Optional['OrderType']:
        """Retorna el tipo de orden opuesto."""
        opposites = {
            OrderType.MARKET_BUY: OrderType.MARKET_SELL,
            OrderType.MARKET_SELL: OrderType.MARKET_BUY,
            OrderType.BUY_LIMIT: OrderType.SELL_LIMIT,
            OrderType.SELL_LIMIT: OrderType.BUY_LIMIT,
            OrderType.BUY_STOP: OrderType.SELL_STOP,
            OrderType.SELL_STOP: OrderType.BUY_STOP
        }
        return opposites.get(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'value': self.value,
            'name': str(self),
            'short_name': self.short_name,
            'is_market': self.is_market,
            'is_pending': self.is_pending,
            'is_stop_order': self.is_stop_order,
            'is_buy': self.is_buy,
            'is_sell': self.is_sell,
            'is_limit': self.is_limit,
            'is_stop': self.is_stop,
            'direction_symbol': self.direction_symbol,
            'execution_type': self.execution_type,
            'description': self.get_description()
        }