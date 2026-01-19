# src/domain/indicators/rsi_indicator.py
import numpy as np
from typing import Optional
from .base_indicator import BaseIndicator, IndicatorType, IndicatorResult


class RSIIndicator(BaseIndicator):
    """Indicador de Índice de Fuerza Relativa."""
    
    def __init__(self, period: int = 14, overbought: int = 80, oversold: int = 20):
        super().__init__(name=f"RSI({period})", type=IndicatorType.OSCILLATOR)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.set_config(
            color="#ffaa00", 
            line_width=2.0, 
            period=period,
            overbought=overbought,
            oversold=oversold
        )
    
    def calculate(self, closes: np.ndarray, highs: Optional[np.ndarray] = None, 
                  lows: Optional[np.ndarray] = None, **kwargs) -> IndicatorResult:
        """
        Calcular RSI.
        
        Args:
            closes: Array de precios de cierre
            highs: No usado para RSI
            lows: No usado para RSI
            
        Returns:
            IndicatorResult con valores RSI
        """
        if not self.validate_input(closes, self.period + 1):
            return self.create_result(
                values=np.array([]),
                timestamps=[]
            )
        
        # Calcular RSI
        rsi_values = self._calculate_rsi(closes, self.period)
        
        # Crear timestamps (asumiendo 1 por dato)
        timestamps = list(range(len(closes)))
        
        return self.create_result(
            values=rsi_values,
            timestamps=timestamps
        )
    
    def get_required_min_length(self) -> int:
        return self.period + 1