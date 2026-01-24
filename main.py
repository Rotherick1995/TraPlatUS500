# main.py
import sys
import os
import traceback
from datetime import datetime

# Agregar src al path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QTimer
    
    from src.infrastructure.ui.main_window import MainWindow
    from src.application.use_cases.connect_to_mt5 import create_connect_to_mt5_use_case
    from src.application.use_cases.fetch_market_data import create_fetch_market_data_use_case
    from src.infrastructure.persistence.mt5.mt5_connection import create_mt5_connection
    from src.infrastructure.persistence.mt5.mt5_data_repository import create_mt5_data_repository
    from src.infrastructure.persistence.mt5.mt5_order_repository import create_mt5_order_repository
    from src.domain.value_objects.timeframe import TimeFrame
    from src.config import settings
    
    # Importaciones para indicadores
    try:
        # Intentar importar indicadores del dominio
        from src.domain.indicators.sma_indicator import SMAIndicator
        from src.domain.indicators.ema_indicator import EMAIndicator
        from src.domain.indicators.rsi_indicator import RSIIndicator
        from src.domain.indicators.macd_indicator import MACDIndicator
        from src.domain.indicators.bollinger_indicator import BollingerIndicator
        from src.domain.indicators.stochastic_indicator import StochasticIndicator
        INDICATORS_AVAILABLE = True
        print("✅ Indicadores del dominio cargados")
    except ImportError as e:
        print(f"⚠️ Indicadores del dominio no disponibles: {e}")
        INDICATORS_AVAILABLE = False
        
except ImportError as e:
    print(f"❌ ERROR DE IMPORTACIÓN: {e}")
    print("\nVerifica que existan estos archivos:")
    print("- src/application/use_cases/connect_to_mt5.py")
    print("- src/application/use_cases/fetch_market_data.py")
    sys.exit(1)


class TradingApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("US500 Trading Platform - Con Indicadores")
        self.app.setStyle('Fusion')
        
        self.is_connected = False
        self.current_symbol = settings.DEFAULT_SYMBOL
        self.current_timeframe = TimeFrame.H1
        
        # NUEVO: Configuración de cantidad de velas
        self.current_candles_count = 100  # Valor por defecto
        
        # Configuración de indicadores
        self.indicators_config = {
            'sma': {'enabled': True, 'color': '#ffff00', 'period': 20, 'line_width': 2},
            'ema': {'enabled': True, 'color': '#ff00ff', 'period': 12, 'line_width': 2},
            'rsi': {'enabled': True, 'color': '#ffaa00', 'period': 14, 'overbought': 70, 'oversold': 30, 'line_width': 2},
            'macd': {'enabled': True, 'fast': 12, 'slow': 26, 'signal': 9, 'line_width': 2},
            'bollinger': {'enabled': True, 'period': 20, 'std': 2.0, 'line_width': 1.5},
            'stochastic': {'enabled': True, 'k_period': 14, 'd_period': 3, 'slowing': 3, 'line_width': 2}
        }
        
        # Instancias de indicadores (si están disponibles)
        self.indicators = {}
        if INDICATORS_AVAILABLE:
            self.init_indicators()
        
        self.mt5_use_case = None
        self.data_use_case = None
        self.data_repository = None
        self.order_repository = None
        
        try:
            self.main_window = MainWindow()
            self.main_window.show()
            
            # Configurar conexiones de señales
            self.setup_signals()
            
            # Cargar datos demo inicial con indicadores
            self.load_demo_data()
            
            # Intentar conexión automática
            if hasattr(settings, 'AUTO_CONNECT') and settings.AUTO_CONNECT:
                QTimer.singleShot(1000, self.connect_to_mt5)
                
        except Exception as e:
            print(f"Error inicializando aplicación: {str(e)}")
            traceback.print_exc()
            sys.exit(1)
    
    def init_indicators(self):
        """Inicializar instancias de indicadores."""
        try:
            self.indicators = {
                'sma': SMAIndicator(period=20),
                'ema': EMAIndicator(period=12),
                'rsi': RSIIndicator(period=14, overbought=70, oversold=30),
                'macd': MACDIndicator(fast_period=12, slow_period=26, signal_period=9),
                'bollinger': BollingerIndicator(period=20, std_multiplier=2.0),
                'stochastic': StochasticIndicator(k_period=14, d_period=3, slowing=3)
            }
            
            # Aplicar configuración a indicadores
            for name, indicator in self.indicators.items():
                if name in self.indicators_config:
                    config = self.indicators_config[name]
                    indicator.set_config(
                        enabled=config.get('enabled', True),
                        color=config.get('color', '#ffffff'),
                        line_width=config.get('line_width', 1.5),
                        **{k: v for k, v in config.items() if k not in ['enabled', 'color', 'line_width']}
                    )
            
            self.log_message("✅ Indicadores técnicos inicializados")
            
        except Exception as e:
            self.log_message(f"⚠️ Error inicializando indicadores: {str(e)}")
    
    def setup_signals(self):
        """Configurar conexiones de señales entre componentes."""
        try:
            # Conexión MT5
            if hasattr(self.main_window, 'btn_connect'):
                self.main_window.btn_connect.clicked.connect(self.toggle_mt5_connection)
            
            # Actualización de datos
            if hasattr(self.main_window, 'btn_refresh'):
                self.main_window.btn_refresh.clicked.connect(self.refresh_all_data)
            
            # Cambio de símbolo
            if hasattr(self.main_window, 'cmb_symbol'):
                self.main_window.cmb_symbol.currentTextChanged.connect(self.on_symbol_changed)
            
            # Cambio de timeframe
            if hasattr(self.main_window, 'cmb_timeframe'):
                self.main_window.cmb_timeframe.currentTextChanged.connect(self.on_timeframe_changed)
            
            # Botón de aplicar indicadores
            if hasattr(self.main_window, 'btn_apply_indicators'):
                self.main_window.btn_apply_indicators.clicked.connect(self.apply_indicators_to_chart)
            
            # Señal de indicadores actualizados
            if hasattr(self.main_window, 'indicators_updated'):
                self.main_window.indicators_updated.connect(self.on_indicators_updated)
            
            # Si el main window tiene control panel, conectar sus señales
            if hasattr(self.main_window, 'control_panel'):
                self.connect_control_panel_signals()
            
            self.log_message("✅ Señales conectadas")
            
        except Exception as e:
            self.log_message(f"⚠️ Error configurando señales: {str(e)}")
    
    def connect_control_panel_signals(self):
        """Conectar señales del control panel."""
        try:
            control_panel = self.main_window.control_panel
            
            # Señales de conexión
            if hasattr(control_panel, 'connect_requested'):
                control_panel.connect_requested.connect(self.connect_to_mt5)
            if hasattr(control_panel, 'disconnect_requested'):
                control_panel.disconnect_requested.connect(self.disconnect_from_mt5)
            
            # Señales de trading
            if hasattr(control_panel, 'buy_requested'):
                control_panel.buy_requested.connect(self.on_trading_signal)
            if hasattr(control_panel, 'sell_requested'):
                control_panel.sell_requested.connect(self.on_trading_signal)
            
            # Señal de indicadores
            if hasattr(control_panel, 'indicators_updated'):
                control_panel.indicators_updated.connect(self.on_indicators_updated_from_control)
                self.log_message("✅ Señal de indicadores del ControlPanel conectada")
            
            # NUEVO: Señal de cantidad de velas
            if hasattr(control_panel, 'candles_count_changed'):
                control_panel.candles_count_changed.connect(self.on_candles_count_changed)
                self.log_message("✅ Señal de cantidad de velas conectada")
            
            self.log_message("✅ Señales del ControlPanel conectadas")
            
        except Exception as e:
            self.log_message(f"⚠️ Error conectando ControlPanel: {str(e)}")
    
    def load_demo_data(self):
        """Cargar datos demo para mostrar indicadores."""
        try:
            # Crear datos demo con cantidad configurable
            demo_candles = self.create_demo_candles(count=self.current_candles_count)
            
            # Aplicar indicadores a datos demo
            self.apply_indicators_to_demo_data(demo_candles)
            
            self.log_message(f"📊 {self.current_candles_count} velas demo cargadas con indicadores")
            
        except Exception as e:
            self.log_message(f"⚠️ Error cargando datos demo: {str(e)}")
    
    def create_demo_candles(self, count=100):
        """Crear datos demo para pruebas."""
        from datetime import datetime, timedelta
        import random
        
        candles = []
        base_price = 5000.0
        current_time = datetime.now() - timedelta(hours=count)
        
        for i in range(count):
            change = random.uniform(-20, 20)
            open_price = base_price
            close_price = base_price + change
            high_price = max(open_price, close_price) + random.uniform(0, 8)
            low_price = min(open_price, close_price) - random.uniform(0, 8)
            
            # Crear objeto candle simple
            candle = type('Candle', (), {
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'timestamp': current_time + timedelta(hours=i),
                'volume': random.randint(1000, 5000)
            })()
            candles.append(candle)
            base_price = close_price
        
        return candles
    
    def apply_indicators_to_demo_data(self, candles):
        """Aplicar indicadores a datos demo."""
        try:
            # Enviar datos demo al chart view
            if hasattr(self.main_window, 'chart_view') and self.main_window.chart_view:
                # Pasar configuración de indicadores
                self.main_window.chart_view.update_indicator_settings(self.indicators_config)
                
                # Actualizar gráfico con datos demo
                self.main_window.chart_view.update_chart(candles, self.indicators_config)
                
                # Actualizar contador de velas
                if hasattr(self.main_window, 'lbl_data_count'):
                    self.main_window.lbl_data_count.setText(f"Velas: {len(candles)}")
                
                # Activar visualización de indicadores
                if hasattr(self.main_window.chart_view, 'btn_toggle_indicators'):
                    self.main_window.chart_view.btn_toggle_indicators.setChecked(True)
                    self.log_message("📈 Botón de indicadores activado")
            
        except Exception as e:
            self.log_message(f"⚠️ Error aplicando indicadores a datos demo: {str(e)}")
    
    def apply_indicators_to_chart(self):
        """Aplicar configuración de indicadores al gráfico."""
        try:
            self.log_message("⚙️ Aplicando indicadores al gráfico...")
            
            # Si tenemos configuración, aplicarla al chart view
            if hasattr(self.main_window, 'chart_view') and self.main_window.chart_view:
                self.main_window.chart_view.update_indicator_settings(self.indicators_config)
                
                # Refrescar datos
                if self.is_connected:
                    self.refresh_market_data()
                else:
                    # Usar datos demo
                    demo_candles = self.create_demo_candles(self.current_candles_count)
                    self.main_window.chart_view.update_chart(demo_candles, self.indicators_config)
                
                # Activar visualización
                if hasattr(self.main_window.chart_view, 'btn_toggle_indicators'):
                    self.main_window.chart_view.btn_toggle_indicators.setChecked(True)
                
                # Contar indicadores activos
                active_count = sum(1 for ind in self.indicators_config.values() if ind['enabled'])
                self.log_message(f"✅ {active_count} indicadores aplicados al gráfico")
            
        except Exception as e:
            self.log_message(f"❌ Error aplicando indicadores: {str(e)}")
    
    def on_indicators_updated(self, indicator_configs):
        """Manejador para señal de indicadores actualizados."""
        try:
            self.log_message("📈 Recibiendo actualización de indicadores...")
            self.indicators_config = indicator_configs
            self.apply_indicators_to_chart()
            
        except Exception as e:
            self.log_message(f"❌ Error en on_indicators_updated: {str(e)}")
    
    def on_indicators_updated_from_control(self, indicator_configs):
        """Manejador para señal de indicadores desde ControlPanel."""
        try:
            self.log_message("📈 Actualización de indicadores desde ControlPanel")
            
            # Actualizar configuración local
            self.indicators_config = indicator_configs
            
            # Actualizar indicadores del dominio si existen
            if self.indicators:
                for name, indicator in self.indicators.items():
                    if name in indicator_configs:
                        config = indicator_configs[name]
                        indicator.set_config(
                            enabled=config.get('enabled', True),
                            color=config.get('color', '#ffffff'),
                            line_width=config.get('line_width', 1.5),
                            **{k: v for k, v in config.items() if k not in ['enabled', 'color', 'line_width']}
                        )
            
            # Aplicar al gráfico
            self.apply_indicators_to_chart()
            
        except Exception as e:
            self.log_message(f"❌ Error en on_indicators_updated_from_control: {str(e)}")
    
    def on_candles_count_changed(self, count):
        """Manejador para cambio de cantidad de velas."""
        try:
            self.current_candles_count = count
            self.log_message(f"📊 Cantidad de velas cambiada a: {count}")
            
            # Actualizar UI si es posible
            if hasattr(self.main_window, 'lbl_candles_count'):
                self.main_window.lbl_candles_count.setText(f"{count}")
            
            # Refrescar datos
            if self.is_connected:
                self.refresh_market_data()
            else:
                # Actualizar datos demo
                demo_candles = self.create_demo_candles(count)
                self.apply_indicators_to_demo_data(demo_candles)
                
        except Exception as e:
            self.log_message(f"❌ Error en on_candles_count_changed: {str(e)}")
    
    def on_symbol_changed(self, symbol):
        """Manejador para cambio de símbolo."""
        self.current_symbol = symbol
        self.log_message(f"📈 Símbolo cambiado a: {symbol}")
        
        # Refrescar datos si está conectado
        if self.is_connected:
            self.refresh_market_data()
    
    def on_timeframe_changed(self, timeframe):
        """Manejador para cambio de timeframe."""
        # Convertir string a TimeFrame
        if hasattr(TimeFrame, timeframe):
            self.current_timeframe = getattr(TimeFrame, timeframe)
        else:
            # Intentar mapear manualmente
            timeframe_map = {
                '1M': TimeFrame.M1, '5M': TimeFrame.M5, '15M': TimeFrame.M15,
                '30M': TimeFrame.M30, '1H': TimeFrame.H1, '4H': TimeFrame.H4,
                '1D': TimeFrame.D1, '1W': TimeFrame.W1
            }
            self.current_timeframe = timeframe_map.get(timeframe, TimeFrame.H1)
        
        self.log_message(f"⏰ Timeframe cambiado a: {timeframe}")
        
        # Refrescar datos si está conectado
        if self.is_connected:
            self.refresh_market_data()
    
    def on_trading_signal(self, order_details):
        """Manejador para señales de trading."""
        action = "COMPRA" if 'buy' in str(order_details).lower() else "VENTA"
        self.log_message(f"📤 Señal de {action} recibida: {order_details}")
    
    def connect_to_mt5(self):
        """Conectar a MetaTrader 5."""
        try:
            if hasattr(self.main_window, 'btn_connect'):
                self.main_window.btn_connect.setEnabled(False)
                self.main_window.btn_connect.setText("Conectando...")
            
            self.mt5_use_case = create_connect_to_mt5_use_case(max_retries=3)
            
            result = self.mt5_use_case.connect()
            
            # VERIFICACIÓN DE TIPO - IMPORTANTE
            if isinstance(result, dict):
                success = result.get('success', False)
                message = result.get('message', '')
                data = result.get('data', {})
            else:
                success = getattr(result, 'success', False)
                message = getattr(result, 'message', '')
                data = getattr(result, 'data', {})
            
            if success:
                self.is_connected = True
                
                # Crear repositorios
                self.data_repository = create_mt5_data_repository()
                self.order_repository = create_mt5_order_repository()
                
                # Crear caso de uso de datos
                self.data_use_case = create_fetch_market_data_use_case(self.mt5_use_case)
                
                # Inicializar repositorios si tienen método initialize
                if self.data_repository and hasattr(self.data_repository, 'initialize'):
                    self.data_repository.initialize()
                if self.order_repository and hasattr(self.order_repository, 'initialize'):
                    self.order_repository.initialize()
                
                # Actualizar UI
                self.update_connection_status(True, "✅ Conectado")
                
                # Actualizar información
                self.update_account_info()
                
                # Aplicar indicadores a datos reales
                QTimer.singleShot(500, self.apply_indicators_to_real_data)
                
                # Log exitoso
                if isinstance(data, dict):
                    account_info = data.get('account_info', {})
                else:
                    account_info = getattr(data, 'account_info', {})
                
                login = account_info.get('login', 'N/A') if isinstance(account_info, dict) else getattr(account_info, 'login', 'N/A')
                self.log_message(f"✅ Conectado a MT5 - Cuenta: {login}")
                self.log_message(f"📈 Aplicando {self.current_candles_count} velas con indicadores...")
                
            else:
                self.update_connection_status(False, f"❌ {message[:30]}")
                self.log_message(f"❌ Error de conexión: {message}")
                
        except Exception as e:
            error_msg = f"Error en conexión MT5: {str(e)}"
            self.update_connection_status(False, "❌ Error")
            self.log_message(f"❌ {error_msg}")
            QMessageBox.critical(self.main_window, "Error de conexión", error_msg)
            
        finally:
            if hasattr(self.main_window, 'btn_connect'):
                self.main_window.btn_connect.setEnabled(True)
                if self.is_connected:
                    self.main_window.btn_connect.setText("🔌 Desconectar")
                else:
                    self.main_window.btn_connect.setText("🔌 Conectar a MT5")
    
    def apply_indicators_to_real_data(self):
        """Aplicar indicadores a datos reales de MT5."""
        try:
            if self.is_connected and self.data_use_case:
                self.refresh_market_data()
        except Exception as e:
            self.log_message(f"⚠️ Error aplicando indicadores a datos reales: {str(e)}")
    
    def disconnect_from_mt5(self):
        """Desconectar de MetaTrader 5."""
        try:
            if self.mt5_use_case:
                result = self.mt5_use_case.disconnect()
                if isinstance(result, dict):
                    success = result.get('success', True)
                    if not success:
                        self.log_message(f"⚠️ Problema al desconectar: {result.get('message', '')}")
            
            self.is_connected = False
            self.update_connection_status(False, "❌ Desconectado")
            
            if hasattr(self.main_window, 'btn_connect'):
                self.main_window.btn_connect.setText("🔌 Conectar a MT5")
            
            # Volver a datos demo con indicadores
            self.load_demo_data()
            
            self.log_message("🔌 Desconectado de MT5 - Volviendo a modo demo")
            
        except Exception as e:
            self.log_message(f"❌ Error desconectando: {str(e)}")
    
    def toggle_mt5_connection(self):
        """Alternar entre conexión y desconexión."""
        if self.is_connected:
            self.disconnect_from_mt5()
        else:
            self.connect_to_mt5()
    
    def update_connection_status(self, connected: bool, message: str):
        """Actualizar estado de conexión en UI."""
        if hasattr(self.main_window, 'lbl_connection_status'):
            self.main_window.lbl_connection_status.setText(message)
    
    def update_account_info(self):
        """Actualizar información de la cuenta."""
        if not self.is_connected or not self.mt5_use_case:
            return
        
        try:
            result = self.mt5_use_case.get_status()
            
            # Manejar tanto dict como objeto
            if isinstance(result, dict):
                success = result.get('success', False)
                data = result.get('data', {})
            else:
                success = getattr(result, 'success', False)
                data = getattr(result, 'data', {})
            
            if success:
                # Obtener account_info de manera segura
                if isinstance(data, dict):
                    account_info = data.get('account_info', {})
                else:
                    account_info = getattr(data, 'account_info', {})
                
                # Actualizar UI
                if hasattr(self.main_window, 'lbl_account'):
                    if isinstance(account_info, dict):
                        login = account_info.get('login', '--')
                    else:
                        login = getattr(account_info, 'login', '--')
                    self.main_window.lbl_account.setText(f"Cuenta: {login}")
                
                if hasattr(self.main_window, 'lbl_balance'):
                    if isinstance(account_info, dict):
                        balance = account_info.get('balance', 0)
                    else:
                        balance = getattr(account_info, 'balance', 0)
                    self.main_window.lbl_balance.setText(f"Balance: ${balance:.2f}")
                
                if hasattr(self.main_window, 'lbl_equity'):
                    if isinstance(account_info, dict):
                        equity = account_info.get('equity', 0)
                    else:
                        equity = getattr(account_info, 'equity', 0)
                    self.main_window.lbl_equity.setText(f"Equity: ${equity:.2f}")
                
                if hasattr(self.main_window, 'lbl_margin'):
                    if isinstance(account_info, dict):
                        margin = account_info.get('margin', 0)
                    else:
                        margin = getattr(account_info, 'margin', 0)
                    self.main_window.lbl_margin.setText(f"Margen: ${margin:.2f}")
                    
        except Exception as e:
            self.log_message(f"❌ Error actualizando cuenta: {str(e)}")
    
    def refresh_all_data(self):
        """Refrescar todos los datos."""
        if not self.is_connected:
            self.log_message("⚠️ No conectado a MT5")
            return
        
        self.log_message("🔄 Actualizando datos...")
        
        # Actualizar información de cuenta
        self.update_account_info()
        
        # Actualizar datos del mercado
        if self.data_use_case:
            self.refresh_market_data()
    
    def refresh_market_data(self):
        """Obtener y mostrar datos del mercado con indicadores."""
        if not self.is_connected or not self.data_use_case:
            return
        
        try:
            # Usar cantidad configurable de velas
            count = self.current_candles_count
            self.log_message(f"📊 Solicitando {count} velas de datos...")
            
            result = self.data_use_case.get_historical_data(
                symbol=self.current_symbol,
                timeframe=self.current_timeframe.value,
                count=count
            )
            
            # Verificar si es diccionario o objeto
            if isinstance(result, dict):
                success = result.get('success', False)
                data = result.get('data', [])
                message = result.get('message', '')
            else:
                success = getattr(result, 'success', False)
                data = getattr(result, 'data', [])
                message = getattr(result, 'message', '')
            
            if success and data:
                self.log_message(f"📊 {len(data)} velas actualizadas")
                
                # Actualizar gráfico CON indicadores
                if hasattr(self.main_window, 'chart_view'):
                    self.main_window.chart_view.update_chart(data, self.indicators_config)
                    
                # Actualizar contador de velas en UI
                if hasattr(self.main_window, 'lbl_data_count'):
                    self.main_window.lbl_data_count.setText(f"Velas: {len(data)}")
                
            else:
                self.log_message(f"⚠️ No se pudieron obtener datos: {message}")
                
        except Exception as e:
            self.log_message(f"❌ Error actualizando datos: {str(e)}")
    
    def log_message(self, message: str):
        """Agregar mensaje al log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            
            # Log en UI si existe
            if hasattr(self.main_window, 'txt_logs'):
                self.main_window.txt_logs.append(log_entry)
            elif hasattr(self.main_window, 'txt_mini_log'):
                self.main_window.txt_mini_log.append(log_entry)
            
            # Imprimir en consola
            print(log_entry)
            
        except:
            pass
    
    def run(self):
        """Ejecutar la aplicación."""
        return self.app.exec_()


def main():
    """Función principal."""
    try:
        print("=" * 50)
        print("🚀 INICIANDO US500 TRADING PLATFORM CON INDICADORES")
        print("=" * 50)
        print(f"📂 Directorio: {current_dir}")
        print(f"🐍 Python: {sys.version}")
        print(f"📈 Indicadores disponibles: {INDICATORS_AVAILABLE}")
        print("=" * 50)
        
        app = TradingApp()
        exit_code = app.run()
        
        print("\n" + "=" * 50)
        print("👋 APLICACIÓN FINALIZADA")
        print("=" * 50)
        
        return exit_code
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())