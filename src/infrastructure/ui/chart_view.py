# src/infrastructure/ui/chart_view.py
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPen
import pyqtgraph as pg
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Optional, Dict, Any

# Configurar pyqtgraph para mejor rendimiento
pg.setConfigOptions(antialias=True)


class DateAxis(pg.AxisItem):
    """Eje personalizado para mostrar fechas con formato completo."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)
        self.tick_positions = []
        self.tick_labels = []
        self.timeframe = "H1"
        
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


class ChartView(QWidget):
    """Widget para gráficos de trading con velas japonesas y indicadores."""
    
    # Señales
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración inicial
        self.current_symbol = "US500"
        self.current_timeframe = "H1"
        self.candles_data = []
        self.symbol_info = {}
        self.server_time = None
        self.x_positions = []
        self.x_dates = []
        
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
        
        self.setMinimumSize(1000, 700)
        
        # Inicializar UI
        self.init_ui()
        self.init_chart()
        
        # Timer para actualizar hora del servidor
        self.server_time_timer = QTimer()
        self.server_time_timer.timeout.connect(self.update_server_time_display)
        self.server_time_timer.start(1000)
        
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
        
        # Ajustar márgenes
        self.candle_plot.layout.setContentsMargins(40, 5, 8, 40)
        
        # Control de visibilidad de etiquetas
        self.show_date_labels = True
        
        # Configurar fuente
        font = QFont('Arial', 8)
        self.date_axis.setTickFont(font)
        
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
        self.graphs_layout.addWidget(self.rsi_plot, 1)
        
        # Gráfico para MACD
        self.macd_plot = IndicatorPlot(self, height=120)
        self.macd_plot.setVisible(False)
        self.macd_plot.plot.setLabel('left', 'MACD')
        self.macd_plot.plot.setXLink(self.candle_plot)
        self.graphs_layout.addWidget(self.macd_plot, 1)
        
        # Gráfico para Stochastic
        self.stoch_plot = IndicatorPlot(self, height=120)
        self.stoch_plot.setVisible(False)
        self.stoch_plot.plot.setLabel('left', 'Stochastic')
        self.stoch_plot.plot.setXLink(self.candle_plot)
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
        
        # Hora del servidor
        self.lbl_server_time = QLabel("Servidor: --:--:--")
        self.lbl_server_time.setStyleSheet("color: #0af; font-size: 11px; font-weight: bold;")
        self.lbl_server_time.setFixedWidth(140)
        
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
        top_layout.addWidget(self.lbl_server_time)
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
        
        # Indicador de precio actual
        self.price_indicator_label = QLabel("Precio actual: --")
        self.price_indicator_label.setStyleSheet("color: #0af; font-weight: bold; font-size: 11px;")
        self.price_indicator_label.setFixedWidth(150)
        
        # Tiempo local vs servidor
        time_group = QWidget()
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_local_time = QLabel("Local: --:--:--")
        self.lbl_local_time.setStyleSheet("color: #0f0; font-size: 10px;")
        
        self.lbl_time_diff = QLabel("Diff: --")
        self.lbl_time_diff.setStyleSheet("color: #aaa; font-size: 10px;")
        
        time_layout.addWidget(self.lbl_local_time)
        time_layout.addWidget(self.lbl_time_diff)
        time_group.setFixedWidth(100)
        
        # Indicadores activos
        self.active_indicators_label = QLabel("Indicadores: --")
        self.active_indicators_label.setStyleSheet("color: #ff9900; font-size: 11px;")
        self.active_indicators_label.setFixedWidth(150)
        
        # Agregar widgets
        info_layout.addWidget(price_scale_group)
        info_layout.addWidget(self.bid_label)
        info_layout.addWidget(self.ask_label)
        info_layout.addWidget(self.spread_label)
        info_layout.addWidget(self.change_label)
        info_layout.addWidget(self.price_indicator_label)
        info_layout.addWidget(self.active_indicators_label)
        info_layout.addWidget(time_group)
        info_layout.addStretch()
    
    def on_mouse_moved(self, pos):
        """Manejar movimiento del ratón para mostrar precio en posición actual."""
        if not self.candle_plot.sceneBoundingRect().contains(pos):
            return
        
        # Convertir posición del ratón a coordenadas del gráfico
        mouse_point = self.candle_plot.vb.mapSceneToView(pos)
        x_pos = mouse_point.x()
        
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
                    
                    self.price_indicator_label.setText(f"Posición: {price_text}")
    
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
    
    def update_price_cross(self, price):
        """Actualizar la cruz azul con el precio actual."""
        if self.x_positions is None or len(self.x_positions) == 0:
            return
        
        last_candle_x = self.x_positions[-1] if self.x_positions else 0
        self.create_price_cross(last_candle_x, price)
        
        if self.symbol_info:
            digits = self.symbol_info.get('digits', 5)
            price_text = f"{price:.{digits}f}"
        else:
            price_text = f"{price:.5f}"
        
        self.price_indicator_label.setText(f"Precio actual: {price_text}")
        self.price_indicator_label.setStyleSheet("color: #0af; font-weight: bold; font-size: 11px;")
    
    def toggle_date_labels(self, checked):
        """Alternar visibilidad de las etiquetas de fecha."""
        self.show_date_labels = checked
        if hasattr(self, 'candles_data') and self.candles_data:
            self.refresh_chart()
    
    def toggle_indicators(self, checked):
        """Alternar visibilidad de los indicadores."""
        if checked and self.candles_data and self.indicators_config:
            self.apply_indicators_to_chart()
        else:
            self.hide_all_indicators()
    
    def prepare_candle_data(self, candles):
        """Preparar datos de velas eliminando gaps."""
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
        
        for i in range(len(times)):
            is_bullish = closes[i] >= opens[i]
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
        """Configurar eje X para mostrar fechas."""
        if not self.x_positions or not self.x_dates or not self.show_date_labels:
            return
        
        tick_positions = []
        tick_labels = []
        
        n_candles = len(self.x_positions)
        target_labels = 20
        
        if n_candles <= target_labels:
            step = 1
            indices = range(0, n_candles)
        else:
            step = max(1, n_candles // (target_labels - 1))
            indices = [0]
            for i in range(step, n_candles - 1, step):
                if len(indices) < target_labels - 1:
                    indices.append(i)
            
            if n_candles > 1:
                indices.append(n_candles - 1)
        
        for idx in indices:
            if idx < len(self.x_positions) and idx < len(self.x_dates):
                dt = self.x_dates[idx]
                label = self.format_date_for_label(dt)
                tick_positions.append(self.x_positions[idx])
                tick_labels.append(label)
        
        # Si tenemos menos de 20 etiquetas, agregar más
        if len(tick_positions) < target_labels and n_candles > 1:
            additional_needed = target_labels - len(tick_positions)
            additional_step = max(1, (n_candles - 2) // (additional_needed + 1))
            
            for i in range(1, n_candles - 1, additional_step):
                if len(tick_positions) >= target_labels:
                    break
                    
                if i not in indices:
                    dt = self.x_dates[i]
                    label = self.format_date_for_label(dt)
                    tick_positions.append(self.x_positions[i])
                    tick_labels.append(label)
        
        sorted_indices = np.argsort(tick_positions)
        tick_positions = [tick_positions[i] for i in sorted_indices]
        tick_labels = [tick_labels[i] for i in sorted_indices]
        
        self.date_axis.set_ticks(tick_positions, tick_labels, self.current_timeframe)
        
        if len(self.x_positions) > 0:
            x_min = min(self.x_positions) - 1
            x_max = max(self.x_positions) + 1
            self.candle_plot.setXRange(x_min, x_max)
    
    def format_date_for_label(self, dt):
        """Formatear fecha para la etiqueta del eje X."""
        if isinstance(dt, datetime):
            return dt.strftime('%Y/%m/%d %H:%M:%S')
        else:
            try:
                pd_dt = pd.Timestamp(dt)
                return pd_dt.strftime('%Y/%m/%d %H:%M:%S')
            except:
                return str(dt)
    
    def auto_scale_chart(self):
        """Auto-ajustar el zoom del gráfico."""
        if not self.candles_data:
            return
        
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(self.candles_data)
        
        if len(times) > 0:
            x_margin = max(1.0, len(times) * 0.02)
            
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
            
            self.update_price_cross(bid)
            self.last_bid = bid
    
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
        if not self.candles_data or not self.indicators_config:
            return
        
        x_positions, opens, highs, lows, closes, volumes = self.prepare_candle_data(self.candles_data)
        
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
        
        # 1. SMA (gráfico principal)
        if self.indicators_config.get('sma', {}).get('enabled', False):
            period = self.indicators_config['sma'].get('period', 20)
            color = self.indicators_config['sma'].get('color', '#ffff00')
            self.draw_sma(x_array, closes_array, period, color)
        
        # 2. EMA (gráfico principal)
        if self.indicators_config.get('ema', {}).get('enabled', False):
            period = self.indicators_config['ema'].get('period', 12)
            color = self.indicators_config['ema'].get('color', '#ff00ff')
            self.draw_ema(x_array, closes_array, period, color)
        
        # 3. Bollinger Bands (gráfico principal)
        if self.indicators_config.get('bollinger', {}).get('enabled', False):
            period = self.indicators_config['bollinger'].get('period', 20)
            std = self.indicators_config['bollinger'].get('std', 2.0)
            self.draw_bollinger_bands(x_array, closes_array, period, std)
        
        # 4. RSI
        if self.indicators_config.get('rsi', {}).get('enabled', False):
            period = self.indicators_config['rsi'].get('period', 14)
            overbought = self.indicators_config['rsi'].get('overbought', 80)
            oversold = self.indicators_config['rsi'].get('oversold', 20)
            color = self.indicators_config['rsi'].get('color', '#ffaa00')
            self.draw_rsi(x_array, closes_array, period, overbought, oversold, color)
        
        # 5. MACD
        if self.indicators_config.get('macd', {}).get('enabled', False):
            fast = self.indicators_config['macd'].get('fast', 12)
            slow = self.indicators_config['macd'].get('slow', 26)
            signal = self.indicators_config['macd'].get('signal', 9)
            self.draw_macd_corrected(x_array, closes_array, fast, slow, signal)
        
        # 6. Stochastic
        if self.indicators_config.get('stochastic', {}).get('enabled', False):
            k_period = self.indicators_config['stochastic'].get('k_period', 14)
            d_period = self.indicators_config['stochastic'].get('d_period', 3)
            slowing = self.indicators_config['stochastic'].get('slowing', 3)
            self.draw_stochastic_with_labels(x_array, highs_array, lows_array, closes_array, 
                                           k_period, d_period, slowing)
    
    def draw_sma(self, x_data, closes, period, color):
        """Dibujar Media Móvil Simple."""
        if len(closes) < period:
            return
        
        sma = np.full_like(closes, np.nan)
        for i in range(period - 1, len(closes)):
            sma[i] = np.mean(closes[i - period + 1:i + 1])
        
        valid_mask = ~np.isnan(sma)
        if np.any(valid_mask):
            sma_line = pg.PlotCurveItem(
                x=x_data[valid_mask],
                y=sma[valid_mask],
                pen=pg.mkPen(color=color, width=2),
                name='sma'
            )
            self.candle_plot.addItem(sma_line)
            self.drawn_indicators['sma'] = sma_line
    
    def draw_ema(self, x_data, closes, period, color):
        """Dibujar Media Móvil Exponencial."""
        if len(closes) < period:
            return
        
        ema = np.full_like(closes, np.nan)
        multiplier = 2 / (period + 1)
        
        sma = np.mean(closes[:period])
        ema[period - 1] = sma
        
        for i in range(period, len(closes)):
            ema[i] = (closes[i] - ema[i - 1]) * multiplier + ema[i - 1]
        
        valid_mask = ~np.isnan(ema)
        if np.any(valid_mask):
            ema_line = pg.PlotCurveItem(
                x=x_data[valid_mask],
                y=ema[valid_mask],
                pen=pg.mkPen(color=color, width=2),
                name='ema'
            )
            self.candle_plot.addItem(ema_line)
            self.drawn_indicators['ema'] = ema_line
    
    def draw_bollinger_bands(self, x_data, closes, period, std_multiplier):
        """Dibujar Bandas de Bollinger."""
        if len(closes) < period:
            return
        
        bb_middle = np.full_like(closes, np.nan)
        bb_upper = np.full_like(closes, np.nan)
        bb_lower = np.full_like(closes, np.nan)
        
        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1:i + 1]
            middle = np.mean(window)
            std = np.std(window)
            
            bb_middle[i] = middle
            bb_upper[i] = middle + (std * std_multiplier)
            bb_lower[i] = middle - (std * std_multiplier)
        
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
    
    def draw_rsi(self, x_data, closes, period, overbought, oversold, color):
        """Dibujar RSI en gráfico separado."""
        if len(closes) < period + 1:
            return
        
        # Calcular RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.zeros_like(closes)
        avg_loss = np.zeros_like(closes)
        rsi = np.full_like(closes, np.nan)
        
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        if avg_loss[period] == 0:
            rsi[period] = 100
        else:
            rs = avg_gain[period] / avg_loss[period]
            rsi[period] = 100 - (100 / (1 + rs))
        
        for i in range(period + 1, len(closes)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
            
            if avg_loss[i] == 0:
                rsi[i] = 100
            else:
                rs = avg_gain[i] / avg_loss[i]
                rsi[i] = 100 - (100 / (1 + rs))
        
        # Mostrar y dibujar RSI
        self.rsi_plot.setVisible(True)
        
        # Agregar líneas horizontales con etiquetas
        self.rsi_plot.add_hline(overbought, color='#ff6666', width=1, label=f"OB ({overbought})")
        self.rsi_plot.add_hline(oversold, color='#66ff66', width=1, label=f"OS ({oversold})")
        self.rsi_plot.add_hline(50, color='#666666', width=0.5, style=Qt.DashLine, label="50")
        
        # Dibujar línea RSI con etiqueta
        self.rsi_plot.plot_indicator(x_data, rsi, color, f'RSI({period})', width=2)
        
        # Ajustar rango Y
        self.rsi_plot.set_y_range(0, 100)
    
    def draw_macd_corrected(self, x_data, closes, fast_period, slow_period, signal_period):
        """Dibujar MACD CORREGIDO - implementación correcta."""
        min_required = max(fast_period, slow_period, signal_period)
        if len(closes) < min_required:
            return
        
        # Calcular EMA rápida
        ema_fast = self.calculate_ema_corrected(closes, fast_period)
        
        # Calcular EMA lenta
        ema_slow = self.calculate_ema_corrected(closes, slow_period)
        
        # Línea MACD = EMA rápida - EMA lenta
        macd_line = np.full_like(closes, np.nan)
        for i in range(len(closes)):
            if not np.isnan(ema_fast[i]) and not np.isnan(ema_slow[i]):
                macd_line[i] = ema_fast[i] - ema_slow[i]
        
        # Línea de señal = EMA de la línea MACD
        signal_line = self.calculate_ema_corrected(macd_line, signal_period)
        
        # Histograma = MACD - Signal
        histogram = np.full_like(closes, np.nan)
        for i in range(len(closes)):
            if not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]):
                histogram[i] = macd_line[i] - signal_line[i]
        
        # Mostrar y dibujar MACD
        self.macd_plot.setVisible(True)
        
        # Agregar línea horizontal en 0
        self.macd_plot.add_hline(0, color='#666666', width=0.5, style=Qt.DashLine, label="0")
        
        # Dibujar histograma PRIMERO (está en el fondo)
        valid_hist = ~np.isnan(histogram)
        if np.any(valid_hist):
            self.macd_plot.plot_histogram(x_data[valid_hist], histogram[valid_hist])
        
        # Dibujar líneas MACD y Signal (encima del histograma)
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
    
    def calculate_ema_corrected(self, data, period):
        """Calcular EMA de manera robusta."""
        if len(data) < period:
            return np.full_like(data, np.nan)
        
        ema = np.full_like(data, np.nan)
        
        # Calcular SMA inicial
        sma = np.nanmean(data[:period])
        if not np.isnan(sma):
            ema[period - 1] = sma
        
        # Multiplicador
        multiplier = 2.0 / (period + 1.0)
        
        # Calcular EMA para valores posteriores
        for i in range(period, len(data)):
            if not np.isnan(ema[i - 1]) and not np.isnan(data[i]):
                ema[i] = (data[i] * multiplier) + (ema[i - 1] * (1 - multiplier))
            elif np.isnan(ema[i - 1]) and not np.isnan(data[i]):
                # Si el EMA anterior es NaN pero el dato actual es válido,
                # usar el dato actual como EMA
                ema[i] = data[i]
        
        return ema
    
    def draw_stochastic_with_labels(self, x_data, highs, lows, closes, k_period, d_period, slowing):
        """Dibujar Oscilador Estocástico CON IDENTIFICADORES."""
        min_required = k_period + max(d_period, slowing)
        if len(closes) < min_required:
            return
        
        # Calcular %K
        k_line = np.full_like(closes, np.nan)
        for i in range(k_period - 1, len(closes)):
            high_window = highs[i - k_period + 1:i + 1]
            low_window = lows[i - k_period + 1:i + 1]
            current_close = closes[i]
            
            highest_high = np.max(high_window)
            lowest_low = np.min(low_window)
            
            if highest_high != lowest_low:
                k_line[i] = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        
        # Suavizar %K si slowing > 1
        if slowing > 1:
            k_line_smoothed = np.full_like(k_line, np.nan)
            for i in range(k_period + slowing - 2, len(k_line)):
                window = k_line[i - slowing + 1:i + 1]
                if np.any(~np.isnan(window)):
                    k_line_smoothed[i] = np.nanmean(window)
            k_line = k_line_smoothed
        
        # Calcular %D (media móvil de %K)
        d_line = np.full_like(closes, np.nan)
        for i in range(k_period + d_period - 2, len(k_line)):
            window = k_line[i - d_period + 1:i + 1]
            if np.any(~np.isnan(window)):
                d_line[i] = np.nanmean(window)
        
        # Mostrar y dibujar Stochastic
        self.stoch_plot.setVisible(True)
        
        # Agregar líneas horizontales con etiquetas claras
        self.stoch_plot.add_hline(80, color='#ff6666', width=1, label="Overbought (80)")
        self.stoch_plot.add_hline(20, color='#66ff66', width=1, label="Oversold (20)")
        self.stoch_plot.add_hline(50, color='#666666', width=0.5, style=Qt.DashLine, label="Mid (50)")
        
        # Dibujar líneas %K y %D con identificadores
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
        """Actualizar el gráfico con nuevos datos."""
        if not data:
            self.status_label.setText("Sin datos disponibles")
            return
        
        self.candles_data = data
        
        if indicator_configs is not None:
            self.indicators_config = indicator_configs
        
        # Limpiar gráfico anterior
        self.candle_plot.clear()
        
        # Preparar datos
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(data)
        
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
                f"Velas: {len(data)} | "
                f"Última: {last_time.strftime('%Y/%m/%d %H:%M:%S')}"
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
    
    def update_server_time_display(self):
        """Actualizar display de hora del servidor."""
        current_local = datetime.now()
        self.lbl_local_time.setText(f"Local: {current_local.strftime('%H:%M:%S')}")
        
        if self.server_time:
            if isinstance(self.server_time, datetime):
                server_dt = self.server_time
            else:
                try:
                    server_dt = pd.Timestamp(self.server_time).to_pydatetime()
                except:
                    server_dt = current_local
            
            self.lbl_server_time.setText(f"Servidor: {server_dt.strftime('%H:%M:%S')}")
            
            time_diff = (server_dt - current_local).total_seconds()
            if abs(time_diff) < 1:
                diff_text = "Sinc"
                color = "#0f0"
            elif time_diff > 0:
                diff_text = f"+{time_diff:.1f}s"
                color = "#0af"
            else:
                diff_text = f"{time_diff:.1f}s"
                color = "#f00"
            
            self.lbl_time_diff.setText(f"Diff: {diff_text}")
            self.lbl_time_diff.setStyleSheet(f"color: {color}; font-size: 10px;")
            self.server_time = server_dt + timedelta(seconds=1)
        else:
            self.lbl_server_time.setText("Servidor: --:--")
            self.lbl_time_diff.setText("Diff: --")
    
    def refresh_chart(self):
        """Refrescar el gráfico manualmente."""
        self.symbol_changed.emit(self.current_symbol)
        self.timeframe_changed.emit(self.current_timeframe)
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.symbol_changed.emit(symbol)
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.current_timeframe = timeframe
        self.timeframe_changed.emit(timeframe)