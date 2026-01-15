# src/domain/entities/candle.py

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    """Entidad que representa una vela japonesa."""
    
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def is_bullish(self) -> bool:
        """Verifica si la vela es alcista."""
        return self.close > self.open
    
    def is_bearish(self) -> bool:
        """Verifica si la vela es bajista."""
        return self.close < self.open
    
    def get_body_size(self) -> float:
        """Obtiene el tamaño del cuerpo de la vela."""
        return abs(self.close - self.open)
    
    def get_wick_upper(self) -> float:
        """Obtiene el tamaño de la mecha superior."""
        return self.high - max(self.open, self.close)
    
    def get_wick_lower(self) -> float:
        """Obtiene el tamaño de la mecha inferior."""
        return min(self.open, self.close) - self.low