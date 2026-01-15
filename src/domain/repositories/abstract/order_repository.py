# src/domain/repositories/abstract/order_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class OrderRepository(ABC):
    """Interfaz abstracta para repositorios de órdenes."""
    
    @abstractmethod
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = 0.0, stop_loss: float = 0.0, 
                   take_profit: float = 0.0, comment: str = "") -> Optional[int]:
        """
        Coloca una nueva orden.
        
        Args:
            symbol: Símbolo a operar.
            order_type: Tipo de orden (ej: "MARKET_BUY", "LIMIT_SELL").
            volume: Volumen de la operación.
            price: Precio de entrada (0 para órdenes de mercado).
            stop_loss: Nivel de stop loss.
            take_profit: Nivel de take profit.
            comment: Comentario para la orden.
            
        Returns:
            Ticket de la orden o None si falla.
        """
        pass
    
    @abstractmethod
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Obtiene posiciones abiertas.
        
        Returns:
            Lista de diccionarios con información de posiciones.
        """
        pass
    
    @abstractmethod
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Obtiene órdenes pendientes.
        
        Returns:
            Lista de diccionarios con información de órdenes.
        """
        pass
    
    @abstractmethod
    def close_position(self, ticket: int) -> bool:
        """
        Cierra una posición.
        
        Args:
            ticket: Ticket de la posición a cerrar.
            
        Returns:
            True si se cerró exitosamente, False en caso contrario.
        """
        pass
    
    @abstractmethod
    def cancel_order(self, ticket: int) -> bool:
        """
        Cancela una orden pendiente.
        
        Args:
            ticket: Ticket de la orden a cancelar.
            
        Returns:
            True si se canceló exitosamente, False en caso contrario.
        """
        pass
    
    @abstractmethod
    def modify_order(self, ticket: int, price: float = None, 
                    stop_loss: float = None, take_profit: float = None) -> bool:
        """
        Modifica una orden pendiente.
        
        Args:
            ticket: Ticket de la orden a modificar.
            price: Nuevo precio de entrada.
            stop_loss: Nuevo stop loss.
            take_profit: Nuevo take profit.
            
        Returns:
            True si se modificó exitosamente, False en caso contrario.
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de la cuenta.
        
        Returns:
            Dict con información de la cuenta o None.
        """
        pass