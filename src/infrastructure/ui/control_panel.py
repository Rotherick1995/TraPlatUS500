# src/infrastructure/ui/control_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QGridLayout, QTextEdit, QCheckBox, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
                             QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
import json


class ControlPanel(QWidget):
    """Panel de control para la plataforma de trading."""
    
    # Señales
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)  # {symbol, volume, sl, tp, comment}
    sell_requested = pyqtSignal(dict)  # {symbol, volume, sl, tp, comment}
    close_position = pyqtSignal(int)  # ticket
    refresh_positions = pyqtSignal()
    refresh_orders = pyqtSignal()
    settings_changed = pyqtSignal(dict)  # nuevas configuraciones
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado
        self.is_connected = False
        self.current_symbol = "EURUSD"
        self.account_info = {}
        self.positions = []
        self.pending_orders = []
        
        # Configuración por defecto
        self.default_volume = 0.1
        self.default_sl = 50
        self.default_tp = 100
        
        # Inicializar UI
        self.init_ui()
        self.init_timers()
        
        # Cargar configuración guardada
        self.load_settings()
    
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Crear pestañas
        self.tab_widget = QTabWidget()
        
        # Pestañas
        self.tab_trading = self.create_trading_tab()
        self.tab_positions = self.create_positions_tab()
        self.tab_orders = self.create_orders_tab()
        self.tab_account = self.create_account_tab()
        self.tab_settings = self.create_settings_tab()
        
        self.tab_widget.addTab(self.tab_trading, "📊 Trading")
        self.tab_widget.addTab(self.tab_positions, "💰 Posiciones")
        self.tab_widget.addTab(self.tab_orders, "⏳ Órdenes")
        self.tab_widget.addTab(self.tab_account, "👤 Cuenta")
        self.tab_widget.addTab(self.tab_settings, "⚙️ Config")
        
        layout.addWidget(self.tab_widget)
    
    def create_trading_tab(self):
        """Crear pestaña de trading."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 1. Grupo de conexión
        group_connection = QGroupBox("Conexión MT5")
        connection_layout = QGridLayout(group_connection)
        
        # Botón de conexión
        self.btn_connect = QPushButton("🔌 Conectar")
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        
        # Estado de conexión
        self.lbl_connection = QLabel("❌ Desconectado")
        self.lbl_connection.setStyleSheet("font-weight: bold; color: #ff6b6b;")
        
        # Información del servidor
        self.lbl_server = QLabel("Servidor: --")
        self.lbl_server.setStyleSheet("color: #aaa; font-size: 12px;")
        
        connection_layout.addWidget(self.btn_connect, 0, 0, 1, 2)
        connection_layout.addWidget(self.lbl_connection, 1, 0, 1, 2)
        connection_layout.addWidget(self.lbl_server, 2, 0, 1, 2)
        
        # 2. Grupo de símbolo
        group_symbol = QGroupBox("Símbolo y Timeframe")
        symbol_layout = QGridLayout(group_symbol)
        
        # Selector de símbolo
        symbol_layout.addWidget(QLabel("Símbolo:"), 0, 0)
        self.cmb_symbol = QComboBox()
        self.cmb_symbol.addItems(["EURUSD", "US500", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"])
        self.cmb_symbol.setCurrentText(self.current_symbol)
        self.cmb_symbol.currentTextChanged.connect(self.on_symbol_changed)
        symbol_layout.addWidget(self.cmb_symbol, 0, 1)
        
        # Selector de timeframe
        symbol_layout.addWidget(QLabel("Timeframe:"), 1, 0)
        self.cmb_timeframe = QComboBox()
        self.cmb_timeframe.addItems(["1M", "5M", "15M", "30M", "1H", "4H", "1D", "1W"])
        self.cmb_timeframe.setCurrentText("1H")
        self.cmb_timeframe.currentTextChanged.connect(self.on_timeframe_changed)
        symbol_layout.addWidget(self.cmb_timeframe, 1, 1)
        
        # Precio actual
        self.lbl_current_price = QLabel("Precio: --")
        self.lbl_current_price.setStyleSheet("font-weight: bold; font-size: 16px;")
        symbol_layout.addWidget(self.lbl_current_price, 2, 0, 1, 2)
        
        # 3. Grupo de operación rápida
        group_quick_trade = QGroupBox("Operación Rápida")
        trade_layout = QGridLayout(group_quick_trade)
        
        # Volumen
        trade_layout.addWidget(QLabel("Volumen:"), 0, 0)
        self.spin_volume = QDoubleSpinBox()
        self.spin_volume.setRange(0.01, 100.0)
        self.spin_volume.setSingleStep(0.01)
        self.spin_volume.setValue(self.default_volume)
        self.spin_volume.setDecimals(2)
        trade_layout.addWidget(self.spin_volume, 0, 1)
        
        # Stop Loss (pips)
        trade_layout.addWidget(QLabel("SL (pips):"), 1, 0)
        self.spin_sl = QSpinBox()
        self.spin_sl.setRange(0, 1000)
        self.spin_sl.setValue(self.default_sl)
        self.spin_sl.setSingleStep(10)
        trade_layout.addWidget(self.spin_sl, 1, 1)
        
        # Take Profit (pips)
        trade_layout.addWidget(QLabel("TP (pips):"), 2, 0)
        self.spin_tp = QSpinBox()
        self.spin_tp.setRange(0, 2000)
        self.spin_tp.setValue(self.default_tp)
        self.spin_tp.setSingleStep(10)
        trade_layout.addWidget(self.spin_tp, 2, 1)
        
        # Comentario
        trade_layout.addWidget(QLabel("Comentario:"), 3, 0)
        self.txt_comment = QLineEdit()
        self.txt_comment.setPlaceholderText("Operación manual")
        trade_layout.addWidget(self.txt_comment, 3, 1)
        
        # Botones de operación
        self.btn_buy = QPushButton("🟢 COMPRAR")
        self.btn_buy.setStyleSheet("""
            QPushButton {
                background-color: #00a86b;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 16px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #00b87b;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.btn_buy.clicked.connect(self.on_buy_clicked)
        self.btn_buy.setEnabled(False)
        
        self.btn_sell = QPushButton("🔴 VENDER")
        self.btn_sell.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #ff5555;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.btn_sell.clicked.connect(self.on_sell_clicked)
        self.btn_sell.setEnabled(False)
        
        trade_layout.addWidget(self.btn_buy, 4, 0, 1, 2)
        trade_layout.addWidget(self.btn_sell, 5, 0, 1, 2)
        
        # 4. Grupo de información rápida
        group_quick_info = QGroupBox("Información Rápida")
        info_layout = QVBoxLayout(group_quick_info)
        
        self.lbl_spread = QLabel("Spread: --")
        self.lbl_spread.setStyleSheet("color: #aaa;")
        
        self.lbl_daily_change = QLabel("Cambio diario: --")
        self.lbl_daily_change.setStyleSheet("color: #aaa;")
        
        self.lbl_high_low = QLabel("Alto/Bajo: --")
        self.lbl_high_low.setStyleSheet("color: #aaa;")
        
        info_layout.addWidget(self.lbl_spread)
        info_layout.addWidget(self.lbl_daily_change)
        info_layout.addWidget(self.lbl_high_low)
        info_layout.addStretch()
        
        # Agregar grupos al layout
        layout.addWidget(group_connection)
        layout.addWidget(group_symbol)
        layout.addWidget(group_quick_trade)
        layout.addWidget(group_quick_info)
        layout.addStretch()
        
        return widget
    
    def create_positions_tab(self):
        """Crear pestaña de posiciones."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Barra de botones
        button_layout = QHBoxLayout()
        
        self.btn_refresh_positions = QPushButton("🔄 Actualizar")
        self.btn_refresh_positions.clicked.connect(self.on_refresh_positions)
        self.btn_refresh_positions.setEnabled(False)
        
        self.btn_close_all = QPushButton("❌ Cerrar Todo")
        self.btn_close_all.clicked.connect(self.on_close_all_positions)
        self.btn_close_all.setEnabled(False)
        
        button_layout.addWidget(self.btn_refresh_positions)
        button_layout.addWidget(self.btn_close_all)
        button_layout.addStretch()
        
        # Tabla de posiciones
        self.table_positions = QTableWidget()
        self.table_positions.setColumnCount(8)
        self.table_positions.setHorizontalHeaderLabels([
            "Ticket", "Símbolo", "Tipo", "Volumen", 
            "Precio", "SL", "TP", "Profit"
        ])
        
        # Configurar tabla
        header = self.table_positions.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_positions.setAlternatingRowColors(True)
        self.table_positions.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Label de resumen
        self.lbl_positions_summary = QLabel("No hay posiciones abiertas")
        self.lbl_positions_summary.setStyleSheet("font-weight: bold; padding: 5px;")
        self.lbl_positions_summary.setAlignment(Qt.AlignCenter)
        
        layout.addLayout(button_layout)
        layout.addWidget(self.lbl_positions_summary)
        layout.addWidget(self.table_positions, 1)
        
        return widget
    
    def create_orders_tab(self):
        """Crear pestaña de órdenes pendientes."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Barra de botones
        button_layout = QHBoxLayout()
        
        self.btn_refresh_orders = QPushButton("🔄 Actualizar")
        self.btn_refresh_orders.clicked.connect(self.on_refresh_orders)
        self.btn_refresh_orders.setEnabled(False)
        
        self.btn_cancel_all = QPushButton("❌ Cancelar Todo")
        self.btn_cancel_all.clicked.connect(self.on_cancel_all_orders)
        self.btn_cancel_all.setEnabled(False)
        
        button_layout.addWidget(self.btn_refresh_orders)
        button_layout.addWidget(self.btn_cancel_all)
        button_layout.addStretch()
        
        # Tabla de órdenes
        self.table_orders = QTableWidget()
        self.table_orders.setColumnCount(8)
        self.table_orders.setHorizontalHeaderLabels([
            "Ticket", "Símbolo", "Tipo", "Volumen", 
            "Precio", "SL", "TP", "Comentario"
        ])
        
        # Configurar tabla
        header = self.table_orders.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_orders.setAlternatingRowColors(True)
        
        # Label de resumen
        self.lbl_orders_summary = QLabel("No hay órdenes pendientes")
        self.lbl_orders_summary.setStyleSheet("font-weight: bold; padding: 5px;")
        self.lbl_orders_summary.setAlignment(Qt.AlignCenter)
        
        layout.addLayout(button_layout)
        layout.addWidget(self.lbl_orders_summary)
        layout.addWidget(self.table_orders, 1)
        
        return widget
    
    def create_account_tab(self):
        """Crear pestaña de información de cuenta."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 1. Información básica
        group_basic = QGroupBox("Información de Cuenta")
        basic_layout = QGridLayout(group_basic)
        
        basic_layout.addWidget(QLabel("Login:"), 0, 0)
        self.lbl_login = QLabel("--")
        basic_layout.addWidget(self.lbl_login, 0, 1)
        
        basic_layout.addWidget(QLabel("Nombre:"), 1, 0)
        self.lbl_name = QLabel("--")
        basic_layout.addWidget(self.lbl_name, 1, 1)
        
        basic_layout.addWidget(QLabel("Servidor:"), 2, 0)
        self.lbl_account_server = QLabel("--")
        basic_layout.addWidget(self.lbl_account_server, 2, 1)
        
        basic_layout.addWidget(QLabel("Moneda:"), 3, 0)
        self.lbl_currency = QLabel("--")
        basic_layout.addWidget(self.lbl_currency, 3, 1)
        
        basic_layout.addWidget(QLabel("Apalancamiento:"), 4, 0)
        self.lbl_leverage = QLabel("--")
        basic_layout.addWidget(self.lbl_leverage, 4, 1)
        
        # 2. Información financiera
        group_financial = QGroupBox("Estado Financiero")
        financial_layout = QGridLayout(group_financial)
        
        financial_layout.addWidget(QLabel("Balance:"), 0, 0)
        self.lbl_balance = QLabel("$ --")
        self.lbl_balance.setStyleSheet("font-weight: bold; font-size: 16px; color: #fff;")
        financial_layout.addWidget(self.lbl_balance, 0, 1)
        
        financial_layout.addWidget(QLabel("Equity:"), 1, 0)
        self.lbl_equity = QLabel("$ --")
        self.lbl_equity.setStyleSheet("font-weight: bold; font-size: 16px; color: #fff;")
        financial_layout.addWidget(self.lbl_equity, 1, 1)
        
        financial_layout.addWidget(QLabel("Margen:"), 2, 0)
        self.lbl_margin = QLabel("$ --")
        financial_layout.addWidget(self.lbl_margin, 2, 1)
        
        financial_layout.addWidget(QLabel("Margen Libre:"), 3, 0)
        self.lbl_free_margin = QLabel("$ --")
        financial_layout.addWidget(self.lbl_free_margin, 3, 1)
        
        financial_layout.addWidget(QLabel("Nivel de Margen:"), 4, 0)
        self.lbl_margin_level = QLabel("--%")
        self.lbl_margin_level.setStyleSheet("font-weight: bold; font-size: 14px;")
        financial_layout.addWidget(self.lbl_margin_level, 4, 1)
        
        # Barra de progreso para nivel de margen
        self.progress_margin = QProgressBar()
        self.progress_margin.setRange(0, 1000)
        self.progress_margin.setTextVisible(True)
        self.progress_margin.setFormat("%v%%")
        financial_layout.addWidget(self.progress_margin, 5, 0, 1, 2)
        
        # 3. Estadísticas de trading
        group_stats = QGroupBox("Estadísticas")
        stats_layout = QGridLayout(group_stats)
        
        stats_layout.addWidget(QLabel("Posiciones:"), 0, 0)
        self.lbl_total_positions = QLabel("0")
        stats_layout.addWidget(self.lbl_total_positions, 0, 1)
        
        stats_layout.addWidget(QLabel("Órdenes:"), 1, 0)
        self.lbl_total_orders = QLabel("0")
        stats_layout.addWidget(self.lbl_total_orders, 1, 1)
        
        stats_layout.addWidget(QLabel("Profit Total:"), 2, 0)
        self.lbl_total_profit = QLabel("$ 0.00")
        stats_layout.addWidget(self.lbl_total_profit, 2, 1)
        
        stats_layout.addWidget(QLabel("Profit Hoy:"), 3, 0)
        self.lbl_daily_profit = QLabel("$ 0.00")
        stats_layout.addWidget(self.lbl_daily_profit, 3, 1)
        
        # Agregar grupos al layout
        layout.addWidget(group_basic)
        layout.addWidget(group_financial)
        layout.addWidget(group_stats)
        layout.addStretch()
        
        return widget
    
    def create_settings_tab(self):
        """Crear pestaña de configuración."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 1. Configuración de trading
        group_trading = QGroupBox("Configuración de Trading")
        trading_layout = QGridLayout(group_trading)
        
        # Volumen por defecto
        trading_layout.addWidget(QLabel("Volumen por defecto:"), 0, 0)
        self.spin_default_volume = QDoubleSpinBox()
        self.spin_default_volume.setRange(0.01, 100.0)
        self.spin_default_volume.setValue(self.default_volume)
        self.spin_default_volume.setDecimals(2)
        trading_layout.addWidget(self.spin_default_volume, 0, 1)
        
        # SL por defecto
        trading_layout.addWidget(QLabel("SL por defecto (pips):"), 1, 0)
        self.spin_default_sl = QSpinBox()
        self.spin_default_sl.setRange(0, 1000)
        self.spin_default_sl.setValue(self.default_sl)
        trading_layout.addWidget(self.spin_default_sl, 1, 1)
        
        # TP por defecto
        trading_layout.addWidget(QLabel("TP por defecto (pips):"), 2, 0)
        self.spin_default_tp = QSpinBox()
        self.spin_default_tp.setRange(0, 2000)
        self.spin_default_tp.setValue(self.default_tp)
        trading_layout.addWidget(self.spin_default_tp, 2, 1)
        
        # Auto-conexión
        self.cb_auto_connect = QCheckBox("Auto-conectar al iniciar")
        self.cb_auto_connect.setChecked(True)
        trading_layout.addWidget(self.cb_auto_connect, 3, 0, 1, 2)
        
        # Auto-refresh
        self.cb_auto_refresh = QCheckBox("Auto-actualizar posiciones")
        self.cb_auto_refresh.setChecked(True)
        trading_layout.addWidget(self.cb_auto_refresh, 4, 0, 1, 2)
        
        # 2. Configuración de riesgo
        group_risk = QGroupBox("Gestión de Riesgo")
        risk_layout = QGridLayout(group_risk)
        
        # Riesgo por operación (%)
        risk_layout.addWidget(QLabel("Riesgo máximo por operación (%):"), 0, 0)
        self.spin_max_risk = QDoubleSpinBox()
        self.spin_max_risk.setRange(0.1, 10.0)
        self.spin_max_risk.setValue(2.0)
        self.spin_max_risk.setDecimals(1)
        risk_layout.addWidget(self.spin_max_risk, 0, 1)
        
        # Margen mínimo requerido
        risk_layout.addWidget(QLabel("Margen mínimo requerido (%):"), 1, 0)
        self.spin_min_margin = QDoubleSpinBox()
        self.spin_min_margin.setRange(10.0, 100.0)
        self.spin_min_margin.setValue(30.0)
        self.spin_min_margin.setDecimals(1)
        risk_layout.addWidget(self.spin_min_margin, 1, 1)
        
        # 3. Botones de acción
        group_actions = QGroupBox("Acciones")
        actions_layout = QHBoxLayout(group_actions)
        
        self.btn_save_settings = QPushButton("💾 Guardar Configuración")
        self.btn_save_settings.clicked.connect(self.on_save_settings)
        
        self.btn_load_settings = QPushButton("📂 Cargar Configuración")
        self.btn_load_settings.clicked.connect(self.on_load_settings)
        
        self.btn_reset_settings = QPushButton("🔄 Restablecer")
        self.btn_reset_settings.clicked.connect(self.on_reset_settings)
        
        actions_layout.addWidget(self.btn_save_settings)
        actions_layout.addWidget(self.btn_load_settings)
        actions_layout.addWidget(self.btn_reset_settings)
        
        # Área de información
        self.txt_settings_info = QTextEdit()
        self.txt_settings_info.setReadOnly(True)
        self.txt_settings_info.setMaximumHeight(100)
        self.txt_settings_info.setPlaceholderText("Información de configuración...")
        
        # Agregar grupos al layout
        layout.addWidget(group_trading)
        layout.addWidget(group_risk)
        layout.addWidget(group_actions)
        layout.addWidget(self.txt_settings_info)
        layout.addStretch()
        
        return widget
    
    def init_timers(self):
        """Inicializar timers para actualizaciones."""
        # Timer para actualizar precios
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self.update_price_display)
        self.price_timer.setInterval(1000)  # 1 segundo
        
        # Timer para actualizar cuenta
        self.account_timer = QTimer()
        self.account_timer.timeout.connect(self.update_account_display)
        self.account_timer.setInterval(5000)  # 5 segundos
    
    # ===== MÉTODOS DE ESTADO =====
    
    def update_connection_status(self, connected, message="", server_info=""):
        """Actualizar estado de conexión."""
        self.is_connected = connected
        
        if connected:
            self.lbl_connection.setText("✅ Conectado")
            self.lbl_connection.setStyleSheet("font-weight: bold; color: #4cd964;")
            self.btn_connect.setText("🔌 Desconectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.on_disconnect_clicked)
            
            self.btn_buy.setEnabled(True)
            self.btn_sell.setEnabled(True)
            self.btn_refresh_positions.setEnabled(True)
            self.btn_refresh_orders.setEnabled(True)
            self.btn_close_all.setEnabled(True)
            self.btn_cancel_all.setEnabled(True)
            
            # Iniciar timers
            self.price_timer.start()
            self.account_timer.start()
        else:
            self.lbl_connection.setText("❌ Desconectado")
            self.lbl_connection.setStyleSheet("font-weight: bold; color: #ff6b6b;")
            self.btn_connect.setText("🔌 Conectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.on_connect_clicked)
            
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(False)
            self.btn_refresh_positions.setEnabled(False)
            self.btn_refresh_orders.setEnabled(False)
            self.btn_close_all.setEnabled(False)
            self.btn_cancel_all.setEnabled(False)
            
            # Detener timers
            self.price_timer.stop()
            self.account_timer.stop()
        
        if server_info:
            self.lbl_server.setText(f"Servidor: {server_info}")
    
    def update_account_info(self, account_info):
        """Actualizar información de cuenta."""
        self.account_info = account_info
        
        # Actualizar etiquetas
        self.lbl_login.setText(str(account_info.get('login', '--')))
        self.lbl_name.setText(account_info.get('name', '--'))
        self.lbl_account_server.setText(account_info.get('server', '--'))
        self.lbl_currency.setText(account_info.get('currency', '--'))
        self.lbl_leverage.setText(f"1:{account_info.get('leverage', '--')}")
        
        # Actualizar información financiera
        balance = account_info.get('balance', 0)
        equity = account_info.get('equity', 0)
        margin = account_info.get('margin', 0)
        free_margin = account_info.get('free_margin', 0)
        
        self.lbl_balance.setText(f"$ {balance:.2f}")
        self.lbl_equity.setText(f"$ {equity:.2f}")
        self.lbl_margin.setText(f"$ {margin:.2f}")
        self.lbl_free_margin.setText(f"$ {free_margin:.2f}")
        
        # Calcular nivel de margen
        margin_level = (equity / margin * 100) if margin > 0 else 0
        self.lbl_margin_level.setText(f"{margin_level:.1f}%")
        
        # Actualizar barra de progreso
        self.progress_margin.setValue(int(margin_level))
        
        # Colores según nivel de margen
        if margin_level < 100:
            self.progress_margin.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
        elif margin_level < 200:
            self.progress_margin.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")
        else:
            self.progress_margin.setStyleSheet("QProgressBar::chunk { background-color: #00aa00; }")
    
    def update_positions(self, positions):
        """Actualizar lista de posiciones."""
        self.positions = positions
        
        # Limpiar tabla
        self.table_positions.setRowCount(0)
        
        if not positions:
            self.lbl_positions_summary.setText("No hay posiciones abiertas")
            self.lbl_total_positions.setText("0")
            self.lbl_total_profit.setText("$ 0.00")
            return
        
        # Actualizar tabla
        total_profit = 0
        for i, pos in enumerate(positions):
            self.table_positions.insertRow(i)
            
            # Ticket
            self.table_positions.setItem(i, 0, QTableWidgetItem(str(pos.get('ticket', ''))))
            
            # Símbolo
            self.table_positions.setItem(i, 1, QTableWidgetItem(pos.get('symbol', '')))
            
            # Tipo (Buy/Sell)
            type_str = "COMPRA" if pos.get('type', 0) == 0 else "VENTA"
            type_item = QTableWidgetItem(type_str)
            type_item.setForeground(QColor('#00ff00') if type_str == "COMPRA" else QColor('#ff0000'))
            self.table_positions.setItem(i, 2, type_item)
            
            # Volumen
            self.table_positions.setItem(i, 3, QTableWidgetItem(str(pos.get('volume', 0))))
            
            # Precio de apertura
            self.table_positions.setItem(i, 4, QTableWidgetItem(f"{pos.get('price_open', 0):.5f}"))
            
            # SL y TP
            self.table_positions.setItem(i, 5, QTableWidgetItem(f"{pos.get('sl', 0):.5f}"))
            self.table_positions.setItem(i, 6, QTableWidgetItem(f"{pos.get('tp', 0):.5f}"))
            
            # Profit
            profit = pos.get('profit', 0)
            total_profit += profit
            profit_item = QTableWidgetItem(f"$ {profit:.2f}")
            profit_item.setForeground(QColor('#00ff00') if profit >= 0 else QColor('#ff0000'))
            self.table_positions.setItem(i, 7, profit_item)
        
        # Actualizar resumen
        self.lbl_positions_summary.setText(f"{len(positions)} posición(es) abierta(s)")
        self.lbl_total_positions.setText(str(len(positions)))
        
        # Actualizar profit total
        self.lbl_total_profit.setText(f"$ {total_profit:.2f}")
        if total_profit >= 0:
            self.lbl_total_profit.setStyleSheet("color: #00ff00; font-weight: bold;")
        else:
            self.lbl_total_profit.setStyleSheet("color: #ff0000; font-weight: bold;")
    
    def update_orders(self, orders):
        """Actualizar lista de órdenes pendientes."""
        self.pending_orders = orders
        
        # Limpiar tabla
        self.table_orders.setRowCount(0)
        
        if not orders:
            self.lbl_orders_summary.setText("No hay órdenes pendientes")
            self.lbl_total_orders.setText("0")
            return
        
        # Actualizar tabla
        for i, order in enumerate(orders):
            self.table_orders.insertRow(i)
            
            # Ticket
            self.table_orders.setItem(i, 0, QTableWidgetItem(str(order.get('ticket', ''))))
            
            # Símbolo
            self.table_orders.setItem(i, 1, QTableWidgetItem(order.get('symbol', '')))
            
            # Tipo de orden
            order_type = order.get('type', 0)
            type_map = {
                0: "BUY LIMIT",
                1: "SELL LIMIT",
                2: "BUY STOP",
                3: "SELL STOP"
            }
            type_str = type_map.get(order_type, "UNKNOWN")
            self.table_orders.setItem(i, 2, QTableWidgetItem(type_str))
            
            # Volumen
            self.table_orders.setItem(i, 3, QTableWidgetItem(str(order.get('volume', 0))))
            
            # Precio
            self.table_orders.setItem(i, 4, QTableWidgetItem(f"{order.get('price_open', 0):.5f}"))
            
            # SL y TP
            self.table_orders.setItem(i, 5, QTableWidgetItem(f"{order.get('sl', 0):.5f}"))
            self.table_orders.setItem(i, 6, QTableWidgetItem(f"{order.get('tp', 0):.5f}"))
            
            # Comentario
            self.table_orders.setItem(i, 7, QTableWidgetItem(order.get('comment', '')))
        
        # Actualizar resumen
        self.lbl_orders_summary.setText(f"{len(orders)} orden(es) pendiente(s)")
        self.lbl_total_orders.setText(str(len(orders)))
    
    def update_price_display(self, price_data=None):
        """Actualizar display de precios."""
        if price_data:
            # Actualizar precio actual
            current_price = price_data.get('bid', 0)
            self.lbl_current_price.setText(f"Precio: {current_price:.5f}")
            
            # Actualizar spread
            spread = price_data.get('spread', 0)
            self.lbl_spread.setText(f"Spread: {spread:.1f} pips")
            
            # Aquí podrías agregar más información de precios
            # como cambio diario, alto/bajo, etc.
    
    def update_account_display(self):
        """Actualizar display de cuenta (llamar periódicamente)."""
        if self.is_connected:
            # Emitir señal para refrescar información de cuenta
            self.refresh_positions.emit()
    
    # ===== MANEJADORES DE EVENTOS =====
    
    def on_connect_clicked(self):
        """Manejador para botón de conexión."""
        self.connect_requested.emit()
    
    def on_disconnect_clicked(self):
        """Manejador para botón de desconexión."""
        self.disconnect_requested.emit()
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.symbol_changed.emit(symbol)
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.timeframe_changed.emit(timeframe)
    
    def on_buy_clicked(self):
        """Manejador para botón de compra."""
        order_details = {
            'symbol': self.current_symbol,
            'volume': self.spin_volume.value(),
            'sl': self.spin_sl.value(),
            'tp': self.spin_tp.value(),
            'comment': self.txt_comment.text() or "Compra manual"
        }
        self.buy_requested.emit(order_details)
    
    def on_sell_clicked(self):
        """Manejador para botón de venta."""
        order_details = {
            'symbol': self.current_symbol,
            'volume': self.spin_volume.value(),
            'sl': self.spin_sl.value(),
            'tp': self.spin_tp.value(),
            'comment': self.txt_comment.text() or "Venta manual"
        }
        self.sell_requested.emit(order_details)
    
    def on_refresh_positions(self):
        """Manejador para refrescar posiciones."""
        self.refresh_positions.emit()
    
    def on_refresh_orders(self):
        """Manejador para refrescar órdenes."""
        self.refresh_orders.emit()
    
    def on_close_all_positions(self):
        """Manejador para cerrar todas las posiciones."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro de cerrar todas las posiciones?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Cerrar cada posición
            for position in self.positions:
                ticket = position.get('ticket')
                if ticket:
                    self.close_position.emit(ticket)
    
    def on_cancel_all_orders(self):
        """Manejador para cancelar todas las órdenes."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro de cancelar todas las órdenes pendientes?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Aquí necesitarías implementar la cancelación de órdenes
            QMessageBox.information(self, "Info", "Función por implementar")
    
    def on_save_settings(self):
        """Guardar configuración."""
        settings = {
            'default_volume': self.spin_default_volume.value(),
            'default_sl': self.spin_default_sl.value(),
            'default_tp': self.spin_default_tp.value(),
            'auto_connect': self.cb_auto_connect.isChecked(),
            'auto_refresh': self.cb_auto_refresh.isChecked(),
            'max_risk': self.spin_max_risk.value(),
            'min_margin': self.spin_min_margin.value()
        }
        
        try:
            with open('trading_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.txt_settings_info.append("✅ Configuración guardada exitosamente")
            self.settings_changed.emit(settings)
            
        except Exception as e:
            self.txt_settings_info.append(f"❌ Error guardando configuración: {str(e)}")
    
    def on_load_settings(self):
        """Cargar configuración."""
        try:
            with open('trading_settings.json', 'r') as f:
                settings = json.load(f)
            
            self.load_settings_from_dict(settings)
            self.txt_settings_info.append("✅ Configuración cargada exitosamente")
            
        except FileNotFoundError:
            self.txt_settings_info.append("ℹ️ No se encontró archivo de configuración")
        except Exception as e:
            self.txt_settings_info.append(f"❌ Error cargando configuración: {str(e)}")
    
    def on_reset_settings(self):
        """Restablecer configuración por defecto."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Restablecer configuración por defecto?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.spin_default_volume.setValue(0.1)
            self.spin_default_sl.setValue(50)
            self.spin_default_tp.setValue(100)
            self.cb_auto_connect.setChecked(True)
            self.cb_auto_refresh.setChecked(True)
            self.spin_max_risk.setValue(2.0)
            self.spin_min_margin.setValue(30.0)
            
            self.txt_settings_info.append("✅ Configuración restablecida")
    
    # ===== UTILIDADES =====
    
    def load_settings(self):
        """Cargar configuración al iniciar."""
        try:
            with open('trading_settings.json', 'r') as f:
                settings = json.load(f)
                self.load_settings_from_dict(settings)
        except:
            # Usar valores por defecto si no hay archivo
            pass
    
    def load_settings_from_dict(self, settings):
        """Cargar configuración desde diccionario."""
        self.spin_default_volume.setValue(settings.get('default_volume', 0.1))
        self.spin_default_sl.setValue(settings.get('default_sl', 50))
        self.spin_default_tp.setValue(settings.get('default_tp', 100))
        self.cb_auto_connect.setChecked(settings.get('auto_connect', True))
        self.cb_auto_refresh.setChecked(settings.get('auto_refresh', True))
        self.spin_max_risk.setValue(settings.get('max_risk', 2.0))
        self.spin_min_margin.setValue(settings.get('min_margin', 30.0))
        
        # Aplicar a controles de trading
        self.spin_volume.setValue(settings.get('default_volume', 0.1))
        self.spin_sl.setValue(settings.get('default_sl', 50))
        self.spin_tp.setValue(settings.get('default_tp', 100))