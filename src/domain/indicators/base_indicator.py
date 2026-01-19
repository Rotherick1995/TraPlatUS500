from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from dataclasses import dataclass
from enum import Enum


class IndicatorType(Enum):
    """Tipos de indicadores disponibles."""
    OVERLAY = "overlay"        # Se dibuja sobre el gráfico de precios (SMA, EMA, Bollinger)
    OSCILLATOR = "oscillator"  # Se dibuja en gráfico separado (RSI, MACD, Stochastic)


@dataclass
class IndicatorConfig:
    """Configuración de un indicador."""
    enabled: bool = True
    color: str = "#ffffff"
    line_width: float = 1.5
    visible: bool = True
    params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class IndicatorResult:
    """Resultado del cálculo de un indicador."""
    values: np.ndarray  # Valores calculados
    timestamps: List    # Timestamps correspondientes
    name: str           # Nombre del indicador
    type: IndicatorType # Tipo de indicador
    config: IndicatorConfig  # Configuración
    sub_indicators: Dict[str, 'IndicatorResult'] = None  # Para indicadores compuestos (MACD, Bollinger)
    
    def get_valid_data(self) -> Tuple[np.ndarray, List]:
        """Obtener datos válidos (sin NaN)."""
        valid_mask = ~np.isnan(self.values)
        return self.values[valid_mask], [self.timestamps[i] for i, valid in enumerate(valid_mask) if valid]
    
    def is_valid(self) -> bool:
        """Verificar si el indicador tiene datos válidos."""
        return len(self.values) > 0 and np.any(~np.isnan(self.values))


class BaseIndicator(ABC):
    """Clase base abstracta para todos los indicadores técnicos."""
    
    def __init__(self, name: str, type: IndicatorType):
        self.name = name
        self.type = type
        self.config = IndicatorConfig()
        self._last_calculation = None
        
    @abstractmethod
    def calculate(self, closes: np.ndarray, highs: Optional[np.ndarray] = None, 
                  lows: Optional[np.ndarray] = None, **kwargs) -> IndicatorResult:
        """
        Calcular el indicador.
        
        Args:
            closes: Array de precios de cierre
            highs: Array de precios máximos (opcional)
            lows: Array de precios mínimos (opcional)
            **kwargs: Parámetros adicionales específicos del indicador
            
        Returns:
            IndicatorResult con los valores calculados
        """
        pass
    
    def validate_input(self, closes: np.ndarray, min_length: int = 1) -> bool:
        """
        Validar datos de entrada.
        
        Args:
            closes: Array de precios de cierre
            min_length: Longitud mínima requerida
            
        Returns:
            True si los datos son válidos
        """
        if closes is None or len(closes) == 0:
            return False
        
        if len(closes) < min_length:
            return False
        
        if np.all(np.isnan(closes)):
            return False
        
        return True
    
    def set_config(self, enabled: bool = None, color: str = None, 
                   line_width: float = None, **params):
        """
        Establecer configuración del indicador.
        
        Args:
            enabled: Si el indicador está habilitado
            color: Color para dibujar
            line_width: Ancho de línea
            **params: Parámetros específicos del indicador
        """
        if enabled is not None:
            self.config.enabled = enabled
        if color is not None:
            self.config.color = color
        if line_width is not None:
            self.config.line_width = line_width
        
        # Actualizar parámetros específicos
        for key, value in params.items():
            self.config.params[key] = value
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Obtener configuración como diccionario."""
        return {
            'enabled': self.config.enabled,
            'color': self.config.color,
            'line_width': self.config.line_width,
            'params': self.config.params.copy()
        }
    
    def should_draw(self) -> bool:
        """Determinar si el indicador debe ser dibujado."""
        return self.config.enabled and self.config.visible
    
    def create_result(self, values: np.ndarray, timestamps: List, 
                     sub_indicators: Dict[str, IndicatorResult] = None) -> IndicatorResult:
        """
        Crear objeto IndicatorResult.
        
        Args:
            values: Valores calculados
            timestamps: Lista de timestamps
            sub_indicators: Sub-indicadores (para MACD, Bollinger, etc.)
            
        Returns:
            IndicatorResult configurado
        """
        return IndicatorResult(
            values=values,
            timestamps=timestamps,
            name=self.name,
            type=self.type,
            config=self.config,
            sub_indicators=sub_indicators
        )
    
    def _calculate_sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcular Media Móvil Simple."""
        sma = np.full_like(data, np.nan)
        for i in range(period - 1, len(data)):
            sma[i] = np.nanmean(data[i - period + 1:i + 1])
        return sma
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcular Media Móvil Exponencial."""
        ema = np.full_like(data, np.nan)
        
        if len(data) < period:
            return ema
        
        # Calcular SMA como primer valor
        sma = np.nanmean(data[:period])
        ema[period - 1] = sma
        
        # Factor de suavizado
        multiplier = 2 / (period + 1)
        
        # Calcular EMA para los valores restantes
        for i in range(period, len(data)):
            if np.isnan(data[i]):
                ema[i] = ema[i - 1]
            else:
                ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]
        
        return ema
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calcular Índice de Fuerza Relativa - VERSIÓN CORREGIDA."""
        if len(prices) < period + 1:
            # CORRECCIÓN: Devolver 50 en lugar de NaN
            return np.full(len(prices), 50.0) if len(prices) > 0 else np.array([])
        
        # Calcular cambios
        deltas = np.diff(prices)
        
        # Separar ganancias y pérdidas
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calcular promedios - CORRECCIÓN: Inicializar arrays
        avg_gain = np.zeros_like(prices, dtype=float)
        avg_loss = np.zeros_like(prices, dtype=float)
        rsi = np.full_like(prices, 50.0, dtype=float)  # CORRECCIÓN: Inicializar con 50
        
        # Valores iniciales para el primer cálculo
        start_idx = period
        
        # Verificar que tenemos datos suficientes
        if start_idx >= len(prices):
            return rsi  # Devolver RSI de 50
        
        # Calcular promedios iniciales
        avg_gain[start_idx] = np.mean(gains[:period])
        avg_loss[start_idx] = np.mean(losses[:period])
        
        # Calcular RSI inicial
        if avg_loss[start_idx] == 0:
            rsi[start_idx] = 100.0
        else:
            rs = avg_gain[start_idx] / avg_loss[start_idx]
            rsi[start_idx] = 100.0 - (100.0 / (1.0 + rs))
        
        # Calcular RSI para el resto
        for i in range(start_idx + 1, len(prices)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
            
            if avg_loss[i] == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain[i] / avg_loss[i]
                rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        
        # CORRECCIÓN: Rellenar primeros valores con 50
        rsi[:start_idx] = 50.0
        
        return rsi
    
    def _calculate_standard_deviation(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcular desviación estándar."""
        std = np.full_like(data, np.nan)
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            valid_values = window[~np.isnan(window)]
            if len(valid_values) > 0:
                std[i] = np.std(valid_values)
        return std
    
    def get_required_min_length(self) -> int:
        """Obtener longitud mínima requerida para calcular el indicador."""
        # Valor por defecto, debe ser sobrescrito por clases hijas
        return 1