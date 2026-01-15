# src/presentation/main_window.py
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QTextEdit, QTabWidget,
                             QSplitter, QGroupBox, QGridLayout, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

# Importaciones de tu proyecto
from src.application.use_cases.connect_to_mt5 import create_connect_to_mt5_use_case
from src.application.use_cases.fetch_market_data import create_fetch_market_data_use_case
from src.config import settings


class MainWindow(QMainWindow):
    """Ventana principal de la plataforma de trading."""
    
    # Señales para comunicación entre hilos
    connection_status_changed = pyqtSignal(bool, str)
    data_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Inicializar casos de uso
        self.mt5_use_case = None
        self.data_use_case = None
        
        # Estado de la aplicación
        self.is_connected = False
        self.current_symbol = settings.DEFAULT_SYMBOL
        self.current_timeframe = "1H"
        
        # Configurar UI
        self.setup_ui()
        self.setup_timers()
        
        # Intentar conexión automática si está configurado
        if hasattr(settings, 'AUTO_CONNECT') and settings.AUTO_CONNECT:
            QTimer.singleShot(1000, self.connect_to_mt5)
    
    def setup_ui(self):
        """Configurar la interfaz de usuario."""
        self.setWindowTitle("US500 Trading Platform")
        self.setGeometry(100, 100, 1400, 800)
        
        # Tema oscuro
        self.set_dark_theme()
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 1. Barra superior (conexión y símbolos)
        top_bar = self.create_top_bar()
        main_layout.addLayout(top_bar)
        
        # 2. Área principal dividida
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo (gráfico - placeholder)
        left_panel = self.create_chart_panel()
        splitter.addWidget(left_panel)
        
        # Panel derecho (control)
        right_panel = self.create_control_panel()
        splitter.addWidget(right_panel)
        
        # Configurar tamaños relativos
        splitter.setSizes([1000, 400])
        
        main_layout.addWidget(splitter)
        
        # 3. Barra inferior (logs)
        log_widget = self.create_log_widget()
        main_layout.addWidget(log_widget)
        
        # 4. Barra de estado
        self.setup_status_bar()
    
    def set_dark_theme(self):
        """Aplicar tema oscuro a la aplicación."""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(dark_palette)
    
    def create_top_bar(self):
        """Crear barra superior con controles de conexión."""
        layout = QHBoxLayout()
        
        # Botón de conexión
        self.btn_connect = QPushButton("🔌 Conectar a MT5")
        self.btn_connect.setFixedWidth(150)
        self.btn_connect.clicked.connect(self.connect_to_mt5)
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        
        # Estado de conexión
        self.lbl_connection_status = QLabel("❌ Desconectado")
        self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #ff6b6b;")
        
        # Selector de símbolo
        self.cmb_symbol = QComboBox()
        self.cmb_symbol.addItems(["US500", "EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"])
        self.cmb_symbol.setCurrentText(self.current_symbol)
        self.cmb_symbol.currentTextChanged.connect(self.on_symbol_changed)
        self.cmb_symbol.setFixedWidth(100)
        
        # Selector de timeframe
        self.cmb_timeframe = QComboBox()
        self.cmb_timeframe.addItems(["1M", "5M", "15M", "30M", "1H", "4H", "1D", "1W"])
        self.cmb_timeframe.setCurrentText(self.current_timeframe)
        self.cmb_timeframe.currentTextChanged.connect(self.on_timeframe_changed)
        self.cmb_timeframe.setFixedWidth(80)
        
        # Botón de actualizar
        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_refresh.setEnabled(False)
        
        # Etiqueta de cuenta
        self.lbl_account = QLabel("Cuenta: --")
        self.lbl_account.setStyleSheet("color: #aaa;")
        
        # Agregar widgets al layout
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.lbl_connection_status)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Símbolo:"))
        layout.addWidget(self.cmb_symbol)
        layout.addWidget(QLabel("TF:"))
        layout.addWidget(self.cmb_timeframe)
        layout.addWidget(self.btn_refresh)
        layout.addStretch()
        layout.addWidget(self.lbl_account)
        
        return layout
    
    def create_chart_panel(self):
        """Crear panel del gráfico (placeholder)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título del gráfico
        self.lbl_chart_title = QLabel(f"Gráfico: {self.current_symbol} - {self.current_timeframe}")
        self.lbl_chart_title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.lbl_chart_title.setAlignment(Qt.AlignCenter)
        
        # Área del gráfico (placeholder)
        self.lbl_chart_placeholder = QLabel(
            "<center><h3>Gráfico de Velas</h3>"
            "<p>Para mostrar el gráfico, instale pyqtgraph:</p>"
            "<code>pip install pyqtgraph</code></center>"
        )
        self.lbl_chart_placeholder.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px dashed #444;
                border-radius: 8px;
                color: #888;
                font-family: monospace;
                padding: 40px;
            }
        """)
        self.lbl_chart_placeholder.setAlignment(Qt.AlignCenter)
        
        # Información de precios
        price_widget = QWidget()
        price_layout = QHBoxLayout(price_widget)
        
        self.lbl_bid = QLabel("Bid: --")
        self.lbl_ask = QLabel("Ask: --")
        self.lbl_spread = QLabel("Spread: --")
        self.lbl_change = QLabel("Cambio: --")
        
        for lbl in [self.lbl_bid, self.lbl_ask, self.lbl_spread, self.lbl_change]:
            lbl.setStyleSheet("font-family: monospace; font-size: 14px; padding: 5px 15px;")
            price_layout.addWidget(lbl)
        
        price_layout.addStretch()
        
        # Agregar al layout principal
        layout.addWidget(self.lbl_chart_title)
        layout.addWidget(self.lbl_chart_placeholder, 1)
        layout.addWidget(price_widget)
        
        return widget
    
    def create_control_panel(self):
        """Crear panel de control lateral."""
        tab_widget = QTabWidget()
        
        # 1. Pestaña de Trading
        trading_tab = self.create_trading_tab()
        tab_widget.addTab(trading_tab, "📊 Trading")
        
        # 2. Pestaña de Posiciones
        positions_tab = self.create_positions_tab()
        tab_widget.addTab(positions_tab, "💰 Posiciones")
        
        # 3. Pestaña de Configuración
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "⚙️ Config")
        
        # 4. Pestaña de Logs
        log_tab = self.create_log_tab()
        tab_widget.addTab(log_tab, "📝 Logs")
        
        return tab_widget
    
    def create_trading_tab(self):
        """Crear pestaña de trading."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Grupo de operación
        group_trade = QGroupBox("Operación Rápida")
        group_layout = QGridLayout(group_trade)
        
        # Volumen
        group_layout.addWidget(QLabel("Volumen:"), 0, 0)
        self.cmb_volume = QComboBox()
        self.cmb_volume.addItems(["0.01", "0.1", "0.5", "1.0", "2.0", "5.0"])
        self.cmb_volume.setCurrentText("0.1")
        group_layout.addWidget(self.cmb_volume, 0, 1)
        
        # SL y TP
        group_layout.addWidget(QLabel("SL (pips):"), 1, 0)
        self.spin_sl = QComboBox()
        self.spin_sl.addItems(["10", "20", "50", "100", "200"])
        self.spin_sl.setCurrentText("50")
        group_layout.addWidget(self.spin_sl, 1, 1)
        
        group_layout.addWidget(QLabel("TP (pips):"), 2, 0)
        self.spin_tp = QComboBox()
        self.spin_tp.addItems(["20", "50", "100", "200", "500"])
        self.spin_tp.setCurrentText("100")
        group_layout.addWidget(self.spin_tp, 2, 1)
        
        # Botones de operación
        self.btn_buy = QPushButton("🟢 COMPRAR")
        self.btn_buy.setStyleSheet("""
            QPushButton {
                background-color: #00a86b;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #00b87b;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.btn_buy.clicked.connect(lambda: self.open_position("buy"))
        self.btn_buy.setEnabled(False)
        
        self.btn_sell = QPushButton("🔴 VENDER")
        self.btn_sell.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ff5555;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.btn_sell.clicked.connect(lambda: self.open_position("sell"))
        self.btn_sell.setEnabled(False)
        
        group_layout.addWidget(self.btn_buy, 3, 0, 1, 2)
        group_layout.addWidget(self.btn_sell, 4, 0, 1, 2)
        
        # Grupo de información de cuenta
        group_account = QGroupBox("Información de Cuenta")
        account_layout = QVBoxLayout(group_account)
        
        self.lbl_balance = QLabel("Balance: --")
        self.lbl_equity = QLabel("Equity: --")
        self.lbl_margin = QLabel("Margen: --")
        self.lbl_free_margin = QLabel("Margen Libre: --")
        self.lbl_margin_level = QLabel("Nivel de Margen: --")
        
        for lbl in [self.lbl_balance, self.lbl_equity, self.lbl_margin, 
                   self.lbl_free_margin, self.lbl_margin_level]:
            lbl.setStyleSheet("font-family: monospace; padding: 3px;")
            account_layout.addWidget(lbl)
        
        account_layout.addStretch()
        
        # Agregar grupos al layout
        layout.addWidget(group_trade)
        layout.addWidget(group_account)
        layout.addStretch()
        
        return widget
    
    def create_positions_tab(self):
        """Crear pestaña de posiciones."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Lista de posiciones (placeholder)
        self.txt_positions = QTextEdit()
        self.txt_positions.setReadOnly(True)
        self.txt_positions.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        self.txt_positions.setPlaceholderText("No hay posiciones abiertas...")
        
        # Botón de actualizar posiciones
        self.btn_refresh_positions = QPushButton("🔄 Actualizar Posiciones")
        self.btn_refresh_positions.clicked.connect(self.refresh_positions)
        self.btn_refresh_positions.setEnabled(False)
        
        layout.addWidget(self.txt_positions)
        layout.addWidget(self.btn_refresh_positions)
        
        return widget
    
    def create_config_tab(self):
        """Crear pestaña de configuración."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Información de configuración
        info_text = f"""
        <h3>Configuración MT5</h3>
        <p><b>Servidor:</b> {getattr(settings, 'MT5_SERVER', 'No configurado')}</p>
        <p><b>Login:</b> {getattr(settings, 'MT5_LOGIN', 'No configurado')}</p>
        <p><b>Símbolo por defecto:</b> {getattr(settings, 'DEFAULT_SYMBOL', 'No configurado')}</p>
        <p><b>Símbolo alternativo:</b> {getattr(settings, 'FALLBACK_SYMBOL', 'No configurado')}</p>
        <hr>
        <p>Edite <code>src/config/settings.py</code> para cambiar la configuración.</p>
        """
        
        lbl_info = QLabel(info_text)
        lbl_info.setWordWrap(True)
        
        layout.addWidget(lbl_info)
        layout.addStretch()
        
        return widget
    
    def create_log_tab(self):
        """Crear pestaña de logs."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("""
            QTextEdit {
                background-color: #000;
                color: #0f0;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #333;
            }
        """)
        
        layout.addWidget(self.txt_logs)
        
        return widget
    
    def create_log_widget(self):
        """Crear widget de log en la parte inferior."""
        widget = QTextEdit()
        widget.setMaximumHeight(100)
        widget.setReadOnly(True)
        widget.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ccc;
                font-family: monospace;
                font-size: 10px;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        widget.setPlaceholderText("Logs de la aplicación...")
        
        self.txt_mini_log = widget
        return widget
    
    def setup_status_bar(self):
        """Configurar barra de estado."""
        self.statusBar().showMessage("Listo")
        
        # Etiquetas de estado
        self.lbl_status_data = QLabel("Datos: Esperando conexión")
        self.lbl_status_time = QLabel("--:--:--")
        
        self.statusBar().addPermanentWidget(self.lbl_status_data)
        self.statusBar().addPermanentWidget(self.lbl_status_time)
    
    def setup_timers(self):
        """Configurar timers para actualizaciones periódicas."""
        # Timer para actualizar hora
        self.timer_clock = QTimer()
        self.timer_clock.timeout.connect(self.update_clock)
        self.timer_clock.start(1000)
        
        # Timer para actualizar precios (si está conectado)
        self.timer_prices = QTimer()
        self.timer_prices.timeout.connect(self.update_prices)
        self.timer_prices.setInterval(2000)  # 2 segundos
    
    def update_clock(self):
        """Actualizar reloj en la barra de estado."""
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        self.lbl_status_time.setText(current_time)
    
    # ===== MÉTODOS DE CONEXIÓN =====
    
    def connect_to_mt5(self):
        """Conectar a MT5."""
        self.log_message("🔌 Intentando conectar a MT5...")
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Conectando...")
        
        try:
            # Crear caso de uso
            self.mt5_use_case = create_connect_to_mt5_use_case(max_retries=3)
            
            # Conectar - esto devuelve un DICCIONARIO
            result = self.mt5_use_case.connect()
            
            # CORRECTO: Usar notación de diccionario
            if result['success']:
                self.is_connected = True
                self.update_connection_status(True, "✅ Conectado a MT5")
                
                # Crear caso de uso de datos
                self.data_use_case = create_fetch_market_data_use_case(self.mt5_use_case)
                
                # Habilitar controles
                self.btn_refresh.setEnabled(True)
                self.btn_buy.setEnabled(True)
                self.btn_sell.setEnabled(True)
                self.btn_refresh_positions.setEnabled(True)
                
                # Actualizar información de cuenta
                self.update_account_info()
                
                # Iniciar actualización de precios
                self.timer_prices.start()
                self.refresh_data()
                
                self.log_message(f"✅ Conectado exitosamente a MT5")
                # CORREGIDO: Usar ['data'] en lugar de .details
                self.log_message(f"   Servidor: {result['data'].get('server', 'N/A')}")
                self.log_message(f"   Cuenta: {result['data'].get('account_info', {}).get('login', 'N/A')}")
            else:
                # CORREGIDO: Usar ['message'] en lugar de .message
                self.update_connection_status(False, f"❌ Error: {result['message']}")
                self.log_message(f"❌ Error de conexión: {result['message']}")
                
        except Exception as e:
            self.update_connection_status(False, f"❌ Excepción: {str(e)}")
            self.log_message(f"❌ Excepción en conexión: {str(e)}")
        finally:
            self.btn_connect.setEnabled(True)
            self.btn_connect.setText("🔌 Conectar a MT5")
    
    def disconnect_from_mt5(self):
        """Desconectar de MT5."""
        if self.mt5_use_case:
            self.mt5_use_case.disconnect()
            self.is_connected = False
            self.update_connection_status(False, "❌ Desconectado")
            self.timer_prices.stop()
            
            # Deshabilitar controles
            self.btn_refresh.setEnabled(False)
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(False)
            self.btn_refresh_positions.setEnabled(False)
            
            self.log_message("🔌 Desconectado de MT5")
    
    def update_connection_status(self, connected, message):
        """Actualizar estado de conexión en UI."""
        self.is_connected = connected
        self.lbl_connection_status.setText(message)
        
        if connected:
            self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #4cd964;")
            self.btn_connect.setText("🔌 Desconectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.disconnect_from_mt5)
        else:
            self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #ff6b6b;")
            self.btn_connect.setText("🔌 Conectar a MT5")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.connect_to_mt5)
    
    # ===== MÉTODOS DE DATOS =====
    
    def refresh_data(self):
        """Actualizar datos del mercado."""
        if not self.is_connected or not self.data_use_case:
            return
        
        try:
            # Obtener datos históricos
            result = self.data_use_case.get_historical_data(
                symbol=self.current_symbol,
                timeframe=self.current_timeframe,
                count=100
            )
            
            # Verificar si es diccionario u objeto
            if isinstance(result, dict):
                success = result.get('success', False)
                data = result.get('data', [])
                message = result.get('message', '')
                # quality puede no estar presente
                quality = result.get('quality', 'UNKNOWN')
            else:
                # Si es objeto con atributos
                success = getattr(result, 'success', False)
                data = getattr(result, 'data', [])
                message = getattr(result, 'message', '')
                quality = getattr(result, 'quality', 'UNKNOWN')
            
            if success:
                self.log_message(f"📊 Datos obtenidos: {len(data)} velas")
                
                # Actualizar información de precios en tiempo real
                self.update_prices()
                
                # Aquí iría la actualización del gráfico si tuvieras pyqtgraph
                # self.update_chart(data)
                
                # Actualizar título del gráfico
                self.lbl_chart_title.setText(f"Gráfico: {self.current_symbol} - {self.current_timeframe} ({len(data)} velas)")
                
                self.lbl_status_data.setText(f"Datos: {len(data)} velas | Calidad: {quality}")
            else:
                self.log_message(f"❌ Error obteniendo datos: {message}")
                
        except Exception as e:
            self.log_message(f"❌ Error refrescando datos: {str(e)}")
    
    def update_prices(self):
        """Actualizar precios en tiempo real."""
        if not self.is_connected or not self.data_use_case:
            return
        
        try:
            # Obtener datos en tiempo real
            result = self.data_use_case.get_real_time_data(self.current_symbol)
            
            # Verificar si es diccionario u objeto
            if isinstance(result, dict):
                success = result.get('success', False)
                data = result.get('data', {})
            else:
                success = getattr(result, 'success', False)
                data = getattr(result, 'data', {})
            
            if success:
                # Obtener valores de data de manera segura
                if isinstance(data, dict):
                    bid = data.get('bid', 0)
                    ask = data.get('ask', 0)
                    spread = data.get('spread', 0)
                    last_price = data.get('last_price', bid)
                else:
                    bid = getattr(data, 'bid', 0)
                    ask = getattr(data, 'ask', 0)
                    spread = getattr(data, 'spread', 0)
                    last_price = getattr(data, 'last_price', bid)
                
                # Actualizar etiquetas
                self.lbl_bid.setText(f"Bid: {bid:.5f}")
                self.lbl_ask.setText(f"Ask: {ask:.5f}")
                self.lbl_spread.setText(f"Spread: {spread:.1f} pips")
                self.lbl_change.setText(f"Último: {last_price:.5f}")
                
        except Exception as e:
            self.log_message(f"❌ Error actualizando precios: {str(e)}")
    
    def update_account_info(self):
        """Actualizar información de la cuenta."""
        if not self.is_connected or not self.mt5_use_case:
            return
        
        try:
            # Obtener información de cuenta desde el caso de uso
            result = self.mt5_use_case.connect()  # Esto devuelve un diccionario
            
            # CORREGIDO: Usar notación de diccionario
            if result['success'] and 'account_info' in result['data']:
                acc_info = result['data']['account_info']
                
                # Actualizar etiquetas
                self.lbl_account.setText(f"Cuenta: {acc_info.get('login', '--')}")
                self.lbl_balance.setText(f"Balance: ${acc_info.get('balance', 0):.2f}")
                self.lbl_equity.setText(f"Equity: ${acc_info.get('equity', 0):.2f}")
                self.lbl_margin.setText(f"Margen: ${acc_info.get('margin', 0):.2f}")
                
                # Calcular margen libre
                margin = acc_info.get('margin', 0)
                equity = acc_info.get('equity', 0)
                free_margin = equity - margin if equity > margin else 0
                self.lbl_free_margin.setText(f"Margen Libre: ${free_margin:.2f}")
                
                # Calcular nivel de margen
                margin_level = (equity / margin * 100) if margin > 0 else 0
                self.lbl_margin_level.setText(f"Nivel de Margen: {margin_level:.1f}%")
                
        except Exception as e:
            self.log_message(f"❌ Error actualizando cuenta: {str(e)}")
    
    def refresh_positions(self):
        """Actualizar lista de posiciones."""
        if not self.is_connected:
            return
        
        # Placeholder - necesitarías implementar la obtención de posiciones
        self.txt_positions.setPlainText("Funcionalidad de posiciones no implementada completamente.\n\n"
                                       "Requiere completar el repositorio de órdenes MT5.")
    
    # ===== MÉTODOS DE TRADING =====
    
    def open_position(self, direction):
        """Abrir una posición (buy/sell)."""
        if not self.is_connected:
            QMessageBox.warning(self, "Error", "No hay conexión a MT5")
            return
        
        volume = float(self.cmb_volume.currentText())
        sl_pips = int(self.spin_sl.currentText())
        tp_pips = int(self.spin_tp.currentText())
        
        # Mostrar confirmación
        reply = QMessageBox.question(
            self, "Confirmar Operación",
            f"¿Abrir posición {direction.upper()}?\n\n"
            f"Símbolo: {self.current_symbol}\n"
            f"Volumen: {volume}\n"
            f"SL: {sl_pips} pips\n"
            f"TP: {tp_pips} pips",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.log_message(f"📤 Enviando orden {direction.upper()} para {self.current_symbol}...")
            # Aquí iría la lógica real para enviar la orden a MT5
            # Necesitarías implementar el caso de uso open_position
    
    # ===== MANEJADORES DE EVENTOS =====
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.log_message(f"📈 Símbolo cambiado a: {symbol}")
        if self.is_connected:
            self.refresh_data()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.current_timeframe = timeframe
        self.log_message(f"⏰ Timeframe cambiado a: {timeframe}")
        if self.is_connected:
            self.refresh_data()
    
    # ===== UTILIDADES =====
    
    def log_message(self, message):
        """Agregar mensaje a los logs."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Log principal
        self.txt_logs.append(log_entry)
        
        # Mini log (solo últimos mensajes)
        self.txt_mini_log.append(log_entry)
        
        # Mantener mini log limitado
        lines = self.txt_mini_log.toPlainText().split('\n')
        if len(lines) > 10:
            self.txt_mini_log.setPlainText('\n'.join(lines[-10:]))
        
        # Auto-scroll
        scrollbar = self.txt_logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Manejador para cerrar la ventana."""
        if self.is_connected:
            reply = QMessageBox.question(
                self, "Confirmar Salida",
                "¿Está seguro de que desea salir?\n\n"
                "Se desconectará de MT5 y se cerrará la aplicación.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.disconnect_from_mt5()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()