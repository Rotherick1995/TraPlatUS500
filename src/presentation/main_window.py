# src/presentation/main_window.py
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QTextEdit, QTabWidget,
                             QSplitter, QGroupBox, QGridLayout, QMessageBox, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# Importar tus componentes
try:
    from src.infrastructure.ui.chart_view import ChartView
    from src.infrastructure.ui.control_panel import ControlPanel
except ImportError:
    # Si no existen aún, crear placeholders
    ChartView = None
    ControlPanel = None


class MainWindow(QMainWindow):
    """Ventana principal de la plataforma de trading."""
    
    # Señales
    connection_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)
    sell_requested = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Configuración inicial
        self.is_dark_theme = True
        
        # Inicializar UI
        self.init_ui()
        
        # Aplicar tema
        self.apply_theme()
        
        # Configurar timers
        self.init_timers()
        
        # Mostrar mensaje de inicio
        self.log_message("🚀 US500 Trading Platform iniciado")
        self.log_message("📊 Versión 1.0.0")
        self.log_message("💡 Presione 'Conectar a MT5' para comenzar")
    
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        self.setWindowTitle("US500 Trading Platform")
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
    
    def create_top_bar(self):
        """Crear barra superior de controles."""
        self.top_bar_layout = QHBoxLayout()
        self.top_bar_layout.setSpacing(10)
        
        # Botón de conexión
        self.btn_connect = QPushButton("🔌 Conectar a MT5")
        self.btn_connect.setFixedWidth(150)
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
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        
        # Estado de conexión
        self.lbl_connection_status = QLabel("❌ Desconectado")
        self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #ff6b6b;")
        
        # Separador
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("color: #333;")
        
        # Selector de símbolo
        self.cmb_symbol = QComboBox()
        self.cmb_symbol.addItems(["US500", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"])
        self.cmb_symbol.setCurrentText("US500")
        self.cmb_symbol.setFixedWidth(100)
        self.cmb_symbol.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        # Selector de timeframe
        self.cmb_timeframe = QComboBox()
        self.cmb_timeframe.addItems(["1M", "5M", "15M", "30M", "1H", "4H", "1D", "1W"])
        self.cmb_timeframe.setCurrentText("1H")
        self.cmb_timeframe.setFixedWidth(80)
        self.cmb_timeframe.setStyleSheet(self.cmb_symbol.styleSheet())
        
        # Botón de actualizar
        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.setFixedWidth(100)
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                padding: 6px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #777;
            }
        """)
        
        # Separador
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setStyleSheet("color: #333;")
        
        # Información de cuenta
        self.lbl_account = QLabel("Cuenta: --")
        self.lbl_account.setStyleSheet("color: #aaa;")
        
        # Espaciador
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Agregar widgets al layout
        self.top_bar_layout.addWidget(self.btn_connect)
        self.top_bar_layout.addWidget(self.lbl_connection_status)
        self.top_bar_layout.addWidget(separator1)
        self.top_bar_layout.addWidget(QLabel("Símbolo:"))
        self.top_bar_layout.addWidget(self.cmb_symbol)
        self.top_bar_layout.addWidget(QLabel("TF:"))
        self.top_bar_layout.addWidget(self.cmb_timeframe)
        self.top_bar_layout.addWidget(self.btn_refresh)
        self.top_bar_layout.addWidget(separator2)
        self.top_bar_layout.addWidget(self.lbl_account)
        self.top_bar_layout.addWidget(spacer)
        
        # Conectar señales
        self.cmb_symbol.currentTextChanged.connect(self.on_symbol_changed)
        self.cmb_timeframe.currentTextChanged.connect(self.on_timeframe_changed)
    
    def create_chart_panel(self):
        """Crear panel del gráfico."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título del gráfico
        self.lbl_chart_title = QLabel("📊 US500 - 1H")
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
        if ChartView:
            self.chart_view = ChartView()
        else:
            # Placeholder si ChartView no existe
            self.chart_view = QLabel(
                "<center><h3>Gráfico de Trading</h3>"
                "<p>Instale pyqtgraph para gráficos interactivos:</p>"
                "<code>pip install pyqtgraph</code></center>"
            )
            self.chart_view.setStyleSheet("""
                QLabel {
                    background-color: #1a1a1a;
                    color: #888;
                    font-family: monospace;
                    border: 2px dashed #444;
                    border-radius: 8px;
                }
            """)
            self.chart_view.setAlignment(Qt.AlignCenter)
        
        # Panel de precios en tiempo real
        price_panel = self.create_price_panel()
        
        # Agregar al layout
        layout.addWidget(self.lbl_chart_title)
        layout.addWidget(self.chart_view, 1)  # 1 = stretch
        layout.addWidget(price_panel)
        
        return widget
    
    def create_price_panel(self):
        """Crear panel de precios en tiempo real."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # Estilo para etiquetas de precio
        price_style = """
            QLabel {
                font-family: 'Consolas', 'Monospace';
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 5px;
                min-width: 140px;
                text-align: center;
                font-size: 13px;
            }
        """
        
        # Precio BID
        self.lbl_bid = QLabel("BID: --")
        self.lbl_bid.setStyleSheet(price_style + "background-color: #1a2a1a; color: #0af;")
        
        # Precio ASK
        self.lbl_ask = QLabel("ASK: --")
        self.lbl_ask.setStyleSheet(price_style + "background-color: #2a1a1a; color: #f0a;")
        
        # Spread
        self.lbl_spread = QLabel("Spread: --")
        self.lbl_spread.setStyleSheet(price_style + "background-color: #2a2a2a; color: #ccc;")
        
        # Cambio
        self.lbl_change = QLabel("Cambio: --")
        self.lbl_change.setStyleSheet(price_style + "background-color: #1a1a2a; color: #ccc;")
        
        # Alto/Bajo
        self.lbl_high = QLabel("Alto: --")
        self.lbl_high.setStyleSheet("QLabel { color: #0f0; font-weight: bold; padding: 5px 10px; }")
        
        self.lbl_low = QLabel("Bajo: --")
        self.lbl_low.setStyleSheet("QLabel { color: #f00; font-weight: bold; padding: 5px 10px; }")
        
        # Agregar widgets
        layout.addWidget(self.lbl_bid)
        layout.addWidget(self.lbl_ask)
        layout.addWidget(self.lbl_spread)
        layout.addWidget(self.lbl_change)
        layout.addStretch()
        layout.addWidget(self.lbl_high)
        layout.addWidget(self.lbl_low)
        
        return widget
    
    def create_control_panel(self):
        """Crear panel de control lateral."""
        # Si ControlPanel existe, usarlo
        if ControlPanel:
            self.control_panel = ControlPanel()
            return self.control_panel
        
        # Si no, crear panel básico
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Pestañas
        self.tab_widget = QTabWidget()
        
        # 1. Pestaña de Trading
        trading_tab = self.create_trading_tab()
        self.tab_widget.addTab(trading_tab, "📊 Trading")
        
        # 2. Pestaña de Posiciones
        positions_tab = self.create_positions_tab()
        self.tab_widget.addTab(positions_tab, "💰 Posiciones")
        
        # 3. Pestaña de Órdenes
        orders_tab = self.create_orders_tab()
        self.tab_widget.addTab(orders_tab, "⏳ Órdenes")
        
        # 4. Pestaña de Cuenta
        account_tab = self.create_account_tab()
        self.tab_widget.addTab(account_tab, "👤 Cuenta")
        
        # 5. Pestaña de Logs
        logs_tab = self.create_logs_tab()
        self.tab_widget.addTab(logs_tab, "📝 Logs")
        
        layout.addWidget(self.tab_widget)
        
        return widget
    
    def create_trading_tab(self):
        """Crear pestaña de trading."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Grupo de operación rápida
        group_trade = QGroupBox("Operación Rápida")
        group_layout = QGridLayout(group_trade)
        
        # Volumen
        group_layout.addWidget(QLabel("Volumen:"), 0, 0)
        self.spin_volume = QComboBox()
        self.spin_volume.addItems(["0.01", "0.1", "0.5", "1.0", "2.0", "5.0"])
        self.spin_volume.setCurrentText("0.1")
        group_layout.addWidget(self.spin_volume, 0, 1)
        
        # SL
        group_layout.addWidget(QLabel("SL (pips):"), 1, 0)
        self.spin_sl = QComboBox()
        self.spin_sl.addItems(["10", "20", "50", "100", "200"])
        self.spin_sl.setCurrentText("50")
        group_layout.addWidget(self.spin_sl, 1, 1)
        
        # TP
        group_layout.addWidget(QLabel("TP (pips):"), 2, 0)
        self.spin_tp = QComboBox()
        self.spin_tp.addItems(["20", "50", "100", "200", "500"])
        self.spin_tp.setCurrentText("100")
        group_layout.addWidget(self.spin_tp, 2, 1)
        
        # Comentario
        group_layout.addWidget(QLabel("Comentario:"), 3, 0)
        self.txt_comment = QComboBox()
        self.txt_comment.addItems(["Operación manual", "Señal técnica", "Scalping", "Swing"])
        self.txt_comment.setEditable(True)
        group_layout.addWidget(self.txt_comment, 3, 1)
        
        # Botón COMPRAR
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
        self.btn_buy.setEnabled(False)
        
        # Botón VENDER
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
        self.btn_sell.setEnabled(False)
        
        group_layout.addWidget(self.btn_buy, 4, 0, 1, 2)
        group_layout.addWidget(self.btn_sell, 5, 0, 1, 2)
        
        # Grupo de información de cuenta
        group_account = QGroupBox("Información Rápida")
        account_layout = QVBoxLayout(group_account)
        
        self.lbl_balance = QLabel("Balance: --")
        self.lbl_balance.setStyleSheet("font-family: monospace; color: #fff;")
        
        self.lbl_equity = QLabel("Equity: --")
        self.lbl_equity.setStyleSheet("font-family: monospace; color: #fff;")
        
        self.lbl_margin = QLabel("Margen: --")
        self.lbl_margin.setStyleSheet("font-family: monospace; color: #fff;")
        
        self.lbl_free_margin = QLabel("Margen Libre: --")
        self.lbl_free_margin.setStyleSheet("font-family: monospace; color: #fff;")
        
        self.lbl_margin_level = QLabel("Nivel de Margen: --")
        self.lbl_margin_level.setStyleSheet("font-family: monospace; color: #fff;")
        
        # Barra de nivel de margen
        self.progress_margin = QProgressBar()
        self.progress_margin.setRange(0, 1000)
        self.progress_margin.setTextVisible(True)
        self.progress_margin.setFormat("%v%%")
        self.progress_margin.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)
        
        account_layout.addWidget(self.lbl_balance)
        account_layout.addWidget(self.lbl_equity)
        account_layout.addWidget(self.lbl_margin)
        account_layout.addWidget(self.lbl_free_margin)
        account_layout.addWidget(self.lbl_margin_level)
        account_layout.addWidget(self.progress_margin)
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
        layout.setSpacing(10)
        
        # Botón de actualizar
        self.btn_refresh_positions = QPushButton("🔄 Actualizar Posiciones")
        self.btn_refresh_positions.setEnabled(False)
        self.btn_refresh_positions.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:disabled {
                background-color: #333;
            }
        """)
        
        # Área de texto para posiciones
        self.txt_positions = QTextEdit()
        self.txt_positions.setReadOnly(True)
        self.txt_positions.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ccc;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        self.txt_positions.setPlaceholderText("No hay posiciones abiertas...")
        
        layout.addWidget(self.btn_refresh_positions)
        layout.addWidget(self.txt_positions, 1)  # 1 = stretch
        
        return widget
    
    def create_orders_tab(self):
        """Crear pestaña de órdenes pendientes."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tabla de órdenes
        self.table_orders = QTableWidget()
        self.table_orders.setColumnCount(7)
        self.table_orders.setHorizontalHeaderLabels(["Ticket", "Símbolo", "Tipo", "Volumen", "Precio", "SL", "TP"])
        
        # Configurar tabla
        header = self.table_orders.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_orders.setAlternatingRowColors(True)
        self.table_orders.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                alternate-background-color: #222;
                color: #ccc;
                gridline-color: #333;
                border: 1px solid #333;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #ddd;
                padding: 5px;
                border: 1px solid #333;
            }
        """)
        
        layout.addWidget(self.table_orders)
        
        return widget
    
    def create_account_tab(self):
        """Crear pestaña de información de cuenta."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Información básica
        group_basic = QGroupBox("Información de Cuenta")
        basic_layout = QGridLayout(group_basic)
        
        basic_layout.addWidget(QLabel("Login:"), 0, 0)
        self.lbl_account_login = QLabel("--")
        basic_layout.addWidget(self.lbl_account_login, 0, 1)
        
        basic_layout.addWidget(QLabel("Nombre:"), 1, 0)
        self.lbl_account_name = QLabel("--")
        basic_layout.addWidget(self.lbl_account_name, 1, 1)
        
        basic_layout.addWidget(QLabel("Servidor:"), 2, 0)
        self.lbl_account_server = QLabel("--")
        basic_layout.addWidget(self.lbl_account_server, 2, 1)
        
        basic_layout.addWidget(QLabel("Moneda:"), 3, 0)
        self.lbl_account_currency = QLabel("--")
        basic_layout.addWidget(self.lbl_account_currency, 3, 1)
        
        basic_layout.addWidget(QLabel("Apalancamiento:"), 4, 0)
        self.lbl_account_leverage = QLabel("--")
        basic_layout.addWidget(self.lbl_account_leverage, 4, 1)
        
        # Estadísticas
        group_stats = QGroupBox("Estadísticas")
        stats_layout = QGridLayout(group_stats)
        
        stats_layout.addWidget(QLabel("Posiciones:"), 0, 0)
        self.lbl_stats_positions = QLabel("0")
        stats_layout.addWidget(self.lbl_stats_positions, 0, 1)
        
        stats_layout.addWidget(QLabel("Órdenes:"), 1, 0)
        self.lbl_stats_orders = QLabel("0")
        stats_layout.addWidget(self.lbl_stats_orders, 1, 1)
        
        stats_layout.addWidget(QLabel("Profit Total:"), 2, 0)
        self.lbl_stats_profit = QLabel("$ 0.00")
        stats_layout.addWidget(self.lbl_stats_profit, 2, 1)
        
        stats_layout.addWidget(QLabel("Profit Hoy:"), 3, 0)
        self.lbl_stats_daily_profit = QLabel("$ 0.00")
        stats_layout.addWidget(self.lbl_stats_daily_profit, 3, 1)
        
        # Agregar grupos
        layout.addWidget(group_basic)
        layout.addWidget(group_stats)
        layout.addStretch()
        
        return widget
    
    def create_logs_tab(self):
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
        self.txt_logs.setPlaceholderText("Logs del sistema...")
        
        layout.addWidget(self.txt_logs)
        
        return widget
    
    def create_bottom_panel(self):
        """Crear panel inferior (mini logs)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Mini log
        self.txt_mini_log = QTextEdit()
        self.txt_mini_log.setMaximumHeight(80)
        self.txt_mini_log.setReadOnly(True)
        self.txt_mini_log.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ccc;
                font-family: monospace;
                font-size: 10px;
                border: 1px solid #333;
                border-radius: 3px;
            }
        """)
        self.txt_mini_log.setPlaceholderText("Logs recientes...")
        
        layout.addWidget(self.txt_mini_log)
        
        return widget
    
    def setup_status_bar(self):
        """Configurar barra de estado."""
        self.statusBar().showMessage("Listo")
        
        # Etiquetas de estado
        self.lbl_status_data = QLabel("Datos: Esperando conexión")
        self.lbl_status_time = QLabel("--:--:--")
        
        self.statusBar().addPermanentWidget(self.lbl_status_data)
        self.statusBar().addPermanentWidget(self.lbl_status_time)
    
    def apply_theme(self):
        """Aplicar tema oscuro a la aplicación."""
        if self.is_dark_theme:
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
    
    def init_timers(self):
        """Inicializar timers."""
        # Timer para actualizar reloj
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
    
    def update_clock(self):
        """Actualizar reloj en barra de estado."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.lbl_status_time.setText(current_time)
    
    def log_message(self, message):
        """Agregar mensaje a los logs."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Agregar a mini log
        self.txt_mini_log.append(log_entry)
        
        # Agregar a log completo
        self.txt_logs.append(log_entry)
        
        # Mantener mini log limitado
        lines = self.txt_mini_log.toPlainText().split('\n')
        if len(lines) > 10:
            self.txt_mini_log.setPlainText('\n'.join(lines[-10:]))
        
        # Auto-scroll en logs
        scrollbar = self.txt_logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Actualizar barra de estado
        self.lbl_status_data.setText(f"Log: {message[:30]}...")
    
    def update_connection_status(self, connected, message=""):
        """Actualizar estado de conexión."""
        self.is_connected = connected
        
        if connected:
            self.lbl_connection_status.setText("✅ Conectado")
            self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #4cd964;")
            self.btn_connect.setText("🔌 Desconectar")
            
            # Habilitar controles
            self.btn_refresh.setEnabled(True)
            self.btn_buy.setEnabled(True)
            self.btn_sell.setEnabled(True)
            self.btn_refresh_positions.setEnabled(True)
            
            if message:
                self.log_message(f"✅ {message}")
        else:
            self.lbl_connection_status.setText("❌ Desconectado")
            self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #ff6b6b;")
            self.btn_connect.setText("🔌 Conectar a MT5")
            
            # Deshabilitar controles
            self.btn_refresh.setEnabled(False)
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(False)
            self.btn_refresh_positions.setEnabled(False)
            
            if message:
                self.log_message(f"❌ {message}")
    
    def update_price_display(self, bid, ask, spread=None):
        """Actualizar display de precios."""
        self.lbl_bid.setText(f"BID: {bid:.5f}")
        self.lbl_ask.setText(f"ASK: {ask:.5f}")
        
        if spread is not None:
            self.lbl_spread.setText(f"Spread: {spread:.1f} pips")
        
        # Calcular cambio (simulado)
        try:
            current_bid = float(bid)
            # Aquí iría lógica para calcular cambio real
            self.lbl_change.setText("Cambio: +0.12%")
        except:
            pass
    
    def update_account_display(self, account_info):
        """Actualizar información de cuenta en UI."""
        if not account_info:
            return
        
        # Información básica
        self.lbl_account.setText(f"Cuenta: {account_info.get('login', '--')}")
        
        # Trading tab
        self.lbl_balance.setText(f"Balance: ${account_info.get('balance', 0):.2f}")
        self.lbl_equity.setText(f"Equity: ${account_info.get('equity', 0):.2f}")
        self.lbl_margin.setText(f"Margen: ${account_info.get('margin', 0):.2f}")
        
        free_margin = account_info.get('free_margin', 0)
        self.lbl_free_margin.setText(f"Margen Libre: ${free_margin:.2f}")
        
        margin_level = account_info.get('margin_level', 0)
        self.lbl_margin_level.setText(f"Nivel de Margen: {margin_level:.1f}%")
        
        # Actualizar barra de progreso
        self.progress_margin.setValue(int(margin_level))
        
        # Colores según nivel de margen
        if margin_level < 100:
            self.progress_margin.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #ff4444;
                }
            """)
        elif margin_level < 200:
            self.progress_margin.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #ffaa00;
                }
            """)
        else:
            self.progress_margin.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #00aa00;
                }
            """)
        
        # Account tab
        self.lbl_account_login.setText(str(account_info.get('login', '--')))
        self.lbl_account_name.setText(account_info.get('name', '--'))
        self.lbl_account_server.setText(account_info.get('server', '--'))
        self.lbl_account_currency.setText(account_info.get('currency', '--'))
        
        leverage = account_info.get('leverage', 0)
        self.lbl_account_leverage.setText(f"1:{leverage}")
    
    def update_positions_display(self, positions):
        """Actualizar display de posiciones."""
        if not positions:
            self.txt_positions.setPlainText("✅ No hay posiciones abiertas")
            self.lbl_stats_positions.setText("0")
            return
        
        text = f"📊 {len(positions)} Posición(es) Abierta(s):\n\n"
        
        total_profit = 0
        for pos in positions:
            if hasattr(pos, 'ticket'):
                # Si es objeto Position
                type_str = "📈 COMPRA" if pos.type == 0 else "📉 VENTA"
                text += f"• #{pos.ticket} {type_str} {pos.symbol} "
                text += f"Vol: {pos.volume} Precio: {pos.price_open:.5f} "
                
                profit = getattr(pos, 'profit', 0)
                total_profit += profit
                
                profit_color = "🟢" if profit >= 0 else "🔴"
                text += f"{profit_color} ${profit:.2f}\n"
            elif isinstance(pos, dict):
                # Si es diccionario
                type_str = "📈 COMPRA" if pos.get('type') == 0 else "📉 VENTA"
                text += f"• #{pos.get('ticket', 'N/A')} {type_str} {pos.get('symbol', 'N/A')} "
                text += f"Vol: {pos.get('volume', 0)} "
                
                profit = pos.get('profit', 0)
                total_profit += profit
                
                profit_color = "🟢" if profit >= 0 else "🔴"
                text += f"{profit_color} ${profit:.2f}\n"
            else:
                text += f"• {str(pos)[:50]}...\n"
        
        self.txt_positions.setPlainText(text)
        self.lbl_stats_positions.setText(str(len(positions)))
        
        # Actualizar profit total
        self.lbl_stats_profit.setText(f"$ {total_profit:.2f}")
        if total_profit >= 0:
            self.lbl_stats_profit.setStyleSheet("color: #0f0; font-weight: bold;")
        else:
            self.lbl_stats_profit.setStyleSheet("color: #f00; font-weight: bold;")
    
    def update_chart_title(self, symbol, timeframe, candle_count=None):
        """Actualizar título del gráfico."""
        if candle_count:
            self.lbl_chart_title.setText(f"📊 {symbol} - {timeframe} ({candle_count} velas)")
        else:
            self.lbl_chart_title.setText(f"📊 {symbol} - {timeframe}")
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.symbol_changed.emit(symbol)
        self.log_message(f"📈 Símbolo cambiado a: {symbol}")
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.timeframe_changed.emit(timeframe)
        self.log_message(f"⏰ Timeframe cambiado a: {timeframe}")
    
    def closeEvent(self, event):
        """Manejador para cerrar la ventana."""
        if hasattr(self, 'is_connected') and self.is_connected:
            reply = QMessageBox.question(
                self, "Confirmar Salida",
                "¿Está seguro de que desea salir?\n\n"
                "Se desconectará de MT5 y se cerrará la aplicación.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.disconnect_requested.emit()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()