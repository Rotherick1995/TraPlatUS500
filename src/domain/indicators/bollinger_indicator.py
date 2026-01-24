# src/domain/indicators/bollinger_indicator.py
import numpy as np
from typing import Optional, Dict
from .base_indicator import BaseIndicator, IndicatorType, IndicatorResult, IndicatorConfig


class BollingerIndicator(BaseIndicator):
    """Indicador de Bandas de Bollinger."""
    
    def __init__(self, period: int = 40, std_multiplier: float = 3.0):
        super().__init__(name=f"BB({period},{std_multiplier})", type=IndicatorType.OVERLAY)
        self.period = period
        self.std_multiplier = std_multiplier
        
        # Configurar colores para las tres líneas
        self.set_config(
            color="#ffffff",  # Color para la banda media
            line_width=1.0,
            period=period,
            std_multiplier=std_multiplier,
            upper_color="#00ffff",
            lower_color="#00ffff"
        )
    
    def calculate(self, closes: np.ndarray, highs: Optional[np.ndarray] = None, 
                  lows: Optional[np.ndarray] = None, **kwargs) -> IndicatorResult:
        """
        Calcular Bandas de Bollinger.
        
        Args:
            closes: Array de precios de cierre
            highs: No usado para Bollinger
            lows: No usado para Bollinger
            
        Returns:
            IndicatorResult con las tres bandas como sub-indicadores
        """
        if not self.validate_input(closes, self.period):
            return self.create_result(
                values=np.array([]),
                timestamps=[]
            )
        
        # Calcular SMA (banda media)
        sma_values = self._calculate_sma(closes, self.period)
        
        # Calcular desviación estándar
        std_values = self._calculate_standard_deviation(closes, self.period)
        
        # Calcular bandas superior e inferior
        upper_band = np.full_like(closes, np.nan)
        lower_band = np.full_like(closes, np.nan)
        
        for i in range(len(closes)):
            if not np.isnan(sma_values[i]) and not np.isnan(std_values[i]):
                upper_band[i] = sma_values[i] + (std_values[i] * self.std_multiplier)
                lower_band[i] = sma_values[i] - (std_values[i] * self.std_multiplier)
        
        # Crear timestamps
        timestamps = list(range(len(closes)))
        
        # Crear sub-indicadores para cada banda
        sub_indicators = {}
        
        # Banda superior
        upper_config = IndicatorConfig(
            enabled=self.config.enabled,
            color=self.config.params.get('upper_color', '#00ffff'),
            line_width=self.config.line_width,
            visible=self.config.visible
        )
        sub_indicators['upper'] = IndicatorResult(
            values=upper_band,
            timestamps=timestamps,
            name=f"{self.name} Upper",
            type=IndicatorType.OVERLAY,
            config=upper_config
        )
        
        # Banda media
        middle_config = IndicatorConfig(
            enabled=self.config.enabled,
            color=self.config.color,
            line_width=self.config.line_width,
            visible=self.config.visible
        )
        sub_indicators['middle'] = IndicatorResult(
            values=sma_values,
            timestamps=timestamps,
            name=f"{self.name} Middle",
            type=IndicatorType.OVERLAY,
            config=middle_config
        )
        
        # Banda inferior
        lower_config = IndicatorConfig(
            enabled=self.config.enabled,
            color=self.config.params.get('lower_color', '#00ffff'),
            line_width=self.config.line_width,
            visible=self.config.visible
        )
        sub_indicators['lower'] = IndicatorResult(
            values=lower_band,
            timestamps=timestamps,
            name=f"{self.name} Lower",
            type=IndicatorType.OVERLAY,
            config=lower_config
        )
        
        # El resultado principal usa la banda media
        return self.create_result(
            values=sma_values,
            timestamps=timestamps,
            sub_indicators=sub_indicators
        )
    
    def get_required_min_length(self) -> int:
        return self.period