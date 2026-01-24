# src/presentation/main_window.py
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QTextEdit, QTabWidget,
                             QSplitter, QGroupBox, QGridLayout, QMessageBox, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# Importar tus componentes
try:
    from src.infrastructure.ui.chart_view import ChartView
    from src.infrastructure.ui.control_panel import ControlPanel
    from src.application.use_cases.connect_to_mt5 import create_connect_to_mt5_use_case
    from src.application.use_cases.fetch_market_data import create_fetch_market_data_use_case
    from src.config import settings
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"⚠️ Advertencia de importación: {e}")
    # Si no existen aún, crear placeholders
    ChartView = None
    ControlPanel = None
    IMPORT_SUCCESS = False


class MainWindow(QMainWindow):
    """Ventana principal de la plataforma de trading."""
    
    # Señales
    connection_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)
    sell_requested = pyqtSignal(dict)
    indicators_updated = pyqtSignal(dict)  # NUEVA SEÑAL PARA INDICADORES
    
    def __init__(self):
        super().__init__()
        
        # Configuración inicial
        self.is_dark_theme = True
        self.is_connected = False
        
        # Variables para MT5
        self.mt5_use_case = None
        self.data_use_case = None
        
        # Estado actual
        self.current_symbol = "US500"
        self.current_timeframe = "1H"
        self.server_name = "No conectado"
        
        # NUEVO: Configuración de indicadores
        self.indicators_config = {
            'sma': {'enabled': True, 'color': '#ffff00', 'period': 20, 'line_width': 2},
            'ema': {'enabled': True, 'color': '#ff00ff', 'period': 12, 'line_width': 2},
            'rsi': {'enabled': True, 'color': '#ffaa00', 'period': 14, 'overbought': 70, 'oversold': 30, 'line_width': 2},
            'macd': {'enabled': True, 'fast': 12, 'slow': 26, 'signal': 9, 'line_width': 2},
            'bollinger': {'enabled': True, 'period': 20, 'std': 2.0, 'line_width': 1.5},
            'stochastic': {'enabled': True, 'k_period': 14, 'd_period': 3, 'slowing': 3, 'line_width': 2}
        }
        
        # Datos demo para pruebas
        self.demo_candles = self.create_demo_candles()
        
        # Inicializar UI
        self.init_ui()
        
        # Aplicar tema
        self.apply_theme()
        
        # Configurar timers
        self.init_timers()
        
        # Conectar señales internas
        self.connect_internal_signals()
        
        # Cargar datos demo inicial
        self.load_demo_data()
        
        # Mostrar mensaje de inicio
        self.log_message("🚀 US500 Trading Platform iniciado")
        self.log_message("📊 Versión 1.0.0 con Indicadores Técnicos")
        self.log_message("💡 Presione 'Conectar a MT5' para datos reales")
    
    def create_demo_candles(self):
        """Crear datos demo para pruebas."""
        from datetime import datetime, timedelta
        import random
        
        candles = []
        base_price = 5000.0
        current_time = datetime.now() - timedelta(hours=100)
        
        for i in range(100):
            change = random.uniform(-20, 20)
            open_price = base_price
            close_price = base_price + change
            high_price = max(open_price, close_price) + random.uniform(0, 8)
            low_price = min(open_price, close_price) - random.uniform(0, 8)
            
            # Crear objeto candle simple
            candle = type('Candle', (), {
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'timestamp': current_time + timedelta(hours=i)
            })()
            candles.append(candle)
            base_price = close_price
        
        return candles
    
    def load_demo_data(self):
        """Cargar datos demo en el gráfico."""
        if not hasattr(self, 'chart_view') or not self.chart_view:
            return
        
        try:
            # Actualizar título
            self.update_chart_title(self.current_symbol, self.current_timeframe, len(self.demo_candles))
            
            # Si ChartView es el componente real
            if isinstance(self.chart_view, ChartView):
                # Pasar configuración de indicadores al gráfico
                self.chart_view.update_indicator_settings(self.indicators_config)
                
                # Actualizar gráfico con datos demo
                self.chart_view.update_chart(self.demo_candles, self.indicators_config)
                
                # Activar indicadores por defecto
                if hasattr(self.chart_view, 'btn_toggle_indicators'):
                    self.chart_view.btn_toggle_indicators.setChecked(True)
                
                self.log_message("📊 Datos demo cargados con indicadores")
            
        except Exception as e:
            self.log_message(f"⚠️ Error cargando datos demo: {str(e)}")
    
    def connect_internal_signals(self):
        """Conectar señales internas entre componentes."""
        try:
            # Conectar botón de conexión
            self.btn_connect.clicked.connect(self.toggle_connection)
            
            # Conectar botones de trading
            self.btn_buy.clicked.connect(lambda: self.on_trading_action('buy'))
            self.btn_sell.clicked.connect(lambda: self.on_trading_action('sell'))
            
            # Conectar botón de actualizar
            self.btn_refresh.clicked.connect(self.refresh_data)
            self.btn_refresh_positions.clicked.connect(self.refresh_positions)
            
            # Conectar señales del control panel si existe
            if hasattr(self, 'control_panel') and self.control_panel:
                if hasattr(self.control_panel, 'connect_requested'):
                    self.control_panel.connect_requested.connect(self.connect_to_mt5)
                if hasattr(self.control_panel, 'disconnect_requested'):
                    self.control_panel.disconnect_requested.connect(self.disconnect_from_mt5)
                if hasattr(self.control_panel, 'symbol_changed'):
                    self.control_panel.symbol_changed.connect(self.on_symbol_changed)
                if hasattr(self.control_panel, 'timeframe_changed'):
                    self.control_panel.timeframe_changed.connect(self.on_timeframe_changed)
                if hasattr(self.control_panel, 'buy_requested'):
                    self.control_panel.buy_requested.connect(self.on_trading_signal)
                if hasattr(self.control_panel, 'sell_requested'):
                    self.control_panel.sell_requested.connect(self.on_trading_signal)
                if hasattr(self.control_panel, 'refresh_positions'):
                    self.control_panel.refresh_positions.connect(self.refresh_positions)
                
                # NUEVO: Conectar señal de indicadores del control panel
                if hasattr(self.control_panel, 'indicators_updated'):
                    self.control_panel.indicators_updated.connect(self.on_indicators_updated)
                    self.log_message("✅ Señal de indicadores conectada")
            
        except Exception as e:
            self.log_message(f"⚠️ Error conectando señales: {str(e)}")
    
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        self.setWindowTitle("US500 Trading Platform - Con Indicadores Técnicos")
        self.setGeometry(100, 100, 1400, 900)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 1. Barra superior (conexión y símbolos)
        self.create_top_bar()
        main_layout.addLayout(self.top_bar_layout)
        
        # 2. Área principal dividida
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo (gráfico)
        left_panel = self.create_chart_panel()
        splitter.addWidget(left_panel)
        
        # Panel derecho (control)
        right_panel = self.create_control_panel()
        splitter.addWidget(right_panel)
        
        # Configurar tamaños relativos
        splitter.setSizes([900, 500])
        
        main_layout.addWidget(splitter, 1)  # 1 = stretch factor
        
        # 3. Barra inferior (logs e información)
        bottom_widget = self.create_bottom_panel()
        main_layout.addWidget(bottom_widget)
        
        # 4. Barra de estado
        self.setup_status_bar()
    
    def create_chart_panel(self):
        """Crear panel del gráfico."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título del gráfico
        self.lbl_chart_title = QLabel("📊 US500 - 1H (Modo Demo)")
        self.lbl_chart_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                background-color: #1a1a1a;
                border-bottom: 1px solid #333;
            }
        """)
        self.lbl_chart_title.setAlignment(Qt.AlignCenter)
        
        # Área del gráfico
        if ChartView and IMPORT_SUCCESS:
            try:
                self.chart_view = ChartView()
                self.log_message("✅ ChartView cargado exitosamente")
                
                # Configurar tamaño mínimo
                self.chart_view.setMinimumSize(800, 500)
                
                # Conectar señales del chart view
                if hasattr(self.chart_view, 'symbol_changed'):
                    self.chart_view.symbol_changed.connect(self.on_symbol_changed)
                if hasattr(self.chart_view, 'timeframe_changed'):
                    self.chart_view.timeframe_changed.connect(self.on_timeframe_changed)
                
            except Exception as e:
                self.log_message(f"⚠️ Error creando ChartView: {str(e)}")
                self.chart_view = self.create_chart_placeholder()
        else:
            self.chart_view = self.create_chart_placeholder()
            self.log_message("⚠️ ChartView no disponible - usando placeholder")
        
        # Panel de precios en tiempo real
        price_panel = self.create_price_panel()
        
        # Agregar al layout
        layout.addWidget(self.lbl_chart_title)
        layout.addWidget(self.chart_view, 1)  # 1 = stretch
        layout.addWidget(price_panel)
        
        return widget
    
    def create_chart_placeholder(self):
        """Crear placeholder para el gráfico."""
        placeholder = QLabel(
            "<center><h3>📈 Gráfico con Indicadores Técnicos</h3>"
            "<p>Conecte a MT5 para ver datos reales</p>"
            "<p><small>Modo Demo: Mostrando datos de prueba</small></p></center>"
        )
        placeholder.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                color: #888;
                font-family: monospace;
                border: 2px dashed #444;
                border-radius: 8px;
                padding: 50px;
            }
        """)
        placeholder.setAlignment(Qt.AlignCenter)
        return placeholder
    
    def create_control_panel(self):
        """Crear panel de control lateral."""
        # Si ControlPanel existe, usarlo
        if ControlPanel and IMPORT_SUCCESS:
            try:
                self.control_panel = ControlPanel()
                self.log_message("✅ ControlPanel cargado exitosamente")
                return self.control_panel
            except Exception as e:
                self.log_message(f"⚠️ Error creando ControlPanel: {str(e)}")
                return self.create_basic_control_panel()
        else:
            self.log_message("⚠️ ControlPanel no disponible - usando versión básica")
            return self.create_basic_control_panel()
    
    def create_basic_control_panel(self):
        """Crear panel de control básico."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Pestañas
        self.tab_widget = QTabWidget()
        
        # 1. Pestaña de Trading
        trading_tab = self.create_trading_tab()
        self.tab_widget.addTab(trading_tab, "📊 Trading")
        
        # 2. Pestaña de Indicadores (NUEVA)
        indicators_tab = self.create_indicators_tab()
        self.tab_widget.addTab(indicators_tab, "📈 Indicadores")
        
        # 3. Pestaña de Posiciones
        positions_tab = self.create_positions_tab()
        self.tab_widget.addTab(positions_tab, "💰 Posiciones")
        
        # 4. Pestaña de Cuenta
        account_tab = self.create_account_tab()
        self.tab_widget.addTab(account_tab, "👤 Cuenta")
        
        layout.addWidget(self.tab_widget)
        
        return widget
    
    def create_indicators_tab(self):
        """Crear pestaña de configuración de indicadores."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Grupo de indicadores
        group_indicators = QGroupBox("Configuración de Indicadores Técnicos")
        indicators_layout = QGridLayout(group_indicators)
        
        # SMA
        indicators_layout.addWidget(QLabel("SMA (20):"), 0, 0)
        self.cb_sma = QComboBox()
        self.cb_sma.addItems(["Desactivado", "Activo"])
        self.cb_sma.setCurrentText("Activo")
        self.cb_sma.currentTextChanged.connect(self.on_indicator_changed)
        indicators_layout.addWidget(self.cb_sma, 0, 1)
        
        # EMA
        indicators_layout.addWidget(QLabel("EMA (12):"), 1, 0)
        self.cb_ema = QComboBox()
        self.cb_ema.addItems(["Desactivado", "Activo"])
        self.cb_ema.setCurrentText("Activo")
        self.cb_ema.currentTextChanged.connect(self.on_indicator_changed)
        indicators_layout.addWidget(self.cb_ema, 1, 1)
        
        # RSI
        indicators_layout.addWidget(QLabel("RSI (14):"), 2, 0)
        self.cb_rsi = QComboBox()
        self.cb_rsi.addItems(["Desactivado", "Activo"])
        self.cb_rsi.setCurrentText("Activo")
        self.cb_rsi.currentTextChanged.connect(self.on_indicator_changed)
        indicators_layout.addWidget(self.cb_rsi, 2, 1)
        
        # MACD
        indicators_layout.addWidget(QLabel("MACD:"), 3, 0)
        self.cb_macd = QComboBox()
        self.cb_macd.addItems(["Desactivado", "Activo"])
        self.cb_macd.setCurrentText("Activo")
        self.cb_macd.currentTextChanged.connect(self.on_indicator_changed)
        indicators_layout.addWidget(self.cb_macd, 3, 1)
        
        # Bollinger Bands
        indicators_layout.addWidget(QLabel("Bollinger:"), 4, 0)
        self.cb_bb = QComboBox()
        self.cb_bb.addItems(["Desactivado", "Activo"])
        self.cb_bb.setCurrentText("Activo")
        self.cb_bb.currentTextChanged.connect(self.on_indicator_changed)
        indicators_layout.addWidget(self.cb_bb, 4, 1)
        
        # Botón para aplicar indicadores
        self.btn_apply_indicators = QPushButton("✅ Aplicar Indicadores al Gráfico")
        self.btn_apply_indicators.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                margin-top: 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.btn_apply_indicators.clicked.connect(self.apply_indicators)
        
        # Información de indicadores
        self.lbl_indicators_info = QLabel("Indicadores: SMA, EMA, RSI, MACD, Bollinger activados")
        self.lbl_indicators_info.setStyleSheet("""
            QLabel {
                color: #0af;
                font-style: italic;
                padding: 10px;
                background-color: #1a1a1a;
                border-radius: 5px;
                border: 1px solid #333;
            }
        """)
        
        # Agregar al layout
        indicators_layout.addWidget(self.btn_apply_indicators, 5, 0, 1, 2)
        indicators_layout.addWidget(self.lbl_indicators_info, 6, 0, 1, 2)
        
        layout.addWidget(group_indicators)
        layout.addStretch()
        
        return widget
    
    def on_indicator_changed(self):
        """Manejador para cambio en configuración de indicadores."""
        # Actualizar configuración local
        self.indicators_config['sma']['enabled'] = (self.cb_sma.currentText() == "Activo")
        self.indicators_config['ema']['enabled'] = (self.cb_ema.currentText() == "Activo")
        self.indicators_config['rsi']['enabled'] = (self.cb_rsi.currentText() == "Activo")
        self.indicators_config['macd']['enabled'] = (self.cb_macd.currentText() == "Activo")
        self.indicators_config['bollinger']['enabled'] = (self.cb_bb.currentText() == "Activo")
        
        # Actualizar etiqueta de información
        active_indicators = []
        if self.indicators_config['sma']['enabled']: active_indicators.append("SMA")
        if self.indicators_config['ema']['enabled']: active_indicators.append("EMA")
        if self.indicators_config['rsi']['enabled']: active_indicators.append("RSI")
        if self.indicators_config['macd']['enabled']: active_indicators.append("MACD")
        if self.indicators_config['bollinger']['enabled']: active_indicators.append("BB")
        
        if active_indicators:
            self.lbl_indicators_info.setText(f"Indicadores activos: {', '.join(active_indicators)}")
        else:
            self.lbl_indicators_info.setText("Ningún indicador activado")
        
        self.log_message(f"⚙️ Configuración de indicadores actualizada")
    
    def apply_indicators(self):
        """Aplicar configuración de indicadores al gráfico."""
        try:
            # Emitir señal con configuración actualizada
            self.indicators_updated.emit(self.indicators_config)
            
            # Si tenemos ChartView, actualizarlo directamente
            if hasattr(self, 'chart_view') and isinstance(self.chart_view, ChartView):
                self.chart_view.update_indicator_settings(self.indicators_config)
                
                # Refrescar gráfico
                if hasattr(self, 'is_connected') and self.is_connected:
                    self.refresh_data()
                else:
                    # Usar datos demo
                    self.chart_view.update_chart(self.demo_candles, self.indicators_config)
            
            self.log_message("✅ Indicadores aplicados al gráfico")
            
            # Contar indicadores activos
            active_count = sum(1 for ind in self.indicators_config.values() if ind['enabled'])
            self.log_message(f"📊 {active_count} indicadores activos")
            
        except Exception as e:
            self.log_message(f"❌ Error aplicando indicadores: {str(e)}")
    
    def on_indicators_updated(self, indicator_configs):
        """Manejador para señal de indicadores actualizados desde control panel."""
        try:
            self.log_message("📈 Recibiendo configuración de indicadores...")
            
            # Actualizar configuración local
            self.indicators_config = indicator_configs
            
            # Aplicar al gráfico
            if hasattr(self, 'chart_view') and isinstance(self.chart_view, ChartView):
                self.chart_view.update_indicator_settings(self.indicators_config)
                
                # Refrescar datos
                if self.is_connected:
                    self.refresh_data()
                else:
                    self.chart_view.update_chart(self.demo_candles, self.indicators_config)
                
                # Activar botón de indicadores si existe
                if hasattr(self.chart_view, 'btn_toggle_indicators'):
                    self.chart_view.btn_toggle_indicators.setChecked(True)
            
            self.log_message("✅ Indicadores actualizados desde ControlPanel")
            
        except Exception as e:
            self.log_message(f"❌ Error en on_indicators_updated: {str(e)}")
    
    def toggle_connection(self):
        """Alternar conexión a MT5."""
        if self.is_connected:
            self.disconnect_from_mt5()
        else:
            self.connect_to_mt5()
    
    def connect_to_mt5(self):
        """Conectar a MT5."""
        try:
            self.log_message("🔌 Conectando a MT5...")
            self.btn_connect.setEnabled(False)
            self.btn_connect.setText("Conectando...")
            
            # Usar casos de uso si están disponibles
            if IMPORT_SUCCESS:
                self.mt5_use_case = create_connect_to_mt5_use_case(max_retries=3)
                result = self.mt5_use_case.connect()
                
                if result.get('success', False):
                    self.is_connected = True
                    
                    # Obtener información del servidor
                    server_info = result.get('data', {}).get('server_info', 'Desconocido')
                    if not server_info:
                        server_info = result.get('data', {}).get('account_info', {}).get('server', 'Desconocido')
                    
                    self.server_name = server_info
                    
                    # Actualizar UI
                    self.update_connection_status(True, f"Conectado a {server_info}")
                    
                    # Crear caso de uso de datos
                    self.data_use_case = create_fetch_market_data_use_case(self.mt5_use_case)
                    
                    # Actualizar información de cuenta
                    self.update_account_display(result.get('data', {}).get('account_info', {}))
                    
                    # Refrescar datos
                    self.refresh_data()
                    
                    # Aplicar indicadores a datos reales
                    self.apply_indicators()
                    
                    self.log_message(f"✅ Conexión exitosa a MT5")
                else:
                    self.update_connection_status(False, f"Error: {result.get('message', 'Desconocido')}")
                    self.log_message(f"❌ Error de conexión: {result.get('message', 'Desconocido')}")
            
            else:
                # Simular conexión exitosa para demo
                self.is_connected = True
                self.update_connection_status(True, "Modo Demo Activado")
                self.log_message("✅ Modo Demo: Simulando conexión a MT5")
                self.log_message("💡 Para datos reales, instale MetaTrader5")
                
                # Simular información de cuenta demo
                demo_account = {
                    'login': '12345678',
                    'name': 'Demo Account',
                    'server': 'Demo-Server',
                    'currency': 'USD',
                    'leverage': 100,
                    'balance': 10000.00,
                    'equity': 10500.00,
                    'margin': 1500.00,
                    'free_margin': 9000.00,
                    'margin_level': 700.0
                }
                self.update_account_display(demo_account)
                
                # Simular algunas posiciones
                demo_positions = [
                    {'ticket': 1001, 'symbol': 'EURUSD', 'type': 0, 'volume': 0.1, 'price_open': 1.0850, 'profit': 25.50},
                    {'ticket': 1002, 'symbol': 'US500', 'type': 1, 'volume': 0.05, 'price_open': 5100.0, 'profit': -12.75}
                ]
                self.update_positions_display(demo_positions)
                
        except Exception as e:
            self.update_connection_status(False, f"Excepción: {str(e)}")
            self.log_message(f"❌ Excepción en conexión: {str(e)}")
        finally:
            self.btn_connect.setEnabled(True)
            if self.is_connected:
                self.btn_connect.setText("🔌 Desconectar")
            else:
                self.btn_connect.setText("🔌 Conectar a MT5")
    
    def disconnect_from_mt5(self):
        """Desconectar de MT5."""
        try:
            if self.mt5_use_case:
                self.mt5_use_case.disconnect()
            
            self.is_connected = False
            self.update_connection_status(False, "Desconectado")
            
            # Volver a datos demo
            self.load_demo_data()
            
            self.log_message("🔌 Desconectado de MT5")
            
        except Exception as e:
            self.log_message(f"⚠️ Error al desconectar: {str(e)}")
    
    def refresh_data(self):
        """Refrescar datos del mercado."""
        try:
            if self.is_connected and self.data_use_case:
                self.log_message("🔄 Actualizando datos de mercado...")
                
                # Obtener datos históricos
                result = self.data_use_case.get_historical_data(
                    symbol=self.current_symbol,
                    timeframe=self.current_timeframe,
                    count=100
                )
                
                if result.get('success', False):
                    data = result.get('data', [])
                    symbol_info = result.get('symbol_info', {})
                    
                    # Actualizar gráfico
                    if hasattr(self, 'chart_view') and isinstance(self.chart_view, ChartView):
                        self.chart_view.update_chart(data, self.indicators_config)
                    
                    # Actualizar título
                    self.update_chart_title(self.current_symbol, self.current_timeframe, len(data))
                    
                    self.log_message(f"✅ Datos actualizados: {len(data)} velas")
                    
                    # Obtener datos en tiempo real
                    real_time_result = self.data_use_case.get_real_time_data(self.current_symbol)
                    if real_time_result.get('success', False):
                        price_data = real_time_result.get('data', {})
                        self.update_price_display(
                            price_data.get('bid', 0),
                            price_data.get('ask', 0),
                            price_data.get('spread', 0)
                        )
                else:
                    self.log_message(f"❌ Error obteniendo datos: {result.get('message', 'Desconocido')}")
            
            elif not self.is_connected:
                # Usar datos demo
                self.load_demo_data()
                
        except Exception as e:
            self.log_message(f"❌ Error refrescando datos: {str(e)}")
    
    def refresh_positions(self):
        """Refrescar posiciones."""
        if self.is_connected:
            self.log_message("🔄 Actualizando posiciones...")
            # Aquí iría la lógica real para obtener posiciones
        else:
            # Simular actualización en modo demo
            self.log_message("ℹ️ Modo Demo: Simulando actualización de posiciones")
    
    def on_trading_action(self, action):
        """Manejador para acciones de trading."""
        if action == 'buy':
            self.log_message("📤 Orden de COMPRA enviada (simulación)")
        elif action == 'sell':
            self.log_message("📤 Orden de VENTA enviada (simulación)")
    
    def on_trading_signal(self, order_details):
        """Manejador para señales de trading desde control panel."""
        action = "COMPRA" if 'buy' in str(order_details).lower() else "VENTA"
        self.log_message(f"📤 Señal de {action} recibida: {order_details}")
    
    # Mantén los métodos restantes igual que en tu versión original...
    # (create_top_bar, create_price_panel, create_trading_tab, etc.)
    # Solo asegúrate de que update_connection_status, update_price_display,
    # update_account_display, update_positions_display, update_chart_title,
    # log_message y closeEvent estén presentes.

    # ... (el resto de los métodos se mantienen igual que en tu código original)