import numpy as np
from typing import Optional, Dict
from .base_indicator import BaseIndicator, IndicatorType, IndicatorResult, IndicatorConfig


class MACDIndicator(BaseIndicator):
    """Indicador MACD con histograma - VERSIÓN CORREGIDA."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(name=f"MACD({fast_period},{slow_period},{signal_period})", 
                        type=IndicatorType.OSCILLATOR)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        # Configurar colores para las líneas e histograma
        self.set_config(
            color="#00ff00",  # Color para línea MACD
            line_width=2.0,
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
            signal_color="#ff0000",
            histogram_positive_color="#00aa00",  # Verde más oscuro para positivo
            histogram_negative_color="#aa0000"   # Rojo más oscuro para negativo
        )
    
    def calculate(self, closes: np.ndarray, highs: Optional[np.ndarray] = None, 
                  lows: Optional[np.ndarray] = None, **kwargs) -> IndicatorResult:
        """
        Calcular MACD con histograma - VERSIÓN CORREGIDA.
        
        Args:
            closes: Array de precios de cierre
            highs: No usado para MACD
            lows: No usado para MACD
            
        Returns:
            IndicatorResult con MACD, señal e histograma como sub-indicadores
        """
        min_required = max(self.fast_period, self.slow_period, self.signal_period)
        if not self.validate_input(closes, min_required):
            return self.create_result(
                values=np.array([]),
                timestamps=[]
            )
        
        # CORRECCIÓN 1: Usar EMA robusto que maneje NaN
        ema_fast = self._calculate_ema_robust(closes, self.fast_period)
        ema_slow = self._calculate_ema_robust(closes, self.slow_period)
        
        # CORRECCIÓN 2: Calcular línea MACD evitando propagación de NaN
        macd_line = np.full_like(closes, 0.0)  # Inicializar con 0, no NaN
        valid_start = max(self.fast_period, self.slow_period) - 1
        
        for i in range(valid_start, len(closes)):
            if not np.isnan(ema_fast[i]) and not np.isnan(ema_slow[i]):
                macd_line[i] = ema_fast[i] - ema_slow[i]
            elif i > 0:
                macd_line[i] = macd_line[i-1]  # Propagación del último valor válido
        
        # CORRECCIÓN 3: Calcular línea de señal con EMA robusto
        signal_line = self._calculate_ema_robust(macd_line, self.signal_period)
        
        # CORRECCIÓN 4: Calcular histograma asegurando valores no NaN
        histogram = np.full_like(closes, 0.0)  # Inicializar con 0
        histogram_start = valid_start + self.signal_period - 1
        
        for i in range(histogram_start, len(closes)):
            if not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]):
                hist_value = macd_line[i] - signal_line[i]
                histogram[i] = hist_value if abs(hist_value) > 0.000001 else 0.0
        
        # Crear timestamps
        timestamps = list(range(len(closes)))
        
        # Crear sub-indicadores
        sub_indicators = {}
        
        # Línea MACD
        macd_config = IndicatorConfig(
            enabled=self.config.enabled,
            color=self.config.color,
            line_width=self.config.line_width,
            visible=self.config.visible
        )
        sub_indicators['macd_line'] = IndicatorResult(
            values=macd_line,
            timestamps=timestamps,
            name=f"{self.name} Line",
            type=IndicatorType.OSCILLATOR,
            config=macd_config
        )
        
        # Línea de señal
        signal_config = IndicatorConfig(
            enabled=self.config.enabled,
            color=self.config.params.get('signal_color', '#ff0000'),
            line_width=self.config.line_width,
            visible=self.config.visible
        )
        sub_indicators['signal_line'] = IndicatorResult(
            values=signal_line,
            timestamps=timestamps,
            name=f"{self.name} Signal",
            type=IndicatorType.OSCILLATOR,
            config=signal_config
        )
        
        # Histograma - CORRECCIÓN 5: Añadir información extra para dibujo
        histogram_config = IndicatorConfig(
            enabled=self.config.enabled,
            color="#ffffff",  # Color base
            line_width=1.0,
            visible=self.config.visible,
            params={
                'positive_color': self.config.params.get('histogram_positive_color', '#00aa00'),
                'negative_color': self.config.params.get('histogram_negative_color', '#aa0000'),
                'bar_width': 0.6,  # Ancho de barra para dibujo
                'min_value': 0.000001  # Valor mínimo para dibujar
            }
        )
        sub_indicators['histogram'] = IndicatorResult(
            values=histogram,
            timestamps=timestamps,
            name=f"{self.name} Histogram",
            type=IndicatorType.OSCILLATOR,
            config=histogram_config,
            # Añadir datos extra para facilitar dibujo
            extra_data={
                'has_positive': np.any(histogram > 0),
                'has_negative': np.any(histogram < 0),
                'max_value': np.nanmax(np.abs(histogram)) if len(histogram) > 0 else 0,
                'valid_count': np.sum(~np.isnan(histogram) & (np.abs(histogram) > 0.000001))
            }
        )
        
        # El resultado principal usa la línea MACD
        return self.create_result(
            values=macd_line,
            timestamps=timestamps,
            sub_indicators=sub_indicators
        )
    
    def _calculate_ema_robust(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcular EMA robusto que evita propagación de NaN."""
        if len(data) < period:
            return np.full_like(data, np.nan)
        
        ema = np.full_like(data, np.nan)
        
        # Encontrar primeros valores no NaN
        valid_data = []
        for i in range(len(data)):
            if not np.isnan(data[i]):
                valid_data.append(data[i])
                if len(valid_data) >= period:
                    break
        
        if len(valid_data) < period:
            return ema
        
        # Calcular SMA inicial con primeros valores válidos
        sma = np.mean(valid_data[:period])
        ema[period - 1] = sma
        
        # Multiplicador
        multiplier = 2.0 / (period + 1.0)
        
        # Calcular EMA propagando el último valor si hay NaN
        for i in range(period, len(data)):
            if np.isnan(data[i]):
                ema[i] = ema[i - 1]  # Propagar último valor EMA
            else:
                ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]
        
        return ema
    
    def get_required_min_length(self) -> int:
        return max(self.fast_period, self.slow_period, self.signal_period)