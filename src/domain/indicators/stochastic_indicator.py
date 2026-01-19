import numpy as np
from typing import Optional, Dict
from .base_indicator import BaseIndicator, IndicatorType, IndicatorResult, IndicatorConfig


class StochasticIndicator(BaseIndicator):
    """Indicador Oscilador Estocástico - VERSIÓN CORREGIDA."""
    
    def __init__(self, k_period: int = 14, d_period: int = 3, slowing: int = 3):
        super().__init__(name=f"Stoch({k_period},{d_period},{slowing})", 
                        type=IndicatorType.OSCILLATOR)
        self.k_period = k_period
        self.d_period = d_period
        self.slowing = slowing
        
        self.set_config(
            color="#00ffff",  # Color para línea %K
            line_width=2.0,
            k_period=k_period,
            d_period=d_period,
            slowing=slowing,
            d_line_color="#ffff00",
            overbought_level=80,
            oversold_level=20
        )
    
    def calculate(self, closes: np.ndarray, highs: Optional[np.ndarray] = None, 
                  lows: Optional[np.ndarray] = None, **kwargs) -> IndicatorResult:
        """
        Calcular Oscilador Estocástico - VERSIÓN CORREGIDA.
        
        Args:
            closes: Array de precios de cierre
            highs: Array de precios máximos (requerido)
            lows: Array de precios mínimos (requerido)
            
        Returns:
            IndicatorResult con líneas %K y %D como sub-indicadores
        """
        if highs is None or lows is None:
            # CORRECCIÓN: Devolver array de 50 en lugar de vacío
            return self.create_result(
                values=np.full(len(closes), 50.0) if len(closes) > 0 else np.array([]),
                timestamps=list(range(len(closes))) if len(closes) > 0 else []
            )
        
        min_required = self.k_period + self.d_period
        if not self.validate_input(closes, min_required):
            # CORRECCIÓN: Devolver array de 50
            return self.create_result(
                values=np.full(len(closes), 50.0) if len(closes) > 0 else np.array([]),
                timestamps=list(range(len(closes))) if len(closes) > 0 else []
            )
        
        # Calcular %K - CORRECCIÓN: Usar método mejorado
        k_line = self._calculate_percent_k_robust(highs, lows, closes, self.k_period, self.slowing)
        
        # Calcular %D (SMA de %K) - CORRECCIÓN: Rellenar NaN
        d_line = self._calculate_sma_robust(k_line, self.d_period)
        
        # Crear timestamps
        timestamps = list(range(len(closes)))
        
        # Crear sub-indicadores
        sub_indicators = {}
        
        # Línea %K
        k_config = IndicatorConfig(
            enabled=self.config.enabled,
            color=self.config.color,
            line_width=self.config.line_width,
            visible=self.config.visible
        )
        sub_indicators['k_line'] = IndicatorResult(
            values=k_line,
            timestamps=timestamps,
            name=f"{self.name} %K",
            type=IndicatorType.OSCILLATOR,
            config=k_config
        )
        
        # Línea %D
        d_config = IndicatorConfig(
            enabled=self.config.enabled,
            color=self.config.params.get('d_line_color', '#ffff00'),
            line_width=self.config.line_width,
            visible=self.config.visible
        )
        sub_indicators['d_line'] = IndicatorResult(
            values=d_line,
            timestamps=timestamps,
            name=f"{self.name} %D",
            type=IndicatorType.OSCILLATOR,
            config=d_config
        )
        
        # Añadir información de niveles para dibujo
        extra_data = {
            'overbought_level': self.config.params.get('overbought_level', 80),
            'oversold_level': self.config.params.get('oversold_level', 20),
            'has_valid_data': np.any(~np.isnan(k_line) & ~np.isnan(d_line))
        }
        
        # El resultado principal usa la línea %K
        result = self.create_result(
            values=k_line,
            timestamps=timestamps,
            sub_indicators=sub_indicators
        )
        
        # Añadir datos extra
        result.extra_data = extra_data
        
        return result
    
    def _calculate_percent_k_robust(self, highs: np.ndarray, lows: np.ndarray, 
                                  closes: np.ndarray, period: int, slowing: int) -> np.ndarray:
        """Calcular línea %K del estocástico - VERSIÓN ROBUSTA."""
        if len(closes) < period:
            return np.full(len(closes), 50.0)  # Valor neutro
        
        k_line = np.full_like(closes, 50.0, dtype=float)  # Inicializar con 50
        
        for i in range(period - 1, len(closes)):
            high_window = highs[i - period + 1:i + 1]
            low_window = lows[i - period + 1:i + 1]
            current_close = closes[i]
            
            # Encontrar máximo y mínimo válidos
            valid_highs = high_window[~np.isnan(high_window)]
            valid_lows = low_window[~np.isnan(low_window)]
            
            if len(valid_highs) > 0 and len(valid_lows) > 0:
                highest_high = np.max(valid_highs)
                lowest_low = np.min(valid_lows)
                
                if highest_high != lowest_low:
                    k_value = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
                    # Limitar entre 0 y 100
                    k_line[i] = max(0.0, min(100.0, k_value))
        
        # Aplicar slowing si está habilitado
        if slowing > 1:
            k_line_smoothed = np.full_like(k_line, 50.0)
            for i in range(period + slowing - 2, len(k_line)):
                window = k_line[i - slowing + 1:i + 1]
                if np.any(~np.isnan(window)):
                    k_line_smoothed[i] = np.nanmean(window)
                else:
                    k_line_smoothed[i] = 50.0
            k_line = k_line_smoothed
        
        return k_line
    
    def _calculate_sma_robust(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcular SMA robusto que maneja NaN."""
        sma = np.full_like(data, 50.0, dtype=float)  # Inicializar con 50
        
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            valid_values = window[~np.isnan(window)]
            
            if len(valid_values) > 0:
                sma[i] = np.mean(valid_values)
            else:
                sma[i] = 50.0  # Valor neutro si no hay valores válidos
        
        return sma
    
    def get_required_min_length(self) -> int:
        return self.k_period + self.d_period