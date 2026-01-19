# src/domain/indicators/sma_indicator.py
import numpy as np
from typing import Optional
from .base_indicator import BaseIndicator, IndicatorType, IndicatorResult


class SMAIndicator(BaseIndicator):
    """Indicador de Media Móvil Simple."""
    
    def __init__(self, period: int = 20):
        super().__init__(name=f"SMA({period})", type=IndicatorType.OVERLAY)
        self.period = period
        self.set_config(color="#ffff00", line_width=1.5, period=period)
    
    def calculate(self, closes: np.ndarray, highs: Optional[np.ndarray] = None, 
                  lows: Optional[np.ndarray] = None, **kwargs) -> IndicatorResult:
        """
        Calcular Media Móvil Simple.
        
        Args:
            closes: Array de precios de cierre
            highs: No usado para SMA
            lows: No usado para SMA
            
        Returns:
            IndicatorResult con valores SMA
        """
        if not self.validate_input(closes, self.period):
            return self.create_result(
                values=np.array([]),
                timestamps=[]
            )
        
        # Calcular SMA
        sma_values = self._calculate_sma(closes, self.period)
        
        # Crear timestamps (asumiendo 1 por dato)
        timestamps = list(range(len(closes)))
        
        return self.create_result(
            values=sma_values,
            timestamps=timestamps
        )
    
    def get_required_min_length(self) -> int:
        return self.period