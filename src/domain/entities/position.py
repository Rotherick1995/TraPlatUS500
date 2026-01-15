# src/domain/entities/position.py
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from decimal import Decimal


class PositionType(Enum):
    """Tipo de posición."""
    BUY = 0
    SELL = 1
    
    def __str__(self):
        return "COMPRA" if self.value == 0 else "VENTA"
    
    @property
    def is_buy(self) -> bool:
        """Retorna True si es posición de compra."""
        return self == PositionType.BUY
    
    @property
    def is_sell(self) -> bool:
        """Retorna True si es posición de venta."""
        return self == PositionType.SELL


class PositionStatus(Enum):
    """Estado de la posición."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"
    CANCELED = "CANCELED"
    
    @property
    def is_active(self) -> bool:
        """Retorna True si la posición está activa."""
        return self in [PositionStatus.OPEN, PositionStatus.PENDING]


@dataclass
class Position:
    """
    Entidad que representa una posición de trading.
    
    Una posición es una operación abierta en el mercado que representa
    una exposición a un activo financiero.
    
    Atributos:
        ticket (int): Identificador único de la posición
        symbol (str): Símbolo del instrumento financiero
        position_type (PositionType): Tipo de posición (BUY/SELL)
        volume (Decimal): Tamaño de la posición (en lotes)
        open_price (Decimal): Precio al que se abrió la posición
        current_price (Decimal): Precio actual del instrumento
        open_time (datetime): Fecha y hora de apertura
        sl_price (Optional[Decimal]): Precio del Stop Loss
        tp_price (Optional[Decimal]): Precio del Take Profit
        swap (Decimal): Swap acumulado
        commission (Decimal): Comisión pagada
        profit (Decimal): Profit/Perdida actual
        comment (str): Comentario de la operación
        status (PositionStatus): Estado de la posición
        magic_number (Optional[int]): Número mágico (para EAs)
        close_price (Optional[Decimal]): Precio de cierre
        close_time (Optional[datetime]): Fecha y hora de cierre
    """
    
    # Identificación
    ticket: int
    symbol: str
    
    # Información de la operación
    position_type: PositionType
    volume: Decimal
    open_price: Decimal
    
    # Estado actual
    current_price: Decimal
    open_time: datetime
    
    # Niveles de protección
    sl_price: Optional[Decimal] = None
    tp_price: Optional[Decimal] = None
    
    # Costos y ganancias
    swap: Decimal = Decimal('0.0')
    commission: Decimal = Decimal('0.0')
    profit: Decimal = Decimal('0.0')
    
    # Metadatos
    comment: str = ""
    status: PositionStatus = PositionStatus.OPEN
    magic_number: Optional[int] = None
    
    # Información de cierre
    close_price: Optional[Decimal] = None
    close_time: Optional[datetime] = None
    
    # Campos calculados
    _pip_value: Optional[Decimal] = field(init=False, default=None)
    _margin_used: Optional[Decimal] = field(init=False, default=None)
    _risk_reward_ratio: Optional[Decimal] = field(init=False, default=None)
    
    def __post_init__(self):
        """Validar y normalizar datos después de la inicialización."""
        self.validate()
        self.normalize()
    
    def validate(self) -> None:
        """Validar los datos de la posición."""
        if self.ticket <= 0:
            raise ValueError("El ticket debe ser un número positivo")
        
        if not self.symbol:
            raise ValueError("El símbolo no puede estar vacío")
        
        if self.volume <= Decimal('0'):
            raise ValueError("El volumen debe ser mayor que 0")
        
        if self.open_price <= Decimal('0'):
            raise ValueError("El precio de apertura debe ser mayor que 0")
        
        if self.current_price <= Decimal('0'):
            raise ValueError("El precio actual debe ser mayor que 0")
        
        if self.sl_price and self.sl_price <= Decimal('0'):
            raise ValueError("El Stop Loss debe ser mayor que 0")
        
        if self.tp_price and self.tp_price <= Decimal('0'):
            raise ValueError("El Take Profit debe ser mayor que 0")
        
        # Validar que SL y TP estén en la dirección correcta
        if self.sl_price and self.tp_price:
            if self.position_type.is_buy:
                if self.sl_price >= self.open_price or self.tp_price <= self.open_price:
                    raise ValueError("Para posiciones BUY: SL < Precio Apertura < TP")
            else:  # SELL
                if self.sl_price <= self.open_price or self.tp_price >= self.open_price:
                    raise ValueError("Para posiciones SELL: SL > Precio Apertura > TP")
    
    def normalize(self) -> None:
        """Normalizar decimales y formatos."""
        # Asegurar que todos los Decimal tengan 5 decimales
        self.open_price = Decimal(str(self.open_price)).quantize(Decimal('0.00001'))
        self.current_price = Decimal(str(self.current_price)).quantize(Decimal('0.00001'))
        
        if self.sl_price:
            self.sl_price = Decimal(str(self.sl_price)).quantize(Decimal('0.00001'))
        
        if self.tp_price:
            self.tp_price = Decimal(str(self.tp_price)).quantize(Decimal('0.00001'))
        
        if self.close_price:
            self.close_price = Decimal(str(self.close_price)).quantize(Decimal('0.00001'))
        
        # Normalizar volumen a 2 decimales
        self.volume = Decimal(str(self.volume)).quantize(Decimal('0.01'))
        
        # Normalizar montos monetarios a 2 decimales
        self.swap = Decimal(str(self.swap)).quantize(Decimal('0.01'))
        self.commission = Decimal(str(self.commission)).quantize(Decimal('0.01'))
        self.profit = Decimal(str(self.profit)).quantize(Decimal('0.01'))
    
    @property
    def is_open(self) -> bool:
        """Retorna True si la posición está abierta."""
        return self.status == PositionStatus.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Retorna True si la posición está cerrada."""
        return self.status == PositionStatus.CLOSED
    
    @property
    def is_pending(self) -> bool:
        """Retorna True si la posición está pendiente."""
        return self.status == PositionStatus.PENDING
    
    @property
    def pip_distance_to_sl(self) -> Optional[Decimal]:
        """Calcula la distancia en pips al Stop Loss."""
        if not self.sl_price:
            return None
        
        if self.position_type.is_buy:
            return (self.open_price - self.sl_price) * Decimal('10000')
        else:
            return (self.sl_price - self.open_price) * Decimal('10000')
    
    @property
    def pip_distance_to_tp(self) -> Optional[Decimal]:
        """Calcula la distancia en pips al Take Profit."""
        if not self.tp_price:
            return None
        
        if self.position_type.is_buy:
            return (self.tp_price - self.open_price) * Decimal('10000')
        else:
            return (self.open_price - self.tp_price) * Decimal('10000')
    
    @property
    def pip_distance_to_current(self) -> Decimal:
        """Calcula la distancia en pips al precio actual."""
        if self.position_type.is_buy:
            return (self.current_price - self.open_price) * Decimal('10000')
        else:
            return (self.open_price - self.current_price) * Decimal('10000')
    
    @property
    def risk_reward_ratio(self) -> Optional[Decimal]:
        """Calcula la relación riesgo/recompensa."""
        if not self.sl_price or not self.tp_price:
            return None
        
        risk = abs(float(self.open_price - self.sl_price))
        reward = abs(float(self.tp_price - self.open_price))
        
        if risk == 0:
            return None
        
        return Decimal(str(reward / risk)).quantize(Decimal('0.01'))
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Calcula el P&L no realizado."""
        pip_value = self.calculate_pip_value()
        pip_distance = self.pip_distance_to_current
        
        return (pip_distance * pip_value * self.volume).quantize(Decimal('0.01'))
    
    @property
    def total_pnl(self) -> Decimal:
        """Calcula el P&L total (realizado + no realizado)."""
        if self.is_closed and self.close_price:
            # Para posiciones cerradas, usar profit
            return self.profit
        else:
            # Para posiciones abiertas, calcular P&L no realizado
            return self.unrealized_pnl
    
    @property
    def duration(self) -> Optional[float]:
        """Calcula la duración de la posición en horas."""
        if self.is_closed and self.close_time:
            duration = (self.close_time - self.open_time).total_seconds() / 3600
            return round(duration, 2)
        elif self.is_open:
            duration = (datetime.now() - self.open_time).total_seconds() / 3600
            return round(duration, 2)
        return None
    
    def calculate_pip_value(self, account_currency: str = "USD") -> Decimal:
        """
        Calcula el valor de un pip para esta posición.
        
        Args:
            account_currency: Moneda de la cuenta (por defecto "USD")
        
        Returns:
            Valor de un pip en la moneda de la cuenta
        """
        # Simplificación: para pares con USD como quote currency,
        # el valor del pip es $10 por lote estándar
        # En una implementación real, esto sería más complejo
        
        base_pip_value = Decimal('10.0')  # $10 por lote estándar
        pip_value = base_pip_value * self.volume
        
        # Ajustar para mini y micro lotes
        if self.volume < Decimal('0.1'):  # Micro lotes
            pip_value = pip_value / Decimal('10')
        elif self.volume < Decimal('1.0'):  # Mini lotes
            pip_value = pip_value / Decimal('100')
        
        return pip_value.quantize(Decimal('0.01'))
    
    def calculate_required_margin(
        self, 
        leverage: int = 100,
        symbol_info: Optional[Dict[str, Any]] = None
    ) -> Decimal:
        """
        Calcula el margen requerido para esta posición.
        
        Args:
            leverage: Apalancamiento de la cuenta
            symbol_info: Información del símbolo (opcional)
        
        Returns:
            Margen requerido en la moneda de la cuenta
        """
        # Fórmula simplificada: (Volume * Contract Size * Price) / Leverage
        # Para pares Forex, Contract Size suele ser 100,000 para un lote estándar
        
        contract_size = Decimal('100000.0')  # Tamaño de contrato estándar
        margin = (self.volume * contract_size * self.open_price) / Decimal(str(leverage))
        
        # Convertir a la moneda de la cuenta si es necesario
        # (simplificado para USD)
        
        return margin.quantize(Decimal('0.01'))
    
    def update_price(self, new_price: Decimal) -> None:
        """
        Actualiza el precio actual de la posición.
        
        Args:
            new_price: Nuevo precio del instrumento
        """
        if new_price <= Decimal('0'):
            raise ValueError("El nuevo precio debe ser mayor que 0")
        
        self.current_price = Decimal(str(new_price)).quantize(Decimal('0.00001'))
        
        # Recalcular profit
        self.profit = self.unrealized_pnl
    
    def check_sl_tp(self) -> Dict[str, bool]:
        """
        Verifica si se han alcanzado los niveles de SL o TP.
        
        Returns:
            Dict con 'sl_hit' y 'tp_hit' como booleanos
        """
        result = {'sl_hit': False, 'tp_hit': False}
        
        if not self.sl_price and not self.tp_price:
            return result
        
        if self.position_type.is_buy:
            if self.sl_price and self.current_price <= self.sl_price:
                result['sl_hit'] = True
            if self.tp_price and self.current_price >= self.tp_price:
                result['tp_hit'] = True
        else:  # SELL
            if self.sl_price and self.current_price >= self.sl_price:
                result['sl_hit'] = True
            if self.tp_price and self.current_price <= self.tp_price:
                result['tp_hit'] = True
        
        return result
    
    def close_position(self, close_price: Decimal, close_time: datetime = None) -> None:
        """
        Cierra la posición.
        
        Args:
            close_price: Precio al que se cierra la posición
            close_time: Fecha y hora de cierre (opcional, por defecto ahora)
        """
        if self.is_closed:
            raise ValueError("La posición ya está cerrada")
        
        if close_price <= Decimal('0'):
            raise ValueError("El precio de cierre debe ser mayor que 0")
        
        self.close_price = Decimal(str(close_price)).quantize(Decimal('0.00001'))
        self.close_time = close_time or datetime.now()
        self.status = PositionStatus.CLOSED
        
        # Calcular profit final
        self.current_price = self.close_price
        self.profit = self.unrealized_pnl
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la posición a diccionario."""
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'position_type': self.position_type.value,
            'position_type_str': str(self.position_type),
            'volume': float(self.volume),
            'open_price': float(self.open_price),
            'current_price': float(self.current_price),
            'open_time': self.open_time.isoformat(),
            'sl_price': float(self.sl_price) if self.sl_price else None,
            'tp_price': float(self.tp_price) if self.tp_price else None,
            'swap': float(self.swap),
            'commission': float(self.commission),
            'profit': float(self.profit),
            'comment': self.comment,
            'status': self.status.value,
            'magic_number': self.magic_number,
            'close_price': float(self.close_price) if self.close_price else None,
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'is_open': self.is_open,
            'pip_distance_to_sl': float(self.pip_distance_to_sl) if self.pip_distance_to_sl else None,
            'pip_distance_to_tp': float(self.pip_distance_to_tp) if self.pip_distance_to_tp else None,
            'risk_reward_ratio': float(self.risk_reward_ratio) if self.risk_reward_ratio else None,
            'duration': self.duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Crea una Position desde un diccionario."""
        return cls(
            ticket=data['ticket'],
            symbol=data['symbol'],
            position_type=PositionType(data['position_type']),
            volume=Decimal(str(data['volume'])),
            open_price=Decimal(str(data['open_price'])),
            current_price=Decimal(str(data.get('current_price', data['open_price']))),
            open_time=datetime.fromisoformat(data['open_time']),
            sl_price=Decimal(str(data['sl_price'])) if data.get('sl_price') else None,
            tp_price=Decimal(str(data['tp_price'])) if data.get('tp_price') else None,
            swap=Decimal(str(data.get('swap', 0))),
            commission=Decimal(str(data.get('commission', 0))),
            profit=Decimal(str(data.get('profit', 0))),
            comment=data.get('comment', ''),
            status=PositionStatus(data.get('status', 'OPEN')),
            magic_number=data.get('magic_number'),
            close_price=Decimal(str(data['close_price'])) if data.get('close_price') else None,
            close_time=datetime.fromisoformat(data['close_time']) if data.get('close_time') else None
        )
    
    def __str__(self) -> str:
        """Representación string de la posición."""
        status_str = "🟢 ABIERTA" if self.is_open else "🔴 CERRADA"
        type_str = "📈 COMPRA" if self.position_type.is_buy else "📉 VENTA"
        
        return (
            f"{status_str} | {type_str} | {self.symbol} | "
            f"Vol: {self.volume} | "
            f"Precio: {self.open_price:.5f} | "
            f"Profit: ${self.total_pnl:+.2f}"
        )
    
    def __repr__(self) -> str:
        """Representación formal de la posición."""
        return (
            f"Position(ticket={self.ticket}, symbol='{self.symbol}', "
            f"type={self.position_type}, volume={self.volume}, "
            f"price={self.open_price}, profit={self.profit})"
        )