# src/application/use_cases/connect_to_mt5.py

from typing import Dict, Any, Optional
from datetime import datetime

from src.infrastructure.persistence.mt5.mt5_connection import create_mt5_connection
from src.config.constants import ConnectionStatus


class ConnectToMT5UseCase:
    """Caso de uso para conectar a MetaTrader 5."""
    
    def __init__(self, max_retries: int = 3):
        """
        Inicializa el caso de uso.
        
        Args:
            max_retries: Número máximo de intentos de conexión.
        """
        self.max_retries = max_retries
        self.connection = create_mt5_connection()
        self.connection_time = None
    
    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta la conexión a MT5.
        
        Returns:
            Dict con resultado de la operación.
        """
        try:
            # Conectar a MT5
            success, message = self.connection.connect(max_retries=self.max_retries)
            
            if success:
                self.connection_time = datetime.now()
                
                # Obtener información de la cuenta
                account_info = self.connection.get_account_info()
                
                return {
                    'success': True,
                    'message': message,
                    'data': {
                        'account_info': account_info,
                        'connection_time': self.connection_time,
                        'connection_status': ConnectionStatus.CONNECTED.value
                    }
                }
            else:
                return {
                    'success': False,
                    'message': message,
                    'data': {
                        'connection_status': ConnectionStatus.ERROR.value
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data': {
                    'connection_status': ConnectionStatus.ERROR.value
                }
            }
    
    def disconnect(self) -> Dict[str, Any]:
        """
        Desconecta de MT5.
        
        Returns:
            Dict con resultado de la operación.
        """
        try:
            self.connection.disconnect()
            self.connection_time = None
            
            return {
                'success': True,
                'message': "Desconectado exitosamente",
                'data': {
                    'connection_status': ConnectionStatus.DISCONNECTED.value
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error al desconectar: {str(e)}",
                'data': {
                    'connection_status': ConnectionStatus.ERROR.value
                }
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de la conexión.
        
        Returns:
            Dict con estado de conexión.
        """
        try:
            is_connected = self.connection.is_connected()
            account_info = self.connection.get_account_info() if is_connected else None
            
            status = ConnectionStatus.CONNECTED if is_connected else ConnectionStatus.DISCONNECTED
            
            return {
                'success': True,
                'message': "Estado obtenido",
                'data': {
                    'connected': is_connected,
                    'connection_status': status.value,
                    'account_info': account_info,
                    'connection_time': self.connection_time
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data': {
                    'connected': False,
                    'connection_status': ConnectionStatus.ERROR.value
                }
            }


# Función factory para crear el caso de uso
def create_connect_to_mt5_use_case(max_retries: int = 3) -> ConnectToMT5UseCase:
    """
    Crea y retorna una instancia de ConnectToMT5UseCase.
    
    Args:
        max_retries: Número máximo de intentos de conexión.
        
    Returns:
        ConnectToMT5UseCase: Instancia configurada.
    """
    return ConnectToMT5UseCase(max_retries=max_retries)