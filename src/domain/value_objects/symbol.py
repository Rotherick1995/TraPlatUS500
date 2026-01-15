# src/domain/value_objects/symbol.py
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any
from enum import Enum


class SymbolCategory(Enum):
    """Categoría del símbolo financiero."""
    FOREX = "FOREX"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    
    def __str__(self):
        return self.value


@dataclass(frozen=True)
class Symbol:
    """
    Value Object que representa un símbolo financiero.
    
    Un símbolo es un identificador único para un instrumento financiero
    que contiene toda la información necesaria para operar con él.
    
    Atributos:
        name (str): Nombre del símbolo (ej: "EURUSD")
        category (SymbolCategory): Categoría del símbolo
        description (str): Descripción legible
        base_currency (str): Moneda base
        quote_currency (str): Moneda de cotización
        point (Decimal): Tamaño de un punto (0.00001 para Forex)
        tick_size (Decimal): Tamaño mínimo de movimiento de precio
        tick_value (Decimal): Valor monetario de un tick
        lot_size (Decimal): Tamaño estándar de un lote
        min_lot (Decimal): Lote mínimo permitido
        max_lot (Decimal): Lote máximo permitido
        lot_step (Decimal): Incremento de lote
        margin_initial (Decimal): Margen inicial requerido
        margin_maintenance (Decimal): Margen de mantenimiento
        spread_float (bool): Si el spread es flotante
        swap_long (Decimal): Swap para posiciones largas
        swap_short (Decimal): Swap para posiciones cortas
        digits (int): Número de decimales
    """
    
    # Identificación
    name: str
    category: SymbolCategory = SymbolCategory.FOREX
    
    # Información descriptiva
    description: str = ""
    base_currency: str = ""
    quote_currency: str = ""
    
    # Especificaciones de trading
    point: Decimal = Decimal('0.00001')
    tick_size: Decimal = Decimal('0.00001')
    tick_value: Decimal = Decimal('1.0')
    lot_size: Decimal = Decimal('100000.0')  # Tamaño estándar de lote Forex
    
    # Límites de volumen
    min_lot: Decimal = Decimal('0.01')
    max_lot: Decimal = Decimal('100.0')
    lot_step: Decimal = Decimal('0.01')
    
    # Requerimientos de margen
    margin_initial: Decimal = Decimal('0.01')  # 1:100 apalancamiento
    margin_maintenance: Decimal = Decimal('0.005')  # 0.5% margen mantenimiento
    
    # Costos de operación
    spread_float: bool = True
    swap_long: Decimal = Decimal('0.0')
    swap_short: Decimal = Decimal('0.0')
    
    # Formato
    digits: int = 5
    
    def __post_init__(self):
        """Validar el símbolo después de la inicialización."""
        self._validate()
    
    def _validate(self) -> None:
        """Validar los datos del símbolo."""
        if not self.name:
            raise ValueError("El nombre del símbolo no puede estar vacío")
        
        if self.point <= Decimal('0'):
            raise ValueError("El punto debe ser mayor que 0")
        
        if self.tick_size <= Decimal('0'):
            raise ValueError("El tamaño del tick debe ser mayor que 0")
        
        if self.lot_size <= Decimal('0'):
            raise ValueError("El tamaño del lote debe ser mayor que 0")
        
        if self.min_lot <= Decimal('0'):
            raise ValueError("El lote mínimo debe ser mayor que 0")
        
        if self.max_lot < self.min_lot:
            raise ValueError("El lote máximo debe ser mayor o igual al mínimo")
        
        if self.lot_step <= Decimal('0'):
            raise ValueError("El paso del lote debe ser mayor que 0")
    
    @property
    def pip_size(self) -> Decimal:
        """Tamaño de un pip (generalmente 10 puntos)."""
        return self.point * Decimal('10')
    
    @property
    def is_forex(self) -> bool:
        """Retorna True si es un par Forex."""
        return self.category == SymbolCategory.FOREX
    
    @property
    def is_crypto(self) -> bool:
        """Retorna True si es una criptomoneda."""
        return self.category == SymbolCategory.CRYPTO
    
    @property
    def currency_pair(self) -> str:
        """Retorna el par de divisas formato 'EUR/USD'."""
        if self.base_currency and self.quote_currency:
            return f"{self.base_currency}/{self.quote_currency}"
        return self.name
    
    def calculate_pip_value(self, account_currency: str = "USD") -> Decimal:
        """
        Calcula el valor de un pip en la moneda de la cuenta.
        
        Args:
            account_currency: Moneda de la cuenta
        
        Returns:
            Valor de un pip para un lote estándar
        """
        # Para pares Forex con USD como quote currency
        if self.quote_currency == account_currency:
            return Decimal('10.0')  # $10 por lote estándar
        
        # Para otros casos (simplificado)
        # En producción, esto requeriría conversión de divisas
        return Decimal('10.0')
    
    def calculate_required_margin(
        self, 
        volume: Decimal, 
        price: Decimal,
        leverage: int = 100
    ) -> Decimal:
        """
        Calcula el margen requerido para una operación.
        
        Args:
            volume: Volumen en lotes
            price: Precio de la operación
            leverage: Apalancamiento (100 = 1:100)
        
        Returns:
            Margen requerido
        """
        contract_value = volume * self.lot_size * price
        margin = contract_value / Decimal(str(leverage))
        return margin.quantize(Decimal('0.01'))
    
    def normalize_price(self, price: Decimal) -> Decimal:
        """
        Normaliza un precio según las especificaciones del símbolo.
        
        Args:
            price: Precio a normalizar
        
        Returns:
            Precio normalizado
        """
        # Redondear al número de dígitos correcto
        normalized = price.quantize(Decimal(f'0.{"0" * self.digits}'))
        
        # Asegurar que sea múltiplo del tick size
        tick_multiple = (normalized / self.tick_size).to_integral_value()
        return tick_multiple * self.tick_size
    
    def validate_volume(self, volume: Decimal) -> bool:
        """
        Valida si un volumen es válido para este símbolo.
        
        Args:
            volume: Volumen a validar
        
        Returns:
            True si el volumen es válido
        """
        if volume < self.min_lot or volume > self.max_lot:
            return False
        
        # Verificar que sea múltiplo del step
        remainder = (volume - self.min_lot) % self.lot_step
        return remainder == Decimal('0')
    
    def get_volume_step(self, volume: Decimal) -> Decimal:
        """
        Ajusta un volumen al step más cercano.
        
        Args:
            volume: Volumen a ajustar
        
        Returns:
            Volumen ajustado
        """
        if volume < self.min_lot:
            return self.min_lot
        
        if volume > self.max_lot:
            return self.max_lot
        
        # Calcular múltiplo más cercano del step
        steps = ((volume - self.min_lot) / self.lot_step).to_integral_value()
        adjusted = self.min_lot + (steps * self.lot_step)
        
        return adjusted.quantize(Decimal('0.01'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el símbolo a diccionario."""
        return {
            'name': self.name,
            'category': self.category.value,
            'description': self.description,
            'base_currency': self.base_currency,
            'quote_currency': self.quote_currency,
            'point': float(self.point),
            'tick_size': float(self.tick_size),
            'tick_value': float(self.tick_value),
            'lot_size': float(self.lot_size),
            'min_lot': float(self.min_lot),
            'max_lot': float(self.max_lot),
            'lot_step': float(self.lot_step),
            'margin_initial': float(self.margin_initial),
            'margin_maintenance': float(self.margin_maintenance),
            'spread_float': self.spread_float,
            'swap_long': float(self.swap_long),
            'swap_short': float(self.swap_short),
            'digits': self.digits,
            'pip_size': float(self.pip_size),
            'currency_pair': self.currency_pair
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Symbol':
        """Crea un Symbol desde un diccionario."""
        return cls(
            name=data['name'],
            category=SymbolCategory(data.get('category', 'FOREX')),
            description=data.get('description', ''),
            base_currency=data.get('base_currency', ''),
            quote_currency=data.get('quote_currency', ''),
            point=Decimal(str(data.get('point', 0.00001))),
            tick_size=Decimal(str(data.get('tick_size', 0.00001))),
            tick_value=Decimal(str(data.get('tick_value', 1.0))),
            lot_size=Decimal(str(data.get('lot_size', 100000.0))),
            min_lot=Decimal(str(data.get('min_lot', 0.01))),
            max_lot=Decimal(str(data.get('max_lot', 100.0))),
            lot_step=Decimal(str(data.get('lot_step', 0.01))),
            margin_initial=Decimal(str(data.get('margin_initial', 0.01))),
            margin_maintenance=Decimal(str(data.get('margin_maintenance', 0.005))),
            spread_float=data.get('spread_float', True),
            swap_long=Decimal(str(data.get('swap_long', 0.0))),
            swap_short=Decimal(str(data.get('swap_short', 0.0))),
            digits=data.get('digits', 5)
        )
    
    def __str__(self) -> str:
        """Representación string del símbolo."""
        return f"{self.name} ({self.category.value})"
    
    def __repr__(self) -> str:
        """Representación formal del símbolo."""
        return f"Symbol(name='{self.name}', category={self.category})"