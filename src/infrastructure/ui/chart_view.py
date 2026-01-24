import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame, QSizePolicy,
                             QSpinBox, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot, QRectF
from PyQt5.QtGui import QColor, QFont, QPen, QPainter
import pyqtgraph as pg
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Optional, Dict, Any
from collections import deque
import pytz


class RealTimeCandle:
    """Clase para manejar velas en tiempo real con crecimiento dinámico."""
    
    def __init__(self, timestamp: datetime, timeframe: str = "H1"):
        self.timestamp = timestamp
        self.timeframe = timeframe
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.volume = 0
        self.is_complete = False
        self.is_bullish = True
        
        # Para animación suave
        self.animated_close = None
        self.animation_speed = 0.2
        
        # Convertir timeframe a segundos
        self.timeframe_seconds = self._timeframe_to_seconds(timeframe)
        
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convertir timeframe a segundos."""
        timeframe_map = {
            'M1': 60,
            'M5': 300,
            'M15': 900,
            'M30': 1800,
            'H1': 3600,
            'H4': 14400,
            'D1': 86400
        }
        return timeframe_map.get(timeframe, 3600)
    
    def update(self, price: float, volume: int = 1):
        """Actualizar vela con nuevo precio con animación suave."""
        if self.open is None:
            self.open = price
            self.high = price
            self.low = price
            self.close = price
            self.animated_close = price
            self.is_bullish = True
        else:
            self.high = max(self.high, price)
            self.low = min(self.low, price)
            
            if self.animated_close is None:
                self.animated_close = self.close
            
            self.animated_close += (price - self.animated_close) * self.animation_speed
            self.close = price
            
            if self.open is not None:
                self.is_bullish = self.close >= self.open
        
        self.volume += volume
        return self.get_animated_data()
    
    def get_animated_data(self):
        """Obtener datos animados de la vela."""
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.animated_close if self.animated_close is not None else self.close,
            'volume': self.volume,
            'is_complete': self.is_complete,
            'is_bullish': self.is_bullish,
            'current_price': self.animated_close if self.animated_close is not None else self.close
        }
    
    def should_close(self, current_time: datetime) -> bool:
        """Verificar si la vela debe cerrarse."""
        if hasattr(self.timestamp, 'tzinfo') and self.timestamp.tzinfo is not None:
            if hasattr(current_time, 'tzinfo') and current_time.tzinfo is not None:
                elapsed = (current_time - self.timestamp).total_seconds()
            else:
                current_time_tz = self.timestamp.tzinfo.localize(current_time.replace(tzinfo=None))
                elapsed = (current_time_tz - self.timestamp).total_seconds()
        else:
            if hasattr(current_time, 'tzinfo') and current_time.tzinfo is not None:
                timestamp_tz = current_time.tzinfo.localize(self.timestamp.replace(tzinfo=None))
                elapsed = (current_time - timestamp_tz).total_seconds()
            else:
                elapsed = (current_time - self.timestamp).total_seconds()
        
        return elapsed >= self.timeframe_seconds
    
    def close_candle(self, price: float = None):
        """Cerrar la vela."""
        if price is not None:
            self.close = price
            self.animated_close = price
            self.high = max(self.high, price)
            self.low = min(self.low, price)
            if self.open is not None:
                self.is_bullish = self.close >= self.open
        
        self.is_complete = True
        return self
    
    def to_dict(self):
        """Convertir a diccionario."""
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'is_complete': self.is_complete,
            'is_bullish': self.is_bullish
        }


class RealTimeCandleManager:
    """Gestor de velas en tiempo real con animación."""
    
    def __init__(self):
        self.current_candle = None
        self.completed_candles = deque()
        self.timeframe = "H1"
        self.timeframe_seconds = 3600
        self.last_price = None
        self.last_update_time = None
        self.animation_active = True
        
    def update_timeframe(self, timeframe: str):
        """Actualizar timeframe."""
        self.timeframe = timeframe
        self.timeframe_seconds = self._timeframe_to_seconds(timeframe)
        self.current_candle = None
        
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convertir timeframe a segundos."""
        timeframe_map = {
            'M1': 60,
            'M5': 300,
            'M15': 900,
            'M30': 1800,
            'H1': 3600,
            'H4': 14400,
            'D1': 86400
        }
        return timeframe_map.get(timeframe, 3600)
    
    def update_price(self, price: float, timestamp: datetime = None) -> Dict[str, Any]:
        """Actualizar precio en tiempo real con animación."""
        if timestamp is None:
            timestamp = datetime.now(pytz.utc)
        
        self.last_price = price
        self.last_update_time = timestamp
        
        candle_start = self._get_candle_start_time_local(timestamp)
        
        should_create_new_candle = False
        
        if self.current_candle is None:
            should_create_new_candle = True
        else:
            current_candle_start = self._get_candle_start_time_local(self.current_candle.timestamp)
            new_candle_start = self._get_candle_start_time_local(candle_start)
            
            current_str = current_candle_start.strftime('%Y%m%d%H%M%S')
            new_str = new_candle_start.strftime('%Y%m%d%H%M%S')
            
            if current_str != new_str:
                should_create_new_candle = True
        
        if should_create_new_candle:
            if self.current_candle is not None and not self.current_candle.is_complete:
                self.completed_candles.append(self.current_candle.close_candle(self.last_price))
            
            self.current_candle = RealTimeCandle(candle_start, self.timeframe)
            candle_data = self.current_candle.update(price)
        else:
            candle_data = self.current_candle.update(price)
        
        current_local_time = self._get_local_time(timestamp)
        if self.current_candle.should_close(current_local_time) and not self.current_candle.is_complete:
            self.completed_candles.append(self.current_candle.close_candle(price))
            
            next_candle_start = self._get_candle_start_time_local(timestamp + timedelta(seconds=self.timeframe_seconds))
            self.current_candle = RealTimeCandle(next_candle_start, self.timeframe)
            candle_data = self.current_candle.update(price)
        
        return {
            'current_candle': candle_data,
            'completed_candles': [c.to_dict() for c in self.completed_candles],
            'last_price': price,
            'timestamp': timestamp,
            'has_changes': True
        }
    
    def _get_local_time(self, timestamp: datetime) -> datetime:
        """Convertir a hora local GMT-4."""
        try:
            if timestamp.tzinfo is not None:
                return timestamp.astimezone(pytz.timezone('America/La_Paz'))
            else:
                utc_dt = pytz.utc.localize(timestamp)
                return utc_dt.astimezone(pytz.timezone('America/La_Paz'))
        except Exception as e:
            print(f"Error convirtiendo a hora local: {e}")
            return timestamp
    
    def _get_candle_start_time_local(self, timestamp: datetime) -> datetime:
        """Calcular el tiempo de inicio de la vela en hora LOCAL (GMT-4)."""
        local_dt = self._get_local_time(timestamp)
        
        if self.timeframe == "M1":
            return local_dt.replace(second=0, microsecond=0)
        elif self.timeframe == "M5":
            minute = (local_dt.minute // 5) * 5
            return local_dt.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "M15":
            minute = (local_dt.minute // 15) * 15
            return local_dt.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "M30":
            minute = (local_dt.minute // 30) * 30
            return local_dt.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "H1":
            return local_dt.replace(minute=0, second=0, microsecond=0)
        elif self.timeframe == "H4":
            hour = (local_dt.hour // 4) * 4
            return local_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
        elif self.timeframe == "D1":
            return local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            return local_dt.replace(second=0, microsecond=0)
    
    def get_time_to_next_candle(self, current_time: datetime = None) -> float:
        """Obtener tiempo restante para la siguiente vela."""
        if current_time is None:
            current_time = datetime.now(pytz.utc)
        
        current_local_time = self._get_local_time(current_time)
        
        if self.current_candle is None:
            return self.timeframe_seconds
        
        candle_end = self.current_candle.timestamp + timedelta(seconds=self.timeframe_seconds)
        time_remaining = (candle_end - current_local_time).total_seconds()
        
        return max(0, time_remaining)
    
    def get_current_candle_data(self) -> Optional[Dict]:
        """Obtener datos de la vela actual."""
        if self.current_candle:
            return self.current_candle.get_animated_data()
        return None
    
    def get_completed_candles(self) -> List[Dict]:
        """Obtener velas completadas."""
        return [c.to_dict() for c in self.completed_candles]
    
    def get_all_candles(self) -> List[Dict]:
        """Obtener todas las velas (completadas + actual)."""
        candles = self.get_completed_candles()
        current = self.get_current_candle_data()
        if current:
            candles.append(current)
        return candles
    
    def reset(self):
        """Reiniciar el gestor."""
        self.current_candle = None
        self.completed_candles.clear()


class DateAxis(pg.AxisItem):
    """Eje personalizado para mostrar fechas con formato legible."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)
        self.tick_positions = []
        self.tick_labels = []
        self.timeframe = "H1"
        
        font = QFont('Arial', 7)
        self.setTickFont(font)
        
    def set_ticks(self, positions, labels, timeframe):
        """Establecer ticks personalizados."""
        self.tick_positions = positions
        self.tick_labels = labels
        self.timeframe = timeframe
        self.ticks = [(pos, label) for pos, label in zip(positions, labels)]
        
    def tickStrings(self, values, scale, spacing):
        """Mostrar etiquetas personalizadas."""
        strings = []
        for v in values:
            if self.tick_positions:
                idx = min(range(len(self.tick_positions)), 
                         key=lambda i: abs(self.tick_positions[i] - v))
                if abs(self.tick_positions[idx] - v) < 0.5:
                    strings.append(self.tick_labels[idx])
                else:
                    strings.append("")
            else:
                strings.append("")
        return strings
    
    def drawPicture(self, p, axisSpec, tickSpecs, textSpecs):
        """Sobreescribir método para mejorar la legibilidad."""
        super().drawPicture(p, axisSpec, tickSpecs, textSpecs)


class IndicatorPlot(QWidget):
    """Widget para mostrar indicadores técnicos en gráficos separados."""
    
    def __init__(self, parent=None, height: int = 150):
        super().__init__(parent)
        self.height = height
        self.plot_items = []
        self.horizontal_lines = []
        self.init_ui()
        
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.plot = pg.PlotWidget()
        self.plot.setBackground('#0a0a0a')
        self.plot.setMinimumHeight(self.height)
        self.plot.setMaximumHeight(self.height)
        self.plot.setLabel('left', 'Valor')
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setMenuEnabled(False)
        
        self.plot.getAxis('left').setPen(pg.mkPen(color='#666'))
        self.plot.getAxis('bottom').setPen(pg.mkPen(color='#666'))
        
        font = QFont('Arial', 7)
        self.plot.getAxis('left').setTickFont(font)
        self.plot.getAxis('bottom').setTickFont(font)
        
        layout.addWidget(self.plot)
    
    def clear(self):
        """Limpiar el gráfico completamente."""
        self.plot.clear()
        self.plot_items = []
        for hline in self.horizontal_lines:
            line = pg.InfiniteLine(
                pos=hline['pos'],
                angle=0,
                pen=pg.mkPen(color=hline['color'], style=hline['style'], width=hline['width'])
            )
            self.plot.addItem(line)
            self.plot_items.append(line)
    
    def clear_all(self):
        """Limpiar todo incluyendo líneas horizontales."""
        self.plot.clear()
        self.plot_items = []
        self.horizontal_lines = []
    
    def set_x_link(self, other_plot):
        """Vincular eje X con otro gráfico."""
        self.plot.setXLink(other_plot)
    
    def plot_indicator(self, x_data, y_data, color='#ffffff', name='', width=2, style=Qt.SolidLine):
        """Graficar un indicador."""
        if len(x_data) == 0 or len(y_data) == 0:
            return None
        
        valid_mask = ~np.isnan(y_data)
        if not np.any(valid_mask):
            return None
        
        x_valid = x_data[valid_mask]
        y_valid = y_data[valid_mask]
        
        line = pg.PlotCurveItem(
            x=x_valid,
            y=y_valid,
            pen=pg.mkPen(color=color, width=width, style=style)
        )
        self.plot.addItem(line)
        self.plot_items.append(line)
        
        if name and len(x_valid) > 0:
            label = pg.TextItem(
                text=name,
                color=color,
                anchor=(0, 1),
                fill=pg.mkBrush(color=(10, 10, 10, 200))
            )
            label.setPos(x_valid[-1], y_valid[-1])
            self.plot.addItem(label)
            self.plot_items.append(label)
        
        return line
    
    def add_hline(self, y_value, color='#666666', style=Qt.DashLine, width=1, label=None):
        """Agregar línea horizontal permanente con etiqueta opcional."""
        line = pg.InfiniteLine(
            pos=y_value,
            angle=0,
            pen=pg.mkPen(color=color, style=style, width=width)
        )
        self.plot.addItem(line)
        self.plot_items.append(line)
        
        if label:
            text_item = pg.TextItem(
                text=label,
                color=color,
                anchor=(1, 0),
                fill=pg.mkBrush(color=(10, 10, 10, 150))
            )
            text_item.setPos(self.plot.getViewBox().viewRange()[0][1] * 0.95, y_value)
            self.plot.addItem(text_item)
            self.plot_items.append(text_item)
        
        self.horizontal_lines.append({
            'pos': y_value,
            'color': color,
            'style': style,
            'width': width,
            'label': label
        })
        
        return line
    
    def plot_histogram(self, x_data, y_data, width=0.6):
        """Graficar histograma para MACD."""
        if len(x_data) == 0 or len(y_data) == 0:
            return []
        
        valid_mask = ~np.isnan(y_data)
        if not np.any(valid_mask):
            return []
        
        x_valid = x_data[valid_mask]
        y_valid = y_data[valid_mask]
        
        x_centers = x_valid
        heights = y_valid
        width = width
        
        brushes = []
        pens = []
        for y in y_valid:
            if y >= 0:
                brushes.append(pg.mkBrush(color='#00ff00'))
                pens.append(pg.mkPen(color='#00ff00', width=0.5))
            else:
                brushes.append(pg.mkBrush(color='#ff0000'))
                pens.append(pg.mkPen(color='#ff0000', width=0.5))
        
        bars = pg.BarGraphItem(
            x=x_centers,
            height=heights,
            width=width,
            brushes=brushes,
            pens=pens
        )
        self.plot.addItem(bars)
        self.plot_items.append(bars)
        
        return [bars]
    
    def set_y_range(self, min_val, max_val, padding=0.1):
        """Establecer rango del eje Y."""
        if min_val != max_val:
            margin = (max_val - min_val) * padding
            self.plot.setYRange(min_val - margin, max_val + margin)
        else:
            self.plot.setYRange(min_val - 1, min_val + 1)
    
    def get_view_x_range(self):
        """Obtener rango actual del eje X."""
        return self.plot.getViewBox().viewRange()[0]
    
    def set_margins(self, left, top, right, bottom):
        """Establecer márgenes del gráfico."""
        plot_item = self.plot.getPlotItem()
        plot_item.layout.setContentsMargins(left, top, right, bottom)


class ChartView(QWidget):
    """Widget para gráficos de trading con velas japonesas y indicadores en tiempo real."""
    
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    request_real_time_data = pyqtSignal(str, str)
    request_historical_data = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_symbol = "US500"
        self.current_timeframe = "H1"
        self.historical_candles = []
        self.symbol_info = {}
        self.x_positions = []
        self.x_dates = []
        
        self.local_timezone = pytz.timezone('America/La_Paz')
        
        # Variables de configuración
        self.display_start_index = 0
        
        self.realtime_manager = RealTimeCandleManager()
        self.realtime_manager.update_timeframe(self.current_timeframe)
        
        self.price_cross = None
        self.cross_h_line = None
        self.cross_v_line = None
        self.cross_label = None
        self.last_bid = None
        
        self.cross_color = QColor(0, 150, 255, 220)
        self.current_cross_x = None
        self.current_cross_y = None
        
        self.indicators_config = {}
        self.indicator_plots = {}
        
        self.candle_items = []
        self.current_realtime_candle_items = []
        self.last_candle_index = -1
        
        self.drawn_indicators = {
            'sma': None,
            'ema': None,
            'bb_upper': None,
            'bb_middle': None,
            'bb_lower': None,
            'rsi': None,
            'macd_line': None,
            'macd_signal': None,
            'macd_histogram': None,
            'stoch_k': None,
            'stoch_d': None
        }
        
        self.real_time_active = True
        self.animation_enabled = True
        
        self.current_candle_display = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'change': None,
            'is_bullish': True
        }
        
        self.update_timers = {}
        self.last_update_time = datetime.now(pytz.utc)
        self.animation_interval = 100
        
        self.setMinimumSize(1200, 800)
        self.init_ui()
        self.init_chart()
        self.init_timers()
    
    def init_timers(self):
        """Inicializar todos los timers."""
        # Timer para animación de velas
        self.candle_animation_timer = QTimer()
        self.candle_animation_timer.timeout.connect(self.animate_current_candle)
        self.candle_animation_timer.start(500)
        
        # Timer para actualizar displays de tiempo
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self.update_time_displays)
        self.time_update_timer.start(1000)
        
        # Timer para animación suave de la cruz
        self.cross_animation_timer = QTimer()
        self.cross_animation_timer.timeout.connect(self.animate_price_cross)
        self.cross_animation_timer.start(100)
    
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)
        
        # Barra superior
        self.create_top_bar()
        main_layout.addWidget(self.top_bar_widget, 0)
        
        # Contenedor para gráficos
        self.graphs_container = QWidget()
        self.graphs_layout = QVBoxLayout(self.graphs_container)
        self.graphs_layout.setContentsMargins(0, 0, 0, 0)
        self.graphs_layout.setSpacing(1)
        main_layout.addWidget(self.graphs_container, 1)
        
        # Barra inferior
        self.create_info_bar()
        main_layout.addWidget(self.info_bar_widget, 0)
    
    def init_chart(self):
        """Inicializar el gráfico principal."""
        self.date_axis = DateAxis(orientation='bottom')
        
        self.main_plot = pg.GraphicsLayoutWidget()
        self.main_plot.setBackground('#0a0a0a')
        self.candle_plot = self.main_plot.addPlot(row=0, col=0, title="", axisItems={'bottom': self.date_axis})
        self.candle_plot.setLabel('left', 'Precio', color='#aaa')
        self.candle_plot.setLabel('bottom', 'Tiempo', color='#aaa')
        
        self.candle_plot.showGrid(x=True, y=True, alpha=0.3)
        self.candle_plot.getAxis('bottom').setGrid(255)
        self.candle_plot.getAxis('left').setGrid(255)
        self.candle_plot.setMouseEnabled(x=True, y=True)
        self.candle_plot.setMenuEnabled(False)
        
        self.up_color = QColor(0, 255, 0, 200)
        self.down_color = QColor(255, 0, 0, 200)
        self.realtime_bullish_color = QColor(0, 255, 0, 255)
        self.realtime_bearish_color = QColor(255, 0, 0, 255)
        
        self.candle_plot.layout.setContentsMargins(60, 5, 8, 50)
        
        font = QFont('Arial', 7)
        self.candle_plot.getAxis('left').setTickFont(font)
        self.candle_plot.getAxis('left').label.setFont(QFont('Arial', 9))
        self.candle_plot.getAxis('bottom').label.setFont(QFont('Arial', 9))
        
        self.show_date_labels = True
        self.graphs_layout.addWidget(self.main_plot, 3)
        
        self.create_indicator_plots()
        self.candle_plot.scene().sigMouseMoved.connect(self.on_mouse_moved)
    
    def create_indicator_plots(self):
        """Crear gráficos separados para indicadores técnicos."""
        self.rsi_plot = IndicatorPlot(self, height=120)
        self.rsi_plot.setVisible(False)
        self.rsi_plot.plot.setLabel('left', 'RSI')
        self.rsi_plot.plot.setXLink(self.candle_plot)
        self.rsi_plot.set_margins(60, 5, 8, 35)
        self.graphs_layout.addWidget(self.rsi_plot, 1)
        
        self.macd_plot = IndicatorPlot(self, height=120)
        self.macd_plot.setVisible(False)
        self.macd_plot.plot.setLabel('left', 'MACD')
        self.macd_plot.plot.setXLink(self.candle_plot)
        self.macd_plot.set_margins(60, 5, 8, 35)
        self.graphs_layout.addWidget(self.macd_plot, 1)
        
        self.stoch_plot = IndicatorPlot(self, height=120)
        self.stoch_plot.setVisible(False)
        self.stoch_plot.plot.setLabel('left', 'Stochastic')
        self.stoch_plot.plot.setXLink(self.candle_plot)
        self.stoch_plot.set_margins(60, 5, 8, 35)
        self.graphs_layout.addWidget(self.stoch_plot, 1)
        
        self.indicator_plots = {
            'rsi': self.rsi_plot,
            'macd': self.macd_plot,
            'stochastic': self.stoch_plot
        }
    
    def create_top_bar(self):
        """Crear barra superior."""
        self.top_bar_widget = QWidget()
        top_layout = QHBoxLayout(self.top_bar_widget)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(10)
        
        # Selector de símbolo
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["EURUSD", "US500", "GBPUSD", "USDJPY", "XAUUSD"])
        self.symbol_combo.setCurrentText(self.current_symbol)
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        self.symbol_combo.setFixedWidth(120)
        top_layout.addWidget(QLabel("Símbolo:"))
        top_layout.addWidget(self.symbol_combo)
        
        # Selector de timeframe
        self.timeframe_combo = QComboBox()
        timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
        self.timeframe_combo.addItems(timeframes)
        self.timeframe_combo.setCurrentText(self.current_timeframe)
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.timeframe_combo.setFixedWidth(80)
        top_layout.addWidget(QLabel("TF:"))
        top_layout.addWidget(self.timeframe_combo)
        
        # Botón de zoom
        self.btn_zoom_fit = QPushButton("🔍 Ajustar")
        self.btn_zoom_fit.clicked.connect(self.auto_scale_chart)
        self.btn_zoom_fit.setFixedWidth(110)
        top_layout.addWidget(self.btn_zoom_fit)
        
        # Botón para alternar indicadores
        self.btn_toggle_indicators = QPushButton("📈 Indicadores")
        self.btn_toggle_indicators.setCheckable(True)
        self.btn_toggle_indicators.setChecked(False)
        self.btn_toggle_indicators.toggled.connect(self.toggle_indicators)
        self.btn_toggle_indicators.setFixedWidth(120)
        top_layout.addWidget(self.btn_toggle_indicators)
        
        # Contador de vela actual
        self.lbl_candle_timer = QLabel("Vela: --:--")
        self.lbl_candle_timer.setStyleSheet("color: #ff9900; font-weight: bold; font-size: 12px;")
        self.lbl_candle_timer.setFixedWidth(80)
        top_layout.addWidget(self.lbl_candle_timer)
        
        top_layout.addStretch()
        
        # Información del símbolo (solo cambio)
        self.lbl_change = QLabel("Cambio: --")
        self.lbl_change.setStyleSheet("color: #aaa; font-size: 12px;")
        self.lbl_change.setFixedWidth(120)
        top_layout.addWidget(self.lbl_change)
    
    def create_info_bar(self):
        """Crear barra inferior."""
        self.info_bar_widget = QWidget()
        self.info_bar_widget.setFixedHeight(60)
        
        info_layout = QHBoxLayout(self.info_bar_widget)
        info_layout.setContentsMargins(12, 6, 12, 6)
        info_layout.setSpacing(15)
        
        self.info_bar_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Símbolo y timeframe
        symbol_group = QWidget()
        symbol_layout = QVBoxLayout(symbol_group)
        symbol_layout.setContentsMargins(0, 0, 0, 0)
        symbol_layout.setSpacing(2)
        
        self.lbl_symbol = QLabel(f"{self.current_symbol}")
        self.lbl_symbol.setStyleSheet("color: #ffa500; font-weight: bold; font-size: 14px;")
        
        self.lbl_timeframe = QLabel(f"TF: {self.current_timeframe}")
        self.lbl_timeframe.setStyleSheet("color: #aaa; font-size: 11px;")
        
        symbol_layout.addWidget(self.lbl_symbol)
        symbol_layout.addWidget(self.lbl_timeframe)
        symbol_group.setFixedWidth(80)
        info_layout.addWidget(symbol_group)
        
        # Separador
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("background-color: #444; margin: 0 5px;")
        separator1.setMaximumWidth(2)
        info_layout.addWidget(separator1)
        
        # Precio BID
        bid_group = QWidget()
        bid_layout = QVBoxLayout(bid_group)
        bid_layout.setContentsMargins(0, 0, 0, 0)
        bid_layout.setSpacing(2)
        
        self.bid_label = QLabel("BID")
        self.bid_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.bid_value = QLabel("--")
        self.bid_value.setStyleSheet("color: #0af; font-weight: bold; font-size: 13px;")
        
        bid_layout.addWidget(self.bid_label)
        bid_layout.addWidget(self.bid_value)
        bid_group.setFixedWidth(100)
        info_layout.addWidget(bid_group)
        
        # Precio ASK
        ask_group = QWidget()
        ask_layout = QVBoxLayout(ask_group)
        ask_layout.setContentsMargins(0, 0, 0, 0)
        ask_layout.setSpacing(2)
        
        self.ask_label = QLabel("ASK")
        self.ask_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.ask_value = QLabel("--")
        self.ask_value.setStyleSheet("color: #f0a; font-weight: bold; font-size: 13px;")
        
        ask_layout.addWidget(self.ask_label)
        ask_layout.addWidget(self.ask_value)
        ask_group.setFixedWidth(100)
        info_layout.addWidget(ask_group)
        
        # Spread
        spread_group = QWidget()
        spread_layout = QVBoxLayout(spread_group)
        spread_layout.setContentsMargins(0, 0, 0, 0)
        spread_layout.setSpacing(2)
        
        self.spread_label = QLabel("SPREAD")
        self.spread_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.spread_value = QLabel("--")
        self.spread_value.setStyleSheet("color: #fff; font-weight: bold; font-size: 13px;")
        
        spread_layout.addWidget(self.spread_label)
        spread_layout.addWidget(self.spread_value)
        spread_group.setFixedWidth(100)
        info_layout.addWidget(spread_group)
        
        # Separador
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setStyleSheet("background-color: #444; margin: 0 5px;")
        separator2.setMaximumWidth(2)
        info_layout.addWidget(separator2)
        
        # Vela actual
        candle_group = QWidget()
        candle_layout = QVBoxLayout(candle_group)
        candle_layout.setContentsMargins(0, 0, 0, 0)
        candle_layout.setSpacing(2)
        
        self.candle_label = QLabel("VELA ACTUAL")
        self.candle_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.candle_direction = QLabel("▲ Alcista")
        self.candle_direction.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 12px;")
        
        candle_layout.addWidget(self.candle_label)
        candle_layout.addWidget(self.candle_direction)
        candle_group.setFixedWidth(120)
        info_layout.addWidget(candle_group)
        
        # Separador
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.VLine)
        separator3.setFrameShadow(QFrame.Sunken)
        separator3.setStyleSheet("background-color: #444; margin: 0 5px;")
        separator3.setMaximumWidth(2)
        info_layout.addWidget(separator3)
        
        # Hora local
        time_group = QWidget()
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(2)
        
        self.time_label = QLabel("HORA LOCAL")
        self.time_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.time_value = QLabel("--:--:--")
        self.time_value.setStyleSheet("color: #0f0; font-size: 12px; font-weight: bold;")
        
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.time_value)
        time_group.setFixedWidth(120)
        info_layout.addWidget(time_group)
        
        # Fecha local
        date_group = QWidget()
        date_layout = QVBoxLayout(date_group)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(2)
        
        self.date_label = QLabel("FECHA LOCAL")
        self.date_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.date_value = QLabel("----/--/--")
        self.date_value.setStyleSheet("color: #ff00ff; font-size: 11px;")
        
        date_layout.addWidget(self.date_label)
        date_layout.addWidget(self.date_value)
        date_group.setFixedWidth(120)
        info_layout.addWidget(date_group)
        
        info_layout.addStretch()
    
    def update_time_displays(self):
        """Actualizar displays de tiempo en tiempo real."""
        local_time = self.get_local_time()
        
        self.time_value.setText(f"{local_time.strftime('%H:%M:%S')}")
        self.date_value.setText(f"{local_time.strftime('%Y/%m/%d')}")
        
        time_remaining = self.realtime_manager.get_time_to_next_candle(local_time)
        if time_remaining > 0:
            minutes = int(time_remaining // 60)
            seconds = int(time_remaining % 60)
            self.lbl_candle_timer.setText(f"{minutes}:{seconds:02d}")
        else:
            self.lbl_candle_timer.setText("0:00")
    
    def get_local_time(self):
        """Obtener la hora actual local (GMT-4)."""
        try:
            utc_now = datetime.now(pytz.utc)
            local_time = utc_now.astimezone(self.local_timezone)
            return local_time
        except Exception as e:
            local_time = datetime.now() - timedelta(hours=4)
            return self.local_timezone.localize(local_time)
    
    def update_current_candle_display(self, candle_data):
        """Actualizar display de la vela actual en tiempo real."""
        if candle_data and candle_data['open'] is not None:
            open_price = candle_data['open']
            high = candle_data['high']
            low = candle_data['low']
            close = candle_data['close']
            
            change = ((close - open_price) / open_price * 100) if open_price != 0 else 0
            change_text = f"{change:+.2f}%"
            
            is_bullish = close >= open_price
            
            if is_bullish:
                self.candle_direction.setText("▲ Alcista")
                self.candle_direction.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 12px;")
                self.lbl_change.setText(f"▲ {change_text}")
                self.lbl_change.setStyleSheet("color: #00ff00; font-weight: bold;")
            else:
                self.candle_direction.setText("▼ Bajista")
                self.candle_direction.setStyleSheet("color: #ff0000; font-weight: bold; font-size: 12px;")
                self.lbl_change.setText(f"▼ {change_text}")
                self.lbl_change.setStyleSheet("color: #ff0000; font-weight: bold;")
    
    def animate_current_candle(self):
        """Animación suave de la vela actual."""
        if not self.animation_enabled or not self.real_time_active:
            return
        
        current_time = datetime.now(pytz.utc)
        time_diff = (current_time - self.last_update_time).total_seconds() * 1000
        
        if time_diff >= self.animation_interval:
            self.last_update_time = current_time
            
            current_candle = self.realtime_manager.get_current_candle_data()
            if current_candle and current_candle['open'] is not None:
                self.update_current_realtime_candle(current_candle)
    
    def animate_price_cross(self):
        """Animación suave de la cruz del precio."""
        if self.last_bid is not None and len(self.x_positions) > 0:
            last_candle_x = self.x_positions[-1] if self.x_positions else 0
            
            if (self.current_cross_y is None or 
                abs(self.current_cross_y - self.last_bid) > 0.00001):
                self.update_price_cross(self.last_bid)
    
    def update_price_cross(self, price):
        """Actualizar la cruz azul con el precio actual."""
        if self.x_positions is None or len(self.x_positions) == 0:
            return
        
        last_candle_x = self.x_positions[-1] if self.x_positions else 0
        
        if self.current_cross_x is None or abs(self.current_cross_x - last_candle_x) > 0.5:
            self.create_price_cross(last_candle_x, price)
        else:
            self.current_cross_y = price
            
            if self.cross_h_line:
                self.cross_h_line.setData(
                    x=np.array([last_candle_x - 0.3, last_candle_x + 0.3], dtype=np.float64),
                    y=np.array([price, price], dtype=np.float64)
                )
            
            if self.cross_v_line:
                self.cross_v_line.setData(
                    x=np.array([last_candle_x, last_candle_x], dtype=np.float64),
                    y=np.array([price - 0.3, price + 0.3], dtype=np.float64)
                )
            
            if self.cross_label:
                if self.symbol_info:
                    digits = self.symbol_info.get('digits', 5)
                    price_text = f"{price:.{digits}f}"
                else:
                    price_text = f"{price:.5f}"
                
                self.cross_label.setText(price_text)
                self.cross_label.setPos(last_candle_x + 0.25, price + 0.45)
    
    def create_price_cross(self, x_pos, y_pos):
        """Crear una cruz azul sutil en la posición indicada."""
        if self.cross_h_line:
            self.candle_plot.removeItem(self.cross_h_line)
        if self.cross_v_line:
            self.candle_plot.removeItem(self.cross_v_line)
        if self.cross_label:
            self.candle_plot.removeItem(self.cross_label)
        
        cross_length = 0.3
        
        self.cross_h_line = pg.PlotCurveItem(
            x=np.array([x_pos - cross_length, x_pos + cross_length], dtype=np.float64),
            y=np.array([y_pos, y_pos], dtype=np.float64),
            pen=pg.mkPen(color=self.cross_color, width=1.8, style=Qt.SolidLine)
        )
        self.cross_h_line.setZValue(100)
        
        self.cross_v_line = pg.PlotCurveItem(
            x=np.array([x_pos, x_pos], dtype=np.float64),
            y=np.array([y_pos - cross_length, y_pos + cross_length], dtype=np.float64),
            pen=pg.mkPen(color=self.cross_color, width=1.8, style=Qt.SolidLine)
        )
        self.cross_v_line.setZValue(100)
        
        if self.symbol_info:
            digits = self.symbol_info.get('digits', 5)
            price_text = f"{y_pos:.{digits}f}"
        else:
            price_text = f"{y_pos:.5f}"
        
        self.cross_label = pg.TextItem(
            text=price_text,
            color=self.cross_color,
            anchor=(0, 1),
            fill=pg.mkBrush(color=(0, 0, 0, 180))
        )
        self.cross_label.setZValue(101)
        
        self.candle_plot.addItem(self.cross_h_line)
        self.candle_plot.addItem(self.cross_v_line)
        self.candle_plot.addItem(self.cross_label)
        
        label_offset_x = 0.25
        label_offset_y = cross_length + 0.15
        self.cross_label.setPos(x_pos + label_offset_x, y_pos + label_offset_y)
        
        self.current_cross_x = x_pos
        self.current_cross_y = y_pos
    
    def on_mouse_moved(self, pos):
        """Manejar movimiento del ratón para mostrar precio en posición actual."""
        if not self.candle_plot.sceneBoundingRect().contains(pos):
            return
        
        mouse_point = self.candle_plot.vb.mapSceneToView(pos)
        x_pos = mouse_point.x()
        y_pos = mouse_point.y()
        
        if len(self.x_positions) > 0:
            idx = np.argmin(np.abs(np.array(self.x_positions) - x_pos))
            if idx < len(self.x_positions):
                pass
    
    def toggle_indicators(self, checked):
        """Alternar visibilidad de los indicadores."""
        if checked and (self.historical_candles) and self.indicators_config:
            self.apply_indicators_to_chart()
        else:
            self.hide_all_indicators()
    
    def hide_all_indicators(self):
        """Ocultar todos los indicadores."""
        for plot in self.indicator_plots.values():
            plot.setVisible(False)
        
        items_to_remove = []
        for item in self.candle_plot.items:
            if hasattr(item, 'name') and item.name in ['sma', 'ema', 'bb_upper', 'bb_middle', 'bb_lower']:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.candle_plot.removeItem(item)
    
    def apply_indicators_to_chart(self):
        """Aplicar indicadores al gráfico."""
        all_candles = self.get_all_candles_for_indicators()
        if not all_candles or not self.indicators_config:
            return
        
        x_positions, opens, highs, lows, closes, volumes = self.prepare_candle_data(all_candles)
        self.calculate_and_draw_indicators(x_positions, opens, highs, lows, closes)
    
    def get_all_candles_for_indicators(self):
        """Obtener todas las velas para cálculos de indicadores."""
        all_candles = []
        all_candles.extend(self.historical_candles)
        
        from src.domain.entities.candle import Candle
        
        for candle_data in self.realtime_manager.get_completed_candles():
            if candle_data['open'] is not None:
                candle = Candle(
                    timestamp=candle_data['timestamp'],
                    open=candle_data['open'],
                    high=candle_data['high'],
                    low=candle_data['low'],
                    close=candle_data['close'],
                    volume=candle_data['volume']
                )
                all_candles.append(candle)
        
        current_candle = self.realtime_manager.get_current_candle_data()
        if current_candle and current_candle['open'] is not None:
            candle = Candle(
                timestamp=current_candle['timestamp'],
                open=current_candle['open'],
                high=current_candle['high'],
                low=current_candle['low'],
                close=current_candle['close'],
                volume=current_candle['volume']
            )
            all_candles.append(candle)
        
        return all_candles
    
    def prepare_candle_data(self, candles):
        """Preparar datos de velas."""
        if not candles:
            return (np.array([]), np.array([]), np.array([]), 
                    np.array([]), np.array([]), np.array([]))
        
        sorted_candles = sorted(candles, key=lambda x: 
            x.timestamp if hasattr(x, 'timestamp') else 
            x.time if hasattr(x, 'time') else 
            datetime.now())
        
        x_positions = []
        x_dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        current_x = 0
        
        for candle in sorted_candles:
            x_positions.append(current_x)
            current_x += 1
            
            if hasattr(candle, 'timestamp'):
                dt = candle.timestamp
            elif hasattr(candle, 'time'):
                dt = candle.time
            else:
                dt = datetime.now()
            
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                try:
                    dt_local = dt.astimezone(self.local_timezone)
                except:
                    dt_local = dt
            else:
                try:
                    dt_utc = pytz.utc.localize(dt)
                    dt_local = dt_utc.astimezone(self.local_timezone)
                except:
                    dt_local = dt
            
            x_dates.append(dt_local)
            opens.append(float(candle.open))
            highs.append(float(candle.high))
            lows.append(float(candle.low))
            closes.append(float(candle.close))
            
            if hasattr(candle, 'volume'):
                volumes.append(float(candle.volume))
            else:
                volumes.append(0)
        
        self.x_positions = x_positions
        self.x_dates = x_dates
        
        return (
            np.array(x_positions, dtype=np.float64),
            np.array(opens, dtype=np.float64),
            np.array(highs, dtype=np.float64),
            np.array(lows, dtype=np.float64),
            np.array(closes, dtype=np.float64),
            np.array(volumes, dtype=np.float64)
        )
    
    def update_current_realtime_candle(self, candle_data):
        """Actualizar solo la vela actual en tiempo real."""
        if not candle_data or candle_data['open'] is None:
            return
        
        existing_candle_idx = -1
        candle_timestamp = candle_data['timestamp']
        
        if isinstance(candle_timestamp, datetime):
            candle_timestamp_local = self._get_local_time(candle_timestamp)
        else:
            candle_timestamp_local = candle_timestamp
        
        for i, candle in enumerate(self.historical_candles):
            if hasattr(candle, 'timestamp'):
                hist_timestamp = self._get_local_time(candle.timestamp)
                if hist_timestamp == candle_timestamp_local:
                    existing_candle_idx = i
                    break
        
        if existing_candle_idx >= 0:
            x_pos = self.x_positions[existing_candle_idx] if existing_candle_idx < len(self.x_positions) else None
            self.update_existing_candle(existing_candle_idx, candle_data, x_pos)
        else:
            completed_candles = self.realtime_manager.get_completed_candles()
            for i, comp_candle in enumerate(completed_candles):
                comp_timestamp = self._get_local_time(comp_candle['timestamp'])
                if comp_timestamp == candle_timestamp_local:
                    existing_candle_idx = len(self.historical_candles) + i
                    x_pos = len(self.x_positions) + i if self.x_positions else i
                    self.update_existing_candle(existing_candle_idx, candle_data, x_pos)
                    return
        
        if existing_candle_idx < 0:
            self.add_new_candle(candle_data)
    
    def _get_local_time(self, timestamp):
        """Convertir timestamp a hora local GMT-4."""
        try:
            if isinstance(timestamp, datetime):
                if timestamp.tzinfo is not None:
                    return timestamp.astimezone(self.local_timezone)
                else:
                    utc_dt = pytz.utc.localize(timestamp)
                    return utc_dt.astimezone(self.local_timezone)
            return timestamp
        except Exception as e:
            print(f"Error convirtiendo a hora local: {e}")
            return timestamp
    
    def update_existing_candle(self, idx, candle_data, x_pos):
        """Actualizar una vela existente en el gráfico."""
        self.clear_candle_at_position(x_pos)
        is_complete = candle_data.get('is_complete', False)
        if is_complete:
            self.draw_single_candle(x_pos, candle_data, is_realtime=False)
        else:
            self.draw_single_candle(x_pos, candle_data, is_realtime=True)
    
    def add_new_candle(self, candle_data):
        """Agregar una nueva vela al gráfico."""
        if len(self.x_positions) > 0:
            new_x = self.x_positions[-1] + 1
        else:
            new_x = 0
        
        self.x_positions.append(new_x)
        self.x_dates.append(candle_data['timestamp'])
        
        is_complete = candle_data.get('is_complete', False)
        if is_complete:
            self.draw_single_candle(new_x, candle_data, is_realtime=False)
        else:
            self.draw_single_candle(new_x, candle_data, is_realtime=True)
        
        self.configure_x_axis_with_dates()
        
        if self.btn_toggle_indicators.isChecked() and self.indicators_config:
            self.update_indicators_with_realtime()
    
    def clear_candle_at_position(self, x_pos):
        """Limpiar elementos de vela en una posición específica."""
        items_to_remove = []
        for item in self.candle_plot.items:
            if hasattr(item, 'getData'):
                data = item.getData()
                if data and len(data[0]) > 0:
                    if len(data[0]) == 2 and data[0][0] == x_pos and data[0][1] == x_pos:
                        items_to_remove.append(item)
            elif hasattr(item, 'rect'):
                rect = item.rect()
                if abs(rect.x() + rect.width()/2 - x_pos) < 0.3:
                    items_to_remove.append(item)
        
        for item in items_to_remove:
            if item in self.candle_plot.items:
                self.candle_plot.removeItem(item)
                if item in self.candle_items:
                    self.candle_items.remove(item)
                if item in self.current_realtime_candle_items:
                    self.current_realtime_candle_items.remove(item)
    
    def draw_single_candle(self, x_position, candle_data, is_realtime=False):
        """Dibujar una sola vela con reglas clásicas."""
        if candle_data['open'] is None or candle_data['close'] is None:
            return
        
        candle_width = 0.5
        is_bullish = candle_data['close'] >= candle_data['open']
        
        if is_realtime:
            if is_bullish:
                color = self.realtime_bullish_color
            else:
                color = self.realtime_bearish_color
        else:
            if is_bullish:
                color = self.up_color
            else:
                color = self.down_color
        
        wick = pg.PlotCurveItem(
            x=np.array([x_position, x_position], dtype=np.float64),
            y=np.array([candle_data['low'], candle_data['high']], dtype=np.float64),
            pen=pg.mkPen(color=color, width=1.5)
        )
        self.candle_plot.addItem(wick)
        
        body_top = max(candle_data['open'], candle_data['close'])
        body_bottom = min(candle_data['open'], candle_data['close'])
        body_height = abs(candle_data['close'] - candle_data['open'])
        
        min_body_height = 0.0001
        if body_height < min_body_height:
            body_height = min_body_height
            if is_bullish:
                body_bottom = (candle_data['open'] + candle_data['close']) / 2 - body_height/2
            else:
                body_top = (candle_data['open'] + candle_data['close']) / 2 + body_height/2
        
        body = pg.QtWidgets.QGraphicsRectItem(
            x_position - candle_width/2,
            body_bottom,
            candle_width,
            body_height
        )
        body.setBrush(pg.mkBrush(color))
        body.setPen(pg.mkPen(color))
        self.candle_plot.addItem(body)
        
        if is_realtime:
            self.current_realtime_candle_items.extend([wick, body])
        else:
            self.candle_items.extend([wick, body])
        
        return wick, body
    
    def draw_candles(self, times, opens, highs, lows, closes):
        """Dibujar velas japonesas (solo históricas)."""
        if len(times) == 0:
            return
        
        self.clear_all_candles()
        
        for i in range(len(times)):
            is_bullish = closes[i] >= opens[i]
            color = self.up_color if is_bullish else self.down_color
            
            wick = pg.PlotCurveItem(
                x=np.array([times[i], times[i]], dtype=np.float64),
                y=np.array([lows[i], highs[i]], dtype=np.float64),
                pen=pg.mkPen(color=color, width=1.5)
            )
            self.candle_plot.addItem(wick)
            
            body_top = max(opens[i], closes[i])
            body_bottom = min(opens[i], closes[i])
            body_height = abs(closes[i] - opens[i])
            
            min_body_height = (max(highs) - min(lows)) * 0.002 if len(highs) > 0 else 0.0001
            if body_height < min_body_height:
                body_height = min_body_height
                if is_bullish:
                    body_bottom = (opens[i] + closes[i]) / 2 - body_height/2
                else:
                    body_top = (opens[i] + closes[i]) / 2 + body_height/2
            
            body = pg.QtWidgets.QGraphicsRectItem(
                times[i] - 0.5/2,
                body_bottom,
                0.5,
                body_height
            )
            body.setBrush(pg.mkBrush(color))
            body.setPen(pg.mkPen(color))
            self.candle_plot.addItem(body)
            
            self.candle_items.extend([wick, body])
        
        self.configure_x_axis_with_dates()
        
        current_candle = self.realtime_manager.get_current_candle_data()
        if current_candle and current_candle['open'] is not None:
            last_x = times[-1] if len(times) > 0 else 0
            self.draw_single_candle(last_x, current_candle, is_realtime=True)
    
    def clear_all_candles(self):
        """Limpiar todas las velas del gráfico."""
        for item in self.candle_items:
            if item in self.candle_plot.items:
                self.candle_plot.removeItem(item)
        
        self.candle_items = []
        self.clear_current_realtime_candle()
        self.clear_price_cross()
    
    def clear_current_realtime_candle(self):
        """Limpiar solo los elementos de la vela actual en tiempo real."""
        for item in self.current_realtime_candle_items:
            if item in self.candle_plot.items:
                self.candle_plot.removeItem(item)
        
        self.current_realtime_candle_items = []
    
    def clear_price_cross(self):
        """Limpiar la cruz del precio."""
        if self.cross_h_line:
            self.candle_plot.removeItem(self.cross_h_line)
            self.cross_h_line = None
        if self.cross_v_line:
            self.candle_plot.removeItem(self.cross_v_line)
            self.cross_v_line = None
        if self.cross_label:
            self.candle_plot.removeItem(self.cross_label)
            self.cross_label = None
        
        self.current_cross_x = None
        self.current_cross_y = None
    
    def configure_x_axis_with_dates(self):
        """Configurar eje X para mostrar fechas claramente."""
        if not self.x_positions or not self.x_dates or not self.show_date_labels:
            self.date_axis.set_ticks([], [], self.current_timeframe)
            return
        
        # Mostrar todas las posiciones
        tick_positions = []
        tick_labels = []
        
        n_candles = len(self.x_positions)
        
        if n_candles <= 15:
            step = 1
        else:
            step = max(1, n_candles // 12)
        
        indices = []
        for i in range(0, n_candles, step):
            indices.append(i)
        
        if n_candles > 0 and indices[-1] != n_candles - 1:
            indices.append(n_candles - 1)
        
        for idx in indices:
            if idx < len(self.x_positions) and idx < len(self.x_dates):
                dt = self.x_dates[idx]
                label = self.format_date_for_label(dt)
                tick_positions.append(self.x_positions[idx])
                tick_labels.append(label)
        
        filtered_positions = []
        filtered_labels = []
        min_distance = 1.5
        
        for i in range(len(tick_positions)):
            if i == 0 or i == len(tick_positions) - 1:
                filtered_positions.append(tick_positions[i])
                filtered_labels.append(tick_labels[i])
            else:
                if tick_positions[i] - filtered_positions[-1] >= min_distance:
                    filtered_positions.append(tick_positions[i])
                    filtered_labels.append(tick_labels[i])
        
        self.date_axis.set_ticks(filtered_positions, filtered_labels, self.current_timeframe)
        
        if len(self.x_positions) > 0:
            x_min = min(self.x_positions) - 1
            x_max = max(self.x_positions) + 1
            self.candle_plot.setXRange(x_min, x_max)
    
    def format_date_for_label(self, dt):
        """Formatear fecha para mostrar AAAA/MM/DD arriba y HH:MM abajo."""
        try:
            if isinstance(dt, datetime):
                if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                    dt_local = dt
                else:
                    dt_utc = pytz.utc.localize(dt)
                    dt_local = dt_utc.astimezone(self.local_timezone)
                
                date_str = dt_local.strftime('%Y/%m/%d')
                time_str = dt_local.strftime('%H:%M')
                return f"{date_str}\n{time_str}"
            else:
                pd_dt = pd.Timestamp(dt)
                if pd_dt.tz is not None:
                    pd_dt_local = pd_dt.tz_convert(self.local_timezone)
                else:
                    pd_dt_local = pd_dt.tz_localize('UTC').tz_convert(self.local_timezone)
                
                date_str = pd_dt_local.strftime('%Y/%m/%d')
                time_str = pd_dt_local.strftime('%H:%M')
                return f"{date_str}\n{time_str}"
        except Exception as e:
            print(f"Error formateando fecha: {e}")
            return str(dt)
    
    def auto_scale_chart(self):
        """Auto-ajustar el zoom del gráfico."""
        all_candles = self.get_all_candles_for_indicators()
        if not all_candles:
            return
        
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(all_candles)
        
        if len(times) > 0:
            x_margin = max(2.0, len(times) * 0.03)
            
            all_prices = np.concatenate([opens, highs, lows, closes])
            min_price = np.min(all_prices)
            max_price = np.max(all_prices)
            
            if self.current_cross_y is not None:
                min_price = min(min_price, self.current_cross_y)
                max_price = max(max_price, self.current_cross_y)
            
            if min_price != max_price:
                price_margin = (max_price - min_price) * 0.05
            else:
                price_margin = abs(min_price) * 0.01 if min_price != 0 else 1.0
            
            self.candle_plot.setXRange(min(times) - x_margin, max(times) + x_margin)
            self.candle_plot.setYRange(min_price - price_margin, max_price + price_margin)
    
    @pyqtSlot(dict)
    def update_price_display(self, price_data):
        """Actualizar display de precios en tiempo real."""
        if not price_data:
            return
        
        bid = price_data.get('bid', 0)
        ask = price_data.get('ask', 0)
        
        if bid > 0 and ask > 0:
            spread = abs(ask - bid) * 10000
            
            if self.symbol_info:
                digits = self.symbol_info.get('digits', 5)
                format_str = f"{{:.{digits}f}}"
                self.bid_value.setText(f"{format_str.format(bid)}")
                self.ask_value.setText(f"{format_str.format(ask)}")
            else:
                self.bid_value.setText(f"{bid:.5f}")
                self.ask_value.setText(f"{ask:.5f}")
            
            self.spread_value.setText(f"{spread:.1f}")
            
            if self.last_bid is not None:
                change = ((bid - self.last_bid) / self.last_bid) * 100
            
            self.last_bid = bid
    
    @pyqtSlot(dict)
    def update_indicator_settings(self, indicators_config: Dict):
        """Actualizar configuración de indicadores."""
        self.indicators_config = indicators_config
        
        if self.btn_toggle_indicators.isChecked():
            self.apply_indicators_to_chart()
    
    def clear_indicator_plots(self):
        """Limpiar todos los gráficos de indicadores."""
        for plot in self.indicator_plots.values():
            plot.clear_all()
    
    def calculate_and_draw_indicators(self, x_positions, opens, highs, lows, closes):
        """Calcular y dibujar indicadores técnicos."""
        if len(closes) == 0:
            return
        
        x_array = np.array(x_positions, dtype=np.float64)
        closes_array = np.array(closes, dtype=np.float64)
        highs_array = np.array(highs, dtype=np.float64)
        lows_array = np.array(lows, dtype=np.float64)
        
        self.clear_indicator_plots()
        
        # 1. SMA
        if self.indicators_config.get('sma', {}).get('enabled', False):
            period = self.indicators_config['sma'].get('period', 20)
            color = self.indicators_config['sma'].get('color', '#ffff00')
            self.draw_sma_from_start(x_array, closes_array, period, color)
        
        # 2. EMA
        if self.indicators_config.get('ema', {}).get('enabled', False):
            period = self.indicators_config['ema'].get('period', 12)
            color = self.indicators_config['ema'].get('color', '#ff00ff')
            self.draw_ema_from_start(x_array, closes_array, period, color)
        
        # 3. Bollinger Bands
        if self.indicators_config.get('bollinger', {}).get('enabled', False):
            period = self.indicators_config['bollinger'].get('period', 20)
            std = self.indicators_config['bollinger'].get('std', 2.0)
            self.draw_bollinger_bands_from_start(x_array, closes_array, period, std)
        
        # 4. RSI
        if self.indicators_config.get('rsi', {}).get('enabled', False):
            period = self.indicators_config['rsi'].get('period', 14)
            overbought = self.indicators_config['rsi'].get('overbought', 80)
            oversold = self.indicators_config['rsi'].get('oversold', 20)
            color = self.indicators_config['rsi'].get('color', '#ffaa00')
            self.draw_rsi_from_start(x_array, closes_array, period, overbought, oversold, color)
        
        # 5. MACD
        if self.indicators_config.get('macd', {}).get('enabled', False):
            fast = self.indicators_config['macd'].get('fast', 12)
            slow = self.indicators_config['macd'].get('slow', 26)
            signal = self.indicators_config['macd'].get('signal', 9)
            self.draw_macd_from_start(x_array, closes_array, fast, slow, signal)
        
        # 6. Stochastic
        if self.indicators_config.get('stochastic', {}).get('enabled', False):
            k_period = self.indicators_config['stochastic'].get('k_period', 14)
            d_period = self.indicators_config['stochastic'].get('d_period', 3)
            slowing = self.indicators_config['stochastic'].get('slowing', 3)
            self.draw_stochastic_from_start(x_array, highs_array, lows_array, closes_array, 
                                          k_period, d_period, slowing)
    
    def draw_sma_from_start(self, x_data, closes, period, color):
        """Dibujar Media Móvil Simple desde la primera vela."""
        if len(closes) < 1:
            return
        
        sma = np.full_like(closes, np.nan)
        
        for i in range(len(closes)):
            if i < period - 1:
                sma[i] = np.mean(closes[:i+1])
            else:
                sma[i] = np.mean(closes[i - period + 1:i + 1])
        
        sma_line = pg.PlotCurveItem(
            x=x_data,
            y=sma,
            pen=pg.mkPen(color=color, width=2),
            name='sma'
        )
        self.candle_plot.addItem(sma_line)
        self.drawn_indicators['sma'] = sma_line
    
    def draw_ema_from_start(self, x_data, closes, period, color):
        """Dibujar Media Móvil Exponencial desde la primera vela."""
        if len(closes) < 1:
            return
        
        ema = np.full_like(closes, np.nan)
        multiplier = 2 / (period + 1)
        
        ema[0] = closes[0]
        
        for i in range(1, len(closes)):
            if np.isnan(ema[i-1]):
                ema[i] = closes[i]
            else:
                ema[i] = (closes[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        ema_line = pg.PlotCurveItem(
            x=x_data,
            y=ema,
            pen=pg.mkPen(color=color, width=2),
            name='ema'
        )
        self.candle_plot.addItem(ema_line)
        self.drawn_indicators['ema'] = ema_line
    
    def draw_bollinger_bands_from_start(self, x_data, closes, period, std_multiplier):
        """Dibujar Bandas de Bollinger desde la primera vela."""
        if len(closes) < 2:
            return
        
        bb_middle = np.full_like(closes, np.nan)
        bb_upper = np.full_like(closes, np.nan)
        bb_lower = np.full_like(closes, np.nan)
        
        for i in range(len(closes)):
            if i < period - 1:
                window = closes[:i+1]
                if len(window) >= 2:
                    middle = np.mean(window)
                    std = np.std(window)
                    bb_middle[i] = middle
                    bb_upper[i] = middle + (std * std_multiplier)
                    bb_lower[i] = middle - (std * std_multiplier)
            else:
                window = closes[i - period + 1:i + 1]
                middle = np.mean(window)
                std = np.std(window)
                bb_middle[i] = middle
                bb_upper[i] = middle + (std * std_multiplier)
                bb_lower[i] = middle - (std * std_multiplier)
        
        valid_mask = ~np.isnan(bb_middle)
        if np.any(valid_mask):
            upper_line = pg.PlotCurveItem(
                x=x_data[valid_mask],
                y=bb_upper[valid_mask],
                pen=pg.mkPen(color='#00ffff', width=1.5, style=Qt.DashLine),
                name='bb_upper'
            )
            self.candle_plot.addItem(upper_line)
            self.drawn_indicators['bb_upper'] = upper_line
            
            middle_line = pg.PlotCurveItem(
                x=x_data[valid_mask],
                y=bb_middle[valid_mask],
                pen=pg.mkPen(color='#ffffff', width=2),
                name='bb_middle'
            )
            self.candle_plot.addItem(middle_line)
            self.drawn_indicators['bb_middle'] = middle_line
            
            lower_line = pg.PlotCurveItem(
                x=x_data[valid_mask],
                y=bb_lower[valid_mask],
                pen=pg.mkPen(color='#00ffff', width=1.5, style=Qt.DashLine),
                name='bb_lower'
            )
            self.candle_plot.addItem(lower_line)
            self.drawn_indicators['bb_lower'] = lower_line
    
    def draw_rsi_from_start(self, x_data, closes, period, overbought, oversold, color):
        """Dibujar RSI desde la primera vela."""
        if len(closes) < 2:
            return
        
        rsi = np.full_like(closes, np.nan)
        rsi[0] = 50
        
        for i in range(1, len(closes)):
            if i < period:
                window_size = min(i, period)
                window = closes[i-window_size+1:i+1]
                if len(window) >= 2:
                    deltas = np.diff(window)
                    gains = np.where(deltas > 0, deltas, 0)
                    losses = np.where(deltas < 0, -deltas, 0)
                    
                    avg_gain = np.mean(gains) if len(gains) > 0 else 0
                    avg_loss = np.mean(losses) if len(losses) > 0 else 0
                    
                    if avg_loss == 0:
                        rsi[i] = 100
                    else:
                        rs = avg_gain / avg_loss
                        rsi[i] = 100 - (100 / (1 + rs))
            else:
                window = closes[i-period+1:i+1]
                deltas = np.diff(window)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                
                avg_gain = np.mean(gains) if len(gains) > 0 else 0
                avg_loss = np.mean(losses) if len(losses) > 0 else 0
                
                if avg_loss == 0:
                    rsi[i] = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi[i] = 100 - (100 / (1 + rs))
        
        self.rsi_plot.setVisible(True)
        self.rsi_plot.add_hline(overbought, color='#ff6666', width=1, label=f"OB ({overbought})")
        self.rsi_plot.add_hline(oversold, color='#66ff66', width=1, label=f"OS ({oversold})")
        self.rsi_plot.add_hline(50, color='#666666', width=0.5, style=Qt.DashLine, label="50")
        
        valid_mask = ~np.isnan(rsi)
        if np.any(valid_mask):
            self.rsi_plot.plot_indicator(x_data[valid_mask], rsi[valid_mask], color, f'RSI({period})', width=2)
        
        self.rsi_plot.set_y_range(0, 100)
    
    def draw_macd_from_start(self, x_data, closes, fast_period, slow_period, signal_period):
        """Dibujar MACD desde la primera vela."""
        if len(closes) < 2:
            return
        
        ema_fast = self.calculate_ema_from_start(closes, fast_period)
        ema_slow = self.calculate_ema_from_start(closes, slow_period)
        
        macd_line = np.full_like(closes, np.nan)
        for i in range(len(closes)):
            if not np.isnan(ema_fast[i]) and not np.isnan(ema_slow[i]):
                macd_line[i] = ema_fast[i] - ema_slow[i]
        
        signal_line = self.calculate_ema_from_start(macd_line, signal_period)
        
        histogram = np.full_like(closes, np.nan)
        for i in range(len(closes)):
            if not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]):
                histogram[i] = macd_line[i] - signal_line[i]
        
        self.macd_plot.setVisible(True)
        self.macd_plot.add_hline(0, color='#666666', width=0.5, style=Qt.DashLine, label="0")
        
        valid_hist = ~np.isnan(histogram)
        if np.any(valid_hist):
            self.macd_plot.plot_histogram(x_data[valid_hist], histogram[valid_hist])
        
        valid_mask = ~np.isnan(macd_line) & ~np.isnan(signal_line)
        if np.any(valid_mask):
            self.macd_plot.plot_indicator(
                x_data[valid_mask], 
                macd_line[valid_mask], 
                '#00aaff',
                f'MACD({fast_period},{slow_period})', 
                width=2
            )
            
            self.macd_plot.plot_indicator(
                x_data[valid_mask], 
                signal_line[valid_mask], 
                '#ffaa00',
                f'Signal({signal_period})', 
                width=2
            )
        
        if np.any(valid_mask):
            macd_vals = macd_line[valid_mask]
            signal_vals = signal_line[valid_mask]
            
            if np.any(valid_hist):
                hist_vals = histogram[valid_hist]
                all_vals = np.concatenate([macd_vals, signal_vals, hist_vals])
            else:
                all_vals = np.concatenate([macd_vals, signal_vals])
            
            if len(all_vals) > 0:
                min_val = np.min(all_vals)
                max_val = np.max(all_vals)
                
                if min_val != max_val:
                    margin = (max_val - min_val) * 0.1
                    self.macd_plot.set_y_range(min_val - margin, max_val + margin)
    
    def calculate_ema_from_start(self, data, period):
        """Calcular EMA desde la primera vela."""
        if len(data) < 1:
            return np.full_like(data, np.nan)
        
        ema = np.full_like(data, np.nan)
        ema[0] = data[0]
        multiplier = 2.0 / (period + 1.0)
        
        for i in range(1, len(data)):
            if not np.isnan(ema[i - 1]) and not np.isnan(data[i]):
                ema[i] = (data[i] * multiplier) + (ema[i - 1] * (1 - multiplier))
            elif np.isnan(ema[i - 1]) and not np.isnan(data[i]):
                ema[i] = data[i]
        
        return ema
    
    def draw_stochastic_from_start(self, x_data, highs, lows, closes, k_period, d_period, slowing):
        """Dibujar Oscilador Estocástico desde la primera vela."""
        if len(closes) < 2:
            return
        
        k_line = np.full_like(closes, np.nan)
        
        for i in range(len(closes)):
            if i < k_period - 1:
                high_window = highs[:i+1]
                low_window = lows[:i+1]
                current_close = closes[i]
                
                if len(high_window) >= 2 and len(low_window) >= 2:
                    highest_high = np.max(high_window)
                    lowest_low = np.min(low_window)
                    
                    if highest_high != lowest_low:
                        k_line[i] = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
                    else:
                        k_line[i] = 50
            else:
                high_window = highs[i - k_period + 1:i + 1]
                low_window = lows[i - k_period + 1:i + 1]
                current_close = closes[i]
                
                highest_high = np.max(high_window)
                lowest_low = np.min(low_window)
                
                if highest_high != lowest_low:
                    k_line[i] = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
                else:
                    k_line[i] = 50
        
        if slowing > 1:
            k_line_smoothed = np.full_like(k_line, np.nan)
            for i in range(len(k_line)):
                if i < slowing - 1:
                    window = k_line[:i+1]
                    if np.any(~np.isnan(window)):
                        k_line_smoothed[i] = np.nanmean(window)
                else:
                    window = k_line[i - slowing + 1:i + 1]
                    if np.any(~np.isnan(window)):
                        k_line_smoothed[i] = np.nanmean(window)
            k_line = k_line_smoothed
        
        d_line = np.full_like(closes, np.nan)
        
        for i in range(len(k_line)):
            if i < d_period - 1:
                window = k_line[:i+1]
                if np.any(~np.isnan(window)):
                    d_line[i] = np.nanmean(window)
            else:
                window = k_line[i - d_period + 1:i + 1]
                if np.any(~np.isnan(window)):
                    d_line[i] = np.nanmean(window)
        
        self.stoch_plot.setVisible(True)
        self.stoch_plot.add_hline(80, color='#ff6666', width=1, label="Overbought (80)")
        self.stoch_plot.add_hline(20, color='#66ff66', width=1, label="Oversold (20)")
        self.stoch_plot.add_hline(50, color='#666666', width=0.5, style=Qt.DashLine, label="Mid (50)")
        
        valid_mask = ~np.isnan(k_line) & ~np.isnan(d_line)
        if np.any(valid_mask):
            self.stoch_plot.plot_indicator(
                x_data[valid_mask], 
                k_line[valid_mask], 
                '#00ffff',
                f'%K({k_period},{slowing})', 
                width=2,
                style=Qt.SolidLine
            )
            
            self.stoch_plot.plot_indicator(
                x_data[valid_mask], 
                d_line[valid_mask], 
                '#ffff00',
                f'%D({d_period})', 
                width=2,
                style=Qt.DashLine
            )
        
        self.stoch_plot.set_y_range(0, 100)
    
    def update_indicators_with_realtime(self):
        """Actualizar indicadores con datos en tiempo real."""
        all_candles = self.get_all_candles_for_indicators()
        if not all_candles:
            return
        
        x_positions, opens, highs, lows, closes, volumes = self.prepare_candle_data(all_candles)
        self.calculate_and_draw_indicators(x_positions, opens, highs, lows, closes)
    
    def update_chart(self, data, indicator_configs=None):
        """Actualizar el gráfico con nuevos datos históricos."""
        if not data:
            return
        
        self.historical_candles = data
        
        if indicator_configs is not None:
            self.indicators_config = indicator_configs
        
        self.candle_plot.clear()
        self.candle_items = []
        self.current_realtime_candle_items = []
        
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(self.historical_candles)
        
        if len(times) == 0:
            return
        
        self.draw_candles(times, opens, highs, lows, closes)
        self.configure_price_axis()
        self.auto_scale_chart()
        
        if self.btn_toggle_indicators.isChecked() and self.indicators_config:
            self.apply_indicators_to_chart()
    
    def get_all_candles(self):
        """Obtener todas las velas (históricas + tiempo real completadas)."""
        all_candles = self.historical_candles.copy()
        
        from src.domain.entities.candle import Candle
        
        for candle_data in self.realtime_manager.get_completed_candles():
            if candle_data['open'] is not None:
                candle = Candle(
                    timestamp=candle_data['timestamp'],
                    open=candle_data['open'],
                    high=candle_data['high'],
                    low=candle_data['low'],
                    close=candle_data['close'],
                    volume=candle_data['volume']
                )
                all_candles.append(candle)
        
        return all_candles
    
    def update_symbol_info_display(self):
        """Actualizar display de información del símbolo."""
        self.lbl_symbol.setText(f"{self.current_symbol}")
        self.lbl_timeframe.setText(f"TF: {self.current_timeframe}")
    
    def configure_price_axis(self):
        """Configurar el eje Y según los dígitos del símbolo."""
        if not self.symbol_info:
            return
        
        digits = self.symbol_info.get('digits', 5)
        left_axis = self.candle_plot.getAxis('left')
        
        if digits == 5:
            left_axis.setLabel('Precio (0.00001)')
        elif digits == 4:
            left_axis.setLabel('Precio (0.0001)')
        elif digits == 3:
            left_axis.setLabel('Precio (0.001)')
        elif digits == 2:
            left_axis.setLabel('Precio (0.01)')
        
        left_axis.enableAutoSIPrefix(False)
    
    def refresh_chart(self):
        """Refrescar el gráfico manualmente."""
        self.symbol_changed.emit(self.current_symbol)
        self.timeframe_changed.emit(self.current_timeframe)
        self.update_symbol_info_display()
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.symbol_changed.emit(symbol)
        self.update_symbol_info_display()
        self.realtime_manager.reset()
        self.clear_current_realtime_candle()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.current_timeframe = timeframe
        self.timeframe_changed.emit(timeframe)
        self.update_symbol_info_display()
        self.realtime_manager.update_timeframe(timeframe)
        self.clear_current_realtime_candle()
    
    def clear_all(self):
        """Limpiar todos los datos del gráfico."""
        self.historical_candles = []
        self.realtime_manager.reset()
        self.clear_all_candles()
        self.clear_indicator_plots()