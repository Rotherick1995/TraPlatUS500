# src/domain/indicators/ema_indicator.py
import numpy as np
from typing import Optional
from .base_indicator import BaseIndicator, IndicatorType, IndicatorResult


class EMAIndicator(BaseIndicator):
    """Indicador de Media Móvil Exponencial."""
    
    def __init__(self, period: int = 12):
        super().__init__(name=f"EMA({period})", type=IndicatorType.OVERLAY)
        self.period = period
        self.set_config(color="#ff00ff", line_width=1.5, period=period)
    
    def calculate(self, closes: np.ndarray, highs: Optional[np.ndarray] = None, 
                  lows: Optional[np.ndarray] = None, **kwargs) -> IndicatorResult:
        """
        Calcular Media Móvil Exponencial.
        
        Args:
            closes: Array de precios de cierre
            highs: No usado para EMA
            lows: No usado para EMA
            
        Returns:
            IndicatorResult con valores EMA
        """
        if not self.validate_input(closes, self.period):
            return self.create_result(
                values=np.array([]),
                timestamps=[]
            )
        
        # Calcular EMA
        ema_values = self._calculate_ema(closes, self.period)
        
        # Crear timestamps (asumiendo 1 por dato)
        timestamps = list(range(len(closes)))
        
        return self.create_result(
            values=ema_values,
            timestamps=timestamps
        )
    
    def get_required_min_length(self) -> int:
        return self.period