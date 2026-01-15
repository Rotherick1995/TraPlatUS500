# src/domain/entities/order.py
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from decimal import Decimal
import uuid

# Importar OrderType desde el value object existente
from src.domain.value_objects.order_type import OrderType


class OrderStatus(Enum):
    """Estados de una orden."""
    PENDING = "PENDING"      # Orden pendiente de ejecución
    FILLED = "FILLED"        # Orden ejecutada completamente
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Orden ejecutada parcialmente
    CANCELED = "CANCELED"    # Orden cancelada
    REJECTED = "REJECTED"    # Orden rechazada
    EXPIRED = "EXPIRED"      # Orden expirada
    
    @property
    def is_active(self) -> bool:
        """Retorna True si la orden está activa."""
        return self in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_final(self) -> bool:
        """Retorna True si la orden está en estado final."""
        return self in [OrderStatus.FILLED, OrderStatus.CANCELED, 
                       OrderStatus.REJECTED, OrderStatus.EXPIRED]


class OrderTimeInForce(Enum):
    """Tiempo de vigencia de la orden."""
    GTC = "GTC"      # Good Till Cancel (válida hasta cancelar)
    GTD = "GTD"      # Good Till Date (válida hasta fecha)
    IOC = "IOC"      # Immediate Or Cancel (ejecutar o cancelar)
    FOK = "FOK"      # Fill Or Kill (ejecutar completamente o cancelar)
    
    @property
    def requires_expiry(self) -> bool:
        """Retorna True si requiere fecha de expiración."""
        return self == OrderTimeInForce.GTD


@dataclass
class Order:
    """
    Entidad que representa una orden de trading.
    
    Una orden es una instrucción para ejecutar una operación en el mercado,
    ya sea de forma inmediata (market) o bajo ciertas condiciones (pendiente).
    
    Atributos:
        symbol (str): Símbolo del instrumento financiero
        order_type (OrderType): Tipo de orden
        volume (Decimal): Volumen/tamaño de la orden (en lotes)
        price (Decimal): Precio de la orden
        order_id (str): Identificador único de la orden (UUID)
        ticket (Optional[int]): Ticket de la orden en el broker
        stop_loss (Optional[Decimal]): Precio de Stop Loss
        take_profit (Optional[Decimal]): Precio de Take Profit
        status (OrderStatus): Estado actual de la orden
        time_in_force (OrderTimeInForce): Tiempo de vigencia
        created_at (datetime): Fecha y hora de creación
        updated_at (datetime): Fecha y hora de última actualización
        filled_at (Optional[datetime]): Fecha y hora de ejecución
        expired_at (Optional[datetime]): Fecha y hora de expiración
        filled_price (Optional[Decimal]): Precio al que se ejecutó
        filled_volume (Decimal): Volumen ejecutado
        comment (str): Comentario de la orden
        magic_number (Optional[int]): Número mágico (para EAs)
        parent_ticket (Optional[int]): Ticket de la posición padre (para SL/TP)
        slippage (Decimal): Slippage permitido (en pips)
        deviation (int): Desviación permitida (en puntos)
    """
    
    # Información de la orden (sin valores por defecto - deben ir PRIMERO)
    symbol: str
    order_type: OrderType
    volume: Decimal
    price: Decimal
    
    # Identificación (con valores por defecto - deben ir DESPUÉS)
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticket: Optional[int] = None
    
    # Niveles de protección
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    
    # Estado
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: OrderTimeInForce = OrderTimeInForce.GTC
    
    # Tiempos
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    # Información de ejecución
    filled_price: Optional[Decimal] = None
    filled_volume: Decimal = Decimal('0.0')
    
    # Metadatos
    comment: str = ""
    magic_number: Optional[int] = None
    parent_ticket: Optional[int] = None  # Para órdenes de stop (SL/TP)
    
    # Parámetros de ejecución
    slippage: Decimal = Decimal('5.0')  # pips
    deviation: int = 10  # puntos
    
    def __post_init__(self):
        """Validar y normalizar datos después de la inicialización."""
        self.validate()
        self.normalize()
    
    def validate(self) -> None:
        """Validar los datos de la orden."""
        if not self.symbol:
            raise ValueError("El símbolo no puede estar vacío")
        
        if self.volume <= Decimal('0'):
            raise ValueError("El volumen debe ser mayor que 0")
        
        if self.price <= Decimal('0'):
            raise ValueError("El precio debe ser mayor que 0")
        
        if self.stop_loss and self.stop_loss <= Decimal('0'):
            raise ValueError("El Stop Loss debe ser mayor que 0")
        
        if self.take_profit and self.take_profit <= Decimal('0'):
            raise ValueError("El Take Profit debe ser mayor que 0")
        
        # Validar órdenes pendientes
        if self.order_type.is_pending():
            if self.order_type.is_buy():
                # BUY LIMIT debe estar por debajo del precio actual
                # BUY STOP debe estar por encima del precio actual
                pass  # Se validaría contra el precio de mercado
            else:  # SELL
                # SELL LIMIT debe estar por encima del precio actual
                # SELL STOP debe estar por debajo del precio actual
                pass  # Se validaría contra el precio de mercado
        
        # Validar tiempo de vigencia
        if self.time_in_force.requires_expiry and not self.expired_at:
            raise ValueError(f"La orden {self.time_in_force.value} requiere fecha de expiración")
        
        # Validar órdenes de stop (SL/TP)
        if self.order_type.is_stop_order() and not self.parent_ticket:
            raise ValueError("Las órdenes de stop requieren un parent_ticket")
    
    def normalize(self) -> None:
        """Normalizar decimales y formatos."""
        # Asegurar que todos los Decimal tengan 5 decimales
        self.price = Decimal(str(self.price)).quantize(Decimal('0.00001'))
        
        if self.stop_loss:
            self.stop_loss = Decimal(str(self.stop_loss)).quantize(Decimal('0.00001'))
        
        if self.take_profit:
            self.take_profit = Decimal(str(self.take_profit)).quantize(Decimal('0.00001'))
        
        if self.filled_price:
            self.filled_price = Decimal(str(self.filled_price)).quantize(Decimal('0.00001'))
        
        # Normalizar volumen a 2 decimales
        self.volume = Decimal(str(self.volume)).quantize(Decimal('0.01'))
        self.filled_volume = Decimal(str(self.filled_volume)).quantize(Decimal('0.01'))
        
        # Normalizar slippage
        self.slippage = Decimal(str(self.slippage)).quantize(Decimal('0.1'))
    
    @property
    def is_active(self) -> bool:
        """Retorna True si la orden está activa."""
        return self.status.is_active
    
    @property
    def is_filled(self) -> bool:
        """Retorna True si la orden está ejecutada."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_pending_execution(self) -> bool:
        """Retorna True si es una orden pendiente de ejecución."""
        return self.status == OrderStatus.PENDING
    
    @property
    def is_partially_filled(self) -> bool:
        """Retorna True si la orden está parcialmente ejecutada."""
        return self.status == OrderStatus.PARTIALLY_FILLED
    
    @property
    def remaining_volume(self) -> Decimal:
        """Retorna el volumen pendiente de ejecución."""
        return max(Decimal('0.0'), self.volume - self.filled_volume)
    
    @property
    def fill_percentage(self) -> Decimal:
        """Retorna el porcentaje de ejecución."""
        if self.volume == Decimal('0'):
            return Decimal('0.0')
        return (self.filled_volume / self.volume * Decimal('100')).quantize(Decimal('0.01'))
    
    @property
    def is_completely_filled(self) -> bool:
        """Retorna True si la orden está completamente ejecutada."""
        return self.filled_volume >= self.volume
    
    @property
    def expiration_status(self) -> Optional[str]:
        """Retorna el estado de expiración."""
        if not self.expired_at:
            return None
        
        if datetime.now() > self.expired_at:
            return "EXPIRED"
        else:
            time_left = self.expired_at - datetime.now()
            hours = time_left.total_seconds() / 3600
            return f"EXPIRES_IN_{hours:.1f}_HOURS"
    
    def calculate_required_margin(
        self, 
        leverage: int = 100,
        symbol_info: Optional[Dict[str, Any]] = None
    ) -> Decimal:
        """
        Calcula el margen requerido para esta orden.
        
        Args:
            leverage: Apalancamiento de la cuenta
            symbol_info: Información del símbolo (opcional)
        
        Returns:
            Margen requerido en la moneda de la cuenta
        """
        # Fórmula simplificada: (Volume * Contract Size * Price) / Leverage
        contract_size = Decimal('100000.0')  # Tamaño de contrato estándar
        
        # Para órdenes pendientes, usar el precio de la orden
        execution_price = self.price
        
        margin = (self.volume * contract_size * execution_price) / Decimal(str(leverage))
        
        return margin.quantize(Decimal('0.01'))
    
    def calculate_potential_profit(
        self, 
        current_price: Optional[Decimal] = None
    ) -> Optional[Decimal]:
        """
        Calcula el profit potencial basado en TP/SL.
        
        Args:
            current_price: Precio actual (opcional)
        
        Returns:
            Profit potencial en la moneda de la cuenta
        """
        if not self.take_profit or not self.stop_loss:
            return None
        
        # Para órdenes de compra
        if self.order_type.is_buy():
            if self.take_profit and self.stop_loss:
                risk = abs(float(self.price - self.stop_loss))
                reward = abs(float(self.take_profit - self.price))
                risk_reward_ratio = reward / risk if risk > 0 else 0
                
                # Calcular profit en dinero
                pip_value = self._calculate_pip_value()
                pip_distance = abs(float(self.take_profit - self.price)) * 10000
                potential_profit = Decimal(str(pip_distance * float(pip_value) * float(self.volume)))
                
                return potential_profit.quantize(Decimal('0.01'))
        
        # Para órdenes de venta
        else:
            if self.take_profit and self.stop_loss:
                risk = abs(float(self.stop_loss - self.price))
                reward = abs(float(self.price - self.take_profit))
                risk_reward_ratio = reward / risk if risk > 0 else 0
                
                # Calcular profit en dinero
                pip_value = self._calculate_pip_value()
                pip_distance = abs(float(self.price - self.take_profit)) * 10000
                potential_profit = Decimal(str(pip_distance * float(pip_value) * float(self.volume)))
                
                return potential_profit.quantize(Decimal('0.01'))
        
        return None
    
    def _calculate_pip_value(self, account_currency: str = "USD") -> Decimal:
        """Calcula el valor de un pip."""
        base_pip_value = Decimal('10.0')  # $10 por lote estándar
        pip_value = base_pip_value * self.volume
        
        if self.volume < Decimal('0.1'):  # Micro lotes
            pip_value = pip_value / Decimal('10')
        elif self.volume < Decimal('1.0'):  # Mini lotes
            pip_value = pip_value / Decimal('100')
        
        return pip_value.quantize(Decimal('0.01'))
    
    def update_status(
        self, 
        new_status: OrderStatus,
        filled_price: Optional[Decimal] = None,
        filled_volume: Optional[Decimal] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Actualiza el estado de la orden.
        
        Args:
            new_status: Nuevo estado de la orden
            filled_price: Precio de ejecución (si aplica)
            filled_volume: Volumen ejecutado (si aplica)
            timestamp: Timestamp de la actualización
        """
        self.status = new_status
        self.updated_at = timestamp or datetime.now()
        
        if filled_price:
            self.filled_price = Decimal(str(filled_price)).quantize(Decimal('0.00001'))
        
        if filled_volume:
            self.filled_volume = Decimal(str(filled_volume)).quantize(Decimal('0.01'))
        
        # Si la orden está ejecutada, registrar tiempo
        if new_status == OrderStatus.FILLED and not self.filled_at:
            self.filled_at = self.updated_at
        
        # Si la orden es cancelada/rechazada/expirada
        if new_status in [OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
            self.filled_at = self.filled_at or self.updated_at
    
    def fill_partial(
        self, 
        filled_price: Decimal,
        filled_volume: Decimal,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Ejecuta parcialmente la orden.
        
        Args:
            filled_price: Precio de ejecución
            filled_volume: Volumen ejecutado
            timestamp: Timestamp de la ejecución
        """
        if filled_volume <= Decimal('0'):
            raise ValueError("El volumen ejecutado debe ser mayor que 0")
        
        if filled_volume > self.remaining_volume:
            raise ValueError("El volumen ejecutado excede el volumen pendiente")
        
        # Actualizar volumen ejecutado
        self.filled_volume += filled_volume
        
        # Actualizar estado
        if self.is_completely_filled:
            self.update_status(
                OrderStatus.FILLED,
                filled_price=filled_price,
                filled_volume=self.filled_volume,
                timestamp=timestamp
            )
        else:
            self.update_status(
                OrderStatus.PARTIALLY_FILLED,
                filled_price=filled_price,
                filled_volume=self.filled_volume,
                timestamp=timestamp
            )
    
    def cancel(self, reason: str = "Cancelado por usuario") -> None:
        """Cancela la orden."""
        if self.status.is_final:
            raise ValueError(f"No se puede cancelar una orden en estado {self.status.value}")
        
        self.comment = f"{self.comment} | {reason}"
        self.update_status(OrderStatus.CANCELED)
    
    def reject(self, reason: str) -> None:
        """Rechaza la orden."""
        if self.status.is_final:
            raise ValueError(f"No se puede rechazar una orden en estado {self.status.value}")
        
        self.comment = f"{self.comment} | {reason}"
        self.update_status(OrderStatus.REJECTED)
    
    def check_expiration(self) -> bool:
        """Verifica si la orden ha expirado."""
        if self.expired_at and datetime.now() > self.expired_at:
            self.update_status(OrderStatus.EXPIRED)
            return True
        return False
    
    def check_execution_conditions(
        self, 
        current_price: Decimal,
        bid_price: Decimal,
        ask_price: Decimal
    ) -> Dict[str, bool]:
        """
        Verifica si se cumplen las condiciones de ejecución.
        
        Args:
            current_price: Precio actual del instrumento
            bid_price: Precio bid actual
            ask_price: Precio ask actual
        
        Returns:
            Dict con condiciones verificadas
        """
        conditions = {
            'can_execute': False,
            'is_below_price': False,
            'is_above_price': False,
            'touches_price': False
        }
        
        if not self.is_active:
            return conditions
        
        # Para órdenes pendientes
        if self.order_type.is_pending():
            if self.order_type == OrderType.BUY_LIMIT:
                # BUY LIMIT: ejecutar cuando el precio baja hasta el nivel
                conditions['is_below_price'] = ask_price <= self.price
                conditions['can_execute'] = conditions['is_below_price']
            
            elif self.order_type == OrderType.SELL_LIMIT:
                # SELL LIMIT: ejecutar cuando el precio sube hasta el nivel
                conditions['is_above_price'] = bid_price >= self.price
                conditions['can_execute'] = conditions['is_above_price']
            
            elif self.order_type == OrderType.BUY_STOP:
                # BUY STOP: ejecutar cuando el precio sube hasta el nivel
                conditions['is_above_price'] = ask_price >= self.price
                conditions['can_execute'] = conditions['is_above_price']
            
            elif self.order_type == OrderType.SELL_STOP:
                # SELL STOP: ejecutar cuando el precio baja hasta el nivel
                conditions['is_below_price'] = bid_price <= self.price
                conditions['can_execute'] = conditions['is_below_price']
        
        # Para órdenes de mercado, siempre pueden ejecutarse
        elif self.order_type.is_market():
            conditions['can_execute'] = True
        
        return conditions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la orden a diccionario."""
        return {
            'order_id': self.order_id,
            'ticket': self.ticket,
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'order_type_str': str(self.order_type),
            'volume': float(self.volume),
            'price': float(self.price),
            'stop_loss': float(self.stop_loss) if self.stop_loss else None,
            'take_profit': float(self.take_profit) if self.take_profit else None,
            'status': self.status.value,
            'time_in_force': self.time_in_force.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'expired_at': self.expired_at.isoformat() if self.expired_at else None,
            'filled_price': float(self.filled_price) if self.filled_price else None,
            'filled_volume': float(self.filled_volume),
            'remaining_volume': float(self.remaining_volume),
            'fill_percentage': float(self.fill_percentage),
            'comment': self.comment,
            'magic_number': self.magic_number,
            'parent_ticket': self.parent_ticket,
            'slippage': float(self.slippage),
            'deviation': self.deviation,
            'is_active': self.is_active,
            'is_filled': self.is_filled,
            'expiration_status': self.expiration_status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Crea una Order desde un diccionario."""
        # Convertir strings a enums
        from src.domain.value_objects.order_type import OrderType as OrderTypeVO
        
        order_type = OrderTypeVO(data['order_type']) if 'order_type' in data else OrderTypeVO.MARKET_BUY
        status = OrderStatus(data['status']) if 'status' in data else OrderStatus.PENDING
        time_in_force = OrderTimeInForce(data.get('time_in_force', 'GTC'))
        
        # Parsear fechas
        created_at = datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now()
        updated_at = datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now()
        
        filled_at = None
        if data.get('filled_at'):
            filled_at = datetime.fromisoformat(data['filled_at'])
        
        expired_at = None
        if data.get('expired_at'):
            expired_at = datetime.fromisoformat(data['expired_at'])
        
        return cls(
            symbol=data['symbol'],
            order_type=order_type,
            volume=Decimal(str(data['volume'])),
            price=Decimal(str(data['price'])),
            order_id=data.get('order_id', str(uuid.uuid4())),
            ticket=data.get('ticket'),
            stop_loss=Decimal(str(data['stop_loss'])) if data.get('stop_loss') else None,
            take_profit=Decimal(str(data['take_profit'])) if data.get('take_profit') else None,
            status=status,
            time_in_force=time_in_force,
            created_at=created_at,
            updated_at=updated_at,
            filled_at=filled_at,
            expired_at=expired_at,
            filled_price=Decimal(str(data['filled_price'])) if data.get('filled_price') else None,
            filled_volume=Decimal(str(data.get('filled_volume', 0))),
            comment=data.get('comment', ''),
            magic_number=data.get('magic_number'),
            parent_ticket=data.get('parent_ticket'),
            slippage=Decimal(str(data.get('slippage', 5.0))),
            deviation=data.get('deviation', 10)
        )
    
    def __str__(self) -> str:
        """Representación string de la orden."""
        status_icon = "🟡" if self.is_active else "🟢" if self.is_filled else "🔴"
        type_str = str(self.order_type)
        
        return (
            f"{status_icon} {type_str} | {self.symbol} | "
            f"Vol: {self.volume} | "
            f"Precio: {self.price:.5f} | "
            f"Estado: {self.status.value}"
        )
    
    def __repr__(self) -> str:
        """Representación formal de la orden."""
        return (
            f"Order(order_id='{self.order_id}', symbol='{self.symbol}', "
            f"type={self.order_type}, volume={self.volume}, "
            f"price={self.price}, status={self.status})"
        )


class OrderFactory:
    """Factory para crear diferentes tipos de órdenes."""
    
    @staticmethod
    def create_market_order(
        symbol: str,
        is_buy: bool,
        volume: Decimal,
        price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        comment: str = "",
        magic_number: Optional[int] = None,
        slippage: Decimal = Decimal('5.0')
    ) -> Order:
        """Crea una orden de mercado."""
        from src.domain.value_objects.order_type import OrderType
        
        order_type = OrderType.MARKET_BUY if is_buy else OrderType.MARKET_SELL
        
        return Order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=comment,
            magic_number=magic_number,
            slippage=slippage
        )
    
    @staticmethod
    def create_limit_order(
        symbol: str,
        is_buy: bool,
        volume: Decimal,
        limit_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        comment: str = "",
        magic_number: Optional[int] = None,
        expired_at: Optional[datetime] = None
    ) -> Order:
        """Crea una orden límite."""
        from src.domain.value_objects.order_type import OrderType
        
        order_type = OrderType.BUY_LIMIT if is_buy else OrderType.SELL_LIMIT
        
        order = Order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=comment,
            magic_number=magic_number
        )
        
        if expired_at:
            order.expired_at = expired_at
            order.time_in_force = OrderTimeInForce.GTD
        
        return order
    
    @staticmethod
    def create_stop_order(
        symbol: str,
        is_buy: bool,
        volume: Decimal,
        stop_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        comment: str = "",
        magic_number: Optional[int] = None,
        expired_at: Optional[datetime] = None
    ) -> Order:
        """Crea una orden stop."""
        from src.domain.value_objects.order_type import OrderType
        
        order_type = OrderType.BUY_STOP if is_buy else OrderType.SELL_STOP
        
        order = Order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=stop_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=comment,
            magic_number=magic_number
        )
        
        if expired_at:
            order.expired_at = expired_at
            order.time_in_force = OrderTimeInForce.GTD
        
        return order
    
    @staticmethod
    def create_stop_loss_order(
        parent_ticket: int,
        symbol: str,
        stop_price: Decimal,
        volume: Optional[Decimal] = None,
        comment: str = ""
    ) -> Order:
        """Crea una orden de Stop Loss."""
        from src.domain.value_objects.order_type import OrderType
        
        return Order(
            symbol=symbol,
            order_type=OrderType.STOP_LOSS,
            volume=volume or Decimal('0.0'),  # Mismo volumen que la posición
            price=stop_price,
            parent_ticket=parent_ticket,
            comment=f"SL for {parent_ticket} | {comment}"
        )
    
    @staticmethod
    def create_take_profit_order(
        parent_ticket: int,
        symbol: str,
        profit_price: Decimal,
        volume: Optional[Decimal] = None,
        comment: str = ""
    ) -> Order:
        """Crea una orden de Take Profit."""
        from src.domain.value_objects.order_type import OrderType
        
        return Order(
            symbol=symbol,
            order_type=OrderType.TAKE_PROFIT,
            volume=volume or Decimal('0.0'),  # Mismo volumen que la posición
            price=profit_price,
            parent_ticket=parent_ticket,
            comment=f"TP for {parent_ticket} | {comment}"
        )