# src/infrastructure/ui/control_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QGridLayout, QTextEdit, QCheckBox, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
                             QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
import json


class ControlPanel(QWidget):
    """Panel de control para la plataforma de trading."""
    
    # Señales
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)
    sell_requested = pyqtSignal(dict)
    refresh_positions = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado
        self.is_connected = False
        self.current_symbol = "EURUSD"
        self.account_info = {}
        self.positions = []
        
        # Configuración por defecto
        self.default_volume = 0.1
        self.default_sl = 50
        self.default_tp = 100
        
        # Inicializar UI
        self.init_ui()
        
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
        self.tab_account = self.create_account_tab()
        self.tab_settings = self.create_settings_tab()
        
        self.tab_widget.addTab(self.tab_trading, "📊 Trading")
        self.tab_widget.addTab(self.tab_positions, "💰 Posiciones")
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
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        
        # Estado de conexión
        self.lbl_connection = QLabel("❌ Desconectado")
        
        connection_layout.addWidget(self.btn_connect, 0, 0, 1, 2)
        connection_layout.addWidget(self.lbl_connection, 1, 0, 1, 2)
        
        # 2. Grupo de símbolo
        group_symbol = QGroupBox("Símbolo y Timeframe")
        symbol_layout = QGridLayout(group_symbol)
        
        # Selector de símbolo
        symbol_layout.addWidget(QLabel("Símbolo:"), 0, 0)
        self.cmb_symbol = QComboBox()
        self.cmb_symbol.addItems(["EURUSD", "US500", "GBPUSD", "USDJPY", "XAUUSD"])
        self.cmb_symbol.setCurrentText(self.current_symbol)
        self.cmb_symbol.currentTextChanged.connect(self.on_symbol_changed)
        symbol_layout.addWidget(self.cmb_symbol, 0, 1)
        
        # Selector de timeframe - CORREGIDO: Usar formato correcto "H1" no "1H"
        symbol_layout.addWidget(QLabel("Timeframe:"), 1, 0)
        self.cmb_timeframe = QComboBox()
        self.cmb_timeframe.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        self.cmb_timeframe.setCurrentText("H1")
        self.cmb_timeframe.currentTextChanged.connect(self.on_timeframe_changed)
        symbol_layout.addWidget(self.cmb_timeframe, 1, 1)
        
        # Precio actual
        self.lbl_current_price = QLabel("Precio: --")
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
        self.btn_buy.clicked.connect(self.on_buy_clicked)
        self.btn_buy.setEnabled(False)
        
        self.btn_sell = QPushButton("🔴 VENDER")
        self.btn_sell.clicked.connect(self.on_sell_clicked)
        self.btn_sell.setEnabled(False)
        
        trade_layout.addWidget(self.btn_buy, 4, 0, 1, 2)
        trade_layout.addWidget(self.btn_sell, 5, 0, 1, 2)
        
        # Agregar grupos al layout
        layout.addWidget(group_connection)
        layout.addWidget(group_symbol)
        layout.addWidget(group_quick_trade)
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
        self.table_positions.setColumnCount(7)
        self.table_positions.setHorizontalHeaderLabels([
            "Ticket", "Símbolo", "Tipo", "Volumen", 
            "Precio", "Profit", "Acciones"
        ])
        
        # Configurar tabla
        header = self.table_positions.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Label de resumen
        self.lbl_positions_summary = QLabel("No hay posiciones abiertas")
        
        layout.addLayout(button_layout)
        layout.addWidget(self.lbl_positions_summary)
        layout.addWidget(self.table_positions, 1)
        
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
        
        basic_layout.addWidget(QLabel("Servidor:"), 1, 0)
        self.lbl_account_server = QLabel("--")
        basic_layout.addWidget(self.lbl_account_server, 1, 1)
        
        basic_layout.addWidget(QLabel("Moneda:"), 2, 0)
        self.lbl_currency = QLabel("--")
        basic_layout.addWidget(self.lbl_currency, 2, 1)
        
        # 2. Información financiera
        group_financial = QGroupBox("Estado Financiero")
        financial_layout = QGridLayout(group_financial)
        
        financial_layout.addWidget(QLabel("Balance:"), 0, 0)
        self.lbl_balance = QLabel("$ --")
        financial_layout.addWidget(self.lbl_balance, 0, 1)
        
        financial_layout.addWidget(QLabel("Equity:"), 1, 0)
        self.lbl_equity = QLabel("$ --")
        financial_layout.addWidget(self.lbl_equity, 1, 1)
        
        financial_layout.addWidget(QLabel("Margen:"), 2, 0)
        self.lbl_margin = QLabel("$ --")
        financial_layout.addWidget(self.lbl_margin, 2, 1)
        
        financial_layout.addWidget(QLabel("Margen Libre:"), 3, 0)
        self.lbl_free_margin = QLabel("$ --")
        financial_layout.addWidget(self.lbl_free_margin, 3, 1)
        
        # Agregar grupos al layout
        layout.addWidget(group_basic)
        layout.addWidget(group_financial)
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
        
        # 2. Botones de acción
        group_actions = QGroupBox("Acciones")
        actions_layout = QHBoxLayout(group_actions)
        
        self.btn_save_settings = QPushButton("💾 Guardar")
        self.btn_save_settings.clicked.connect(self.on_save_settings)
        
        self.btn_load_settings = QPushButton("📂 Cargar")
        self.btn_load_settings.clicked.connect(self.on_load_settings)
        
        actions_layout.addWidget(self.btn_save_settings)
        actions_layout.addWidget(self.btn_load_settings)
        
        # Área de información
        self.txt_settings_info = QTextEdit()
        self.txt_settings_info.setReadOnly(True)
        self.txt_settings_info.setMaximumHeight(100)
        self.txt_settings_info.setPlaceholderText("Información de configuración...")
        
        # Agregar grupos al layout
        layout.addWidget(group_trading)
        layout.addWidget(group_actions)
        layout.addWidget(self.txt_settings_info)
        layout.addStretch()
        
        return widget
    
    # ===== MÉTODOS DE ESTADO =====
    
    def update_connection_status(self, connected, message="", server_info=""):
        """Actualizar estado de conexión."""
        self.is_connected = connected
        
        if connected:
            self.lbl_connection.setText("✅ Conectado")
            self.btn_connect.setText("🔌 Desconectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.on_disconnect_clicked)
            
            self.btn_buy.setEnabled(True)
            self.btn_sell.setEnabled(True)
            self.btn_refresh_positions.setEnabled(True)
            self.btn_close_all.setEnabled(True)
        else:
            self.lbl_connection.setText("❌ Desconectado")
            self.btn_connect.setText("🔌 Conectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.on_connect_clicked)
            
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(False)
            self.btn_refresh_positions.setEnabled(False)
            self.btn_close_all.setEnabled(False)
    
    def update_account_info(self, account_info):
        """Actualizar información de cuenta."""
        self.account_info = account_info
        
        # Actualizar etiquetas
        self.lbl_login.setText(str(account_info.get('login', '--')))
        self.lbl_account_server.setText(account_info.get('server', '--'))
        self.lbl_currency.setText(account_info.get('currency', '--'))
        
        # Actualizar información financiera
        balance = account_info.get('balance', 0)
        equity = account_info.get('equity', 0)
        margin = account_info.get('margin', 0)
        free_margin = account_info.get('free_margin', 0)
        
        self.lbl_balance.setText(f"$ {balance:.2f}")
        self.lbl_equity.setText(f"$ {equity:.2f}")
        self.lbl_margin.setText(f"$ {margin:.2f}")
        self.lbl_free_margin.setText(f"$ {free_margin:.2f}")
    
    def update_positions(self, positions):
        """Actualizar lista de posiciones."""
        self.positions = positions
        
        # Limpiar tabla
        self.table_positions.setRowCount(0)
        
        if not positions:
            self.lbl_positions_summary.setText("No hay posiciones abiertas")
            return
        
        # Actualizar tabla
        for i, pos in enumerate(positions):
            self.table_positions.insertRow(i)
            
            # Ticket
            self.table_positions.setItem(i, 0, QTableWidgetItem(str(pos.get('ticket', ''))))
            
            # Símbolo
            self.table_positions.setItem(i, 1, QTableWidgetItem(pos.get('symbol', '')))
            
            # Tipo (Buy/Sell)
            type_str = "COMPRA" if pos.get('type', 0) == 0 else "VENTA"
            type_item = QTableWidgetItem(type_str)
            self.table_positions.setItem(i, 2, type_item)
            
            # Volumen
            self.table_positions.setItem(i, 3, QTableWidgetItem(str(pos.get('volume', 0))))
            
            # Precio de apertura
            self.table_positions.setItem(i, 4, QTableWidgetItem(f"{pos.get('price_open', 0):.5f}"))
            
            # Profit
            profit = pos.get('profit', 0)
            profit_item = QTableWidgetItem(f"$ {profit:.2f}")
            self.table_positions.setItem(i, 5, profit_item)
            
            # Botón de cerrar
            close_btn = QPushButton("Cerrar")
            ticket = pos.get('ticket')
            if ticket:
                close_btn.clicked.connect(lambda checked, t=ticket: self.on_close_position(t))
            self.table_positions.setCellWidget(i, 6, close_btn)
        
        # Actualizar resumen
        self.lbl_positions_summary.setText(f"{len(positions)} posición(es) abierta(s)")
    
    def update_price_display(self, price_data=None):
        """Actualizar display de precios."""
        if price_data:
            current_price = price_data.get('bid', 0)
            self.lbl_current_price.setText(f"Precio: {current_price:.5f}")
    
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
                    # Aquí necesitarías implementar el cierre
                    pass
    
    def on_close_position(self, ticket):
        """Manejador para cerrar posición específica."""
        # Aquí necesitarías implementar el cierre de posición individual
        pass
    
    def on_save_settings(self):
        """Guardar configuración."""
        settings = {
            'default_volume': self.spin_default_volume.value(),
            'default_sl': self.spin_default_sl.value(),
            'default_tp': self.spin_default_tp.value(),
            'auto_connect': self.cb_auto_connect.isChecked()
        }
        
        try:
            with open('trading_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.txt_settings_info.append("✅ Configuración guardada")
            
        except Exception as e:
            self.txt_settings_info.append(f"❌ Error: {str(e)}")
    
    def on_load_settings(self):
        """Cargar configuración."""
        try:
            with open('trading_settings.json', 'r') as f:
                settings = json.load(f)
            
            self.load_settings_from_dict(settings)
            self.txt_settings_info.append("✅ Configuración cargada")
            
        except FileNotFoundError:
            self.txt_settings_info.append("ℹ️ No se encontró archivo")
        except Exception as e:
            self.txt_settings_info.append(f"❌ Error: {str(e)}")
    
    # ===== UTILIDADES =====
    
    def load_settings(self):
        """Cargar configuración al iniciar."""
        try:
            with open('trading_settings.json', 'r') as f:
                settings = json.load(f)
                self.load_settings_from_dict(settings)
        except:
            pass
    
    def load_settings_from_dict(self, settings):
        """Cargar configuración desde diccionario."""
        self.spin_default_volume.setValue(settings.get('default_volume', 0.1))
        self.spin_default_sl.setValue(settings.get('default_sl', 50))
        self.spin_default_tp.setValue(settings.get('default_tp', 100))
        self.cb_auto_connect.setChecked(settings.get('auto_connect', True))
        
        # Aplicar a controles de trading
        self.spin_volume.setValue(settings.get('default_volume', 0.1))
        self.spin_sl.setValue(settings.get('default_sl', 50))
        self.spin_tp.setValue(settings.get('default_tp', 100))