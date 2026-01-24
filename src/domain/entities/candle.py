# src/domain/entities/candle.py

from dataclasses import dataclass
from datetime import datetime
import pytz


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
    
    def get_local_time_string(self) -> str:
        """Obtiene la fecha/hora en formato yyyy-mm-dd HH:MM para zona horaria de La Paz, Bolivia."""
        try:
            # Definir zona horaria de La Paz, Bolivia (GMT-4)
            la_paz_tz = pytz.timezone('America/La_Paz')
            
            # Convertir el timestamp a la zona horaria de La Paz
            if self.timestamp.tzinfo is None:
                # Si no tiene zona horaria, asumir UTC y convertir
                utc_dt = pytz.utc.localize(self.timestamp)
                local_dt = utc_dt.astimezone(la_paz_tz)
            else:
                # Si ya tiene zona horaria, convertir directamente
                local_dt = self.timestamp.astimezone(la_paz_tz)
            
            # Formatear como yyyy-mm-dd HH:MM
            return local_dt.strftime('%Y-%m-%d %H:%M')
            
        except Exception:
            # En caso de error, devolver el timestamp original formateado
            return self.timestamp.strftime('%Y-%m-%d %H:%M')
    
    def get_local_datetime(self):
        """Obtiene el datetime convertido a zona horaria de La Paz, Bolivia."""
        try:
            # Definir zona horaria de La Paz, Bolivia (GMT-4)
            la_paz_tz = pytz.timezone('America/La_Paz')
            
            # Convertir el timestamp a la zona horaria de La Paz
            if self.timestamp.tzinfo is None:
                # Si no tiene zona horaria, asumir UTC y convertir
                utc_dt = pytz.utc.localize(self.timestamp)
                return utc_dt.astimezone(la_paz_tz)
            else:
                # Si ya tiene zona horaria, convertir directamente
                return self.timestamp.astimezone(la_paz_tz)
                
        except Exception:
            # En caso de error, devolver el timestamp original
            return self.timestamp
    
    @classmethod
    def from_utc_to_local(cls, timestamp: datetime, open: float, high: float, 
                         low: float, close: float, volume: int = 0):
        """Crea una vela convirtiendo UTC a hora local de La Paz."""
        try:
            # Definir zona horaria de La Paz, Bolivia (GMT-4)
            la_paz_tz = pytz.timezone('America/La_Paz')
            
            # Si no tiene zona horaria, asumir UTC
            if timestamp.tzinfo is None:
                utc_dt = pytz.utc.localize(timestamp)
                local_dt = utc_dt.astimezone(la_paz_tz)
            else:
                # Si ya tiene zona horaria, convertir a La Paz
                local_dt = timestamp.astimezone(la_paz_tz)
            
            # Crear la vela con el timestamp convertido
            return cls(
                timestamp=local_dt,
                open=open,
                high=high,
                low=low,
                close=close,
                volume=volume
            )
        except Exception:
            # En caso de error, crear con el timestamp original
            return cls(
                timestamp=timestamp,
                open=open,
                high=high,
                low=low,
                close=close,
                volume=volume
            )
    
    def to_dict(self, local_time: bool = True) -> dict:
        """Convierte la vela a diccionario, opcionalmente con hora local."""
        data = {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'is_bullish': self.is_bullish(),
            'is_bearish': self.is_bearish(),
            'body_size': self.get_body_size(),
            'wick_upper': self.get_wick_upper(),
            'wick_lower': self.get_wick_lower()
        }
        
        if local_time:
            data['local_time_string'] = self.get_local_time_string()
            data['local_datetime'] = self.get_local_datetime()
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Crea una vela desde un diccionario."""
        # Extraer el timestamp (puede venir en diferentes formatos)
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            # Intentar parsear si es string
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                # Si falla, usar datetime actual
                timestamp = datetime.now()
        
        return cls(
            timestamp=timestamp or datetime.now(),
            open=float(data.get('open', 0)),
            high=float(data.get('high', 0)),
            low=float(data.get('low', 0)),
            close=float(data.get('close', 0)),
            volume=int(data.get('volume', 0))
        )