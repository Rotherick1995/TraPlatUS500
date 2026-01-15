# src/domain/value_objects/money.py
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from enum import Enum


class Currency(Enum):
    """Enumeración de monedas soportadas."""
    USD = "USD"  # Dólar estadounidense
    EUR = "EUR"  # Euro
    GBP = "GBP"  # Libra esterlina
    JPY = "JPY"  #Yen japonés
    AUD = "AUD"  # Dólar australiano
    CAD = "CAD"  # Dólar canadiense
    CHF = "CHF"  # Franco suizo
    CNY = "CNY"  # Yuan chino
    BTC = "BTC"  # Bitcoin
    ETH = "ETH"  # Ethereum
    
    def __str__(self):
        return self.value
    
    @property
    def symbol(self) -> str:
        """Símbolo de la moneda."""
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'AUD': 'A$',
            'CAD': 'C$',
            'CHF': 'CHF',
            'CNY': '¥',
            'BTC': '₿',
            'ETH': 'Ξ'
        }
        return symbols.get(self.value, self.value)
    
    @property
    def decimals(self) -> int:
        """Número de decimales para mostrar."""
        if self in [Currency.JPY, Currency.CNY]:
            return 0
        elif self in [Currency.BTC, Currency.ETH]:
            return 8
        else:
            return 2


@dataclass(frozen=True)
class Money:
    """
    Value Object que representa una cantidad monetaria.
    
    Inmutable y con soporte para operaciones aritméticas,
    conversión de divisas y formateo.
    
    Atributos:
        amount (Decimal): Cantidad
        currency (Currency): Tipo de moneda
    """
    
    amount: Decimal
    currency: Currency = Currency.USD
    
    def __post_init__(self):
        """Validar y normalizar después de la inicialización."""
        # Asegurar que amount sea Decimal
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        
        # Redondear a los decimales apropiados de la moneda
        rounded = self.amount.quantize(
            Decimal(f'0.{"0" * self.currency.decimals}'),
            rounding=ROUND_HALF_UP
        )
        object.__setattr__(self, 'amount', rounded)
    
    # ===== OPERACIONES ARITMÉTICAS =====
    
    def __add__(self, other: 'Money') -> 'Money':
        """Suma de cantidades monetarias (misma moneda)."""
        if not isinstance(other, Money):
            raise TypeError("Solo se pueden sumar objetos Money")
        
        if self.currency != other.currency:
            raise ValueError("No se pueden sumar monedas diferentes")
        
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        """Resta de cantidades monetarias (misma moneda)."""
        if not isinstance(other, Money):
            raise TypeError("Solo se pueden restar objetos Money")
        
        if self.currency != other.currency:
            raise ValueError("No se pueden restar monedas diferentes")
        
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, scalar: Decimal) -> 'Money':
        """Multiplicación por un escalar."""
        if not isinstance(scalar, (Decimal, int, float)):
            raise TypeError("Solo se puede multiplicar por un número")
        
        scalar_decimal = Decimal(str(scalar))
        return Money(self.amount * scalar_decimal, self.currency)
    
    def __truediv__(self, scalar: Decimal) -> 'Money':
        """División por un escalar."""
        if not isinstance(scalar, (Decimal, int, float)):
            raise TypeError("Solo se puede dividir por un número")
        
        scalar_decimal = Decimal(str(scalar))
        if scalar_decimal == Decimal('0'):
            raise ZeroDivisionError("No se puede dividir por cero")
        
        return Money(self.amount / scalar_decimal, self.currency)
    
    def __rmul__(self, scalar: Decimal) -> 'Money':
        """Multiplicación inversa."""
        return self.__mul__(scalar)
    
    # ===== OPERACIONES DE COMPARACIÓN =====
    
    def __eq__(self, other: object) -> bool:
        """Igualdad (misma moneda y cantidad)."""
        if not isinstance(other, Money):
            return False
        
        return self.currency == other.currency and self.amount == other.amount
    
    def __lt__(self, other: 'Money') -> bool:
        """Menor que (misma moneda)."""
        if not isinstance(other, Money):
            raise TypeError("Comparación no soportada")
        
        if self.currency != other.currency:
            raise ValueError("No se pueden comparar monedas diferentes")
        
        return self.amount < other.amount
    
    def __le__(self, other: 'Money') -> bool:
        """Menor o igual que (misma moneda)."""
        if not isinstance(other, Money):
            raise TypeError("Comparación no soportada")
        
        if self.currency != other.currency:
            raise ValueError("No se pueden comparar monedas diferentes")
        
        return self.amount <= other.amount
    
    def __gt__(self, other: 'Money') -> bool:
        """Mayor que (misma moneda)."""
        if not isinstance(other, Money):
            raise TypeError("Comparación no soportada")
        
        if self.currency != other.currency:
            raise ValueError("No se pueden comparar monedas diferentes")
        
        return self.amount > other.amount
    
    def __ge__(self, other: 'Money') -> bool:
        """Mayor o igual que (misma moneda)."""
        if not isinstance(other, Money):
            raise TypeError("Comparación no soportada")
        
        if self.currency != other.currency:
            raise ValueError("No se pueden comparar monedas diferentes")
        
        return self.amount >= other.amount
    
    # ===== PROPIEDADES =====
    
    @property
    def is_positive(self) -> bool:
        """Retorna True si la cantidad es positiva."""
        return self.amount > Decimal('0')
    
    @property
    def is_negative(self) -> bool:
        """Retorna True si la cantidad es negativa."""
        return self.amount < Decimal('0')
    
    @property
    def is_zero(self) -> bool:
        """Retorna True si la cantidad es cero."""
        return self.amount == Decimal('0')
    
    @property
    def absolute(self) -> 'Money':
        """Retorna el valor absoluto."""
        return Money(abs(self.amount), self.currency)
    
    @property
    def negative(self) -> 'Money':
        """Retorna el valor negativo."""
        return Money(-self.amount, self.currency)
    
    # ===== MÉTODOS DE UTILIDAD =====
    
    def format(self, include_symbol: bool = True) -> str:
        """
        Formatea la cantidad monetaria para mostrar.
        
        Args:
            include_symbol: Incluir símbolo de moneda
        
        Returns:
            String formateado
        """
        amount_str = format(self.amount, f'.{self.currency.decimals}f')
        
        if include_symbol:
            if self.currency.symbol in ['$', '€', '£', '¥']:
                return f"{self.currency.symbol}{amount_str}"
            else:
                return f"{amount_str} {self.currency.symbol}"
        else:
            return amount_str
    
    def convert(
        self, 
        target_currency: Currency, 
        exchange_rate: Decimal
    ) -> 'Money':
        """
        Convierte a otra moneda usando una tasa de cambio.
        
        Args:
            target_currency: Moneda destino
            exchange_rate: Tasa de cambio (1 unidad de origen = X destino)
        
        Returns:
            Nueva cantidad en la moneda destino
        """
        if exchange_rate <= Decimal('0'):
            raise ValueError("La tasa de cambio debe ser positiva")
        
        converted_amount = self.amount * exchange_rate
        
        return Money(converted_amount, target_currency)
    
    def allocate(self, ratios: list) -> list['Money']:
        """
        Distribuye la cantidad según proporciones.
        
        Args:
            ratios: Lista de proporciones (ej: [3, 7] para 30%/70%)
        
        Returns:
            Lista de cantidades distribuidas
        """
        total_ratio = Decimal(str(sum(ratios)))
        
        if total_ratio <= Decimal('0'):
            raise ValueError("La suma de proporciones debe ser positiva")
        
        allocated = []
        remainder = self.amount
        
        for i, ratio in enumerate(ratios):
            if i == len(ratios) - 1:
                # Último elemento: tomar el resto
                allocated.append(Money(remainder, self.currency))
            else:
                # Calcular proporción
                share = (self.amount * Decimal(str(ratio))) / total_ratio
                share = share.quantize(
                    Decimal(f'0.{"0" * self.currency.decimals}'),
                    rounding=ROUND_HALF_UP
                )
                allocated.append(Money(share, self.currency))
                remainder -= share
        
        return allocated
    
    def split(self, parts: int) -> list['Money']:
        """
        Divide la cantidad en partes iguales.
        
        Args:
            parts: Número de partes
        
        Returns:
            Lista de cantidades iguales
        """
        if parts <= 0:
            raise ValueError("El número de partes debe ser positivo")
        
        part_amount = self.amount / Decimal(str(parts))
        part_amount = part_amount.quantize(
            Decimal(f'0.{"0" * self.currency.decimals}'),
            rounding=ROUND_HALF_UP
        )
        
        parts_list = [Money(part_amount, self.currency) for _ in range(parts - 1)]
        
        # Última parte puede diferir ligeramente por redondeo
        last_part_amount = self.amount - (part_amount * (parts - 1))
        parts_list.append(Money(last_part_amount, self.currency))
        
        return parts_list
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'amount': float(self.amount),
            'currency': self.currency.value,
            'formatted': self.format(),
            'symbol': self.currency.symbol
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Money':
        """Crea Money desde diccionario."""
        currency = Currency(data['currency']) if 'currency' in data else Currency.USD
        return cls(Decimal(str(data['amount'])), currency)
    
    @classmethod
    def zero(cls, currency: Currency = Currency.USD) -> 'Money':
        """Crea una cantidad cero."""
        return cls(Decimal('0'), currency)
    
    @classmethod
    def from_string(cls, amount_str: str, currency: Currency = Currency.USD) -> 'Money':
        """Crea Money desde string."""
        try:
            amount = Decimal(amount_str.replace(',', ''))
            return cls(amount, currency)
        except:
            raise ValueError(f"No se pudo convertir '{amount_str}' a Decimal")
    
    def __str__(self) -> str:
        """Representación string."""
        return self.format()
    
    def __repr__(self) -> str:
        """Representación formal."""
        return f"Money(amount={self.amount}, currency={self.currency})"