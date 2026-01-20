# src/infrastructure/ui/chart_view.py
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot, QRectF
from PyQt5.QtGui import QColor, QFont, QPen, QPainter
import pyqtgraph as pg
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Optional, Dict, Any
import time
from collections import deque

# Configurar pyqtgraph para mejor rendimiento
pg.setConfigOptions(antialias=True)


class RealTimeCandle:
    """Clase para manejar velas en tiempo real."""
    
    def __init__(self, timestamp: datetime, timeframe: str = "H1"):
        self.timestamp = timestamp
        self.timeframe = timeframe
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.volume = 0
        self.is_complete = False
        
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
        """Actualizar vela con nuevo precio."""
        if self.open is None:
            self.open = price
            self.high = price
            self.low = price
            self.close = price
        else:
            self.high = max(self.high, price)
            self.low = min(self.low, price)
            self.close = price
        
        self.volume += volume
    
    def should_close(self, current_time: datetime) -> bool:
        """Verificar si la vela debe cerrarse."""
        elapsed = (current_time - self.timestamp).total_seconds()
        return elapsed >= self.timeframe_seconds
    
    def close_candle(self, price: float = None):
        """Cerrar la vela."""
        if price is not None:
            self.close = price
            self.high = max(self.high, price)
            self.low = min(self.low, price)
        
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
            'is_complete': self.is_complete
        }


class RealTimeCandleManager:
    """Gestor de velas en tiempo real."""
    
    def __init__(self, max_realtime_candles: int = 50):
        self.current_candle = None
        self.completed_candles = deque(maxlen=max_realtime_candles)
        self.timeframe = "H1"
        self.timeframe_seconds = 3600
        self.last_price = None
        self.last_update_time = None
        
    def update_timeframe(self, timeframe: str):
        """Actualizar timeframe."""
        self.timeframe = timeframe
        self.timeframe_seconds = self._timeframe_to_seconds(timeframe)
        
        # Reiniciar vela actual
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
        """Actualizar precio en tiempo real."""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.last_price = price
        self.last_update_time = timestamp
        
        # Determinar el inicio de la vela actual
        candle_start = self._get_candle_start_time(timestamp)
        
        # Si no hay vela actual o la vela actual pertenece a un periodo diferente
        if self.current_candle is None or self.current_candle.timestamp != candle_start:
            # Si hay una vela actual, cerrarla
            if self.current_candle is not None and not self.current_candle.is_complete:
                self.completed_candles.append(self.current_candle.close_candle(self.last_price))
            
            # Crear nueva vela
            self.current_candle = RealTimeCandle(candle_start, self.timeframe)
            self.current_candle.update(price)
        else:
            # Actualizar vela actual
            self.current_candle.update(price)
        
        # Verificar si la vela actual debe cerrarse
        if self.current_candle.should_close(timestamp) and not self.current_candle.is_complete:
            self.completed_candles.append(self.current_candle.close_candle(price))
            
            # Crear nueva vela para el siguiente periodo
            next_candle_start = self._get_candle_start_time(timestamp + timedelta(seconds=1))
            self.current_candle = RealTimeCandle(next_candle_start, self.timeframe)
            self.current_candle.update(price)
        
        return {
            'current_candle': self.current_candle.to_dict() if self.current_candle else None,
            'completed_candles': [c.to_dict() for c in self.completed_candles],
            'last_price': price,
            'timestamp': timestamp
        }
    
    def _get_candle_start_time(self, timestamp: datetime) -> datetime:
        """Calcular el tiempo de inicio de la vela."""
        if self.timeframe == "M1":
            return timestamp.replace(second=0, microsecond=0)
        elif self.timeframe == "M5":
            minute = (timestamp.minute // 5) * 5
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "M15":
            minute = (timestamp.minute // 15) * 15
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "M30":
            minute = (timestamp.minute // 30) * 30
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "H1":
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif self.timeframe == "H4":
            hour = (timestamp.hour // 4) * 4
            return timestamp.replace(hour=hour, minute=0, second=0, microsecond=0)
        elif self.timeframe == "D1":
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            return timestamp.replace(second=0, microsecond=0)
    
    def get_time_to_next_candle(self, current_time: datetime = None) -> float:
        """Obtener tiempo restante para la siguiente vela."""
        if current_time is None:
            current_time = datetime.now()
        
        if self.current_candle is None:
            return self.timeframe_seconds
        
        # Calcular tiempo de finalización de la vela actual
        candle_end = self.current_candle.timestamp + timedelta(seconds=self.timeframe_seconds)
        
        # Calcular tiempo restante
        time_remaining = (candle_end - current_time).total_seconds()
        return max(0, time_remaining)
    
    def get_current_candle_data(self) -> Optional[Dict]:
        """Obtener datos de la vela actual."""
        if self.current_candle:
            return self.current_candle.to_dict()
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
        
        # Configurar fuente pequeña y legible
        font = QFont('Arial', 7)  # Fuente pequeña pero legible
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
        # Llamar al método original para mantener el comportamiento por defecto
        super().drawPicture(p, axisSpec, tickSpecs, textSpecs)


class IndicatorPlot(QWidget):
    """Widget para mostrar indicadores técnicos en gráficos separados."""
    
    def __init__(self, parent=None, height: int = 150):
        super().__init__(parent)
        self.height = height
        self.plot_items = []  # Mantener referencia a todos los items
        self.horizontal_lines = []  # Líneas horizontales fijas
        self.init_ui()
        
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Gráfico para indicadores
        self.plot = pg.PlotWidget()
        self.plot.setBackground('#0a0a0a')
        self.plot.setMinimumHeight(self.height)
        self.plot.setMaximumHeight(self.height)
        self.plot.setLabel('left', 'Valor')
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setMenuEnabled(False)
        
        # Configurar colores de ejes
        self.plot.getAxis('left').setPen(pg.mkPen(color='#666'))
        self.plot.getAxis('bottom').setPen(pg.mkPen(color='#666'))
        
        # Configurar fuente pequeña para ejes de indicadores
        font = QFont('Arial', 7)
        self.plot.getAxis('left').setTickFont(font)
        self.plot.getAxis('bottom').setTickFont(font)
        
        layout.addWidget(self.plot)
    
    def clear(self):
        """Limpiar el gráfico completamente."""
        self.plot.clear()
        self.plot_items = []
        # Re-crear líneas horizontales si existen
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
        
        # Filtrar valores NaN
        valid_mask = ~np.isnan(y_data)
        if not np.any(valid_mask):
            return None
        
        x_valid = x_data[valid_mask]
        y_valid = y_data[valid_mask]
        
        # Crear línea del indicador
        line = pg.PlotCurveItem(
            x=x_valid,
            y=y_valid,
            pen=pg.mkPen(color=color, width=width, style=style)
        )
        self.plot.addItem(line)
        self.plot_items.append(line)
        
        # Agregar etiqueta con el nombre
        if name and len(x_valid) > 0:
            # Crear etiqueta al final de la línea
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
        
        # Agregar etiqueta si se proporciona
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
        
        # Guardar referencia para re-crear después de clear()
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
        
        # Filtrar valores NaN
        valid_mask = ~np.isnan(y_data)
        if not np.any(valid_mask):
            return []
        
        x_valid = x_data[valid_mask]
        y_valid = y_data[valid_mask]
        
        # Preparar datos para BarGraphItem
        x_centers = x_valid
        heights = y_valid
        width = width
        
        # Crear colores basados en valores positivos/negativos
        brushes = []
        pens = []
        for y in y_valid:
            if y >= 0:
                brushes.append(pg.mkBrush(color='#00ff00'))
                pens.append(pg.mkPen(color='#00ff00', width=0.5))
            else:
                brushes.append(pg.mkBrush(color='#ff0000'))
                pens.append(pg.mkPen(color='#ff0000', width=0.5))
        
        # Crear histograma como un solo BarGraphItem para mejor performance
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
        # En pyqtgraph, necesitamos acceder al layout interno del PlotItem
        plot_item = self.plot.getPlotItem()
        plot_item.layout.setContentsMargins(left, top, right, bottom)


class ChartView(QWidget):
    """Widget para gráficos de trading con velas japonesas y indicadores en tiempo real."""
    
    # Señales
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    request_real_time_data = pyqtSignal(str, str)  # Señal para datos en tiempo real
    request_historical_data = pyqtSignal(str, str, int)  # Señal para datos históricos
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración inicial
        self.current_symbol = "US500"
        self.current_timeframe = "H1"
        self.historical_candles = []  # Velas históricas
        self.realtime_candles = []    # Velas en tiempo real
        self.symbol_info = {}
        self.x_positions = []
        self.x_dates = []
        
        # Gestor de velas en tiempo real
        self.realtime_manager = RealTimeCandleManager(max_realtime_candles=100)
        self.realtime_manager.update_timeframe(self.current_timeframe)
        
        # Variables para el señalador
        self.price_cross = None
        self.cross_h_line = None
        self.cross_v_line = None
        self.cross_label = None
        self.last_bid = None
        
        # Color fijo para la cruz
        self.cross_color = QColor(0, 150, 255, 220)
        
        # Variables para la posición de la cruz
        self.current_cross_x = None
        self.current_cross_y = None
        
        # Configuración de indicadores
        self.indicators_config = {}
        self.indicator_plots = {}
        
        # Diccionario para mantener referencias a los indicadores dibujados
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
        
        # Variables para tiempo real
        self.real_time_active = True  # Activado por defecto
        self.current_candle_start = None
        
        # Estado de visualización de vela actual
        self.current_candle_display = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'change': None,
            'is_bullish': True
        }
        
        # Timers
        self.update_timers = {}
        
        self.setMinimumSize(1200, 800)  # Aumentado el tamaño mínimo
        
        # Inicializar UI
        self.init_ui()
        self.init_chart()
        
        # Iniciar timers
        self.init_timers()
    
    def init_timers(self):
        """Inicializar todos los timers."""
        # Timer para actualización de displays de tiempo
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self.update_time_displays)
        self.time_update_timer.start(1000)  # Actualizar cada segundo
        
        # Timer para datos en tiempo real
        self.real_time_timer = QTimer()
        self.real_time_timer.timeout.connect(self.update_real_time_data)
        self.real_time_timer.start(2000)  # Actualizar cada 2 segundos
        
        # Timer para actualizar vela en tiempo real
        self.candle_update_timer = QTimer()
        self.candle_update_timer.timeout.connect(self.update_realtime_candle_display)
        self.candle_update_timer.start(500)  # Actualizar cada 500ms
        
        # Timer para animación suave de la cruz
        self.cross_animation_timer = QTimer()
        self.cross_animation_timer.timeout.connect(self.animate_price_cross)
        self.cross_animation_timer.start(100)  # Actualizar cada 100ms
        
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)
        
        # 1. Barra superior de controles
        self.create_top_bar()
        main_layout.addWidget(self.top_bar_widget)
        
        # 2. Contenedor para gráficos
        self.graphs_container = QWidget()
        self.graphs_layout = QVBoxLayout(self.graphs_container)
        self.graphs_layout.setContentsMargins(0, 0, 0, 0)
        self.graphs_layout.setSpacing(1)
        main_layout.addWidget(self.graphs_container, 1)
        
        # 3. Barra inferior
        self.create_info_bar()
        main_layout.addWidget(self.info_bar_widget)
        
    def init_chart(self):
        """Inicializar el gráfico principal."""
        self.date_axis = DateAxis(orientation='bottom')
        
        # Crear plot para velas
        self.main_plot = pg.GraphicsLayoutWidget()
        self.main_plot.setBackground('#0a0a0a')
        self.candle_plot = self.main_plot.addPlot(row=0, col=0, title="", axisItems={'bottom': self.date_axis})
        self.candle_plot.setLabel('left', 'Precio', color='#aaa')
        self.candle_plot.setLabel('bottom', 'Tiempo', color='#aaa')
        
        # Configurar grid
        self.candle_plot.showGrid(x=True, y=True, alpha=0.3)
        self.candle_plot.getAxis('bottom').setGrid(255)
        self.candle_plot.getAxis('left').setGrid(255)
        self.candle_plot.setMouseEnabled(x=True, y=True)
        self.candle_plot.setMenuEnabled(False)
        
        # Configurar colores para velas
        self.up_color = QColor(0, 255, 0, 200)
        self.down_color = QColor(255, 0, 0, 200)
        
        # Color para vela actual en tiempo real
        self.realtime_candle_color = QColor(255, 165, 0, 150)  # Naranja semitransparente
        
        # Configurar márgenes para mejor legibilidad
        self.candle_plot.layout.setContentsMargins(60, 5, 8, 50)  # Margen ajustado
        
        # Configurar fuente para ejes
        font = QFont('Arial', 7)
        self.candle_plot.getAxis('left').setTickFont(font)
        self.candle_plot.getAxis('left').label.setFont(QFont('Arial', 9))
        self.candle_plot.getAxis('bottom').label.setFont(QFont('Arial', 9))
        
        # Control de visibilidad de etiquetas
        self.show_date_labels = True
        
        # Añadir el gráfico principal
        self.graphs_layout.addWidget(self.main_plot, 3)
        
        # Crear gráficos para indicadores
        self.create_indicator_plots()
        
        # Conectar señales de movimiento del ratón para actualizar la cruz
        self.candle_plot.scene().sigMouseMoved.connect(self.on_mouse_moved)
    
    def create_indicator_plots(self):
        """Crear gráficos separados para indicadores técnicos."""
        # Gráfico para RSI
        self.rsi_plot = IndicatorPlot(self, height=120)
        self.rsi_plot.setVisible(False)
        self.rsi_plot.plot.setLabel('left', 'RSI')
        self.rsi_plot.plot.setXLink(self.candle_plot)
        # Usar el método set_margins para establecer márgenes
        self.rsi_plot.set_margins(60, 5, 8, 35)  # Margen ajustado
        self.graphs_layout.addWidget(self.rsi_plot, 1)
        
        # Gráfico para MACD
        self.macd_plot = IndicatorPlot(self, height=120)
        self.macd_plot.setVisible(False)
        self.macd_plot.plot.setLabel('left', 'MACD')
        self.macd_plot.plot.setXLink(self.candle_plot)
        self.macd_plot.set_margins(60, 5, 8, 35)  # Margen ajustado
        self.graphs_layout.addWidget(self.macd_plot, 1)
        
        # Gráfico para Stochastic
        self.stoch_plot = IndicatorPlot(self, height=120)
        self.stoch_plot.setVisible(False)
        self.stoch_plot.plot.setLabel('left', 'Stochastic')
        self.stoch_plot.plot.setXLink(self.candle_plot)
        self.stoch_plot.set_margins(60, 5, 8, 35)  # Margen ajustado
        self.graphs_layout.addWidget(self.stoch_plot, 1)
        
        # Registrar gráficos
        self.indicator_plots = {
            'rsi': self.rsi_plot,
            'macd': self.macd_plot,
            'stochastic': self.stoch_plot
        }
    
    def create_top_bar(self):
        """Crear barra superior de controles."""
        self.top_bar_widget = QWidget()
        top_layout = QHBoxLayout(self.top_bar_widget)
        top_layout.setContentsMargins(8, 4, 8, 4)
        
        # Selector de símbolo
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["EURUSD", "US500", "GBPUSD", "USDJPY", "XAUUSD"])
        self.symbol_combo.setCurrentText(self.current_symbol)
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        self.symbol_combo.setFixedWidth(120)
        
        # Selector de timeframe
        self.timeframe_combo = QComboBox()
        timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
        self.timeframe_combo.addItems(timeframes)
        self.timeframe_combo.setCurrentText(self.current_timeframe)
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.timeframe_combo.setFixedWidth(80)
        
        # Botón de actualización
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setToolTip("Actualizar gráfico")
        self.btn_refresh.clicked.connect(self.refresh_chart)
        self.btn_refresh.setFixedSize(30, 30)
        
        # Botón de zoom
        self.btn_zoom_fit = QPushButton("🔍 Ajustar")
        self.btn_zoom_fit.clicked.connect(self.auto_scale_chart)
        self.btn_zoom_fit.setFixedWidth(110)
        
        # Botón para alternar visibilidad de etiquetas
        self.btn_toggle_labels = QPushButton("📝 Etiquetas")
        self.btn_toggle_labels.setCheckable(True)
        self.btn_toggle_labels.setChecked(True)
        self.btn_toggle_labels.toggled.connect(self.toggle_date_labels)
        self.btn_toggle_labels.setFixedWidth(120)
        
        # Botón para alternar indicadores
        self.btn_toggle_indicators = QPushButton("📈 Indicadores")
        self.btn_toggle_indicators.setCheckable(True)
        self.btn_toggle_indicators.setChecked(False)
        self.btn_toggle_indicators.toggled.connect(self.toggle_indicators)
        self.btn_toggle_indicators.setFixedWidth(120)
        
        # Información del símbolo
        self.lbl_symbol_info = QLabel("Dígitos: -- | Punto: -- | Spread: --")
        self.lbl_symbol_info.setStyleSheet("color: #aaa; font-size: 11px;")
        self.lbl_symbol_info.setFixedWidth(250)
        
        # Botón para modo tiempo real
        self.btn_real_time = QPushButton("⏸ Tiempo Real")
        self.btn_real_time.setCheckable(True)
        self.btn_real_time.setChecked(True)
        self.btn_real_time.setToolTip("Activar/desactivar datos en tiempo real")
        self.btn_real_time.toggled.connect(self.toggle_real_time)
        self.btn_real_time.setFixedWidth(120)
        
        # Contador de vela actual
        self.lbl_candle_timer = QLabel("Vela: --:--")
        self.lbl_candle_timer.setStyleSheet("color: #ff9900; font-weight: bold; font-size: 12px;")
        self.lbl_candle_timer.setFixedWidth(80)
        
        # Estado de tiempo real
        self.lbl_realtime_status = QLabel("🟢 TIEMPO REAL")
        self.lbl_realtime_status.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 11px;")
        self.lbl_realtime_status.setFixedWidth(100)
        
        # Etiqueta de estado
        self.status_label = QLabel("Cargando datos...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; padding-left: 8px;")
        self.status_label.setFixedWidth(350)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        
        # Agregar widgets
        top_layout.addWidget(QLabel("Símbolo:"))
        top_layout.addWidget(self.symbol_combo)
        top_layout.addWidget(QLabel("TF:"))
        top_layout.addWidget(self.timeframe_combo)
        top_layout.addWidget(self.btn_refresh)
        top_layout.addWidget(separator)
        top_layout.addWidget(self.btn_zoom_fit)
        top_layout.addWidget(self.btn_toggle_labels)
        top_layout.addWidget(self.btn_toggle_indicators)
        top_layout.addWidget(separator)
        top_layout.addWidget(self.lbl_symbol_info)
        top_layout.addWidget(self.btn_real_time)
        top_layout.addWidget(self.lbl_candle_timer)
        top_layout.addWidget(self.lbl_realtime_status)
        top_layout.addStretch()
        top_layout.addWidget(self.status_label)
        
    def create_info_bar(self):
        """Crear barra inferior de información."""
        self.info_bar_widget = QWidget()
        info_layout = QHBoxLayout(self.info_bar_widget)
        info_layout.setContentsMargins(12, 6, 12, 6)
        
        # Información de escala del precio
        price_scale_group = QWidget()
        price_layout = QVBoxLayout(price_scale_group)
        price_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_price_scale = QLabel("Escala: --")
        self.lbl_price_scale.setStyleSheet("color: #ffa500; font-size: 10px;")
        
        self.lbl_min_price_move = QLabel("Mín. movimiento: --")
        self.lbl_min_price_move.setStyleSheet("color: #aaa; font-size: 10px;")
        
        price_layout.addWidget(self.lbl_price_scale)
        price_layout.addWidget(self.lbl_min_price_move)
        
        # Precio BID
        self.bid_label = QLabel("BID: --")
        self.bid_label.setStyleSheet("color: #0af; font-weight: bold; font-size: 13px;")
        self.bid_label.setFixedWidth(120)
        
        # Precio ASK
        self.ask_label = QLabel("ASK: --")
        self.ask_label.setStyleSheet("color: #f0a; font-weight: bold; font-size: 13px;")
        self.ask_label.setFixedWidth(120)
        
        # Spread
        self.spread_label = QLabel("Spread: --")
        self.spread_label.setStyleSheet("color: #fff; font-weight: bold; font-size: 13px;")
        self.spread_label.setFixedWidth(120)
        
        # Cambio
        self.change_label = QLabel("Cambio: --")
        self.change_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self.change_label.setFixedWidth(120)
        
        # Vela actual en tiempo real
        self.current_candle_label = QLabel("Vela actual: --")
        self.current_candle_label.setStyleSheet(
            "color: #ff9900; font-weight: bold; font-size: 11px; "
            "background-color: #222; padding: 2px 4px; border-radius: 3px;"
        )
        self.current_candle_label.setFixedWidth(250)
        
        # Tiempo para siguiente vela
        time_group = QWidget()
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_local_time = QLabel("Local: --:--:--")
        self.lbl_local_time.setStyleSheet("color: #0f0; font-size: 10px;")
        
        self.lbl_next_candle = QLabel("Sig. vela: --:--")
        self.lbl_next_candle.setStyleSheet("color: #ff00ff; font-size: 10px; font-weight: bold;")
        
        time_layout.addWidget(self.lbl_local_time)
        time_layout.addWidget(self.lbl_next_candle)
        time_group.setFixedWidth(120)
        
        # Indicadores activos
        self.active_indicators_label = QLabel("Indicadores: --")
        self.active_indicators_label.setStyleSheet("color: #ff9900; font-size: 11px;")
        self.active_indicators_label.setFixedWidth(150)
        
        # Información de vela en tiempo real
        self.realtime_stats_label = QLabel("Velas RT: 0 | Hist: 0")
        self.realtime_stats_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self.realtime_stats_label.setFixedWidth(120)
        
        # Agregar widgets
        info_layout.addWidget(price_scale_group)
        info_layout.addWidget(self.bid_label)
        info_layout.addWidget(self.ask_label)
        info_layout.addWidget(self.spread_label)
        info_layout.addWidget(self.change_label)
        info_layout.addWidget(self.current_candle_label)
        info_layout.addWidget(self.active_indicators_label)
        info_layout.addWidget(self.realtime_stats_label)
        info_layout.addWidget(time_group)
        info_layout.addStretch()
    
    def toggle_real_time(self, enabled):
        """Activar/desactivar modo tiempo real."""
        self.real_time_active = enabled
        if enabled:
            self.btn_real_time.setText("⏸ Tiempo Real")
            self.lbl_realtime_status.setText("🟢 TIEMPO REAL")
            self.lbl_realtime_status.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 11px;")
            self.status_label.setText("Modo tiempo real ACTIVADO")
            
            # Reiniciar datos de tiempo real
            self.realtime_manager.reset()
            self.realtime_candles = []
            
            # Solicitar datos iniciales
            self.request_initial_data()
        else:
            self.btn_real_time.setText("▶ Tiempo Real")
            self.lbl_realtime_status.setText("🔴 PAUSADO")
            self.lbl_realtime_status.setStyleSheet("color: #ff0000; font-weight: bold; font-size: 11px;")
            self.status_label.setText("Modo tiempo real DESACTIVADO")
    
    def request_initial_data(self):
        """Solicitar datos iniciales."""
        if self.real_time_active:
            # Solicitar datos históricos
            self.request_historical_data.emit(
                self.current_symbol,
                self.current_timeframe,
                100  # Últimas 100 velas
            )
            
            # Solicitar datos en tiempo real
            self.request_real_time_data.emit(
                self.current_symbol,
                self.current_timeframe
            )
    
    def update_real_time_data(self):
        """Actualizar datos en tiempo real."""
        if self.real_time_active:
            # Solicitar datos en tiempo real
            self.request_real_time_data.emit(self.current_symbol, self.current_timeframe)
    
    def update_realtime_candle_display(self):
        """Actualizar display de la vela en tiempo real."""
        if self.real_time_active and self.last_bid is not None:
            # Actualizar gestor de tiempo real
            result = self.realtime_manager.update_price(self.last_bid)
            
            # Actualizar display de la vela actual
            current_candle = self.realtime_manager.get_current_candle_data()
            if current_candle:
                self.update_current_candle_display(current_candle)
                
                # Actualizar estadísticas
                self.update_realtime_stats()
                
                # Redibujar si hay cambios significativos
                if len(self.realtime_manager.completed_candles) > len(self.realtime_candles):
                    self.update_realtime_chart()
    
    def update_realtime_stats(self):
        """Actualizar estadísticas en tiempo real."""
        realtime_count = len(self.realtime_manager.completed_candles)
        historical_count = len(self.historical_candles)
        total_candles = realtime_count + historical_count
        
        self.realtime_stats_label.setText(
            f"Velas RT: {realtime_count} | Hist: {historical_count} | Total: {total_candles}"
        )
    
    def update_realtime_chart(self):
        """Actualizar gráfico con velas en tiempo real."""
        # Obtener todas las velas (históricas + tiempo real)
        all_candles = self.get_all_candles()
        
        if not all_candles:
            return
        
        # Preparar datos
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(all_candles)
        
        # Redibujar velas
        self.draw_candles(times, opens, highs, lows, closes)
        
        # Redibujar indicadores si están activos
        if self.btn_toggle_indicators.isChecked() and self.indicators_config:
            self.apply_indicators_to_chart()
        
        # Actualizar cruz
        if self.last_bid is not None and len(times) > 0:
            self.update_price_cross(self.last_bid)
    
    def get_all_candles(self):
        """Obtener todas las velas (históricas + tiempo real)."""
        all_candles = self.historical_candles.copy()
        
        # Convertir velas de tiempo real a objetos Candle
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
        
        # Agregar vela actual si existe
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
    
    def update_time_displays(self):
        """Actualizar displays de tiempo en tiempo real."""
        current_local = datetime.now()
        
        # Actualizar hora local
        self.lbl_local_time.setText(f"Local: {current_local.strftime('%H:%M:%S')}")
        
        # Calcular tiempo para siguiente vela
        time_remaining = self.realtime_manager.get_time_to_next_candle(current_local)
        
        if time_remaining > 0:
            minutes = int(time_remaining // 60)
            seconds = int(time_remaining % 60)
            self.lbl_candle_timer.setText(f"{minutes}:{seconds:02d}")
            self.lbl_next_candle.setText(f"Sig. vela: {minutes}:{seconds:02d}")
        else:
            self.lbl_candle_timer.setText("0:00")
            self.lbl_next_candle.setText("Sig. vela: 0:00")
    
    def update_current_candle_display(self, candle_data):
        """Actualizar display de la vela actual en tiempo real."""
        if candle_data and candle_data['open'] is not None:
            open_price = candle_data['open']
            high = candle_data['high']
            low = candle_data['low']
            close = candle_data['close']
            
            # Calcular cambio
            change = ((close - open_price) / open_price * 100) if open_price != 0 else 0
            change_text = f"{change:+.2f}%"
            
            # Determinar si es alcista o bajista
            is_bullish = close >= open_price
            
            # Formatear precios según dígitos
            if self.symbol_info:
                digits = self.symbol_info.get('digits', 5)
                open_text = f"{open_price:.{digits}f}"
                close_text = f"{close:.{digits}f}"
                high_text = f"{high:.{digits}f}"
                low_text = f"{low:.{digits}f}"
            else:
                open_text = f"{open_price:.5f}"
                close_text = f"{close:.5f}"
                high_text = f"{high:.5f}"
                low_text = f"{low:.5f}"
            
            # Actualizar label
            self.current_candle_label.setText(
                f"Vela: O:{open_text} H:{high_text} L:{low_text} C:{close_text} ({change_text})"
            )
            
            # Cambiar color según dirección
            if is_bullish:
                self.current_candle_label.setStyleSheet(
                    "color: #00ff00; font-weight: bold; font-size: 11px; "
                    "background-color: #002200; padding: 2px 4px; border-radius: 3px;"
                )
            else:
                self.current_candle_label.setStyleSheet(
                    "color: #ff0000; font-weight: bold; font-size: 11px; "
                    "background-color: #220000; padding: 2px 4px; border-radius: 3px;"
                )
            
            # Guardar datos para referencia
            self.current_candle_display = {
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'change': change,
                'is_bullish': is_bullish
            }
    
    def on_mouse_moved(self, pos):
        """Manejar movimiento del ratón para mostrar precio en posición actual."""
        if not self.candle_plot.sceneBoundingRect().contains(pos):
            return
        
        # Convertir posición del ratón a coordenadas del gráfico
        mouse_point = self.candle_plot.vb.mapSceneToView(pos)
        x_pos = mouse_point.x()
        y_pos = mouse_point.y()
        
        # Encontrar la vela más cercana
        if len(self.x_positions) > 0:
            # Buscar el índice más cercano
            idx = np.argmin(np.abs(np.array(self.x_positions) - x_pos))
            if idx < len(self.x_positions):
                # Mostrar precio en la barra inferior
                if hasattr(self, 'candles_data') and idx < len(self.candles_data):
                    candle = self.candles_data[idx]
                    price = float(candle.close)
                    
                    if self.symbol_info:
                        digits = self.symbol_info.get('digits', 5)
                        price_text = f"{price:.{digits}f}"
                    else:
                        price_text = f"{price:.5f}"
    
    def create_price_cross(self, x_pos, y_pos):
        """Crear una cruz azul sutil en la posición indicada."""
        if self.cross_h_line:
            self.candle_plot.removeItem(self.cross_h_line)
        if self.cross_v_line:
            self.candle_plot.removeItem(self.cross_v_line)
        if self.cross_label:
            self.candle_plot.removeItem(self.cross_label)
        
        cross_length = 0.3
        
        # Crear línea horizontal
        self.cross_h_line = pg.PlotCurveItem(
            x=np.array([x_pos - cross_length, x_pos + cross_length], dtype=np.float64),
            y=np.array([y_pos, y_pos], dtype=np.float64),
            pen=pg.mkPen(color=self.cross_color, width=1.8, style=Qt.SolidLine)
        )
        self.cross_h_line.setZValue(100)
        
        # Crear línea vertical
        self.cross_v_line = pg.PlotCurveItem(
            x=np.array([x_pos, x_pos], dtype=np.float64),
            y=np.array([y_pos - cross_length, y_pos + cross_length], dtype=np.float64),
            pen=pg.mkPen(color=self.cross_color, width=1.8, style=Qt.SolidLine)
        )
        self.cross_v_line.setZValue(100)
        
        # Crear etiqueta con el precio
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
        
        # Agregar elementos
        self.candle_plot.addItem(self.cross_h_line)
        self.candle_plot.addItem(self.cross_v_line)
        self.candle_plot.addItem(self.cross_label)
        
        # Posicionar etiqueta
        label_offset_x = 0.25
        label_offset_y = cross_length + 0.15
        self.cross_label.setPos(x_pos + label_offset_x, y_pos + label_offset_y)
        
        self.current_cross_x = x_pos
        self.current_cross_y = y_pos
    
    def animate_price_cross(self):
        """Animación suave de la cruz del precio."""
        if self.last_bid is not None and len(self.x_positions) > 0:
            # Calcular posición X para la última vela
            last_candle_x = self.x_positions[-1] if self.x_positions else 0
            
            # Si la cruz no existe o la posición ha cambiado, actualizarla
            if (self.current_cross_y is None or 
                abs(self.current_cross_y - self.last_bid) > 0.00001):
                self.update_price_cross(self.last_bid)
    
    def update_price_cross(self, price):
        """Actualizar la cruz azul con el precio actual."""
        if self.x_positions is None or len(self.x_positions) == 0:
            return
        
        last_candle_x = self.x_positions[-1] if self.x_positions else 0
        
        # Si la posición X ha cambiado (nueva vela), actualizar completamente
        if self.current_cross_x is None or abs(self.current_cross_x - last_candle_x) > 0.5:
            self.create_price_cross(last_candle_x, price)
        else:
            # Solo actualizar posición Y (precio)
            self.current_cross_y = price
            
            # Actualizar posición de la cruz
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
            
            # Actualizar etiqueta
            if self.cross_label:
                if self.symbol_info:
                    digits = self.symbol_info.get('digits', 5)
                    price_text = f"{price:.{digits}f}"
                else:
                    price_text = f"{price:.5f}"
                
                self.cross_label.setText(price_text)
                self.cross_label.setPos(last_candle_x + 0.25, price + 0.45)
    
    def toggle_date_labels(self, checked):
        """Alternar visibilidad de las etiquetas de fecha."""
        self.show_date_labels = checked
        
        # Forzar la actualización del eje
        if hasattr(self, 'x_dates') and self.x_dates:
            self.configure_x_axis_with_dates()
        else:
            # Si no hay datos todavía, simplemente establecer los ticks vacíos
            self.date_axis.set_ticks([], [], self.current_timeframe)
        
        # Refrescar el gráfico
        self.candle_plot.update()
    
    def toggle_indicators(self, checked):
        """Alternar visibilidad de los indicadores."""
        if checked and (self.historical_candles or self.realtime_candles) and self.indicators_config:
            self.apply_indicators_to_chart()
        else:
            self.hide_all_indicators()
    
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
            
            # Guardar fecha
            x_dates.append(dt)
            
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
    
    def draw_candles(self, times, opens, highs, lows, closes):
        """Dibujar velas japonesas."""
        if len(times) == 0:
            return
        
        candle_width = 0.5
        self.candle_plot.clear()
        
        # Determinar qué velas son en tiempo real
        realtime_indices = []
        if len(self.realtime_manager.completed_candles) > 0:
            # Las últimas N velas son en tiempo real
            realtime_count = min(len(self.realtime_manager.completed_candles), len(times))
            realtime_indices = list(range(len(times) - realtime_count, len(times)))
        
        for i in range(len(times)):
            is_bullish = closes[i] >= opens[i]
            
            # Determinar color (naranja para tiempo real, verde/rojo para histórico)
            if i in realtime_indices or i == len(times) - 1:
                # Vela en tiempo real (actual o reciente)
                color = self.realtime_candle_color
            else:
                color = self.up_color if is_bullish else self.down_color
            
            # Dibujar mecha
            wick = pg.PlotCurveItem(
                x=np.array([times[i], times[i]], dtype=np.float64),
                y=np.array([lows[i], highs[i]], dtype=np.float64),
                pen=pg.mkPen(color=color, width=1.5)
            )
            self.candle_plot.addItem(wick)
            
            # Dibujar cuerpo
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
                times[i] - candle_width/2,
                body_bottom,
                candle_width,
                body_height
            )
            body.setBrush(pg.mkBrush(color))
            body.setPen(pg.mkPen(color))
            self.candle_plot.addItem(body)
        
        self.configure_x_axis_with_dates()
        
        if self.last_bid is not None and len(times) > 0:
            self.update_price_cross(self.last_bid)
    
    def configure_x_axis_with_dates(self):
        """Configurar eje X para mostrar fechas claramente."""
        if not self.x_positions or not self.x_dates or not self.show_date_labels:
            self.date_axis.set_ticks([], [], self.current_timeframe)
            return
        
        tick_positions = []
        tick_labels = []
        
        n_candles = len(self.x_positions)
        target_labels = 10  # Etiquetas suficientes para buena legibilidad
        
        if n_candles <= target_labels:
            step = 1
            indices = range(0, n_candles)
        else:
            step = max(2, n_candles // (target_labels - 1))
            indices = [0]
            for i in range(step, n_candles - 1, step):
                if len(indices) < target_labels - 1:
                    indices.append(i)
            
            if n_candles > 1:
                indices.append(n_candles - 1)
        
        for idx in indices:
            if idx < len(self.x_positions) and idx < len(self.x_dates):
                dt = self.x_dates[idx]
                label = self.format_date_for_label_clear(dt)
                tick_positions.append(self.x_positions[idx])
                tick_labels.append(label)
        
        # Asegurar que las etiquetas estén bien espaciadas
        filtered_positions = []
        filtered_labels = []
        min_distance = 2.0  # Distancia mínima entre ticks
        
        for i in range(len(tick_positions)):
            if i == 0 or i == len(tick_positions) - 1:
                # Siempre incluir primera y última etiqueta
                filtered_positions.append(tick_positions[i])
                filtered_labels.append(tick_labels[i])
            else:
                # Verificar distancia con el anterior
                if tick_positions[i] - filtered_positions[-1] >= min_distance:
                    filtered_positions.append(tick_positions[i])
                    filtered_labels.append(tick_labels[i])
        
        self.date_axis.set_ticks(filtered_positions, filtered_labels, self.current_timeframe)
        
        if len(self.x_positions) > 0:
            x_min = min(self.x_positions) - 1
            x_max = max(self.x_positions) + 1
            self.candle_plot.setXRange(x_min, x_max)
    
    def format_date_for_label_clear(self, dt):
        """Formatear fecha para mostrar claramente a qué vela pertenece."""
        if isinstance(dt, datetime):
            if self.current_timeframe in ["D1"]:
                # Para diario: mostrar mes-día
                return dt.strftime('%m-%d')
            elif self.current_timeframe in ["H4", "H1"]:
                # Para horarios: mostrar día y hora
                return dt.strftime('%d/%H:%M')
            elif self.current_timeframe in ["M30", "M15"]:
                # Para medias horas: mostrar hora:minuto
                return dt.strftime('%H:%M')
            else:  # M5, M1
                # Para minutos: mostrar hora:minuto
                return dt.strftime('%H:%M')
        else:
            try:
                pd_dt = pd.Timestamp(dt)
                if self.current_timeframe in ["D1"]:
                    return pd_dt.strftime('%m-%d')
                elif self.current_timeframe in ["H4", "H1"]:
                    return pd_dt.strftime('%d/%H:%M')
                elif self.current_timeframe in ["M30", "M15"]:
                    return pd_dt.strftime('%H:%M')
                else:
                    return pd_dt.strftime('%H:%M')
            except:
                return str(dt)
    
    def auto_scale_chart(self):
        """Auto-ajustar el zoom del gráfico."""
        all_candles = self.get_all_candles()
        if not all_candles:
            return
        
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(all_candles)
        
        if len(times) > 0:
            x_margin = max(2.0, len(times) * 0.03)  # Aumentado de 1.0 a 2.0
            
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
                self.bid_label.setText(f"BID: {format_str.format(bid)}")
                self.ask_label.setText(f"ASK: {format_str.format(ask)}")
            else:
                self.bid_label.setText(f"BID: {bid:.5f}")
                self.ask_label.setText(f"ASK: {ask:.5f}")
            
            self.spread_label.setText(f"Spread: {spread:.1f} pips")
            
            if self.last_bid is not None:
                change = ((bid - self.last_bid) / self.last_bid) * 100
                change_text = f"{change:+.2f}%"
                if change >= 0:
                    self.change_label.setText(f"▲ {change_text}")
                    self.change_label.setStyleSheet("color: #00ff00; font-weight: bold;")
                else:
                    self.change_label.setText(f"▼ {change_text}")
                    self.change_label.setStyleSheet("color: #ff0000; font-weight: bold;")
            
            # Actualizar último precio
            self.last_bid = bid
            
            # Si hay datos en tiempo real, actualizar estado
            if self.real_time_active:
                self.status_label.setText(
                    f"{self.current_symbol} {self.current_timeframe} | "
                    f"Tiempo real activo | "
                    f"BID: {bid:.5f} ASK: {ask:.5f}"
                )
    
    @pyqtSlot(dict)
    def update_indicator_settings(self, indicators_config: Dict):
        """Actualizar configuración de indicadores."""
        self.indicators_config = indicators_config
        
        if self.btn_toggle_indicators.isChecked():
            self.apply_indicators_to_chart()
        
        self.update_active_indicators_label()
    
    def update_active_indicators_label(self):
        """Actualizar etiqueta de indicadores activos."""
        if not self.indicators_config:
            self.active_indicators_label.setText("Indicadores: --")
            return
        
        active_indicators = []
        for name, config in self.indicators_config.items():
            if config.get('enabled', False):
                if name == 'sma':
                    active_indicators.append(f"SMA{config.get('period', '')}")
                elif name == 'ema':
                    active_indicators.append(f"EMA{config.get('period', '')}")
                elif name == 'rsi':
                    active_indicators.append(f"RSI{config.get('period', '')}")
                elif name == 'macd':
                    active_indicators.append(f"MACD")
                elif name == 'bollinger':
                    active_indicators.append(f"BB")
                elif name == 'stochastic':
                    active_indicators.append(f"STOCH")
        
        if active_indicators:
            self.active_indicators_label.setText(f"Indicadores: {', '.join(active_indicators)}")
        else:
            self.active_indicators_label.setText("Indicadores: Ninguno")
    
    def apply_indicators_to_chart(self):
        """Aplicar indicadores al gráfico."""
        all_candles = self.get_all_candles()
        if not all_candles or not self.indicators_config:
            return
        
        x_positions, opens, highs, lows, closes, volumes = self.prepare_candle_data(all_candles)
        
        # Calcular y dibujar indicadores
        self.calculate_and_draw_indicators(x_positions, opens, highs, lows, closes)
    
    def hide_all_indicators(self):
        """Ocultar todos los indicadores."""
        # Ocultar gráficos de indicadores
        for plot in self.indicator_plots.values():
            plot.setVisible(False)
        
        # Limpiar indicadores del gráfico principal
        items_to_remove = []
        for item in self.candle_plot.items:
            if hasattr(item, 'name') and item.name in ['sma', 'ema', 'bb_upper', 'bb_middle', 'bb_lower']:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.candle_plot.removeItem(item)
    
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
        
        # Limpiar gráficos de indicadores
        self.clear_indicator_plots()
        
        # 1. SMA (gráfico principal) - MODIFICADO para empezar desde primera vela
        if self.indicators_config.get('sma', {}).get('enabled', False):
            period = self.indicators_config['sma'].get('period', 20)
            color = self.indicators_config['sma'].get('color', '#ffff00')
            self.draw_sma_from_start(x_array, closes_array, period, color)
        
        # 2. EMA (gráfico principal) - MODIFICADO para empezar desde primera vela
        if self.indicators_config.get('ema', {}).get('enabled', False):
            period = self.indicators_config['ema'].get('period', 12)
            color = self.indicators_config['ema'].get('color', '#ff00ff')
            self.draw_ema_from_start(x_array, closes_array, period, color)
        
        # 3. Bollinger Bands (gráfico principal) - MODIFICADO para empezar desde primera vela
        if self.indicators_config.get('bollinger', {}).get('enabled', False):
            period = self.indicators_config['bollinger'].get('period', 20)
            std = self.indicators_config['bollinger'].get('std', 2.0)
            self.draw_bollinger_bands_from_start(x_array, closes_array, period, std)
        
        # 4. RSI - MODIFICADO para empezar desde primera vela
        if self.indicators_config.get('rsi', {}).get('enabled', False):
            period = self.indicators_config['rsi'].get('period', 14)
            overbought = self.indicators_config['rsi'].get('overbought', 80)
            oversold = self.indicators_config['rsi'].get('oversold', 20)
            color = self.indicators_config['rsi'].get('color', '#ffaa00')
            self.draw_rsi_from_start(x_array, closes_array, period, overbought, oversold, color)
        
        # 5. MACD - MODIFICADO para empezar desde primera vela
        if self.indicators_config.get('macd', {}).get('enabled', False):
            fast = self.indicators_config['macd'].get('fast', 12)
            slow = self.indicators_config['macd'].get('slow', 26)
            signal = self.indicators_config['macd'].get('signal', 9)
            self.draw_macd_from_start(x_array, closes_array, fast, slow, signal)
        
        # 6. Stochastic - MODIFICADO para empezar desde primera vela
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
        
        # Calcular SMA progresivamente desde el principio
        for i in range(len(closes)):
            if i < period - 1:
                # Para las primeras velas (menos del período), usar el promedio de lo disponible
                sma[i] = np.mean(closes[:i+1])
            else:
                # Una vez que tenemos el período completo, calcular normalmente
                sma[i] = np.mean(closes[i - period + 1:i + 1])
        
        # Dibujar línea completa desde el principio
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
        
        # Usar la primera vela como EMA inicial
        ema[0] = closes[0]
        
        # Calcular EMA para las siguientes velas
        for i in range(1, len(closes)):
            if np.isnan(ema[i-1]):
                ema[i] = closes[i]
            else:
                ema[i] = (closes[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        # Dibujar línea completa desde el principio
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
        if len(closes) < 2:  # Necesitamos al menos 2 velas para calcular desviación estándar
            return
        
        bb_middle = np.full_like(closes, np.nan)
        bb_upper = np.full_like(closes, np.nan)
        bb_lower = np.full_like(closes, np.nan)
        
        # Calcular Bandas de Bollinger progresivamente
        for i in range(len(closes)):
            if i < period - 1:
                # Para las primeras velas (menos del período), usar lo disponible
                window = closes[:i+1]
                if len(window) >= 2:
                    middle = np.mean(window)
                    std = np.std(window)
                    bb_middle[i] = middle
                    bb_upper[i] = middle + (std * std_multiplier)
                    bb_lower[i] = middle - (std * std_multiplier)
            else:
                # Una vez que tenemos el período completo, calcular normalmente
                window = closes[i - period + 1:i + 1]
                middle = np.mean(window)
                std = np.std(window)
                bb_middle[i] = middle
                bb_upper[i] = middle + (std * std_multiplier)
                bb_lower[i] = middle - (std * std_multiplier)
        
        # Dibujar todas las líneas desde el principio
        valid_mask = ~np.isnan(bb_middle)
        if np.any(valid_mask):
            # Banda superior
            upper_line = pg.PlotCurveItem(
                x=x_data[valid_mask],
                y=bb_upper[valid_mask],
                pen=pg.mkPen(color='#00ffff', width=1.5, style=Qt.DashLine),
                name='bb_upper'
            )
            self.candle_plot.addItem(upper_line)
            self.drawn_indicators['bb_upper'] = upper_line
            
            # Banda media
            middle_line = pg.PlotCurveItem(
                x=x_data[valid_mask],
                y=bb_middle[valid_mask],
                pen=pg.mkPen(color='#ffffff', width=2),
                name='bb_middle'
            )
            self.candle_plot.addItem(middle_line)
            self.drawn_indicators['bb_middle'] = middle_line
            
            # Banda inferior
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
        
        # Calcular RSI desde el principio
        rsi = np.full_like(closes, np.nan)
        
        # Para la primera vela, establecer RSI = 50 (neutral)
        rsi[0] = 50
        
        # Calcular RSI para el resto de las velas
        for i in range(1, len(closes)):
            if i < period:
                # Para las primeras velas (menos del período), usar promedio simple
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
                # Usar el método estándar una vez que tenemos suficientes datos
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
        
        # Mostrar y dibujar RSI
        self.rsi_plot.setVisible(True)
        
        # Agregar líneas horizontales con etiquetas
        self.rsi_plot.add_hline(overbought, color='#ff6666', width=1, label=f"OB ({overbought})")
        self.rsi_plot.add_hline(oversold, color='#66ff66', width=1, label=f"OS ({oversold})")
        self.rsi_plot.add_hline(50, color='#666666', width=0.5, style=Qt.DashLine, label="50")
        
        # Dibujar línea RSI con etiqueta desde el principio
        valid_mask = ~np.isnan(rsi)
        if np.any(valid_mask):
            self.rsi_plot.plot_indicator(x_data[valid_mask], rsi[valid_mask], color, f'RSI({period})', width=2)
        
        # Ajustar rango Y
        self.rsi_plot.set_y_range(0, 100)
    
    def draw_macd_from_start(self, x_data, closes, fast_period, slow_period, signal_period):
        """Dibujar MACD desde la primera vela."""
        if len(closes) < 2:
            return
        
        # Calcular EMA rápida desde el principio
        ema_fast = self.calculate_ema_from_start(closes, fast_period)
        
        # Calcular EMA lenta desde el principio
        ema_slow = self.calculate_ema_from_start(closes, slow_period)
        
        # Línea MACD = EMA rápida - EMA lenta
        macd_line = np.full_like(closes, np.nan)
        for i in range(len(closes)):
            if not np.isnan(ema_fast[i]) and not np.isnan(ema_slow[i]):
                macd_line[i] = ema_fast[i] - ema_slow[i]
        
        # Línea de señal = EMA de la línea MACD desde el principio
        signal_line = self.calculate_ema_from_start(macd_line, signal_period)
        
        # Histograma = MACD - Signal
        histogram = np.full_like(closes, np.nan)
        for i in range(len(closes)):
            if not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]):
                histogram[i] = macd_line[i] - signal_line[i]
        
        # Mostrar y dibujar MACD
        self.macd_plot.setVisible(True)
        
        # Agregar línea horizontal en 0
        self.macd_plot.add_hline(0, color='#666666', width=0.5, style=Qt.DashLine, label="0")
        
        # Dibujar histograma desde el principio
        valid_hist = ~np.isnan(histogram)
        if np.any(valid_hist):
            self.macd_plot.plot_histogram(x_data[valid_hist], histogram[valid_hist])
        
        # Dibujar líneas MACD y Signal desde el principio
        valid_mask = ~np.isnan(macd_line) & ~np.isnan(signal_line)
        if np.any(valid_mask):
            # Línea MACD (azul)
            self.macd_plot.plot_indicator(
                x_data[valid_mask], 
                macd_line[valid_mask], 
                '#00aaff',  # Azul claro
                f'MACD({fast_period},{slow_period})', 
                width=2
            )
            
            # Línea de señal (naranja)
            self.macd_plot.plot_indicator(
                x_data[valid_mask], 
                signal_line[valid_mask], 
                '#ffaa00',  # Naranja
                f'Signal({signal_period})', 
                width=2
            )
        
        # Ajustar rango Y dinámicamente
        if np.any(valid_mask):
            # Calcular rangos
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
        
        # Usar la primera vela como EMA inicial
        ema[0] = data[0]
        
        # Calcular EMA para el resto de las velas
        multiplier = 2.0 / (period + 1.0)
        
        for i in range(1, len(data)):
            if not np.isnan(ema[i - 1]) and not np.isnan(data[i]):
                ema[i] = (data[i] * multiplier) + (ema[i - 1] * (1 - multiplier))
            elif np.isnan(ema[i - 1]) and not np.isnan(data[i]):
                # Si el EMA anterior es NaN pero el dato actual es válido,
                # usar el dato actual como EMA
                ema[i] = data[i]
        
        return ema
    
    def draw_stochastic_from_start(self, x_data, highs, lows, closes, k_period, d_period, slowing):
        """Dibujar Oscilador Estocástico desde la primera vela."""
        if len(closes) < 2:
            return
        
        # Calcular %K desde el principio
        k_line = np.full_like(closes, np.nan)
        
        for i in range(len(closes)):
            if i < k_period - 1:
                # Para las primeras velas (menos del período), usar lo disponible
                high_window = highs[:i+1]
                low_window = lows[:i+1]
                current_close = closes[i]
                
                if len(high_window) >= 2 and len(low_window) >= 2:
                    highest_high = np.max(high_window)
                    lowest_low = np.min(low_window)
                    
                    if highest_high != lowest_low:
                        k_line[i] = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
                    else:
                        k_line[i] = 50  # Valor neutral cuando no hay variación
            else:
                # Una vez que tenemos el período completo, calcular normalmente
                high_window = highs[i - k_period + 1:i + 1]
                low_window = lows[i - k_period + 1:i + 1]
                current_close = closes[i]
                
                highest_high = np.max(high_window)
                lowest_low = np.min(low_window)
                
                if highest_high != lowest_low:
                    k_line[i] = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
                else:
                    k_line[i] = 50  # Valor neutral cuando no hay variación
        
        # Suavizar %K si slowing > 1
        if slowing > 1:
            k_line_smoothed = np.full_like(k_line, np.nan)
            for i in range(len(k_line)):
                if i < slowing - 1:
                    # Para las primeras velas, usar lo disponible
                    window = k_line[:i+1]
                    if np.any(~np.isnan(window)):
                        k_line_smoothed[i] = np.nanmean(window)
                else:
                    window = k_line[i - slowing + 1:i + 1]
                    if np.any(~np.isnan(window)):
                        k_line_smoothed[i] = np.nanmean(window)
            k_line = k_line_smoothed
        
        # Calcular %D (media móvil de %K) desde el principio
        d_line = np.full_like(closes, np.nan)
        
        for i in range(len(k_line)):
            if i < d_period - 1:
                # Para las primeras velas, usar lo disponible
                window = k_line[:i+1]
                if np.any(~np.isnan(window)):
                    d_line[i] = np.nanmean(window)
            else:
                window = k_line[i - d_period + 1:i + 1]
                if np.any(~np.isnan(window)):
                    d_line[i] = np.nanmean(window)
        
        # Mostrar y dibujar Stochastic
        self.stoch_plot.setVisible(True)
        
        # Agregar líneas horizontales con etiquetas claras
        self.stoch_plot.add_hline(80, color='#ff6666', width=1, label="Overbought (80)")
        self.stoch_plot.add_hline(20, color='#66ff66', width=1, label="Oversold (20)")
        self.stoch_plot.add_hline(50, color='#666666', width=0.5, style=Qt.DashLine, label="Mid (50)")
        
        # Dibujar líneas %K y %D desde el principio
        valid_mask = ~np.isnan(k_line) & ~np.isnan(d_line)
        if np.any(valid_mask):
            # %K (línea continua cian)
            self.stoch_plot.plot_indicator(
                x_data[valid_mask], 
                k_line[valid_mask], 
                '#00ffff',  # Cian brillante
                f'%K({k_period},{slowing})', 
                width=2,
                style=Qt.SolidLine
            )
            
            # %D (línea discontinua amarilla)
            self.stoch_plot.plot_indicator(
                x_data[valid_mask], 
                d_line[valid_mask], 
                '#ffff00',  # Amarillo brillante
                f'%D({d_period})', 
                width=2,
                style=Qt.DashLine
            )
        
        # Ajustar rango Y
        self.stoch_plot.set_y_range(0, 100)
    
    def update_chart(self, data, indicator_configs=None):
        """Actualizar el gráfico con nuevos datos históricos."""
        if not data:
            self.status_label.setText("Sin datos disponibles")
            return
        
        # Guardar datos históricos
        self.historical_candles = data
        
        if indicator_configs is not None:
            self.indicators_config = indicator_configs
        
        # Limpiar gráfico anterior
        self.candle_plot.clear()
        
        # Obtener todas las velas (históricas + tiempo real)
        all_candles = self.get_all_candles()
        
        if not all_candles:
            return
        
        # Preparar datos
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(all_candles)
        
        # Dibujar velas
        self.draw_candles(times, opens, highs, lows, closes)
        
        # Configurar escala
        self.configure_price_axis()
        
        # Auto-ajustar zoom
        self.auto_scale_chart()
        
        # Aplicar indicadores si están activados
        if self.btn_toggle_indicators.isChecked() and self.indicators_config:
            self.apply_indicators_to_chart()
        
        # Actualizar estado
        if data:
            last_candle = data[-1]
            if hasattr(last_candle, 'timestamp'):
                last_time = last_candle.timestamp
            elif hasattr(last_candle, 'time'):
                last_time = last_candle.time
            else:
                last_time = datetime.now()
            
            self.status_label.setText(
                f"{self.current_symbol} {self.current_timeframe} | "
                f"Velas históricas: {len(data)} | "
                f"Última: {last_time.strftime('%H:%M:%S')}"
            )
    
    def update_symbol_info_display(self):
        """Actualizar display de información del símbolo."""
        if not self.symbol_info:
            return
        
        digits = self.symbol_info.get('digits', 5)
        point = self.symbol_info.get('point', 0.00001)
        spread = self.symbol_info.get('spread', 0)
        
        self.lbl_symbol_info.setText(f"Dígitos: {digits} | Punto: {point:.6f} | Spread: {spread}")
        
        if digits == 5:
            price_scale = "0.00001"
            min_move = "0.1 pip"
        elif digits == 4:
            price_scale = "0.0001"
            min_move = "1 pip"
        elif digits == 3:
            price_scale = "0.001"
            min_move = "10 pips"
        elif digits == 2:
            price_scale = "0.01"
            min_move = "100 pips"
        else:
            price_scale = f"10^{-(digits)}"
            min_move = f"{10**(5-digits)} pips"
        
        self.lbl_price_scale.setText(f"Escala: {price_scale}")
        self.lbl_min_price_move.setText(f"Mín. movimiento: {min_move}")
    
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
        
        # Si está activo el tiempo real, solicitar datos iniciales
        if self.real_time_active:
            self.request_initial_data()
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.symbol_changed.emit(symbol)
        
        # Reiniciar gestor de tiempo real
        self.realtime_manager.reset()
        self.realtime_candles = []
        
        # Actualizar timeframe en el gestor
        self.realtime_manager.update_timeframe(self.current_timeframe)
        
        # Solicitar datos en tiempo real para nuevo símbolo
        if self.real_time_active:
            self.request_initial_data()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.current_timeframe = timeframe
        self.timeframe_changed.emit(timeframe)
        
        # Actualizar timeframe en el gestor
        self.realtime_manager.update_timeframe(timeframe)
        self.realtime_candles = []
        
        # Solicitar datos en tiempo real para nuevo timeframe
        if self.real_time_active:
            self.request_initial_data()
    
    def clear_all(self):
        """Limpiar todos los datos del gráfico."""
        self.historical_candles = []
        self.realtime_candles = []
        self.realtime_manager.reset()
        self.candle_plot.clear()
        self.clear_indicator_plots()
        
        self.status_label.setText("Gráfico limpiado")
    
    def set_realtime_active(self, active: bool):
        """Establecer estado de tiempo real."""
        self.real_time_active = active
        self.btn_real_time.setChecked(active)
        self.toggle_real_time(active)