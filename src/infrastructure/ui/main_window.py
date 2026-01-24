# src/presentation/main_window.py
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QTabWidget,
                             QSplitter, QGroupBox, QGridLayout, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5

# Importaciones de tu proyecto
from src.application.use_cases.connect_to_mt5 import create_connect_to_mt5_use_case
from src.application.use_cases.fetch_market_data import create_fetch_market_data_use_case
from src.config import settings
from src.infrastructure.ui.chart_view import ChartView
from src.infrastructure.ui.control_panel import ControlPanel


class MainWindow(QMainWindow):
    """Ventana principal de la plataforma de trading."""
    
    def __init__(self):
        super().__init__()
        
        # Inicializar casos de uso
        self.mt5_use_case = None
        self.data_use_case = None
        
        # Estado de la aplicación
        self.is_connected = False
        self.current_symbol = settings.DEFAULT_SYMBOL
        self.current_timeframe = "H1"
        self.server_name = "No conectado"
        self.server_time = None  # Hora del servidor MT5
        self.server_timezone = "UTC"  # Zona horaria del servidor
        
        # NUEVO: Configuración de cantidad de velas
        self.current_candles_count = 100  # Valor por defecto
        
        # Configurar UI
        self.setup_ui()
        self.setup_timers()
        
        # Intentar conexión automática si está configurado
        if hasattr(settings, 'AUTO_CONNECT') and settings.AUTO_CONNECT:
            QTimer.singleShot(1000, self.connect_to_mt5)
    
    def setup_ui(self):
        """Configurar la interfaz de usuario."""
        self.setWindowTitle("Rotherick's Trading Platform")
        
        # Iniciar en pantalla completa
        self.showMaximized()
        
        # Tema oscuro
        self.set_dark_theme()
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 1. Cabecera con título y hora del servidor
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)
        
        # 2. Barra superior simplificada
        top_bar = self.create_top_bar()
        main_layout.addLayout(top_bar)
        
        # 3. Área principal dividida
        splitter = QSplitter(Qt.Horizontal)
        
        # Control panel
        self.control_panel = ControlPanel()
        self.control_panel.setMinimumWidth(400)
        self.control_panel.setMaximumWidth(600)
        
        # Chart view
        self.chart_view = ChartView()
        self.chart_view.setMinimumWidth(800)
        
        # Agregar widgets en orden de visualización
        splitter.addWidget(self.chart_view)      # Izquierda: Chart
        splitter.addWidget(self.control_panel)   # Derecha: Control panel
        
        # Configurar proporciones iniciales (70% chart, 30% panel)
        splitter.setSizes([700, 300])
        
        # Establecer stretch factors
        splitter.setStretchFactor(0, 3)  # Chart tiene stretch factor 3
        splitter.setStretchFactor(1, 1)  # Panel tiene stretch factor 1
        
        # Conectar señales del control panel
        self.control_panel.connect_requested.connect(self.connect_to_mt5)
        self.control_panel.disconnect_requested.connect(self.disconnect_from_mt5)
        self.control_panel.symbol_changed.connect(self.on_symbol_changed)
        self.control_panel.timeframe_changed.connect(self.on_timeframe_changed)
        self.control_panel.buy_requested.connect(self.on_buy_requested)
        self.control_panel.sell_requested.connect(self.on_sell_requested)
        self.control_panel.refresh_positions.connect(self.refresh_positions)
        
        # Conectar NUEVA señal para cantidad de velas
        self.control_panel.candles_count_changed.connect(self.on_candles_count_changed)
        
        # Conectar señales del chart view
        self.chart_view.symbol_changed.connect(self.on_symbol_changed)
        self.chart_view.timeframe_changed.connect(self.on_timeframe_changed)
        
        # Conectar señales de indicadores
        if hasattr(self.control_panel, 'indicators_updated'):
            self.control_panel.indicators_updated.connect(self.chart_view.update_indicator_settings)
        
        main_layout.addWidget(splitter, 1)
        
        # 4. Barra de estado
        self.setup_status_bar()
    
    def create_header(self):
        """Crear cabecera con título grande y hora del servidor."""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        # Título principal
        title_label = QLabel("Rotherick's Trading Platform")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff; padding: 5px;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # Hora del servidor
        server_time_layout = QHBoxLayout()
        server_time_layout.addStretch()
        
        self.lbl_server_time = QLabel("🕒 Hora servidor: --/--/---- --:--:-- (UTC)")
        self.lbl_server_time.setStyleSheet("""
            QLabel {
                color: #00ffff;
                font-size: 14px;
                font-weight: bold;
                padding: 5px 15px;
                background-color: rgba(0, 60, 80, 0.4);
                border-radius: 8px;
                border: 1px solid #008888;
            }
        """)
        self.lbl_server_time.setAlignment(Qt.AlignCenter)
        self.lbl_server_time.setMinimumWidth(350)
        
        server_time_layout.addWidget(self.lbl_server_time)
        server_time_layout.addStretch()
        
        # Línea separadora
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #444; margin: 5px 0px;")
        separator.setMaximumHeight(2)
        
        header_layout.addWidget(title_label)
        header_layout.addLayout(server_time_layout)
        header_layout.addWidget(separator)
        
        return header_layout
    
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
        """Crear barra superior simplificada."""
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
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        
        # Estado de conexión
        self.lbl_connection_status = QLabel("❌ Desconectado")
        self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #ff6b6b;")
        
        # Información del servidor
        server_group = QWidget()
        server_layout = QVBoxLayout(server_group)
        server_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_server_label = QLabel("Servidor:")
        self.lbl_server_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.lbl_server_name = QLabel("No conectado")
        self.lbl_server_name.setStyleSheet("font-weight: bold; color: #4cd964; font-size: 12px;")
        
        server_layout.addWidget(self.lbl_server_label)
        server_layout.addWidget(self.lbl_server_name)
        
        # Información de cuenta
        account_group = QWidget()
        account_layout = QVBoxLayout(account_group)
        account_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_account_label = QLabel("Cuenta:")
        self.lbl_account_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.lbl_account_info = QLabel("--")
        self.lbl_account_info.setStyleSheet("font-weight: bold; color: #ffa500; font-size: 12px;")
        
        account_layout.addWidget(self.lbl_account_label)
        account_layout.addWidget(self.lbl_account_info)
        
        # Información de velas
        candles_group = QWidget()
        candles_layout = QVBoxLayout(candles_group)
        candles_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_candles_label = QLabel("Velas cargadas:")
        self.lbl_candles_label.setStyleSheet("color: #aaa; font-size: 11px;")
        
        self.lbl_candles_count = QLabel("100")
        self.lbl_candles_count.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 12px;")
        
        candles_layout.addWidget(self.lbl_candles_label)
        candles_layout.addWidget(self.lbl_candles_count)
        
        # Separadores
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("background-color: #444;")
        separator1.setMaximumWidth(2)
        
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setStyleSheet("background-color: #444;")
        separator2.setMaximumWidth(2)
        
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.VLine)
        separator3.setFrameShadow(QFrame.Sunken)
        separator3.setStyleSheet("background-color: #444;")
        separator3.setMaximumWidth(2)
        
        # Versión/estado
        self.lbl_status_info = QLabel("Versión 1.0 | Modo: Demo")
        self.lbl_status_info.setStyleSheet("color: #aaa; font-size: 11px;")
        
        # Agregar widgets al layout
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.lbl_connection_status)
        layout.addWidget(separator1)
        layout.addWidget(server_group)
        layout.addWidget(separator2)
        layout.addWidget(account_group)
        layout.addWidget(separator3)
        layout.addWidget(candles_group)
        layout.addStretch()
        layout.addWidget(self.lbl_status_info)
        
        return layout
    
    def setup_status_bar(self):
        """Configurar barra de estado."""
        self.statusBar().showMessage("Listo")
        
        # Etiquetas de estado
        self.lbl_status_data = QLabel("Datos: Esperando conexión")
        self.lbl_status_data.setStyleSheet("color: #aaa;")
        
        # Hora local en barra de estado
        self.lbl_local_time = QLabel("Local: --:--:--")
        self.lbl_local_time.setStyleSheet("color: #0af; font-weight: bold;")
        
        # Contador de datos
        self.lbl_data_count = QLabel("Velas: 0")
        self.lbl_data_count.setStyleSheet("color: #4cd964; font-weight: bold;")
        
        self.statusBar().addPermanentWidget(self.lbl_status_data)
        self.statusBar().addPermanentWidget(self.lbl_data_count)
        self.statusBar().addPermanentWidget(self.lbl_local_time)
    
    def setup_timers(self):
        """Configurar timers para actualizaciones periódicas."""
        # Timer para actualizar hora local
        self.timer_local_clock = QTimer()
        self.timer_local_clock.timeout.connect(self.update_local_clock)
        self.timer_local_clock.start(1000)
        
        # Timer para actualizar hora del servidor
        self.timer_server_clock = QTimer()
        self.timer_server_clock.timeout.connect(self.update_server_clock_display)
        self.timer_server_clock.setInterval(1000)  # 1 segundo
        
        # Timer para actualizar precios (si está conectado)
        self.timer_prices = QTimer()
        self.timer_prices.timeout.connect(self.update_prices)
        self.timer_prices.setInterval(2000)  # 2 segundos
        
        # Timer para sincronizar hora del servidor periódicamente
        self.timer_sync_server_time = QTimer()
        self.timer_sync_server_time.timeout.connect(self.sync_server_time)
        self.timer_sync_server_time.setInterval(30000)  # 30 segundos
    
    def update_local_clock(self):
        """Actualizar reloj local."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.lbl_local_time.setText(f"Local: {current_time}")
    
    def update_server_clock_display(self):
        """Actualizar display de hora del servidor."""
        if self.is_connected and self.server_time:
            try:
                # Incrementar 1 segundo
                self.server_time = self.server_time + timedelta(seconds=1)
                
                # Formatear fecha y hora completa
                date_str = self.server_time.strftime("%d/%m/%Y")
                time_str = self.server_time.strftime("%H:%M:%S")
                
                # Mostrar con zona horaria
                self.lbl_server_time.setText(f"🕒 Hora servidor: {date_str} {time_str} ({self.server_timezone})")
                
            except Exception as e:
                # Si hay error, mostrar hora local
                local_time = datetime.now()
                self.lbl_server_time.setText(f"🕒 Hora local: {local_time.strftime('%d/%m/%Y %H:%M:%S')}")
        elif not self.is_connected:
            self.lbl_server_time.setText("🕒 Hora servidor: --/--/---- --:--:-- (UTC)")
    
    def sync_server_time(self):
        """Sincronizar hora del servidor desde MT5."""
        if self.is_connected:
            self.fetch_server_time_from_mt5()
    
    # ===== MÉTODOS DE CONEXIÓN =====
    
    def connect_to_mt5(self):
        """Conectar a MT5."""
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Conectando...")
        
        try:
            # Crear caso de uso
            self.mt5_use_case = create_connect_to_mt5_use_case(max_retries=3)
            
            # Conectar
            result = self.mt5_use_case.connect()
            
            if result['success']:
                self.is_connected = True
                
                # Obtener información del servidor
                server_info = "Desconocido"
                if 'server_info' in result['data']:
                    server_info = result['data']['server_info']
                elif 'account_info' in result['data']:
                    account_info = result['data']['account_info']
                    server_info = account_info.get('server', 'Desconocido')
                
                self.server_name = server_info
                
                # Actualizar UI de conexión
                self.update_connection_status(True, f"✅ Conectado a {server_info}")
                
                # Crear caso de uso de datos
                self.data_use_case = create_fetch_market_data_use_case(self.mt5_use_case)
                
                # OBTENER HORA DEL SERVIDOR DESDE METATRADER 5
                self.fetch_server_time_from_mt5()
                
                # Actualizar información de cuenta y servidor
                self.update_account_info(result['data'])
                
                # Obtener configuraciones de indicadores del control panel
                if hasattr(self.control_panel, 'get_indicator_configurations'):
                    indicator_configs = self.control_panel.get_indicator_configurations()
                    self.chart_view.update_indicator_settings(indicator_configs)
                
                # Iniciar timers
                self.timer_server_clock.start()
                self.timer_sync_server_time.start()
                self.timer_prices.start()
                self.refresh_data()
            else:
                self.update_connection_status(False, f"❌ Error: {result['message']}")
                
        except Exception as e:
            self.update_connection_status(False, f"❌ Excepción: {str(e)}")
        finally:
            self.btn_connect.setEnabled(True)
            self.btn_connect.setText("🔌 Conectar a MT5")
    
    def fetch_server_time_from_mt5(self):
        """Obtener hora del servidor directamente desde MetaTrader 5."""
        if not self.is_connected:
            return
        
        try:
            # Usar la API de MetaTrader5 directamente para obtener la hora del servidor
            server_time_dt = mt5.time_trade_server()
            
            if server_time_dt:
                # Convertir a datetime
                self.server_time = datetime.fromtimestamp(server_time_dt)
                
                # Determinar zona horaria basada en el servidor
                self.determine_server_timezone()
                
                # Formatear para mostrar
                date_str = self.server_time.strftime("%d/%m/%Y")
                time_str = self.server_time.strftime("%H:%M:%S")
                
                # Actualizar display inmediatamente
                self.lbl_server_time.setText(f"🕒 Hora servidor: {date_str} {time_str} ({self.server_timezone})")
            else:
                # Fallback: usar hora local
                self.server_time = datetime.now()
                self.server_timezone = "LOCAL"
                self.lbl_server_time.setText(f"🕒 Hora local: {self.server_time.strftime('%d/%m/%Y %H:%M:%S')}")
                
        except Exception as e:
            # Fallback a hora local
            self.server_time = datetime.now()
            self.server_timezone = "LOCAL"
            self.lbl_server_time.setText(f"🕒 Hora local: {self.server_time.strftime('%d/%m/%Y %H:%M:%S')}")
    
    def determine_server_timezone(self):
        """Determinar zona horaria del servidor basado en su nombre."""
        if not self.server_name:
            self.server_timezone = "UTC"
            return
        
        server_lower = self.server_name.lower()
        
        # Detectar zonas horarias comunes por nombre de servidor
        if any(x in server_lower for x in ['london', 'uk', 'gb', 'fca', 'fca-regulated']):
            self.server_timezone = "GMT"
        elif any(x in server_lower for x in ['new york', 'ny', 'us', 'nfa', 'america']):
            self.server_timezone = "EST"
        elif any(x in server_lower for x in ['chicago', 'cme']):
            self.server_timezone = "CST"
        elif any(x in server_lower for x in ['sydney', 'australia', 'asic']):
            self.server_timezone = "AEST"
        elif any(x in server_lower for x in ['tokyo', 'japan']):
            self.server_timezone = "JST"
        elif any(x in server_lower for x in ['hong kong', 'singapore', 'asia']):
            self.server_timezone = "HKT/SGT"
        elif any(x in server_lower for x in ['cyprus', 'cysec']):
            self.server_timezone = "EET"
        elif any(x in server_lower for x in ['demo', 'test', 'practice']):
            # Para servidores demo, usualmente UTC
            self.server_timezone = "UTC"
        else:
            # Por defecto UTC
            self.server_timezone = "UTC"
    
    def disconnect_from_mt5(self):
        """Desconectar de MT5."""
        if self.mt5_use_case:
            self.mt5_use_case.disconnect()
            self.is_connected = False
            self.server_name = "No conectado"
            self.server_time = None
            self.server_timezone = "UTC"
            self.update_connection_status(False, "❌ Desconectado")
            
            # Detener todos los timers
            self.timer_prices.stop()
            self.timer_server_clock.stop()
            self.timer_sync_server_time.stop()
            
            # Actualizar información del servidor
            self.lbl_server_name.setText("No conectado")
            self.lbl_server_name.setStyleSheet("font-weight: bold; color: #ff6b6b; font-size: 12px;")
            
            # Actualizar información de cuenta
            self.lbl_account_info.setText("--")
            self.lbl_account_info.setStyleSheet("font-weight: bold; color: #aaa; font-size: 12px;")
            
            # Resetear hora del servidor
            self.lbl_server_time.setText("🕒 Hora servidor: --/--/---- --:--:-- (UTC)")
            
            # Actualizar paneles
            self.control_panel.update_connection_status(False)
    
    def update_connection_status(self, connected, message):
        """Actualizar estado de conexión en UI."""
        self.is_connected = connected
        self.lbl_connection_status.setText(message)
        
        if connected:
            self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #4cd964;")
            self.btn_connect.setText("🔌 Desconectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.disconnect_from_mt5)
            
            # Actualizar información del servidor
            self.lbl_server_name.setText(self.server_name)
            self.lbl_server_name.setStyleSheet("font-weight: bold; color: #4cd964; font-size: 12px;")
            
            # Actualizar modo
            if "demo" in self.server_name.lower():
                self.lbl_status_info.setText("Versión 1.0 | Modo: Demo")
            elif "real" in self.server_name.lower() or "live" in self.server_name.lower():
                self.lbl_status_info.setText("Versión 1.0 | Modo: Real")
            else:
                self.lbl_status_info.setText("Versión 1.0 | Modo: Desconocido")
        else:
            self.lbl_connection_status.setStyleSheet("font-weight: bold; color: #ff6b6b;")
            self.btn_connect.setText("🔌 Conectar a MT5")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.connect_to_mt5)
            self.lbl_status_info.setText("Versión 1.0 | Modo: Desconectado")
        
        # Actualizar panel de control
        self.control_panel.update_connection_status(connected, message)
    
    def update_account_info(self, data):
        """Actualizar información de cuenta."""
        try:
            if 'account_info' in data:
                acc_info = data['account_info']
                
                # Formatear información de cuenta
                account_number = str(acc_info.get('login', '--'))
                account_name = str(acc_info.get('name', 'Sin nombre'))
                account_type = "Demo" if acc_info.get('trade_mode', 0) == 0 else "Real"
                
                # Limitar longitud del nombre si es muy largo
                if len(account_name) > 20:
                    account_name = account_name[:17] + "..."
                
                # Actualizar etiquetas
                account_text = f"{account_number} - {account_type}"
                self.lbl_account_info.setText(account_text)
                self.lbl_account_info.setStyleSheet("font-weight: bold; color: #ffa500; font-size: 12px;")
                
                # Pasar información al panel de control
                self.control_panel.update_account_info(acc_info)
                
        except Exception as e:
            self.lbl_account_info.setText("Error")
            self.lbl_account_info.setStyleSheet("font-weight: bold; color: #ff6b6b; font-size: 12px;")
    
    # ===== MÉTODOS DE DATOS =====
    
    def refresh_data(self):
        """Actualizar datos del mercado."""
        if not self.is_connected or not self.data_use_case:
            return
        
        try:
            # Obtener datos históricos CON CANTIDAD DE VELAS CONFIGURABLE
            result = self.data_use_case.get_historical_data(
                symbol=self.current_symbol,
                timeframe=self.current_timeframe,
                count=self.current_candles_count  # Usar cantidad configurable
            )
            
            if result['success']:
                data = result['data']
                symbol_info = result.get('symbol_info')
                
                # Obtener datos en tiempo real para precio actual
                real_time_result = self.data_use_case.get_real_time_data(self.current_symbol)
                real_time_data = None
                if real_time_result['success']:
                    real_time_data = real_time_result['data']
                    if not symbol_info:
                        symbol_info = real_time_result.get('symbol_info')
                
                # Obtener configuraciones de indicadores
                indicator_configs = {}
                if hasattr(self.control_panel, 'get_indicator_configurations'):
                    indicator_configs = self.control_panel.get_indicator_configurations()
                
                # Actualizar gráfico con la información
                self.chart_view.update_chart(
                    data, 
                    indicator_configs  # Pasar configuraciones de indicadores
                )
                
                # Actualizar precios en el panel de control
                if real_time_data:
                    self.control_panel.update_price_display(real_time_data)
                
                # Actualizar contador de velas
                self.lbl_data_count.setText(f"Velas: {len(data)}")
                self.lbl_candles_count.setText(f"{len(data)}")
                self.lbl_status_data.setText(f"Datos: {len(data)} velas cargadas")
                
                # Log de información
                self.control_panel.add_log_message(f"📊 {len(data)} velas cargadas para {self.current_symbol} ({self.current_timeframe})", "DATA")
                
        except Exception as e:
            self.control_panel.add_log_message(f"❌ Error al cargar datos: {str(e)}", "ERROR")
    
    def update_prices(self):
        """Actualizar precios en tiempo real."""
        if not self.is_connected or not self.data_use_case:
            return
        
        try:
            # Obtener datos en tiempo real
            result = self.data_use_case.get_real_time_data(self.current_symbol)
            
            if result['success']:
                data = result['data']
                
                # Actualizar precios en el gráfico
                self.chart_view.update_price_display(data)
                
                # Actualizar precios en el panel de control
                self.control_panel.update_price_display(data)
                
        except Exception as e:
            pass
    
    def refresh_positions(self):
        """Actualizar lista de posiciones."""
        if not self.is_connected:
            return
        
        # Aquí puedes agregar lógica para obtener posiciones reales
    
    # ===== MÉTODOS DE TRADING =====
    
    def on_buy_requested(self, order_details):
        """Manejador para solicitud de compra."""
        # Aquí integrarías con el caso de uso open_position
        pass
    
    def on_sell_requested(self, order_details):
        """Manejador para solicitud de venta."""
        # Aquí integrarías con el caso de uso open_position
        pass
    
    # ===== MANEJADORES DE EVENTOS =====
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        
        # Sincronizar chart view
        self.chart_view.current_symbol = symbol
        
        # Sincronizar control panel
        self.control_panel.current_symbol = symbol
        
        if self.is_connected:
            self.refresh_data()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.current_timeframe = timeframe
        
        # Sincronizar chart view
        self.chart_view.current_timeframe = timeframe
        
        # Sincronizar control panel
        self.control_panel.cmb_timeframe.blockSignals(True)
        self.control_panel.cmb_timeframe.setCurrentText(timeframe)
        self.control_panel.cmb_timeframe.blockSignals(False)
        
        if self.is_connected:
            self.refresh_data()
    
    def on_candles_count_changed(self, count):
        """Manejador para cambio en cantidad de velas."""
        self.current_candles_count = count
        self.lbl_candles_count.setText(f"{count}")
        
        if self.is_connected:
            self.refresh_data()
    
    def on_indicator_settings_changed(self, indicator_name, settings):
        """Manejador para cambio de configuración de indicador."""
        # Obtener configuraciones actualizadas
        if hasattr(self.control_panel, 'get_indicator_configurations'):
            indicator_configs = self.control_panel.get_indicator_configurations()
            
            # Actualizar chart view
            self.chart_view.update_indicator_settings(indicator_configs)
            
            # Refrescar datos si está conectado
            if self.is_connected:
                self.refresh_data()
    
    def sync_ui_with_panels(self):
        """Sincronizar la UI superior con los paneles."""
        # No es necesario sincronizar controles removidos
        pass
    
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


# Función para ejecutar la aplicación
def run_application():
    """Ejecutar la aplicación."""
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()
    
    # Ejecutar aplicación
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_application()