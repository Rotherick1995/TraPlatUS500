# src/domain/value_objects/timeframe.py
from enum import Enum
from typing import Optional, Dict, Any
from datetime import timedelta


class TimeFrame(Enum):
    """
    Value Object que representa un timeframe de trading.
    
    Los timeframes definen la granularidad de los datos de precios
    y son fundamentales para el análisis técnico.
    """
    
    # Timeframes intraday
    M1 = "M1"   # 1 minuto
    M5 = "M5"   # 5 minutos
    M15 = "M15" # 15 minutos
    M30 = "M30" # 30 minutos
    H1 = "H1"   # 1 hora
    H4 = "H4"   # 4 horas
    
    # Timeframes diarios y mayores
    D1 = "D1"   # 1 día
    W1 = "W1"   # 1 semana
    MN1 = "MN1" # 1 mes
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def is_intraday(self) -> bool:
        """Retorna True si es un timeframe intraday."""
        return self in [TimeFrame.M1, TimeFrame.M5, TimeFrame.M15, 
                       TimeFrame.M30, TimeFrame.H1, TimeFrame.H4]
    
    @property
    def is_daily_or_higher(self) -> bool:
        """Retorna True si es diario o mayor."""
        return self in [TimeFrame.D1, TimeFrame.W1, TimeFrame.MN1]
    
    @property
    def duration_minutes(self) -> int:
        """Duración en minutos."""
        durations = {
            TimeFrame.M1: 1,
            TimeFrame.M5: 5,
            TimeFrame.M15: 15,
            TimeFrame.M30: 30,
            TimeFrame.H1: 60,
            TimeFrame.H4: 240,
            TimeFrame.D1: 1440,      # 24 horas
            TimeFrame.W1: 10080,     # 7 días
            TimeFrame.MN1: 43200     # 30 días aproximado
        }
        return durations[self]
    
    @property
    def duration_timedelta(self) -> timedelta:
        """Duración como timedelta."""
        return timedelta(minutes=self.duration_minutes)
    
    @property
    def display_name(self) -> str:
        """Nombre para mostrar."""
        names = {
            TimeFrame.M1: "1 Minuto",
            TimeFrame.M5: "5 Minutos",
            TimeFrame.M15: "15 Minutos",
            TimeFrame.M30: "30 Minutos",
            TimeFrame.H1: "1 Hora",
            TimeFrame.H4: "4 Horas",
            TimeFrame.D1: "1 Día",
            TimeFrame.W1: "1 Semana",
            TimeFrame.MN1: "1 Mes"
        }
        return names[self]
    
    @property
    def short_name(self) -> str:
        """Nombre corto."""
        return self.value
    
    @property
    def candles_per_day(self) -> int:
        """Número de velas por día (aproximado)."""
        if self == TimeFrame.M1:
            return 1440
        elif self == TimeFrame.M5:
            return 288
        elif self == TimeFrame.M15:
            return 96
        elif self == TimeFrame.M30:
            return 48
        elif self == TimeFrame.H1:
            return 24
        elif self == TimeFrame.H4:
            return 6
        elif self == TimeFrame.D1:
            return 1
        elif self == TimeFrame.W1:
            return 0.142857  # 1/7
        elif self == TimeFrame.MN1:
            return 0.033333  # 1/30
        return 0
    
    @classmethod
    def from_string(cls, value: str) -> 'TimeFrame':
        """
        Crea un TimeFrame desde string.
        
        Args:
            value: String como "M1", "H1", "D1", etc.
        
        Returns:
            Instancia de TimeFrame
        """
        value = value.upper()
        
        # Mapeo de valores comunes
        mapping = {
            '1M': 'M1', '5M': 'M5', '15M': 'M15', '30M': 'M30',
            '1H': 'H1', '4H': 'H4', '1D': 'D1', '1W': 'W1', '1MN': 'MN1',
            'M': 'M1', 'H': 'H1', 'D': 'D1', 'W': 'W1', 'MN': 'MN1'
        }
        
        normalized = mapping.get(value, value)
        
        try:
            return cls(normalized)
        except ValueError:
            raise ValueError(f"TimeFrame '{value}' no válido. "
                           f"Usar: {', '.join([tf.value for tf in cls])}")
    
    @classmethod
    def from_minutes(cls, minutes: int) -> Optional['TimeFrame']:
        """
        Crea un TimeFrame desde minutos.
        
        Args:
            minutes: Duración en minutos
        
        Returns:
            TimeFrame más cercano o None
        """
        timeframes_by_minutes = {
            1: TimeFrame.M1,
            5: TimeFrame.M5,
            15: TimeFrame.M15,
            30: TimeFrame.M30,
            60: TimeFrame.H1,
            240: TimeFrame.H4,
            1440: TimeFrame.D1,
            10080: TimeFrame.W1,
            43200: TimeFrame.MN1
        }
        
        return timeframes_by_minutes.get(minutes)
    
    def to_mt5_timeframe(self) -> int:
        """
        Convierte a timeframe de MT5.
        
        Returns:
            Constante MT5_TIMEFRAME
        """
        import MetaTrader5 as mt5
        
        mapping = {
            TimeFrame.M1: mt5.TIMEFRAME_M1,
            TimeFrame.M5: mt5.TIMEFRAME_M5,
            TimeFrame.M15: mt5.TIMEFRAME_M15,
            TimeFrame.M30: mt5.TIMEFRAME_M30,
            TimeFrame.H1: mt5.TIMEFRAME_H1,
            TimeFrame.H4: mt5.TIMEFRAME_H4,
            TimeFrame.D1: mt5.TIMEFRAME_D1,
            TimeFrame.W1: mt5.TIMEFRAME_W1,
            TimeFrame.MN1: mt5.TIMEFRAME_MN1
        }
        
        return mapping.get(self, mt5.TIMEFRAME_H1)
    
    @classmethod
    def from_mt5_timeframe(cls, mt5_timeframe: int) -> 'TimeFrame':
        """
        Crea desde timeframe de MT5.
        
        Args:
            mt5_timeframe: Constante MT5_TIMEFRAME
        
        Returns:
            Instancia de TimeFrame
        """
        import MetaTrader5 as mt5
        
        mapping = {
            mt5.TIMEFRAME_M1: cls.M1,
            mt5.TIMEFRAME_M5: cls.M5,
            mt5.TIMEFRAME_M15: cls.M15,
            mt5.TIMEFRAME_M30: cls.M30,
            mt5.TIMEFRAME_H1: cls.H1,
            mt5.TIMEFRAME_H4: cls.H4,
            mt5.TIMEFRAME_D1: cls.D1,
            mt5.TIMEFRAME_W1: cls.W1,
            mt5.TIMEFRAME_MN1: cls.MN1
        }
        
        return mapping.get(mt5_timeframe, cls.H1)
    
    def get_higher_timeframe(self) -> Optional['TimeFrame']:
        """Retorna el timeframe inmediatamente superior."""
        order = [
            TimeFrame.M1, TimeFrame.M5, TimeFrame.M15, TimeFrame.M30,
            TimeFrame.H1, TimeFrame.H4, TimeFrame.D1, TimeFrame.W1, TimeFrame.MN1
        ]
        
        index = order.index(self) if self in order else -1
        if index < len(order) - 1:
            return order[index + 1]
        return None
    
    def get_lower_timeframe(self) -> Optional['TimeFrame']:
        """Retorna el timeframe inmediatamente inferior."""
        order = [
            TimeFrame.M1, TimeFrame.M5, TimeFrame.M15, TimeFrame.M30,
            TimeFrame.H1, TimeFrame.H4, TimeFrame.D1, TimeFrame.W1, TimeFrame.MN1
        ]
        
        index = order.index(self) if self in order else -1
        if index > 0:
            return order[index - 1]
        return None
    
    def is_multiple_of(self, other: 'TimeFrame') -> bool:
        """
        Verifica si este timeframe es múltiplo de otro.
        
        Args:
            other: Otro timeframe
        
        Returns:
            True si es múltiplo
        """
        return self.duration_minutes % other.duration_minutes == 0
    
    def calculate_candle_count(
        self, 
        days: int = 1,
        weeks: int = 0,
        months: int = 0
    ) -> int:
        """
        Calcula el número de velas para un período.
        
        Args:
            days: Número de días
            weeks: Número de semanas
            months: Número de meses
        
        Returns:
            Número estimado de velas
        """
        total_days = days + (weeks * 7) + (months * 30)
        
        if self.is_intraday:
            return int(self.candles_per_day * total_days)
        elif self == TimeFrame.D1:
            return total_days
        elif self == TimeFrame.W1:
            return int(total_days / 7)
        elif self == TimeFrame.MN1:
            return int(total_days / 30)
        
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'value': self.value,
            'display_name': self.display_name,
            'duration_minutes': self.duration_minutes,
            'is_intraday': self.is_intraday,
            'candles_per_day': self.candles_per_day,
            'short_name': self.short_name
        }
    
    @classmethod
    def all_timeframes(cls) -> list['TimeFrame']:
        """Retorna todos los timeframes en orden."""
        return [
            cls.M1, cls.M5, cls.M15, cls.M30,
            cls.H1, cls.H4, cls.D1, cls.W1, cls.MN1
        ]
    
    @classmethod
    def intraday_timeframes(cls) -> list['TimeFrame']:
        """Retorna solo timeframes intraday."""
        return [tf for tf in cls.all_timeframes() if tf.is_intraday]
    
    @classmethod
    def daily_plus_timeframes(cls) -> list['TimeFrame']:
        """Retorna timeframes diarios y mayores."""
        return [tf for tf in cls.all_timeframes() if tf.is_daily_or_higher]