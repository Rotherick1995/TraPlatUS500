# src/infrastructure/ui/control_panel.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt5.QtCore import pyqtSignal

# Importar las pestañas modularizadas
from src.infrastructure.ui.trading_panel import TradingPanel
from src.infrastructure.ui.indicators_panel import IndicatorsPanel


class ControlPanel(QWidget):
    """Panel de control simplificado con pestaña de Trading e Indicadores."""
    
    # Señales necesarias para la comunicación
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)
    sell_requested = pyqtSignal(dict)
    refresh_positions = pyqtSignal()
    indicators_updated = pyqtSignal(dict)
    candles_count_changed = pyqtSignal(int)
    log_message_received = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado básico
        self.is_connected = False
        
        # Instancias de las pestañas modularizadas
        self.trading_panel = None
        self.indicators_panel = None
        
        # Inicializar UI
        self.init_ui()
        
        # Conectar señal de logs
        self.log_message_received.connect(self.add_log_message)
        
        # Agregar mensaje inicial al log
        self.add_log_message("✅ Panel de Control inicializado", "INFO")
    
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Crear pestañas
        self.tab_widget = QTabWidget()
        
        # Crear pestañas modularizadas
        self.tab_trading = self.create_trading_tab()
        self.tab_indicators = self.create_indicators_tab()
        
        # Agregar pestañas al widget
        self.tab_widget.addTab(self.tab_trading, "📊 Trading")
        self.tab_widget.addTab(self.tab_indicators, "📈 Indicadores")
        
        layout.addWidget(self.tab_widget)
    
    def create_trading_tab(self):
        """Crear pestaña de trading usando el panel modularizado."""
        # Crear instancia del panel de trading
        self.trading_panel = TradingPanel()
        
        # Conectar señales del trading panel a las señales del ControlPanel
        self.trading_panel.connect_requested.connect(self.connect_requested)
        self.trading_panel.disconnect_requested.connect(self.disconnect_requested)
        self.trading_panel.symbol_changed.connect(self.symbol_changed)
        self.trading_panel.timeframe_changed.connect(self.timeframe_changed)
        self.trading_panel.buy_requested.connect(self.buy_requested)
        self.trading_panel.sell_requested.connect(self.sell_requested)
        self.trading_panel.refresh_requested.connect(self.refresh_positions)
        self.trading_panel.log_message.connect(self.log_message_received)
        
        return self.trading_panel
    
    def create_indicators_tab(self):
        """Crear pestaña de indicadores usando el panel modularizado."""
        # Crear instancia del panel de indicadores
        self.indicators_panel = IndicatorsPanel()
        
        # Conectar señales del indicators panel a las señales del ControlPanel
        self.indicators_panel.indicators_updated.connect(self.indicators_updated)
        self.indicators_panel.log_message.connect(self.log_message_received)
        
        return self.indicators_panel
    
    # ===== MÉTODOS DE ESTADO (INTERFAZ PÚBLICA) =====
    
    def update_connection_status(self, connected, message="", server_info=""):
        """Actualizar estado de conexión."""
        self.is_connected = connected
        
        # Actualizar trading panel si existe
        if self.trading_panel:
            self.trading_panel.update_connection_status(connected, message)
        
        if connected:
            self.add_log_message(f"✅ Conectado a MT5 - {server_info}", "CONNECTION")
        else:
            if message:
                self.add_log_message(f"❌ Desconectado: {message}", "ERROR")
    
    def update_account_info(self, account_info):
        """Actualizar información de cuenta."""
        # Método vacío ya que no tenemos panel de cuenta
        # Se mantiene por compatibilidad con MainWindow
        pass
    
    def update_price_display(self, price_data):
        """Actualizar display de precios."""
        if self.trading_panel:
            self.trading_panel.update_price_display(price_data)
    
    def update_symbol(self, symbol):
        """Actualizar símbolo actual."""
        if self.trading_panel and hasattr(self.trading_panel, 'cmb_symbol'):
            self.trading_panel.cmb_symbol.blockSignals(True)
            self.trading_panel.cmb_symbol.setCurrentText(symbol)
            self.trading_panel.cmb_symbol.blockSignals(False)
    
    def update_timeframe(self, timeframe):
        """Actualizar timeframe actual."""
        if self.trading_panel and hasattr(self.trading_panel, 'cmb_timeframe'):
            self.trading_panel.cmb_timeframe.blockSignals(True)
            self.trading_panel.cmb_timeframe.setCurrentText(timeframe)
            self.trading_panel.cmb_timeframe.blockSignals(False)
    
    def update_candles_count(self, count):
        """Actualizar cantidad de velas (si es necesario)."""
        # Si tu trading_panel tiene control de cantidad de velas, actualízalo aquí
        pass
    
    # ===== MÉTODOS DE LOGS =====
    
    def add_log_message(self, message, msg_type="INFO"):
        """Agregar un mensaje al log."""
        try:
            # Solo imprimir en consola para debug
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Imprimir en consola con colores
            if msg_type == "ERROR":
                print(f"\033[91m[CPanel] [{timestamp}] {message}\033[0m")  # Rojo
            elif msg_type == "WARNING":
                print(f"\033[93m[CPanel] [{timestamp}] {message}\033[0m")  # Amarillo
            elif msg_type == "INFO":
                print(f"\033[92m[CPanel] [{timestamp}] {message}\033[0m")  # Verde
            else:
                print(f"[CPanel] [{timestamp}] {message}")
            
        except Exception as e:
            print(f"Error en add_log_message: {e}")
    
    # ===== MÉTODOS PARA ACCEDER A LOS PANELES =====
    
    def get_trading_panel(self):
        """Obtener referencia al panel de trading."""
        return self.trading_panel
    
    def get_indicators_panel(self):
        """Obtener referencia al panel de indicadores."""
        return self.indicators_panel
    
    def get_current_indicator_config(self):
        """Obtener configuración actual de indicadores."""
        if self.indicators_panel:
            return self.indicators_panel.get_current_config()
        return {}