# src/application/use_cases/close_position.py

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

from src.domain.repositories.abstract.order_repository import OrderRepository
from src.application.validators.order_validator import OrderValidator


@dataclass
class ClosePositionRequest:
    """Solicitud para cerrar una o más posiciones."""
    
    ticket: Optional[int] = None  # Ticket específico (None = cerrar todo)
    symbol: Optional[str] = None  # Símbolo específico (None = todos los símbolos)
    volume: float = 0.0  # Volumen a cerrar (0 = cerrar todo)
    partial_close: bool = False  # True para cierre parcial
    comment: str = "Cerrado por aplicación"


@dataclass
class ClosePositionResponse:
    """Respuesta del cierre de posición."""
    
    success: bool
    message: str
    tickets_closed: List[int] = None
    tickets_failed: List[int] = None
    total_profit: float = 0.0
    total_volume: float = 0.0
    timestamp: str = ""


@dataclass
class CloseAllPositionsRequest:
    """Solicitud para cerrar todas las posiciones."""
    
    comment: str = "Cerrado todo por aplicación"
    filter_symbol: Optional[str] = None  # Filtrar por símbolo específico


class ClosePositionUseCase:
    """Caso de uso para cerrar posiciones."""
    
    def __init__(self, order_repository: OrderRepository):
        """
        Inicializa el caso de uso para cerrar posiciones.
        
        Args:
            order_repository: Repositorio de órdenes para comunicación con MT5
        """
        self.order_repository = order_repository
        self.validator = OrderValidator()
        self.logger = logging.getLogger(__name__)
    
    def execute(self, request: ClosePositionRequest) -> ClosePositionResponse:
        """
        Ejecuta el cierre de una posición específica.
        
        Args:
            request: Datos de la posición a cerrar
            
        Returns:
            ClosePositionResponse: Resultado de la operación
        """
        try:
            self.logger.info(f"Iniciando cierre de posición - Ticket: {request.ticket}")
            
            # Validar que tenemos un ticket
            if request.ticket is None or request.ticket <= 0:
                return ClosePositionResponse(
                    success=False,
                    message="Ticket de posición inválido o no especificado",
                    tickets_closed=[],
                    tickets_failed=[],
                    timestamp=datetime.now().isoformat()
                )
            
            # Verificar que la posición existe
            position = self.order_repository.get_position_by_ticket(request.ticket)
            if not position:
                return ClosePositionResponse(
                    success=False,
                    message=f"No se encontró la posición con ticket {request.ticket}",
                    tickets_closed=[],
                    tickets_failed=[request.ticket],
                    timestamp=datetime.now().isoformat()
                )
            
            # Si es cierre parcial, validar volumen
            if request.partial_close and request.volume > 0:
                current_volume = position.get('volume', 0.0)
                if request.volume > current_volume:
                    return ClosePositionResponse(
                        success=False,
                        message=f"Volumen solicitado ({request.volume}) mayor al disponible ({current_volume})",
                        tickets_closed=[],
                        tickets_failed=[request.ticket],
                        timestamp=datetime.now().isoformat()
                    )
                
                # Realizar cierre parcial
                success = self.order_repository.close_position_partial(
                    ticket=request.ticket,
                    volume=request.volume
                )
                
                if success:
                    self.logger.info(f"✅ Cierre parcial exitoso - Ticket: {request.ticket}, Volumen: {request.volume}")
                    return ClosePositionResponse(
                        success=True,
                        message=f"Cierre parcial exitoso: {request.volume} lotes",
                        tickets_closed=[request.ticket],
                        tickets_failed=[],
                        total_volume=request.volume,
                        total_profit=self._calculate_partial_profit(position, request.volume),
                        timestamp=datetime.now().isoformat()
                    )
                else:
                    error_msg = self.order_repository.get_last_error()
                    self.logger.error(f"❌ Error en cierre parcial: {error_msg}")
                    return ClosePositionResponse(
                        success=False,
                        message=f"Error en cierre parcial: {error_msg}",
                        tickets_closed=[],
                        tickets_failed=[request.ticket],
                        timestamp=datetime.now().isoformat()
                    )
            
            else:
                # Cierre completo de la posición
                success = self.order_repository.close_position(request.ticket)
                
                if success:
                    profit = position.get('profit', 0.0)
                    volume = position.get('volume', 0.0)
                    
                    self.logger.info(f"✅ Cierre completo exitoso - Ticket: {request.ticket}, Profit: ${profit:.2f}")
                    
                    return ClosePositionResponse(
                        success=True,
                        message=f"Posición {request.ticket} cerrada exitosamente",
                        tickets_closed=[request.ticket],
                        tickets_failed=[],
                        total_profit=profit,
                        total_volume=volume,
                        timestamp=datetime.now().isoformat()
                    )
                else:
                    error_msg = self.order_repository.get_last_error()
                    self.logger.error(f"❌ Error al cerrar posición: {error_msg}")
                    return ClosePositionResponse(
                        success=False,
                        message=f"Error al cerrar posición: {error_msg}",
                        tickets_closed=[],
                        tickets_failed=[request.ticket],
                        timestamp=datetime.now().isoformat()
                    )
                
        except Exception as e:
            self.logger.exception(f"Excepción inesperada al cerrar posición: {str(e)}")
            
            return ClosePositionResponse(
                success=False,
                message=f"Error inesperado: {str(e)}",
                tickets_closed=[],
                tickets_failed=[request.ticket] if request.ticket else [],
                timestamp=datetime.now().isoformat()
            )
    
    def execute_close_all(self, request: CloseAllPositionsRequest) -> ClosePositionResponse:
        """
        Ejecuta el cierre de todas las posiciones.
        
        Args:
            request: Configuración para cerrar todas las posiciones
            
        Returns:
            ClosePositionResponse: Resultado de la operación
        """
        try:
            self.logger.info(f"Iniciando cierre de todas las posiciones...")
            
            # Obtener todas las posiciones abiertas
            positions = self.order_repository.get_open_positions()
            
            if not positions:
                return ClosePositionResponse(
                    success=True,
                    message="No hay posiciones abiertas para cerrar",
                    tickets_closed=[],
                    tickets_failed=[],
                    total_profit=0.0,
                    total_volume=0.0,
                    timestamp=datetime.now().isoformat()
                )
            
            # Filtrar por símbolo si se especifica
            if request.filter_symbol:
                positions = [p for p in positions if p.get('symbol') == request.filter_symbol]
                self.logger.info(f"Filtrando por símbolo {request.filter_symbol}: {len(positions)} posiciones")
            
            if not positions:
                return ClosePositionResponse(
                    success=True,
                    message=f"No hay posiciones abiertas para el símbolo {request.filter_symbol}",
                    tickets_closed=[],
                    tickets_failed=[],
                    timestamp=datetime.now().isoformat()
                )
            
            tickets_closed = []
            tickets_failed = []
            total_profit = 0.0
            total_volume = 0.0
            
            self.logger.info(f"Cerrando {len(positions)} posiciones...")
            
            # Cerrar cada posición
            for position in positions:
                ticket = position.get('ticket')
                symbol = position.get('symbol', 'Desconocido')
                profit = position.get('profit', 0.0)
                volume = position.get('volume', 0.0)
                
                try:
                    self.logger.debug(f"Cerrando posición {ticket} ({symbol})...")
                    
                    success = self.order_repository.close_position(ticket)
                    
                    if success:
                        tickets_closed.append(ticket)
                        total_profit += profit
                        total_volume += volume
                        
                        self.logger.debug(f"✅ Posición {ticket} cerrada - Profit: ${profit:.2f}")
                    else:
                        error_msg = self.order_repository.get_last_error()
                        tickets_failed.append(ticket)
                        self.logger.error(f"❌ Error al cerrar posición {ticket}: {error_msg}")
                        
                except Exception as e:
                    tickets_failed.append(ticket)
                    self.logger.error(f"❌ Excepción al cerrar posición {ticket}: {str(e)}")
            
            # Preparar mensaje de resultado
            closed_count = len(tickets_closed)
            failed_count = len(tickets_failed)
            
            if closed_count > 0 and failed_count == 0:
                message = f"Todas las {closed_count} posiciones cerradas exitosamente"
            elif closed_count > 0 and failed_count > 0:
                message = f"{closed_count} posiciones cerradas, {failed_count} fallaron"
            else:
                message = f"Fallo al cerrar {failed_count} posiciones"
            
            return ClosePositionResponse(
                success=closed_count > 0,
                message=message,
                tickets_closed=tickets_closed,
                tickets_failed=tickets_failed,
                total_profit=total_profit,
                total_volume=total_volume,
                timestamp=datetime.now().isoformat()
            )
                
        except Exception as e:
            self.logger.exception(f"Excepción inesperada al cerrar todas las posiciones: {str(e)}")
            
            return ClosePositionResponse(
                success=False,
                message=f"Error inesperado: {str(e)}",
                tickets_closed=[],
                tickets_failed=[],
                timestamp=datetime.now().isoformat()
            )
    
    def execute_close_by_symbol(self, symbol: str, comment: str = "Cerrado por símbolo") -> ClosePositionResponse:
        """
        Cierra todas las posiciones de un símbolo específico.
        
        Args:
            symbol: Símbolo a cerrar
            comment: Comentario para las órdenes
            
        Returns:
            ClosePositionResponse: Resultado de la operación
        """
        request = CloseAllPositionsRequest(
            comment=comment,
            filter_symbol=symbol
        )
        return self.execute_close_all(request)
    
    def _calculate_partial_profit(self, position: Dict[str, Any], closed_volume: float) -> float:
        """
        Calcula el profit proporcional para un cierre parcial.
        
        Args:
            position: Información de la posición
            closed_volume: Volumen cerrado
            
        Returns:
            float: Profit proporcional calculado
        """
        try:
            total_volume = position.get('volume', 0.0)
            total_profit = position.get('profit', 0.0)
            
            if total_volume <= 0 or closed_volume <= 0:
                return 0.0
            
            # Calcular profit proporcional
            proportion = closed_volume / total_volume
            partial_profit = total_profit * proportion
            
            return round(partial_profit, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculando profit parcial: {str(e)}")
            return 0.0
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de todas las posiciones abiertas.
        
        Returns:
            Dict[str, Any]: Resumen de posiciones
        """
        try:
            positions = self.order_repository.get_open_positions()
            
            if not positions:
                return {
                    "total_positions": 0,
                    "total_volume": 0.0,
                    "total_profit": 0.0,
                    "by_symbol": {},
                    "has_positions": False
                }
            
            total_profit = sum(p.get('profit', 0.0) for p in positions)
            total_volume = sum(p.get('volume', 0.0) for p in positions)
            
            # Agrupar por símbolo
            by_symbol = {}
            for position in positions:
                symbol = position.get('symbol', 'Desconocido')
                if symbol not in by_symbol:
                    by_symbol[symbol] = {
                        "count": 0,
                        "total_profit": 0.0,
                        "total_volume": 0.0,
                        "tickets": []
                    }
                
                by_symbol[symbol]["count"] += 1
                by_symbol[symbol]["total_profit"] += position.get('profit', 0.0)
                by_symbol[symbol]["total_volume"] += position.get('volume', 0.0)
                by_symbol[symbol]["tickets"].append(position.get('ticket'))
            
            return {
                "total_positions": len(positions),
                "total_volume": total_volume,
                "total_profit": total_profit,
                "by_symbol": by_symbol,
                "has_positions": True
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen de posiciones: {str(e)}")
            return {
                "total_positions": 0,
                "total_volume": 0.0,
                "total_profit": 0.0,
                "by_symbol": {},
                "has_positions": False,
                "error": str(e)
            }


# Factory function para crear el caso de uso
def create_close_position_use_case(order_repository: OrderRepository) -> ClosePositionUseCase:
    """
    Crea una instancia del caso de uso para cerrar posiciones.
    
    Args:
        order_repository: Repositorio de órdenes
        
    Returns:
        ClosePositionUseCase: Instancia del caso de uso
    """
    return ClosePositionUseCase(order_repository)