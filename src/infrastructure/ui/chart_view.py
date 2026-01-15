# src/infrastructure/ui/chart_view.py
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor
import pyqtgraph as pg
from datetime import datetime, timedelta
import pandas as pd


class CustomDateAxis(pg.AxisItem):
    """Eje personalizado para mostrar fechas y horas SIN GAPS."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)
        self.tick_positions = []
        self.tick_labels = []
        
    def set_ticks(self, positions, labels):
        """Establecer ticks personalizados."""
        self.tick_positions = positions
        self.tick_labels = labels
        self.ticks = [(pos, label) for pos, label in zip(positions, labels)]
        
    def tickStrings(self, values, scale, spacing):
        """Mostrar etiquetas personalizadas."""
        strings = []
        for v in values:
            # Buscar la etiqueta más cercana
            if self.tick_positions:
                # Encontrar el índice más cercano
                idx = min(range(len(self.tick_positions)), 
                         key=lambda i: abs(self.tick_positions[i] - v))
                if abs(self.tick_positions[idx] - v) < 0.5:  # Tolerancia
                    strings.append(self.tick_labels[idx])
                else:
                    strings.append("")
            else:
                strings.append("")
        return strings


class ChartView(QWidget):
    """Widget para gráficos de trading con velas japonesas."""
    
    # Señales
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración inicial
        self.current_symbol = "EURUSD"
        self.current_timeframe = "H1"
        self.candles_data = []
        self.symbol_info = {}
        self.server_time = None
        self.x_positions = []  # Posiciones X sin gaps
        self.x_dates = []      # Fechas correspondientes
        
        # Inicializar UI
        self.init_ui()
        self.init_chart()
        
        # Timer para actualizar hora del servidor
        self.server_time_timer = QTimer()
        self.server_time_timer.timeout.connect(self.update_server_time_display)
        self.server_time_timer.start(1000)  # Actualizar cada segundo
        
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
        
        # 3. Barra inferior de precios e información
        self.create_info_bar()
        main_layout.addWidget(self.info_bar_widget)
        
    def create_top_bar(self):
        """Crear barra superior de controles."""
        self.top_bar_widget = QWidget()
        top_layout = QHBoxLayout(self.top_bar_widget)
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        # Selector de símbolo
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["EURUSD", "US500", "GBPUSD", "USDJPY", "XAUUSD"])
        self.symbol_combo.setCurrentText(self.current_symbol)
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        self.symbol_combo.setFixedWidth(100)
        
        # Selector de timeframe
        self.timeframe_combo = QComboBox()
        timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
        self.timeframe_combo.addItems(timeframes)
        self.timeframe_combo.setCurrentText(self.current_timeframe)
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        self.timeframe_combo.setFixedWidth(70)
        
        # Botón de actualización
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setToolTip("Actualizar gráfico")
        self.btn_refresh.clicked.connect(self.refresh_chart)
        self.btn_refresh.setFixedSize(30, 30)
        
        # Botón de zoom
        self.btn_zoom_fit = QPushButton("🔍 Ajustar")
        self.btn_zoom_fit.clicked.connect(self.auto_scale_chart)
        
        # Información del símbolo
        self.lbl_symbol_info = QLabel("Dígitos: -- | Punto: --")
        self.lbl_symbol_info.setStyleSheet("color: #aaa; font-size: 12px;")
        
        # Hora del servidor
        self.lbl_server_time = QLabel("Servidor: --:--")
        self.lbl_server_time.setStyleSheet("color: #0af; font-size: 12px; font-weight: bold;")
        
        # Etiqueta de estado
        self.status_label = QLabel("Cargando datos...")
        self.status_label.setStyleSheet("color: #888; font-size: 12px; padding-left: 10px;")
        
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
        top_layout.addWidget(separator)
        top_layout.addWidget(self.lbl_symbol_info)
        top_layout.addWidget(self.lbl_server_time)
        top_layout.addStretch()
        top_layout.addWidget(self.status_label)
        
    def create_info_bar(self):
        """Crear barra inferior de información."""
        self.info_bar_widget = QWidget()
        info_layout = QHBoxLayout(self.info_bar_widget)
        info_layout.setContentsMargins(15, 8, 15, 8)
        
        # Información de escala del precio
        price_scale_group = QWidget()
        price_layout = QVBoxLayout(price_scale_group)
        price_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_price_scale = QLabel("Escala: --")
        self.lbl_price_scale.setStyleSheet("color: #ffa500; font-size: 11px;")
        
        self.lbl_min_price_move = QLabel("Mín. movimiento: --")
        self.lbl_min_price_move.setStyleSheet("color: #aaa; font-size: 11px;")
        
        price_layout.addWidget(self.lbl_price_scale)
        price_layout.addWidget(self.lbl_min_price_move)
        
        # Precio BID
        self.bid_label = QLabel("BID: --")
        self.bid_label.setStyleSheet("color: #0af; font-weight: bold; font-size: 14px;")
        
        # Precio ASK
        self.ask_label = QLabel("ASK: --")
        self.ask_label.setStyleSheet("color: #f0a; font-weight: bold; font-size: 14px;")
        
        # Spread
        self.spread_label = QLabel("Spread: --")
        self.spread_label.setStyleSheet("color: #fff; font-weight: bold; font-size: 14px;")
        
        # Cambio
        self.change_label = QLabel("Cambio: --")
        self.change_label.setStyleSheet("color: #aaa; font-size: 13px;")
        
        # Tiempo local vs servidor
        time_group = QWidget()
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_local_time = QLabel("Local: --:--")
        self.lbl_local_time.setStyleSheet("color: #0f0; font-size: 11px;")
        
        self.lbl_time_diff = QLabel("Diff: --")
        self.lbl_time_diff.setStyleSheet("color: #aaa; font-size: 11px;")
        
        time_layout.addWidget(self.lbl_local_time)
        time_layout.addWidget(self.lbl_time_diff)
        
        # Agregar widgets
        info_layout.addWidget(price_scale_group)
        info_layout.addWidget(self.bid_label)
        info_layout.addWidget(self.ask_label)
        info_layout.addWidget(self.spread_label)
        info_layout.addWidget(self.change_label)
        info_layout.addWidget(time_group)
        info_layout.addStretch()
        
    def init_chart(self):
        """Inicializar el gráfico principal."""
        # Usar nuestro eje personalizado
        self.date_axis = CustomDateAxis(orientation='bottom')
        
        # Crear plot para velas
        self.main_plot = self.graph_widget.addPlot(row=0, col=0, title="", axisItems={'bottom': self.date_axis})
        self.main_plot.setLabel('left', 'Precio', color='#aaa')
        self.main_plot.showGrid(x=True, y=True, alpha=0.2)
        self.main_plot.setMouseEnabled(x=True, y=True)
        self.main_plot.setMenuEnabled(False)
        
        # Configurar colores
        self.up_color = QColor(0, 255, 0, 200)
        self.down_color = QColor(255, 0, 0, 200)
    
    # ===== MÉTODOS PRINCIPALES MODIFICADOS =====
    
    def prepare_candle_data(self, candles):
        """Preparar datos de velas ELIMINANDO GAPS entre días/trading."""
        if not candles:
            return (np.array([]), np.array([]), np.array([]), 
                    np.array([]), np.array([]), np.array([]))
        
        # Ordenar velas por tiempo
        sorted_candles = sorted(candles, key=lambda x: 
            x.timestamp if hasattr(x, 'timestamp') else 
            x.time if hasattr(x, 'time') else 
            datetime.now())
        
        # Crear índices continuos (eliminar gaps)
        x_positions = []
        x_dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        # Usar índice incremental para eliminar espacios vacíos
        current_x = 0
        
        for i, candle in enumerate(sorted_candles):
            # Posición X continua (sin gaps)
            x_positions.append(current_x)
            current_x += 1  # Incremento constante
            
            # Guardar fecha para etiquetas
            if hasattr(candle, 'timestamp'):
                dt = candle.timestamp
            elif hasattr(candle, 'time'):
                dt = candle.time
            else:
                dt = datetime.now()
            x_dates.append(dt)
            
            # Precios
            opens.append(float(candle.open))
            highs.append(float(candle.high))
            lows.append(float(candle.low))
            closes.append(float(candle.close))
            
            # Volumen
            if hasattr(candle, 'volume'):
                volumes.append(float(candle.volume))
            else:
                volumes.append(0)
        
        # Guardar para uso posterior
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
        """Dibujar velas japonesas con ESPACIADO MEJORADO."""
        if len(times) == 0:
            return
        
        # Ancho de vela fijo para espaciado uniforme
        candle_width = 0.5  # 70% del espacio disponible (más separación)
        
        # Limpiar el gráfico
        self.main_plot.clear()
        
        # Dibujar todas las velas
        for i in range(len(times)):
            # Determinar color
            is_bullish = closes[i] >= opens[i]
            color = self.up_color if is_bullish else self.down_color
            
            # Dibujar mecha (línea de alto a bajo)
            wick = pg.PlotCurveItem(
                x=np.array([times[i], times[i]], dtype=np.float64),
                y=np.array([lows[i], highs[i]], dtype=np.float64),
                pen=pg.mkPen(color=color, width=1.5)  # Mecha más gruesa
            )
            self.main_plot.addItem(wick)
            
            # Dibujar cuerpo (rectángulo open-close)
            body_top = max(opens[i], closes[i])
            body_bottom = min(opens[i], closes[i])
            body_height = abs(closes[i] - opens[i])
            
            # Asegurar altura mínima para cuerpos muy pequeños
            min_body_height = (max(highs) - min(lows)) * 0.002 if len(highs) > 0 else 0.0001
            if body_height < min_body_height:
                body_height = min_body_height
                # Ajustar posición para mantener centro
                if is_bullish:
                    body_bottom = (opens[i] + closes[i]) / 2 - body_height/2
                else:
                    body_top = (opens[i] + closes[i]) / 2 + body_height/2
            
            # Crear rectángulo para el cuerpo
            body = pg.QtWidgets.QGraphicsRectItem(
                times[i] - candle_width/2,
                body_bottom,
                candle_width,
                body_height
            )
            body.setBrush(pg.mkBrush(color))
            body.setPen(pg.mkPen(color))
            self.main_plot.addItem(body)
        
        # Configurar eje X con fechas
        self.configure_x_axis_with_dates()
    
    def configure_x_axis_with_dates(self):
        """Configurar eje X para mostrar fechas en posiciones específicas."""
        if not self.x_positions or not self.x_dates:
            return
        
        # Crear etiquetas para algunas posiciones (no todas)
        tick_positions = []
        tick_labels = []
        
        # Número máximo de etiquetas
        max_labels = min(10, len(self.x_positions))
        
        # Seleccionar posiciones para etiquetas
        if len(self.x_positions) <= max_labels:
            # Mostrar todas
            indices = range(len(self.x_positions))
        else:
            # Mostrar algunas (primera, última y distribuidas)
            step = len(self.x_positions) // (max_labels - 2)
            indices = [0]  # Primera
            for i in range(step, len(self.x_positions) - step, step):
                if len(tick_positions) < max_labels - 2:
                    indices.append(i)
            indices.append(len(self.x_positions) - 1)  # Última
        
        # Crear ticks
        for idx in indices:
            if idx < len(self.x_positions) and idx < len(self.x_dates):
                # Formatear fecha según timeframe
                dt = self.x_dates[idx]
                
                if isinstance(dt, datetime):
                    # Formato según timeframe
                    if self.current_timeframe in ["D1", "W1"]:
                        date_str = dt.strftime('%d/%m')
                    elif self.current_timeframe in ["H1", "H4"]:
                        date_str = dt.strftime('%d/%m %H:%M')
                    else:  # Timeframes más cortos
                        date_str = dt.strftime('%H:%M')
                else:
                    try:
                        pd_dt = pd.Timestamp(dt)
                        if self.current_timeframe in ["D1", "W1"]:
                            date_str = pd_dt.strftime('%d/%m')
                        elif self.current_timeframe in ["H1", "H4"]:
                            date_str = pd_dt.strftime('%d/%m %H:%M')
                        else:
                            date_str = pd_dt.strftime('%H:%M')
                    except:
                        date_str = str(idx)
                
                tick_positions.append(self.x_positions[idx])
                tick_labels.append(date_str)
        
        # Configurar eje X personalizado
        self.date_axis.set_ticks(tick_positions, tick_labels)
        
        # Configurar rango del eje X con márgenes
        if len(self.x_positions) > 0:
            x_min = min(self.x_positions) - 1
            x_max = max(self.x_positions) + 1
            self.main_plot.setXRange(x_min, x_max)
    
    def auto_scale_chart(self):
        """Auto-ajustar el zoom del gráfico."""
        if not self.candles_data:
            return
        
        # Preparar datos para obtener rangos
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(self.candles_data)
        
        if len(times) > 0:
            # Margen horizontal
            x_margin = 1.0  # Margen fijo para mejor visualización
            
            # Obtener rango de precios
            all_prices = np.concatenate([opens, highs, lows, closes])
            min_price = np.min(all_prices)
            max_price = np.max(all_prices)
            
            # Margen vertical (5% del rango)
            if min_price != max_price:
                price_margin = (max_price - min_price) * 0.05
            else:
                price_margin = abs(min_price) * 0.01 if min_price != 0 else 1.0
            
            # Establecer rangos
            self.main_plot.setXRange(min(times) - x_margin, max(times) + x_margin)
            self.main_plot.setYRange(min_price - price_margin, max_price + price_margin)
    
    # ===== MÉTODOS EXISTENTES (MANTENIDOS) =====
    
    def update_chart(self, candles, real_time_data=None, symbol_info=None, server_time=None):
        """Actualizar el gráfico con nuevos datos."""
        if not candles:
            self.status_label.setText("Sin datos disponibles")
            return
        
        self.candles_data = candles
        
        # Guardar información del símbolo
        if symbol_info:
            self.symbol_info = symbol_info
            self.update_symbol_info_display()
        
        # Guardar hora del servidor
        if server_time:
            self.server_time = server_time
            self.update_server_time_display()
        
        # Limpiar gráfico anterior
        self.main_plot.clear()
        
        # Preparar datos (ahora sin gaps)
        times, opens, highs, lows, closes, volumes = self.prepare_candle_data(candles)
        
        # Dibujar velas
        self.draw_candles(times, opens, highs, lows, closes)
        
        # Actualizar información de precios
        if real_time_data:
            self.update_price_display(real_time_data)
        
        # Configurar escala del eje Y
        self.configure_price_axis()
        
        # Auto-ajustar zoom
        self.auto_scale_chart()
        
        # Actualizar estado
        if candles:
            last_candle = candles[-1]
            if hasattr(last_candle, 'timestamp'):
                last_time = last_candle.timestamp
            elif hasattr(last_candle, 'time'):
                last_time = last_candle.time
            else:
                last_time = datetime.now()
            
            self.status_label.setText(
                f"{self.current_symbol} {self.current_timeframe} | "
                f"Velas: {len(candles)} | "
                f"Última: {last_time.strftime('%d/%m %H:%M')}"
            )
    
    def update_symbol_info_display(self):
        """Actualizar display de información del símbolo."""
        if not self.symbol_info:
            return
        
        digits = self.symbol_info.get('digits', 5)
        point = self.symbol_info.get('point', 0.00001)
        spread = self.symbol_info.get('spread', 0)
        
        self.lbl_symbol_info.setText(f"Dígitos: {digits} | Punto: {point:.6f} | Spread: {spread}")
        
        # Mostrar escala del precio
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
        left_axis = self.main_plot.getAxis('left')
        
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
            self.lbl_time_diff.setStyleSheet(f"color: {color}; font-size: 11px;")
            self.server_time = server_dt + timedelta(seconds=1)
        else:
            self.lbl_server_time.setText("Servidor: --:--")
            self.lbl_time_diff.setText("Diff: --")
    
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
            
            if hasattr(self, 'last_bid'):
                change = ((bid - self.last_bid) / self.last_bid) * 100
                change_text = f"{change:+.2f}%"
                if change >= 0:
                    self.change_label.setText(f"▲ {change_text}")
                    self.change_label.setStyleSheet("color: #00ff00; font-weight: bold;")
                else:
                    self.change_label.setText(f"▼ {change_text}")
                    self.change_label.setStyleSheet("color: #ff0000; font-weight: bold;")
            
            self.last_bid = bid
    
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