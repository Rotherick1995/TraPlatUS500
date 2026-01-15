# src/infrastructure/ui/chart_view.py
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame, QToolButton, QMenu)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush
import pyqtgraph as pg
from datetime import datetime, timedelta
import pandas as pd
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# Configurar pyqtgraph
pg.setConfigOptions(antialias=True, background='k', foreground='w', useOpenGL=True)


class ChartView(QWidget):
    """Widget avanzado para gráficos de trading con velas japonesas."""
    
    # Señales
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    chart_clicked = pyqtSignal(dict)  # {x, y, price, time}
    indicator_added = pyqtSignal(str, dict)  # nombre, parámetros
    indicator_removed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración inicial
        self.current_symbol = "EURUSD"
        self.current_timeframe = "1H"
        self.candles_data = []
        self.real_time_prices = deque(maxlen=100)  # Buffer para precios en tiempo real
        
        # Indicadores activos
        self.active_indicators = {
            'SMA': {'period': 20, 'color': '#FFD700', 'enabled': False},
            'EMA': {'period': 12, 'color': '#00FFFF', 'enabled': False},
            'RSI': {'period': 14, 'color': '#FF00FF', 'enabled': False},
            'MACD': {'fast': 12, 'slow': 26, 'signal': 9, 'enabled': False},
            'Bollinger': {'period': 20, 'std': 2, 'color': '#888888', 'enabled': False}
        }
        
        # Objetos gráficos
        self.candle_items = []
        self.indicator_items = []
        
        # Inicializar UI
        self.init_ui()
        self.init_chart()
        self.init_toolbar()
        
        # Timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.auto_update_chart)
        self.update_timer.start(1000)  # Actualizar cada segundo
        
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.blink_current_price)
        self.blink_timer.start(500)
        
        # Estado
        self.is_blinking = False
        self.last_price = None
        self.price_change = 0
        
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        self.setMinimumSize(800, 500)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        
        # 1. Barra superior de controles
        self.create_top_bar()
        main_layout.addWidget(self.top_bar_widget)
        
        # 2. Widget de gráfico
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.graph_widget.setBackground('#0a0a0a')
        main_layout.addWidget(self.graph_widget, 1)
        
        # 3. Barra inferior de precios
        self.create_price_bar()
        main_layout.addWidget(self.price_bar_widget)
        
    def create_top_bar(self):
        """Crear barra superior de controles."""
        self.top_bar_widget = QWidget()
        top_layout = QHBoxLayout(self.top_bar_widget)
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        # Selector de símbolo
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["EURUSD", "US500", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD", "ETHUSD"])
        self.symbol_combo.setCurrentText(self.current_symbol)
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        self.symbol_combo.setFixedWidth(100)
        self.symbol_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 3px;
            }
            QComboBox:hover {
                border: 1px solid #555;
            }
        """)
        
        # Selector de timeframe
        self.timeframe_combo = QComboBox()
        timeframes = ["1m", "5m", "15m", "30m", "1H", "4H", "1D", "1W"]
        self.timeframe_combo.addItems(timeframes)
        self.timeframe_combo.setCurrentText(self.current_timeframe)
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.timeframe_combo.setFixedWidth(70)
        self.timeframe_combo.setStyleSheet(self.symbol_combo.styleSheet())
        
        # Botón de actualización
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setToolTip("Actualizar gráfico")
        self.btn_refresh.clicked.connect(self.refresh_chart)
        self.btn_refresh.setFixedSize(30, 30)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #333;
                border-radius: 3px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #555;
            }
        """)
        
        # Botón de indicadores (con menú desplegable)
        self.btn_indicators = QToolButton()
        self.btn_indicators.setText("📈 Indicadores")
        self.btn_indicators.setPopupMode(QToolButton.InstantPopup)
        self.btn_indicators.setStyleSheet("""
            QToolButton {
                background-color: #2a2a2a;
                border: 1px solid #333;
                border-radius: 3px;
                color: white;
                padding: 5px 10px;
            }
            QToolButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #555;
            }
        """)
        
        # Menú de indicadores
        indicators_menu = QMenu()
        
        # SMA
        sma_action = indicators_menu.addAction("SMA (20)")
        sma_action.setCheckable(True)
        sma_action.triggered.connect(lambda: self.toggle_indicator('SMA'))
        
        # EMA
        ema_action = indicators_menu.addAction("EMA (12)")
        ema_action.setCheckable(True)
        ema_action.triggered.connect(lambda: self.toggle_indicator('EMA'))
        
        # RSI
        rsi_action = indicators_menu.addAction("RSI (14)")
        rsi_action.setCheckable(True)
        rsi_action.triggered.connect(lambda: self.toggle_indicator('RSI'))
        
        # MACD
        macd_action = indicators_menu.addAction("MACD")
        macd_action.setCheckable(True)
        macd_action.triggered.connect(lambda: self.toggle_indicator('MACD'))
        
        # Bollinger Bands
        bb_action = indicators_menu.addAction("Bollinger Bands")
        bb_action.setCheckable(True)
        bb_action.triggered.connect(lambda: self.toggle_indicator('Bollinger'))
        
        self.btn_indicators.setMenu(indicators_menu)
        
        # Botón de dibujo
        self.btn_drawing = QPushButton("✏️ Dibujar")
        self.btn_drawing.setCheckable(True)
        self.btn_drawing.setStyleSheet(self.btn_indicators.styleSheet())
        
        # Botón de zoom
        self.btn_zoom_fit = QPushButton("🔍 Ajustar")
        self.btn_zoom_fit.clicked.connect(self.auto_scale_chart)
        self.btn_zoom_fit.setStyleSheet(self.btn_indicators.styleSheet())
        
        # Etiqueta de estado
        self.status_label = QLabel("Cargando datos...")
        self.status_label.setStyleSheet("color: #888; font-size: 12px; padding-left: 10px;")
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #333;")
        
        # Agregar widgets
        top_layout.addWidget(QLabel("Símbolo:"))
        top_layout.addWidget(self.symbol_combo)
        top_layout.addWidget(QLabel("TF:"))
        top_layout.addWidget(self.timeframe_combo)
        top_layout.addWidget(self.btn_refresh)
        top_layout.addWidget(separator)
        top_layout.addWidget(self.btn_indicators)
        top_layout.addWidget(self.btn_drawing)
        top_layout.addWidget(self.btn_zoom_fit)
        top_layout.addStretch()
        top_layout.addWidget(self.status_label)
        
    def create_price_bar(self):
        """Crear barra inferior de precios."""
        self.price_bar_widget = QWidget()
        price_layout = QHBoxLayout(self.price_bar_widget)
        price_layout.setContentsMargins(15, 8, 15, 8)
        
        # Estilo para etiquetas de precio
        price_style = """
            QLabel {
                font-family: 'Consolas', 'Monospace';
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
                min-width: 140px;
                text-align: center;
            }
        """
        
        # Precio BID
        self.bid_label = QLabel("BID: --")
        self.bid_label.setStyleSheet(price_style + "background-color: #1a2a1a; color: #0af; font-size: 14px;")
        
        # Precio ASK
        self.ask_label = QLabel("ASK: --")
        self.ask_label.setStyleSheet(price_style + "background-color: #2a1a1a; color: #f0a; font-size: 14px;")
        
        # Spread
        self.spread_label = QLabel("Spread: --")
        self.spread_label.setStyleSheet(price_style + "background-color: #2a2a2a; color: #ccc; font-size: 13px;")
        
        # Cambio
        self.change_label = QLabel("Cambio: --")
        self.change_label.setStyleSheet(price_style + "background-color: #1a1a2a; color: #ccc; font-size: 13px;")
        
        # Alto del día
        self.high_label = QLabel("Alto: --")
        self.high_label.setStyleSheet("QLabel { color: #0f0; font-weight: bold; padding: 5px; }")
        
        # Bajo del día
        self.low_label = QLabel("Bajo: --")
        self.low_label.setStyleSheet("QLabel { color: #f00; font-weight: bold; padding: 5px; }")
        
        # Volumen
        self.volume_label = QLabel("Vol: --")
        self.volume_label.setStyleSheet("QLabel { color: #aaa; font-weight: bold; padding: 5px; }")
        
        # Agregar widgets
        price_layout.addWidget(self.bid_label)
        price_layout.addWidget(self.ask_label)
        price_layout.addWidget(self.spread_label)
        price_layout.addWidget(self.change_label)
        price_layout.addWidget(self.high_label)
        price_layout.addWidget(self.low_label)
        price_layout.addWidget(self.volume_label)
        price_layout.addStretch()
        
    def init_chart(self):
        """Inicializar el gráfico principal."""
        # Crear plot para velas
        self.main_plot = self.graph_widget.addPlot(row=0, col=0, title="")
        self.main_plot.setLabel('left', 'Precio', color='#aaa')
        self.main_plot.setLabel('bottom', 'Tiempo', color='#aaa')
        self.main_plot.showGrid(x=True, y=True, alpha=0.2)
        self.main_plot.setMouseEnabled(x=True, y=True)
        self.main_plot.setMenuEnabled(False)
        
        # Configurar eje X para mostrar tiempo
        self.main_plot.getAxis('bottom').setPen(pg.mkPen('#555'))
        self.main_plot.getAxis('left').setPen(pg.mkPen('#555'))
        
        # Configurar colores
        self.up_color = QColor(0, 255, 0, 200)  # Verde para velas alcistas
        self.down_color = QColor(255, 0, 0, 200)  # Rojo para velas bajistas
        
        # Línea de precio actual
        self.current_price_line = pg.InfiniteLine(
            angle=0, pen=pg.mkPen('#FFA500', width=2, style=Qt.DashLine)
        )
        self.main_plot.addItem(self.current_price_line)
        
        # Plot para indicadores (RSI, MACD)
        self.indicator_plot = self.graph_widget.addPlot(row=1, col=0)
        self.indicator_plot.setMaximumHeight(150)
        self.indicator_plot.showGrid(x=True, y=True, alpha=0.2)
        self.indicator_plot.setMouseEnabled(x=True, y=False)
        self.indicator_plot.setMenuEnabled(False)
        
        # Ajustar proporciones
        self.graph_widget.ci.layout.setRowStretchFactor(0, 3)
        self.graph_widget.ci.layout.setRowStretchFactor(1, 1)
        
    def init_toolbar(self):
        """Inicializar barra de herramientas del gráfico."""
        # ViewBox para interactividad
        self.vb = self.main_plot.getViewBox()
        
        # Crosshair (líneas cruzadas)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#666', style=Qt.DashLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#666', style=Qt.DashLine))
        
        # Agregar al plot pero ocultar inicialmente
        self.main_plot.addItem(self.v_line, ignoreBounds=True)
        self.main_plot.addItem(self.h_line, ignoreBounds=True)
        
        # Conectar eventos del mouse
        self.main_plot.scene().sigMouseMoved.connect(self.mouse_moved)
        self.main_plot.scene().sigMouseClicked.connect(self.mouse_clicked)
        
    def update_chart(self, candles, real_time_data=None):
        """Actualizar el gráfico con nuevos datos."""
        if not candles:
            self.status_label.setText("Sin datos disponibles")
            return
        
        self.candles_data = candles
        
        # Limpiar gráfico anterior
        self.clear_chart_items()
        
        # Preparar datos para pyqtgraph
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(candles)
        
        # Dibujar velas
        self.draw_candles(times, opens, highs, lows, closes)
        
        # Dibujar indicadores activos
        self.draw_indicators(times, closes)
        
        # Actualizar información de precios
        if real_time_data:
            self.update_price_display(real_time_data)
        
        # Actualizar línea de precio actual
        if closes:
            current_price = closes[-1]
            self.current_price_line.setPos(current_price)
            self.last_price = current_price
        
        # Actualizar estadísticas
        self.update_statistics(candles)
        
        # Auto-ajustar zoom
        self.auto_scale_chart()
        
        # Actualizar estado
        self.status_label.setText(
            f"{self.current_symbol} {self.current_timeframe} | "
            f"Velas: {len(candles)} | "
            f"Última: {candles[-1].time.strftime('%d/%m %H:%M')}"
        )
        
    def prepare_candle_data(self, candles):
        """Preparar datos de velas para pyqtgraph."""
        times = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        for candle in candles:
            # Convertir datetime a timestamp
            if hasattr(candle, 'time'):
                if hasattr(candle.time, 'timestamp'):
                    times.append(candle.time.timestamp())
                else:
                    times.append(pd.Timestamp(candle.time).timestamp())
            else:
                times.append(len(times))
            
            # Obtener precios OHLC
            if hasattr(candle, 'open'):
                opens.append(float(candle.open))
                highs.append(float(candle.high))
                lows.append(float(candle.low))
                closes.append(float(candle.close))
            elif isinstance(candle, dict):
                opens.append(float(candle.get('open', 0)))
                highs.append(float(candle.get('high', 0)))
                lows.append(float(candle.get('low', 0)))
                closes.append(float(candle.get('close', 0)))
            
            # Volumen (si está disponible)
            if hasattr(candle, 'volume'):
                volumes.append(float(candle.volume))
            else:
                volumes.append(0)
        
        return (
            np.array(times),
            np.array(opens),
            np.array(highs),
            np.array(lows),
            np.array(closes),
            np.array(volumes)
        )
    
    def draw_candles(self, times, opens, highs, lows, closes):
        """Dibujar velas japonesas en el gráfico."""
        # Ancho de las velas (en segundos)
        if len(times) > 1:
            candle_width = (times[1] - times[0]) * 0.7
        else:
            candle_width = 3600 * 0.7  # 1 hora por defecto
        
        for i in range(len(times)):
            # Determinar color según dirección
            is_bullish = closes[i] >= opens[i]
            color = self.up_color if is_bullish else self.down_color
            
            # Dibujar mecha (línea de alto a bajo)
            wick = pg.PlotCurveItem(
                x=[times[i], times[i]],
                y=[lows[i], highs[i]],
                pen=pg.mkPen(color=color, width=1)
            )
            self.main_plot.addItem(wick)
            self.candle_items.append(wick)
            
            # Dibujar cuerpo (rectángulo open-close)
            body_top = max(opens[i], closes[i])
            body_bottom = min(opens[i], closes[i])
            body_height = abs(closes[i] - opens[i])
            
            # Solo dibujar cuerpo si hay altura
            if body_height > 0:
                body = pg.QtWidgets.QGraphicsRectItem(
                    times[i] - candle_width/2,
                    body_bottom,
                    candle_width,
                    body_height
                )
                body.setBrush(pg.mkBrush(color))
                body.setPen(pg.mkPen(color))
                self.main_plot.addItem(body)
                self.candle_items.append(body)
            else:
                # Línea para velas doji
                line = pg.PlotCurveItem(
                    x=[times[i] - candle_width/2, times[i] + candle_width/2],
                    y=[opens[i], opens[i]],
                    pen=pg.mkPen(color=color, width=1)
                )
                self.main_plot.addItem(line)
                self.candle_items.append(line)
    
    def draw_indicators(self, times, closes):
        """Dibujar indicadores técnicos."""
        # Limpiar indicadores anteriores
        self.indicator_plot.clear()
        
        # Preparar datos como pandas Series
        close_series = pd.Series(closes)
        
        # SMA
        if self.active_indicators['SMA']['enabled']:
            period = self.active_indicators['SMA']['period']
            if len(closes) >= period:
                sma = close_series.rolling(window=period).mean().values
                sma_line = pg.PlotCurveItem(
                    x=times[period-1:],
                    y=sma[period-1:],
                    pen=pg.mkPen(color=self.active_indicators['SMA']['color'], width=2),
                    name='SMA'
                )
                self.main_plot.addItem(sma_line)
                self.indicator_items.append(sma_line)
        
        # EMA
        if self.active_indicators['EMA']['enabled']:
            period = self.active_indicators['EMA']['period']
            if len(closes) >= period:
                ema = close_series.ewm(span=period, adjust=False).mean().values
                ema_line = pg.PlotCurveItem(
                    x=times[period-1:],
                    y=ema[period-1:],
                    pen=pg.mkPen(color=self.active_indicators['EMA']['color'], width=2),
                    name='EMA'
                )
                self.main_plot.addItem(ema_line)
                self.indicator_items.append(ema_line)
        
        # RSI
        if self.active_indicators['RSI']['enabled']:
            period = self.active_indicators['RSI']['period']
            if len(closes) > period:
                delta = close_series.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                # Dibujar RSI
                rsi_line = pg.PlotCurveItem(
                    x=times[period:],
                    y=rsi[period:],
                    pen=pg.mkPen(color=self.active_indicators['RSI']['color'], width=2)
                )
                self.indicator_plot.addItem(rsi_line)
                
                # Líneas de referencia
                overbought = pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('#f00', style=Qt.DashLine))
                oversold = pg.InfiniteLine(pos=30, angle=0, pen=pg.mkPen('#0f0', style=Qt.DashLine))
                self.indicator_plot.addItem(overbought)
                self.indicator_plot.addItem(oversold)
                
                self.indicator_plot.setYRange(0, 100)
                self.indicator_plot.setLabel('left', 'RSI')
        
        # Bollinger Bands
        elif self.active_indicators['Bollinger']['enabled']:
            period = self.active_indicators['Bollinger']['period']
            std = self.active_indicators['Bollinger']['std']
            
            if len(closes) >= period:
                # Calcular banda media (SMA)
                sma = close_series.rolling(window=period).mean()
                std_dev = close_series.rolling(window=period).std()
                
                upper_band = sma + (std_dev * std)
                lower_band = sma - (std_dev * std)
                
                # Dibujar bandas
                upper_line = pg.PlotCurveItem(
                    x=times[period-1:],
                    y=upper_band[period-1:],
                    pen=pg.mkPen(color='#888', width=1, style=Qt.DashLine)
                )
                middle_line = pg.PlotCurveItem(
                    x=times[period-1:],
                    y=sma[period-1:],
                    pen=pg.mkPen(color='#aaa', width=1)
                )
                lower_line = pg.PlotCurveItem(
                    x=times[period-1:],
                    y=lower_band[period-1:],
                    pen=pg.mkPen(color='#888', width=1, style=Qt.DashLine)
                )
                
                self.main_plot.addItem(upper_line)
                self.main_plot.addItem(middle_line)
                self.main_plot.addItem(lower_line)
                
                self.indicator_items.extend([upper_line, middle_line, lower_line])
    
    def update_price_display(self, price_data):
        """Actualizar display de precios en tiempo real."""
        if not price_data:
            return
        
        # Extraer datos
        bid = price_data.get('bid', 0)
        ask = price_data.get('ask', 0)
        
        if bid > 0 and ask > 0:
            # Calcular spread
            spread = abs(ask - bid) * 10000  # en pips
            
            # Calcular cambio
            if self.last_price:
                self.price_change = ((bid - self.last_price) / self.last_price) * 100
                self.last_price = bid
            
            # Actualizar etiquetas
            self.bid_label.setText(f"BID: {bid:.5f}")
            self.ask_label.setText(f"ASK: {ask:.5f}")
            self.spread_label.setText(f"Spread: {spread:.1f}")
            
            # Cambio con color
            if self.price_change >= 0:
                self.change_label.setText(f"▲ {self.price_change:+.2f}%")
                self.change_label.setStyleSheet(
                    "QLabel { background-color: #1a2a1a; color: #0f0; font-weight: bold; padding: 5px 12px; border-radius: 4px; }"
                )
            else:
                self.change_label.setText(f"▼ {self.price_change:+.2f}%")
                self.change_label.setStyleSheet(
                    "QLabel { background-color: #2a1a1a; color: #f00; font-weight: bold; padding: 5px 12px; border-radius: 4px; }"
                )
            
            # Actualizar línea de precio actual
            self.current_price_line.setPos(bid)
            
            # Guardar para siguiente comparación
            self.real_time_prices.append(bid)
    
    def update_statistics(self, candles):
        """Calcular y mostrar estadísticas."""
        if not candles:
            return
        
        # Calcular alto y bajo
        highs = [float(c.high) for c in candles if hasattr(c, 'high')]
        lows = [float(c.low) for c in candles if hasattr(c, 'low')]
        
        if highs and lows:
            daily_high = max(highs)
            daily_low = min(lows)
            
            self.high_label.setText(f"Alto: {daily_high:.5f}")
            self.low_label.setText(f"Bajo: {daily_low:.5f}")
            
            # Volumen (si está disponible)
            if hasattr(candles[0], 'volume'):
                total_volume = sum(float(c.volume) for c in candles if hasattr(c, 'volume'))
                self.volume_label.setText(f"Vol: {total_volume:,.0f}")
    
    def clear_chart_items(self):
        """Limpiar todos los elementos del gráfico."""
        # Remover velas
        for item in self.candle_items:
            self.main_plot.removeItem(item)
        self.candle_items.clear()
        
        # Remover indicadores
        for item in self.indicator_items:
            if item in self.main_plot.items:
                self.main_plot.removeItem(item)
            if item in self.indicator_plot.items:
                self.indicator_plot.removeItem(item)
        self.indicator_items.clear()
        
        # Limpiar plot de indicadores
        self.indicator_plot.clear()
    
    def auto_scale_chart(self):
        """Auto-ajustar el zoom del gráfico."""
        if not self.candles_data:
            return
        
        # Obtener rangos de tiempo y precio
        times = []
        prices = []
        
        for candle in self.candles_data:
            # Tiempo
            if hasattr(candle.time, 'timestamp'):
                times.append(candle.time.timestamp())
            else:
                times.append(pd.Timestamp(candle.time).timestamp())
            
            # Precios
            if hasattr(candle, 'high'):
                prices.append(float(candle.high))
                prices.append(float(candle.low))
        
        if times and prices:
            # Agregar márgenes
            time_margin = (max(times) - min(times)) * 0.05
            price_margin = (max(prices) - min(prices)) * 0.05
            
            # Establecer rangos
            self.main_plot.setXRange(min(times) - time_margin, max(times) + time_margin)
            self.main_plot.setYRange(min(prices) - price_margin, max(prices) + price_margin)
    
    def toggle_indicator(self, indicator_name):
        """Activar/desactivar un indicador."""
        if indicator_name in self.active_indicators:
            self.active_indicators[indicator_name]['enabled'] = not self.active_indicators[indicator_name]['enabled']
            
            # Emitir señal
            if self.active_indicators[indicator_name]['enabled']:
                self.indicator_added.emit(indicator_name, self.active_indicators[indicator_name])
            else:
                self.indicator_removed.emit(indicator_name)
            
            # Redibujar si hay datos
            if self.candles_data:
                times, opens, highs, lows, closes, volumes = self.prepare_candle_data(self.candles_data)
                self.draw_indicators(times, closes)
    
    def mouse_moved(self, pos):
        """Manejador para movimiento del mouse (crosshair)."""
        if self.main_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.main_plot.vb.mapSceneToView(pos)
            
            # Actualizar líneas del crosshair
            self.v_line.setPos(mouse_point.x())
            self.h_line.setPos(mouse_point.y())
            
            # Mostrar información en tooltip
            if hasattr(self, 'tooltip_label'):
                self.tooltip_label.setText(f"X: {mouse_point.x():.2f}, Y: {mouse_point.y():.5f}")
    
    def mouse_clicked(self, event):
        """Manejador para clic del mouse."""
        if event.double():
            # Doble clic: auto-zoom
            self.auto_scale_chart()
        else:
            # Clic simple: emitir señal con coordenadas
            if self.main_plot.sceneBoundingRect().contains(event.scenePos()):
                mouse_point = self.main_plot.vb.mapSceneToView(event.scenePos())
                
                # Buscar la vela más cercana
                if self.candles_data:
                    times, _, _, _, closes, _ = self.prepare_candle_data(self.candles_data)
                    
                    # Encontrar índice más cercano
                    idx = np.abs(times - mouse_point.x()).argmin()
                    
                    # Emitir señal
                    self.chart_clicked.emit({
                        'x': mouse_point.x(),
                        'y': mouse_point.y(),
                        'price': closes[idx] if idx < len(closes) else mouse_point.y(),
                        'time': datetime.fromtimestamp(times[idx]) if idx < len(times) else None,
                        'index': idx
                    })
    
    def blink_current_price(self):
        """Efecto de parpadeo para la línea de precio actual."""
        if self.is_blinking:
            self.current_price_line.setPen(pg.mkPen('#FFA500', width=2, style=Qt.DashLine))
        else:
            self.current_price_line.setPen(pg.mkPen('#FFA500', width=1, style=Qt.SolidLine))
        
        self.is_blinking = not self.is_blinking
    
    def auto_update_chart(self):
        """Actualización automática del gráfico."""
        if self.candles_data:
            # Simular actualización de precio
            if self.real_time_prices:
                last_price = self.real_time_prices[-1]
                # Pequeña variación aleatoria para simulación
                import random
                new_price = last_price + random.uniform(-0.0001, 0.0001)
                self.update_price_display({'bid': new_price, 'ask': new_price + 0.0001})
    
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
    
    def set_theme(self, theme='dark'):
        """Establecer tema del gráfico."""
        if theme == 'dark':
            self.graph_widget.setBackground('#0a0a0a')
            self.main_plot.getAxis('bottom').setPen(pg.mkPen('#666'))
            self.main_plot.getAxis('left').setPen(pg.mkPen('#666'))
        elif theme == 'light':
            self.graph_widget.setBackground('#ffffff')
            self.main_plot.getAxis('bottom').setPen(pg.mkPen('#333'))
            self.main_plot.getAxis('left').setPen(pg.mkPen('#333'))
    
    def save_chart_image(self, filename='chart.png'):
        """Guardar el gráfico como imagen."""
        try:
            self.graph_widget.grab().save(filename)
            return True
        except Exception as e:
            print(f"Error guardando imagen: {e}")
            return False