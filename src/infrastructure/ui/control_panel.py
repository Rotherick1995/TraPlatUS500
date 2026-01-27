# src/infrastructure/ui/control_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QGridLayout, QTextEdit, QCheckBox, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
                             QMessageBox, QFrame, QScrollArea, QSlider, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QTextCursor
import json
import datetime

# Importar indicadores de dominio
from src.domain.indicators import (
    SMAIndicator, EMAIndicator, RSIIndicator,
    MACDIndicator, BollingerIndicator, StochasticIndicator
)


class ControlPanel(QWidget):
    """Panel de control para la plataforma de trading."""
    
    # Señales EXISTENTES
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    symbol_changed = pyqtSignal(str)
    timeframe_changed = pyqtSignal(str)
    buy_requested = pyqtSignal(dict)
    sell_requested = pyqtSignal(dict)
    refresh_positions = pyqtSignal()
    
    # NUEVAS SEÑALES
    indicators_updated = pyqtSignal(dict)
    candles_count_changed = pyqtSignal(int)  # Nueva señal para cantidad de velas
    log_message_received = pyqtSignal(str, str)  # message, type
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado EXISTENTE
        self.is_connected = False
        self.current_symbol = "US500"
        self.account_info = {}
        self.positions = []
        
        # NUEVO: Lista de órdenes realizadas
        self.orders = []
        
        # Configuración por defecto
        self.default_volume = 0.1
        self.default_sl = 50
        self.default_tp = 100
        
        # NUEVO: Configuración de velas
        self.default_candles_count = 100
        self.min_candles_count = 10
        self.max_candles_count = 10000
        self.current_candles_count = self.default_candles_count
        
        # NUEVO: Diccionario de información de símbolos (actualizado)
        self.symbol_info = {
            'EURUSD': {'digits': 5, 'point': 0.00001, 'lot_size': 100000, 'tick_value': 10, 'tick_size': 0.00001},
            'US500': {'digits': 2, 'point': 0.01, 'lot_size': 1, 'tick_value': 1, 'tick_size': 0.01},
            'GBPUSD': {'digits': 5, 'point': 0.00001, 'lot_size': 100000, 'tick_value': 10, 'tick_size': 0.00001},
            'USDJPY': {'digits': 3, 'point': 0.001, 'lot_size': 100000, 'tick_value': 1000, 'tick_size': 0.001},
            'XAUUSD': {'digits': 2, 'point': 0.01, 'lot_size': 100, 'tick_value': 10, 'tick_size': 0.01}
        }
        
        # NUEVO: Precio actual para cálculos
        self.current_bid_price = 0.0
        self.current_ask_price = 0.0
        
        # Instancias de indicadores de dominio
        self.indicators = {
            'sma': SMAIndicator(period=20),
            'ema': EMAIndicator(period=12),
            'rsi': RSIIndicator(period=14, overbought=70, oversold=30),
            'macd': MACDIndicator(fast_period=12, slow_period=26, signal_period=9),
            'bollinger': BollingerIndicator(period=20, std_multiplier=2.0),
            'stochastic': StochasticIndicator(k_period=14, d_period=3, slowing=3)
        }
        
        # Inicializar sistema de logs
        self.log_messages = []
        self.max_log_messages = 1000
        self.show_timestamp = True
        
        # Inicializar UI
        self.init_ui()
        
        # Conectar señal de logs
        self.log_message_received.connect(self.add_log_message)
        
        # Cargar configuración guardada
        self.load_settings()
        
        # Agregar mensaje inicial al log
        self.add_log_message("✅ Sistema de control inicializado", "INFO")
    
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
        
        # Pestañas adicionales
        self.tab_logs = self.create_logs_tab()
        self.tab_indicators = self.create_indicators_tab()
        self.tab_chart_config = self.create_chart_config_tab()
        self.tab_orders = self.create_orders_tab()  # NUEVA PESTAÑA
        
        # Agregar pestañas
        self.tab_widget.addTab(self.tab_trading, "📊 Trading")
        self.tab_widget.addTab(self.tab_positions, "💰 Posiciones")
        self.tab_widget.addTab(self.tab_account, "👤 Cuenta")
        self.tab_widget.addTab(self.tab_indicators, "📈 Indicadores")
        self.tab_widget.addTab(self.tab_chart_config, "📊 Config Gráfico")
        self.tab_widget.addTab(self.tab_orders, "📝 Órdenes")  # NUEVA PESTAÑA
        self.tab_widget.addTab(self.tab_logs, "📋 Logs")
        self.tab_widget.addTab(self.tab_settings, "⚙️ Config")
        
        layout.addWidget(self.tab_widget)
    
    # ===== NUEVA PESTAÑA: ÓRDENES REALIZADAS =====
    
    def create_orders_tab(self):
        """Crear pestaña de órdenes realizadas."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Barra de herramientas superior
        toolbar_layout = QHBoxLayout()
        
        # Título
        title_label = QLabel("📝 ÓRDENES REALIZADAS")
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin: 5px; 
            color: #ffffff;
            padding: 5px;
        """)
        toolbar_layout.addWidget(title_label)
        toolbar_layout.addStretch()
        
        # Botones de acción
        self.btn_refresh_orders = QPushButton("🔄 Actualizar")
        self.btn_refresh_orders.clicked.connect(self.on_refresh_orders)
        self.btn_refresh_orders.setEnabled(False)
        self.btn_refresh_orders.setFixedHeight(25)
        
        self.btn_export_orders = QPushButton("💾 Exportar")
        self.btn_export_orders.clicked.connect(self.export_orders)
        self.btn_export_orders.setFixedHeight(25)
        
        self.btn_clear_orders = QPushButton("🗑️ Limpiar")
        self.btn_clear_orders.clicked.connect(self.clear_orders_history)
        self.btn_clear_orders.setFixedHeight(25)
        
        toolbar_layout.addWidget(self.btn_refresh_orders)
        toolbar_layout.addWidget(self.btn_export_orders)
        toolbar_layout.addWidget(self.btn_clear_orders)
        
        layout.addLayout(toolbar_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #666; margin: 5px 0px;")
        layout.addWidget(separator)
        
        # Panel de estadísticas
        stats_panel = QWidget()
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setContentsMargins(5, 0, 5, 0)
        
        # Estadísticas de órdenes
        self.lbl_orders_stats = QLabel("Total: 0 órdenes | Compras: 0 | Ventas: 0 | Ganadas: 0 | Perdidas: 0")
        self.lbl_orders_stats.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        stats_layout.addWidget(self.lbl_orders_stats)
        stats_layout.addStretch()
        
        layout.addWidget(stats_panel)
        
        # Tabla de órdenes
        self.table_orders = QTableWidget()
        self.table_orders.setColumnCount(11)
        self.table_orders.setHorizontalHeaderLabels([
            "Ticket", "Símbolo", "Tipo", "Volumen", "Precio", 
            "SL", "TP", "Profit", "Comentario", "Fecha", "Estado"
        ])
        
        # Configurar tabla
        header = self.table_orders.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # Comentario más ancho
        
        # Estilos para la tabla
        self.table_orders.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                gridline-color: #444;
                font-size: 10px;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #444;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 3px;
            }
        """)
        
        layout.addWidget(self.table_orders, 1)
        
        # Panel inferior con detalles
        details_panel = QGroupBox("📋 Detalles de la Orden")
        details_layout = QVBoxLayout(details_panel)
        
        self.txt_order_details = QTextEdit()
        self.txt_order_details.setReadOnly(True)
        self.txt_order_details.setMaximumHeight(150)
        self.txt_order_details.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
                font-size: 10px;
            }
        """)
        self.txt_order_details.setPlaceholderText("Seleccione una orden para ver los detalles...")
        details_layout.addWidget(self.txt_order_details)
        
        layout.addWidget(details_panel)
        
        # Conectar señal de selección
        self.table_orders.itemSelectionChanged.connect(self.on_order_selected)
        
        return widget
    
    # ===== MÉTODOS PARA MANEJAR ÓRDENES =====
    
    def add_order(self, order_data):
        """Agregar una nueva orden a la lista."""
        try:
            # Agregar timestamp si no existe
            if 'time' not in order_data:
                order_data['time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Agregar estado si no existe
            if 'status' not in order_data:
                order_data['status'] = 'Ejecutada'
            
            # Agregar a la lista
            self.orders.append(order_data)
            
            # Mantener un límite razonable
            if len(self.orders) > 1000:
                self.orders = self.orders[-1000:]
            
            # Actualizar la tabla
            self.update_orders_table()
            
            # Actualizar estadísticas
            self.update_orders_stats()
            
            # Actualizar botón de refrescar
            self.btn_refresh_orders.setEnabled(self.is_connected)
            
            return True
            
        except Exception as e:
            self.add_log_message(f"❌ Error al agregar orden: {str(e)}", "ERROR")
            return False
    
    def update_orders_table(self):
        """Actualizar la tabla de órdenes."""
        try:
            # Limpiar tabla
            self.table_orders.setRowCount(0)
            
            # Ordenar órdenes por fecha (más recientes primero)
            sorted_orders = sorted(self.orders, 
                                  key=lambda x: x.get('time', ''), 
                                  reverse=True)
            
            # Agregar filas
            for i, order in enumerate(sorted_orders):
                self.table_orders.insertRow(i)
                
                # Ticket
                ticket = str(order.get('ticket', ''))
                self.table_orders.setItem(i, 0, QTableWidgetItem(ticket))
                
                # Símbolo
                symbol = order.get('symbol', '')
                self.table_orders.setItem(i, 1, QTableWidgetItem(symbol))
                
                # Tipo (Buy/Sell/Pending)
                order_type = order.get('type', 0)
                if order_type == 0:
                    type_str = "COMPRA"
                    type_color = "#4CAF50"
                elif order_type == 1:
                    type_str = "VENTA"
                    type_color = "#F44336"
                else:
                    type_str = "PENDIENTE"
                    type_color = "#FF9800"
                
                type_item = QTableWidgetItem(type_str)
                type_item.setForeground(QColor(type_color))
                self.table_orders.setItem(i, 2, type_item)
                
                # Volumen
                volume = order.get('volume', 0)
                self.table_orders.setItem(i, 3, QTableWidgetItem(f"{volume:.2f}"))
                
                # Precio
                price = order.get('price', 0)
                self.table_orders.setItem(i, 4, QTableWidgetItem(f"{price:.5f}"))
                
                # Stop Loss
                sl = order.get('sl', 0)
                sl_item = QTableWidgetItem(f"{sl:.5f}" if sl > 0 else "Sin SL")
                if sl > 0:
                    sl_item.setForeground(QColor("#ff6666"))
                self.table_orders.setItem(i, 5, sl_item)
                
                # Take Profit
                tp = order.get('tp', 0)
                tp_item = QTableWidgetItem(f"{tp:.5f}" if tp > 0 else "Sin TP")
                if tp > 0:
                    tp_item.setForeground(QColor("#66ff66"))
                self.table_orders.setItem(i, 6, tp_item)
                
                # Profit
                profit = order.get('profit', 0)
                profit_item = QTableWidgetItem(f"${profit:.2f}")
                if profit > 0:
                    profit_item.setForeground(QColor("#4CAF50"))
                    profit_item.setText(f"+${profit:.2f}")
                elif profit < 0:
                    profit_item.setForeground(QColor("#F44336"))
                self.table_orders.setItem(i, 7, profit_item)
                
                # Comentario
                comment = order.get('comment', '')
                self.table_orders.setItem(i, 8, QTableWidgetItem(comment))
                
                # Fecha
                time = order.get('time', '')
                self.table_orders.setItem(i, 9, QTableWidgetItem(time))
                
                # Estado
                status = order.get('status', '')
                status_item = QTableWidgetItem(status)
                if status == 'Ejecutada':
                    status_item.setForeground(QColor("#4CAF50"))
                elif status == 'Cancelada':
                    status_item.setForeground(QColor("#F44336"))
                elif status == 'Modificada':
                    status_item.setForeground(QColor("#2196F3"))
                self.table_orders.setItem(i, 10, status_item)
            
            # Actualizar el título de la pestaña
            self.tab_widget.setTabText(self.tab_widget.indexOf(self.tab_orders), 
                                     f"📝 Órdenes ({len(self.orders)})")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al actualizar tabla de órdenes: {str(e)}", "ERROR")
    
    def update_orders_stats(self):
        """Actualizar estadísticas de órdenes."""
        try:
            total = len(self.orders)
            buys = sum(1 for o in self.orders if o.get('type', 0) == 0)
            sells = sum(1 for o in self.orders if o.get('type', 0) == 1)
            
            # Calcular ganadas/perdidas basado en profit
            won = sum(1 for o in self.orders if o.get('profit', 0) > 0)
            lost = sum(1 for o in self.orders if o.get('profit', 0) < 0)
            
            self.lbl_orders_stats.setText(
                f"Total: {total} órdenes | "
                f"Compras: {buys} | "
                f"Ventas: {sells} | "
                f"Ganadas: {won} | "
                f"Perdidas: {lost}"
            )
            
        except Exception as e:
            print(f"Error al actualizar estadísticas: {e}")
    
    def on_order_selected(self):
        """Manejador cuando se selecciona una orden en la tabla."""
        try:
            selected_items = self.table_orders.selectedItems()
            if not selected_items:
                return
            
            row = selected_items[0].row()
            
            # Obtener datos de la orden
            ticket = self.table_orders.item(row, 0).text()
            symbol = self.table_orders.item(row, 1).text()
            order_type = self.table_orders.item(row, 2).text()
            volume = self.table_orders.item(row, 3).text()
            price = self.table_orders.item(row, 4).text()
            sl = self.table_orders.item(row, 5).text()
            tp = self.table_orders.item(row, 6).text()
            profit = self.table_orders.item(row, 7).text()
            comment = self.table_orders.item(row, 8).text()
            time = self.table_orders.item(row, 9).text()
            status = self.table_orders.item(row, 10).text()
            
            # Buscar orden completa en la lista
            order_data = None
            for order in self.orders:
                if str(order.get('ticket', '')) == ticket:
                    order_data = order
                    break
            
            # Generar texto de detalles
            details = f"""📋 DETALLES DE LA ORDEN #{ticket}

• Símbolo: {symbol}
• Tipo: {order_type}
• Volumen: {volume} lotes
• Precio de entrada: {price}
• Stop Loss: {sl}
• Take Profit: {tp}
• Resultado: {profit}
• Estado: {status}
• Fecha/Hora: {time}
• Comentario: {comment}

📊 INFORMACIÓN ADICIONAL:
"""
            
            # Agregar información adicional si está disponible
            if order_data:
                if 'price_open' in order_data:
                    details += f"• Precio apertura: {order_data['price_open']:.5f}\n"
                if 'price_close' in order_data:
                    details += f"• Precio cierre: {order_data['price_close']:.5f}\n"
                if 'magic' in order_data:
                    details += f"• Magic number: {order_data['magic']}\n"
                if 'swap' in order_data:
                    details += f"• Swap: ${order_data['swap']:.2f}\n"
                if 'commission' in order_data:
                    details += f"• Comisión: ${order_data['commission']:.2f}\n"
            
            self.txt_order_details.setText(details)
            
        except Exception as e:
            self.txt_order_details.setText(f"Error al cargar detalles: {str(e)}")
    
    def on_refresh_orders(self):
        """Refrescar la lista de órdenes desde MT5."""
        try:
            if self.is_connected:
                self.add_log_message("🔄 Refrescando historial de órdenes...", "INFO")
                # Aquí deberías llamar a MT5 para obtener el historial de órdenes
                # Por ahora, solo actualizamos la tabla local
                self.update_orders_table()
                self.add_log_message("✅ Historial de órdenes actualizado", "INFO")
        except Exception as e:
            self.add_log_message(f"❌ Error al refrescar órdenes: {str(e)}", "ERROR")
    
    def export_orders(self):
        """Exportar órdenes a archivo CSV."""
        try:
            if not self.orders:
                QMessageBox.warning(self, "Sin datos", "No hay órdenes para exportar.")
                return
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"orders_export_{timestamp}.csv"
            
            with open(filename, 'w', encoding='utf-8') as f:
                # Escribir encabezados
                f.write("Ticket,Símbolo,Tipo,Volumen,Precio,SL,TP,Profit,Comentario,Fecha,Estado\n")
                
                # Escribir datos
                for order in self.orders:
                    ticket = str(order.get('ticket', ''))
                    symbol = order.get('symbol', '')
                    order_type = "COMPRA" if order.get('type', 0) == 0 else "VENTA"
                    volume = f"{order.get('volume', 0):.2f}"
                    price = f"{order.get('price', 0):.5f}"
                    sl = f"{order.get('sl', 0):.5f}"
                    tp = f"{order.get('tp', 0):.5f}"
                    profit = f"{order.get('profit', 0):.2f}"
                    comment = order.get('comment', '').replace(',', ';')
                    time = order.get('time', '')
                    status = order.get('status', '')
                    
                    f.write(f"{ticket},{symbol},{order_type},{volume},{price},{sl},{tp},{profit},\"{comment}\",{time},{status}\n")
            
            self.add_log_message(f"✅ Órdenes exportadas a: {filename}", "INFO")
            QMessageBox.information(self, "Exportación exitosa", 
                                  f"Órdenes exportadas a:\n{filename}")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al exportar órdenes: {str(e)}", "ERROR")
    
    def clear_orders_history(self):
        """Limpiar el historial de órdenes."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro de limpiar todo el historial de órdenes?\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.orders.clear()
            self.update_orders_table()
            self.update_orders_stats()
            self.add_log_message("🗑️ Historial de órdenes limpiado", "INFO")
    
    # ===== NUEVA PESTAÑA: CONFIGURACIÓN DE GRÁFICO =====
    
    def create_chart_config_tab(self):
        """Crear pestaña de configuración del gráfico."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Estilos para elementos de esta pestaña
        label_style = "color: #ffffff; font-size: 12px; font-weight: bold;"
        spinbox_style = """
            QSpinBox {
                color: #ffffff;
                background-color: #333;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
            }
            QSpinBox:focus {
                border: 1px solid #00bfff;
            }
        """
        checkbox_style = "color: #ffffff; font-size: 12px; padding: 5px;"
        
        # Título
        title_label = QLabel("📊 CONFIGURACIÓN DEL GRÁFICO")
        title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #ffffff;
            padding: 10px;
            background-color: #2a2a2a;
            border-radius: 5px;
            border: 1px solid #444;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Grupo: Configuración de Velas
        group_candles = QGroupBox("⚙️ Configuración de Velas")
        group_candles.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                color: #ffffff;
                border: 1px solid #666;
                border-radius: 5px;
                margin-top: 10px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #00bfff;
            }
        """)
        candles_layout = QGridLayout(group_candles)
        
        # Cantidad de velas
        lbl_candles = QLabel("Cantidad de velas:")
        lbl_candles.setStyleSheet(label_style)
        candles_layout.addWidget(lbl_candles, 0, 0)
        
        self.spin_candles_count = QSpinBox()
        self.spin_candles_count.setRange(self.min_candles_count, self.max_candles_count)
        self.spin_candles_count.setValue(self.current_candles_count)
        self.spin_candles_count.setSingleStep(10)
        self.spin_candles_count.setSuffix(" velas")
        self.spin_candles_count.setStyleSheet(spinbox_style)
        self.spin_candles_count.valueChanged.connect(self.on_candles_count_changed)
        candles_layout.addWidget(self.spin_candles_count, 0, 1)
        
        # Botón para aplicar cantidad de velas
        self.btn_apply_candles = QPushButton("✅ Aplicar Cantidad")
        self.btn_apply_candles.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.btn_apply_candles.clicked.connect(self.apply_candles_count)
        self.btn_apply_candles.setEnabled(False)
        candles_layout.addWidget(self.btn_apply_candles, 0, 2)
        
        # Información sobre cantidad de velas
        info_label = QLabel("Configura la cantidad de velas históricas que se cargarán en el gráfico.\n"
                           "Mínimo: 10 | Máximo: 10,000 | Valor por defecto: 100")
        info_label.setStyleSheet("color: #aaaaaa; font-size: 11px; font-style: italic;")
        info_label.setWordWrap(True)
        candles_layout.addWidget(info_label, 1, 0, 1, 3)
        
        layout.addWidget(group_candles)
        
        # Grupo: Rango de Cantidad de Velas
        group_candles_range = QGroupBox("📏 Rango de Cantidad de Velas")
        group_candles_range.setStyleSheet(group_candles.styleSheet())
        range_layout = QGridLayout(group_candles_range)
        
        # Configuración de rangos
        lbl_min_candles = QLabel("Cantidad mínima:")
        lbl_min_candles.setStyleSheet(label_style)
        range_layout.addWidget(lbl_min_candles, 0, 0)
        
        self.spin_min_candles = QSpinBox()
        self.spin_min_candles.setRange(5, 1000)
        self.spin_min_candles.setValue(self.min_candles_count)
        self.spin_min_candles.setStyleSheet(spinbox_style)
        self.spin_min_candles.valueChanged.connect(self.on_min_candles_changed)
        range_layout.addWidget(self.spin_min_candles, 0, 1)
        
        lbl_max_candles = QLabel("Cantidad máxima:")
        lbl_max_candles.setStyleSheet(label_style)
        range_layout.addWidget(lbl_max_candles, 1, 0)
        
        self.spin_max_candles = QSpinBox()
        self.spin_max_candles.setRange(100, 20000)
        self.spin_max_candles.setValue(self.max_candles_count)
        self.spin_max_candles.setStyleSheet(spinbox_style)
        self.spin_max_candles.valueChanged.connect(self.on_max_candles_changed)
        range_layout.addWidget(self.spin_max_candles, 1, 1)
        
        # Botón para aplicar rangos
        self.btn_apply_range = QPushButton("⚙️ Aplicar Rangos")
        self.btn_apply_range.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_apply_range.clicked.connect(self.apply_candles_range)
        range_layout.addWidget(self.btn_apply_range, 0, 2, 2, 1)
        
        layout.addWidget(group_candles_range)
        
        # Grupo: Configuración de Visualización
        group_display = QGroupBox("👁️ Configuración de Visualización")
        group_display.setStyleSheet(group_candles.styleSheet())
        display_layout = QVBoxLayout(group_display)
        
        # Mostrar/Ocultar líneas de grid
        self.cb_show_grid = QCheckBox("Mostrar líneas de grid en el gráfico")
        self.cb_show_grid.setChecked(True)
        self.cb_show_grid.setStyleSheet(checkbox_style)
        self.cb_show_grid.stateChanged.connect(self.on_show_grid_changed)
        display_layout.addWidget(self.cb_show_grid)
        
        # Mostrar/Ocultar volumen
        self.cb_show_volume = QCheckBox("Mostrar volumen en el gráfico")
        self.cb_show_volume.setChecked(True)
        self.cb_show_volume.setStyleSheet(checkbox_style)
        self.cb_show_volume.stateChanged.connect(self.on_show_volume_changed)
        display_layout.addWidget(self.cb_show_volume)
        
        # Mostrar/Ocultar precios cruzados
        self.cb_show_crosshair = QCheckBox("Mostrar precios cruzados (crosshair)")
        self.cb_show_crosshair.setChecked(True)
        self.cb_show_crosshair.setStyleSheet(checkbox_style)
        self.cb_show_crosshair.stateChanged.connect(self.on_show_crosshair_changed)
        display_layout.addWidget(self.cb_show_crosshair)
        
        layout.addWidget(group_display)
        
        # Grupo: Colores del Gráfico
        group_colors = QGroupBox("🎨 Colores del Gráfico")
        group_colors.setStyleSheet(group_candles.styleSheet())
        colors_layout = QGridLayout(group_colors)
        
        # Botón para color de velas alcistas
        lbl_bull_color = QLabel("Velas alcistas:")
        lbl_bull_color.setStyleSheet(label_style)
        colors_layout.addWidget(lbl_bull_color, 0, 0)
        
        self.btn_bull_color = QPushButton("▉")
        self.btn_bull_color.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: 2px solid #ffffff;
                border-radius: 3px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5CBF60;
                border: 2px solid #00ff00;
            }
        """)
        self.btn_bull_color.clicked.connect(self.change_bull_color)
        colors_layout.addWidget(self.btn_bull_color, 0, 1)
        
        # Botón para color de velas bajistas
        lbl_bear_color = QLabel("Velas bajistas:")
        lbl_bear_color.setStyleSheet(label_style)
        colors_layout.addWidget(lbl_bear_color, 1, 0)
        
        self.btn_bear_color = QPushButton("▉")
        self.btn_bear_color.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                border: 2px solid #ffffff;
                border-radius: 3px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FF5347;
                border: 2px solid #ff0000;
            }
        """)
        self.btn_bear_color.clicked.connect(self.change_bear_color)
        colors_layout.addWidget(self.btn_bear_color, 1, 1)
        
        # Botón para color de fondo
        lbl_bg_color = QLabel("Fondo del gráfico:")
        lbl_bg_color.setStyleSheet(label_style)
        colors_layout.addWidget(lbl_bg_color, 2, 0)
        
        self.btn_background_color = QPushButton("▉")
        self.btn_background_color.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                border: 2px solid #ffffff;
                border-radius: 3px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2e2e2e;
                border: 2px solid #00bfff;
            }
        """)
        self.btn_background_color.clicked.connect(self.change_background_color)
        colors_layout.addWidget(self.btn_background_color, 2, 1)
        
        layout.addWidget(group_colors)
        
        # Panel de información
        info_group = QGroupBox("ℹ️ Información del Gráfico")
        info_group.setStyleSheet(group_candles.styleSheet())
        info_layout = QVBoxLayout(info_group)
        
        self.chart_info_text = QTextEdit()
        self.chart_info_text.setReadOnly(True)
        self.chart_info_text.setMaximumHeight(100)
        self.chart_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
            }
        """)
        self.chart_info_text.setPlaceholderText("Información del gráfico...")
        info_layout.addWidget(self.chart_info_text)
        
        # Actualizar información inicial
        self.update_chart_info()
        
        layout.addWidget(info_group)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Botón para aplicar todos los cambios
        self.btn_apply_all_changes = QPushButton("🚀 Aplicar Todos los Cambios")
        self.btn_apply_all_changes.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 15px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 12px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.btn_apply_all_changes.clicked.connect(self.apply_all_chart_changes)
        buttons_layout.addWidget(self.btn_apply_all_changes)
        
        # Botón para guardar configuración
        self.btn_save_chart_config = QPushButton("💾 Guardar Config")
        self.btn_save_chart_config.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 15px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_save_chart_config.clicked.connect(self.save_chart_config)
        buttons_layout.addWidget(self.btn_save_chart_config)
        
        # Botón para cargar configuración
        self.btn_load_chart_config = QPushButton("📂 Cargar Config")
        self.btn_load_chart_config.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 10px 15px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.btn_load_chart_config.clicked.connect(self.load_chart_config)
        buttons_layout.addWidget(self.btn_load_chart_config)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        return widget
    
    # ===== MÉTODOS PARA MANEJAR CONFIGURACIÓN DE GRÁFICO =====
    
    def on_candles_count_changed(self, value):
        """Manejador para cambio en cantidad de velas."""
        self.current_candles_count = value
        self.btn_apply_candles.setEnabled(True)
        self.update_chart_info()
    
    def apply_candles_count(self):
        """Aplicar cantidad de velas seleccionada."""
        try:
            self.candles_count_changed.emit(self.current_candles_count)
            self.add_log_message(f"📊 Cantidad de velas cambiada a: {self.current_candles_count}", "INFO")
            self.chart_info_text.append(f"✅ Cantidad de velas aplicada: {self.current_candles_count}")
            self.btn_apply_candles.setEnabled(False)
            
        except Exception as e:
            self.add_log_message(f"❌ Error al aplicar cantidad de velas: {str(e)}", "ERROR")
            self.chart_info_text.append(f"❌ Error: {str(e)}")
    
    def on_min_candles_changed(self, value):
        """Manejador para cambio en cantidad mínima."""
        self.min_candles_count = value
        if value > self.spin_candles_count.value():
            self.spin_candles_count.setValue(value)
    
    def on_max_candles_changed(self, value):
        """Manejador para cambio en cantidad máxima."""
        self.max_candles_count = value
        if value < self.spin_candles_count.value():
            self.spin_candles_count.setValue(value)
    
    def apply_candles_range(self):
        """Aplicar rango de velas seleccionado."""
        try:
            self.spin_candles_count.setRange(self.min_candles_count, self.max_candles_count)
            self.add_log_message(f"📏 Rango de velas actualizado: {self.min_candles_count}-{self.max_candles_count}", "INFO")
            self.chart_info_text.append(f"✅ Rango actualizado: {self.min_candles_count}-{self.max_candles_count}")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al aplicar rango de velas: {str(e)}", "ERROR")
            self.chart_info_text.append(f"❌ Error: {str(e)}")
    
    def on_show_grid_changed(self, state):
        """Manejador para mostrar/ocultar grid."""
        show_grid = state == Qt.Checked
        # Aquí deberías emitir una señal o llamar a un método para actualizar el gráfico
        self.add_log_message(f"📐 Grid {'activado' if show_grid else 'desactivado'}", "INFO")
    
    def on_show_volume_changed(self, state):
        """Manejador para mostrar/ocultar volumen."""
        show_volume = state == Qt.Checked
        # Aquí deberías emitir una señal o llamar a un método para actualizar el gráfico
        self.add_log_message(f"📈 Volumen {'activado' if show_volume else 'desactivado'}", "INFO")
    
    def on_show_crosshair_changed(self, state):
        """Manejador para mostrar/ocultar crosshair."""
        show_crosshair = state == Qt.Checked
        # Aquí deberías emitir una señal o llamar a un método para actualizar el gráfico
        self.add_log_message(f"🎯 Crosshair {'activado' if show_crosshair else 'desactivado'}", "INFO")
    
    def change_bull_color(self):
        """Cambiar color de velas alcistas."""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.btn_bull_color.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 2px solid #ffffff;
                    border-radius: 3px;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {self._adjust_color(hex_color, 20)};
                    border: 2px solid #00ff00;
                }}
            """)
            self.add_log_message(f"🎨 Color de velas alcistas cambiado a: {hex_color}", "INFO")
    
    def change_bear_color(self):
        """Cambiar color de velas bajistas."""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.btn_bear_color.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 2px solid #ffffff;
                    border-radius: 3px;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {self._adjust_color(hex_color, 20)};
                    border: 2px solid #ff0000;
                }}
            """)
            self.add_log_message(f"🎨 Color de velas bajistas cambiado a: {hex_color}", "INFO")
    
    def change_background_color(self):
        """Cambiar color de fondo del gráfico."""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.btn_background_color.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 2px solid #ffffff;
                    border-radius: 3px;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {self._adjust_color(hex_color, 20)};
                    border: 2px solid #00bfff;
                }}
            """)
            self.add_log_message(f"🎨 Color de fondo cambiado a: {hex_color}", "INFO")
    
    def _adjust_color(self, hex_color, amount):
        """Ajustar brillo de color (método auxiliar)."""
        # Método simplificado para ajustar color
        # En implementación real, deberías convertir el color y ajustar brillo
        return hex_color
    
    def update_chart_info(self):
        """Actualizar información del gráfico."""
        info_text = f"""📊 INFORMACIÓN DEL GRÁFICO:

• Cantidad de velas actual: {self.current_candles_count}
• Rango permitido: {self.min_candles_count} - {self.max_candles_count}
• Grid: {'Activado' if self.cb_show_grid.isChecked() else 'Desactivado'}
• Volumen: {'Visible' if self.cb_show_volume.isChecked() else 'Oculto'}
• Crosshair: {'Activado' if self.cb_show_crosshair.isChecked() else 'Desactivado'}

⚙️ Haga clic en 'Aplicar Cantidad' para cargar la cantidad de velas seleccionada.
"""
        self.chart_info_text.setText(info_text)
    
    def apply_all_chart_changes(self):
        """Aplicar todos los cambios de configuración del gráfico."""
        try:
            # Aplicar cantidad de velas
            self.apply_candles_count()
            
            # Aplicar rango de velas
            self.apply_candles_range()
            
            # Aquí deberías agregar más lógica para aplicar otros cambios
            self.add_log_message("🚀 Todos los cambios del gráfico aplicados", "INFO")
            self.chart_info_text.append("✅ Todos los cambios aplicados exitosamente")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al aplicar cambios: {str(e)}", "ERROR")
            self.chart_info_text.append(f"❌ Error: {str(e)}")
    
    def save_chart_config(self):
        """Guardar configuración del gráfico en archivo."""
        config_data = {
            'candles_count': self.current_candles_count,
            'min_candles': self.min_candles_count,
            'max_candles': self.max_candles_count,
            'show_grid': self.cb_show_grid.isChecked(),
            'show_volume': self.cb_show_volume.isChecked(),
            'show_crosshair': self.cb_show_crosshair.isChecked(),
            'chart_settings': {
                'bull_color': self.btn_bull_color.styleSheet().split('background-color: ')[1].split(';')[0],
                'bear_color': self.btn_bear_color.styleSheet().split('background-color: ')[1].split(';')[0],
                'background_color': self.btn_background_color.styleSheet().split('background-color: ')[1].split(';')[0]
            }
        }
        
        try:
            with open('chart_config.json', 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self.add_log_message("💾 Configuración del gráfico guardada exitosamente", "INFO")
            self.chart_info_text.append("💾 Configuración guardada exitosamente")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al guardar configuración del gráfico: {str(e)}", "ERROR")
            self.chart_info_text.append(f"❌ Error: {str(e)}")
    
    def load_chart_config(self):
        """Cargar configuración del gráfico desde archivo."""
        try:
            with open('chart_config.json', 'r') as f:
                config_data = json.load(f)
            
            # Aplicar configuración
            self.current_candles_count = config_data.get('candles_count', 100)
            self.min_candles_count = config_data.get('min_candles', 10)
            self.max_candles_count = config_data.get('max_candles', 10000)
            
            # Actualizar controles
            self.spin_candles_count.setValue(self.current_candles_count)
            self.spin_min_candles.setValue(self.min_candles_count)
            self.spin_max_candles.setValue(self.max_candles_count)
            
            # Aplicar checkboxes
            self.cb_show_grid.setChecked(config_data.get('show_grid', True))
            self.cb_show_volume.setChecked(config_data.get('show_volume', True))
            self.cb_show_crosshair.setChecked(config_data.get('show_crosshair', True))
            
            # Aplicar colores si existen
            chart_settings = config_data.get('chart_settings', {})
            if 'bull_color' in chart_settings:
                self.btn_bull_color.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {chart_settings['bull_color']};
                        border: 2px solid #ffffff;
                        border-radius: 3px;
                        padding: 10px;
                        font-weight: bold;
                        font-size: 14px;
                    }}
                """)
            
            if 'bear_color' in chart_settings:
                self.btn_bear_color.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {chart_settings['bear_color']};
                        border: 2px solid #ffffff;
                        border-radius: 3px;
                        padding: 10px;
                        font-weight: bold;
                        font-size: 14px;
                    }}
                """)
            
            if 'background_color' in chart_settings:
                self.btn_background_color.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {chart_settings['background_color']};
                        border: 2px solid #ffffff;
                        border-radius: 3px;
                        padding: 10px;
                        font-weight: bold;
                        font-size: 14px;
                    }}
                """)
            
            self.add_log_message("📂 Configuración del gráfico cargada exitosamente", "INFO")
            self.chart_info_text.append("📂 Configuración cargada exitosamente")
            self.update_chart_info()
            
        except FileNotFoundError:
            self.add_log_message("ℹ️ No se encontró archivo de configuración del gráfico", "INFO")
            self.chart_info_text.append("ℹ️ No se encontró archivo de configuración")
        except Exception as e:
            self.add_log_message(f"❌ Error al cargar configuración del gráfico: {str(e)}", "ERROR")
            self.chart_info_text.append(f"❌ Error: {str(e)}")
    
    # ===== NUEVOS MÉTODOS PARA CÁLCULOS DE SL/TP EN DÓLARES =====
    
    def calculate_sl_tp_dollars(self, pips: float, operation_type: str = 'buy') -> dict:
        """
        Calcular valor en dólares de SL/TP basado en pips.
        
        Args:
            pips: Cantidad de pips (puede ser positivo o negativo)
            operation_type: 'buy' o 'sell'
            
        Returns:
            dict: {'dollars': valor en dólares, 'pips': pips originales, 'type': 'pips' o 'level'}
        """
        symbol = self.current_symbol
        if symbol not in self.symbol_info:
            return {'dollars': 0.0, 'pips': pips, 'type': 'error'}
        
        info = self.symbol_info[symbol]
        volume = self.spin_volume.value()
        
        # Si pips es negativo, interpretar como nivel absoluto
        if pips < 0:
            # Para niveles absolutos, el valor en dólares depende de la diferencia con el precio actual
            if operation_type == 'buy':
                # Para compras: si el nivel es más bajo que el precio actual, es pérdida
                current_price = self.current_ask_price
                level = abs(pips) * info['tick_size']
                price_diff = abs(current_price - level)
            else:
                # Para ventas: si el nivel es más alto que el precio actual, es pérdida
                current_price = self.current_bid_price
                level = abs(pips) * info['tick_size']
                price_diff = abs(level - current_price)
            
            # Calcular valor en dólares basado en la diferencia de precio
            pip_value = (price_diff / info['point']) * volume * info['tick_value']
            
            return {
                'dollars': abs(pip_value),
                'pips': pips,
                'type': 'level',
                'level': level
            }
        else:
            # Pips positivos: calcular normalmente
            pip_value = (pips / info['point']) * volume * info['tick_value']
            
            return {
                'dollars': abs(pip_value),
                'pips': pips,
                'type': 'pips'
            }
    
    def calculate_sl_tp_levels(self, operation_type: str, price: float, sl_pips: float, tp_pips: float) -> dict:
        """
        Calcular niveles de SL y TP basado en pips (positivos o negativos).
        
        Args:
            operation_type: 'buy' o 'sell'
            price: Precio de entrada
            sl_pips: Pips para SL (positivo = distancia, negativo = nivel absoluto)
            tp_pips: Pips para TP (positivo = distancia, negativo = nivel absoluto)
        
        Returns:
            dict: {'sl_level': precio, 'tp_level': precio, 'sl_distance': pips, 'tp_distance': pips}
        """
        if not price or price <= 0:
            return {'sl_level': 0, 'tp_level': 0, 'sl_distance': 0, 'tp_distance': 0}
        
        symbol = self.current_symbol
        if symbol not in self.symbol_info:
            return {'sl_level': 0, 'tp_level': 0, 'sl_distance': 0, 'tp_distance': 0}
        
        info = self.symbol_info[symbol]
        point = info['point']
        tick_size = info.get('tick_size', point)
        
        # Calcular niveles
        if operation_type == 'buy':
            # Para compras:
            # - SL debe estar POR DEBAJO del precio de entrada (menor valor)
            # - TP debe estar POR ENCIMA del precio de entrada (mayor valor)
            
            if sl_pips < 0:
                # Si es negativo, interpretar como nivel absoluto
                sl_level = abs(sl_pips) * tick_size if sl_pips != 0 else 0
            else:
                # Si es positivo, calcular distancia desde precio
                sl_level = price - (sl_pips * point)
            
            if tp_pips < 0:
                # Si es negativo, interpretar como nivel absoluto
                tp_level = abs(tp_pips) * tick_size if tp_pips != 0 else 0
            else:
                # Si es positivo, calcular distancia desde precio
                tp_level = price + (tp_pips * point)
        
        else:  # sell
            # Para ventas:
            # - SL debe estar POR ENCIMA del precio de entrada (mayor valor)
            # - TP debe estar POR DEBAJO del precio de entrada (menor valor)
            
            if sl_pips < 0:
                # Si es negativo, interpretar como nivel absoluto
                sl_level = abs(sl_pips) * tick_size if sl_pips != 0 else 0
            else:
                # Si es positivo, calcular distancia desde precio
                sl_level = price + (sl_pips * point)
            
            if tp_pips < 0:
                # Si es negativo, interpretar como nivel absoluto
                tp_level = abs(tp_pips) * tick_size if tp_pips != 0 else 0
            else:
                # Si es positivo, calcular distancia desde precio
                tp_level = price - (tp_pips * point)
        
        # Calcular distancia en pips
        sl_distance = abs((price - sl_level) / point) if sl_level > 0 else 0
        tp_distance = abs((tp_level - price) / point) if tp_level > 0 else 0
        
        return {
            'sl_level': sl_level,
            'tp_level': tp_level,
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def update_sl_display(self):
        """Actualizar display de Stop Loss."""
        sl_pips = self.spin_sl.value()
        
        # Mostrar información sobre SL negativo
        if sl_pips < 0:
            symbol_info = self.symbol_info.get(self.current_symbol, {})
            sl_level = abs(sl_pips) * symbol_info.get('tick_size', symbol_info.get('point', 0.00001))
            
            tooltip_text = f"""
            Stop Loss ({self.current_symbol}):
            • Nivel absoluto: {sl_level:.5f}
            • Pips ingresados: {sl_pips} (negativo = nivel absoluto)
            • Punto: {symbol_info.get('point', 0.00001)}
            • Tick size: {symbol_info.get('tick_size', 0.00001)}
            • Dígitos: {symbol_info.get('digits', 5)}
            """
            self.spin_sl.setToolTip(tooltip_text.strip())
            
            if hasattr(self, 'lbl_sl_value'):
                self.lbl_sl_value.setText(f"SL: Nivel {sl_level:.5f}")
        else:
            calculation = self.calculate_sl_tp_dollars(sl_pips)
            
            symbol_info = self.symbol_info.get(self.current_symbol, {})
            tooltip_text = f"""
            Stop Loss ({self.current_symbol}):
            • Pips: {sl_pips}
            • Valor en dólares: ${calculation['dollars']:.2f}
            • Punto: {symbol_info.get('point', 0.00001)}
            • Dígitos: {symbol_info.get('digits', 5)}
            """
            self.spin_sl.setToolTip(tooltip_text.strip())
            
            if hasattr(self, 'lbl_sl_value'):
                self.lbl_sl_value.setText(f"SL: {sl_pips} pips (${calculation['dollars']:.2f})")
    
    def update_tp_display(self):
        """Actualizar display de Take Profit."""
        tp_pips = self.spin_tp.value()
        
        # Mostrar información sobre TP negativo
        if tp_pips < 0:
            symbol_info = self.symbol_info.get(self.current_symbol, {})
            tp_level = abs(tp_pips) * symbol_info.get('tick_size', symbol_info.get('point', 0.00001))
            
            tooltip_text = f"""
            Take Profit ({self.current_symbol}):
            • Nivel absoluto: {tp_level:.5f}
            • Pips ingresados: {tp_pips} (negativo = nivel absoluto)
            • Punto: {symbol_info.get('point', 0.00001)}
            • Tick size: {symbol_info.get('tick_size', 0.00001)}
            • Dígitos: {symbol_info.get('digits', 5)}
            """
            self.spin_tp.setToolTip(tooltip_text.strip())
            
            if hasattr(self, 'lbl_tp_value'):
                self.lbl_tp_value.setText(f"TP: Nivel {tp_level:.5f}")
        else:
            calculation = self.calculate_sl_tp_dollars(tp_pips)
            
            symbol_info = self.symbol_info.get(self.current_symbol, {})
            tooltip_text = f"""
            Take Profit ({self.current_symbol}):
            • Pips: {tp_pips}
            • Valor en dólares: ${calculation['dollars']:.2f}
            • Punto: {symbol_info.get('point', 0.00001)}
            • Dígitos: {symbol_info.get('digits', 5)}
            """
            self.spin_tp.setToolTip(tooltip_text.strip())
            
            if hasattr(self, 'lbl_tp_value'):
                self.lbl_tp_value.setText(f"TP: {tp_pips} pips (${calculation['dollars']:.2f})")
    
    def update_risk_reward_ratio(self):
        """Actualizar ratio riesgo/recompensa."""
        sl_pips = self.spin_sl.value()
        tp_pips = self.spin_tp.value()
        
        if sl_pips > 0 and tp_pips > 0:
            ratio = tp_pips / sl_pips
            if hasattr(self, 'lbl_risk_reward'):
                self.lbl_risk_reward.setText(f"R/R: 1:{ratio:.2f}")
        elif sl_pips < 0 or tp_pips < 0:
            if hasattr(self, 'lbl_risk_reward'):
                self.lbl_risk_reward.setText(f"R/R: Niveles absolutos")
    
    # ===== MÉTODOS PARA LOGS =====
    
    def add_log_message(self, message, msg_type="INFO"):
        """Agregar un mensaje al log."""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = {
                'timestamp': timestamp,
                'message': message,
                'type': msg_type,
                'visible': True
            }
            
            # Agregar al historial
            self.log_messages.append(log_entry)
            
            # Mantener límite de mensajes
            if len(self.log_messages) > self.max_log_messages:
                self.log_messages.pop(0)
            
            # Actualizar display si el tipo está filtrado
            show_timestamp = self.show_timestamp
            
            # Colores según tipo
            colors = {
                "INFO": "#00ff00",
                "ERROR": "#ff0000",
                "WARNING": "#ffff00",
                "CONNECTION": "#00ffff",
                "TRADE": "#ff00ff",
                "DATA": "#aaaaaa"
            }
            
            color = colors.get(msg_type, "#ffffff")
            
            # Verificar filtro
            filter_checkboxes = {
                "INFO": self.cb_log_info,
                "ERROR": self.cb_log_error,
                "WARNING": self.cb_log_warning,
                "TRADE": self.cb_log_trade,
                "CONNECTION": self.cb_log_connection,
                "DATA": self.cb_log_data
            }
            
            if filter_checkboxes.get(msg_type, self.cb_log_info).isChecked():
                # Formatear mensaje
                if show_timestamp:
                    formatted_message = f'<font color="#888888">[{timestamp}]</font> <font color="{color}">{message}</font>'
                else:
                    formatted_message = f'<font color="{color}">{message}</font>'
                
                # Agregar al text edit
                self.log_text_edit.append(formatted_message)
                
                # Auto-scroll si está activado
                if self.cb_auto_scroll.isChecked():
                    self.log_text_edit.moveCursor(QTextCursor.End)
            
            # Actualizar contador
            self.lbl_log_count.setText(f"Mensajes: {len(self.log_messages)}")
            
        except Exception as e:
            print(f"Error al agregar log: {e}")
    
    def clear_logs(self):
        """Limpiar todos los logs."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro de que desea limpiar todos los logs?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.log_text_edit.clear()
            self.log_messages.clear()
            self.lbl_log_count.setText("Mensajes: 0")
            self.add_log_message("Logs limpiados", "INFO")
    
    def save_logs(self):
        """Guardar logs a archivo de texto."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_logs_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== LOGS DE TRADING ===\n")
                f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                
                for log in self.log_messages:
                    if log.get('visible', True):
                        f.write(f"[{log['timestamp']}] [{log['type']}] {log['message']}\n")
            
            self.add_log_message(f"Logs guardados en: {filename}", "INFO")
            QMessageBox.information(self, "Logs Guardados", 
                                  f"Los logs se han guardado en:\n{filename}")
            
        except Exception as e:
            self.add_log_message(f"Error al guardar logs: {str(e)}", "ERROR")
    
    def copy_logs(self):
        """Copiar logs al portapapeles."""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            
            plain_text = ""
            for log in self.log_messages:
                if log.get('visible', True):
                    plain_text += f"[{log['timestamp']}] [{log['type']}] {log['message']}\n"
            
            clipboard.setText(plain_text)
            self.add_log_message("Logs copiados al portapapeles", "INFO")
            
        except Exception as e:
            self.add_log_message(f"Error al copiar logs: {str(e)}", "ERROR")
    
    def export_logs_html(self):
        """Exportar logs como HTML."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_logs_{timestamp}.html"
            
            # Colores para HTML
            colors = {
                "INFO": "#00ff00",
                "ERROR": "#ff0000",
                "WARNING": "#ffff00",
                "CONNECTION": "#00ffff",
                "TRADE": "#ff00ff",
                "DATA": "#aaaaaa"
            }
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Trading Logs - {timestamp}</title>
                <style>
                    body {{
                        background-color: #0a0a0a;
                        color: #e0e0e0;
                        font-family: Consolas, monospace;
                        padding: 20px;
                    }}
                    h1 {{
                        color: #ffffff;
                        border-bottom: 2px solid #444;
                        padding-bottom: 10px;
                    }}
                    .log-entry {{
                        margin: 5px 0;
                        padding: 2px 5px;
                        border-left: 3px solid #444;
                    }}
                    .timestamp {{
                        color: #888888;
                        font-weight: bold;
                    }}
                    .type {{
                        font-weight: bold;
                        padding: 1px 5px;
                        border-radius: 3px;
                        margin: 0 5px;
                    }}
                    .message {{
                        color: #ffffff;
                    }}
                </style>
            </head>
            <body>
                <h1>📋 Logs de Trading</h1>
                <p>Fecha de exportación: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Total de mensajes: {len(self.log_messages)}</p>
                <hr>
                <div id="logs">
            """
            
            for log in self.log_messages:
                if log.get('visible', True):
                    color = colors.get(log['type'], "#ffffff")
                    html_content += f"""
                    <div class="log-entry">
                        <span class="timestamp">[{log['timestamp']}]</span>
                        <span class="type" style="background-color: {color};">{log['type']}</span>
                        <span class="message">{log['message']}</span>
                    </div>
                    """
            
            html_content += """
                </div>
            </body>
            </html>
            """
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.add_log_message(f"Logs exportados como HTML: {filename}", "INFO")
            QMessageBox.information(self, "Exportación Exitosa", 
                                  f"Logs exportados como HTML:\n{filename}")
            
        except Exception as e:
            self.add_log_message(f"Error al exportar HTML: {str(e)}", "ERROR")
    
    def filter_logs(self):
        """Filtrar logs según selección."""
        try:
            # Guardar posición del scroll
            scrollbar = self.log_text_edit.verticalScrollBar()
            scroll_position = scrollbar.value()
            
            # Limpiar display actual
            self.log_text_edit.clear()
            
            # Volver a mostrar logs filtrados
            for log in self.log_messages:
                msg_type = log.get('type', 'INFO')
                
                # Verificar filtro
                filter_checkboxes = {
                    "INFO": self.cb_log_info,
                    "ERROR": self.cb_log_error,
                    "WARNING": self.cb_log_warning,
                    "TRADE": self.cb_log_trade,
                    "CONNECTION": self.cb_log_connection,
                    "DATA": self.cb_log_data
                }
                
                if filter_checkboxes.get(msg_type, self.cb_log_info).isChecked():
                    log['visible'] = True
                    
                    # Colores según tipo
                    colors = {
                        "INFO": "#00ff00",
                        "ERROR": "#ff0000",
                        "WARNING": "#ffff00",
                        "CONNECTION": "#00ffff",
                        "TRADE": "#ff00ff",
                        "DATA": "#aaaaaa"
                    }
                    
                    color = colors.get(msg_type, "#ffffff")
                    
                    # Formatear mensaje
                    if self.show_timestamp:
                        formatted_message = f'<font color="#888888">[{log["timestamp"]}]</font> <font color="{color}">{log["message"]}</font>'
                    else:
                        formatted_message = f'<font color="{color}">{log["message"]}</font>'
                    
                    self.log_text_edit.append(formatted_message)
                else:
                    log['visible'] = False
            
            # Restaurar posición del scroll
            scrollbar.setValue(scroll_position)
            
        except Exception as e:
            print(f"Error al filtrar logs: {e}")
    
    def toggle_timestamp(self):
        """Alternar visibilidad del timestamp."""
        self.show_timestamp = self.btn_toggle_timestamp.isChecked()
        self.filter_logs()
    
    def set_log_limit(self, limit):
        """Establecer límite de mensajes en el log."""
        self.max_log_messages = limit
        # Remover mensajes antiguos si excede el límite
        if len(self.log_messages) > self.max_log_messages:
            self.log_messages = self.log_messages[-self.max_log_messages:]
            self.filter_logs()
    
    # ===== MÉTODO PARA RECIBIR LOGS DEL CHARTVIEW =====
    
    def receive_chart_log(self, message, msg_type="INFO"):
        """Recibir logs del ChartView."""
        self.log_message_received.emit(message, msg_type)
    
    # ===== PESTAÑA DE INDICADORES =====
    
    def create_indicators_tab(self):
        """Crear pestaña de indicadores técnicos."""
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
                    font-size: 11px;
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
        
        # Mostrar mensaje de confirmación en el log
        enabled_count = sum(1 for config in indicators_config.values() if config['enabled'])
        self.add_log_message(f"✅ {enabled_count} indicadores aplicados al gráfico", "INFO")
        
        # Mantener mensaje en el panel de indicadores
        self.indicators_info.append("✅ Indicadores aplicados al gráfico")
        self.indicators_info.append(f"📊 {enabled_count} indicadores activos")
    
    def save_indicators_config(self):
        """Guardar configuración de indicadores en archivo."""
        config_data = {}
        for name, indicator in self.indicators.items():
            config_data[name] = indicator.get_config_dict()
        
        try:
            with open('indicators_config.json', 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self.add_log_message("💾 Configuración de indicadores guardada exitosamente", "INFO")
            self.indicators_info.append("💾 Configuración guardada exitosamente")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al guardar configuración: {str(e)}", "ERROR")
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
            
            self.add_log_message("📂 Configuración de indicadores cargada exitosamente", "INFO")
            self.indicators_info.append("📂 Configuración cargada exitosamente")
            self.update_indicators_info()
            
        except FileNotFoundError:
            self.add_log_message("ℹ️ No se encontró archivo de configuración de indicadores", "INFO")
            self.indicators_info.append("ℹ️ No se encontró archivo de configuración")
        except Exception as e:
            self.add_log_message(f"❌ Error al cargar configuración: {str(e)}", "ERROR")
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
    
    # ===== PESTAÑA DE LOGS =====
    
    def create_logs_tab(self):
        """Crear pestaña de logs del sistema."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Barra de herramientas superior
        toolbar_layout = QHBoxLayout()
        
        # Título
        title_label = QLabel("📋 LOGS DEL SISTEMA")
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin: 5px; 
            color: #ffffff;
            padding: 5px;
        """)
        toolbar_layout.addWidget(title_label)
        toolbar_layout.addStretch()
        
        # Botones de acción
        self.btn_clear_logs = QPushButton("🗑️ Limpiar")
        self.btn_clear_logs.clicked.connect(self.clear_logs)
        self.btn_clear_logs.setFixedHeight(25)
        self.btn_clear_logs.setToolTip("Limpiar todos los logs")
        
        self.btn_save_logs = QPushButton("💾 Guardar")
        self.btn_save_logs.clicked.connect(self.save_logs)
        self.btn_save_logs.setFixedHeight(25)
        self.btn_save_logs.setToolTip("Guardar logs a archivo")
        
        self.btn_copy_logs = QPushButton("📋 Copiar")
        self.btn_copy_logs.clicked.connect(self.copy_logs)
        self.btn_copy_logs.setFixedHeight(25)
        self.btn_copy_logs.setToolTip("Copiar logs al portapapeles")
        
        self.btn_export_html = QPushButton("🌐 Exportar HTML")
        self.btn_export_html.clicked.connect(self.export_logs_html)
        self.btn_export_html.setFixedHeight(25)
        self.btn_export_html.setToolTip("Exportar logs como HTML")
        
        toolbar_layout.addWidget(self.btn_clear_logs)
        toolbar_layout.addWidget(self.btn_save_logs)
        toolbar_layout.addWidget(self.btn_copy_logs)
        toolbar_layout.addWidget(self.btn_export_html)
        
        layout.addLayout(toolbar_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #666; margin: 5px 0px;")
        layout.addWidget(separator)
        
        # Panel de controles de filtro
        filter_panel = QWidget()
        filter_layout = QHBoxLayout(filter_panel)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Etiqueta de filtro
        filter_label = QLabel("Filtrar por tipo:")
        filter_label.setStyleSheet("color: #ffffff; font-size: 11px;")
        filter_layout.addWidget(filter_label)
        
        # Checkboxes de filtro
        self.cb_log_info = QCheckBox("INFO")
        self.cb_log_info.setChecked(True)
        self.cb_log_info.setStyleSheet("color: #00ff00; font-size: 11px;")
        self.cb_log_info.stateChanged.connect(self.filter_logs)
        
        self.cb_log_warning = QCheckBox("WARNING")
        self.cb_log_warning.setChecked(True)
        self.cb_log_warning.setStyleSheet("color: #ffff00; font-size: 11px;")
        self.cb_log_warning.stateChanged.connect(self.filter_logs)
        
        self.cb_log_error = QCheckBox("ERROR")
        self.cb_log_error.setChecked(True)
        self.cb_log_error.setStyleSheet("color: #ff0000; font-size: 11px;")
        self.cb_log_error.stateChanged.connect(self.filter_logs)
        
        self.cb_log_trade = QCheckBox("TRADE")
        self.cb_log_trade.setChecked(True)
        self.cb_log_trade.setStyleSheet("color: #ff00ff; font-size: 11px;")
        self.cb_log_trade.stateChanged.connect(self.filter_logs)
        
        self.cb_log_connection = QCheckBox("CONNECTION")
        self.cb_log_connection.setChecked(True)
        self.cb_log_connection.setStyleSheet("color: #00ffff; font-size: 11px;")
        self.cb_log_connection.stateChanged.connect(self.filter_logs)
        
        self.cb_log_data = QCheckBox("DATA")
        self.cb_log_data.setChecked(True)
        self.cb_log_data.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.cb_log_data.stateChanged.connect(self.filter_logs)
        
        filter_layout.addWidget(self.cb_log_info)
        filter_layout.addWidget(self.cb_log_warning)
        filter_layout.addWidget(self.cb_log_error)
        filter_layout.addWidget(self.cb_log_trade)
        filter_layout.addWidget(self.cb_log_connection)
        filter_layout.addWidget(self.cb_log_data)
        filter_layout.addStretch()
        
        layout.addWidget(filter_panel)
        
        # Área de texto para mostrar logs
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text_edit.setFont(QFont("Consolas", 9))
        self.log_text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 3px;
                selection-background-color: #2a5c8a;
            }
        """)
        
        layout.addWidget(self.log_text_edit, 1)
        
        # Panel inferior con estadísticas
        stats_panel = QWidget()
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setContentsMargins(5, 0, 5, 0)
        
        # Contador de mensajes
        self.lbl_log_count = QLabel("Mensajes: 0")
        self.lbl_log_count.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        
        # Checkbox para auto-scroll
        self.cb_auto_scroll = QCheckBox("Auto-scroll")
        self.cb_auto_scroll.setChecked(True)
        self.cb_auto_scroll.setStyleSheet("color: #cccccc; font-size: 11px;")
        
        # Botón para mostrar/ocultar timestamp
        self.btn_toggle_timestamp = QPushButton("⏰ Timestamp")
        self.btn_toggle_timestamp.setCheckable(True)
        self.btn_toggle_timestamp.setChecked(True)
        self.btn_toggle_timestamp.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #2a5c8a;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.btn_toggle_timestamp.clicked.connect(self.toggle_timestamp)
        
        # Selector de límite de mensajes
        limit_layout = QHBoxLayout()
        limit_layout.setSpacing(5)
        limit_label = QLabel("Límite:")
        limit_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        limit_layout.addWidget(limit_label)
        
        self.spin_log_limit = QSpinBox()
        self.spin_log_limit.setRange(100, 10000)
        self.spin_log_limit.setValue(self.max_log_messages)
        self.spin_log_limit.setSuffix(" mensajes")
        self.spin_log_limit.setStyleSheet("""
            QSpinBox {
                color: #ffffff;
                background-color: #333;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px;
                font-size: 10px;
            }
        """)
        self.spin_log_limit.valueChanged.connect(self.set_log_limit)
        limit_layout.addWidget(self.spin_log_limit)
        
        stats_layout.addWidget(self.lbl_log_count)
        stats_layout.addStretch()
        stats_layout.addWidget(self.cb_auto_scroll)
        stats_layout.addWidget(self.btn_toggle_timestamp)
        stats_layout.addLayout(limit_layout)
        
        layout.addWidget(stats_panel)
        
        return widget
    
    # ===== PESTAÑA DE TRADING (MODIFICADA CON SL/TP NEGATIVOS) =====
    
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
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # Estado de conexión
        self.lbl_connection = QLabel("❌ Desconectado")
        self.lbl_connection.setStyleSheet("color: #ff6666; font-weight: bold;")
        
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
        self.lbl_current_price = QLabel("Bid: -- | Ask: --")
        self.lbl_current_price.setStyleSheet("color: #ffff00; font-weight: bold;")
        symbol_layout.addWidget(self.lbl_current_price, 2, 0, 1, 2)
        
        # 3. Grupo de operación rápida (MODIFICADO PARA SL/TP NEGATIVOS)
        group_quick_trade = QGroupBox("Operación Rápida")
        trade_layout = QGridLayout(group_quick_trade)
        
        # Volumen
        trade_layout.addWidget(QLabel("Volumen (lotes):"), 0, 0)
        self.spin_volume = QDoubleSpinBox()
        self.spin_volume.setRange(0.01, 100.0)
        self.spin_volume.setSingleStep(0.01)
        self.spin_volume.setValue(self.default_volume)
        self.spin_volume.setDecimals(2)
        self.spin_volume.valueChanged.connect(self.update_trade_calculations)
        trade_layout.addWidget(self.spin_volume, 0, 1)
        
        # Stop Loss (pips - permite negativos)
        trade_layout.addWidget(QLabel("Stop Loss:"), 1, 0)
        self.spin_sl = QSpinBox()
        self.spin_sl.setRange(-1000, 1000)  # Permite valores negativos
        self.spin_sl.setValue(self.default_sl)
        self.spin_sl.setSingleStep(10)
        self.spin_sl.setSpecialValueText("0 (Sin SL)")
        self.spin_sl.valueChanged.connect(self.update_trade_calculations)
        trade_layout.addWidget(self.spin_sl, 1, 1)
        
        # Label para mostrar valor SL en dólares
        self.lbl_sl_value = QLabel("SL: 0 pips ($0.00)")
        self.lbl_sl_value.setStyleSheet("color: #ff6666; font-size: 10px;")
        trade_layout.addWidget(self.lbl_sl_value, 2, 0, 1, 2)
        
        # Take Profit (pips - permite negativos)
        trade_layout.addWidget(QLabel("Take Profit:"), 3, 0)
        self.spin_tp = QSpinBox()
        self.spin_tp.setRange(-2000, 2000)  # Permite valores negativos
        self.spin_tp.setValue(self.default_tp)
        self.spin_tp.setSingleStep(10)
        self.spin_tp.setSpecialValueText("0 (Sin TP)")
        self.spin_tp.valueChanged.connect(self.update_trade_calculations)
        trade_layout.addWidget(self.spin_tp, 3, 1)
        
        # Label para mostrar valor TP en dólares
        self.lbl_tp_value = QLabel("TP: 0 pips ($0.00)")
        self.lbl_tp_value.setStyleSheet("color: #66ff66; font-size: 10px;")
        trade_layout.addWidget(self.lbl_tp_value, 4, 0, 1, 2)
        
        # Información sobre SL/TP negativos
        info_label = QLabel("💡 SL/TP negativos = niveles de precio absolutos (ej: -112.50)")
        info_label.setStyleSheet("color: #888; font-size: 9px; font-style: italic;")
        info_label.setWordWrap(True)
        trade_layout.addWidget(info_label, 5, 0, 1, 2)
        
        # Ratio riesgo/recompensa
        self.lbl_risk_reward = QLabel("R/R: 1:0.00")
        self.lbl_risk_reward.setStyleSheet("color: #ffff66; font-size: 11px; font-weight: bold;")
        trade_layout.addWidget(self.lbl_risk_reward, 6, 0, 1, 2)
        
        # Comentario
        trade_layout.addWidget(QLabel("Comentario:"), 7, 0)
        self.txt_comment = QLineEdit()
        self.txt_comment.setPlaceholderText("Operación manual")
        trade_layout.addWidget(self.txt_comment, 7, 1)
        
        # Botones de operación
        self.btn_buy = QPushButton("🟢 COMPRAR")
        self.btn_buy.clicked.connect(self.on_buy_clicked)
        self.btn_buy.setEnabled(False)
        # COLOR PLOMO CUANDO ESTÁ DESHABILITADO
        self.btn_buy.setStyleSheet("""
            QPushButton {
                background-color: #808080;
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
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)
        
        self.btn_sell = QPushButton("🔴 VENDER")
        self.btn_sell.clicked.connect(self.on_sell_clicked)
        self.btn_sell.setEnabled(False)
        # COLOR PLOMO CUANDO ESTÁ DESHABILITADO
        self.btn_sell.setStyleSheet("""
            QPushButton {
                background-color: #808080;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)
        
        trade_layout.addWidget(self.btn_buy, 8, 0, 1, 2)
        trade_layout.addWidget(self.btn_sell, 9, 0, 1, 2)
        
        # Agregar grupos al layout
        layout.addWidget(group_connection)
        layout.addWidget(group_symbol)
        layout.addWidget(group_quick_trade)
        layout.addStretch()
        
        # Actualizar cálculos iniciales
        self.update_trade_calculations()
        
        return widget
    
    def update_trade_calculations(self):
        """Actualizar todos los cálculos de trading."""
        try:
            # Actualizar displays de SL y TP
            self.update_sl_display()
            self.update_tp_display()
            self.update_risk_reward_ratio()
            
        except Exception as e:
            self.add_log_message(f"Error en cálculos de trading: {str(e)}", "ERROR")
    
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
        self.btn_refresh_positions.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        
        self.btn_close_all = QPushButton("❌ Cerrar Todo")
        self.btn_close_all.clicked.connect(self.on_close_all_positions)
        self.btn_close_all.setEnabled(False)
        self.btn_close_all.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        
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
        self.lbl_positions_summary.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        
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
        self.lbl_balance.setStyleSheet("color: #4CAF50; font-weight: bold;")
        financial_layout.addWidget(self.lbl_balance, 0, 1)
        
        financial_layout.addWidget(QLabel("Equity:"), 1, 0)
        self.lbl_equity = QLabel("$ --")
        self.lbl_equity.setStyleSheet("color: #2196F3; font-weight: bold;")
        financial_layout.addWidget(self.lbl_equity, 1, 1)
        
        financial_layout.addWidget(QLabel("Margen:"), 2, 0)
        self.lbl_margin = QLabel("$ --")
        financial_layout.addWidget(self.lbl_margin, 2, 1)
        
        financial_layout.addWidget(QLabel("Margen Libre:"), 3, 0)
        self.lbl_free_margin = QLabel("$ --")
        self.lbl_free_margin.setStyleSheet("color: #FF9800; font-weight: bold;")
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
        self.spin_default_sl.setRange(-1000, 1000)  # Permite negativos
        self.spin_default_sl.setValue(self.default_sl)
        trading_layout.addWidget(self.spin_default_sl, 1, 1)
        
        # TP por defecto
        trading_layout.addWidget(QLabel("TP por defecto (pips):"), 2, 0)
        self.spin_default_tp = QSpinBox()
        self.spin_default_tp.setRange(-2000, 2000)  # Permite negativos
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
        self.btn_save_settings.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.btn_load_settings = QPushButton("📂 Cargar")
        self.btn_load_settings.clicked.connect(self.on_load_settings)
        self.btn_load_settings.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        actions_layout.addWidget(self.btn_save_settings)
        actions_layout.addWidget(self.btn_load_settings)
        
        # Área de información
        self.txt_settings_info = QTextEdit()
        self.txt_settings_info.setReadOnly(True)
        self.txt_settings_info.setMaximumHeight(100)
        self.txt_settings_info.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
        """)
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
            self.lbl_connection.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.add_log_message(f"✅ Conectado a MT5 - {server_info}", "CONNECTION")
            self.btn_connect.setText("🔌 Desconectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.on_disconnect_clicked)
            self.btn_connect.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    padding: 8px;
                    font-weight: bold;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            
            # Cambiar color de botones de compra/venta cuando están habilitados
            self.btn_buy.setEnabled(True)
            self.btn_sell.setEnabled(True)
            self.btn_buy.setStyleSheet("""
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
                QPushButton:disabled {
                    background-color: #666666;
                    color: #999999;
                }
            """)
            self.btn_sell.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    padding: 10px;
                    font-weight: bold;
                    border-radius: 5px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
                QPushButton:disabled {
                    background-color: #666666;
                    color: #999999;
                }
            """)
            
            self.btn_refresh_positions.setEnabled(True)
            self.btn_close_all.setEnabled(True)
            self.btn_refresh_orders.setEnabled(True)
        else:
            self.lbl_connection.setText("❌ Desconectado")
            self.lbl_connection.setStyleSheet("color: #ff6666; font-weight: bold;")
            if message:
                self.add_log_message(f"❌ Desconectado de MT5: {message}", "ERROR")
            self.btn_connect.setText("🔌 Conectar")
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self.on_connect_clicked)
            self.btn_connect.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px;
                    font-weight: bold;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            
            # Cambiar botones de compra/venta a color plomo (gris) cuando están deshabilitados
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(False)
            self.btn_buy.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
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
                QPushButton:disabled {
                    background-color: #666666;
                    color: #999999;
                }
            """)
            self.btn_sell.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: none;
                    padding: 10px;
                    font-weight: bold;
                    border-radius: 5px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
                QPushButton:disabled {
                    background-color: #666666;
                    color: #999999;
                }
            """)
            
            self.btn_refresh_positions.setEnabled(False)
            self.btn_close_all.setEnabled(False)
            self.btn_refresh_orders.setEnabled(False)
    
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
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    padding: 5px;
                    font-weight: bold;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            ticket = pos.get('ticket')
            if ticket:
                close_btn.clicked.connect(lambda checked, t=ticket: self.on_close_position(t))
            self.table_positions.setCellWidget(i, 6, close_btn)
        
        # Actualizar resumen
        self.lbl_positions_summary.setText(f"{len(positions)} posición(es) abierta(s)")
    
    def update_price_display(self, price_data=None):
        """Actualizar display de precios."""
        if price_data:
            self.current_bid_price = price_data.get('bid', 0)
            self.current_ask_price = price_data.get('ask', 0)
            self.lbl_current_price.setText(f"Bid: {self.current_bid_price:.5f} | Ask: {self.current_ask_price:.5f}")
            
            # Actualizar cálculos cuando cambia el precio
            self.update_trade_calculations()
    
    # ===== MANEJADORES DE EVENTOS MODIFICADOS =====
    
    def on_connect_clicked(self):
        """Manejador para botón de conexión."""
        self.add_log_message("Solicitando conexión a MT5...", "CONNECTION")
        self.connect_requested.emit()
    
    def on_disconnect_clicked(self):
        """Manejador para botón de desconexión."""
        self.add_log_message("Solicitando desconexión de MT5...", "CONNECTION")
        self.disconnect_requested.emit()
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.add_log_message(f"Símbolo cambiado a: {symbol}", "INFO")
        self.symbol_changed.emit(symbol)
        
        # Actualizar cálculos con nuevo símbolo
        self.update_trade_calculations()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        self.add_log_message(f"Timeframe cambiado a: {timeframe}", "INFO")
        self.timeframe_changed.emit(timeframe)
    
    def on_buy_clicked(self):
        """Manejador para botón de compra."""
        try:
            if not self.is_connected:
                self.add_log_message("❌ No hay conexión a MT5", "ERROR")
                return
            
            if self.current_ask_price <= 0:
                self.add_log_message("❌ No se pudo obtener el precio de compra", "ERROR")
                return
            
            # Calcular niveles de SL/TP
            sl_pips = self.spin_sl.value()
            tp_pips = self.spin_tp.value()
            
            levels = self.calculate_sl_tp_levels('buy', self.current_ask_price, sl_pips, tp_pips)
            
            order_details = {
                'symbol': self.current_symbol,
                'volume': self.spin_volume.value(),
                'sl': sl_pips,
                'tp': tp_pips,
                'sl_level': levels['sl_level'],
                'tp_level': levels['tp_level'],
                'comment': self.txt_comment.text() or "Compra manual",
                'type': 0,  # 0 = compra
                'price': self.current_ask_price,
                'operation': 'buy'
            }
            
            self.add_log_message(f"📈 Orden de COMPRA enviada:", "TRADE")
            self.add_log_message(f"   • Símbolo: {order_details['symbol']}", "TRADE")
            self.add_log_message(f"   • Volumen: {order_details['volume']} lotes", "TRADE")
            self.add_log_message(f"   • Precio: {order_details['price']:.5f}", "TRADE")
            
            if sl_pips < 0:
                self.add_log_message(f"   • SL: Nivel {order_details['sl_level']:.5f}", "TRADE")
            else:
                self.add_log_message(f"   • SL: {sl_pips} pips ({order_details['sl_level']:.5f})", "TRADE")
            
            if tp_pips < 0:
                self.add_log_message(f"   • TP: Nivel {order_details['tp_level']:.5f}", "TRADE")
            else:
                self.add_log_message(f"   • TP: {tp_pips} pips ({order_details['tp_level']:.5f})", "TRADE")
            
            # Emitir señal para ejecutar en MT5
            self.buy_requested.emit(order_details)
            
        except Exception as e:
            self.add_log_message(f"❌ Error en orden de compra: {str(e)}", "ERROR")
    
    def on_sell_clicked(self):
        """Manejador para botón de venta."""
        try:
            if not self.is_connected:
                self.add_log_message("❌ No hay conexión a MT5", "ERROR")
                return
            
            if self.current_bid_price <= 0:
                self.add_log_message("❌ No se pudo obtener el precio de venta", "ERROR")
                return
            
            # Calcular niveles de SL/TP
            sl_pips = self.spin_sl.value()
            tp_pips = self.spin_tp.value()
            
            levels = self.calculate_sl_tp_levels('sell', self.current_bid_price, sl_pips, tp_pips)
            
            order_details = {
                'symbol': self.current_symbol,
                'volume': self.spin_volume.value(),
                'sl': sl_pips,
                'tp': tp_pips,
                'sl_level': levels['sl_level'],
                'tp_level': levels['tp_level'],
                'comment': self.txt_comment.text() or "Venta manual",
                'type': 1,  # 1 = venta
                'price': self.current_bid_price,
                'operation': 'sell'
            }
            
            self.add_log_message(f"📉 Orden de VENTA enviada:", "TRADE")
            self.add_log_message(f"   • Símbolo: {order_details['symbol']}", "TRADE")
            self.add_log_message(f"   • Volumen: {order_details['volume']} lotes", "TRADE")
            self.add_log_message(f"   • Precio: {order_details['price']:.5f}", "TRADE")
            
            if sl_pips < 0:
                self.add_log_message(f"   • SL: Nivel {order_details['sl_level']:.5f}", "TRADE")
            else:
                self.add_log_message(f"   • SL: {sl_pips} pips ({order_details['sl_level']:.5f})", "TRADE")
            
            if tp_pips < 0:
                self.add_log_message(f"   • TP: Nivel {order_details['tp_level']:.5f}", "TRADE")
            else:
                self.add_log_message(f"   • TP: {tp_pips} pips ({order_details['tp_level']:.5f})", "TRADE")
            
            # Emitir señal para ejecutar en MT5
            self.sell_requested.emit(order_details)
            
        except Exception as e:
            self.add_log_message(f"❌ Error en orden de venta: {str(e)}", "ERROR")
    
    def on_refresh_positions(self):
        """Manejador para refrescar posiciones."""
        self.add_log_message("Solicitando actualización de posiciones...", "INFO")
        self.refresh_positions.emit()
    
    def on_close_all_positions(self):
        """Manejador para cerrar todas las posiciones."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro de cerrar todas las posiciones?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.add_log_message("Solicitando cierre de todas las posiciones...", "TRADE")
            # Aquí deberías emitir una señal para cerrar todas las posiciones
            self.add_log_message("⚠️ Función de cerrar todo pendiente de implementar", "WARNING")
    
    def on_close_position(self, ticket):
        """Manejador para cerrar posición específica."""
        self.add_log_message(f"Solicitando cierre de posición {ticket}...", "TRADE")
        # Aquí deberías emitir una señal para cerrar la posición específica
        self.add_log_message(f"⚠️ Función de cerrar posición {ticket} pendiente de implementar", "WARNING")
    
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
            
            self.add_log_message("✅ Configuración de trading guardada", "INFO")
            self.txt_settings_info.append("✅ Configuración guardada")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al guardar configuración: {str(e)}", "ERROR")
            self.txt_settings_info.append(f"❌ Error: {str(e)}")
    
    def on_load_settings(self):
        """Cargar configuración."""
        try:
            with open('trading_settings.json', 'r') as f:
                settings = json.load(f)
            
            self.load_settings_from_dict(settings)
            self.add_log_message("✅ Configuración de trading cargada", "INFO")
            self.txt_settings_info.append("✅ Configuración cargada")
            
        except FileNotFoundError:
            self.add_log_message("ℹ️ No se encontró archivo de configuración", "INFO")
            self.txt_settings_info.append("ℹ️ No se encontró archivo")
        except Exception as e:
            self.add_log_message(f"❌ Error al cargar configuración: {str(e)}", "ERROR")
            self.txt_settings_info.append(f"❌ Error: {str(e)}")
    
    # ===== MÉTODOS PARA MANEJAR RESULTADOS DE ÓRDENES MT5 =====
    
    def on_order_executed(self, success: bool, message: str, ticket: int = None, order_data: dict = None):
        """Manejador para resultado de orden ejecutada en MT5."""
        if success:
            self.add_log_message(f"✅ Orden ejecutada exitosamente. Ticket: {ticket}", "TRADE")
            
            if order_data:
                # Crear registro local de la orden
                order_record = {
                    'ticket': ticket,
                    'symbol': order_data.get('symbol', ''),
                    'type': order_data.get('type', 0),
                    'volume': order_data.get('volume', 0),
                    'price': order_data.get('price', 0),
                    'sl': order_data.get('sl_level', 0),
                    'tp': order_data.get('tp_level', 0),
                    'profit': 0.0,  # Inicialmente 0
                    'comment': order_data.get('comment', ''),
                    'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'status': 'Ejecutada'
                }
                
                # Agregar a la lista de órdenes
                self.add_order(order_record)
        else:
            self.add_log_message(f"❌ Error al ejecutar orden: {message}", "ERROR")
    
    def on_position_closed(self, success: bool, message: str, ticket: int = None):
        """Manejador para resultado de posición cerrada en MT5."""
        if success:
            self.add_log_message(f"✅ Posición {ticket} cerrada exitosamente", "TRADE")
            
            # Actualizar la orden correspondiente en el historial
            for order in self.orders:
                if order.get('ticket') == ticket:
                    order['status'] = 'Cerrada'
                    order['time_close'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    break
            
            self.update_orders_table()
        else:
            self.add_log_message(f"❌ Error al cerrar posición {ticket}: {message}", "ERROR")
    
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