# src/presentation/main_window.py
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QTextEdit, QTabWidget,
                             QSplitter, QGroupBox, QGridLayout, QMessageBox,QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import pyqtgraph as pg
import numpy as np
from datetime import datetime

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
        
        # Configurar UI
        self.setup_ui()
        self.setup_timers()
        
        # Intentar conexión automática si está configurado
        if hasattr(settings, 'AUTO_CONNECT') and settings.AUTO_CONNECT:
            QTimer.singleShot(1000, self.connect_to_mt5)
    
    def setup_ui(self):
        """Configurar la interfaz de usuario."""
        self.setWindowTitle("Rotherick's Trading Platform")
        self.setGeometry(100, 100, 1400, 800)
        
        # Tema oscuro
        self.set_dark_theme()
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 1. Cabecera con título y estado de conexión
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)
        
        # 2. Barra superior simplificada
        top_bar = self.create_top_bar()
        main_layout.addLayout(top_bar)
        
        # 3. Área principal dividida
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo (gráfico) - Usar ChartView personalizado
        self.chart_view = ChartView()
        splitter.addWidget(self.chart_view)
        
        # Panel derecho (control) - Usar ControlPanel personalizado
        self.control_panel = ControlPanel()
        splitter.addWidget(self.control_panel)
        
        # Conectar señales del control panel
        self.control_panel.connect_requested.connect(self.connect_to_mt5)
        self.control_panel.disconnect_requested.connect(self.disconnect_from_mt5)
        self.control_panel.symbol_changed.connect(self.on_symbol_changed)
        self.control_panel.timeframe_changed.connect(self.on_timeframe_changed)
        self.control_panel.buy_requested.connect(self.on_buy_requested)
        self.control_panel.sell_requested.connect(self.on_sell_requested)
        self.control_panel.refresh_positions.connect(self.refresh_positions)
        
        # Conectar señales del chart view
        self.chart_view.symbol_changed.connect(self.on_symbol_changed)
        self.chart_view.timeframe_changed.connect(self.on_timeframe_changed)
        
        # Configurar tamaños relativos
        splitter.setSizes([1000, 400])
        
        main_layout.addWidget(splitter)
        
        # 4. Barra inferior (logs)
        self.txt_mini_log = QTextEdit()
        self.txt_mini_log.setMaximumHeight(100)
        self.txt_mini_log.setReadOnly(True)
        self.txt_mini_log.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ccc;
                font-family: monospace;
                font-size: 10px;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        self.txt_mini_log.setPlaceholderText("Logs de la aplicación...")
        
        main_layout.addWidget(self.txt_mini_log)
        
        # 5. Barra de estado
        self.setup_status_bar()
    
    def create_header(self):
        """Crear cabecera con título grande."""
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
        
        # Línea separadora
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #444; margin: 5px 0px;")
        separator.setMaximumHeight(2)
        
        header_layout.addWidget(title_label)
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
        
        # Separador
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
        layout.addStretch()
        layout.addWidget(self.lbl_status_info)
        
        return layout
    
    def setup_status_bar(self):
        """Configurar barra de estado."""
        self.statusBar().showMessage("Listo")
        
        # Etiquetas de estado
        self.lbl_status_data = QLabel("Datos: Esperando conexión")
        self.lbl_status_data.setStyleSheet("color: #aaa;")
        
        self.lbl_status_time = QLabel("--:--:--")
        self.lbl_status_time.setStyleSheet("color: #0af; font-weight: bold;")
        
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
                
                # Actualizar información de cuenta y servidor
                self.update_account_info(result['data'])
                
                # Sincronizar controles con los paneles
                self.sync_ui_with_panels()
                
                # Iniciar actualización de precios
                self.timer_prices.start()
                self.refresh_data()
                
                self.log_message(f"✅ Conectado exitosamente a MT5")
                self.log_message(f"   Servidor: {server_info}")
                if 'account_info' in result['data']:
                    acc_info = result['data']['account_info']
                    self.log_message(f"   Cuenta: {acc_info.get('login', 'N/A')}")
                    self.log_message(f"   Nombre: {acc_info.get('name', 'N/A')}")
            else:
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
            self.server_name = "No conectado"
            self.update_connection_status(False, "❌ Desconectado")
            self.timer_prices.stop()
            
            # Actualizar información del servidor
            self.lbl_server_name.setText("No conectado")
            self.lbl_server_name.setStyleSheet("font-weight: bold; color: #ff6b6b; font-size: 12px;")
            
            # Actualizar información de cuenta
            self.lbl_account_info.setText("--")
            self.lbl_account_info.setStyleSheet("font-weight: bold; color: #aaa; font-size: 12px;")
            
            # Actualizar paneles
            self.control_panel.update_connection_status(False)
            
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
            self.log_message(f"⚠️ Error actualizando cuenta: {str(e)}")
            self.lbl_account_info.setText("Error")
            self.lbl_account_info.setStyleSheet("font-weight: bold; color: #ff6b6b; font-size: 12px;")
    
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
            
            if result['success']:
                data = result['data']
                symbol_info = result.get('symbol_info')
                server_time = result.get('server_time')
                
                self.log_message(f"📊 Datos obtenidos: {len(data)} velas")
                
                # Obtener datos en tiempo real para precio actual
                real_time_result = self.data_use_case.get_real_time_data(self.current_symbol)
                real_time_data = None
                if real_time_result['success']:
                    real_time_data = real_time_result['data']
                    # Usar la misma información del símbolo y hora del servidor
                    if not symbol_info:
                        symbol_info = real_time_result.get('symbol_info')
                    if not server_time:
                        server_time = real_time_result.get('server_time')
                
                # Actualizar gráfico con TODA la información
                self.chart_view.update_chart(
                    data, 
                    real_time_data,
                    symbol_info,
                    server_time
                )
                
                # Actualizar precios en el panel de control
                if real_time_data:
                    self.control_panel.update_price_display(real_time_data)
                
                self.lbl_status_data.setText(f"Datos: {len(data)} velas")
            else:
                self.log_message(f"❌ Error obteniendo datos: {result['message']}")
                
        except Exception as e:
            self.log_message(f"❌ Error refrescando datos: {str(e)}")
    
    def update_prices(self):
        """Actualizar precios en tiempo real."""
        if not self.is_connected or not self.data_use_case:
            return
        
        try:
            # Obtener datos en tiempo real
            result = self.data_use_case.get_real_time_data(self.current_symbol)
            
            if result['success']:
                data = result['data']
                symbol_info = result.get('symbol_info')
                server_time = result.get('server_time')
                
                # Actualizar precios en el gráfico
                self.chart_view.update_price_display(data)
                
                # Actualizar precios en el panel de control
                self.control_panel.update_price_display(data)
                
                # Actualizar hora del servidor en el gráfico
                if server_time:
                    self.chart_view.server_time = server_time
                
        except Exception as e:
            self.log_message(f"❌ Error actualizando precios: {str(e)}")
    
    def refresh_positions(self):
        """Actualizar lista de posiciones."""
        if not self.is_connected:
            return
        
        # Aquí puedes agregar lógica para obtener posiciones reales
        self.log_message("🔄 Actualizando posiciones...")
    
    # ===== MÉTODOS DE TRADING =====
    
    def on_buy_requested(self, order_details):
        """Manejador para solicitud de compra."""
        self.log_message(f"📤 Solicitando COMPRA: {order_details}")
        # Aquí integrarías con el caso de uso open_position
    
    def on_sell_requested(self, order_details):
        """Manejador para solicitud de venta."""
        self.log_message(f"📤 Solicitando VENTA: {order_details}")
        # Aquí integrarías con el caso de uso open_position
    
    # ===== MANEJADORES DE EVENTOS =====
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.log_message(f"📈 Símbolo cambiado a: {symbol}")
        
        # Sincronizar chart view
        self.chart_view.current_symbol = symbol
        
        # Sincronizar control panel
        self.control_panel.current_symbol = symbol
        
        if self.is_connected:
            self.refresh_data()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.current_timeframe = timeframe
        self.log_message(f"⏰ Timeframe cambiado a: {timeframe}")
        
        # Sincronizar chart view
        self.chart_view.current_timeframe = timeframe
        
        # Sincronizar control panel
        self.control_panel.cmb_timeframe.blockSignals(True)
        self.control_panel.cmb_timeframe.setCurrentText(timeframe)
        self.control_panel.cmb_timeframe.blockSignals(False)
        
        if self.is_connected:
            self.refresh_data()
    
    def sync_ui_with_panels(self):
        """Sincronizar la UI superior con los paneles."""
        # No es necesario sincronizar controles removidos
        pass
    
    # ===== UTILIDADES =====
    
    def log_message(self, message):
        """Agregar mensaje a los logs."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Mini log
        self.txt_mini_log.append(log_entry)
        
        # Mantener mini log limitado
        lines = self.txt_mini_log.toPlainText().split('\n')
        if len(lines) > 10:
            self.txt_mini_log.setPlainText('\n'.join(lines[-10:]))
        
        # Auto-scroll
        scrollbar = self.txt_mini_log.verticalScrollBar()
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