# src/infrastructure/ui/control_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QGridLayout, QTextEdit, QCheckBox, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
                             QMessageBox, QFrame, QScrollArea, QSlider, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
import json

# Importar indicadores de dominio
from src.domain.indicators import (
    SMAIndicator, EMAIndicator, RSIIndicator,
    MACDIndicator, BollingerIndicator, StochasticIndicator
)


class ControlPanel(QWidget):
    """Panel de control para la plataforma de trading."""
    
    # Señales EXISTENTES (se mantienen igual)
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)
    sell_requested = pyqtSignal(dict)
    refresh_positions = pyqtSignal()
    
    # NUEVA SEÑAL para indicadores
    indicators_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado EXISTENTE (se mantiene igual)
        self.is_connected = False
        self.current_symbol = "US500"
        self.account_info = {}
        self.positions = []
        
        # Configuración por defecto EXISTENTE (se mantiene igual)
        self.default_volume = 0.1
        self.default_sl = 50
        self.default_tp = 100
        
        # Instancias de indicadores de dominio
        self.indicators = {
            'sma': SMAIndicator(period=20),
            'ema': EMAIndicator(period=12),
            'rsi': RSIIndicator(period=14, overbought=70, oversold=30),
            'macd': MACDIndicator(fast_period=12, slow_period=26, signal_period=9),
            'bollinger': BollingerIndicator(period=20, std_multiplier=2.0),
            'stochastic': StochasticIndicator(k_period=14, d_period=3, slowing=3)
        }
        
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
        
        # Pestañas EXISTENTES (se mantienen igual)
        self.tab_trading = self.create_trading_tab()
        self.tab_positions = self.create_positions_tab()
        self.tab_account = self.create_account_tab()
        self.tab_settings = self.create_settings_tab()
        
        # NUEVA PESTAÑA
        self.tab_indicators = self.create_indicators_tab()
        
        # Agregar pestañas
        self.tab_widget.addTab(self.tab_trading, "📊 Trading")
        self.tab_widget.addTab(self.tab_positions, "💰 Posiciones")
        self.tab_widget.addTab(self.tab_account, "👤 Cuenta")
        self.tab_widget.addTab(self.tab_indicators, "📈 Indicadores")
        self.tab_widget.addTab(self.tab_settings, "⚙️ Config")
        
        layout.addWidget(self.tab_widget)
    
    # ===== PESTAÑA DE INDICADORES MEJORADA =====
    
    def create_indicators_tab(self):
        """Crear pestaña de indicadores técnicos integrada con dominio."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Título
        title_label = QLabel("📈 CONFIGURACIÓN DE INDICADORES TÉCNICOS")
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin: 5px; 
            color: #ffffff;
            padding: 5px;
        """)
        layout.addWidget(title_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #666; margin: 5px 0px;")
        layout.addWidget(separator)
        
        # Área de scroll
        scroll_area = QScrollArea()
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Estilos
        group_style = """
            QGroupBox {
                font-weight: bold; 
                color: #ffffff;
                border: 1px solid #666;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
        """
        
        label_style = "color: #ffffff;"
        checkbox_style = "color: #ffffff;"
        spinbox_style = "color: #ffffff; background-color: #333;"
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #666;
                height: 6px;
                background: #333;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #4CAF50;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
            }
        """
        
        # 1. Grupo de Medias Móviles
        ma_group = QGroupBox("📊 Medias Móviles")
        ma_group.setStyleSheet(group_style)
        ma_layout = QVBoxLayout(ma_group)
        
        # SMA con selector de color
        sma_layout = QHBoxLayout()
        self.sma_checkbox = QCheckBox("Media Móvil Simple (SMA)")
        self.sma_checkbox.setChecked(self.indicators['sma'].config.enabled)
        self.sma_checkbox.stateChanged.connect(self.on_sma_changed)
        self.sma_checkbox.setStyleSheet(checkbox_style)
        
        sma_layout.addWidget(self.sma_checkbox)
        
        sma_layout.addWidget(QLabel("Período:", styleSheet=label_style))
        self.sma_period_spin = QSpinBox()
        self.sma_period_spin.setRange(5, 200)
        self.sma_period_spin.setValue(self.indicators['sma'].config.params['period'])
        self.sma_period_spin.valueChanged.connect(self.on_sma_changed)
        self.sma_period_spin.setStyleSheet(spinbox_style)
        sma_layout.addWidget(self.sma_period_spin)
        
        # Botón para cambiar color SMA
        self.sma_color_btn = QPushButton("🎨")
        self.sma_color_btn.setToolTip("Cambiar color SMA")
        self.sma_color_btn.setFixedSize(30, 30)
        self.sma_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['sma'].config.color};
                border: 1px solid #666;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #fff;
            }}
        """)
        self.sma_color_btn.clicked.connect(lambda: self.change_indicator_color('sma'))
        sma_layout.addWidget(self.sma_color_btn)
        
        sma_layout.addStretch()
        ma_layout.addLayout(sma_layout)
        
        # EMA con selector de color
        ema_layout = QHBoxLayout()
        self.ema_checkbox = QCheckBox("Media Móvil Exponencial (EMA)")
        self.ema_checkbox.setChecked(self.indicators['ema'].config.enabled)
        self.ema_checkbox.stateChanged.connect(self.on_ema_changed)
        self.ema_checkbox.setStyleSheet(checkbox_style)
        
        ema_layout.addWidget(self.ema_checkbox)
        
        ema_layout.addWidget(QLabel("Período:", styleSheet=label_style))
        self.ema_period_spin = QSpinBox()
        self.ema_period_spin.setRange(5, 200)
        self.ema_period_spin.setValue(self.indicators['ema'].config.params['period'])
        self.ema_period_spin.valueChanged.connect(self.on_ema_changed)
        self.ema_period_spin.setStyleSheet(spinbox_style)
        ema_layout.addWidget(self.ema_period_spin)
        
        # Botón para cambiar color EMA
        self.ema_color_btn = QPushButton("🎨")
        self.ema_color_btn.setToolTip("Cambiar color EMA")
        self.ema_color_btn.setFixedSize(30, 30)
        self.ema_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['ema'].config.color};
                border: 1px solid #666;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #fff;
            }}
        """)
        self.ema_color_btn.clicked.connect(lambda: self.change_indicator_color('ema'))
        ema_layout.addWidget(self.ema_color_btn)
        
        ema_layout.addStretch()
        ma_layout.addLayout(ema_layout)
        
        scroll_layout.addWidget(ma_group)
        
        # 2. Grupo de RSI
        rsi_group = QGroupBox("📉 Índice de Fuerza Relativa (RSI)")
        rsi_group.setStyleSheet(group_style)
        rsi_layout = QVBoxLayout(rsi_group)
        
        # Checkbox de habilitación
        rsi_check_layout = QHBoxLayout()
        self.rsi_checkbox = QCheckBox("Habilitar RSI")
        self.rsi_checkbox.setChecked(self.indicators['rsi'].config.enabled)
        self.rsi_checkbox.stateChanged.connect(self.on_rsi_changed)
        self.rsi_checkbox.setStyleSheet(checkbox_style)
        rsi_check_layout.addWidget(self.rsi_checkbox)
        
        # Botón para cambiar color RSI
        self.rsi_color_btn = QPushButton("🎨")
        self.rsi_color_btn.setToolTip("Cambiar color RSI")
        self.rsi_color_btn.setFixedSize(30, 30)
        self.rsi_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['rsi'].config.color};
                border: 1px solid #666;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #fff;
            }}
        """)
        self.rsi_color_btn.clicked.connect(lambda: self.change_indicator_color('rsi'))
        rsi_check_layout.addWidget(self.rsi_color_btn)
        
        rsi_check_layout.addStretch()
        rsi_layout.addLayout(rsi_check_layout)
        
        # Período RSI
        rsi_period_layout = QHBoxLayout()
        rsi_period_layout.addWidget(QLabel("Período:", styleSheet=label_style))
        
        self.rsi_period_slider = QSlider(Qt.Horizontal)
        self.rsi_period_slider.setRange(5, 50)
        self.rsi_period_slider.setValue(self.indicators['rsi'].config.params['period'])
        self.rsi_period_slider.setTickPosition(QSlider.TicksBelow)
        self.rsi_period_slider.setTickInterval(5)
        self.rsi_period_slider.valueChanged.connect(self.on_rsi_period_changed)
        self.rsi_period_slider.setStyleSheet(slider_style)
        rsi_period_layout.addWidget(self.rsi_period_slider)
        
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(5, 50)
        self.rsi_period_spin.setValue(self.indicators['rsi'].config.params['period'])
        self.rsi_period_spin.valueChanged.connect(self.on_rsi_period_changed)
        self.rsi_period_spin.setStyleSheet(spinbox_style)
        rsi_period_layout.addWidget(self.rsi_period_spin)
        rsi_layout.addLayout(rsi_period_layout)
        
        # Niveles RSI
        rsi_levels_layout = QVBoxLayout()
        
        # Nivel de sobrecompra
        overbought_layout = QHBoxLayout()
        overbought_layout.addWidget(QLabel("Sobrecompra:", styleSheet=label_style))
        
        self.rsi_overbought_spin = QSpinBox()
        self.rsi_overbought_spin.setRange(60, 90)
        self.rsi_overbought_spin.setValue(self.indicators['rsi'].config.params['overbought'])
        self.rsi_overbought_spin.valueChanged.connect(self.on_rsi_levels_changed)
        self.rsi_overbought_spin.setStyleSheet(spinbox_style)
        overbought_layout.addWidget(self.rsi_overbought_spin)
        overbought_layout.addStretch()
        rsi_levels_layout.addLayout(overbought_layout)
        
        # Nivel de sobreventa
        oversold_layout = QHBoxLayout()
        oversold_layout.addWidget(QLabel("Sobreventa:", styleSheet=label_style))
        
        self.rsi_oversold_spin = QSpinBox()
        self.rsi_oversold_spin.setRange(10, 40)
        self.rsi_oversold_spin.setValue(self.indicators['rsi'].config.params['oversold'])
        self.rsi_oversold_spin.valueChanged.connect(self.on_rsi_levels_changed)
        self.rsi_oversold_spin.setStyleSheet(spinbox_style)
        oversold_layout.addWidget(self.rsi_oversold_spin)
        oversold_layout.addStretch()
        rsi_levels_layout.addLayout(oversold_layout)
        
        rsi_layout.addLayout(rsi_levels_layout)
        scroll_layout.addWidget(rsi_group)
        
        # 3. Grupo de MACD
        macd_group = QGroupBox("📈 Oscilador MACD con Histograma")
        macd_group.setStyleSheet(group_style)
        macd_layout = QVBoxLayout(macd_group)
        
        # Checkbox de habilitación
        macd_check_layout = QHBoxLayout()
        self.macd_checkbox = QCheckBox("Habilitar MACD")
        self.macd_checkbox.setChecked(self.indicators['macd'].config.enabled)
        self.macd_checkbox.stateChanged.connect(self.on_macd_changed)
        self.macd_checkbox.setStyleSheet(checkbox_style)
        macd_check_layout.addWidget(self.macd_checkbox)
        macd_check_layout.addStretch()
        macd_layout.addLayout(macd_check_layout)
        
        # EMA Rápida
        macd_fast_layout = QHBoxLayout()
        macd_fast_layout.addWidget(QLabel("EMA Rápida:", styleSheet=label_style))
        
        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setRange(5, 50)
        self.macd_fast_spin.setValue(self.indicators['macd'].config.params['fast_period'])
        self.macd_fast_spin.valueChanged.connect(self.on_macd_params_changed)
        self.macd_fast_spin.setStyleSheet(spinbox_style)
        macd_fast_layout.addWidget(self.macd_fast_spin)
        macd_fast_layout.addStretch()
        macd_layout.addLayout(macd_fast_layout)
        
        # EMA Lenta
        macd_slow_layout = QHBoxLayout()
        macd_slow_layout.addWidget(QLabel("EMA Lenta:", styleSheet=label_style))
        
        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setRange(10, 100)
        self.macd_slow_spin.setValue(self.indicators['macd'].config.params['slow_period'])
        self.macd_slow_spin.valueChanged.connect(self.on_macd_params_changed)
        self.macd_slow_spin.setStyleSheet(spinbox_style)
        macd_slow_layout.addWidget(self.macd_slow_spin)
        macd_slow_layout.addStretch()
        macd_layout.addLayout(macd_slow_layout)
        
        # Señal
        macd_signal_layout = QHBoxLayout()
        macd_signal_layout.addWidget(QLabel("Señal:", styleSheet=label_style))
        
        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setRange(5, 30)
        self.macd_signal_spin.setValue(self.indicators['macd'].config.params['signal_period'])
        self.macd_signal_spin.valueChanged.connect(self.on_macd_params_changed)
        self.macd_signal_spin.setStyleSheet(spinbox_style)
        macd_signal_layout.addWidget(self.macd_signal_spin)
        macd_signal_layout.addStretch()
        macd_layout.addLayout(macd_signal_layout)
        
        scroll_layout.addWidget(macd_group)
        
        # 4. Grupo de Bandas de Bollinger
        bb_group = QGroupBox("📊 Bandas de Bollinger")
        bb_group.setStyleSheet(group_style)
        bb_layout = QVBoxLayout(bb_group)
        
        # Checkbox de habilitación
        bb_check_layout = QHBoxLayout()
        self.bb_checkbox = QCheckBox("Habilitar Bandas de Bollinger")
        self.bb_checkbox.setChecked(self.indicators['bollinger'].config.enabled)
        self.bb_checkbox.stateChanged.connect(self.on_bollinger_changed)
        self.bb_checkbox.setStyleSheet(checkbox_style)
        bb_check_layout.addWidget(self.bb_checkbox)
        bb_check_layout.addStretch()
        bb_layout.addLayout(bb_check_layout)
        
        # Período
        bb_period_layout = QHBoxLayout()
        bb_period_layout.addWidget(QLabel("Período SMA:", styleSheet=label_style))
        
        self.bb_period_spin = QSpinBox()
        self.bb_period_spin.setRange(10, 50)
        self.bb_period_spin.setValue(self.indicators['bollinger'].config.params['period'])
        self.bb_period_spin.valueChanged.connect(self.on_bollinger_params_changed)
        self.bb_period_spin.setStyleSheet(spinbox_style)
        bb_period_layout.addWidget(self.bb_period_spin)
        bb_period_layout.addStretch()
        bb_layout.addLayout(bb_period_layout)
        
        # Desviaciones
        bb_std_layout = QHBoxLayout()
        bb_std_layout.addWidget(QLabel("Desviaciones:", styleSheet=label_style))
        
        self.bb_std_spin = QDoubleSpinBox()
        self.bb_std_spin.setRange(1.0, 3.0)
        self.bb_std_spin.setSingleStep(0.1)
        self.bb_std_spin.setValue(self.indicators['bollinger'].config.params['std_multiplier'])
        self.bb_std_spin.valueChanged.connect(self.on_bollinger_params_changed)
        self.bb_std_spin.setStyleSheet(spinbox_style)
        bb_std_layout.addWidget(self.bb_std_spin)
        bb_std_layout.addStretch()
        bb_layout.addLayout(bb_std_layout)
        
        scroll_layout.addWidget(bb_group)
        
        # 5. Grupo de Stochastic
        stoch_group = QGroupBox("📈 Oscilador Estocástico (Stochastic)")
        stoch_group.setStyleSheet(group_style)
        stoch_layout = QVBoxLayout(stoch_group)
        
        # Checkbox de habilitación
        stoch_check_layout = QHBoxLayout()
        self.stoch_checkbox = QCheckBox("Habilitar Stochastic")
        self.stoch_checkbox.setChecked(self.indicators['stochastic'].config.enabled)
        self.stoch_checkbox.stateChanged.connect(self.on_stochastic_changed)
        self.stoch_checkbox.setStyleSheet(checkbox_style)
        stoch_check_layout.addWidget(self.stoch_checkbox)
        stoch_check_layout.addStretch()
        stoch_layout.addLayout(stoch_check_layout)
        
        # Período %K
        stoch_k_layout = QHBoxLayout()
        stoch_k_layout.addWidget(QLabel("Período %K:", styleSheet=label_style))
        
        self.stoch_k_spin = QSpinBox()
        self.stoch_k_spin.setRange(5, 50)
        self.stoch_k_spin.setValue(self.indicators['stochastic'].config.params['k_period'])
        self.stoch_k_spin.valueChanged.connect(self.on_stochastic_params_changed)
        self.stoch_k_spin.setStyleSheet(spinbox_style)
        stoch_k_layout.addWidget(self.stoch_k_spin)
        stoch_k_layout.addStretch()
        stoch_layout.addLayout(stoch_k_layout)
        
        # Período %D
        stoch_d_layout = QHBoxLayout()
        stoch_d_layout.addWidget(QLabel("Período %D:", styleSheet=label_style))
        
        self.stoch_d_spin = QSpinBox()
        self.stoch_d_spin.setRange(1, 10)
        self.stoch_d_spin.setValue(self.indicators['stochastic'].config.params['d_period'])
        self.stoch_d_spin.valueChanged.connect(self.on_stochastic_params_changed)
        self.stoch_d_spin.setStyleSheet(spinbox_style)
        stoch_d_layout.addWidget(self.stoch_d_spin)
        stoch_d_layout.addStretch()
        stoch_layout.addLayout(stoch_d_layout)
        
        # Slowing
        stoch_slowing_layout = QHBoxLayout()
        stoch_slowing_layout.addWidget(QLabel("Slowing:", styleSheet=label_style))
        
        self.stoch_slowing_spin = QSpinBox()
        self.stoch_slowing_spin.setRange(1, 10)
        self.stoch_slowing_spin.setValue(self.indicators['stochastic'].config.params['slowing'])
        self.stoch_slowing_spin.valueChanged.connect(self.on_stochastic_params_changed)
        self.stoch_slowing_spin.setStyleSheet(spinbox_style)
        stoch_slowing_layout.addWidget(self.stoch_slowing_spin)
        stoch_slowing_layout.addStretch()
        stoch_layout.addLayout(stoch_slowing_layout)
        
        scroll_layout.addWidget(stoch_group)
        
        # 6. Botones de acción
        buttons_layout = QHBoxLayout()
        
        # Botón para aplicar cambios
        self.btn_apply_indicators = QPushButton("✅ Aplicar al Gráfico")
        self.btn_apply_indicators.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.btn_apply_indicators.clicked.connect(self.apply_indicators)
        buttons_layout.addWidget(self.btn_apply_indicators)
        
        # Botón para guardar configuración
        self.btn_save_indicators = QPushButton("💾 Guardar Config")
        self.btn_save_indicators.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_save_indicators.clicked.connect(self.save_indicators_config)
        buttons_layout.addWidget(self.btn_save_indicators)
        
        # Botón para cargar configuración
        self.btn_load_indicators = QPushButton("📂 Cargar Config")
        self.btn_load_indicators.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.btn_load_indicators.clicked.connect(self.load_indicators_config)
        buttons_layout.addWidget(self.btn_load_indicators)
        
        buttons_layout.addStretch()
        scroll_layout.addLayout(buttons_layout)
        
        # 7. Panel de información
        info_group = QGroupBox("ℹ️ Información de Indicadores")
        info_group.setStyleSheet(group_style)
        info_layout = QVBoxLayout(info_group)
        
        self.indicators_info = QTextEdit()
        self.indicators_info.setReadOnly(True)
        self.indicators_info.setMaximumHeight(120)
        self.indicators_info.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
            }
        """)
        self.indicators_info.setPlaceholderText("Información de indicadores...")
        info_layout.addWidget(self.indicators_info)
        
        scroll_layout.addWidget(info_group)
        scroll_layout.addStretch()
        
        # Configurar scroll area
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        
        # Actualizar información inicial
        self.update_indicators_info()
        
        return widget
    
    # ===== MÉTODOS PARA MANEJAR INDICADORES =====
    
    def change_indicator_color(self, indicator_name: str):
        """Cambiar color de un indicador."""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.indicators[indicator_name].set_config(color=hex_color)
            
            # Actualizar botón de color
            btn = getattr(self, f'{indicator_name}_color_btn')
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 1px solid #666;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #fff;
                }}
            """)
            
            self.update_indicators_info()
    
    def on_sma_changed(self):
        """Manejador para cambios en SMA."""
        enabled = self.sma_checkbox.isChecked()
        period = self.sma_period_spin.value()
        self.indicators['sma'].set_config(
            enabled=enabled,
            period=period
        )
        self.update_indicators_info()
    
    def on_ema_changed(self):
        """Manejador para cambios en EMA."""
        enabled = self.ema_checkbox.isChecked()
        period = self.ema_period_spin.value()
        self.indicators['ema'].set_config(
            enabled=enabled,
            period=period
        )
        self.update_indicators_info()
    
    def on_rsi_changed(self):
        """Manejador para habilitar/deshabilitar RSI."""
        enabled = self.rsi_checkbox.isChecked()
        self.indicators['rsi'].set_config(enabled=enabled)
        self.update_indicators_info()
    
    def on_rsi_period_changed(self):
        """Manejador para cambios en período RSI."""
        period = self.rsi_period_spin.value()
        self.rsi_period_slider.setValue(period)
        self.indicators['rsi'].set_config(period=period)
        self.update_indicators_info()
    
    def on_rsi_levels_changed(self):
        """Manejador para cambios en niveles RSI."""
        overbought = self.rsi_overbought_spin.value()
        oversold = self.rsi_oversold_spin.value()
        self.indicators['rsi'].set_config(
            overbought=overbought,
            oversold=oversold
        )
        self.update_indicators_info()
    
    def on_macd_changed(self):
        """Manejador para habilitar/deshabilitar MACD."""
        enabled = self.macd_checkbox.isChecked()
        self.indicators['macd'].set_config(enabled=enabled)
        self.update_indicators_info()
    
    def on_macd_params_changed(self):
        """Manejador para cambios en parámetros MACD."""
        fast = self.macd_fast_spin.value()
        slow = self.macd_slow_spin.value()
        signal = self.macd_signal_spin.value()
        self.indicators['macd'].set_config(
            fast_period=fast,
            slow_period=slow,
            signal_period=signal
        )
        self.update_indicators_info()
    
    def on_bollinger_changed(self):
        """Manejador para habilitar/deshabilitar Bollinger."""
        enabled = self.bb_checkbox.isChecked()
        self.indicators['bollinger'].set_config(enabled=enabled)
        self.update_indicators_info()
    
    def on_bollinger_params_changed(self):
        """Manejador para cambios en parámetros Bollinger."""
        period = self.bb_period_spin.value()
        std = self.bb_std_spin.value()
        self.indicators['bollinger'].set_config(
            period=period,
            std_multiplier=std
        )
        self.update_indicators_info()
    
    def on_stochastic_changed(self):
        """Manejador para habilitar/deshabilitar Stochastic."""
        enabled = self.stoch_checkbox.isChecked()
        self.indicators['stochastic'].set_config(enabled=enabled)
        self.update_indicators_info()
    
    def on_stochastic_params_changed(self):
        """Manejador para cambios en parámetros Stochastic."""
        k_period = self.stoch_k_spin.value()
        d_period = self.stoch_d_spin.value()
        slowing = self.stoch_slowing_spin.value()
        self.indicators['stochastic'].set_config(
            k_period=k_period,
            d_period=d_period,
            slowing=slowing
        )
        self.update_indicators_info()
    
    def apply_indicators(self):
        """Aplicar configuración de indicadores al gráfico."""
        # Obtener configuración actual de todos los indicadores
        indicators_config = {}
        for name, indicator in self.indicators.items():
            indicators_config[name] = {
                'enabled': indicator.config.enabled,
                'color': indicator.config.color,
                'line_width': indicator.config.line_width,
                'params': indicator.config.params.copy()
            }
        
        # Emitir señal con la configuración
        self.indicators_updated.emit(indicators_config)
        
        # Mostrar mensaje de confirmación
        self.indicators_info.append("✅ Indicadores aplicados al gráfico")
        
        # Log de lo que se envió
        enabled_count = sum(1 for config in indicators_config.values() if config['enabled'])
        self.indicators_info.append(f"📊 {enabled_count} indicadores activos")
    
    def save_indicators_config(self):
        """Guardar configuración de indicadores en archivo."""
        config_data = {}
        for name, indicator in self.indicators.items():
            config_data[name] = indicator.get_config_dict()
        
        try:
            with open('indicators_config.json', 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self.indicators_info.append("💾 Configuración guardada exitosamente")
            
        except Exception as e:
            self.indicators_info.append(f"❌ Error al guardar: {str(e)}")
    
    def load_indicators_config(self):
        """Cargar configuración de indicadores desde archivo."""
        try:
            with open('indicators_config.json', 'r') as f:
                config_data = json.load(f)
            
            # Aplicar configuración a cada indicador
            for name, config in config_data.items():
                if name in self.indicators:
                    self.indicators[name].set_config(**config)
            
            # Actualizar controles UI
            self.update_ui_from_config()
            
            self.indicators_info.append("📂 Configuración cargada exitosamente")
            self.update_indicators_info()
            
        except FileNotFoundError:
            self.indicators_info.append("ℹ️ No se encontró archivo de configuración")
        except Exception as e:
            self.indicators_info.append(f"❌ Error al cargar: {str(e)}")
    
    def update_ui_from_config(self):
        """Actualizar controles UI desde configuración de indicadores."""
        # SMA
        self.sma_checkbox.setChecked(self.indicators['sma'].config.enabled)
        self.sma_period_spin.setValue(self.indicators['sma'].config.params['period'])
        self.sma_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['sma'].config.color};
                border: 1px solid #666;
                border-radius: 4px;
            }}
        """)
        
        # EMA
        self.ema_checkbox.setChecked(self.indicators['ema'].config.enabled)
        self.ema_period_spin.setValue(self.indicators['ema'].config.params['period'])
        self.ema_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['ema'].config.color};
                border: 1px solid #666;
                border-radius: 4px;
            }}
        """)
        
        # RSI
        self.rsi_checkbox.setChecked(self.indicators['rsi'].config.enabled)
        self.rsi_period_spin.setValue(self.indicators['rsi'].config.params['period'])
        self.rsi_period_slider.setValue(self.indicators['rsi'].config.params['period'])
        self.rsi_overbought_spin.setValue(self.indicators['rsi'].config.params['overbought'])
        self.rsi_oversold_spin.setValue(self.indicators['rsi'].config.params['oversold'])
        self.rsi_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['rsi'].config.color};
                border: 1px solid #666;
                border-radius: 4px;
            }}
        """)
        
        # MACD
        self.macd_checkbox.setChecked(self.indicators['macd'].config.enabled)
        self.macd_fast_spin.setValue(self.indicators['macd'].config.params['fast_period'])
        self.macd_slow_spin.setValue(self.indicators['macd'].config.params['slow_period'])
        self.macd_signal_spin.setValue(self.indicators['macd'].config.params['signal_period'])
        
        # Bollinger
        self.bb_checkbox.setChecked(self.indicators['bollinger'].config.enabled)
        self.bb_period_spin.setValue(self.indicators['bollinger'].config.params['period'])
        self.bb_std_spin.setValue(self.indicators['bollinger'].config.params['std_multiplier'])
        
        # Stochastic
        self.stoch_checkbox.setChecked(self.indicators['stochastic'].config.enabled)
        self.stoch_k_spin.setValue(self.indicators['stochastic'].config.params['k_period'])
        self.stoch_d_spin.setValue(self.indicators['stochastic'].config.params['d_period'])
        self.stoch_slowing_spin.setValue(self.indicators['stochastic'].config.params['slowing'])
    
    def update_indicators_info(self):
        """Actualizar panel de información de indicadores."""
        info_text = "📊 ESTADO ACTUAL DE INDICADORES:\n\n"
        
        for name, indicator in self.indicators.items():
            status = "✅ ACTIVADO" if indicator.config.enabled else "❌ DESACTIVADO"
            
            if name == 'sma':
                info_text += f"• SMA {indicator.config.params['period']}: {status} ({indicator.config.color})\n"
            elif name == 'ema':
                info_text += f"• EMA {indicator.config.params['period']}: {status} ({indicator.config.color})\n"
            elif name == 'rsi':
                info_text += f"• RSI {indicator.config.params['period']}: {status} ({indicator.config.params['oversold']}/{indicator.config.params['overbought']})\n"
            elif name == 'macd':
                info_text += f"• MACD ({indicator.config.params['fast_period']}/{indicator.config.params['slow_period']}/{indicator.config.params['signal_period']}): {status}\n"
            elif name == 'bollinger':
                info_text += f"• BB ({indicator.config.params['period']},{indicator.config.params['std_multiplier']:.1f}σ): {status}\n"
            elif name == 'stochastic':
                info_text += f"• Stochastic %K{indicator.config.params['k_period']}/%D{indicator.config.params['d_period']}/S{indicator.config.params['slowing']}: {status}\n"
        
        info_text += "\n🔄 Haga clic en 'Aplicar al Gráfico' para actualizar"
        
        self.indicators_info.setText(info_text)
    
    # ===== MÉTODOS EXISTENTES (MANTENIDOS SIN CAMBIOS) =====
    
    def create_trading_tab(self):
        """Crear pestaña de trading."""
        # ... (MANTENER CÓDIGO EXISTENTE SIN CAMBIOS)
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
        
        # Selector de timeframe
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
        # ... (MANTENER CÓDIGO EXISTENTE SIN CAMBIOS)
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
        # ... (MANTENER CÓDIGO EXISTENTE SIN CAMBIOS)
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
        # ... (MANTENER CÓDIGO EXISTENTE SIN CAMBIOS)
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
    
    # ===== MÉTODOS DE ESTADO (MANTENIDOS) =====
    
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
    
    # ===== MANEJADORES DE EVENTOS (MANTENIDOS) =====
    
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
    
    # ===== UTILIDADES (MANTENIDAS) =====
    
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