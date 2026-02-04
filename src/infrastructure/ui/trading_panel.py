# src/infrastructure/ui/trading_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QPushButton, QComboBox, QDoubleSpinBox,
                             QSpinBox, QLineEdit, QGridLayout, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QCheckBox, QRadioButton, QButtonGroup,
                             QDialog, QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QBrush
import datetime
import MetaTrader5 as mt5
import sys
from pathlib import Path

# Agregar configuración
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

try:
    from src.config.settings import *
    SETTINGS_LOADED = True
except ImportError:
    SETTINGS_LOADED = False
    print("⚠️ No se pudo cargar la configuración, usando valores por defecto")


class TradingPanel(QWidget):
    """Pestaña de Trading modularizada para ControlPanel."""
    
    # Señales que debe manejar el ControlPanel principal
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)
    sell_requested = pyqtSignal(dict)
    market_order_requested = pyqtSignal(dict)
    pending_order_requested = pyqtSignal(dict)
    modify_order_requested = pyqtSignal(dict)
    delete_order_requested = pyqtSignal(dict)
    close_position_requested = pyqtSignal(dict)
    modify_position_requested = pyqtSignal(dict)
    refresh_requested = pyqtSignal()
    log_message = pyqtSignal(str, str)  # message, type
    
    # NUEVA SEÑAL: Cantidad de velas a cargar
    candles_to_load_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado
        self.is_connected = False
        self.current_symbol = DEFAULT_SYMBOL if SETTINGS_LOADED else "US500"
        self.current_timeframe = "H1"
        
        # Configuración por defecto basada en el script de prueba
        if SETTINGS_LOADED:
            self.default_volume = DEFAULT_LOT_SIZE
        else:
            self.default_volume = 0.1  # US500_MIN_VOLUME del script de prueba
        
        # AHORA LOS VALORES POR DEFECTO SON EN PRECIOS
        self.default_sl_price = 6495.00  # Ejemplo: 5 puntos debajo de 6500
        self.default_tp_price = 6505.00  # Ejemplo: 5 puntos arriba de 6500
        
        # NUEVO: Cantidad de velas por defecto
        self.default_candles_to_load = 500
        
        # Precios actuales
        self.current_bid = 0.0
        self.current_ask = 0.0
        
        # Información de símbolos (actualizada dinámicamente)
        self.symbol_info = {}
        
        # Timer para actualizar precios y órdenes
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_prices_and_orders)
        self.update_interval = 1000  # 1 segundo
        
        # Inicializar UI
        self.init_ui()
        
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 1. Grupo de conexión
        group_connection = self.create_connection_group()
        layout.addWidget(group_connection)
        
        # 2. Crear pestañas
        self.tab_widget = QTabWidget()
        
        # Pestaña 1: Trading rápido
        self.quick_trading_tab = self.create_quick_trading_tab()
        self.tab_widget.addTab(self.quick_trading_tab, "⚡ Trading Rápido")
        
        # Pestaña 2: Posiciones y Órdenes Pendientes (COMBINADAS)
        self.positions_orders_tab = self.create_positions_orders_tab()
        self.tab_widget.addTab(self.positions_orders_tab, "📊 Posiciones")
        
        # NO AGREGAR PESTAÑA DE CALCULADORA
        layout.addWidget(self.tab_widget)
        layout.addStretch()
        
        # Cargar información inicial de símbolos DESPUÉS de crear la UI
        self.load_initial_symbol_info()
    
    def load_initial_symbol_info(self):
        """Cargar información inicial de símbolos."""
        # Valores por defecto basados en el script de prueba
        default_info = {
            'US500': {
                'digits': 2,
                'point': 0.01,
                'pip_value': 0.1,  # 1 pip = 10 puntos para US500
                'pip_position': 1,
                'volume_min': 0.1,  # US500_MIN_VOLUME del script de prueba
                'volume_max': 10.0,  # US500_MAX_VOLUME del script de prueba
                'volume_step': 0.1,  # US500_VOLUME_STEP del script de prueba
                'spread': 0.0,
                'trade_mode': 0,
                'visible': True
            },
            'EURUSD': {
                'digits': 5,
                'point': 0.00001,
                'pip_value': 0.0001,
                'pip_position': 4,
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01,
                'spread': 0.0,
                'trade_mode': 0,
                'visible': True
            },
            'GBPUSD': {
                'digits': 5,
                'point': 0.00001,
                'pip_value': 0.0001,
                'pip_position': 4,
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01,
                'spread': 0.0,
                'trade_mode': 0,
                'visible': True
            },
            'USDJPY': {
                'digits': 3,
                'point': 0.001,
                'pip_value': 0.01,
                'pip_position': 2,
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01,
                'spread': 0.0,
                'trade_mode': 0,
                'visible': True
            },
            'XAUUSD': {
                'digits': 2,
                'point': 0.01,
                'pip_value': 0.1,
                'pip_position': 1,
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01,
                'spread': 0.0,
                'trade_mode': 0,
                'visible': True
            }
        }
        self.symbol_info = default_info
        
        # Actualizar volumen según el símbolo actual
        if self.current_symbol in self.symbol_info:
            info = self.symbol_info[self.current_symbol]
            min_volume = info.get('volume_min', 0.01)
            step = info.get('volume_step', 0.01)
            
            # Configurar spinbox de volumen
            self.spin_volume.setMinimum(min_volume)
            self.spin_volume.setSingleStep(step)
            
            # Si el volumen actual es menor que el mínimo, ajustarlo
            if self.spin_volume.value() < min_volume:
                self.spin_volume.setValue(min_volume)
    
    def update_symbol_info_from_mt5(self, symbol):
        """Actualizar información del símbolo desde MT5."""
        if not self.is_connected:
            return False
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info:
            # Convertir pip_value según el script de prueba
            point = symbol_info.point
            digits = symbol_info.digits
            
            # Para US500 y XAUUSD, 1 pip = 10 puntos
            # Para forex con 5 dígitos, 1 pip = 10 puntos
            if digits == 2 or digits == 5:
                pip_value = point * 10
            else:
                pip_value = point * 10
            
            self.symbol_info[symbol] = {
                'digits': digits,
                'point': point,
                'pip_value': pip_value,
                'pip_position': 4 if digits == 5 else 2 if digits == 3 else 1,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'spread': symbol_info.ask - symbol_info.bid,
                'trade_mode': symbol_info.trade_mode,
                'visible': symbol_info.visible
            }
            
            # Actualizar la UI si es el símbolo actual
            if symbol == self.current_symbol:
                # Actualizar spinbox de volumen
                self.spin_volume.setMinimum(symbol_info.volume_min)
                self.spin_volume.setMaximum(symbol_info.volume_max)
                self.spin_volume.setSingleStep(symbol_info.volume_step)
                
                # Ajustar volumen actual si es necesario
                if self.spin_volume.value() < symbol_info.volume_min:
                    self.spin_volume.setValue(symbol_info.volume_min)
                
                # Actualizar spinboxes de órdenes pendientes para que sean en precio
                # Establecer rango apropiado según el símbolo
                current_price = symbol_info.bid
                price_range = current_price * 0.5  # ±50% del precio actual
                
                # Actualizar SL/TP en precio para órdenes a mercado
                self.spin_sl.setDecimals(digits)
                self.spin_sl.setRange(current_price - price_range, current_price + price_range)
                
                self.spin_tp.setDecimals(digits)
                self.spin_tp.setRange(current_price - price_range, current_price + price_range)
                
                # Actualizar SL/TP en precio para órdenes pendientes
                self.spin_order_sl.setDecimals(digits)
                self.spin_order_sl.setRange(current_price - price_range, current_price + price_range)
                
                self.spin_order_tp.setDecimals(digits)
                self.spin_order_tp.setRange(current_price - price_range, current_price + price_range)
            
            return True
        return False
    
    def create_connection_group(self):
        """Crear grupo de conexión CON CONTROL DE VELAS."""
        group = QGroupBox("🔗 Conexión MT5 y Configuración Gráfico")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #666;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
        """)
        
        layout = QGridLayout(group)
        
        # Botón de conexión
        self.btn_connect = QPushButton("🔌 Conectar")
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        self.btn_connect.setFixedHeight(35)
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #808080;
                color: white;
                border: 2px solid #555555;
                padding: 6px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 11px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #8a8a8a;
                border: 2px solid #666666;
            }
            QPushButton:pressed {
                background-color: #757575;
                border: 2px solid #444444;
            }
        """)
        
        # Estado de conexión
        self.lbl_connection = QLabel("❌ Desconectado")
        self.lbl_connection.setStyleSheet("color: #ff6666; font-weight: bold; font-size: 11px;")
        
        # Símbolo y timeframe
        layout.addWidget(QLabel("Símbolo:", styleSheet="color: #fff; font-size: 11px;"), 0, 2)
        self.cmb_symbol = QComboBox()
        self.cmb_symbol.addItems(["US500", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD"])
        self.cmb_symbol.setCurrentText(self.current_symbol)
        self.cmb_symbol.currentTextChanged.connect(self.on_symbol_changed)
        self.cmb_symbol.setFixedHeight(30)
        self.cmb_symbol.setFixedWidth(100)
        self.cmb_symbol.setStyleSheet(self.get_combo_style())
        
        layout.addWidget(self.cmb_symbol, 0, 3)
        
        # Timeframe
        layout.addWidget(QLabel("Timeframe:", styleSheet="color: #fff; font-size: 11px;"), 1, 2)
        self.cmb_timeframe = QComboBox()
        self.cmb_timeframe.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"])
        self.cmb_timeframe.setCurrentText(self.current_timeframe)
        self.cmb_timeframe.currentTextChanged.connect(self.on_timeframe_changed)
        self.cmb_timeframe.setFixedHeight(30)
        self.cmb_timeframe.setFixedWidth(80)
        self.cmb_timeframe.setStyleSheet(self.get_combo_style())
        
        layout.addWidget(self.cmb_timeframe, 1, 3)
        
        # NUEVO: Control de cantidad de velas a cargar
        layout.addWidget(QLabel("Velas a cargar:", styleSheet="color: #fff; font-size: 11px;"), 0, 4)
        self.spin_candles = QSpinBox()
        self.spin_candles.setRange(50, 10000)  # Rango de 50 a 10,000 velas
        self.spin_candles.setValue(self.default_candles_to_load)
        self.spin_candles.setSingleStep(50)
        self.spin_candles.setFixedHeight(30)
        self.spin_candles.setFixedWidth(100)
        self.spin_candles.setStyleSheet(self.get_spinbox_style())
        self.spin_candles.valueChanged.connect(self.on_candles_changed)
        
        # Botón para aplicar cantidad de velas
        self.btn_apply_candles = QPushButton("📊 Aplicar")
        self.btn_apply_candles.clicked.connect(self.on_apply_candles_clicked)
        self.btn_apply_candles.setFixedHeight(30)
        self.btn_apply_candles.setFixedWidth(80)
        self.btn_apply_candles.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: 1px solid #7B1FA2;
                padding: 5px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
                border: 1px solid #6A1B9A;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
                border: 1px solid #555555;
            }
        """)
        
        layout.addWidget(self.spin_candles, 0, 5)
        layout.addWidget(self.btn_apply_candles, 1, 5)
        
        # Precio actual
        self.lbl_price = QLabel("Bid: -- | Ask: --")
        self.lbl_price.setStyleSheet("color: #ffff00; font-weight: bold; font-size: 11px;")
        
        layout.addWidget(self.btn_connect, 0, 0, 1, 2)
        layout.addWidget(self.lbl_connection, 1, 0, 1, 2)
        layout.addWidget(self.lbl_price, 2, 0, 1, 6)
        
        # Botón de refresh
        self.btn_refresh = QPushButton("🔄 Actualizar Todo")
        self.btn_refresh.clicked.connect(self.on_refresh_clicked)
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.setFixedWidth(120)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
                padding: 5px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
                border: 1px solid #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
                border: 1px solid #0D47A1;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
                border: 1px solid #555555;
            }
        """)
        
        # Botón de info de símbolo
        self.btn_symbol_info = QPushButton("ℹ️ Info Símbolo")
        self.btn_symbol_info.clicked.connect(self.show_symbol_info)
        self.btn_symbol_info.setFixedHeight(30)
        self.btn_symbol_info.setFixedWidth(100)
        self.btn_symbol_info.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: 1px solid #7B1FA2;
                padding: 5px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
                border: 1px solid #6A1B9A;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
                border: 1px solid #555555;
            }
        """)
        
        layout.addWidget(self.btn_refresh, 2, 4, 1, 1)
        layout.addWidget(self.btn_symbol_info, 2, 5, 1, 1)
        
        return group
    
    def create_quick_trading_tab(self):
        """Crear pestaña de trading rápido."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        
        # Grupo de configuración para órdenes a mercado
        group_config = QGroupBox("⚙️ Configuración para Órdenes a Mercado")
        group_config.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #666;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FF9800;
            }
        """)
        
        config_layout = QGridLayout(group_config)
        
        # Volumen
        config_layout.addWidget(QLabel("Volumen (lotes):", styleSheet="color: #fff; font-size: 11px;"), 0, 0)
        self.spin_volume = QDoubleSpinBox()
        self.spin_volume.setRange(0.01, 100.0)
        self.spin_volume.setValue(self.default_volume)
        self.spin_volume.setSingleStep(0.01)
        self.spin_volume.setDecimals(2)
        self.spin_volume.valueChanged.connect(self.update_calculations)
        self.spin_volume.setFixedHeight(30)
        self.spin_volume.setStyleSheet(self.get_spinbox_style())
        config_layout.addWidget(self.spin_volume, 0, 1)
        
        # Stop Loss (AHORA EN PRECIO)
        config_layout.addWidget(QLabel("Stop Loss:", styleSheet="color: #fff; font-size: 11px;"), 1, 0)
        
        sl_layout = QHBoxLayout()
        self.spin_sl = QDoubleSpinBox()
        self.spin_sl.setRange(0, 1000000)  # Rango amplio para precios
        self.spin_sl.setValue(self.default_sl_price)
        self.spin_sl.setSingleStep(0.01)
        self.spin_sl.setDecimals(5)
        self.spin_sl.valueChanged.connect(self.update_calculations)
        self.spin_sl.setFixedHeight(30)
        self.spin_sl.setStyleSheet(self.get_spinbox_style())
        
        # REMOVIDA LA OPCIÓN USD - SOLO PRECIO
        self.cmb_sl_type = QComboBox()
        self.cmb_sl_type.addItems(["precio"])
        self.cmb_sl_type.setCurrentText("precio")
        self.cmb_sl_type.setFixedHeight(30)
        self.cmb_sl_type.setFixedWidth(80)
        self.cmb_sl_type.setStyleSheet(self.get_combo_style())
        self.cmb_sl_type.setEnabled(True)
        
        sl_layout.addWidget(self.spin_sl)
        sl_layout.addWidget(self.cmb_sl_type)
        config_layout.addLayout(sl_layout, 1, 1)
        
        # Take Profit (AHORA EN PRECIO)
        config_layout.addWidget(QLabel("Take Profit:", styleSheet="color: #fff; font-size: 11px;"), 2, 0)
        
        tp_layout = QHBoxLayout()
        self.spin_tp = QDoubleSpinBox()
        self.spin_tp.setRange(0, 2000000)  # Rango amplio para precios
        self.spin_tp.setValue(self.default_tp_price)
        self.spin_tp.setSingleStep(0.01)
        self.spin_tp.setDecimals(5)
        self.spin_tp.valueChanged.connect(self.update_calculations)
        self.spin_tp.setFixedHeight(30)
        self.spin_tp.setStyleSheet(self.get_spinbox_style())
        
        # REMOVIDA LA OPCIÓN USD - SOLO PRECIO
        self.cmb_tp_type = QComboBox()
        self.cmb_tp_type.addItems(["precio"])
        self.cmb_tp_type.setCurrentText("precio")
        self.cmb_tp_type.setFixedHeight(30)
        self.cmb_tp_type.setFixedWidth(80)
        self.cmb_tp_type.setStyleSheet(self.get_combo_style())
        self.cmb_tp_type.setEnabled(True)
        
        tp_layout.addWidget(self.spin_tp)
        tp_layout.addWidget(self.cmb_tp_type)
        config_layout.addLayout(tp_layout, 2, 1)
        
        # Comentario
        config_layout.addWidget(QLabel("Comentario:", styleSheet="color: #fff; font-size: 11px;"), 3, 0)
        self.txt_comment = QLineEdit()
        self.txt_comment.setPlaceholderText("Operación manual")
        self.txt_comment.setFixedHeight(30)
        self.txt_comment.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QLineEdit:hover {
                border: 1px solid #777;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
        config_layout.addWidget(self.txt_comment, 3, 1)
        
        # NUEVO: Información de cálculo con valores en USD
        self.lbl_calculation = QLabel("")
        self.lbl_calculation.setStyleSheet("""
            color: #FFD700;
            font-size: 10px;
            font-weight: bold;
            background-color: #2a2a2a;
            padding: 5px;
            border-radius: 3px;
            border: 1px solid #444;
        """)
        self.lbl_calculation.setWordWrap(True)
        config_layout.addWidget(self.lbl_calculation, 4, 0, 1, 2)
        
        layout.addWidget(group_config)
        
        # ESPACIO ADICIONAL entre grupo de configuración y botones de trading
        spacer = QWidget()
        spacer.setFixedHeight(10)
        layout.addWidget(spacer)
        
        # Grupo de órdenes a mercado
        group_market = QGroupBox("📈 Órdenes a Mercado")
        group_market.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #666;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
        """)
        
        market_layout = QVBoxLayout(group_market)
        market_layout.setSpacing(15)  # Más espacio entre elementos
        
        # Etiqueta para botones de trading
        label_market = QLabel("Realizar operaciones rápidas:")
        label_market.setStyleSheet("color: #fff; font-size: 11px; font-weight: bold;")
        label_market.setAlignment(Qt.AlignCenter)
        market_layout.addWidget(label_market)
        
        # Botón de COMPRA
        self.btn_buy = QPushButton("🟢 COMPRAR")
        self.btn_buy.clicked.connect(self.on_buy_market_clicked)
        self.btn_buy.setFixedHeight(35)  # Reducido de 40
        self.btn_buy.setStyleSheet("""
            QPushButton {
                background-color: #606060;
                color: white;
                border: 3px solid #4CAF50;
                padding: 5px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 11px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
                border: 3px solid #45a049;
            }
            QPushButton:pressed {
                background-color: #555555;
                border: 3px solid #3d8b40;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
                border: 3px solid #555555;
            }
        """)
        
        # Botón de VENTA
        self.btn_sell = QPushButton("🔴 VENDER")
        self.btn_sell.clicked.connect(self.on_sell_market_clicked)
        self.btn_sell.setFixedHeight(35)  # Reducido de 40
        self.btn_sell.setStyleSheet("""
            QPushButton {
                background-color: #606060;
                color: white;
                border: 3px solid #F44336;
                padding: 5px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 11px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
                border: 3px solid #d32f2f;
            }
            QPushButton:pressed {
                background-color: #555555;
                border: 3px solid #b71c1c;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
                border: 3px solid #555555;
            }
        """)
        
        # Layout horizontal para los botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_buy)
        buttons_layout.addSpacing(20)  # Espacio entre botones
        buttons_layout.addWidget(self.btn_sell)
        buttons_layout.addStretch()
        
        market_layout.addLayout(buttons_layout)
        layout.addWidget(group_market)
        
        # ESPACIO ADICIONAL entre grupo de market y grupo de órdenes pendientes
        spacer2 = QWidget()
        spacer2.setFixedHeight(10)
        layout.addWidget(spacer2)
        
        # Grupo de órdenes pendientes CON SUS PROPIOS SL/TP - CORREGIDO
        group_pending = QGroupBox("⏱ Órdenes Pendientes - Configuración Específica")
        group_pending.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #666;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FF9800;
            }
        """)
        
        pending_layout = QVBoxLayout(group_pending)
        pending_layout.setSpacing(8)  # Espacio entre elementos dentro del grupo
        
        # Tipo de orden pendiente
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo de orden:", styleSheet="color: #fff; font-size: 11px;"))
        
        self.btn_group_order_type = QButtonGroup(self)
        
        self.radio_buy_limit = QRadioButton("Buy Limit")
        self.radio_buy_stop = QRadioButton("Buy Stop")
        self.radio_sell_limit = QRadioButton("Sell Limit")
        self.radio_sell_stop = QRadioButton("Sell Stop")
        
        # Agregar botones al grupo
        self.btn_group_order_type.addButton(self.radio_buy_limit, mt5.ORDER_TYPE_BUY_LIMIT)
        self.btn_group_order_type.addButton(self.radio_buy_stop, mt5.ORDER_TYPE_BUY_STOP)
        self.btn_group_order_type.addButton(self.radio_sell_limit, mt5.ORDER_TYPE_SELL_LIMIT)
        self.btn_group_order_type.addButton(self.radio_sell_stop, mt5.ORDER_TYPE_SELL_STOP)
        
        # Establecer Buy Limit como seleccionado por defecto
        self.radio_buy_limit.setChecked(True)
        
        # Establecer estilo y agregar al layout
        for radio in [self.radio_buy_limit, self.radio_buy_stop, self.radio_sell_limit, self.radio_sell_stop]:
            radio.setStyleSheet("""
                QRadioButton {
                    color: #fff;
                    font-size: 10px;
                    padding: 2px;
                }
                QRadioButton::indicator {
                    width: 12px;
                    height: 12px;
                }
                QRadioButton::indicator:checked {
                    background-color: #4CAF50;
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                }
                QRadioButton::indicator:unchecked {
                    background-color: #333;
                    border: 2px solid #666;
                    border-radius: 6px;
                }
            """)
            type_layout.addWidget(radio)
        
        type_layout.addStretch()
        pending_layout.addLayout(type_layout)
        
        # Precio de activación
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("Precio activación:", styleSheet="color: #fff; font-size: 11px;"))
        
        self.spin_order_price = QDoubleSpinBox()
        self.spin_order_price.setRange(0, 1000000)
        self.spin_order_price.setDecimals(5)
        self.spin_order_price.setSingleStep(10)
        self.spin_order_price.setValue(5000.00)  # Valor por defecto fijo
        self.spin_order_price.setFixedHeight(30)
        self.spin_order_price.setStyleSheet(self.get_spinbox_style())
        self.spin_order_price.valueChanged.connect(self.on_order_price_changed)
        price_layout.addWidget(self.spin_order_price)
        
        # Botón para ver precio actual
        self.btn_show_current = QPushButton("Ver Actual")
        self.btn_show_current.clicked.connect(self.show_current_price)
        self.btn_show_current.setFixedHeight(30)
        self.btn_show_current.setFixedWidth(80)
        self.btn_show_current.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
                padding: 3px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #1976D2;
                border: 1px solid #1565C0;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
                border: 1px solid #555555;
            }
        """)
        price_layout.addWidget(self.btn_show_current)
        
        pending_layout.addLayout(price_layout)
        
        # Configuración ESPECÍFICA para órdenes pendientes (SL/TP en precio)
        order_sl_tp_layout = QGridLayout()
        
        # Stop Loss para orden pendiente (AHORA EN PRECIO)
        order_sl_tp_layout.addWidget(QLabel("SL orden:", styleSheet="color: #fff; font-size: 11px;"), 0, 0)
        
        order_sl_layout = QHBoxLayout()
        self.spin_order_sl = QDoubleSpinBox()
        self.spin_order_sl.setRange(0, 1000000)  # Rango amplio para precios
        self.spin_order_sl.setValue(self.default_sl_price)
        self.spin_order_sl.setSingleStep(0.01)
        self.spin_order_sl.setDecimals(5)
        self.spin_order_sl.valueChanged.connect(self.update_order_pending_calculations)
        self.spin_order_sl.setFixedHeight(30)
        self.spin_order_sl.setStyleSheet(self.get_spinbox_style())
        
        self.cmb_order_sl_type = QComboBox()
        self.cmb_order_sl_type.addItems(["precio"])
        self.cmb_order_sl_type.setFixedHeight(30)
        self.cmb_order_sl_type.setFixedWidth(80)
        self.cmb_order_sl_type.setStyleSheet(self.get_combo_style())
        self.cmb_order_sl_type.setCurrentText("precio")
        self.cmb_order_sl_type.setEnabled(True)
        
        order_sl_layout.addWidget(self.spin_order_sl)
        order_sl_layout.addWidget(self.cmb_order_sl_type)
        order_sl_tp_layout.addLayout(order_sl_layout, 0, 1)
        
        # Take Profit para orden pendiente (AHORA EN PRECIO)
        order_sl_tp_layout.addWidget(QLabel("TP orden:", styleSheet="color: #fff; font-size: 11px;"), 1, 0)
        
        order_tp_layout = QHBoxLayout()
        self.spin_order_tp = QDoubleSpinBox()
        self.spin_order_tp.setRange(0, 2000000)  # Rango amplio para precios
        self.spin_order_tp.setValue(self.default_tp_price)
        self.spin_order_tp.setSingleStep(0.01)
        self.spin_order_tp.setDecimals(5)
        self.spin_order_tp.valueChanged.connect(self.update_order_pending_calculations)
        self.spin_order_tp.setFixedHeight(30)
        self.spin_order_tp.setStyleSheet(self.get_spinbox_style())
        
        self.cmb_order_tp_type = QComboBox()
        self.cmb_order_tp_type.addItems(["precio"])
        self.cmb_order_tp_type.setFixedHeight(30)
        self.cmb_order_tp_type.setFixedWidth(80)
        self.cmb_order_tp_type.setStyleSheet(self.get_combo_style())
        self.cmb_order_tp_type.setCurrentText("precio")
        self.cmb_order_tp_type.setEnabled(True)
        
        order_tp_layout.addWidget(self.spin_order_tp)
        order_tp_layout.addWidget(self.cmb_order_tp_type)
        order_sl_tp_layout.addLayout(order_tp_layout, 1, 1)
        
        pending_layout.addLayout(order_sl_tp_layout)
        
        # NUEVO: Información de cálculo para órdenes pendientes
        self.lbl_order_calculation = QLabel("")
        self.lbl_order_calculation.setStyleSheet("""
            color: #FFA500;
            font-size: 10px;
            font-weight: bold;
            background-color: #2a2a2a;
            padding: 5px;
            border-radius: 3px;
            border: 1px solid #444;
        """)
        self.lbl_order_calculation.setWordWrap(True)
        pending_layout.addWidget(self.lbl_order_calculation)
        
        # Comentario específico para orden pendiente
        order_comment_layout = QHBoxLayout()
        order_comment_layout.addWidget(QLabel("Comentario:", styleSheet="color: #fff; font-size: 11px;"))
        
        self.txt_order_comment = QLineEdit()
        self.txt_order_comment.setPlaceholderText("Orden pendiente")
        self.txt_order_comment.setFixedHeight(30)
        self.txt_order_comment.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QLineEdit:hover {
                border: 1px solid #777;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
        order_comment_layout.addWidget(self.txt_order_comment)
        pending_layout.addLayout(order_comment_layout)
        
        # Etiqueta informativa sobre el tipo de orden seleccionado
        self.lbl_order_info = QLabel("Buy Limit: Orden de compra que se ejecuta cuando el precio BAJA al nivel especificado")
        self.lbl_order_info.setStyleSheet("""
            color: #FF9800;
            font-size: 9px;
            font-style: italic;
            background-color: #2a2a2a;
            padding: 5px;
            border-radius: 3px;
            border: 1px solid #444;
        """)
        self.lbl_order_info.setWordWrap(True)
        pending_layout.addWidget(self.lbl_order_info)
        
        # Botón de orden pendiente
        self.btn_pending_order = QPushButton("⏱ Colocar Orden Pendiente")
        self.btn_pending_order.clicked.connect(self.on_pending_order_clicked)
        self.btn_pending_order.setFixedHeight(35)
        self.btn_pending_order.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: 2px solid #F57C00;
                padding: 5px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F57C00;
                border: 2px solid #EF6C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
                border: 2px solid #E65100;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
                border: 2px solid #555555;
            }
        """)
        
        pending_layout.addWidget(self.btn_pending_order)
        
        layout.addWidget(group_pending)
        
        # Conectar señales para actualizar la información del tipo de orden
        self.radio_buy_limit.toggled.connect(self.update_order_info)
        self.radio_buy_stop.toggled.connect(self.update_order_info)
        self.radio_sell_limit.toggled.connect(self.update_order_info)
        self.radio_sell_stop.toggled.connect(self.update_order_info)
        
        return tab
    
    def create_positions_orders_tab(self):
        """Crear pestaña COMBINADA de posiciones y órdenes pendientes."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        
        # Crear pestañas dentro de esta pestaña
        inner_tab_widget = QTabWidget()
        
        # Sub-pestaña 1: Posiciones Abiertas
        positions_widget = QWidget()
        positions_layout = QVBoxLayout(positions_widget)
        
        # Tabla de posiciones
        self.table_positions = QTableWidget()
        self.table_positions.setColumnCount(11)
        self.table_positions.setHorizontalHeaderLabels([
            "Ticket", "Símbolo", "Tipo", "Volumen", "Precio", "Actual",
            "SL", "TP", "Beneficio", "Swap", "Acciones"
        ])
        
        # Ajustar anchos de columna
        header = self.table_positions.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Ticket
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Símbolo
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Volumen
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Precio
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Actual
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # SL
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # TP
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Beneficio
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Swap
        header.setSectionResizeMode(10, QHeaderView.Fixed)  # Acciones (ancho fijo)
        
        # Establecer ancho específico para columna de acciones
        self.table_positions.setColumnWidth(10, 100)
        
        self.table_positions.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: white;
                gridline-color: #444;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 2px;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 4px;
                border: 1px solid #555;
                font-weight: bold;
                font-size: 10px;
            }
        """)
        
        positions_layout.addWidget(self.table_positions)
        
        # Botones de acción para posiciones
        positions_button_layout = QHBoxLayout()
        
        self.btn_refresh_positions = QPushButton("🔄 Actualizar Posiciones")
        self.btn_refresh_positions.clicked.connect(self.refresh_positions_table)
        self.btn_refresh_positions.setFixedHeight(30)
        
        self.btn_close_position = QPushButton("❌ Cerrar Seleccionada")
        self.btn_close_position.clicked.connect(self.on_close_position_clicked)
        self.btn_close_position.setFixedHeight(30)
        self.btn_close_position.setEnabled(False)
        
        self.btn_close_all_positions = QPushButton("❌ Cerrar Todas")
        self.btn_close_all_positions.clicked.connect(self.on_close_all_positions_clicked)
        self.btn_close_all_positions.setFixedHeight(30)
        
        self.btn_modify_position = QPushButton("✏️ Modificar SL/TP")
        self.btn_modify_position.clicked.connect(self.on_modify_position_clicked)
        self.btn_modify_position.setFixedHeight(30)
        self.btn_modify_position.setEnabled(False)
        
        for btn in [self.btn_refresh_positions, self.btn_close_position, 
                   self.btn_close_all_positions, self.btn_modify_position]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #666;
                    padding: 5px;
                    font-weight: bold;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #666;
                    border: 1px solid #777;
                }
                QPushButton:pressed {
                    background-color: #444;
                    border: 1px solid #555;
                }
                QPushButton:disabled {
                    background-color: #333;
                    color: #666;
                    border: 1px solid #444;
                }
            """)
        
        positions_button_layout.addWidget(self.btn_refresh_positions)
        positions_button_layout.addWidget(self.btn_close_position)
        positions_button_layout.addWidget(self.btn_modify_position)
        positions_button_layout.addWidget(self.btn_close_all_positions)
        
        positions_layout.addLayout(positions_button_layout)
        
        # Sub-pestaña 2: Órdenes Pendientes
        orders_widget = QWidget()
        orders_layout = QVBoxLayout(orders_widget)
        orders_layout.setSpacing(8)
        
        # Agregar un mensaje informativo
        info_label = QLabel("🔄 Las órdenes pendientes se activarán automáticamente cuando el precio alcance el nivel especificado")
        info_label.setStyleSheet("""
            color: #FF9800;
            font-size: 10px;
            font-style: italic;
            background-color: #2a2a2a;
            padding: 5px;
            border-radius: 3px;
            border: 1px solid #444;
        """)
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        orders_layout.addWidget(info_label)
        
        # Tabla de órdenes pendientes
        self.table_orders = QTableWidget()
        self.table_orders.setColumnCount(10)
        self.table_orders.setHorizontalHeaderLabels([
            "Ticket", "Símbolo", "Tipo", "Volumen", "Precio", 
            "Activa en", "SL", "TP", "Comentario", "Acciones"
        ])
        
        # Ajustar anchos de columna
        header = self.table_orders.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Ticket
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Símbolo
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Volumen
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Precio
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Activa en
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # SL
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # TP
        header.setSectionResizeMode(8, QHeaderView.Stretch)          # Comentario
        header.setSectionResizeMode(9, QHeaderView.Fixed)            # Acciones (ancho fijo)
        
        # Establecer ancho específico para columna de acciones
        self.table_orders.setColumnWidth(9, 100)
        
        self.table_orders.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: white;
                gridline-color: #444;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 2px;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 4px;
                border: 1px solid #555;
                font-weight: bold;
                font-size: 10px;
            }
        """)
        
        orders_layout.addWidget(self.table_orders)
        
        # Botones de acción para órdenes
        orders_button_layout = QHBoxLayout()
        
        self.btn_refresh_orders = QPushButton("🔄 Actualizar Órdenes")
        self.btn_refresh_orders.clicked.connect(self.refresh_orders_table)
        self.btn_refresh_orders.setFixedHeight(30)
        
        self.btn_modify_order = QPushButton("✏️ Modificar Seleccionada")
        self.btn_modify_order.clicked.connect(self.on_modify_order_clicked)
        self.btn_modify_order.setFixedHeight(30)
        self.btn_modify_order.setEnabled(False)
        
        self.btn_delete_order = QPushButton("🗑️ Eliminar Seleccionada")
        self.btn_delete_order.clicked.connect(self.on_delete_order_clicked)
        self.btn_delete_order.setFixedHeight(30)
        self.btn_delete_order.setEnabled(False)
        
        self.btn_delete_all = QPushButton("🗑️ Eliminar Todas")
        self.btn_delete_all.clicked.connect(self.on_delete_all_clicked)
        self.btn_delete_all.setFixedHeight(30)
        
        for btn in [self.btn_refresh_orders, self.btn_modify_order, self.btn_delete_order, self.btn_delete_all]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #666;
                    padding: 5px;
                    font-weight: bold;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #666;
                    border: 1px solid #777;
                }
                QPushButton:pressed {
                    background-color: #444;
                    border: 1px solid #555;
                }
                QPushButton:disabled {
                    background-color: #333;
                    color: #666;
                    border: 1px solid #444;
                }
            """)
        
        orders_button_layout.addWidget(self.btn_refresh_orders)
        orders_button_layout.addWidget(self.btn_modify_order)
        orders_button_layout.addWidget(self.btn_delete_order)
        orders_button_layout.addWidget(self.btn_delete_all)
        
        orders_layout.addLayout(orders_button_layout)
        
        # Añadir sub-pestañas
        inner_tab_widget.addTab(positions_widget, "Posiciones Abiertas")
        inner_tab_widget.addTab(orders_widget, "Órdenes Pendientes")
        
        layout.addWidget(inner_tab_widget)
        
        # Conectar selección de tabla
        self.table_positions.itemSelectionChanged.connect(self.on_position_selection_changed)
        self.table_orders.itemSelectionChanged.connect(self.on_order_selection_changed)
        
        return tab
    
    def get_combo_style(self):
        """Obtener estilo para ComboBox."""
        return """
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #777;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"><polygon points="0,0 12,0 6,6" fill="white"/></svg>');
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #555;
                selection-background-color: #4CAF50;
                selection-color: white;
                outline: none;
            }
        """
    
    def get_spinbox_style(self):
        """Obtener estilo para SpinBox."""
        return """
            QDoubleSpinBox, QSpinBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QDoubleSpinBox:hover, QSpinBox:hover {
                border: 1px solid #777;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #444;
                border: 1px solid #555;
                width: 20px;
                border-radius: 2px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #555;
                border: 1px solid #666;
            }
        """
    
    def update_order_info(self):
        """Actualizar información del tipo de orden seleccionado."""
        if self.radio_buy_limit.isChecked():
            self.lbl_order_info.setText("Buy Limit: Orden de compra que se ejecuta cuando el precio BAJA al nivel especificado")
        elif self.radio_buy_stop.isChecked():
            self.lbl_order_info.setText("Buy Stop: Orden de compra que se ejecuta cuando el precio SUBE al nivel especificado")
        elif self.radio_sell_limit.isChecked():
            self.lbl_order_info.setText("Sell Limit: Orden de venta que se ejecuta cuando el precio SUBE al nivel especificado")
        elif self.radio_sell_stop.isChecked():
            self.lbl_order_info.setText("Sell Stop: Orden de venta que se ejecuta cuando el precio BAJA al nivel especificado")
        
        # NUEVO: Actualizar cálculos también
        self.update_order_pending_calculations()
    
    def on_order_price_changed(self, value):
        """Manejador para cambio en el precio de la orden pendiente."""
        # Actualizar cálculos de órdenes pendientes
        self.update_order_pending_calculations()
    
    def calculate_pnl_for_market_order(self, entry_price, sl_price, tp_price, volume, is_buy=True):
        """Calcular P&L para órdenes a mercado."""
        if sl_price == 0 and tp_price == 0:
            return (0, 0)
        
        symbol = self.current_symbol
        if symbol not in self.symbol_info:
            return (0, 0)
        
        pip_value = self.symbol_info[symbol]['pip_value']
        point = self.symbol_info[symbol]['point']
        
        # Calcular distancia en pips
        if sl_price != 0:
            sl_distance_pips = abs(entry_price - sl_price) / (point * 10)
        else:
            sl_distance_pips = 0
            
        if tp_price != 0:
            tp_distance_pips = abs(tp_price - entry_price) / (point * 10)
        else:
            tp_distance_pips = 0
        
        # Calcular USD
        value_per_pip = volume * pip_value * 100
        
        sl_usd = sl_distance_pips * value_per_pip
        tp_usd = tp_distance_pips * value_per_pip
        
        # Ajustar para venta (si no es compra, invertir)
        if not is_buy:
            # Para venta, el SL está arriba y TP abajo
            sl_usd = sl_distance_pips * value_per_pip
            tp_usd = tp_distance_pips * value_per_pip
        
        return (sl_usd, tp_usd)
    
    def calculate_pnl_for_pending_order(self, order_type, entry_price, sl_price, tp_price, volume):
        """Calcular P&L para órdenes pendientes."""
        if sl_price == 0 and tp_price == 0:
            return (0, 0)
        
        symbol = self.current_symbol
        if symbol not in self.symbol_info:
            return (0, 0)
        
        pip_value = self.symbol_info[symbol]['pip_value']
        point = self.symbol_info[symbol]['point']
        
        # Calcular distancia en pips
        sl_distance_pips = 0
        tp_distance_pips = 0
        
        if sl_price != 0:
            sl_distance_pips = abs(entry_price - sl_price) / (point * 10)
            
        if tp_price != 0:
            tp_distance_pips = abs(tp_price - entry_price) / (point * 10)
        
        # Calcular USD
        value_per_pip = volume * pip_value * 100
        
        sl_usd = sl_distance_pips * value_per_pip
        tp_usd = tp_distance_pips * value_per_pip
        
        # Para órdenes de venta, la lógica es la misma
        if order_type in [mt5.ORDER_TYPE_SELL_LIMIT, mt5.ORDER_TYPE_SELL_STOP]:
            # Para sell, el SL está arriba del precio y TP abajo
            sl_usd = sl_distance_pips * value_per_pip
            tp_usd = tp_distance_pips * value_per_pip
        
        return (sl_usd, tp_usd)
    
    def update_calculations(self):
        """Actualizar cálculos de trading para órdenes a mercado."""
        symbol = self.current_symbol
        
        if symbol not in self.symbol_info:
            self.lbl_calculation.setText("ℹ️ Seleccione un símbolo válido")
            return
        
        # Obtener precios actuales para cálculo
        bid = self.current_bid
        ask = self.current_ask
        
        if bid <= 0 or ask <= 0:
            self.lbl_calculation.setText("ℹ️ Esperando datos de precio...")
            return
        
        # Para órdenes a mercado, usar ask para compra y bid para venta como referencia
        reference_price = ask  # Usar ask como referencia para compra
        
        # Obtener valores
        sl_price = self.spin_sl.value()
        tp_price = self.spin_tp.value()
        volume = self.spin_volume.value()
        
        # Calcular P&L para COMPRA
        sl_usd, tp_usd = self.calculate_pnl_for_market_order(
            reference_price, sl_price, tp_price, volume, is_buy=True
        )
        
        # Calcular ratio riesgo/beneficio
        risk_reward = tp_usd / sl_usd if sl_usd > 0 else 0
        
        # Actualizar label con información
        if sl_price == 0 and tp_price == 0:
            self.lbl_calculation.setText("ℹ️ Sin SL/TP configurados")
        else:
            info = f"""
            📊 <b>Análisis para COMPRA:</b>
            • <font color='#FF6B6B'>Pérdida en SL:</font> ${sl_usd:.2f}
            • <font color='#4ECDC4'>Ganancia en TP:</font> ${tp_usd:.2f}
            • <b>Ratio R/B:</b> 1:{risk_reward:.2f}
            """
            self.lbl_calculation.setText(info)
    
    def update_order_pending_calculations(self):
        """Actualizar cálculos para órdenes pendientes."""
        symbol = self.current_symbol
        
        if symbol not in self.symbol_info:
            self.lbl_order_calculation.setText("ℹ️ Seleccione un símbolo válido")
            return
        
        # Obtener tipo de orden
        order_type = self.btn_group_order_type.checkedId()
        if order_type == -1:
            return
        
        # Obtener valores
        entry_price = self.spin_order_price.value()
        sl_price = self.spin_order_sl.value()
        tp_price = self.spin_order_tp.value()
        volume = self.spin_volume.value()
        
        if entry_price <= 0:
            self.lbl_order_calculation.setText("ℹ️ Establezca un precio de activación")
            return
        
        # Calcular P&L
        sl_usd, tp_usd = self.calculate_pnl_for_pending_order(
            order_type, entry_price, sl_price, tp_price, volume
        )
        
        # Determinar nombre del tipo de orden
        order_name = ""
        if order_type == mt5.ORDER_TYPE_BUY_LIMIT:
            order_name = "Buy Limit"
        elif order_type == mt5.ORDER_TYPE_BUY_STOP:
            order_name = "Buy Stop"
        elif order_type == mt5.ORDER_TYPE_SELL_LIMIT:
            order_name = "Sell Limit"
        elif order_type == mt5.ORDER_TYPE_SELL_STOP:
            order_name = "Sell Stop"
        
        # Calcular ratio riesgo/beneficio
        risk_reward = tp_usd / sl_usd if sl_usd > 0 else 0
        
        # Actualizar label
        if sl_price == 0 and tp_price == 0:
            self.lbl_order_calculation.setText(f"ℹ️ {order_name} - Sin SL/TP configurados")
        else:
            info = f"""
            📊 <b>Análisis para {order_name}:</b>
            • <font color='#FF6B6B'>Pérdida en SL:</font> ${sl_usd:.2f}
            • <font color='#4ECDC4'>Ganancia en TP:</font> ${tp_usd:.2f}
            • <b>Ratio R/B:</b> 1:{risk_reward:.2f}
            """
            self.lbl_order_calculation.setText(info)
    
    def on_connect_clicked(self):
        """Manejador para botón de conexión."""
        if not self.is_connected:
            self.connect_requested.emit()
        else:
            self.disconnect_requested.emit()
    
    def on_refresh_clicked(self):
        """Manejador para botón de refresh."""
        self.refresh_requested.emit()
        self.refresh_orders_table()
        self.refresh_positions_table()
        
        # NUEVO: Emitir señal de cantidad de velas al hacer refresh
        self.on_apply_candles_clicked()
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.symbol_changed.emit(symbol)
        
        # Actualizar información del símbolo desde MT5 si está conectado
        if self.is_connected:
            self.update_symbol_info_from_mt5(symbol)
        
        # Actualizar precios del símbolo
        self.update_price_display({'bid': self.current_bid, 'ask': self.current_ask})
        
        # Actualizar cálculos
        self.update_calculations()
        self.update_order_pending_calculations()
        
        # NUEVO: Emitir señal de velas cuando se cambia de símbolo
        self.on_apply_candles_clicked()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.current_timeframe = timeframe
        self.timeframe_changed.emit(timeframe)
        
        # NUEVO: Emitir señal de velas cuando se cambia de timeframe
        self.on_apply_candles_clicked()
    
    def on_candles_changed(self, value):
        """Manejador para cambio en la cantidad de velas."""
        # NUEVO: Emitir señal cuando se cambia el valor
        # Solo emitir si estamos conectados
        if self.is_connected:
            self.log_message.emit(f"📊 Configuradas {value} velas para cargar", "INFO")
    
    def on_apply_candles_clicked(self):
        """Manejador para aplicar la cantidad de velas."""
        candles_count = self.spin_candles.value()
        
        # NUEVO: Emitir señal con la cantidad de velas
        self.candles_to_load_changed.emit(candles_count)
        
        self.log_message.emit(f"📊 Aplicadas {candles_count} velas para {self.current_symbol} ({self.current_timeframe})", "INFO")
        
        # Mostrar mensaje informativo
        QMessageBox.information(self, "Configuración Gráfico", 
                               f"Se cargarán {candles_count} velas de {self.current_symbol} en {self.current_timeframe}")
    
    def show_current_price(self):
        """Mostrar el precio actual en un mensaje, pero no establecerlo automáticamente."""
        if not self.is_connected:
            QMessageBox.information(self, "Información", "Conéctese primero a MT5.")
            return
        
        symbol_info = mt5.symbol_info(self.current_symbol)
        if not symbol_info:
            QMessageBox.warning(self, "Error", f"No se pudo obtener información de {self.current_symbol}")
            return
        
        # Mostrar precio actual en un mensaje informativo
        msg = f"Precio actual de {self.current_symbol}:\n\n"
        msg += f"Bid (Venta): {symbol_info.bid:.{symbol_info.digits}f}\n"
        msg += f"Ask (Compra): {symbol_info.ask:.{symbol_info.digits}f}\n"
        msg += f"Spread: {symbol_info.ask - symbol_info.bid:.{symbol_info.digits}f}\n\n"
        
        # Sugerir precios según el tipo de orden seleccionado
        if self.radio_buy_limit.isChecked():
            # Buy Limit debe estar POR DEBAJO del precio actual
            suggested_price = symbol_info.bid - (symbol_info.point * 100)  # 10 pips por debajo
            msg += f"Para Buy Limit, establezca un precio por DEBAJO de {symbol_info.bid:.{symbol_info.digits}f}\n"
            msg += f"Precio sugerido: {suggested_price:.{symbol_info.digits}f}"
            
        elif self.radio_buy_stop.isChecked():
            # Buy Stop debe estar POR ENCIMA del precio actual
            suggested_price = symbol_info.bid + (symbol_info.point * 100)  # 10 pips por encima
            msg += f"Para Buy Stop, establezca un precio por ENCIMA de {symbol_info.bid:.{symbol_info.digits}f}\n"
            msg += f"Precio sugerido: {suggested_price:.{symbol_info.digits}f}"
            
        elif self.radio_sell_limit.isChecked():
            # Sell Limit debe estar POR ENCIMA del precio actual
            suggested_price = symbol_info.ask + (symbol_info.point * 100)  # 10 pips por encima
            msg += f"Para Sell Limit, establezca un precio por ENCIMA de {symbol_info.ask:.{symbol_info.digits}f}\n"
            msg += f"Precio sugerido: {suggested_price:.{symbol_info.digits}f}"
            
        elif self.radio_sell_stop.isChecked():
            # Sell Stop debe estar POR DEBAJO del precio actual
            suggested_price = symbol_info.ask - (symbol_info.point * 100)  # 10 pips por debajo
            msg += f"Para Sell Stop, establezca un precio por DEBAJO de {symbol_info.ask:.{symbol_info.digits}f}\n"
            msg += f"Precio sugerido: {suggested_price:.{symbol_info.digits}f}"
        
        QMessageBox.information(self, "Precio Actual", msg)
        
        # Actualizar el spinbox con el precio sugerido si el usuario quiere
        reply = QMessageBox.question(self, "Usar precio sugerido", 
                                    "¿Desea usar el precio sugerido en el campo de precio de activación?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if symbol_info.digits == 2:
                self.spin_order_price.setDecimals(2)
            elif symbol_info.digits == 3:
                self.spin_order_price.setDecimals(3)
            else:
                self.spin_order_price.setDecimals(5)
            
            if 'suggested_price' in locals():
                self.spin_order_price.setValue(suggested_price)
        
        # Actualizar cálculos después de cambiar el precio
        self.update_order_pending_calculations()
    
    def on_buy_market_clicked(self):
        """Manejador para orden de compra a mercado - ENVÍA DIRECTAMENTE A MT5."""
        if not self.is_connected:
            self.log_message.emit("❌ No hay conexión a MT5", "ERROR")
            QMessageBox.warning(self, "Sin conexión", "Conéctese a MT5 primero.")
            return
        
        # Verificar AutoTrading
        if not self.check_autotrading_status():
            self.log_message.emit("❌ AutoTrading deshabilitado en MT5", "WARNING")
            response = QMessageBox.warning(self, "AutoTrading deshabilitado", 
                "AutoTrading podría estar deshabilitado. ¿Continuar de todos modos?",
                QMessageBox.Yes | QMessageBox.No)
            if response != QMessageBox.Yes:
                return
        
        # Verificar que el símbolo esté disponible
        if not mt5.symbol_select(self.current_symbol, True):
            error = mt5.last_error()
            self.log_message.emit(f"❌ No se pudo seleccionar {self.current_symbol}: {error}", "ERROR")
            return
        
        symbol_info = mt5.symbol_info(self.current_symbol)
        if not symbol_info:
            self.log_message.emit(f"❌ No se pudo obtener información de {self.current_symbol}", "ERROR")
            return
        
        if symbol_info.ask <= 0:
            self.log_message.emit("❌ No se pudo obtener el precio de compra", "ERROR")
            return
        
        # Ajustar volumen según las especificaciones del símbolo
        requested_volume = self.spin_volume.value()
        adjusted_volume = self.get_appropriate_volume(requested_volume)
        
        if adjusted_volume != requested_volume:
            self.log_message.emit(f"⚠️ Volumen ajustado de {requested_volume} a {adjusted_volume}", "WARNING")
        
        # AHORA USAMOS PRECIOS DIRECTAMENTE PARA SL y TP
        price = symbol_info.ask
        
        # Obtener SL en precio
        sl_price = 0
        sl_value = self.spin_sl.value()
        
        if sl_value != 0:
            sl_price = sl_value  # Usar precio directamente
        
        # Obtener TP en precio
        tp_price = 0
        tp_value = self.spin_tp.value()
        
        if tp_value != 0:
            tp_price = tp_value  # Usar precio directamente
        
        # Calcular USD para mostrar antes de enviar
        sl_usd, tp_usd = self.calculate_pnl_for_market_order(
            price, sl_price, tp_price, adjusted_volume, is_buy=True
        )
        
        # Mostrar confirmación con valores en USD
        confirm_msg = f"""
        ¿Confirmar orden de COMPRA?
        
        Símbolo: {self.current_symbol}
        Volumen: {adjusted_volume} lotes
        Precio: {price:.5f}
        
        SL: {sl_price:.5f} (${sl_usd:.2f})
        TP: {tp_price:.5f} (${tp_usd:.2f})
        
        Comentario: {self.txt_comment.text() or 'Operación manual'}
        """
        
        reply = QMessageBox.question(self, "Confirmar COMPRA", confirm_msg, 
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        # Preparar solicitud EXACTAMENTE como en el script de prueba
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.current_symbol,
            "volume": adjusted_volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": DEFAULT_SLIPPAGE if SETTINGS_LOADED else 10,  # En puntos, no pips
            "magic": 1001,
            "comment": self.txt_comment.text() or f"BUY {self.current_symbol} {datetime.datetime.now().strftime('%H:%M')}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        self.log_message.emit(f"📈 Enviando orden de COMPRA para {self.current_symbol} ({adjusted_volume} lots)", "TRADE")
        
        # ENVIAR ORDEN DIRECTAMENTE A MT5
        result = mt5.order_send(request)
        
        # Manejar resultado
        success = self.handle_order_result(result, "COMPRA")
        
        if success:
            # Emitir señal para el ControlPanel principal
            order_data = {
                'request': request,
                'symbol': self.current_symbol,
                'volume': adjusted_volume,
                'price': price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_usd': sl_usd,
                'tp_usd': tp_usd,
                'comment': request['comment'],
                'type': 'buy_market',
                'result': result
            }
            
            self.buy_requested.emit(order_data)
        
        # Actualizar después de un momento
        QTimer.singleShot(1000, self.refresh_orders_table)
        QTimer.singleShot(1000, self.refresh_positions_table)
    
    def on_sell_market_clicked(self):
        """Manejador para orden de venta a mercado - ENVÍA DIRECTAMENTE A MT5."""
        if not self.is_connected:
            self.log_message.emit("❌ No hay conexión a MT5", "ERROR")
            QMessageBox.warning(self, "Sin conexión", "Conéctese a MT5 primero.")
            return
        
        # Verificar AutoTrading
        if not self.check_autotrading_status():
            self.log_message.emit("❌ AutoTrading deshabilitado en MT5", "WARNING")
            response = QMessageBox.warning(self, "AutoTrading deshabilitado", 
                "AutoTrading podría estar deshabilitado. ¿Continuar de todos modos?",
                QMessageBox.Yes | QMessageBox.No)
            if response != QMessageBox.Yes:
                return
        
        # Verificar que el símbolo esté disponible
        if not mt5.symbol_select(self.current_symbol, True):
            error = mt5.last_error()
            self.log_message.emit(f"❌ No se pudo seleccionar {self.current_symbol}: {error}", "ERROR")
            return
        
        symbol_info = mt5.symbol_info(self.current_symbol)
        if not symbol_info:
            self.log_message.emit(f"❌ No se pudo obtener información de {self.current_symbol}", "ERROR")
            return
        
        if symbol_info.bid <= 0:
            self.log_message.emit("❌ No se pudo obtener el precio de venta", "ERROR")
            return
        
        # Ajustar volumen según las especificaciones del símbolo
        requested_volume = self.spin_volume.value()
        adjusted_volume = self.get_appropriate_volume(requested_volume)
        
        if adjusted_volume != requested_volume:
            self.log_message.emit(f"⚠️ Volumen ajustado de {requested_volume} a {adjusted_volume}", "WARNING")
        
        # AHORA USAMOS PRECIOS DIRECTAMENTE PARA SL y TP
        price = symbol_info.bid
        
        # Obtener SL en precio
        sl_price = 0
        sl_value = self.spin_sl.value()
        
        if sl_value != 0:
            sl_price = sl_value  # Usar precio directamente
        
        # Obtener TP en precio
        tp_price = 0
        tp_value = self.spin_tp.value()
        
        if tp_value != 0:
            tp_price = tp_value  # Usar precio directamente
        
        # Calcular USD para mostrar antes de enviar
        sl_usd, tp_usd = self.calculate_pnl_for_market_order(
            price, sl_price, tp_price, adjusted_volume, is_buy=False
        )
        
        # Mostrar confirmación con valores en USD
        confirm_msg = f"""
        ¿Confirmar orden de VENTA?
        
        Símbolo: {self.current_symbol}
        Volumen: {adjusted_volume} lotes
        Precio: {price:.5f}
        
        SL: {sl_price:.5f} (${sl_usd:.2f})
        TP: {tp_price:.5f} (${tp_usd:.2f})
        
        Comentario: {self.txt_comment.text() or 'Operación manual'}
        """
        
        reply = QMessageBox.question(self, "Confirmar VENTA", confirm_msg, 
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        # Preparar solicitud EXACTAMENTE como en el script de prueba
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.current_symbol,
            "volume": adjusted_volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": DEFAULT_SLIPPAGE if SETTINGS_LOADED else 10,
            "magic": 1002,
            "comment": self.txt_comment.text() or f"SELL {self.current_symbol} {datetime.datetime.now().strftime('%H:%M')}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        self.log_message.emit(f"📉 Enviando orden de VENTA para {self.current_symbol} ({adjusted_volume} lots)", "TRADE")
        
        # ENVIAR ORDEN DIRECTAMENTE A MT5
        result = mt5.order_send(request)
        
        # Manejar resultado
        success = self.handle_order_result(result, "VENTA")
        
        if success:
            # Emitir señal para el ControlPanel principal
            order_data = {
                'request': request,
                'symbol': self.current_symbol,
                'volume': adjusted_volume,
                'price': price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_usd': sl_usd,
                'tp_usd': tp_usd,
                'comment': request['comment'],
                'type': 'sell_market',
                'result': result
            }
            
            self.sell_requested.emit(order_data)
        
        # Actualizar después de un momento
        QTimer.singleShot(1000, self.refresh_orders_table)
        QTimer.singleShot(1000, self.refresh_positions_table)
    
    def on_pending_order_clicked(self):
        """Manejador para orden pendiente - ENVÍA DIRECTAMENTE A MT5 CON SL/TP EN PRECIOS."""
        if not self.is_connected:
            self.log_message.emit("❌ No hay conexión a MT5", "ERROR")
            QMessageBox.warning(self, "Sin conexión", "Conéctese a MT5 primero.")
            return
        
        # Verificar AutoTrading
        if not self.check_autotrading_status():
            self.log_message.emit("❌ AutoTrading deshabilitado en MT5", "WARNING")
            response = QMessageBox.warning(self, "AutoTrading deshabilitado", 
                "AutoTrading podría estar deshabilitado. ¿Continuar de todos modos?",
                QMessageBox.Yes | QMessageBox.No)
            if response != QMessageBox.Yes:
                return
        
        order_type = self.btn_group_order_type.checkedId()
        if order_type == -1:
            self.log_message.emit("❌ Seleccione un tipo de orden pendiente", "ERROR")
            QMessageBox.warning(self, "Error", "Por favor, seleccione un tipo de orden pendiente.")
            return
        
        # Verificar que el símbolo esté disponible
        if not mt5.symbol_select(self.current_symbol, True):
            error = mt5.last_error()
            self.log_message.emit(f"❌ No se pudo seleccionar {self.current_symbol}: {error}", "ERROR")
            return
        
        symbol_info = mt5.symbol_info(self.current_symbol)
        if not symbol_info:
            self.log_message.emit(f"❌ No se pudo obtener información de {self.current_symbol}", "ERROR")
            return
        
        # Ajustar volumen - USANDO EL VOLUMEN ESPECÍFICO para órdenes pendientes
        requested_volume = self.spin_volume.value()
        adjusted_volume = self.get_appropriate_volume(requested_volume)
        
        if adjusted_volume != requested_volume:
            self.log_message.emit(f"⚠️ Volumen ajustado de {requested_volume} a {adjusted_volume}", "WARNING")
        
        # Obtener precio de activación
        activation_price = self.spin_order_price.value()
        
        # Obtener precio actual para validación
        current_bid = symbol_info.bid
        current_ask = symbol_info.ask
        
        # Validar que el precio de activación NO sea el precio actual o muy cercano
        tolerance = symbol_info.point * 10  # 1 pip de tolerancia
        
        # Validación específica por tipo de orden
        validation_passed = True
        error_message = ""
        
        if order_type == mt5.ORDER_TYPE_BUY_LIMIT:
            # Buy Limit debe estar POR DEBAJO del precio actual (bid)
            if activation_price >= current_bid:
                validation_passed = False
                error_message = f"Buy Limit debe colocarse POR DEBAJO del precio actual.\nPrecio actual (Bid): {current_bid:.{symbol_info.digits}f}\nPrecio ingresado: {activation_price:.{symbol_info.digits}f}"
            elif abs(activation_price - current_bid) <= tolerance:
                validation_passed = False
                error_message = f"El precio de activación está demasiado cerca del precio actual.\nDebe haber al menos {tolerance:.{symbol_info.digits}f} de diferencia."
                
        elif order_type == mt5.ORDER_TYPE_BUY_STOP:
            # Buy Stop debe estar POR ENCIMA del precio actual (bid)
            if activation_price <= current_bid:
                validation_passed = False
                error_message = f"Buy Stop debe colocarse POR ENCIMA del precio actual.\nPrecio actual (Bid): {current_bid:.{symbol_info.digits}f}\nPrecio ingresado: {activation_price:.{symbol_info.digits}f}"
            elif abs(activation_price - current_bid) <= tolerance:
                validation_passed = False
                error_message = f"El precio de activación está demasiado cerca del precio actual.\nDebe haber al menos {tolerance:.{symbol_info.digits}f} de diferencia."
                
        elif order_type == mt5.ORDER_TYPE_SELL_LIMIT:
            # Sell Limit debe estar POR ENCIMA del precio actual (ask)
            if activation_price <= current_ask:
                validation_passed = False
                error_message = f"Sell Limit debe colocarse POR ENCIMA del precio actual.\nPrecio actual (Ask): {current_ask:.{symbol_info.digits}f}\nPrecio ingresado: {activation_price:.{symbol_info.digits}f}"
            elif abs(activation_price - current_ask) <= tolerance:
                validation_passed = False
                error_message = f"El precio de activación está demasiado cerca del precio actual.\nDebe haber al menos {tolerance:.{symbol_info.digits}f} de diferencia."
                
        elif order_type == mt5.ORDER_TYPE_SELL_STOP:
            # Sell Stop debe estar POR DEBAJO del precio actual (ask)
            if activation_price >= current_ask:
                validation_passed = False
                error_message = f"Sell Stop debe colocarse POR DEBAJO del precio actual.\nPrecio actual (Ask): {current_ask:.{symbol_info.digits}f}\nPrecio ingresado: {activation_price:.{symbol_info.digits}f}"
            elif abs(activation_price - current_ask) <= tolerance:
                validation_passed = False
                error_message = f"El precio de activación está demasiado cerca del precio actual.\nDebe haber al menos {tolerance:.{symbol_info.digits}f} de diferencia."
        
        if not validation_passed:
            QMessageBox.warning(self, "Precio inválido", error_message)
            return
        
        # Obtener SL y TP EN PRECIOS directamente
        sl_price = 0
        tp_price = 0
        
        # Obtener SL en precio
        sl_value = self.spin_order_sl.value()
        
        if sl_value != 0 and sl_value > 0:
            sl_price = sl_value  # Usar precio directamente
        
        # Obtener TP en precio
        tp_value = self.spin_order_tp.value()
        
        if tp_value != 0 and tp_value > 0:
            tp_price = tp_value  # Usar precio directamente
        
        # Calcular USD para mostrar antes de enviar
        sl_usd, tp_usd = self.calculate_pnl_for_pending_order(
            order_type, activation_price, sl_price, tp_price, adjusted_volume
        )
        
        # Obtener nombre del tipo de orden
        order_type_name = self.get_order_type_name(order_type)
        
        # Mostrar confirmación con valores en USD
        confirm_msg = f"""
        ¿Confirmar {order_type_name}?
        
        Símbolo: {self.current_symbol}
        Volumen: {adjusted_volume} lotes
        Precio activación: {activation_price:.5f}
        
        SL: {sl_price:.5f} (${sl_usd:.2f})
        TP: {tp_price:.5f} (${tp_usd:.2f})
        
        Comentario: {self.txt_order_comment.text() or f'{order_type_name} {self.current_symbol}'}
        """
        
        reply = QMessageBox.question(self, f"Confirmar {order_type_name}", confirm_msg, 
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        # Preparar solicitud de orden pendiente
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.current_symbol,
            "volume": adjusted_volume,
            "type": order_type,
            "price": activation_price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": DEFAULT_SLIPPAGE if SETTINGS_LOADED else 10,
            "magic": 1000 + order_type,
            "comment": self.txt_order_comment.text() or f"{order_type_name} {self.current_symbol}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        self.log_message.emit(f"⏱ Enviando {order_type_name} para {self.current_symbol} a {activation_price:.5f} con SL:{sl_price:.5f} TP:{tp_price:.5f}", "TRADE")
        
        # ENVIAR ORDEN DIRECTAMENTE A MT5
        result = mt5.order_send(request)
        
        # Manejar resultado
        success = self.handle_order_result(result, order_type_name)
        
        if success:
            # Emitir señal
            order_data = {
                'request': request,
                'symbol': self.current_symbol,
                'volume': adjusted_volume,
                'price': activation_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_usd': sl_usd,
                'tp_usd': tp_usd,
                'comment': request['comment'],
                'order_type': order_type,
                'order_type_name': order_type_name,
                'type': 'pending',
                'result': result
            }
            
            self.pending_order_requested.emit(order_data)
            
            # Limpiar campos después de éxito
            self.spin_order_price.setValue(0.0)
            self.spin_order_sl.setValue(0)
            self.spin_order_tp.setValue(0)
            self.txt_order_comment.clear()
            
            # Actualizar después de un momento
            QTimer.singleShot(1000, self.refresh_orders_table)
    
    def handle_order_result(self, result, order_type):
        """Manejar el resultado de una orden (igual que en el script de prueba)."""
        if result is None:
            error = mt5.last_error()
            error_msg = f"❌ Error al enviar orden: {error}"
            self.log_message.emit(error_msg, "ERROR")
            
            # Manejar errores específicos
            error_code = error[0] if isinstance(error, tuple) and len(error) > 0 else 0
            
            if error_code == 10016:  # AutoTrading disabled
                error_msg = "❌ ERROR: AutoTrading deshabilitado\nPor favor, habilita AutoTrading en MT5"
                self.log_message.emit(error_msg, "ERROR")
            elif error_code == 10019:  # Trade disabled
                error_msg = "❌ ERROR: Trading deshabilitado\nVerifica que el trading esté habilitado en la cuenta"
                self.log_message.emit(error_msg, "ERROR")
            elif error_code == 10013:  # Invalid volume
                error_msg = "❌ ERROR: Volumen inválido\nVerifica el volumen mínimo del símbolo"
                self.log_message.emit(error_msg, "ERROR")
            
            return False
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            success_msg = f"✅ ORDEN DE {order_type} EXITOSA\nID Orden: {result.order}\nPrecio: {result.price:.5f}"
            self.log_message.emit(success_msg, "SUCCESS")
            QMessageBox.information(self, "Orden Exitosa", success_msg)
            return True
        else:
            error_msg = f"❌ ORDEN RECHAZADA\nRazón: {result.comment}"
            self.log_message.emit(error_msg, "ERROR")
            QMessageBox.warning(self, "Orden Rechazada", error_msg)
            
            # Errores comunes de MT5
            error_messages = {
                10004: "Requote - precio cambiado",
                10006: "Rechazada por el dealer",
                10007: "Cancelada por el cliente",
                10008: "Volumen insuficiente",
                10009: "Sin conexión",
                10010: "Timeout",
                10012: "Orden inválida",
                10013: "Volumen inválido",
                10014: "Precio inválido",
                10015: "Símbolo inválido",
                10016: "AutoTrading deshabilitado",
                10017: "No hay suficientes fondos",
                10018: "Mercado cerrado",
                10019: "Trade deshabilitado",
                10020: "Prohibido",
                10021: "Margen insuficiente",
                10022: "Posición no encontrada",
                10023: "Límite de operaciones alcanzado",
                10024: "Límite de volumen alcanzado",
                10025: "Cuenta bloqueada",
                10026: "Cuenta invalidada",
                10027: "Hedge prohibido",
                10028: "Ordenes prohibidas",
                10029: "Demasiadas solicitudes",
                10030: "Cambios no permitidos",
                10031: "Trade contexto ocupado",
                10032: "Expiración denegada",
                10033: "Demasiadas órdenes",
                10034: "No hay precios",
                10035: "Precio inválido",
                10036: "Símbolo no válido",
                10038: "Orden no válida",
                10039: "Volumen demasiado pequeño",
                10040: "Volumen demasiado grande",
            }
            
            if result.retcode in error_messages:
                detail_msg = f"Detalle: {error_messages[result.retcode]}"
                self.log_message.emit(detail_msg, "INFO")
            
            return False
    
    def on_modify_order_clicked(self):
        """Manejador para modificar orden seleccionada."""
        selected_items = self.table_orders.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Seleccionar Orden", "Por favor, seleccione una orden de la tabla.")
            return
        
        ticket_item = self.table_orders.item(selected_items[0].row(), 0)
        if not ticket_item:
            return
        
        ticket = int(ticket_item.text())
        
        # Obtener datos actuales de la orden
        order = self.get_order_by_ticket(ticket)
        if not order:
            self.log_message.emit(f"❌ No se encontró la orden {ticket}", "ERROR")
            return
        
        # Crear diálogo para modificar
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modificar Orden #{ticket}")
        dialog.setFixedWidth(300)
        
        layout = QFormLayout(dialog)
        
        # Mostrar información actual
        layout.addRow(QLabel(f"Símbolo: {order.symbol}"))
        layout.addRow(QLabel(f"Tipo: {self.get_order_type_name(order.type)}"))
        layout.addRow(QLabel(f"Precio: {order.price_open:.5f}"))
        layout.addRow(QLabel(f"Volumen: {order.volume_initial}"))
        
        # Obtener información del símbolo
        symbol_info = mt5.symbol_info(order.symbol)
        point = symbol_info.point if symbol_info else 0.00001
        
        # Calcular valores actuales en USD
        current_sl_usd = 0
        current_tp_usd = 0
        
        if order.sl != 0:
            sl_pips = abs(order.price_open - order.sl) / (point * 10)
            value_per_pip = order.volume_initial * (point * 10) * 100
            current_sl_usd = sl_pips * value_per_pip
        
        if order.tp != 0:
            tp_pips = abs(order.tp - order.price_open) / (point * 10)
            value_per_pip = order.volume_initial * (point * 10) * 100
            current_tp_usd = tp_pips * value_per_pip
        
        layout.addRow(QLabel(f"SL actual: {order.sl:.5f} (${current_sl_usd:.2f})"))
        layout.addRow(QLabel(f"TP actual: {order.tp:.5f} (${current_tp_usd:.2f})"))
        
        # Nuevo SL en precio
        sl_spin = QDoubleSpinBox()
        sl_spin.setRange(0, 1000000)
        sl_spin.setValue(order.sl if order.sl != 0 else 0)
        sl_spin.setDecimals(5)
        layout.addRow("Nuevo SL (precio):", sl_spin)
        
        # Nuevo TP en precio
        tp_spin = QDoubleSpinBox()
        tp_spin.setRange(0, 2000000)
        tp_spin.setValue(order.tp if order.tp != 0 else 0)
        tp_spin.setDecimals(5)
        layout.addRow("Nuevo TP (precio):", tp_spin)
        
        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # Usar precios directamente
            new_sl_price = sl_spin.value()
            new_tp_price = tp_spin.value()
            
            # Calcular nuevos valores en USD
            new_sl_usd = 0
            new_tp_usd = 0
            
            if new_sl_price != 0:
                sl_pips = abs(order.price_open - new_sl_price) / (point * 10)
                value_per_pip = order.volume_initial * (point * 10) * 100
                new_sl_usd = sl_pips * value_per_pip
            
            if new_tp_price != 0:
                tp_pips = abs(new_tp_price - order.price_open) / (point * 10)
                value_per_pip = order.volume_initial * (point * 10) * 100
                new_tp_usd = tp_pips * value_per_pip
            
            # Mostrar confirmación con USD
            confirm_msg = f"""
            ¿Confirmar modificación?
            
            SL: {order.sl:.5f} → {new_sl_price:.5f}
            (${current_sl_usd:.2f} → ${new_sl_usd:.2f})
            
            TP: {order.tp:.5f} → {new_tp_price:.5f}
            (${current_tp_usd:.2f} → ${new_tp_usd:.2f})
            """
            
            reply = QMessageBox.question(self, "Confirmar Modificación", confirm_msg,
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply != QMessageBox.Yes:
                return
            
            # Preparar solicitud de modificación
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "symbol": order.symbol,
                "sl": new_sl_price,
                "tp": new_tp_price,
            }
            
            self.log_message.emit(f"✏️ Modificando orden #{ticket}", "INFO")
            
            # ENVIAR MODIFICACIÓN DIRECTAMENTE A MT5
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.log_message.emit(f"✅ Orden #{ticket} modificada exitosamente", "SUCCESS")
            else:
                error = mt5.last_error() if result is None else result.comment
                self.log_message.emit(f"❌ Error al modificar orden #{ticket}: {error}", "ERROR")
            
            # Emitir señal
            modify_data = {
                'ticket': ticket,
                'sl_price': new_sl_price,
                'tp_price': new_tp_price,
                'sl_usd': new_sl_usd,
                'tp_usd': new_tp_usd,
                'symbol': order.symbol,
                'order_type': order.type,
                'action': mt5.TRADE_ACTION_MODIFY,
                'result': result
            }
            
            self.modify_order_requested.emit(modify_data)
            
            # Actualizar tabla después de un momento
            QTimer.singleShot(1000, self.refresh_orders_table)
    
    def on_delete_order_clicked(self):
        """Manejador para eliminar orden seleccionada."""
        selected_items = self.table_orders.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Seleccionar Orden", "Por favor, seleccione una orden de la tabla.")
            return
        
        ticket_item = self.table_orders.item(selected_items[0].row(), 0)
        if not ticket_item:
            return
        
        ticket = int(ticket_item.text())
        
        reply = QMessageBox.question(self, "Confirmar Eliminación",
                                    f"¿Está seguro de eliminar la orden #{ticket}?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_message.emit(f"🗑️ Eliminando orden #{ticket}", "INFO")
            
            # ENVIAR SOLICITUD DE ELIMINACIÓN DIRECTAMENTE A MT5
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.log_message.emit(f"✅ Orden #{ticket} eliminada exitosamente", "SUCCESS")
            else:
                error = mt5.last_error() if result is None else result.comment
                self.log_message.emit(f"❌ Error al eliminar orden #{ticket}: {error}", "ERROR")
            
            # Emitir señal
            self.delete_order_requested.emit({'ticket': ticket, 'result': result})
            
            # Actualizar tabla después de un momento
            QTimer.singleShot(1000, self.refresh_orders_table)
    
    def on_delete_all_clicked(self):
        """Manejador para eliminar todas las órdenes."""
        if not self.is_connected:
            return
        
        orders = mt5.orders_get()
        if not orders:
            QMessageBox.information(self, "Órdenes", "No hay órdenes pendientes.")
            return
        
        reply = QMessageBox.question(self, "Confirmar Eliminación",
                                    f"¿Está seguro de eliminar TODAS las {len(orders)} órdenes pendientes?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_message.emit(f"🗑️ Eliminando todas las {len(orders)} órdenes pendientes", "INFO")
            
            # Eliminar cada orden individualmente
            success_count = 0
            for order in orders:
                request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order.ticket,
                }
                
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    success_count += 1
                    self.delete_order_requested.emit({'ticket': order.ticket, 'result': result})
            
            self.log_message.emit(f"✅ {success_count} de {len(orders)} órdenes eliminadas", "SUCCESS")
            
            # Actualizar tabla después de un momento
            QTimer.singleShot(1000, self.refresh_orders_table)
    
    def on_order_selection_changed(self):
        """Manejador para cambio de selección en tabla."""
        has_selection = len(self.table_orders.selectedItems()) > 0
        self.btn_modify_order.setEnabled(has_selection)
        self.btn_delete_order.setEnabled(has_selection)
    
    def on_position_selection_changed(self):
        """Manejador para cambio de selección en tabla de posiciones."""
        has_selection = len(self.table_positions.selectedItems()) > 0
        self.btn_close_position.setEnabled(has_selection)
        self.btn_modify_position.setEnabled(has_selection)
    
    def on_close_position_clicked(self):
        """Manejador para cerrar posición seleccionada (igual que en script de prueba)."""
        selected_items = self.table_positions.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Seleccionar Posición", "Por favor, seleccione una posición de la tabla.")
            return
        
        ticket_item = self.table_positions.item(selected_items[0].row(), 0)
        if not ticket_item:
            return
        
        ticket = int(ticket_item.text())
        
        reply = QMessageBox.question(self, "Confirmar Cierre",
                                    f"¿Está seguro de cerrar la posición #{ticket}?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_message.emit(f"❌ Cerrando posición #{ticket}", "INFO")
            
            # Buscar la posición
            position = mt5.positions_get(ticket=ticket)
            if not position or len(position) == 0:
                self.log_message.emit(f"❌ No se encontró la posición #{ticket}", "ERROR")
                return
            
            position = position[0]
            
            # Obtener precio actual
            tick = mt5.symbol_info_tick(position.symbol)
            if not tick:
                self.log_message.emit(f"❌ No se pudo obtener precio para {position.symbol}", "ERROR")
                return
            
            # Preparar orden de cierre EXACTAMENTE como en el script de prueba
            if position.type == 0:  # BUY position -> close with SELL
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:  # SELL position -> close with BUY
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position.ticket,
                "price": price,
                "deviation": DEFAULT_SLIPPAGE if SETTINGS_LOADED else 10,
                "magic": 1003,
                "comment": f"CLOSE {datetime.datetime.now().strftime('%H:%M')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # ENVIAR ORDEN DE CIERRE DIRECTAMENTE A MT5
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.log_message.emit(f"✅ Posición #{ticket} cerrada exitosamente\nPrecio: {result.price:.5f}", "SUCCESS")
            else:
                error = mt5.last_error() if result is None else result.comment
                self.log_message.emit(f"❌ Error al cerrar posición #{ticket}: {error}", "ERROR")
            
            # Emitir señal
            close_data = {
                'ticket': ticket,
                'symbol': position.symbol,
                'volume': position.volume,
                'position': position.ticket,
                'type': order_type,
                'comment': request['comment'],
                'result': result
            }
            
            self.close_position_requested.emit(close_data)
            
            # Actualizar después de un momento
            QTimer.singleShot(1000, self.refresh_positions_table)
    
    def on_close_all_positions_clicked(self):
        """Manejador para cerrar todas las posiciones."""
        if not self.is_connected:
            return
        
        positions = mt5.positions_get()
        if not positions:
            QMessageBox.information(self, "Posiciones", "No hay posiciones abiertas.")
            return
        
        reply = QMessageBox.question(self, "Confirmar Cierre",
                                    f"¿Está seguro de cerrar TODAS las {len(positions)} posiciones?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_message.emit(f"❌ Cerrando todas las {len(positions)} posiciones", "INFO")
            
            success_count = 0
            for pos in positions:
                # Obtener precio actual
                tick = mt5.symbol_info_tick(pos.symbol)
                if not tick:
                    continue
                
                # Preparar orden de cierre
                if pos.type == 0:  # BUY position -> close with SELL
                    order_type = mt5.ORDER_TYPE_SELL
                    price = tick.bid
                else:  # SELL position -> close with BUY
                    order_type = mt5.ORDER_TYPE_BUY
                    price = tick.ask
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": order_type,
                    "position": pos.ticket,
                    "price": price,
                    "deviation": DEFAULT_SLIPPAGE if SETTINGS_LOADED else 10,
                    "magic": 1003,
                    "comment": f"CLOSE ALL {datetime.datetime.now().strftime('%H:%M')}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                # Enviar orden de cierre
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    success_count += 1
                    self.close_position_requested.emit({
                        'ticket': pos.ticket,
                        'symbol': pos.symbol,
                        'volume': pos.volume,
                        'position': pos.ticket,
                        'type': order_type,
                        'comment': request['comment'],
                        'result': result
                    })
            
            self.log_message.emit(f"✅ {success_count} de {len(positions)} posiciones cerradas", "SUCCESS")
            
            # Actualizar después de un momento
            QTimer.singleShot(2000, self.refresh_positions_table)
    
    def on_modify_position_clicked(self):
        """Manejador para modificar SL/TP de posición seleccionada."""
        selected_items = self.table_positions.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Seleccionar Posición", "Por favor, seleccione una posición de la tabla.")
            return
        
        ticket_item = self.table_positions.item(selected_items[0].row(), 0)
        if not ticket_item:
            return
        
        ticket = int(ticket_item.text())
        
        # Buscar la posición
        position = mt5.positions_get(ticket=ticket)
        if not position:
            QMessageBox.warning(self, "Error", f"No se encontró la posición #{ticket}")
            return
        
        position = position[0]
        
        # Crear diálogo para modificar
        dialog = QDialog(self)
        dialog.setWindowTitle(f"✏️ Modificar Posición #{ticket}")
        dialog.setFixedWidth(350)
        
        layout = QFormLayout(dialog)
        
        # Mostrar información actual
        layout.addRow(QLabel(f"Símbolo: {position.symbol}"))
        layout.addRow(QLabel(f"Tipo: {'COMPRA' if position.type == 0 else 'VENTA'}"))
        layout.addRow(QLabel(f"Volumen: {position.volume}"))
        layout.addRow(QLabel(f"Precio apertura: {position.price_open:.5f}"))
        
        # Obtener información del símbolo para calcular USD
        symbol_info = mt5.symbol_info(position.symbol)
        point = symbol_info.point if symbol_info else 0.00001
        
        # Calcular valores actuales en USD
        current_sl_usd = 0
        current_tp_usd = 0
        
        if position.sl != 0:
            sl_pips = abs(position.price_open - position.sl) / (point * 10)
            value_per_pip = position.volume * (point * 10) * 100
            current_sl_usd = sl_pips * value_per_pip
        
        if position.tp != 0:
            tp_pips = abs(position.tp - position.price_open) / (point * 10)
            value_per_pip = position.volume * (point * 10) * 100
            current_tp_usd = tp_pips * value_per_pip
        
        layout.addRow(QLabel(f"SL actual: {position.sl:.5f} (${current_sl_usd:.2f})"))
        layout.addRow(QLabel(f"TP actual: {position.tp:.5f} (${current_tp_usd:.2f})"))
        
        # Nuevo SL en precio
        sl_spin = QDoubleSpinBox()
        sl_spin.setRange(0, 1000000)
        sl_spin.setValue(position.sl if position.sl != 0 else 0)
        sl_spin.setDecimals(5)
        layout.addRow("Nuevo SL (precio):", sl_spin)
        
        # Nuevo TP en precio
        tp_spin = QDoubleSpinBox()
        tp_spin.setRange(0, 2000000)
        tp_spin.setValue(position.tp if position.tp != 0 else 0)
        tp_spin.setDecimals(5)
        layout.addRow("Nuevo TP (precio):", tp_spin)
        
        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # Usar precios directamente
            new_sl_price = sl_spin.value()
            new_tp_price = tp_spin.value()
            
            # Calcular nuevos valores en USD
            new_sl_usd = 0
            new_tp_usd = 0
            
            if new_sl_price != 0:
                sl_pips = abs(position.price_open - new_sl_price) / (point * 10)
                value_per_pip = position.volume * (point * 10) * 100
                new_sl_usd = sl_pips * value_per_pip
            
            if new_tp_price != 0:
                tp_pips = abs(new_tp_price - position.price_open) / (point * 10)
                value_per_pip = position.volume * (point * 10) * 100
                new_tp_usd = tp_pips * value_per_pip
            
            # Mostrar confirmación con USD
            confirm_msg = f"""
            ¿Confirmar modificación?
            
            SL: {position.sl:.5f} → {new_sl_price:.5f}
            (${current_sl_usd:.2f} → ${new_sl_usd:.2f})
            
            TP: {position.tp:.5f} → {new_tp_price:.5f}
            (${current_tp_usd:.2f} → ${new_tp_usd:.2f})
            """
            
            reply = QMessageBox.question(self, "Confirmar Modificación", confirm_msg,
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply != QMessageBox.Yes:
                return
            
            # Preparar solicitud de modificación
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": position.symbol,
                "sl": new_sl_price,
                "tp": new_tp_price,
            }
            
            self.log_message.emit(f"✏️ Modificando SL/TP de posición #{ticket}", "INFO")
            
            # ENVIAR MODIFICACIÓN DIRECTAMENTE A MT5
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.log_message.emit(f"✅ SL/TP de posición #{ticket} modificados exitosamente", "SUCCESS")
            else:
                error = mt5.last_error() if result is None else result.comment
                self.log_message.emit(f"❌ Error al modificar posición #{ticket}: {error}", "ERROR")
            
            # Emitir señal
            modify_data = {
                'ticket': ticket,
                'sl_price': new_sl_price,
                'tp_price': new_tp_price,
                'sl_usd': new_sl_usd,
                'tp_usd': new_tp_usd,
                'symbol': position.symbol,
                'action': mt5.TRADE_ACTION_SLTP,
                'result': result
            }
            
            self.modify_position_requested.emit(modify_data)
            
            # Actualizar tabla
            QTimer.singleShot(1000, self.refresh_positions_table)
    
    def calculate_pips_from_input(self, value, value_type, entry_price, is_sell=False):
        """Calcular pips desde entrada (precio o USD)."""
        if value == 0:
            return 0
        
        if value_type == "precio":
            # Convertir diferencia de precio a pips
            if self.current_symbol in self.symbol_info:
                symbol_info = self.symbol_info[self.current_symbol]
            else:
                symbol_info = self.symbol_info.get('US500', {'point': 0.01})
            
            point = symbol_info['point']
            pip_value = point * 10
            
            # Calcular diferencia en pips
            price_difference = abs(value - entry_price)
            pips = price_difference / pip_value
            return pips
        else:
            # Convertir USD a pips
            usd_value = abs(value)
            if self.current_symbol in self.symbol_info:
                symbol_info = self.symbol_info[self.current_symbol]
            else:
                symbol_info = self.symbol_info.get('US500', {'pip_value': 0.1})
            
            pip_value = symbol_info['pip_value']
            
            # Valor por pip por lote
            value_per_pip = self.spin_volume.value() * pip_value * 100
            
            if value_per_pip > 0:
                pips = usd_value / value_per_pip
                return pips
            else:
                return 0
    
    def calculate_usd_from_pips(self, pips, is_sell=False):
        """Calcular USD desde pips."""
        if pips == 0:
            return 0
        
        if self.current_symbol in self.symbol_info:
            symbol_info = self.symbol_info[self.current_symbol]
        else:
            symbol_info = self.symbol_info.get('US500', {'pip_value': 0.1})
        
        pip_value = symbol_info['pip_value']
        
        # Valor por pip por lote
        value_per_pip = self.spin_volume.value() * pip_value * 100
        
        return pips * value_per_pip
    
    def refresh_orders_table(self):
        """Actualizar tabla de órdenes pendientes."""
        if not self.is_connected:
            return
        
        # Limpiar tabla
        self.table_orders.setRowCount(0)
        
        # Obtener órdenes pendientes
        orders = mt5.orders_get()
        
        if orders is None:
            orders = []
        
        for i, order in enumerate(orders):
            self.table_orders.insertRow(i)
            
            # Ticket
            self.table_orders.setItem(i, 0, QTableWidgetItem(str(order.ticket)))
            
            # Símbolo
            self.table_orders.setItem(i, 1, QTableWidgetItem(order.symbol))
            
            # Tipo con COLORES
            order_type_name = self.get_order_type_name(order.type)
            type_item = QTableWidgetItem(order_type_name)
            
            # Color por tipo
            if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP]:
                type_item.setForeground(QBrush(QColor("#4CAF50")))  # Verde para compra
            else:
                type_item.setForeground(QBrush(QColor("#F44336")))  # Rojo para venta
            
            self.table_orders.setItem(i, 2, type_item)
            
            # Volumen
            self.table_orders.setItem(i, 3, QTableWidgetItem(str(order.volume_initial)))
            
            # Precio con color según tipo
            price_item = QTableWidgetItem(f"{order.price_open:.5f}")
            if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP]:
                price_item.setForeground(QBrush(QColor("#4CAF50")))
            else:
                price_item.setForeground(QBrush(QColor("#F44336")))
            self.table_orders.setItem(i, 4, price_item)
            
            # Columna "Activa en" - mostrar lógica de activación
            activation_info = self.get_activation_info(order, order_type_name)
            activation_item = QTableWidgetItem(activation_info)
            activation_item.setForeground(QBrush(QColor("#FF9800")))  # Naranja para información de activación
            self.table_orders.setItem(i, 5, activation_item)
            
            # SL (AHORA EN PRECIO) con cálculo USD
            sl_text = f"{order.sl:.5f}" if order.sl != 0 else "Sin SL"
            
            # Calcular USD para SL si existe
            if order.sl != 0:
                symbol_info = mt5.symbol_info(order.symbol)
                if symbol_info:
                    point = symbol_info.point
                    sl_pips = abs(order.price_open - order.sl) / (point * 10)
                    value_per_pip = order.volume_initial * (point * 10) * 100
                    sl_usd = sl_pips * value_per_pip
                    sl_text = f"{order.sl:.5f} (${sl_usd:.2f})"
            
            sl_item = QTableWidgetItem(sl_text)
            if order.sl != 0:
                sl_item.setForeground(QBrush(QColor("#FF9800")))  # Naranja para SL
            self.table_orders.setItem(i, 6, sl_item)
            
            # TP (AHORA EN PRECIO) con cálculo USD
            tp_text = f"{order.tp:.5f}" if order.tp != 0 else "Sin TP"
            
            # Calcular USD para TP si existe
            if order.tp != 0:
                symbol_info = mt5.symbol_info(order.symbol)
                if symbol_info:
                    point = symbol_info.point
                    tp_pips = abs(order.tp - order.price_open) / (point * 10)
                    value_per_pip = order.volume_initial * (point * 10) * 100
                    tp_usd = tp_pips * value_per_pip
                    tp_text = f"{order.tp:.5f} (${tp_usd:.2f})"
            
            tp_item = QTableWidgetItem(tp_text)
            if order.tp != 0:
                tp_item.setForeground(QBrush(QColor("#2196F3")))  # Azul para TP
            self.table_orders.setItem(i, 7, tp_item)
            
            # Comentario
            comment = order.comment if order.comment else ""
            self.table_orders.setItem(i, 8, QTableWidgetItem(comment))
            
            # Acciones - BOTONES CORREGIDOS
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(5)
            
            # Botón de modificar (lápiz) - CORREGIDO
            btn_modify = QPushButton("✏️")
            btn_modify.setFixedSize(30, 25)
            btn_modify.setToolTip("Modificar SL/TP")
            btn_modify.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #666;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #666;
                    border: 1px solid #777;
                }
                QPushButton:pressed {
                    background-color: #444;
                    border: 1px solid #555;
                }
            """)
            btn_modify.clicked.connect(lambda checked, t=order.ticket: self.on_modify_specific_clicked(t))
            
            # Botón de eliminar (X) - CORREGIDO
            btn_delete = QPushButton("❌")
            btn_delete.setFixedSize(30, 25)
            btn_delete.setToolTip("Eliminar orden")
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #666;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F44336;
                    border: 1px solid #d32f2f;
                }
                QPushButton:pressed {
                    background-color: #d32f2f;
                    border: 1px solid #b71c1c;
                }
            """)
            btn_delete.clicked.connect(lambda checked, t=order.ticket: self.on_delete_specific_clicked(t))
            
            actions_layout.addWidget(btn_modify)
            actions_layout.addWidget(btn_delete)
            actions_layout.addStretch()
            
            self.table_orders.setCellWidget(i, 9, actions_widget)
        
        # Actualizar contador en pestaña INTERNA
        inner_tab = self.positions_orders_tab.findChild(QTabWidget)
        if inner_tab:
            inner_tab.setTabText(1, f"Órdenes Pendientes ({len(orders)})")
    
    def get_activation_info(self, order, order_type_name):
        """Obtener información de activación para la orden."""
        # Obtener precio actual del símbolo
        symbol_info = mt5.symbol_info(order.symbol)
        if not symbol_info:
            return "Precio no disponible"
        
        current_price = symbol_info.bid  # Usar bid como referencia
        
        if order.type == mt5.ORDER_TYPE_BUY_LIMIT:
            # Se activa cuando el precio BAJA al nivel especificado
            if current_price > order.price_open:
                distance = current_price - order.price_open
                return f"↓ {distance:.5f} para activar"
            else:
                return "✅ ACTIVADA"
                
        elif order.type == mt5.ORDER_TYPE_BUY_STOP:
            # Se activa cuando el precio SUBE al nivel especificado
            if current_price < order.price_open:
                distance = order.price_open - current_price
                return f"↑ {distance:.5f} para activar"
            else:
                return "✅ ACTIVADA"
                
        elif order.type == mt5.ORDER_TYPE_SELL_LIMIT:
            # Se activa cuando el precio SUBE al nivel especificado
            if current_price < order.price_open:
                distance = order.price_open - current_price
                return f"↑ {distance:.5f} para activar"
            else:
                return "✅ ACTIVADA"
                
        elif order.type == mt5.ORDER_TYPE_SELL_STOP:
            # Se activa cuando el precio BAJA al nivel especificado
            if current_price > order.price_open:
                distance = current_price - order.price_open
                return f"↓ {distance:.5f} para activar"
            else:
                return "✅ ACTIVADA"
        
        return f"Precio: {order.price_open:.5f}"
    
    def refresh_positions_table(self):
        """Actualizar tabla de posiciones abiertas CON COLORES MEJORADOS Y BOTONES CORREGIDOS."""
        if not self.is_connected:
            return
        
        # Limpiar tabla
        self.table_positions.setRowCount(0)
        
        # Obtener posiciones abiertas
        positions = mt5.positions_get()
        
        if positions is None:
            positions = []
        
        total_profit = 0
        
        for i, pos in enumerate(positions):
            self.table_positions.insertRow(i)
            
            # Ticket
            self.table_positions.setItem(i, 0, QTableWidgetItem(str(pos.ticket)))
            
            # Símbolo
            self.table_positions.setItem(i, 1, QTableWidgetItem(pos.symbol))
            
            # Tipo con COLOR FUERTE
            type_text = "COMPRA" if pos.type == 0 else "VENTA"
            type_item = QTableWidgetItem(type_text)
            if pos.type == 0:
                type_item.setForeground(QBrush(QColor("#00FF00")))  # VERDE FUERTE
                type_item.setFont(QFont("Arial", 10, QFont.Bold))
            else:
                type_item.setForeground(QBrush(QColor("#FF0000")))  # ROJO FUERTE
                type_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.table_positions.setItem(i, 2, type_item)
            
            # Volumen
            self.table_positions.setItem(i, 3, QTableWidgetItem(str(pos.volume)))
            
            # Precio apertura con color según tipo
            symbol_info = self.symbol_info.get(pos.symbol, {'digits': 5})
            digits = symbol_info.get('digits', 5)
            price_open_item = QTableWidgetItem(f"{pos.price_open:.{digits}f}")
            if pos.type == 0:
                price_open_item.setForeground(QBrush(QColor("#90EE90")))  # Verde claro
            else:
                price_open_item.setForeground(QBrush(QColor("#FFB6C1")))  # Rojo claro
            self.table_positions.setItem(i, 4, price_open_item)
            
            # Precio ACTUAL con color dinámico (VERDE si es mayor, ROJO si es menor)
            current_price = pos.price_current
            price_current_item = QTableWidgetItem(f"{current_price:.{digits}f}")
            
            if pos.type == 0:  # COMPRA
                if current_price > pos.price_open:
                    price_current_item.setForeground(QBrush(QColor("#00FF00")))  # VERDE (ganando)
                elif current_price < pos.price_open:
                    price_current_item.setForeground(QBrush(QColor("#FF0000")))  # ROJO (perdiendo)
                else:
                    price_current_item.setForeground(QBrush(QColor("#FFFFFF")))  # BLANCO (igual)
            else:  # VENTA
                if current_price < pos.price_open:
                    price_current_item.setForeground(QBrush(QColor("#00FF00")))  # VERDE (ganando)
                elif current_price > pos.price_open:
                    price_current_item.setForeground(QBrush(QColor("#FF0000")))  # ROJO (perdiendo)
                else:
                    price_current_item.setForeground(QBrush(QColor("#FFFFFF")))  # BLANCO (igual)
            
            self.table_positions.setItem(i, 5, price_current_item)
            
            # SL (AHORA EN PRECIO) con cálculo USD
            sl_text = f"{pos.sl:.{digits}f}" if pos.sl != 0 else "Sin SL"
            
            # Calcular USD para SL si existe
            if pos.sl != 0:
                symbol_info = mt5.symbol_info(pos.symbol)
                if symbol_info:
                    point = symbol_info.point
                    sl_pips = abs(pos.price_open - pos.sl) / (point * 10)
                    value_per_pip = pos.volume * (point * 10) * 100
                    sl_usd = sl_pips * value_per_pip
                    sl_text = f"{pos.sl:.{digits}f} (${sl_usd:.2f})"
            
            sl_item = QTableWidgetItem(sl_text)
            if pos.sl != 0:
                sl_item.setForeground(QBrush(QColor("#FFA500")))  # Naranja
            self.table_positions.setItem(i, 6, sl_item)
            
            # TP (AHORA EN PRECIO) con cálculo USD
            tp_text = f"{pos.tp:.{digits}f}" if pos.tp != 0 else "Sin TP"
            
            # Calcular USD para TP si existe
            if pos.tp != 0:
                symbol_info = mt5.symbol_info(pos.symbol)
                if symbol_info:
                    point = symbol_info.point
                    tp_pips = abs(pos.tp - pos.price_open) / (point * 10)
                    value_per_pip = pos.volume * (point * 10) * 100
                    tp_usd = tp_pips * value_per_pip
                    tp_text = f"{pos.tp:.{digits}f} (${tp_usd:.2f})"
            
            tp_item = QTableWidgetItem(tp_text)
            if pos.tp != 0:
                tp_item.setForeground(QBrush(QColor("#4169E1")))  # Azul real
            self.table_positions.setItem(i, 7, tp_item)
            
            # Beneficio con COLOR MUY VISIBLE
            profit_item = QTableWidgetItem(f"${pos.profit:.2f}")
            if pos.profit > 0:
                profit_item.setForeground(QBrush(QColor("#00FF00")))  # VERDE FUERTE
                profit_item.setFont(QFont("Arial", 10, QFont.Bold))
            elif pos.profit < 0:
                profit_item.setForeground(QBrush(QColor("#FF0000")))  # ROJO FUERTE
                profit_item.setFont(QFont("Arial", 10, QFont.Bold))
            else:
                profit_item.setForeground(QBrush(QColor("#FFFFFF")))  # BLANCO
            
            self.table_positions.setItem(i, 8, profit_item)
            
            total_profit += pos.profit
            
            # Swap
            swap_item = QTableWidgetItem(f"${pos.swap:.2f}")
            if pos.swap > 0:
                swap_item.setForeground(QBrush(QColor("#00FF00")))  # Verde
            elif pos.swap < 0:
                swap_item.setForeground(QBrush(QColor("#FF0000")))  # Rojo
            self.table_positions.setItem(i, 9, swap_item)
            
            # Acciones - BOTONES CORREGIDOS CON "X"
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(5)
            
            # Botón de cerrar (X) - CAMBIADO A "X"
            btn_close = QPushButton("❌")
            btn_close.setFixedSize(30, 25)
            btn_close.setToolTip("Cerrar posición")
            btn_close.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #666;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F44336;
                    border: 1px solid #d32f2f;
                }
                QPushButton:pressed {
                    background-color: #d32f2f;
                    border: 1px solid #b71c1c;
                }
            """)
            btn_close.clicked.connect(lambda checked, t=pos.ticket: self.on_close_specific_clicked(t))
            
            # Botón de modificar (lápiz) - CORREGIDO
            btn_modify = QPushButton("✏️")
            btn_modify.setFixedSize(30, 25)
            btn_modify.setToolTip("Modificar SL/TP")
            btn_modify.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #666;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #666;
                    border: 1px solid #777;
                }
                QPushButton:pressed {
                    background-color: #444;
                    border: 1px solid #555;
                }
            """)
            btn_modify.clicked.connect(lambda checked, t=pos.ticket: self.on_modify_specific_position_clicked(t))
            
            actions_layout.addWidget(btn_close)
            actions_layout.addWidget(btn_modify)
            actions_layout.addStretch()
            
            self.table_positions.setCellWidget(i, 10, actions_widget)
        
        # Actualizar contador en pestaña INTERNA (no la principal)
        inner_tab = self.positions_orders_tab.findChild(QTabWidget)
        if inner_tab:
            inner_tab.setTabText(0, f"Posiciones Abiertas ({len(positions)})")
        
        # Actualizar pestaña PRINCIPAL con beneficio total en COLOR
        profit_color = "#00FF00" if total_profit >= 0 else "#FF0000"
        self.tab_widget.setTabText(1, f"📊 Posiciones ({len(positions)}) ")
    
    def on_modify_specific_clicked(self, ticket):
        """Manejador para modificar orden específica."""
        # Deseleccionar todo primero
        self.table_orders.clearSelection()
        
        # Buscar la fila con el ticket
        for row in range(self.table_orders.rowCount()):
            item = self.table_orders.item(row, 0)
            if item and int(item.text()) == ticket:
                self.table_orders.selectRow(row)
                self.on_modify_order_clicked()
                break
    
    def on_delete_specific_clicked(self, ticket):
        """Manejador para eliminar orden específica."""
        # Deseleccionar todo primero
        self.table_orders.clearSelection()
        
        # Buscar la fila con el ticket
        for row in range(self.table_orders.rowCount()):
            item = self.table_orders.item(row, 0)
            if item and int(item.text()) == ticket:
                self.table_orders.selectRow(row)
                self.on_delete_order_clicked()
                break
    
    def on_close_specific_clicked(self, ticket):
        """Manejador para cerrar posición específica."""
        # Deseleccionar todo primero
        self.table_positions.clearSelection()
        
        # Buscar la fila con el ticket
        for row in range(self.table_positions.rowCount()):
            item = self.table_positions.item(row, 0)
            if item and int(item.text()) == ticket:
                self.table_positions.selectRow(row)
                self.on_close_position_clicked()
                break
    
    def on_modify_specific_position_clicked(self, ticket):
        """Manejador para modificar posición específica."""
        # Deseleccionar todo primero
        self.table_positions.clearSelection()
        
        # Buscar la fila con el ticket
        for row in range(self.table_positions.rowCount()):
            item = self.table_positions.item(row, 0)
            if item and int(item.text()) == ticket:
                self.table_positions.selectRow(row)
                self.on_modify_position_clicked()
                break
    
    def get_order_by_ticket(self, ticket):
        """Obtener orden por ticket."""
        if not self.is_connected:
            return None
        
        orders = mt5.orders_get(ticket=ticket)
        if orders and len(orders) > 0:
            return orders[0]
        return None
    
    def get_order_type_name(self, order_type):
        """Obtener nombre legible del tipo de orden."""
        type_names = {
            mt5.ORDER_TYPE_BUY: "Buy",
            mt5.ORDER_TYPE_SELL: "Sell",
            mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit",
            mt5.ORDER_TYPE_BUY_STOP: "Buy Stop",
            mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit",
            mt5.ORDER_TYPE_SELL_STOP: "Sell Stop"
        }
        return type_names.get(order_type, f"Tipo {order_type}")
    
    def get_appropriate_volume(self, requested_volume):
        """Obtener volumen apropiado según las especificaciones del símbolo (según script de prueba)."""
        if self.current_symbol in self.symbol_info:
            info = self.symbol_info[self.current_symbol]
            volume_min = info.get('volume_min', 0.01)
            volume_max = info.get('volume_max', 100.0)
            volume_step = info.get('volume_step', 0.01)
            
            # Asegurar que el volumen esté dentro de los límites
            volume = max(requested_volume, volume_min)
            volume = min(volume, volume_max)
            
            # Redondear al paso apropiado
            if volume_step > 0:
                volume = round(volume / volume_step) * volume_step
            
            return volume
        
        return requested_volume
    
    def update_prices_and_orders(self):
        """Actualizar precios y órdenes periódicamente."""
        if self.is_connected:
            try:
                # Actualizar precios
                symbol_info = mt5.symbol_info(self.current_symbol)
                if symbol_info:
                    self.current_bid = symbol_info.bid
                    self.current_ask = symbol_info.ask
                    self.update_price_display({'bid': self.current_bid, 'ask': self.current_ask})
                
                # Actualizar cálculos
                self.update_calculations()
                self.update_order_pending_calculations()
                
                # Actualizar tabla de posiciones si estamos en esa pestaña
                if self.tab_widget.currentIndex() == 1:  # Pestaña de posiciones/órdenes
                    self.refresh_positions_table()
                    
            except Exception as e:
                # Silenciar errores de actualización para no interrumpir la UI
                pass
    
    def update_connection_status(self, connected, message=""):
        """Actualizar estado de conexión."""
        self.is_connected = connected
        
        if connected:
            self.lbl_connection.setText("✅ Conectado")
            self.lbl_connection.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 11px;")
            self.btn_connect.setText("🔌 Desconectar")
            
            # Habilitar componentes
            self.btn_buy.setEnabled(True)
            self.btn_sell.setEnabled(True)
            self.btn_pending_order.setEnabled(True)
            self.btn_refresh_orders.setEnabled(True)
            self.btn_delete_all.setEnabled(True)
            self.btn_refresh_positions.setEnabled(True)
            self.btn_close_all_positions.setEnabled(True)
            self.btn_symbol_info.setEnabled(True)
            self.btn_show_current.setEnabled(True)
            self.btn_apply_candles.setEnabled(True)  # NUEVO: Habilitar botón de aplicar velas
            
            # Actualizar información del símbolo actual
            self.update_symbol_info_from_mt5(self.current_symbol)
            
            # Iniciar timer de actualización
            self.update_timer.start(self.update_interval)
            
            # Actualizar precios inicialmente
            self.update_prices_and_orders()
            
            # Actualizar tablas
            QTimer.singleShot(500, self.refresh_orders_table)
            QTimer.singleShot(500, self.refresh_positions_table)
            
            # NUEVO: Emitir señal de cantidad de velas al conectar
            QTimer.singleShot(1000, self.on_apply_candles_clicked)
            
        else:
            self.lbl_connection.setText("❌ Desconectado")
            self.lbl_connection.setStyleSheet("color: #ff6666; font-weight: bold; font-size: 11px;")
            self.btn_connect.setText("🔌 Conectar")
            
            # Deshabilitar componentes
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(False)
            self.btn_pending_order.setEnabled(False)
            self.btn_modify_order.setEnabled(False)
            self.btn_delete_order.setEnabled(False)
            self.btn_refresh_orders.setEnabled(False)
            self.btn_delete_all.setEnabled(False)
            self.btn_close_position.setEnabled(False)
            self.btn_modify_position.setEnabled(False)
            self.btn_refresh_positions.setEnabled(False)
            self.btn_close_all_positions.setEnabled(False)
            self.btn_symbol_info.setEnabled(False)
            self.btn_show_current.setEnabled(False)
            self.btn_apply_candles.setEnabled(False)  # NUEVO: Deshabilitar botón de aplicar velas
            
            # Detener timer
            self.update_timer.stop()
            
            # Limpiar tablas
            self.table_orders.setRowCount(0)
            self.table_positions.setRowCount(0)
            
            # Actualizar textos de pestañas
            self.tab_widget.setTabText(1, "📊 Posiciones")
    
    def update_price_display(self, price_data):
        """Actualizar display de precios."""
        if price_data:
            bid = price_data.get('bid', 0)
            ask = price_data.get('ask', 0)
            
            if bid > 0 and ask > 0:
                self.current_bid = bid
                self.current_ask = ask
                
                if self.current_symbol in self.symbol_info:
                    digits = self.symbol_info[self.current_symbol]['digits']
                    self.lbl_price.setText(f"Bid: {bid:.{digits}f} | Ask: {ask:.{digits}f}")
                else:
                    self.lbl_price.setText(f"Bid: {bid:.5f} | Ask: {ask:.5f}")
    
    def update_symbol_info(self, symbol, info):
        """Actualizar información de un símbolo."""
        self.symbol_info[symbol] = info
    
    def get_current_symbol(self):
        """Obtener símbolo actual."""
        return self.current_symbol
    
    def get_current_timeframe(self):
        """Obtener timeframe actual."""
        return self.current_timeframe
    
    def get_current_candles_to_load(self):
        """NUEVO: Obtener cantidad de velas a cargar."""
        return self.spin_candles.value()
    
    def show_symbol_info(self):
        """Mostrar información detallada del símbolo (según script de prueba)."""
        if not self.is_connected:
            QMessageBox.information(self, "Información", "Conéctese primero a MT5.")
            return
        
        symbol = self.current_symbol
        symbol_info = mt5.symbol_info(symbol)
        
        if not symbol_info:
            QMessageBox.warning(self, "Error", f"No se pudo obtener información de {symbol}")
            return
        
        # Crear diálogo de información
        dialog = QDialog(self)
        dialog.setWindowTitle(f"ℹ️ Información de {symbol}")
        dialog.setFixedWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        info_text = f"""
        <h3>{symbol} - Información Técnica</h3>
        <hr>
        <b>Precios:</b><br>
        • Bid: {symbol_info.bid:.{symbol_info.digits}f}<br>
        • Ask: {symbol_info.ask:.{symbol_info.digits}f}<br>
        • Spread: {symbol_info.ask - symbol_info.bid:.{symbol_info.digits}f}<br>
        <br>
        <b>Volumen:</b><br>
        • Mínimo: {symbol_info.volume_min}<br>
        • Máximo: {symbol_info.volume_max}<br>
        • Paso: {symbol_info.volume_step}<br>
        <br>
        <b>Características:</b><br>
        • Punto: {symbol_info.point}<br>
        • Dígitos: {symbol_info.digits}<br>
        • 1 pip = {symbol_info.point * 10} (10 puntos)<br>
        <br>
        <b>Estado:</b><br>
        • Trading: {'✅ Permitido' if symbol_info.trade_mode == 0 else '❌ No permitido'}<br>
        • Visible: {'✅ Sí' if symbol_info.visible else '❌ No'}<br>
        • Spread flotante: {'✅ Sí' if symbol_info.spread_float else '❌ No'}<br>
        <br>
        <b>Configuración gráfico:</b><br>
        • Timeframe: {self.current_timeframe}<br>
        • Velas a cargar: {self.spin_candles.value()}<br>
        """
        
        label = QLabel(info_text)
        label.setWordWrap(True)
        label.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(label)
        
        # Botón de cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        
        dialog.exec_()
    
    def check_autotrading_status(self):
        """Verificar estado de AutoTrading (según script de prueba)."""
        if not self.is_connected:
            return False
        
        terminal_info = mt5.terminal_info()
        if not terminal_info:
            return False
        
        if not terminal_info.trade_allowed:
            self.log_message.emit("⚠️ AutoTrading deshabilitado en MT5", "WARNING")
            return False
        
        return True