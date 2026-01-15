# src/application/use_cases/connect_to_mt5.py - VERSIÓN CORREGIDA
from typing import Dict, Any
from datetime import datetime

try:
    import MetaTrader5 as mt5
    from src.infrastructure.persistence.mt5.mt5_connection import create_mt5_connection
    from src.config import settings  # Importar settings para obtener el servidor
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️ MT5 connection no disponible")


class ConnectToMT5UseCase:
    """Caso de uso para conectar a MetaTrader 5."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        if MT5_AVAILABLE:
            self.connection = create_mt5_connection()
        else:
            self.connection = None
        self.connection_time = None
        
        # Obtener servidor desde settings
        self.server_from_settings = getattr(settings, 'MT5_SERVER', 'Pepperstone-Demo')
    
    def connect(self) -> Dict[str, Any]:
        """Conectar a MT5."""
        if not MT5_AVAILABLE or not self.connection:
            return {
                'success': False,
                'message': "MT5 no disponible",
                'data': {}
            }
        
        try:
            # Conectar a MT5
            success, message = self.connection.connect(max_retries=self.max_retries)
            
            if success:
                self.connection_time = datetime.now()
                
                # Obtener información de la cuenta
                account_info = self.connection.get_account_info()
                
                # Obtener información real del servidor desde MT5 si es posible
                server_name = self.server_from_settings  # Por defecto el de settings
                
                # Intentar obtener el servidor real de MT5
                try:
                    if account_info and 'server' in account_info:
                        server_name = account_info.get('server', self.server_from_settings)
                    # Alternativa: intentar obtener de mt5 directamente
                    elif MT5_AVAILABLE and mt5.terminal_info() is not None:
                        # Obtener información de la terminal
                        terminal_info = mt5.terminal_info()
                        if hasattr(terminal_info, 'server'):
                            server_name = terminal_info.server
                        elif hasattr(terminal_info, 'name'):
                            server_name = terminal_info.name
                except:
                    server_name = self.server_from_settings
                
                return {
                    'success': True,
                    'message': message,
                    'data': {
                        'account_info': account_info,
                        'connection_time': self.connection_time,
                        'server': server_name  # Ahora muestra el servidor real
                    }
                }
            else:
                return {
                    'success': False,
                    'message': message,
                    'data': {}
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data': {}
            }
    
    def execute(self) -> Dict[str, Any]:
        """Alias para connect() para compatibilidad."""
        return self.connect()
    
    def disconnect(self) -> Dict[str, Any]:
        """Desconectar de MT5."""
        if not MT5_AVAILABLE or not self.connection:
            return {
                'success': False,
                'message': "MT5 no disponible",
                'data': {}
            }
        
        try:
            self.connection.disconnect()
            self.connection_time = None
            
            return {
                'success': True,
                'message': "Desconectado exitosamente",
                'data': {}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error al desconectar: {str(e)}",
                'data': {}
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de la conexión."""
        if not MT5_AVAILABLE or not self.connection:
            return {
                'success': False,
                'message': "MT5 no disponible",
                'data': {
                    'connected': False
                }
            }
        
        try:
            is_connected = self.connection.is_connected()
            account_info = self.connection.get_account_info() if is_connected else None
            
            server_name = self.server_from_settings
            # Intentar obtener el servidor actual si hay conexión
            if is_connected and account_info:
                server_name = account_info.get('server', self.server_from_settings)
            
            return {
                'success': True,
                'message': "Estado obtenido",
                'data': {
                    'connected': is_connected,
                    'account_info': account_info,
                    'connection_time': self.connection_time,
                    'server': server_name
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data': {
                    'connected': False,
                    'server': self.server_from_settings
                }
            }


def create_connect_to_mt5_use_case(max_retries: int = 3) -> ConnectToMT5UseCase:
    """Crea una instancia de ConnectToMT5UseCase."""
    return ConnectToMT5UseCase(max_retries=max_retries)