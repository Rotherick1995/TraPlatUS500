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
    
except ImportError as e:
    print(f"❌ ERROR DE IMPORTACIÓN: {e}")
    print("\nVerifica que existan estos archivos:")
    print("- src/application/use_cases/connect_to_mt5.py")
    print("- src/application/use_cases/fetch_market_data.py")
    sys.exit(1)


class TradingApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("US500 Trading Platform")
        self.app.setStyle('Fusion')
        
        self.is_connected = False
        self.current_symbol = settings.DEFAULT_SYMBOL
        self.current_timeframe = TimeFrame.H1
        
        self.mt5_use_case = None
        self.data_use_case = None
        self.data_repository = None
        self.order_repository = None
        
        try:
            self.main_window = MainWindow()
            self.main_window.show()
            
            if hasattr(self.main_window, 'btn_connect'):
                self.main_window.btn_connect.clicked.connect(self.toggle_mt5_connection)
            
            if hasattr(self.main_window, 'btn_refresh'):
                self.main_window.btn_refresh.clicked.connect(self.refresh_all_data)
            
            # Intentar conexión automática
            if hasattr(settings, 'AUTO_CONNECT') and settings.AUTO_CONNECT:
                QTimer.singleShot(1000, self.connect_to_mt5)
                
        except Exception as e:
            print(f"Error inicializando aplicación: {str(e)}")
            traceback.print_exc()
            sys.exit(1)
    
    def connect_to_mt5(self):
        """Conectar a MetaTrader 5."""
        try:
            if hasattr(self.main_window, 'btn_connect'):
                self.main_window.btn_connect.setEnabled(False)
                self.main_window.btn_connect.setText("Conectando...")
            
            self.mt5_use_case = create_connect_to_mt5_use_case(max_retries=3)
            
            # Esto devuelve un DICCIONARIO
            result = self.mt5_use_case.connect()
            
            # VERIFICACIÓN DE TIPO - IMPORTANTE
            if isinstance(result, dict):
                success = result.get('success', False)
                message = result.get('message', '')
                data = result.get('data', {})
            else:
                # Si no es dict, intentar acceder como objeto
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
                
                # Log exitoso
                if isinstance(data, dict):
                    account_info = data.get('account_info', {})
                else:
                    account_info = getattr(data, 'account_info', {})
                
                login = account_info.get('login', 'N/A') if isinstance(account_info, dict) else getattr(account_info, 'login', 'N/A')
                self.log_message(f"✅ Conectado a MT5 - Cuenta: {login}")
                
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
    
    def disconnect_from_mt5(self):
        """Desconectar de MetaTrader 5."""
        try:
            if self.mt5_use_case:
                result = self.mt5_use_case.disconnect()
                # Verificar si el disconnect fue exitoso si devuelve un dict
                if isinstance(result, dict):
                    success = result.get('success', True)
                    if not success:
                        self.log_message(f"⚠️ Problema al desconectar: {result.get('message', '')}")
            
            self.is_connected = False
            self.update_connection_status(False, "❌ Desconectado")
            
            if hasattr(self.main_window, 'btn_connect'):
                self.main_window.btn_connect.setText("🔌 Conectar a MT5")
            
            self.log_message("🔌 Desconectado de MT5")
            
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
            # Esto devuelve un DICCIONARIO u objeto
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
                
                # Actualizar UI - manejar tanto dict como objeto
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
        
        # Actualizar datos del mercado si existe el caso de uso
        if self.data_use_case:
            self.refresh_market_data()
    
    def refresh_market_data(self):
        """Obtener y mostrar datos del mercado."""
        if not self.is_connected or not self.data_use_case:
            return
        
        try:
            result = self.data_use_case.get_historical_data(
                symbol=self.current_symbol,
                timeframe=self.current_timeframe.value,
                count=100
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
                self.log_message(f"📊 Datos actualizados: {len(data)} velas")
                
                # Actualizar gráfico
                if hasattr(self.main_window, 'chart_view'):
                    self.main_window.chart_view.update_chart(data)
                    
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
        print("🚀 INICIANDO US500 TRADING PLATFORM")
        print("=" * 50)
        print(f"📂 Directorio: {current_dir}")
        print(f"🐍 Python: {sys.version}")
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