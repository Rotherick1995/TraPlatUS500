# src/infrastructure/ui/indicators_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QSlider, QPushButton,
                             QTextEdit, QScrollArea, QColorDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
import json

# Importar indicadores de dominio
from src.domain.indicators import (
    SMAIndicator, EMAIndicator, RSIIndicator,
    MACDIndicator, BollingerIndicator, StochasticIndicator
)


class IndicatorsPanel(QWidget):
    """Panel de configuración de indicadores técnicos."""
    
    # Señal para actualizar indicadores en el gráfico
    indicators_updated = pyqtSignal(dict)
    # Señal para logs
    log_message = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
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
        
        # Actualizar información inicial
        self.update_indicators_info()
    
    def init_ui(self):
        """Inicializar la interfaz de usuario."""
        layout = QVBoxLayout(self)
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
        from PyQt5.QtWidgets import QFrame
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
        
        label_style = "color: #ffffff; font-size: 12px;"
        checkbox_style = "color: #ffffff; font-size: 12px; padding: 2px;"
        spinbox_style = """
            QSpinBox, QDoubleSpinBox {
                color: #ffffff;
                background-color: #333;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 3px;
                font-size: 11px;
                min-width: 60px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #00bfff;
            }
        """
        
        # 1. Grupo de Medias Móviles
        ma_group = QGroupBox("📊 Medias Móviles")
        ma_group.setStyleSheet(group_style)
        ma_layout = QVBoxLayout(ma_group)
        
        # SMA
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
        self.sma_color_btn.setFixedSize(30, 25)
        self.sma_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['sma'].config.color};
                border: 1px solid #666;
                border-radius: 3px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border: 2px solid #fff;
            }}
        """)
        self.sma_color_btn.clicked.connect(lambda: self.change_indicator_color('sma'))
        sma_layout.addWidget(self.sma_color_btn)
        
        sma_layout.addStretch()
        ma_layout.addLayout(sma_layout)
        
        # EMA
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
        self.ema_color_btn.setFixedSize(30, 25)
        self.ema_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['ema'].config.color};
                border: 1px solid #666;
                border-radius: 3px;
                font-size: 11px;
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
        self.rsi_color_btn.setFixedSize(30, 25)
        self.rsi_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.indicators['rsi'].config.color};
                border: 1px solid #666;
                border-radius: 3px;
                font-size: 11px;
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
        self.rsi_period_slider.setStyleSheet("""
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
        """)
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
        self.bb_std_spin.setDecimals(1)
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
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    border: 2px solid #fff;
                }}
            """)
            
            self.update_indicators_info()
            self.log_message.emit(f"🎨 Color {indicator_name.upper()} cambiado a: {hex_color}", "INFO")
    
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
        try:
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
            enabled_count = sum(1 for config in indicators_config.values() if config['enabled'])
            self.log_message.emit(f"✅ {enabled_count} indicadores aplicados al gráfico", "INFO")
            
            # Mantener mensaje en el panel de indicadores
            self.indicators_info.append("✅ Indicadores aplicados al gráfico")
            self.indicators_info.append(f"📊 {enabled_count} indicadores activos")
            
        except Exception as e:
            self.log_message.emit(f"❌ Error al aplicar indicadores: {str(e)}", "ERROR")
    
    def save_indicators_config(self):
        """Guardar configuración de indicadores en archivo."""
        config_data = {}
        for name, indicator in self.indicators.items():
            config_data[name] = indicator.get_config_dict()
        
        try:
            with open('indicators_config.json', 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self.log_message.emit("💾 Configuración de indicadores guardada exitosamente", "INFO")
            self.indicators_info.append("💾 Configuración guardada exitosamente")
            
        except Exception as e:
            self.log_message.emit(f"❌ Error al guardar configuración: {str(e)}", "ERROR")
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
            
            self.log_message.emit("📂 Configuración de indicadores cargada exitosamente", "INFO")
            self.indicators_info.append("📂 Configuración cargada exitosamente")
            self.update_indicators_info()
            
        except FileNotFoundError:
            self.log_message.emit("ℹ️ No se encontró archivo de configuración de indicadores", "INFO")
            self.indicators_info.append("ℹ️ No se encontró archivo de configuración")
        except Exception as e:
            self.log_message.emit(f"❌ Error al cargar configuración: {str(e)}", "ERROR")
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
                font-size: 11px;
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
                font-size: 11px;
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
                font-size: 11px;
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
    
    def get_current_config(self):
        """Obtener configuración actual de indicadores."""
        config = {}
        for name, indicator in self.indicators.items():
            config[name] = {
                'enabled': indicator.config.enabled,
                'color': indicator.config.color,
                'params': indicator.config.params.copy()
            }
        return config
    
    def set_indicator_enabled(self, indicator_name: str, enabled: bool):
        """Habilitar/deshabilitar un indicador específico."""
        if indicator_name in self.indicators:
            self.indicators[indicator_name].set_config(enabled=enabled)
            
            # Actualizar checkbox correspondiente
            if hasattr(self, f'{indicator_name}_checkbox'):
                getattr(self, f'{indicator_name}_checkbox').setChecked(enabled)
            
            self.update_indicators_info()
    
    def set_indicator_param(self, indicator_name: str, param_name: str, value):
        """Establecer un parámetro específico de un indicador."""
        if indicator_name in self.indicators:
            params = self.indicators[indicator_name].config.params.copy()
            params[param_name] = value
            self.indicators[indicator_name].set_config(**params)
            
            # Actualizar control UI correspondiente
            control_name = f'{indicator_name}_{param_name}_spin'
            if hasattr(self, control_name):
                getattr(self, control_name).setValue(value)
            
            self.update_indicators_info()