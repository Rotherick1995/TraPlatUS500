# src/infrastructure/persistence/mt5/mt5_connection.py

import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

import MetaTrader5 as mt5

from src.config.settings import (
    MT5_LOGIN, MT5_SERVER, MT5_PASSWORD,
    MT5_TIMEOUT, MAX_CONNECTION_RETRIES, CONNECTION_RETRY_DELAY
)


class MT5Connection:
    """Clase para manejar la conexión con MetaTrader 5."""
    
    def __init__(self):
        """Inicializa la conexión MT5."""
        self._initialized = False
    
    def initialize(self) -> bool:
        """Inicializa la conexión con MT5."""
        try:
            if not mt5.initialize(
                login=MT5_LOGIN,
                server=MT5_SERVER,
                password=MT5_PASSWORD,
                timeout=MT5_TIMEOUT
            ):
                return False
            
            self._initialized = True
            return True
            
        except Exception:
            return False
    
    def connect(self, max_retries: int = None) -> Tuple[bool, str]:
        """
        Conecta a la cuenta MT5.
        
        Args:
            max_retries: Número máximo de intentos de conexión.
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        if max_retries is None:
            max_retries = MAX_CONNECTION_RETRIES
        
        # Primero inicializar MT5 si no está inicializado
        if not self._initialized:
            if not self.initialize():
                return False, "No se pudo inicializar MT5"
        
        # Intentar conexión con reintentos
        for attempt in range(max_retries):
            try:
                # Intentar login
                authorized = mt5.login(
                    login=MT5_LOGIN,
                    password=MT5_PASSWORD,
                    server=MT5_SERVER
                )
                
                if authorized:
                    return True, "Conexión exitosa"
                else:
                    if attempt < max_retries - 1:
                        time.sleep(CONNECTION_RETRY_DELAY)
                    
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(CONNECTION_RETRY_DELAY)
        
        return False, f"Fallo la conexión después de {max_retries} intentos"
    
    def disconnect(self):
        """Desconecta de MT5."""
        mt5.shutdown()
        self._initialized = False
    
    def is_connected(self) -> bool:
        """Verifica si está conectado a MT5."""
        try:
            account_info = mt5.account_info()
            return account_info is not None
        except Exception:
            return False
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Obtiene información de la cuenta."""
        if not self.is_connected():
            return None
        
        try:
            account_info = mt5.account_info()
            
            if account_info is None:
                return None
            
            return {
                'login': account_info.login,
                'server': account_info.server,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'currency': account_info.currency,
                'leverage': account_info.leverage
            }
            
        except Exception:
            return None


# Función factory para crear la conexión
def create_mt5_connection() -> MT5Connection:
    """Crea y retorna una instancia de MT5Connection."""
    return MT5Connection()